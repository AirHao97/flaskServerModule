'''
author:AHAO
createTime:2024/10/23 14:32
description: 采购订单接口
'''

from flask import Blueprint,jsonify,request,current_app,make_response,send_file
import pandas as pd
from Models import db
import uuid
from flask_jwt_extended import jwt_required,get_jwt
from sqlalchemy import or_,cast, DateTime
from sqlalchemy.orm import joinedload
import json
import math
from decimal import Decimal
import random
import base64
from datetime import datetime, timedelta
import threading
import traceback
import xlsxwriter
from io import BytesIO
import io
from PIL import Image as PILImage
import requests
import concurrent.futures
import pytz

from Utils.crud import getDataFromDataBase_BaseData,addDataFromDataBase,modifyDataFromDataBase,deleteDataFromDataBase
from Utils.apiRightsDecorator import admin_required,operations_required,active_required
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType
from Utils.Constant.purchaseStatus import PurchaseStatus
from Utils.Constant.purchaseProductType import PurchaseProductType
from Utils.Constant.purchaseProductStatus import PurchaseProductStatus
from Utils.Constant.systemStatus import SystemStatus
from Utils.purchase_product_label_print import generate_qrcodes_pdf
from Utils.API_1688 import get1688OrderList, get1688OrderDetail,create1688OrderPreview,create1688Order

from Models.Work.purchase_order_model import PurchaseOrder
from Models.Work.purchase_product_model import PurchaseProduct
from Models.Work.system_product_model import SystemProduct 
from Models.User.user_model import User
from Models.Work.ozon_order_model import OzonOrder
from Models.Work.shop_model import Shop

purchase_order_list = Blueprint('purchase_order', __name__, url_prefix='/purchase_order')


# 查询全部的采购数据
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/getData', methods=['GET'])
@jwt_required()
@active_required
def getData():

    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:
        start = int(request.args.get('start', 0))
        limit = int(request.args.get('limit', 10))
        keyWord = request.args.get('keyWord', None)
        purchase_platform = request.args.get('purchase_platform',None)
        status = request.args.get('status',None)
        is_ask = request.args.get('is_ask',None)
        dateRange = request.args.get('dateRange', None)

        if dateRange:
            dateRange = json.loads(dateRange)
            try:
                start_date = datetime.strptime(dateRange[0], "%Y-%m-%d %H:%M:%S")
                end_date = datetime.strptime(dateRange[1], "%Y-%m-%d %H:%M:%S")
                
                utc = pytz.UTC
                start_date_utc = start_date.astimezone(utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                end_date_utc = end_date.astimezone(utc).strftime('%Y-%m-%dT%H:%M:%SZ')

            except ValueError:
                return jsonify({"msg": "时间范围格式错误！"}), 400

        if keyWord:
            columns = [column.name for column in PurchaseOrder.__table__.columns ]
            filters = [getattr(PurchaseOrder, col).like(f'%{keyWord}%') for col in columns]
            query = PurchaseOrder.query.filter(or_(*filters))

            purchase_order_columns = [column.name for column in PurchaseOrder.__table__.columns ]
            purchase_order_filters = [getattr(PurchaseOrder, col).like(f'%{keyWord}%') for col in purchase_order_columns]
            system_product_columns = [column.name for column in SystemProduct.__table__.columns]
            system_product_filters = [getattr(SystemProduct, col).like(f'%{keyWord}%') for col in system_product_columns]

            filters = or_(*purchase_order_filters, *system_product_filters)

            query = (
                PurchaseOrder.query
                .outerjoin(SystemProduct, SystemProduct.id == PurchaseOrder.system_product_id)
                .filter(filters)
            )
        else:
            query = PurchaseOrder.query.outerjoin(SystemProduct, SystemProduct.id == PurchaseOrder.system_product_id)

        if dateRange:
            query = query.filter(
                PurchaseOrder.create_time.between(start_date, end_date),
            )

        if status:
            if status == "全部":
                pass
            else:
               query = query.filter(PurchaseOrder.status == status)
        
        if purchase_platform:
            if purchase_platform == "全部":
                pass
            else:
                query = query.filter(PurchaseOrder.purchase_platform == purchase_platform)
        else:
            return {"msg":"平台选择不能为空！"},400
        
        if is_ask:
            if is_ask == "全部":
                pass
            elif is_ask == "咨询中":
                query = query.filter(PurchaseOrder.is_error == True)
            elif is_ask == "未咨询":
                query = query.filter(PurchaseOrder.is_error == False)

        if current_user.is_admin:
            pass
        elif current_user.department and (current_user.is_department_admin or any(role.id == "2" for role in current_user.roles)):
            query = query.filter(PurchaseOrder.department_id == current_user.department_id)
        else:
            return {"msg":"当前账户无操作权限！"},400

        if status and status == "待采购":
            # 先筛出待采购
            query = query.filter(PurchaseOrder.status == "待采购")
            # 再按 father_id 和 create_time 排序
            query = query.order_by(SystemProduct.father_id.asc(),PurchaseOrder.create_time.asc())
        else:
            query = query.order_by(PurchaseOrder.create_time.asc())

        results = query.offset(start).limit(limit).all()
        count = query.count()
            
        results = {
            "data" :[
            {

                "id": result.id,
                "purchase_id": result.purchase_id,
                "price": result.price,
                "shipping_fee": result.shipping_fee,
                "posting_numbers": result.posting_numbers,
                "logistics_status": result.logistics_status,
                "purchase_platform": result.purchase_platform,
                "status": result.status,
                "is_error": result.is_error,
                "error_words": result.error_words,
                "platform_status": result.platform_status,
                "fill_purchase_id_time": result.fill_purchase_id_time,
                "packer_msg":result.packer_msg,
                "back_fee":result.back_fee,
                "mark": result.mark,
                
                "wait_for_purchase_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                "in_basket_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                "in_transit_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                "stock_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                "out_stock_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                "loss_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.loss]),
                "create_time": result.create_time,

                "system_product": {
                    "id": result.system_product.id,
                    "primary_image": result.system_product.primary_image,
                    "system_sku": result.system_product.system_sku,
                    "reference_weight": result.system_product.reference_weight,
                    "reference_cost": result.system_product.reference_cost,
                    "purchase_link": result.system_product.purchase_link,
                    "supplier_name": result.system_product.supplier_name,
                    "purchase_platform": result.system_product.purchase_platform,
                    "create_time": result.system_product.create_time,
                    "wait_for_purchase_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                    "in_basket_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                    "in_transit_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                    "stock_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                    "out_stock_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                    "loss_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.loss]),
                } if  result.system_product  else None,

                "purchase_products":[
                    {
                        "id": purchase_product.id,
                        "price": purchase_product.price,
                        "stock_in_date": purchase_product.stock_in_date,
                        "sku": purchase_product.sku,
                        "type": purchase_product.type,
                        "status": purchase_product.status,
                        "mark": purchase_product.mark,
                        "purchase_order_id": purchase_product.purchase_order_id,
                        "ozon_order_id": purchase_product.ozon_order_id,
                        "system_product_id": purchase_product.system_product_id,
                        "create_time": purchase_product.create_time,
                        "modify_time": purchase_product.modify_time,
                    }
                    for purchase_product in result.purchase_products
                ]
            } 
            for result in results],
            "count":count
        }

        return jsonify({
            "msg":"查询成功！",
            "data":results
        }), 200 
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 400  

# 查询异常的采购数据
# 系统管理员、部门管理员 和 运营 可操作
@purchase_order_list.route('/operationGetErrorData', methods=['GET'])
@jwt_required()
@active_required
def operationGetErrorData():

    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:
        start = int(request.args.get('start', 0))
        limit = int(request.args.get('limit', 10))
        keyWord = str(request.args.get('keyWord', None))

        if keyWord:
            purchase_product_columns = [column.name for column in PurchaseOrder.__table__.columns ]
            purchase_product_filters = [getattr(PurchaseOrder, col).like(f'%{keyWord}%') for col in purchase_product_columns]

            user_columns = [column.name for column in User.__table__.columns ]
            user_filters = [getattr(User, col).like(f'%{keyWord}%') for col in user_columns]

            filters = or_(*purchase_product_filters, *user_filters)

            query = (
                PurchaseOrder.query
                .outerjoin(PurchaseProduct, PurchaseOrder.id == PurchaseProduct.purchase_order_id)
                .outerjoin(OzonOrder, PurchaseProduct.ozon_order_id == OzonOrder.id)
                .outerjoin(Shop, Shop.id == OzonOrder.shop_id)
                .outerjoin(User, Shop.owner_id == User.id)
                .filter(filters)
            )
        else:
            query = PurchaseOrder.query
        
        query = query.filter(PurchaseOrder.is_error == True)
        
        if current_user.is_admin:
            pass
        elif current_user.department and current_user.is_department_admin:
            query = query.filter(PurchaseOrder.department_id == current_user.department_id)
        elif current_user.department and any(role.id == "1" for role in current_user.roles):
            query = query.join(
                PurchaseProduct, PurchaseOrder.id == PurchaseProduct.purchase_order_id
            ).join(
                OzonOrder,PurchaseProduct.ozon_order_id == OzonOrder.id
            ).join(
                Shop, OzonOrder.shop_id == Shop.id
            ).filter(
                Shop.owner_id == current_user.id
            )
        else:
            return {"msg":"当前账户无操作权限！"},400

        results = query.order_by(PurchaseOrder.create_time).offset(start).limit(limit).all()
        count = query.order_by(PurchaseOrder.create_time).count()
            
        results = {
            "data" :[
            {

                "id": result.id,
                "purchase_id": result.purchase_id,
                "price": result.price,
                "shipping_fee": result.shipping_fee,
                "posting_numbers": result.posting_numbers,
                "logistics_status": result.logistics_status,
                "purchase_platform": result.purchase_platform,
                "status": result.status,
                "is_error": result.is_error,
                "error_words": result.error_words,
                "platform_status": result.platform_status,
                "fill_purchase_id_time": result.fill_purchase_id_time,
                "packer_msg":result.packer_msg,
                "back_fee":result.back_fee,
                "mark": result.mark,

                "wait_for_purchase_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                "in_basket_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                "in_transit_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                "stock_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                "out_stock_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                "loss_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.loss]),
                
                "system_product": {
                    "id": result.system_product.id,
                    "primary_image": result.system_product.primary_image,
                    "system_sku": result.system_product.system_sku,
                    "reference_weight": result.system_product.reference_weight,
                    "reference_cost": result.system_product.reference_cost,
                    "purchase_link": result.system_product.purchase_link,
                    "supplier_name": result.system_product.supplier_name,
                    "purchase_platform": result.system_product.purchase_platform,
                    "create_time": result.system_product.create_time,
                    "wait_for_purchase_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                    "in_basket_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                    "in_transit_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                    "stock_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                    "out_stock_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                    "loss_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.loss]),
                } if  result.system_product  else None,

                "purchase_products":[
                    {
                        "id": purchase_product.id,
                        "price": purchase_product.price,
                        "stock_in_date": purchase_product.stock_in_date,
                        "sku": purchase_product.sku,
                        "type": purchase_product.type,
                        "status": purchase_product.status,
                        "mark": purchase_product.mark,
                        "purchase_order_id": purchase_product.purchase_order_id,
                        "ozon_order_id": purchase_product.ozon_order_id,
                        "system_product_id": purchase_product.system_product_id,
                        "create_time": purchase_product.create_time,
                        "modify_time": purchase_product.modify_time,
                        "operation": purchase_product.ozon_order.shop.owner.username
                    }
                    for purchase_product in result.purchase_products
                ]
            } 
            for result in results],
            "count":count
        }

        return jsonify({
            "msg":"查询成功！",
            "data":results
        }), 200 
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 400  

# 手动修改采购订单的信息(异常信息)
# 系统管理员、部门管理员 和 运营 可操作
# 只能修改备注信息
@purchase_order_list.route('/operationModifyData', methods=['POST'])
@jwt_required()
@active_required
def operationModifyData(): 
    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "id" in data:
        purchase_order_id = data['id']
    else:
        return jsonify({"msg":"id 不能为空！"}),401
    
    purchase_order = PurchaseOrder.query.filter_by(id = purchase_order_id).first()

    if not purchase_order:
        return {"msg":f"找不到id为{purchase_order_id}的采购订单！"},401

    # 权限校验
    if not current_user.is_admin:
        if not (current_user.is_department_admin and purchase_order.department_id == current_user.department_id):
            if not (any(role.id == "1" for role in current_user.roles) and purchase_order.department_id == current_user.department_id):
                return {"msg":"当前账户无操作权限！"},400
    
    modifyContext = []


    if "error_words" in data:
        modifyContext.append(f"异常留言:({purchase_order.error_words} -> {data['error_words']})")
        purchase_order.error_words = data['error_words']

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseOrder,describe=f"操作人:{current_user.username}, 操作:修改信息 id:{purchase_order.id}, 修改内容：{modifyContext}")
        return {"msg":"回复成功！"}, 200  
    except Exception as e:
        return {"msg":"采购订单信息修改失败！"}, 400

# 获取待采购订单的供应商列表
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/getWaitForPurchaseOrderSupplier', methods=['GET'])
@jwt_required()
@active_required
def getWaitForPurchaseOrderSupplier():

    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:

        if current_user.is_admin:
            supplier_names = (
                db.session.query(SystemProduct.supplier_name)
                .join(PurchaseOrder, PurchaseOrder.system_product_id == SystemProduct.id)
                .filter(
                    PurchaseOrder.purchase_platform == "1688",
                    PurchaseOrder.status == PurchaseStatus.waitForPurchase
                )
                .distinct()
                .all()
            )
        elif current_user.department and (current_user.is_department_admin or any(role.id == "2" for role in current_user.roles)):
            supplier_names = (
                db.session.query(SystemProduct.supplier_name)
                .join(PurchaseOrder, PurchaseOrder.system_product_id == SystemProduct.id)
                .filter(
                    PurchaseOrder.purchase_platform == "1688",
                    PurchaseOrder.status == PurchaseStatus.waitForPurchase,
                    PurchaseOrder.department_id == current_user.department_id
                )
                .distinct()
                .all()
            )
        else:
            return {"msg":"当前账户无操作权限！"},400


        supplier_names = (
            db.session.query(SystemProduct.supplier_name)
            .join(PurchaseOrder, PurchaseOrder.system_product_id == SystemProduct.id)
            .filter(
                PurchaseOrder.purchase_platform == "1688",
                PurchaseOrder.status == PurchaseStatus.waitForPurchase
            )
            .distinct()
            .all()
        )

        # 提取 supplier_name
        supplier_names_array = [name.supplier_name if name.supplier_name else "无" for name in supplier_names]
            
        results = {
            "data" : supplier_names_array
        }

        return jsonify({
            "msg":"查询成功！",
            "data":results
        }), 200 
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 400 

# 根据待采购单供应商分类数据
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/getDataInPurchaseMode', methods=['GET'])
@jwt_required()
@active_required
def getDataInPurchaseMode():

    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    supplier_name =  request.args.get('supplier_name',None)
        
    if supplier_name == None:
        return jsonify({"msg":"供应商名字不能为空！"}),401

    if current_user:

        if current_user.is_admin:
            query = PurchaseOrder.query.filter_by(status = PurchaseStatus.waitForPurchase).filter_by(purchase_platform = "1688").join(SystemProduct,PurchaseOrder.system_product_id == SystemProduct.id).filter(SystemProduct.supplier_name == supplier_name)

        elif current_user.department and (current_user.is_department_admin or any(role.id == "2" for role in current_user.roles)):
            query = PurchaseOrder.query.filter_by(status = PurchaseStatus.waitForPurchase).filter_by(department_id = current_user.department_id).filter_by(purchase_platform = "1688").join(SystemProduct,PurchaseOrder.system_product_id == SystemProduct.id).filter(SystemProduct.supplier_name == supplier_name)
        else:
            return {"msg":"当前账户无操作权限！"},400

        results = query.order_by(PurchaseOrder.create_time).all()
        count = query.order_by(PurchaseOrder.create_time).count()
            
        results = {
            "data" :[
            {

                "id": result.id,
                "purchase_id": result.purchase_id,
                "price": result.price,
                "shipping_fee": result.shipping_fee,
                "posting_numbers": result.posting_numbers,
                "logistics_status": result.logistics_status,
                "purchase_platform": result.purchase_platform,
                "status": result.status,
                "is_error": result.is_error,
                "error_words": result.error_words,
                "platform_status": result.platform_status,
                "fill_purchase_id_time": result.fill_purchase_id_time,
                "packer_msg":result.packer_msg,
                "back_fee":result.back_fee,
                "mark": result.mark,

                "wait_for_purchase_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                "in_basket_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                "in_transit_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                "stock_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                "out_stock_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                "loss_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.loss]),
                
                "system_product": {
                    "id": result.system_product.id,
                    "primary_image": result.system_product.primary_image,
                    "system_sku": result.system_product.system_sku,
                    "reference_weight": result.system_product.reference_weight,
                    "reference_cost": result.system_product.reference_cost,
                    "purchase_link": result.system_product.purchase_link,
                    "supplier_name": result.system_product.supplier_name,
                    "purchase_platform": result.system_product.purchase_platform,
                    "create_time": result.system_product.create_time,
                    "wait_for_purchase_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                    "in_basket_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                    "in_transit_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                    "stock_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                    "out_stock_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                    "loss_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.loss]),
                } if  result.system_product  else None,

                "purchase_products":[
                    {
                        "id": purchase_product.id,
                        "price": purchase_product.price,
                        "stock_in_date": purchase_product.stock_in_date,
                        "sku": purchase_product.sku,
                        "type": purchase_product.type,
                        "status": purchase_product.status,
                        "mark": purchase_product.mark,
                        "purchase_order_id": purchase_product.purchase_order_id,
                        "ozon_order_id": purchase_product.ozon_order_id,
                        "system_product_id": purchase_product.system_product_id,
                        "create_time": purchase_product.create_time,
                        "modify_time": purchase_product.modify_time,
                    }
                    for purchase_product in result.purchase_products
                ]
            } 
            for result in results],
            "count":count
        }

        return jsonify({
            "msg":"查询成功！",
            "data":results
        }), 200 
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 400 

# 更新待采购单数据
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/updateData', methods=['POST'])
@jwt_required()
@active_required
def updateData():
    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()
    
    if current_user:
        if current_user.is_admin:
            # 已通过运营审核 等待备货的 ozon订单
            ozon_orders = OzonOrder.query.filter_by(system_status = SystemStatus.reviewedPendingStock).order_by(cast(OzonOrder.in_process_at, DateTime)).all()
        elif current_user.department and (current_user.is_department_admin or any(role.id == "2" for role in current_user.roles)):
            # 已通过运营审核 等待备货的 同部门下的 ozon订单
            ozon_orders = OzonOrder.query.filter_by(system_status = SystemStatus.reviewedPendingStock).join(Shop, OzonOrder.shop_id == Shop.id).join(User,Shop.owner_id == User.id).filter(User.department_id == current_user.department_id).order_by(cast(OzonOrder.in_process_at, DateTime)).all()
        else:
            return {"msg":"当前账户无操作权限！"},400

        # 订单有国内运单号并且在系统内审核的
        ozon_orders = [ozon_order for ozon_order in ozon_orders if (ozon_order.tracking_number and ozon_order.audit_in_system)]
        # ozon_orders = [ozon_order for ozon_order in ozon_orders if ozon_order.tracking_number]     

        for ozon_order in ozon_orders:
            # 已经绑定的全部采购商品
            purchase_products = ozon_order.purchase_products

            for ozon_products_msg in ozon_order.ozon_products_msg:
                quantity1 = int(ozon_products_msg.quantity)
                ozon_product = ozon_products_msg.ozon_product

                for system_product_msg in ozon_product.system_products_msg:
                    system_product = system_product_msg.system_product
                    quantity2 = int(system_product_msg.quantity)
                    quantity = quantity1 * quantity2

                    # 如果没有绑定过采购商品
                    if not purchase_products:
                        for _ in range(quantity):
                            
                            # 采购商品中 有无 库存
                            purchase_product = PurchaseProduct.query.filter_by(system_product_id = system_product.id).filter_by(ozon_order_id = None).filter(
                                or_(
                                    PurchaseProduct.status == PurchaseProductStatus.wait_purchase,
                                    PurchaseProduct.status == PurchaseProductStatus.in_transit,
                                    PurchaseProduct.status == PurchaseProductStatus.in_stock,
                                    PurchaseProduct.status == PurchaseProductStatus.in_basket,
                                )
                            ).first()
                            # 有库存
                            if purchase_product:
                                purchase_product_add_flag = False
                                purchase_order_add_flag = False
                            # 无库存
                            else:
                                purchase_product_add_flag = True

                                # 新建采购商品
                                purchase_product = PurchaseProduct()
                                purchase_product.id = str(uuid.uuid1())
                                purchase_product.sku = system_product.system_sku + "-" + str(random.randint(1000000, 9999999))
                                purchase_product.status = PurchaseProductStatus.wait_purchase
                                purchase_product.system_product_id = system_product.id

                                # 判断是否已经存在这个system_product的 待采购状态的采购单
                                if current_user.is_admin:
                                    purchase_orders_query = PurchaseOrder.query.filter_by(status = PurchaseStatus.waitForPurchase)
                                elif current_user.department and (current_user.is_department_admin or any(role.id == "4" for role in current_user.roles)):
                                    purchase_orders_query = PurchaseOrder.query.filter_by(status = PurchaseStatus.waitForPurchase, department_id = current_user.department_id)

                                purchase_order = purchase_orders_query.filter_by(system_product_id = system_product.id).first()

                                # 已存在此系统内商品的待采购单
                                if purchase_order:
                                    purchase_order_add_flag = False
                                # 没有这个系统内商品的待采购单
                                else:
                                    purchase_order_add_flag = True
                                    # 新增一个采购单
                                    purchase_order = PurchaseOrder()
                                    purchase_order.id = str(uuid.uuid1())
                                    purchase_order.purchase_platform = system_product.purchase_platform
                                    purchase_order.status = PurchaseStatus.waitForPurchase
                                    purchase_order.system_product_id = system_product.id
                                    if ozon_order.shop.owner:
                                        purchase_order.department_id = ozon_order.shop.owner.department_id
                                    else:
                                        return {"msg": f"店铺{ozon_order.shop.name} 尚未分配责任人！"}, 400
                                    
                                # 采购商品绑定采购单
                                purchase_product.purchase_order_id = purchase_order.id

                                db.session.add(purchase_order)
                                db.session.add(purchase_product)

                            # 更新信息    
                            # 非组合单
                            if len(ozon_order.ozon_products_msg) == 1 and len(ozon_product.system_products_msg) == 1 and quantity == 1:
                                purchase_product.type = PurchaseProductType.single_order
                            # 组合单
                            else:
                                purchase_product.type = PurchaseProductType.group_order
                            
                            purchase_product.ozon_order_id = ozon_order.id

                            # 数据加载入数据库
                            try:
                                if purchase_order_add_flag:
                                    operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:新增采购单, id:{purchase_order.id}")                                
                                if purchase_product_add_flag:
                                    operate_log_writer_func(operateType=OperateType.purchaseProduct, describe=f"操作人:{current_user.username}, 操作:新增采购商品, 库存采购订单id:{purchase_product.id},用于 ozon订单{ozon_order.id},绑定采购订单{purchase_order.id}")
                                else:
                                    operate_log_writer_func(operateType=OperateType.purchaseProduct, describe=f"操作人:{current_user.username}, 操作:申用库存采购商品, 库存采购商品id:{purchase_product.id} 用于 ozon订单{ozon_order.id}")
                                
                                db.session.commit()
                            except Exception as e:
                                operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:更新采购单, 报错：{e}")
                                return {"msg": f"采购单更新失败！{e}"}, 400
                    
                    # 绑定过采购商品
                    else:
                        # 已绑定的这个系统内商品目录下的采购商品
                        already_purchase_products = [purchase_product for purchase_product in purchase_products if ((purchase_product.system_product_id == system_product.id) and (not (purchase_product.status == PurchaseProductStatus.loss or purchase_product.status == PurchaseProductStatus.out_stock)))]
                        already_number = len(already_purchase_products)

                        # 校验 商品数量是否正确
                        if already_number == quantity:
                            pass
                        if already_number > quantity:
                            # 可能是对应关系改了 随机把多出来的置空
                            # 绑定还没下单的采购产品
                            already_purchase_products_wait_for_purchase = [item for item in already_purchase_products if item.purchase_order.status == PurchaseStatus.waitForPurchase]
                            already_purchase_products_wait_for_purchase_number = len(already_purchase_products_wait_for_purchase)
                            
                            if already_purchase_products_wait_for_purchase_number >= (already_number - quantity):
                                
                                wait_for_purchase_purchase_order_id_list = []
                                modify_context_purchase_order = []
                                modify_context_purchase_product = []

                                for index in range(already_number - quantity):
                                    purchase_product = already_purchase_products_wait_for_purchase[index]
                                    purchase_order = purchase_product.purchase_order
                                    # 如果采购单还是待采购 
                                    if purchase_order.status == PurchaseStatus.waitForPurchase:
                                        if purchase_order.id not in wait_for_purchase_purchase_order_id_list:
                                            wait_for_purchase_purchase_order_id_list.append(purchase_order.id)
                                        db.session.delete(purchase_product)
                                        modify_context_purchase_product.append(f"ozon订单{ozon_order.id}初始绑定系统内商品数量大于现在所需,删除该采购商品{purchase_product.id}")
                                    else:
                                        purchase_product.ozon_order_id = None
                                        purchase_product.type = PurchaseProductType.unmatched
                                        modify_context_purchase_product.append(f"ozon订单{ozon_order.id}初始绑定系统内商品数量大于现在所需,解除该采购商品{purchase_product.id}与ozon订单的关联，该ozon商品变成库存商品！")
                                
                                # 更新关系
                                db.session.flush()

                                for wait_for_purchase_purchase_order_id in wait_for_purchase_purchase_order_id_list:
                                    item_purchase_order = PurchaseOrder.query.filter_by(id = wait_for_purchase_purchase_order_id).first()

                                    if not item_purchase_order.purchase_products:
                                        db.session.delete(item_purchase_order)
                                        modify_context_purchase_order.append(f"ozon订单{ozon_order.id}初始绑定系统内商品数量大于现在所需,去除多待采购产品后，采购单数量为空，删除该采购订单{wait_for_purchase_purchase_order_id}")
                                
                                # 更新订单中商品的状态信息
                                for item in ozon_order.purchase_products:
                                    # 更新信息    
                                    # 非组合单
                                    if len(ozon_order.ozon_products_msg) == 1 and len(ozon_product.system_products_msg) == 1 and quantity == 1:
                                        item.type = PurchaseProductType.single_order
                                    # 组合单
                                    else:
                                        item.type = PurchaseProductType.group_order


                                # 数据加载入数据库
                                try:
                                    if modify_context_purchase_order:
                                        operate_log_writer_func(operateType=OperateType.purchaseOrder,describe=f"操作人:{current_user.username}, 操作:{modify_context_purchase_order}",isSystem=True)
                                    if modify_context_purchase_product:
                                        operate_log_writer_func(operateType=OperateType.purchaseProduct,describe=f"操作人:{current_user.username}, 操作:{modify_context_purchase_product}",isSystem=True)
                                    db.session.commit()
                                except Exception as e:
                                    operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:更新采购单, id:{purchase_order.id}, 报错：{e}")
                                    return {"msg": f"采购单更新失败！{e}"}, 400
                            else:
                                wait_for_purchase_purchase_order_id_list = []
                                modify_context_purchase_order = []
                                modify_context_purchase_product = []

                                # 先把待采购的全删了
                                for purchase_product in already_purchase_products_wait_for_purchase:                             
                                    purchase_order = purchase_product.purchase_order
                                    # 如果采购单还是待采购 
                                    if purchase_order.status == PurchaseStatus.waitForPurchase:
                                        wait_for_purchase_purchase_order_id_list.append(purchase_order)
                                        db.session.delete(purchase_product)
                                        modify_context_purchase_product.append(f"ozon订单{ozon_order.id}初始绑定系统内商品数量大于现在所需,删除该采购商品{purchase_product.id}")
                                    else:
                                        purchase_product.ozon_order_id = None
                                        purchase_product.type = PurchaseProductType.unmatched
                                        modify_context_purchase_product.append(f"ozon订单{ozon_order.id}初始绑定系统内商品数量大于现在所需,解除该采购商品{purchase_product.id}与ozon订单的关联，该ozon商品变成库存商品！")
                                
                                # 更新关系
                                db.session.flush()

                                for wait_for_purchase_purchase_order_id in wait_for_purchase_purchase_order_id_list:
                                    item_purchase_order = PurchaseOrder.query.filter_by(id = wait_for_purchase_purchase_order_id).first()

                                    if not item_purchase_order.purchase_products:
                                        db.session.delete(item_purchase_order)
                                        modify_context_purchase_order.append(f"ozon订单{ozon_order.id}初始绑定系统内商品数量大于现在所需,去除多待采购产品后，采购单数量为空，删除该采购订单{wait_for_purchase_purchase_order_id}")

                                    
                                # 剩下非待采购的随机挑几个把对应的ozon id、对应ozon订单的类别改掉
                                already_purchase_products_not_wait_for_purchase = [item for item in already_purchase_products if not item.purchase_order.status == PurchaseStatus.waitForPurchase]
                                for index in range(already_number - quantity - already_purchase_products_wait_for_purchase_number):
                                    purchase_product = already_purchase_products_not_wait_for_purchase[index]
                                    purchase_product.ozon_order_id = None
                                    purchase_product.type = PurchaseProductType.unmatched
                                    modify_context_purchase_product.append(f"ozon订单{ozon_order.id}初始绑定系统内商品数量大于现在所需,解除该采购商品{purchase_product.id}与ozon订单的关联，该ozon商品变成库存商品！")
                                
                                # 更新关系
                                db.session.flush()

                                # 更新订单中商品的状态信息
                                for item in ozon_order.purchase_products:
                                    # 更新信息    
                                    # 非组合单
                                    if len(ozon_order.ozon_products_msg) == 1 and len(ozon_product.system_products_msg) == 1 and quantity == 1:
                                        item.type = PurchaseProductType.single_order
                                    # 组合单
                                    else:
                                        item.type = PurchaseProductType.group_order

                                # 数据加载入数据库
                                try:
                                    if modify_context_purchase_order:
                                        operate_log_writer_func(operateType=OperateType.purchaseOrder,describe=f"操作人:{current_user.username}, 操作:{modify_context_purchase_order}",isSystem=True)
                                    if modify_context_purchase_product:
                                        operate_log_writer_func(operateType=OperateType.purchaseProduct,describe=f"操作人:{current_user.username}, 操作:{modify_context_purchase_product}",isSystem=True)
                                    db.session.commit()
                                except Exception as e:
                                    operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:更新采购单, id:{purchase_order.id}, 报错：{e}")
                                    return {"msg": f"采购单更新失败！{e}"}, 400
                        
                        if already_number < quantity:
                            # 更新前面的单子的状态
                            for item in already_purchase_products:
                                # 更新信息    
                                # 非组合单
                                if len(ozon_order.ozon_products_msg) == 1 and len(ozon_product.system_products_msg) == 1 and quantity == 1:
                                    item.type = PurchaseProductType.single_order
                                # 组合单
                                else:
                                    item.type = PurchaseProductType.group_order

                            for _ in range(quantity - already_number):
                                # 采购商品中 有无 库存
                                purchase_product = PurchaseProduct.query.filter_by(system_product_id = system_product.id).filter_by(ozon_order_id = None).filter(
                                    or_(
                                        PurchaseProduct.status == PurchaseProductStatus.wait_purchase,
                                        PurchaseProduct.status == PurchaseProductStatus.in_transit,
                                        PurchaseProduct.status == PurchaseProductStatus.in_stock,
                                        PurchaseProduct.status == PurchaseProductStatus.in_basket,
                                    )
                                ).first()
                                
                                # 有库存
                                if purchase_product:
                                    purchase_product_add_flag = False
                                # 无库存
                                else:
                                    purchase_product_add_flag = True

                                    # 新建采购商品
                                    purchase_product = PurchaseProduct()
                                    purchase_product.id = str(uuid.uuid1())
                                    purchase_product.sku = system_product.system_sku + "-" + str(random.randint(1000000, 9999999))
                                    purchase_product.status = PurchaseProductStatus.wait_purchase
                                    purchase_product.system_product_id = system_product.id

                                    # 判断是否已经存在这个system_product的 待采购状态的采购单
                                    if current_user.is_admin:
                                        purchase_orders_query = PurchaseOrder.query.filter_by(status = PurchaseStatus.waitForPurchase)
                                    elif current_user.department and (current_user.is_department_admin or any(role.id == "4" for role in current_user.roles)):
                                        purchase_orders_query = PurchaseOrder.query.filter_by(status = PurchaseStatus.waitForPurchase, department_id = current_user.department_id)

                                    purchase_order = purchase_orders_query.filter_by(system_product_id = system_product.id).first()

                                    # 已存在此系统内商品的待采购单
                                    if purchase_order:
                                        purchase_order_add_flag = False
                                    # 没有这个系统内商品的待采购单
                                    else:
                                        purchase_order_add_flag = True
                                        # 新增一个采购单
                                        purchase_order = PurchaseOrder()
                                        purchase_order.id = str(uuid.uuid1())
                                        purchase_order.purchase_platform = system_product.purchase_platform
                                        purchase_order.status = PurchaseStatus.waitForPurchase
                                        purchase_order.system_product_id = system_product.id
                                        purchase_order.department_id = ozon_order.shop.owner.department_id

                                    # 采购商品绑定采购单
                                    purchase_product.purchase_order_id = purchase_order.id

                                    db.session.add(purchase_order)
                                    db.session.add(purchase_product)

                                # 更新信息    
                                # 非组合单
                                if len(ozon_order.ozon_products_msg) == 1 and len(ozon_product.system_products_msg) == 1 and quantity == 1:
                                    purchase_product.type = PurchaseProductType.single_order
                                # 组合单
                                else:
                                    purchase_product.type = PurchaseProductType.group_order
                                
                                purchase_product.ozon_order_id = ozon_order.id

                                # 数据加载入数据库
                                try:
                                    if purchase_order_add_flag:
                                        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:新增采购单, id:{purchase_order.id}")                                
                                    if purchase_product_add_flag:
                                        operate_log_writer_func(operateType=OperateType.purchaseProduct, describe=f"操作人:{current_user.username}, 操作:新增采购商品, 库存采购商品id:{purchase_product.id},用于 ozon订单{ozon_order.id},绑定采购订单{purchase_order.id}")
                                    else:
                                        operate_log_writer_func(operateType=OperateType.purchaseProduct, describe=f"操作人:{current_user.username}, 操作:申用库存采购商品, 库存采购商品id:{purchase_product.id} 用于 ozon订单{ozon_order.id}")
                                    
                                    db.session.commit()
                                except Exception as e:
                                    operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:更新采购单, id:{purchase_order.id}, 报错：{e}")
                                    return {"msg": f"采购单更新失败！{e}"}, 400
        return jsonify({
            "msg":"采购单更新成功！"
        }), 200

    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 400 

# 批量给采购订单填写订单号
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/fillThePurchaseIdForPurchaseOrders', methods=['POST'])
@jwt_required()
@active_required
def fillThePurchaseIdForPurchaseOrders(): 
    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if not current_user.is_admin:
        if not (current_user.is_department_admin):
                if not any(role.id == "2" for role in current_user.roles):
                    return {"msg":"当前账户无操作权限！"},400
        
    data = request.get_json()

    if "purchase_order_ids" in data:
        purchase_order_ids = data['purchase_order_ids']
    else:
        return jsonify({"msg":"修改采购单列表 不能为空！"}),401
    
    if not purchase_order_ids:
        return jsonify({"msg":"修改采购单列表 不能为空！"}),401
        

    if "purchase_id" in data:
        purchase_id = data['purchase_id']
    else:
        return jsonify({"msg":"运单号 不能为空！"}),401
    
    if not purchase_id:
        return jsonify({"msg":"运单号 不能为空！"}),401
    
    purchase_orders = PurchaseOrder.query.filter((PurchaseOrder.id.in_(purchase_order_ids))).all()
    
    modifyContext = []

    for purchase_order in purchase_orders:
        if not current_user.is_admin:
            if purchase_order.department_id != current_user.department_id:
                return jsonify({"msg": f"采购单{purchase_order.id} 不在当前账号部门！"}),400
        
        # 填写运单号
        if purchase_order.purchase_id:
            return jsonify({"msg": f"采购单{purchase_order.id} 已经存在订单号！"}),400    
        
        purchase_order.purchase_id = purchase_id
        purchase_order.purchaser_id = current_user.id
        # 新增填写运单号的时间
        purchase_order.fill_purchase_id_time = datetime.now()

        # 更改采购单状态
        if not purchase_order.status == PurchaseStatus.waitForPurchase:
            return jsonify({"msg": f"采购单{purchase_order.id} 当前状态为{purchase_order.status},无法添加采购单号！"}),400  
         
        modifyContext.append(f"采购订单{purchase_order.id} 状态变更 {purchase_order.status} => {PurchaseStatus.inTransit}")
        purchase_order.status = PurchaseStatus.inTransit
        # 采购商品更改状态
        for purchase_product in purchase_order.purchase_products:
            if purchase_product.status == PurchaseProductStatus.wait_purchase:
                modifyContext.append(f"采购商品 {purchase_product.id} 状态变更 {purchase_product.status} => {PurchaseProductStatus.in_transit}")
                purchase_product.status = PurchaseProductStatus.in_transit
        
    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:采购单添加订单号, ids:{[purchase_order.id for purchase_order in purchase_orders]} 运单号：{purchase_id} 状态变更信息：{modifyContext}")
        return jsonify({
            "msg":"采购单添加国内运单号成功！"
        }), 200
    except Exception as e:
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:采购单添加订单号, ids:{[purchase_order.id for purchase_order in purchase_orders]}, 报错：{e}")
        return {"msg":"采购单添加国内运单号失败！"}, 400

# 给采购订单填写订单号
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/fillThePurchaseIdForPurchaseOrder', methods=['POST'])
@jwt_required()
@active_required
def fillThePurchaseIdForPurchaseOrder(): 
    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if not current_user.is_admin:
        if not (current_user.is_department_admin):
                if not any(role.id == "2" for role in current_user.roles):
                    return {"msg":"当前账户无操作权限！"},400
        
    data = request.get_json()
    
    if "purchase_order_id" in data:
        purchase_order_id = data['purchase_order_id']
    else:
        return jsonify({"msg":"修改采购单列表 不能为空！"}),401
    
    if not purchase_order_id:
        return jsonify({"msg":"修改采购单列表 不能为空！"}),401
        

    if "purchase_id" in data:
        purchase_id = data['purchase_id']
    else:
        return jsonify({"msg":"运单号 不能为空！"}),401
    
    if not purchase_id:
        return jsonify({"msg":"运单号 不能为空！"}),401
    
    purchase_order = PurchaseOrder.query.filter_by(id = purchase_order_id).first()
    
    if not purchase_order.status == PurchaseStatus.waitForPurchase:
        return jsonify({"msg": f"采购单{purchase_order.id} 当前状态为{purchase_order.status},无法添加采购单号！"}),400
    
    modifyContext = []

    if not current_user.is_admin:
        if purchase_order.department_id != current_user.department_id:
            return jsonify({"msg": f"采购单{purchase_order.id} 不在当前账号部门！"}),400
        
    # 填写运单号
    if purchase_order.purchase_id:
        return jsonify({"msg": f"采购单{purchase_order.id} 已经存在订单号！"}),400

    purchase_order.purchase_id = purchase_id
    # 更改采购单状态
    purchase_order.purchaser_id = current_user.id
    # 新增填写运单号的时间
    purchase_order.fill_purchase_id_time = datetime.now()


    modifyContext.append(f"采购订单{purchase_order.id} 状态变更 {purchase_order.status} => {PurchaseStatus.inTransit}")
    purchase_order.status = PurchaseStatus.inTransit
    
    # 采购商品更改状态
    for purchase_product in purchase_order.purchase_products:
        if purchase_product.status == PurchaseProductStatus.wait_purchase:
            modifyContext.append(f"采购商品 {purchase_product.id} 状态变更 {purchase_product.status} => {PurchaseProductStatus.in_transit}")
            purchase_product.status = PurchaseProductStatus.in_transit
        
    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:采购单添加订单号, id:{purchase_order.id} 订单号：{purchase_id} 状态变更信息：{modifyContext}")
        return jsonify({
            "msg":"采购单添加国内运单号成功！"
        }), 200
    except Exception as e:
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:采购单添加订单号, ids:{purchase_order.id}, 报错：{e}")
        return {"msg":"采购单添加国内运单号失败！"}, 400
    
# 手动修改采购订单的信息
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/modifyData', methods=['POST'])
@jwt_required()
@active_required
def modifyData(): 
    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "id" in data:
        purchase_order_id = data['id']
    else:
        return jsonify({"msg":"id 不能为空！"}),401
    
    purchase_order = PurchaseOrder.query.filter_by(id = purchase_order_id).first()

    if not purchase_order:
        return {"msg":f"找不到id为{purchase_order_id}的产品！"},401

    # 权限校验
    if not current_user.is_admin:
        if not (current_user.is_department_admin and purchase_order.department_id == current_user.department_id):
            if not (any(role.id == "2" for role in current_user.roles) and purchase_order.department_id == current_user.department_id):
                return {"msg":"当前账户无操作权限！"},400
    
    modifyContext = []

    if "logistics_status" in data:
        modifyContext.append(f"物流状态:({purchase_order.logistics_status} -> {data['logistics_status']})")
        purchase_order.logistics_status = data['logistics_status']
    if "posting_numbers" in data:
        modifyContext.append(f"国内运单号:({purchase_order.posting_numbers} -> {data['posting_numbers']})")
        purchase_order.posting_numbers = data['posting_numbers']
    if "price" in data:
        modifyContext.append(f"价格:({purchase_order.price} -> {data['price']})")
        purchase_order.price = data['price']
    if "purchase_id" in data:
        modifyContext.append(f"采购订单号:({purchase_order.purchase_id} -> {data['purchase_id']})")
        purchase_order.purchase_id = data['purchase_id']
    if "purchase_platform" in data:
        modifyContext.append(f"采购平台:({purchase_order.purchase_platform} -> {data['purchase_platform']})")
        purchase_order.purchase_platform = data['purchase_platform']
    if "status" in data:
        modifyContext.append(f"采购状态:({purchase_order.status} -> {data['status']})")
        purchase_order.status = data['status']
    if "is_error" in data:
        modifyContext.append(f"是否异常:({purchase_order.is_error} -> {data['is_error']})")
        purchase_order.is_error = data['is_error']
    if "error_words" in data:
        modifyContext.append(f"异常留言:({purchase_order.error_words} -> {data['error_words']})")
        purchase_order.error_words = data['error_words']
    if "shipping_fee" in data:
        modifyContext.append(f"运费:({purchase_order.shipping_fee} -> {data['shipping_fee']})")
        purchase_order.shipping_fee = data['shipping_fee']
    if "back_fee" in data:
        modifyContext.append(f"退货费用:({purchase_order.back_fee} -> {data['back_fee']})")
        purchase_order.back_fee = data['back_fee']
    if "mark" in data:
        modifyContext.append(f"订单备注:({purchase_order.mark} -> {data['mark']})")
        purchase_order.mark = data['mark']

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseOrder,describe=f"操作人:{current_user.username}, 操作:修改信息 id:{purchase_order.id}, 修改内容：{modifyContext}")
        return {"msg":"采购订单信息修改成功！"}, 200  
    except Exception as e:
        return {"msg":"采购订单信息修改失败！"}, 400

# 拆分采购订单
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/divideData', methods=['POST'])
@jwt_required()
@active_required
def divideData(): 
    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "id" in data:
        purchase_order_id = data['id']
    else:
        return jsonify({"msg":"id 不能为空！"}),401
    
    if "number" in data:
        number = data['number']
    else:
        return jsonify({"msg":"拆分数量不能为空！"}),401
    
    purchase_order = PurchaseOrder.query.filter_by(id = purchase_order_id).first()

    if not purchase_order:
        return {"msg":f"找不到id为{purchase_order_id}的产品！"},401
    
    if not purchase_order.status == PurchaseStatus.waitForPurchase:
        return {"msg":f"只能拆分待采购采购单，当前采购单状态为：{purchase_order.status}，无法拆分！"},400

    # 权限校验
    if not current_user.is_admin:
        if not (current_user.is_department_admin and purchase_order.department_id == current_user.department_id):
            if not (any(role.id == "2" for role in current_user.roles) and purchase_order.department_id == current_user.department_id):
                return {"msg":"当前账户无操作权限！"},400
            
    
    change_purchase_products_ids = []

    purchase_products = purchase_order.purchase_products

    if int(number) > len(purchase_products):
        return {"msg":f"拆分数量不能大于被拆分采购单总商品数量！"},400
    
    new_purchase_order = PurchaseOrder()
    new_purchase_order.id = str(uuid.uuid1())
    new_purchase_order.purchase_platform = purchase_order.purchase_platform
    new_purchase_order.status = PurchaseStatus.waitForPurchase
    new_purchase_order.system_product_id = purchase_order.id
    new_purchase_order.department_id = purchase_order.department_id
    new_purchase_order.system_product_id = purchase_order.system_product_id

    db.session.add(new_purchase_order)
    
    for index in range(int(number)):
        purchase_product = purchase_products[index]
        change_purchase_products_ids.append(purchase_product.id)
        purchase_product.purchase_order_id = new_purchase_order.id

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseOrder,describe=f"操作人:{current_user.username}, 操作:采购单拆单 id:{purchase_order.id} 拆出{number}, 生成新采购单{new_purchase_order.id}, 采购商品id：{change_purchase_products_ids} 更换采购单 {purchase_order.id} => {new_purchase_order.id}")
        return {"msg":"采购订单拆单成功！"}, 200  
    except Exception as e:
        return {"msg":"采购订单拆单失败！"}, 400
    
# 采购单作废
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/cancleThePurchaseOrder', methods=['POST'])
@jwt_required()
@active_required
def cancleThePurchaseOrder(): 

    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if not current_user.is_admin:
        if not (current_user.is_department_admin):
            if not any(role.id == "2" for role in current_user.roles):
                return {"msg":"当前账户无操作权限！"},400
        
    data = request.get_json()

    if "purchase_order_id" in data:
        purchase_order_id = data['purchase_order_id']
    else:
        return jsonify({"msg":"purchase_order_id 不能为空！"}),401
    
    purchase_order = PurchaseOrder.query.filter_by(id = purchase_order_id).first()

    if not purchase_order:
        return {"msg":"找不到对应采购订单！"},401

    if not current_user.is_admin:
        if not purchase_order.department_id == current_user.department_id:
            return jsonify({"msg": f"当前账号无权作废该采购单！"}),400
    
    if purchase_order.status == PurchaseStatus.waitForPurchase:
        purchase_order.status = PurchaseStatus.cancelled
        # 删掉采购单关联的采购商品
        PurchaseProduct.query.filter_by(purchase_order_id=purchase_order_id).delete()

    elif purchase_order.status == PurchaseStatus.finished:
        # 更改采购单状态
        purchase_order.status = PurchaseStatus.cancelled
    else:
        return jsonify({
            "msg":"当前代购单状态，无法作废！"
        }), 400
    
    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:采购单作废, id:{purchase_order.id}")
        return jsonify({
            "msg":"采购订单作废成功！"
        }), 200
    except Exception as e:
        return {"msg":"采购订单作废失败！"}, 400

# 采购单查询 根据国内运单号 查询包含这个运单号的所有采购单
# 系统管理员、部门管理员 和 打包 可操作
@purchase_order_list.route('/getThePostingOfPurchaseOrder', methods=['POST'])
@jwt_required()
@active_required
def getThePostingOfPurchaseOrder():

    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if not current_user.is_admin:
        if not (current_user.is_department_admin):
            if not any(role.id == "3" for role in current_user.roles):
                return {"msg":"当前账户无操作权限！"},400
        
    data = request.get_json()

    if "posting_number" in data:
        posting_number = data['posting_number']
    else:
        return jsonify({"msg":"入库 快递运单号 不能为空！"}),401
    

    purchase_orders = PurchaseOrder.query.filter(PurchaseOrder.posting_numbers.like(f'%{posting_number}%')).filter(PurchaseOrder.status == PurchaseStatus.inTransit).all()

    if not purchase_orders:
        return jsonify({"msg":f"无对应 快递运单号 {posting_number} 状态为运输中的采购单！请检查后重试！"}),401

    if not current_user.is_admin:
        for purchase_order in purchase_orders:
            if not purchase_order.department_id == current_user.department_id:
                return jsonify({"msg": f"采购单{purchase_order.id} 不在当前账号部门！"}),400

    try:
        db.session.commit()
        
        results = {
            "data" :[
            {

                "id": result.id,
                "purchase_id": result.purchase_id,
                "price": result.price,
                "shipping_fee": result.shipping_fee,
                "posting_numbers": result.posting_numbers,
                "logistics_status": result.logistics_status,
                "purchase_platform": result.purchase_platform,
                "status": result.status,
                "is_error": result.is_error,
                "error_words": result.error_words,
                "platform_status": result.platform_status,
                "fill_purchase_id_time": result.fill_purchase_id_time,
                "packer_msg":result.packer_msg,
                "back_fee":result.back_fee,
                "mark": result.mark,

                "wait_for_purchase_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                "in_basket_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                "in_transit_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                "stock_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                "out_stock_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                "loss_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.loss]),
                
                "system_product": {
                    "id": result.system_product.id,
                    "primary_image": result.system_product.primary_image,
                    "system_sku": result.system_product.system_sku,
                    "reference_weight": result.system_product.reference_weight,
                    "reference_cost": result.system_product.reference_cost,
                    "purchase_link": result.system_product.purchase_link,
                    "supplier_name": result.system_product.supplier_name,
                    "purchase_platform": result.system_product.purchase_platform,
                    "create_time": result.system_product.create_time,
                    "wait_for_purchase_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                    "in_basket_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                    "in_transit_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                    "stock_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                    "out_stock_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                    "loss_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.loss]),
                } if  result.system_product  else None,

                "purchase_products":[
                    {
                        "id": purchase_product.id,
                        "price": purchase_product.price,
                        "stock_in_date": purchase_product.stock_in_date,
                        "sku": purchase_product.sku,
                        "type": purchase_product.type,
                        "status": purchase_product.status,
                        "mark": purchase_product.mark,
                        "purchase_order_id": purchase_product.purchase_order_id,
                        "ozon_order_id": purchase_product.ozon_order_id,
                        "system_product_id": purchase_product.system_product_id,
                        "create_time": purchase_product.create_time,
                        "modify_time": purchase_product.modify_time,
                    }
                    for purchase_product in result.purchase_products
                ]
            } 
            for result in purchase_orders],
            "count":len(purchase_orders)
        }
        
        return jsonify({
            "msg":f"快递 运单号:{posting_number} 查询成功！",
            "data":results
        }), 200 
    except Exception as e:
        return {"msg":f"快递 运单号:{posting_number} 查询失败！"}, 400

# 入库包含此系统中产品的 采购单 并填写到货数量
# 返回所有待打印的 打印凭条pdf（采购商品id sku type）
# 系统管理员、部门管理员 和 打包 可操作
@purchase_order_list.route('/signTheSystemProductsOfPurchaseOrder', methods=['POST'])
@jwt_required()
@active_required
def signTheSystemProductsOfPurchaseOrder():

    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if not current_user.is_admin:
        if not (current_user.is_department_admin):
            if not any(role.id == "3" for role in current_user.roles):
                return {"msg":"当前账户无操作权限！"},400
        
    data = request.get_json()

    if "purchase_order_msgs" in data:
        purchase_order_msgs = data['purchase_order_msgs']
    else:
        return jsonify({"msg":"采购单信息 不能为空！"}),401
    
    if "posting_number" in data:
        posting_number = data['posting_number']
    else:
        return jsonify({"msg":"国内运单号信息 不能为空！"}),401
    

    products = []

    for purchase_order_msg in purchase_order_msgs:

        purchase_order_id = purchase_order_msg["id"]
        quantity = purchase_order_msg["quantity"]
        msg = purchase_order_msg["msg"]

        purchase_order = PurchaseOrder.query.filter_by(id = purchase_order_id).first()

        if not purchase_order:
            return jsonify({"msg":f"无id为{purchase_order_id} 的采购单！"}),401

        if not current_user.is_admin:
            if not purchase_order.department_id == current_user.department_id:
                return jsonify({"msg": f"采购单{purchase_order.id} 不在当前账号部门！"}),400
            
        if not purchase_order.status == PurchaseStatus.inTransit:
            return jsonify({"msg":f"采购订单{purchase_order.id}的状态为{purchase_order.status}，无法签收，请检查采购订单状态！"}),400
        
        if msg:
            purchase_order.packer_msg = msg
            purchase_order.packer_msg_date = datetime.now()
        
        purchase_products_wait_for_sign = [item for item in purchase_order.purchase_products if item.status == PurchaseProductStatus.in_transit]
        purchase_products_wait_for_sign_numbers = len(purchase_products_wait_for_sign)

        if int(quantity) > int(purchase_products_wait_for_sign_numbers):
            return jsonify({"msg": f"采购单{purchase_order.id} 剩余可入库数量{int(purchase_products_wait_for_sign_numbers)}小于当前要入库的产品数量{quantity}！"}),400

        elif int(quantity) < int(purchase_products_wait_for_sign_numbers):
            
            # 采购订单对应的 快递国内运单号 入库
            posting_list = json.loads(purchase_order.posting_numbers)
            
            findFlag = False
            
            for entry in posting_list:
                if entry['value'] == posting_number:
                    findFlag = True
                    if entry['signed'] == '已入库':
                        return jsonify({"msg": f"运单号 {posting_number} 已入库，请勿重复入库！ "}),400
                    entry['signed'] = '已入库'
            purchase_order.posting_numbers = json.dumps(posting_list,ensure_ascii=False)
            
            if not findFlag:
                return jsonify({"msg": f"运单号 {posting_number} 不存在于采购单 {purchase_order.id}，请检查后重试！ "}),400

            # 给系统内商品依次入库
            
            for index in range(int(quantity)):
                purchase_product_wait_for_sign = purchase_products_wait_for_sign[index]
                purchase_product_wait_for_sign.status = PurchaseProductStatus.in_basket
                purchase_product_wait_for_sign.stock_in_date = datetime.now()
                purchase_product_wait_for_sign.stock_in_id = current_user.id

                products.append(
                    {
                        'id': purchase_product_wait_for_sign.id,
                        'sku': purchase_product_wait_for_sign.sku,
                        'price': purchase_product_wait_for_sign.price,
                        'product_type': purchase_product_wait_for_sign.type,
                        'stock_in_date': purchase_product_wait_for_sign.stock_in_date
                    }
                )

            if products:
                pdf_byte_arr = generate_qrcodes_pdf(products)

            # 判断采购单是否异常（如果运单号全部都签收了但是入库的产品的数量小于应该有的数量 即为快递少了）
            if all(item["signed"] == "已入库" for item in posting_list):
                purchase_order.status = PurchaseStatus.error
                # 剩余的绑定商品状态改为丢失
                for item in purchase_products_wait_for_sign:
                    if item.status == PurchaseProductStatus.in_transit:
                        item.status = PurchaseProductStatus.loss
                        item.ozon_order_id = None
                        item.loss_date = datetime.now()
                        item.mark = "绑定的国内运单全部入库，但是产品数量少了"
                        if msg:
                            item.mark += f"采购留言：{msg}"
        
        elif int(quantity) == int(purchase_products_wait_for_sign_numbers):

            # 采购订单对应的 快递国内运单号 入库
            posting_list = json.loads(purchase_order.posting_numbers)
            for entry in posting_list:
                if entry['value'] == posting_number:
                    if entry['signed'] == '已入库':
                        return jsonify({"msg": f"运单号 {posting_number} 已入库，请勿重复入库！ "}),400
                    entry['signed'] = '已入库'
            purchase_order.posting_numbers = json.dumps(posting_list,ensure_ascii=False)

            # 采购单已完成
            purchase_order.status = PurchaseStatus.finished

            # 给系统内商品依次入库
            for index in range(int(quantity)):
                purchase_product_wait_for_sign = purchase_products_wait_for_sign[index]
                purchase_product_wait_for_sign.status = PurchaseProductStatus.in_basket
                purchase_product_wait_for_sign.stock_in_date = datetime.now()
                purchase_product_wait_for_sign.stock_in_id = current_user.id

                products.append(
                    {
                        'id': purchase_product_wait_for_sign.id,
                        'sku': purchase_product_wait_for_sign.sku,
                        'price': purchase_product_wait_for_sign.price,
                        'product_type': purchase_product_wait_for_sign.type,
                        'stock_in_date': purchase_product_wait_for_sign.stock_in_date
                    }
                )

    if products:
        pdf_byte_arr = generate_qrcodes_pdf(products)

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:采购订单{purchase_order_msgs}签收成功！")
        return jsonify({
            "msg":f"采购订单{purchase_order_msgs}签收成功！",
            "data": base64.b64encode(pdf_byte_arr).decode('utf-8') if products else None
        }), 200
    except Exception as e:
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:采购订单{purchase_order_msgs}签收失败！, 报错：{e}")
        return {"msg":f"采购订单{purchase_order_msgs} 签收失败！"}, 400

#获取所有的 状态为 运输中 的采购订单
#系统管理员、部门管理员 和 打包 可操作
@purchase_order_list.route('/getInTransitPurchaseOrderData', methods=['GET'])
@jwt_required()
@active_required
def getInTransitPurchaseOrderData():

    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:
        
        start = int(request.args.get('start', 0))
        limit = int(request.args.get('limit', 10))
        keyWord = str(request.args.get('keyWord', None))

        if keyWord:
            columns = [column.name for column in PurchaseOrder.__table__.columns ]
            filters = [getattr(PurchaseOrder, col).like(f'%{keyWord}%') for col in columns]
            query = PurchaseOrder.query.filter(or_(*filters))
        else:
            query = PurchaseOrder.query

        if current_user.is_admin:
            pass
        elif current_user.department and (current_user.is_department_admin or any(role.id == "3" for role in current_user.roles)):
            query = query.filter_by(department_id = current_user.department_id)
        else:
            return {"msg":"当前账户无操作权限！"},400

        query = query.filter_by(status=PurchaseStatus.inTransit)

        results = query.order_by(PurchaseOrder.create_time).offset(start).limit(limit).all()
        count = query.order_by(PurchaseOrder.create_time).count()
            
        results = {
            "data" :[
            {

                "id": result.id,
                "purchase_id": result.purchase_id,
                "price": result.price,
                "shipping_fee": result.shipping_fee,
                "posting_numbers": result.posting_numbers,
                "logistics_status": result.logistics_status,
                "purchase_platform": result.purchase_platform,
                "status": result.status,
                "is_error": result.is_error,
                "error_words": result.error_words,
                "platform_status": result.platform_status,
                "fill_purchase_id_time": result.fill_purchase_id_time,
                "packer_msg":result.packer_msg,
                "back_fee":result.back_fee,
                "mark": result.mark,

                "wait_for_purchase_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                "in_basket_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                "in_transit_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                "stock_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                "out_stock_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                "loss_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.loss]),
                
                "system_product": {
                    "id": result.system_product.id,
                    "primary_image": result.system_product.primary_image,
                    "system_sku": result.system_product.system_sku,
                    "reference_weight": result.system_product.reference_weight,
                    "reference_cost": result.system_product.reference_cost,
                    "purchase_link": result.system_product.purchase_link,
                    "supplier_name": result.system_product.supplier_name,
                    "purchase_platform": result.system_product.purchase_platform,
                    "create_time": result.system_product.create_time,
                    "wait_for_purchase_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                    "in_basket_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                    "in_transit_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                    "stock_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                    "out_stock_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                    "loss_quantity": len([item for item in result.system_product.purchase_products if item.status == PurchaseProductStatus.loss]),
                } if  result.system_product  else None,

                "purchase_products":[
                    {
                        "id": purchase_product.id,
                        "price": purchase_product.price,
                        "stock_in_date": purchase_product.stock_in_date,
                        "sku": purchase_product.sku,
                        "type": purchase_product.type,
                        "status": purchase_product.status,
                        "mark": purchase_product.mark,
                        "purchase_order_id": purchase_product.purchase_order_id,
                        "ozon_order_id": purchase_product.ozon_order_id,
                        "system_product_id": purchase_product.system_product_id,
                        "create_time": purchase_product.create_time,
                        "modify_time": purchase_product.modify_time,
                    }
                    for purchase_product in result.purchase_products
                ]
            } 
            for result in results],
            "count":count
        }

        return jsonify({
            "msg":"查询成功！",
            "data":results
        }), 200 
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 400 

# 一键更新1688商品
# 全局变量
updataRunning = False

updataMsg = {
    "msg": "", 
    "updataProgress": {
        "nowUpdata": 0, 
        "allCount": 0, 
    }
}

# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/updatePurchaseOrdersIn1688WithAPI', methods=['POST'])
@jwt_required()
@active_required
def updatePurchaseOrdersIn1688WithAPI():

    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:

        if current_user.is_admin:
            pass
        elif current_user.department and (current_user.is_department_admin or any(role.id == "2" for role in current_user.roles)):
            pass
        else:
            return {"msg":"当前账户无操作权限！"},400
        
        global updataRunning

        if not updataRunning:
            thread = threading.Thread(target=updataDataThread, args=(current_app._get_current_object(),))
            thread.start()
            operate_log_writer_func(operateType=OperateType.ozonOrder,describe="开始更新1688订单!")
            return jsonify({"msg": "1688订单更新已启动!"}), 200
        else:
            return jsonify({"msg": f"1688订单更新正在进行中... 进程:{updataMsg['updataProgress']['nowUpdata']}/{updataMsg['updataProgress']['allCount']} msg:{updataMsg['msg']}"}), 200
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 400 

# 更新1688数据子线程
def updataDataThread(app):
    global updataRunning
    global updataMsg

    with app.app_context():
        try:
            # 数据初始化
            updataMsg = {
                "msg": "", 
                "updataProgress": {
                    "nowUpdata": 0, 
                    "allCount": 0, 
                }
            }
            updataRunning = True

            # 获取1688 运输中/待付款 采购订单
            purchase_orders_query = PurchaseOrder.query.filter_by(
                purchase_platform="1688"
            ).filter(
                or_(
                    PurchaseOrder.status == PurchaseStatus.inTransit,
                    PurchaseOrder.status == PurchaseStatus.waitForPay
                )
            )
            
            # 获取更新订单的日期
            now = datetime.now()
            half_month_ago = now - timedelta(days=15)

            today_str = now.replace(hour=23, minute=59, second=59, microsecond=0).strftime('%Y%m%d%H%M%S%f')[:-3] + '+0800'
            half_month_ago_str = half_month_ago.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y%m%d%H%M%S%f')[:-3] + '+0800'
            
            # 更新订单
            Record = get1688OrderList(half_month_ago_str,today_str,1,1)["data"]
            
            if Record:
                totalRecord = Record["totalRecord"]
                pages = math.ceil(int(totalRecord)/50)
                updataMsg["updataProgress"]["allCount"] = totalRecord

                for page in range(pages):

                    result = get1688OrderList(half_month_ago_str,today_str,page+1,50)["data"]

                    orders = result["result"]
                    
                    if orders:
                        for order in orders:
                            updataMsg["updataProgress"]["nowUpdata"] += 1

                            purchase_id = order["baseInfo"]["id"]

                            # if purchase_id == "2405394195001558276" or purchase_id == "2405806754785558276":
                            #     print(order)
                            #     a = input()
                                
                            shipping_fee = order["baseInfo"]["shippingFee"]

                            product_items = order["productItems"]

                            for product in product_items:
                                # 商品总价
                                price = product["itemAmount"]
                                # 商品单价
                                single_price = product["price"]
                                product_id = product["productID"]
                                # 商品id
                                sku_id = ""
                                if "skuID" in product:
                                    sku_id = product["skuID"]
                                # 商品状态
                                status_str = product["statusStr"]
                                
                                if sku_id:
                                    purchase_order = purchase_orders_query.filter_by(
                                        purchase_id = purchase_id
                                    ).join(
                                        PurchaseOrder.system_product
                                    ).filter(
                                        SystemProduct.skuId_1688 == sku_id
                                    ).first()
                                else:
                                    purchase_order = purchase_orders_query.filter_by(
                                        purchase_id = purchase_id
                                    ).join(
                                        PurchaseOrder.system_product
                                    ).filter(
                                        SystemProduct.productId_1688 == product_id
                                    ).first()
                                
                                if purchase_order:
                                    purchase_order.price = price
                                    purchase_order.platform_status = status_str
                                    purchase_order.shipping_fee = shipping_fee
                                    
                                    for purchase_product in purchase_order.purchase_products:
                                        if purchase_product.status != PurchaseProductStatus.loss:
                                            purchase_product.price = single_price

                                    if purchase_order.status == PurchaseStatus.waitForPay:
                                          
                                        if status_str == "交易取消" or status_str == "交易终止":
                                            purchase_order.status = PurchaseStatus.cancelled
                                            # 删掉关联的采购商品
                                            db.session.query(PurchaseProduct).filter(
                                                PurchaseProduct.purchase_order_id == purchase_order.id
                                            ).delete()
                                            refundStatus = get1688OrderDetail(purchase_order.purchase_id)["refundStatus"]
                                            if refundStatus:
                                                purchase_product.logistics_status = refundStatus

                                        elif status_str == "等待买家付款":
                                            pass
                                        elif status_str == "等待买家收货":
                                            purchase_order.status = PurchaseStatus.inTransit
                                            # 全部待采购 采购产品 状态变更为 在途中
                                            for purchase_product in purchase_order.purchase_products:
                                                if purchase_product.status == PurchaseProductStatus.wait_purchase:
                                                    purchase_product.status = PurchaseProductStatus.in_transit
                                            # 更新一下物流单号
                                            logisticsBillNos = get1688OrderDetail(purchase_order.purchase_id)["data"]
                                            if logisticsBillNos:
                                                purchase_order.posting_numbers = json.dumps([{"value":item,"signed":"未入库"} for item in logisticsBillNos])
                                        else:
                                            
                                            purchase_order.status = PurchaseStatus.inTransit
                                            # 全部待采购 采购产品 状态变更为 在途中
                                            for purchase_product in purchase_order.purchase_products:
                                                if purchase_product.status == PurchaseProductStatus.wait_purchase:
                                                    purchase_product.status = PurchaseProductStatus.in_transit

                                    elif purchase_order.status == PurchaseStatus.inTransit:
                                        
                                        if status_str == "交易取消" or status_str == "交易终止":
                                            purchase_order.status = PurchaseStatus.cancelled
                                            # 删掉关联的采购商品
                                            db.session.query(PurchaseProduct).filter(
                                                PurchaseProduct.purchase_order_id == purchase_order.id
                                            ).delete()
                                        elif status_str == "等待买家收货" or status_str == "等待买家签收":
                                            if purchase_order.posting_numbers:
                                                posting_number = json.loads(purchase_order.posting_numbers)
                                                if not posting_number:
                                                    # 更新一下物流单号
                                                    logisticsBillNos = get1688OrderDetail(purchase_order.purchase_id)["data"]
                                                    if logisticsBillNos:
                                                        purchase_order.posting_numbers = json.dumps([{"value":item,"signed":"未入库"} for item in logisticsBillNos], ensure_ascii=False)
                                            else:
                                                # 更新一下物流单号
                                                logisticsBillNos = get1688OrderDetail(purchase_order.purchase_id)["data"]
                                                if logisticsBillNos:
                                                    purchase_order.posting_numbers = json.dumps([{"value":item,"signed":"未入库"} for item in logisticsBillNos], ensure_ascii=False)
                        try:
                            db.session.commit()
                        except Exception as e:
                            updataRunning = False 
                            operate_log_writer_func(operateType=OperateType.purchaseOrder,describe=f"更新1688订单失败!,错误信息”：{e}",isSystem=True)
                            updataMsg["msg"] = f"更新1688订单失败!,错误信息”：{e}"

            updataMsg["msg"] = f'更新1688订单成功！共更新商品数据{updataMsg["updataProgress"]["nowUpdata"]}'
            operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f'操作:更新1688订单成功！共更新商品数据{updataMsg["updataProgress"]["nowUpdata"]}',isSystem=True)
            updataRunning = False 
        except Exception as e:
            stack_trace = traceback.format_exc()
            updataRunning = False 
            operate_log_writer_func(operateType=OperateType.purchaseOrder,describe=f"更新1688订单失败!,错误信息”：{stack_trace}",isSystem=True)
            updataMsg["msg"] = f"更新1688订单失败!,错误信息”：{stack_trace}"


# 一键采购同一供应商的1688商品
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/buyPurchaseProductIn1688WithAPI_flow', methods=['POST'])
@jwt_required()
@active_required
def buyPurchaseProductIn1688WithAPI_flow():


    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:
        if not current_user.is_admin:
            if not (current_user.is_department_admin):
                if not any(role.id == "2" for role in current_user.roles):
                    return {"msg":"当前账户无操作权限！"},400
            
        data = request.get_json()

        if "purchase_order_msgs" in data:
            purchase_order_msgs = data['purchase_order_msgs']
        else:
            return jsonify({"msg":"采购单信息 不能为空！"}),401
        
        supplier_name = ""
        
        # 下单的产品列表
        cargoParamList = []

        purchase_order_list = []

        ids = []

        for purchase_order_msg in purchase_order_msgs:

            purchase_order_id = purchase_order_msg["id"]
            purchase_order = PurchaseOrder.query.filter_by(id = purchase_order_id).first()

            if not purchase_order:
                return jsonify({"msg":f"无id为{purchase_order_id} 的采购单！"}),401

            if not current_user.is_admin:
                if not purchase_order.department_id == current_user.department_id:
                    return jsonify({"msg": f"采购单{purchase_order.id} 不在当前账号部门！"}),400
            
            if not purchase_order.purchase_platform == "1688":
                return jsonify({"msg": f"采购单{purchase_order.id} 不是1688平台！无法采购！"}),400
            
            if not  purchase_order.system_product.productId_1688:
                return jsonify({"msg": f"采购单{purchase_order.id} 未绑定1688productId，无法采购！"}),400

            if not purchase_order.status == PurchaseStatus.waitForPurchase:
                return jsonify({"msg":f"采购订单{purchase_order.id}的状态为{purchase_order.status}，无法采购，请检查采购订单状态！"}),400
            
            if supplier_name:
                if not purchase_order.system_product.supplier_name == supplier_name:
                    return jsonify({"msg":f"采购订单对应货品供应商不一致！请检查后重试！"}),400
            else:
                supplier_name = purchase_order.system_product.supplier_name

            purchase_products_wait_for_purchase = [item for item in purchase_order.purchase_products if item.status == PurchaseProductStatus.wait_purchase]
            purchase_products_wait_for_purchase_numbers = len(purchase_products_wait_for_purchase)

            purchase_order_list.append(purchase_order)

            if purchase_order.system_product.skuId_1688 == "无":
                ids.append(purchase_order.system_product.id)
                cargoParamList.append(
                    {
                        "offerId": purchase_order.system_product.productId_1688,
                        "quantity": str(purchase_products_wait_for_purchase_numbers)
                    }
                )
            else:
                ids.append(purchase_order.system_product.id)
                cargoParamList.append(
                    {
                        "offerId": purchase_order.system_product.productId_1688,
                        "specId": purchase_order.system_product.specId_1688,
                        "quantity": str(purchase_products_wait_for_purchase_numbers)
                    }
                )

        data = create1688OrderPreview(cargoParamList)
        flow = data["data"]["orderPreviewResuslt"][0]["flowFlag"] if data["data"] else None
        
        if flow:
            products = []
            amount = 0
            
            sumPayment = data["data"]["orderPreviewResuslt"][0]["sumPayment"]
            sumCarriage = data["data"]["orderPreviewResuslt"][0]["sumCarriage"]
            sumPaymentNoCarriage = data["data"]["orderPreviewResuslt"][0]["sumPaymentNoCarriage"]


            for product in data["data"]["orderPreviewResuslt"][0]["cargoList"]:
                
                if "skuId" in  product:
                    skuId_1688 = product["skuId"]
                    productId_1688 = product["offerId"]
                    specId_1688 =  product["specId"]

                    system_product = SystemProduct.query.filter_by(skuId_1688 = skuId_1688).filter(SystemProduct.id.in_(ids)).first()

                    for item in cargoParamList:
                        if "specId" in item:
                            if item["specId"] == specId_1688:
                                quantity = item["quantity"]

                else:
                    productId_1688 = product["offerId"]
                    system_product = SystemProduct.query.filter_by(productId_1688 = productId_1688).filter(SystemProduct.id.in_(ids)).first()

                    for item in cargoParamList:
                        if item["offerId"] == productId_1688:
                            quantity = item["quantity"]
                

                if system_product:
                    amount += product["amount"]

                    products.append(
                        {
                            "id": system_product.id,
                            "primary_image": system_product.primary_image,
                            "system_sku": system_product.system_sku,
                            "reference_weight": system_product.reference_weight,
                            "reference_cost": system_product.reference_cost,
                            "purchase_link": system_product.purchase_link,
                            "purchase_platform": system_product.purchase_platform,
                            "supplier_name": system_product.supplier_name,
                            "finalUnitPrice": product["finalUnitPrice"],
                            "amount": product["amount"],
                            "quantity": quantity if quantity else None
                        }
                    )
            return {
                "msg": "获取订单预览数据成功！",
                "data": {
                    "products":products,
                    "flow":flow,
                    "purchase_order_msgs":purchase_order_msgs,
                    "amount": amount,
                    "sumPayment": sumPayment,
                    "sumCarriage": sumCarriage,
                    "sumPaymentNoCarriage": sumPaymentNoCarriage
                }
            },200
            
        else:
            return jsonify({"msg":f"获取订单前预览数据（获取flow）失败！{data['msg']}"}),400
            
    else:
        return jsonify({
                    "msg":"未找到对应用户！",
                }), 400 

# 一键采购同一供应商的1688商品
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/buyPurchaseProductIn1688WithAPI_buy', methods=['POST'])
@jwt_required()
@active_required
def buyPurchaseProductIn1688WithAPI_buy():

    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:
        if not current_user.is_admin:
            if not (current_user.is_department_admin):
                if not any(role.id == "2" for role in current_user.roles):
                    return {"msg":"当前账户无操作权限！"},400
            
        data = request.get_json()

        if "purchase_order_msgs" in data:
            purchase_order_msgs = data['purchase_order_msgs']
        else:
            return jsonify({"msg":"采购单信息 不能为空！"}),401
        
        if "flow" in data:
            flow = data['flow']
        else:
            return jsonify({"msg":"flow 不能为空！"}),401
        
        supplier_name = ""
        
        # 下单的产品列表
        cargoParamList = []

        purchase_order_list = []

        for purchase_order_msg in purchase_order_msgs:

            purchase_order_id = purchase_order_msg["id"]
            purchase_order = PurchaseOrder.query.filter_by(id = purchase_order_id).first()

            if not purchase_order:
                return jsonify({"msg":f"无id为{purchase_order_id} 的采购单！"}),401

            if not current_user.is_admin:
                if not purchase_order.department_id == current_user.department_id:
                    return jsonify({"msg": f"采购单{purchase_order.id} 不在当前账号部门！"}),400
            
            if not purchase_order.purchase_platform == "1688":
                return jsonify({"msg": f"采购单{purchase_order.id} 不是1688平台！无法采购！"}),400
            
            if not  purchase_order.system_product.productId_1688:
                return jsonify({"msg": f"采购单{purchase_order.id} 未绑定1688productId，无法采购！"}),400

            if not purchase_order.status == PurchaseStatus.waitForPurchase:
                return jsonify({"msg":f"采购订单{purchase_order.id}的状态为{purchase_order.status}，无法采购，请检查采购订单状态！"}),400
            
            if supplier_name:
                if not purchase_order.system_product.supplier_name == supplier_name:
                    return jsonify({"msg":f"采购订单对应货品供应商不一致！请检查后重试！"}),400
            else:
                supplier_name = purchase_order.system_product.supplier_name

            purchase_products_wait_for_purchase = [item for item in purchase_order.purchase_products if item.status == PurchaseProductStatus.wait_purchase]
            purchase_products_wait_for_purchase_numbers = len(purchase_products_wait_for_purchase)
            
            # 更改采购订单采购状态
            purchase_order.status = PurchaseStatus.waitForPay

            purchase_order_list.append(purchase_order)

            if purchase_order.system_product.skuId_1688 == "无":
                cargoParamList.append(
                    {
                        "offerId": purchase_order.system_product.productId_1688,
                        "quantity": str(purchase_products_wait_for_purchase_numbers)
                    }
                )
            else:
                cargoParamList.append(
                    {
                        "offerId": purchase_order.system_product.productId_1688,
                        "specId": purchase_order.system_product.specId_1688,
                        "quantity": str(purchase_products_wait_for_purchase_numbers)
                    }
                )

        if flow:
            result = create1688Order(flow,cargoParamList)

            if result["data"]:
                purchase_id = result["data"]["result"]["orderId"]

                for purchase_order in purchase_order_list:
                    purchase_order.purchase_id = purchase_id
                    purchase_order.purchaser_id = current_user.id
                    # 新增填写运单号的时间
                    purchase_order.fill_purchase_id_time = datetime.now()


                db.session.commit()
                operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:自动下单1688订单{cargoParamList}成功！")
                return jsonify({"msg":f"1688自动下单成功！"}),200
            else:
                return jsonify({"msg":f"获取订单前预览数据（获取flow）失败！"}),400
        else:
            return jsonify({"msg":f"获取订单前预览数据（获取flow）失败！"}),400
            
    else:
        return jsonify({
                    "msg":"未找到对应用户！",
                }), 400 

# 更新pdd订单数据
@purchase_order_list.route('/updatePurchaseOrdersInPddWithData', methods=['POST'])
def updatePurchaseOrdersInPddWithData():
    try:
        data = request.get_json()

        if "orders" in data:
            orders = data['orders']
        else:
            return jsonify({"msg":"订单信息不能为空！"}),401


        # 获取pdd 运输中 采购订单
        purchase_orders_query = PurchaseOrder.query.filter_by(
            purchase_platform="pdd"
        ).filter(
            or_(
                PurchaseOrder.status == PurchaseStatus.inTransit
            )
        )
        
        for order in orders:

            purchase_id = order["order_sn"]
            status_str = order["order_status_prompt"]
            price = float(order["order_amount"])
            posting_numbers = order["tracking_number"]
            extra_info = order["extra_info"]
            goods_number = int(order["goods_number"])

            purchase_order = purchase_orders_query.filter_by(purchase_id = purchase_id).first()

            if not purchase_order:
                continue
            
            purchase_order.price = price/100
            purchase_order.logistics_status = extra_info
            purchase_order.platform_status = status_str

            for purchase_product in purchase_order.purchase_products:
                if purchase_product.status != PurchaseProductStatus.loss:
                    purchase_product.price = order["order_amount"]/goods_number/100
                        
            if (
                status_str == "未发货，退款成功" 
                or status_str == "已发货，退货待用户寄出" 
                or status_str == "交易已取消" 
                or status_str == "已发货，退款成功" 
                or status_str == "退货退款，待取件" 
                or status_str == "已签收，退货待用户寄出" 
                or status_str == "已签收，退款成功" 
            ):
                purchase_order.status = PurchaseStatus.cancelled
                # 删掉关联的采购商品
                db.session.query(PurchaseProduct).filter(
                    PurchaseProduct.purchase_order_id == purchase_order.id
                ).delete()
            elif status_str == "待收货":
                if purchase_order.posting_numbers:
                    posting_number = json.loads(purchase_order.posting_numbers)
                    if not posting_number:
                        # 更新一下物流单号
                        if posting_numbers:
                            purchase_order.posting_numbers = json.dumps([{"value":item["tracking_number"],"signed":"未入库"} for item in posting_numbers], ensure_ascii=False)
                else:
                    # 更新一下物流单号
                    if posting_numbers:
                        purchase_order.posting_numbers = json.dumps([{"value":item["tracking_number"],"signed":"未入库"} for item in posting_numbers], ensure_ascii=False)
        try:
            db.session.commit()
        except Exception as e:
            operate_log_writer_func(operateType=OperateType.purchaseOrder,describe=f"更新pdd订单失败!,错误信息”：{e}",isSystem=True)
            return jsonify({"msg":f"更新pdd订单失败!,错误信息”：{e}"}),400
            
        return jsonify({"msg":f'更新pdd订单成功！本次更新数据{orders}'}),200
    
    except Exception as e:
        stack_trace = traceback.format_exc()
        operate_log_writer_func(operateType=OperateType.purchaseOrder,describe=f"更新pdd订单失败!,错误信息”：{stack_trace}",isSystem=True)
        return jsonify({"msg":f"更新pdd订单失败!,错误信息”：{stack_trace}"}),400

# 打印线下的待采购商品清单
# 系统管理员、部门管理员 和 采购可操作
@purchase_order_list.route('/getUnderLinePurchaseProductsToExcel', methods=['GET'])
@jwt_required()
@active_required
def getUnderLinePurchaseProductsToExcel():
    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:

        query = PurchaseOrder.query.filter_by(
            status = PurchaseStatus.waitForPurchase
        ).filter_by(
            purchase_platform = "线下"
        )
     
        if current_user.is_admin:
            pass
        elif current_user.department and (current_user.is_department_admin or any(role.id == "2" for role in current_user.roles)):
            query = query.filter_by(department_id = current_user.department_id)
        else:
            return {"msg":"当前账户无操作权限！"},400
        
        purchase_order_list = query.all()

        data = {}

        for purchase_order in purchase_order_list:

            for purchase_product in purchase_order.purchase_products:

                if purchase_product.status == PurchaseProductStatus.wait_purchase:
                    
                    if purchase_product.system_product_id in data:
                        data[purchase_product.system_product_id]["quantity"] += 1
                    else:
                        data[purchase_product.system_product_id] = {"quantity":1,"sku":purchase_product.system_product.system_sku,"pic":purchase_product.system_product.primary_image}

        data = [{"pic":value["pic"],"sku":value["sku"],"quantity":value["quantity"]} for key,value in data.items()]

        output = io.BytesIO()

        # 获取全部的图片io
        def getPicIO(item):
            try:
                timeout = 10
                response = requests.get(item["pic"] ,timeout=timeout)
                if response.status_code == 200:
                    # print(f"order:{order['货件号']} 运行成功！")
                    item["pic"] = BytesIO(response.content)
                else:
                    item["pic"] = None
            except:
                item["pic"] = None


        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(getPicIO, item) for item in data]
            concurrent.futures.wait(futures)
            
            # 创建DataFrame
            df = pd.DataFrame(data)

            # 创建一个新的Excel文件
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet()

            # 标题
            for col_idx, col_name in enumerate(df.columns):
                worksheet.write(0, col_idx, col_name)

            # 写数据
            for row_idx, row_data in enumerate(df.values):
                # row_data 形如 (BytesIO 或 None, "SKU", 1)
                for col_idx, cell_value in enumerate(row_data):
                    # 如果是图片列
                    if col_idx == 0:
                        img_data = cell_value  # BytesIO 或者 None
                        if img_data:
                            try:
                                pil_img = PILImage.open(img_data)
                                # 调整大小
                                pil_img = pil_img.resize((80, 80))
                                # 二次写入 BytesIO 用于 xlsxwriter
                                resized_data = BytesIO()
                                pil_img.save(resized_data, format='PNG')
                                resized_data.seek(0)

                                worksheet.set_column(0, 0, 15)
                                worksheet.set_row(row_idx + 1, 80)

                                # 插入图片
                                worksheet.insert_image(
                                    row_idx + 1, 
                                    0, 
                                    '', 
                                    {'image_data': resized_data, 'x_scale': 1, 'y_scale': 1}
                                )
                            except Exception as e:
                                print(f"图片加载失败：{e}")
                            # 给这个单元格写空字符串或别的占位
                            worksheet.write(row_idx + 1, 0, "")
                        else:
                            # 如果没有图片，写一个提示或空白
                            worksheet.write(row_idx + 1, 0, "No Image")
                    else:
                        worksheet.write(row_idx + 1, col_idx, cell_value)

            # 关闭并保存Excel文件
            workbook.close()
            # 确保流的指针在开始位置
            output.seek(0)

            # 将流作为文件返回给前端
            response = make_response(send_file(
                output,
                as_attachment=True,
                download_name="Ozon订单数据.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ))

            return response

    else:
       return jsonify({
            "msg":"未找到对应用户！",
        }), 401