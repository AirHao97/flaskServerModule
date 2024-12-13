'''
author:AHAO
createTime:2024/05/30 8:56
description: 刀具CRUD接口
'''

from flask import Blueprint,jsonify,request,current_app,send_file
from Models import db
import uuid
from flask_jwt_extended import jwt_required,get_jwt_identity
from sqlalchemy.orm import joinedload
from sqlalchemy import or_,cast, DateTime
from datetime import datetime, timedelta
import time
import threading
from decimal import Decimal, getcontext
import traceback
from PyPDF2 import PdfMerger
import io
import pytz
import base64
import json

from Utils.crud import getDataFromDataBase_BaseData,addDataFromDataBase,modifyDataFromDataBase,deleteDataFromDataBase
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.apiRightsDecorator import admin_required,operations_required,active_required
from Utils.ozonAPI import getOrders,orderShip,getProductInfo,getProductAttributes,GetPackageLabel
from Utils.Constant.operateType import OperateType
from Utils.Constant.systemStatus import SystemStatus
from Utils.Constant.purchaseProductStatus import PurchaseProductStatus
from Utils.Constant.purchaseStatus import PurchaseStatus
from Utils.Constant.purchaseProductType import PurchaseProductType

from Models.Work.ozon_order_model import OzonOrder,OzonOrderOzonProduct
from Models.Work.ozon_product_model import OzonProduct
from Models.Work.system_product_model import SystemProduct
from Models.Work.purchase_product_model import PurchaseProduct
from Models.Work.shop_model import Shop
from Models.User.user_model import User



ozon_order_list = Blueprint('ozon_order', __name__, url_prefix='/ozon_order')

updataRunning = False

updataMsg = {
    "msg": "", 
    "updataProgress": {
        "nowUpdata": 0, 
        "allCount": 0, 
    },
    "lastUpdataData": {
        "lastUpdataTime": None,
        "updataOrderNumber": 0,
        "addOrderNumber":0,
        "updataProductNumber":0,
        "addProductNumber":0
    }
}

# 初始化数据计算精度
getcontext().prec = 4

# 加载订单与产品数据的子线程
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
                },
                "lastUpdataData": {
                    "lastUpdataTime": None,
                    "updataOrderNumber": 0,
                    "addOrderNumber":0,
                    "updataProductNumber":0,
                    "addProductNumber":0
                }
            }
            updataRunning = True
            
            shops = Shop.query.all()

            today = datetime.now()
            today_str = today.strftime('%Y-%m-%dT23:59:59Z')
            three_months_ago = today - timedelta(days=3)
            three_months_ago_str = three_months_ago.strftime('%Y-%m-%dT00:00:00Z')

            sinceTime = three_months_ago_str
            toTime = today_str

            # 总更新数量
            num = 0

            for index, i in enumerate(shops):

                updataMsg["updataProgress"]["nowUpdata"] = index
                updataMsg["updataProgress"]["allCount"] = len(shops)
                
                has_next = True
                offsetNumber = 0
                
                while has_next:

                    modify_context_purchase_order = []
                    modify_context_purchase_product = []
                    
                    updataMsg["msg"] = f"正在更新店铺:{i.name},更新店铺数量{index}/{len(shops)},已更新数据{num * 1000}条"

                    num += 1
                    result = getOrders(sinceTime=sinceTime, toTime=toTime, api_id=i.api_id, api_key=i.api_key, limit=1000, offset=offsetNumber)
                    
                    if result["data"]:
                        orders = result["data"]["postings"]

                        for itemOrders in orders:

                            addList_order = []
                            addList_product = []
                            addList_relation = []

                            ozon_order = OzonOrder.query.filter_by(posting_number=itemOrders["posting_number"]).first()
                            if not ozon_order:
                                ozon_order = OzonOrder()
                                ozon_order.id = str(uuid.uuid1()) 

                                addList_order.append(ozon_order)
                                updataMsg["lastUpdataData"]["addOrderNumber"] += 1
                            else:
                                updataMsg["lastUpdataData"]["updataOrderNumber"] += 1

                            ozon_order.order_id = itemOrders["order_id"]
                            ozon_order.order_number = itemOrders["order_number"]
                            ozon_order.posting_number = itemOrders["posting_number"]

                            ozon_order.posting_status = itemOrders["status"]

                            if not ozon_order.system_status == SystemStatus.freeze:
                                # ---对应 已创建待审核---
                                # 还未申请运单号
                                if itemOrders["status"]  == "awaiting_packaging":
                                    ozon_order.system_status = SystemStatus.createdPendingReview
                                # ---对应 等待国际运单号同步---
                                # 已经申请了运单号 等待运单号出来 
                                elif itemOrders["status"]  == "awaiting_registration":
                                    ozon_order.system_status = SystemStatus.waitForOzon
                                # ---对应 已审核待备货---
                                # 运单号已经出来了 等待发货给快递
                                elif itemOrders["status"]  == "awaiting_deliver":
                                    if not (ozon_order.system_status == SystemStatus.stockPreparedPendingOutward or ozon_order.system_status == SystemStatus.outwardShippedPendingDispatch):
                                        ozon_order.system_status = SystemStatus.reviewedPendingStock
                                # ---对应 已发货待签收---
                                # 在路上了
                                elif (
                                    itemOrders["status"]  == "acceptance_in_progress" 
                                    or itemOrders["status"]  == "driver_pickup"
                                    or itemOrders["status"]  == "delivering"
                                ):
                                    ozon_order.system_status = SystemStatus.dispatchedPendingSignatureConfirmation
                                # ---对应 已完成---
                                elif itemOrders["status"]  == "delivered":
                                    ozon_order.system_status = SystemStatus.signedforReceived
                                # ---对应 已取消---
                                elif itemOrders["status"]  == "cancelled":
                                    ozon_order.system_status = SystemStatus.cancelled
                                    # 解除系统中的ozon商品和采购商品的关联关系
                                    wait_for_purchase_purchase_order_list = []
                                    for purchase_product in ozon_order.purchase_products:
                                        # 采购商品对应的采购单
                                        purchase_order = purchase_product.purchase_order
                                        # 如果采购单还是待采购 
                                        if purchase_order.status == PurchaseStatus.waitForPurchase:
                                            wait_for_purchase_purchase_order_list.append(purchase_order)
                                            db.session.delete(purchase_product)
                                            modify_context_purchase_product.append(f"ozon订单{ozon_order.id}取消,且ozon订单绑定采购商品关联订单状态为{purchase_order.status},删除该采购商品{purchase_product.id}")
                                        else:
                                            purchase_product.ozon_order_id = None
                                            purchase_product.type = PurchaseProductType.unmatched
                                            modify_context_purchase_product.append(f"ozon订单{ozon_order.id}取消,且ozon订单绑定采购商品关联订单状态为{purchase_order.status},解除该采购商品{purchase_product.id}与ozon订单的关联，该ozon商品变成库存商品！")
                                        db.session.flush()

                                    for wait_for_purchase_purchase_order in wait_for_purchase_purchase_order_list:
                                        if not wait_for_purchase_purchase_order.purchase_products:
                                            db.session.delete(wait_for_purchase_purchase_order)
                                            modify_context_purchase_order.append(f"ozon订单{ozon_order.id}取消,且ozon订单绑定的采购商品对应的采购订单仅包含这一个ozon订单的采购商品，删除该采购订单{wait_for_purchase_purchase_order.id}")

                                # ---对应 仲裁中---
                                elif itemOrders["status"]  == "arbitration" or itemOrders["status"]  == "client_arbitration":
                                    ozon_order.system_status = SystemStatus.arbitration
                                # ---对应 其他未知的状态---
                                else:
                                    ozon_order.system_status = SystemStatus.other

                            ozon_order.logistics_status = itemOrders["substatus"]
                            ozon_order.delivery_id = itemOrders["delivery_method"]["id"]
                            ozon_order.delivery_name = itemOrders["delivery_method"]["name"]
                            ozon_order.delivery_tpl_provider_type = itemOrders["tpl_integration_type"]
                            ozon_order.delivery_tpl_provider_id = itemOrders["delivery_method"]["tpl_provider_id"]
                            ozon_order.delivery_tpl_provider_name = itemOrders["delivery_method"]["tpl_provider"]
                            ozon_order.warehouse_id = itemOrders["delivery_method"]["warehouse_id"]
                            ozon_order.warehouse_name = itemOrders["delivery_method"]["warehouse"]
                            ozon_order.tracking_number = itemOrders["tracking_number"]
                            # 客户信息返回都是null
                            # ozon_order.customer_id = itemOrders["customer"]["customer_id"]
                            # ozon_order.customer_name = itemOrders["customer"]["name"]
                            # ozon_order.address_city = itemOrders["customer"]["address"]["city"]
                            ozon_order.in_process_at = itemOrders["in_process_at"]
                            ozon_order.shipment_date = itemOrders["shipment_date"]
                            ozon_order.delivering_date = itemOrders["delivering_date"]
                            if itemOrders["cancellation"]:
                                ozon_order.cancel_reason = itemOrders["cancellation"]["cancel_reason"]
                                ozon_order.cancellation_type = itemOrders["cancellation"]["cancellation_type"]
                            ozon_order.currency_code = itemOrders["products"][0]["currency_code"]
                            ozon_order.shop_id = i.id

                            total_price = Decimal(0.0)

                            for itemProduct in itemOrders['products']:
                                
                                total_price = total_price + Decimal(itemProduct["price"]) * Decimal(itemProduct["quantity"])

                                ozon_product = OzonProduct.query.filter_by(sku=itemProduct["sku"]).first()
                                if not ozon_product:
                                    ozon_product = OzonProduct()
                                    ozon_product.id = str(uuid.uuid1())
                                    addList_product.append(ozon_product)
                                    updataMsg["lastUpdataData"]["addProductNumber"] += 1
                                else:
                                    updataMsg["lastUpdataData"]["updataProductNumber"] += 1
                                    
                                ozon_product.offer_id = itemProduct["offer_id"]
                                ozon_product.name = itemProduct["name"]
                                # ozon_product.price = itemProduct["price"]
                                ozon_product.currency_code = itemProduct["currency_code"]
                                ozon_product.sku = itemProduct["sku"]
                                ozon_product.shop_id = i.id

                                itemRelation = OzonOrderOzonProduct.query.filter_by(order_id=ozon_order.id, product_id=ozon_product.id).first()
                                if not itemRelation:
                                    itemRelation = OzonOrderOzonProduct()
                                    itemRelation.order_id = ozon_order.id
                                    itemRelation.product_id = ozon_product.id
                                    addList_relation.append(itemRelation)

                                itemRelation.quantity = itemProduct["quantity"]
                                itemRelation.price = itemProduct["price"]

                            ozon_order.total_price = float(total_price)

                            try:
                                if modify_context_purchase_order:
                                    operate_log_writer_func(operateType=OperateType.purchaseOrder,describe=modify_context_purchase_order,isSystem=True)
                                if modify_context_purchase_product:
                                    operate_log_writer_func(operateType=OperateType.purchaseProduct,describe=modify_context_purchase_product,isSystem=True)
                                db.session.add_all(addList_order)
                                db.session.add_all(addList_product)
                                db.session.add_all(addList_relation)
                                db.session.commit()
                                
                            except Exception as e:
                                updataMsg["msg"] = f"ozon订单更新失败!错误信息：{e}"
                                operate_log_writer_func(operateType=OperateType.ozonOrder,describe=f'ozon订单更新失败，错误信息”：{e}',isSystem=True)
                                return 
                        
                        has_next = result["data"]["has_next"]
                        offsetNumber += 1000
                    else:
                        has_next = False
                        updataRunning = False
                        operate_log_writer_func(operateType=OperateType.ozonOrder,describe=f'ozon订单更新失败,错误信息”：{result["msg"]}',isSystem=True)
                        updataMsg["msg"] = f'ozon订单更新失败,错误信息”：{result["msg"]}'
                        return
            
            updataMsg["msg"] = "ozon订单更新完成!开始准备更新产品数据！"
            updataMsg["lastUpdataData"]["lastUpdataTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")                        
            operate_log_writer_func(operateType=OperateType.ozonOrder,describe=f'ozon订单更新完成! 共更新订单数据{updataMsg["lastUpdataData"]["updataOrderNumber"]},新增订单数据{updataMsg["lastUpdataData"]["addOrderNumber"]},更新产品数据{updataMsg["lastUpdataData"]["updataProductNumber"]},新增产品数据{updataMsg["lastUpdataData"]["addProductNumber"]}',isSystem=True)

        except Exception as e:
            updataRunning = False
            operate_log_writer_func(operateType=OperateType.ozonOrder,describe=f"ozon订单更新失败,错误信息”：{e}",isSystem=True)
            stack_trace = traceback.format_exc()
            updataMsg["msg"] =  f"ozon订单更新失败,错误信息”：{stack_trace}"
            return
        
        # 开始更新商品数据
        try:
            # 数据初始化
            updataMsg = {
                "msg": "", 
                "updataProgress": {
                    "nowUpdata": 0, 
                    "allCount": 0, 
                },
                "lastUpdataData": {
                    "lastUpdataTime": None,
                    "updataOrderNumber": 0,
                    "addOrderNumber":0,
                    "updataProductNumber":0,
                    "addProductNumber":0
                }
            }

            # 获取全部的未更新product_id的ozon商品
            ozon_products = OzonProduct.query.filter_by(product_id=None).all()
            updataMsg["updataProgress"]["allCount"] = len(ozon_products)
            
            # 一条条更新产品的product_id
            for ozon_product in ozon_products:
                
                # 更新产品佣金信息
                shop = ozon_product.shop
                result = getProductInfo(api_id=shop.api_id,api_key=shop.api_key,sku=ozon_product.sku)
                if result["data"]:
                    product_msg = result["data"]["result"]
                    updataMsg["updataProgress"]["nowUpdata"] += 1

                    ozon_product.product_id = product_msg["id"]
                    ozon_product.category_two_id = product_msg["description_category_id"]
                    ozon_product.category_three_id = product_msg["type_id"]
                    
                    if product_msg["old_price"]:
                        ozon_product.price = product_msg["old_price"]
                    else:
                        ozon_product.price = product_msg["price"]

                    if product_msg["primary_image"]:
                        ozon_product.primary_image = product_msg["primary_image"]
                    else:
                        ozon_product.primary_image = product_msg["images"][0]
                    
                    for commission in product_msg["commissions"]:
                        if commission["sale_schema"] == "fbo":
                            ozon_product.fbo_commission_percent = commission["percent"]
                            ozon_product.fbo_commission_value = commission["value"]
                        elif commission["sale_schema"] == "fbs":
                            ozon_product.fbs_commission_percent = commission["percent"]
                            ozon_product.fbs_commission_value = commission["value"]
                        elif commission["sale_schema"] == "rfbs":
                            ozon_product.rfbs_commission_percent = commission["percent"]
                            ozon_product.rfbs_commission_value = commission["value"]
                        elif commission["sale_schema"] == "fbp":
                            ozon_product.fbp_commission_percent = commission["percent"]
                            ozon_product.fbp_commission_value = commission["value"]                            
                    try:
                        db.session.commit()
                    except Exception as e:
                        updataMsg["msg"] = f"ozon商品更新失败!错误信息：{e}"
                        operate_log_writer_func(operateType=OperateType.ozonProduct,describe=f'ozon商品更新失败，错误信息”：{e}',isSystem=True)
                        return 
                else:
                    updataRunning = False
                    operate_log_writer_func(operateType=OperateType.ozonProduct,describe=f'ozon商品更新失败,错误信息”：{result["msg"]}',isSystem=True)
                    updataMsg["msg"] = f'ozon商品更新失败,错误信息”：{result["msg"]}'
                    return

            updataMsg["msg"] = "ozon商品信息更新完成!"
            updataMsg["lastUpdataData"]["lastUpdataTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")                        
            operate_log_writer_func(operateType=OperateType.ozonProduct,describe=f'ozon商品信息更新完成! 共更新商品数据{updataMsg["updataProgress"]["nowUpdata"]}',isSystem=True)
            updataRunning = False          

        except Exception as e:
            updataRunning = False  
            operate_log_writer_func(operateType=OperateType.ozonOrder,describe=f"ozonc产品更新失败,错误信息”：{e}",isSystem=True)
            stack_trace = traceback.format_exc()
            updataMsg["msg"] =  f"ozon商品更新失败,错误信息”：{stack_trace}"
            return

# ozon订单/ozon 商品 初始化（加载四个月内 所有创建的店铺的ozon订单）
# 仅管理员可操作
@ozon_order_list.route('/updataData', methods=['POST'])
@jwt_required()
@active_required
@admin_required
def updataData():
    global updataRunning

    if not updataRunning:
        thread = threading.Thread(target=updataDataThread, args=(current_app._get_current_object(),))
        thread.start()
        operate_log_writer_func(operateType=OperateType.ozonOrder,describe="开始更新ozon订单!")
        return jsonify({"msg": "ozon订单更新已启动!"}), 200
    else:
        return jsonify({"msg": f"ozon订单更新正在进行中...{updataMsg['msg']}"}), 200


# 获取当前数据更新进度
# 登陆即可操作
@ozon_order_list.route('/progress', methods=['POST'])
@jwt_required()
@active_required
def getProgress():
    global updataMsg
    return jsonify(updataMsg), 200

# 查询全部的订单数据
# 系统管理员、部门管理员、小组管理员 和 运营可操作
# 系统管理员可查询全部数据
# 部门管理员可以查询本部门数据
# 小组管理员可以查询本小组数据
# 运营只能查询自己店铺 和 被授权的下的数据
@ozon_order_list.route('/getData', methods=['GET'])
@jwt_required()
@active_required
def getData():
    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()
    if user:
        start = int(request.args.get('start', 0))
        limit = int(request.args.get('limit', 10))
        keyWord = str(request.args.get('keyWord', None))
        system_status = str(request.args.get('system_status', None))
        dateRange = request.args.get('dateRange', None)

        if dateRange:
            dateRange = json.loads(dateRange)
            try:
                start_date = datetime.strptime(dateRange[0], "%Y-%m-%d %H:%M:%S")
                end_date = datetime.strptime(dateRange[1], "%Y-%m-%d %H:%M:%S")
                
                utc = pytz.UTC
                start_date_utc =utc.localize(datetime.strptime(dateRange[0], "%Y-%m-%d %H:%M:%S"))
                end_date_utc = utc.localize(datetime.strptime(dateRange[1], "%Y-%m-%d %H:%M:%S"))

            except ValueError:
                return jsonify({"msg": "时间范围格式错误！"}), 400
        

        if keyWord:
            # 获取 OzonOrder 的所有字段
            order_columns = [column.name for column in OzonOrder.__table__.columns]
            # 获取 OzonProduct 的所有字段
            product_columns = [column.name for column in OzonProduct.__table__.columns]
            # 构建 OzonOrder 字段的过滤条件
            order_filters = [getattr(OzonOrder, col).like(f'%{keyWord}%') for col in order_columns]
            # 构建 OzonProduct 字段的过滤条件
            product_filters = [getattr(OzonProduct, col).like(f'%{keyWord}%') for col in product_columns]
            # 联合查询条件
            filters = or_(*order_filters, *product_filters)

            query = (
                OzonOrder.query
                .outerjoin(OzonOrderOzonProduct, OzonOrder.id == OzonOrderOzonProduct.order_id)
                .outerjoin(OzonProduct, OzonOrderOzonProduct.product_id == OzonProduct.id)
                .filter(filters)
                .options(joinedload(OzonOrder.ozon_products_msg))
            )
        else:
            query = OzonOrder.query


        if dateRange:
            query = query.filter(
                OzonOrder.in_process_at.between(start_date_utc, end_date_utc),
            )

        if system_status and system_status != "全部":
            query = query.filter_by(system_status = system_status)

        if user.is_admin:
            results = query.order_by(OzonOrder.create_time).offset(start).limit(limit).all()
            count = query.order_by(OzonOrder.create_time).count()
        elif user.is_department_admin and user.department:
            shop_ids = []
            users = User.query.filter_by(department_id = user.department_id).all()
            # 本部门
            for i in users:
                for j in i.owner_shops:
                    shop_ids.append(j.id)
            # 自己关联的
            for i in user.partner_orders_of:
                for j in i.owner_shops:
                    shop_ids.append(j.id)
            query = query.filter(OzonOrder.shop_id.in_(shop_ids)).order_by(OzonOrder.create_time)
            results = query.offset(start).limit(limit).all()
            count = query.count()

        elif user.is_team_admin and user.team:
            shop_ids = []
            users = User.query.filter_by(team_id = user.team_id).all()
            # 本小组的
            for i in users:
                for j in i.owner_shops:
                    shop_ids.append(j.id)
            # 自己关联的
            for i in user.partner_orders_of:
                for j in i.owner_shops:
                    shop_ids.append(j.id)
            query = query.filter(OzonOrder.shop_id.in_(shop_ids)).order_by(OzonOrder.create_time)
            results = query.offset(start).limit(limit).all()
            count = query.count()
        else:
            if not any(role.id == "1" for role in user.roles):
                return {"msg":"当前账户无操作权限！"},400
            
            # 自己店铺下的id
            shop_ids = [item.id for item in user.owner_shops]
            # 可处理订单的关系伙伴下的店铺id
            for i in user.partner_orders_of:
                for j in i.owner_shops:
                    shop_ids.append(j.id)
            query = query.filter(OzonOrder.shop_id.in_(shop_ids)).order_by(OzonOrder.create_time)
            results = query.offset(start).limit(limit).all()
            count = query.count()

        results = {
            "data" :[
            {
                "id": result.id,
                "order_id": result.order_id,
                "order_number": result.order_number,
                "posting_number": result.posting_number,
                "posting_status": result.posting_status,
                "logistics_status": result.logistics_status,
                "delivery" : {
                    "delivery_id": result.delivery_id,
                    "delivery_name": result.delivery_name,
                    "delivery_tpl_provider_type": result.delivery_tpl_provider_type,
                    "delivery_tpl_provider_id": result.delivery_tpl_provider_id,
                    "delivery_tpl_provider_name": result.delivery_tpl_provider_name,
                },
                "warehouse_id": result.warehouse_id,
                "warehouse_name": result.warehouse_name,
                "tracking_number": result.tracking_number,
                "customer_id": result.customer_id,
                "customer_name": result.customer_name,
                "address_city": result.address_city,
                "in_process_at": result.in_process_at,
                "shipment_date": result.shipment_date,
                "delivering_date": result.delivering_date,
                "cancel_reason": result.cancel_reason,
                "cancellation_type": result.cancellation_type,
                "currency_code": result.currency_code,
                "total_price": result.total_price,
                "system_status": result.system_status,
                "approval_time": result.approval_time,
                "dispatch_time": result.dispatch_time,
                "shop": {"id":result.shop.id, "name":result.shop.name},
                "owner": {"id":result.shop.owner.id, "name":result.shop.owner.username} if result.shop.owner else None,
                "create_time": result.create_time,
                "modify_time": result.modify_time,
                
                # 对应的采购的商品
                "purchase_products":[
                    {
                        "id": purchase_product.id,
                        "price": purchase_product.price,
                        "stock_in_date": purchase_product.stock_in_date,
                        "sku": purchase_product.sku,
                        "type": purchase_product.type,
                        "status": purchase_product.status,
                        "purchase_order_id": purchase_product.purchase_order_id,
                        "system_product_id": purchase_product.system_product_id,
                        "create_time": purchase_product.create_time,
                        "modify_time": purchase_product.modify_time,
                    } for purchase_product in result.purchase_products
                ],

                # 对应的ozon商品
                "products":[
                    {
                        "quantity": item.quantity,
                        "real_price":item.price,
                        "id": item.ozon_product.id,
                        "offer_id": item.ozon_product.offer_id,
                        "name": item.ozon_product.name,
                        "price": item.ozon_product.price,
                        "currency_code": item.ozon_product.currency_code,
                        "sku": item.ozon_product.sku,
                        "link": item.ozon_product.link,
                        "mandatory_mark": item.ozon_product.mandatory_mark,
                        "fbo_commission_percent": item.ozon_product.fbo_commission_percent,
                        "fbo_commission_value": item.ozon_product.fbo_commission_value,
                        "fbs_commission_percent": item.ozon_product.fbs_commission_percent,
                        "fbs_commission_value": item.ozon_product.fbs_commission_value,
                        "rfbs_commission_percent": item.ozon_product.rfbs_commission_percent,
                        "rfbs_commission_value": item.ozon_product.rfbs_commission_value,
                        "fbp_commission_percent": item.ozon_product.fbp_commission_percent,
                        "fbp_commission_value": item.ozon_product.fbp_commission_value,
                        "product_id": item.ozon_product.product_id,
                        "create_time": item.ozon_product.create_time,
                        "primary_image":item.ozon_product.primary_image,
                        "category_two_id":item.ozon_product.category_two_id,
                        "category_three_id":item.ozon_product.category_three_id,
                        "create_time": item.ozon_product.create_time,
                        "modify_time": item.ozon_product.modify_time,
                        "system_products":[
                            {
                                "id": system_products_msg.system_product.id,
                                "primary_image": system_products_msg.system_product.primary_image,
                                "system_sku": system_products_msg.system_product.system_sku,
                                "reference_weight": system_products_msg.system_product.reference_weight,
                                "reference_cost": system_products_msg.system_product.reference_cost,
                                "purchase_link": system_products_msg.system_product.purchase_link,
                                "supplier_name": system_products_msg.system_product.supplier_name,
                                "purchase_platform": system_products_msg.system_product.purchase_platform,
                                "creator": {"id":system_products_msg.system_product.creator_id, "name":system_products_msg.system_product.creator.username},
                                "create_time": system_products_msg.system_product.create_time,
                                "modify_time": system_products_msg.system_product.modify_time,
                                "quantity":system_products_msg.quantity,
                                
                                "wait_for_purchase_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                                "in_basket_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                                "in_transit_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                                "stock_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                                "out_stock_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                                "loss_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.loss]),

                            } for system_products_msg in item.ozon_product.system_products_msg
                        ]
                    } for item in result.ozon_products_msg
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

# 订单审核（申请运单号）
# 系统管理员、部门管理员、小组管理员 和 运营可操作
# 系统管理员可审核全部订单
# 部门管理员可以审核本部门订单
# 小组管理员可以审核本小组订单
# 运营可以审核自己的店铺下的订单
@ozon_order_list.route('/auditOrder', methods=['POST'])
@jwt_required()
@active_required
def auditOrder():
    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "posting_number" in data:
        posting_number = data['posting_number']
    else:
        return jsonify({"msg":"posting_number 不能为空！"}),401
    
    order = OzonOrder.query.filter_by(posting_number=posting_number).first()

    if not order:
        return {"msg":"找不到当前订单！"},401

    if user:
        if (
            # 系统管理员
            user.is_admin
            # 部门管理员 
            or (user.is_department_admin and user.department and order.shop.owner.department_id == user.department_id)
            # 小组管理员
            or (user.is_team_admin and user.team and order.shop.owner.team_id == user.team_id)
            # 单子属于运营自己
            or (any(role.id == "1" for role in user.roles) and user.id == order.shop.owner.id)
            # 用户属于订单的拥有者的订单关联伙伴
            or (any(user.id == partner_orders.id for partner_orders in order.shop.owner.partners_orders))
        ):
            
            # 订单 拆分/直接 申请运单号
            if "packages" in data:
                packages = data['packages']
            else:
                return {"msg":"packages 不能为空！"},401
            
            result = orderShip(
                api_id = order.shop.api_id, 
                api_key = order.shop.api_key, 
                posting_number = posting_number,
                packages = packages
            )

            
            # 新增的关系数据
            addList_relation = []
            addList_order = []

            if result["code"] == 200:
                order.system_status = SystemStatus.reviewedPendingStock
                order.approval_time = datetime.now()

                # 未拆分
                if (len(result["data"]["result"]) == 1):
                    pass
                # 拆分 
                # 新建拆分后的子订单和产品
                else:
                    for item in result["data"]["additional_data"]:
                        # 主订单号
                        if item["posting_number"] == order.posting_number:
                            # 更新原订单和产品的关系
                            total_price = Decimal(0.0)
                            itemRelationList = []
                            for itemProduct in item["products"]:

                                total_price = total_price + Decimal(itemProduct["price"]) * Decimal(itemProduct["quantity"])
                                ozon_product = OzonProduct.query.filter_by(sku=itemProduct["sku"]).first()                                
                                itemRelation = OzonOrderOzonProduct.query.filter_by(order_id=order.id, product_id=ozon_product.id).first()
                                itemRelation.quantity = itemProduct["quantity"]
                                itemRelation.price  = itemProduct["price"]
                                itemRelationList.append(itemRelation)
                            
                            # 删除多余的连接关系
                            relations = OzonOrderOzonProduct.query.filter_by(order_id=order.id).all()                            
                            itemRelationList_id = [item.id for item in itemRelationList]
                            to_delete_relations = [item for item in relations if item.id not in itemRelationList_id]
                            for relation in to_delete_relations:
                                db.session.delete(relation)

                            order.total_price = float(total_price)

                        else:
                            ozon_order = OzonOrder()
                            ozon_order.id = str(uuid.uuid1())
                            ozon_order.posting_number = item["posting_number"]
                            ozon_order.system_status = SystemStatus.reviewedPendingStock
                            ozon_order.approval_time = datetime.now()
                            addList_order.append(ozon_order)
                        
                            total_price = Decimal(0.0)

                            for itemProduct in item["products"]:
                                total_price = total_price + Decimal(itemProduct["price"]) * Decimal(itemProduct["quantity"])
                                ozon_product = OzonProduct.query.filter_by(sku=itemProduct["sku"]).first()
                                itemRelation = OzonOrderOzonProduct()

                                itemRelation.order_id = ozon_order.id
                                itemRelation.product_id = ozon_product.id
                                itemRelation.quantity = itemProduct["quantity"]
                                itemRelation.price = itemProduct["price"]

                                addList_relation.append(itemRelation)

                            order.total_price = float(total_price)
                try:
                    db.session.add_all(addList_order)
                    db.session.add_all(addList_relation)
                    db.session.commit()
                    operate_log_writer_func(operateType=OperateType.ozonOrder, describe=f"操作人:{user.username}, 操作:审核订单, id:{order.id}")
                    return {"msg":"订单审核成功！"}, 200  
                except Exception as e:
                    print(e)
                    return {"msg":"审核后订单数据存储失败！"}, 400
            else:
                return {"msg":"订单审核失败！"}, 400                
        else:
            return jsonify({
                "msg":"无该订单审核权限！",
            }), 400 
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 401

# 订单冻结
# 系统管理员、部门管理员、小组管理员 和 运营可操作
# 系统管理员可冻结全部订单
# 部门管理员可冻结本部门订单
# 小组管理员可冻结本小组订单
# 运营可以冻结自己的店铺下的订单
@ozon_order_list.route('/freezeOrder', methods=['POST'])
@jwt_required()
@active_required
def freezeOrder():
    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "order_id" in data:
        order_id = data['order_id']
    else:
        return jsonify({"msg":"order_id 不能为空！"}),401

    order = OzonOrder.query.filter_by(id=order_id).first()

    if not order:
        return {"msg":"找不到当前订单！"},401

    if user:
        if (
            # 系统管理员
            user.is_admin
            # 部门管理员 
            or (user.is_department_admin and user.department and order.shop.owner.department_id == user.department_id)
            # 小组管理员
            or (user.is_team_admin and user.team and order.shop.owner.team_id == user.team_id)
            # 单子属于运营自己
            or (any(role.id == "1" for role in user.roles) and user.id == order.shop.owner.id)
            # 用户属于订单的拥有者的订单关联伙伴
            or (any(user.id == partner_orders.id for partner_orders in order.shop.owner.partners_orders))
        ):
             
            order.system_status = SystemStatus.freeze

            try:
                db.session.commit()
                operate_log_writer_func(operateType=OperateType.ozonOrder, describe=f"操作人:{user.username}, 操作:冻结订单, id:{order.id}")
                return {"msg":"订单冻结成功！"}, 200  
            except Exception as e:
                return {"msg":"订单冻结失败！"}, 400
                    
        else:
            return jsonify({
                "msg":"无该订单冻结权限！",
            }), 400 
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 401

# 订单解冻
# 系统管理员、部门管理员、小组管理员 和 运营可操作
# 系统管理员可解冻全部订单
# 部门管理员可解冻本部门订单
# 小组管理员可解冻本小组订单
# 运营可以解冻自己的店铺下的订单
@ozon_order_list.route('/unfreezeOrder', methods=['POST'])
@jwt_required()
@active_required
def unfreezeOrder():
    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "order_id" in data:
        order_id = data['order_id']
    else:
        return jsonify({"msg":"order_id 不能为空！"}),401

    order = OzonOrder.query.filter_by(id=order_id).first()

    if not order:
        return {"msg":"找不到当前订单！"},401
    
    if order.system_status != SystemStatus.freeze:
        return {"msg":"无法解冻未冻结的订单！"},400

    if user:
        if (
            # 系统管理员
            user.is_admin
            # 部门管理员 
            or (user.is_department_admin and user.department and order.shop.owner.department_id == user.department_id)
            # 小组管理员
            or (user.is_team_admin and user.team and order.shop.owner.team_id == user.team_id)
            # 单子属于运营自己
            or (any(role.id == "1" for role in user.roles) and user.id == order.shop.owner.id)
            # 用户属于订单的拥有者的订单关联伙伴
            or (any(user.id == partner_orders.id for partner_orders in order.shop.owner.partners_orders))
        ):
             
            order.system_status = SystemStatus.other

            try:
                db.session.commit()
                operate_log_writer_func(operateType=OperateType.ozonOrder, describe=f"操作人:{user.username}, 操作:解冻订单, id:{order.id}")
                return {"msg":"订单成解冻功！"}, 200  
            except Exception as e:
                return {"msg":"订单解冻失败！"}, 400
                    
        else:
            return jsonify({
                "msg":"无该订单解冻权限！",
            }), 400 
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 401

# 更新待出库订单
# 系统管理员、部门管理员 和 打包 可操作
@ozon_order_list.route('/getOrderForDispatch', methods=['POST'])
@jwt_required()
@active_required
def getOrderForDispatch():
    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:
        if current_user.is_admin:
            query = OzonOrder.query.filter(
                OzonOrder.system_status == SystemStatus.reviewedPendingStock
            )
        elif current_user.department and (current_user.is_department_admin  or any(role.id == "3" for role in current_user.roles)):
            query = OzonOrder.query.filter(
                OzonOrder.system_status == SystemStatus.reviewedPendingStock
            ).join(Shop, OzonOrder.shop_id == Shop.id).join(User,Shop.owner_id == User.id).filter(User.department_id == current_user.department_id)
        
        else:
            return {"msg":"当前账户无操作权限！"},400

        # 已审核待备货 本部门 ozon订单 根据开始处理时间排序
        ozon_orders = query.order_by(cast(OzonOrder.in_process_at, DateTime)).all()
        
        # 可出库订单 按时间顺序从早到晚
        res = []
        # 需要从库存中拿的商品信息
        get_from_stock_msg = []
        
        context = []
        for ozon_order in ozon_orders:

            flag = True

            if ozon_order.purchase_products:
                
                # 计算每个品类绑定的商品数量是否正确
                for ozon_products_msg in ozon_order.ozon_products_msg:
                    quantity1 = int(ozon_products_msg.quantity)
                    ozon_product = ozon_products_msg.ozon_product

                    for system_product_msg in ozon_product.system_products_msg:
                        system_product = system_product_msg.system_product
                        quantity2 = int(system_product_msg.quantity)
                        quantity = quantity1 * quantity2

                        item = [product for product in ozon_order.purchase_products if product.system_product_id == system_product.id]
                        
                        if not len(item) == quantity:
                            flag = False

                for purchase_product in ozon_order.purchase_products:
                    temp = []
                    if purchase_product.status == PurchaseProductStatus.in_basket:
                        pass                        
                    elif purchase_product.status == PurchaseProductStatus.in_stock:
                        temp.append({"id":purchase_product.id,"sku":purchase_product.sku})
                    else:
                        flag = False
            else:
                flag = False

            if flag:
                context.append({"订单id":ozon_order.id,"状态":f"{ozon_order.system_status} => {SystemStatus.stockPreparedPendingOutward}"})
                res.append(ozon_order)
                ozon_order.system_status = SystemStatus.stockPreparedPendingOutward
                if temp:
                    get_from_stock_msg.extend(temp)
        
        try:
            db.session.commit()
            operate_log_writer_func(operateType=OperateType.ozonOrder, describe=f"操作人:{current_user.username}, 操作:更新可打包订单,可打包订单更新成功！共{len(res)}条, 其中需要从库存获取的产品为{get_from_stock_msg}")
            
            return jsonify(
                {
                    "msg":f"可打包订单更新成功！共{len(res)}条,需要从库存获取的产品数量为{len(get_from_stock_msg)}",
                    "data": get_from_stock_msg
                }
                ), 200 
        except Exception as e:
            return {"msg":"可打包订单更新失败！"}, 400

    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 400 
    
# 获取已备货待出库的ozon订单数据
# 管理员、部门管理员、打包可操作
@ozon_order_list.route('/getStockPreparedPendingOutwardOzonOrderData', methods=['GET'])
@jwt_required()
@active_required
def getStockPreparedPendingOutwardOzonOrderData():
    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:

        if current_user.is_admin:
            query = OzonOrder.query
        elif current_user.department and (current_user.is_department_admin or any(role.id == "3" for role in current_user.roles)):
            query = OzonOrder.query.join(Shop, OzonOrder.shop_id == Shop.id).join(User,Shop.owner_id == User.id).filter(User.department_id == current_user.department_id)
        else:
            return {"msg":"当前账户无操作权限！"},400
        
        start = int(request.args.get('start', 0))
        limit = int(request.args.get('limit', 10))
        keyWord = str(request.args.get('keyWord', None))

        if keyWord:
            columns = [column.name for column in OzonOrder.__table__.columns ]
            filters = [getattr(OzonOrder, col).like(f'%{keyWord}%') for col in columns]
            query = query.filter(or_(*filters))

        query = query.filter(OzonOrder.system_status==SystemStatus.stockPreparedPendingOutward)
        # query = query.filter_by(system_status=SystemStatus.reviewedPendingStock)

        results = query.order_by(OzonOrder.create_time).offset(start).limit(limit).all()
        count = query.order_by(OzonOrder.create_time).count()

        results = {
            "data" :[
            {
                "id": result.id,
                "order_id": result.order_id,
                "order_number": result.order_number,
                "posting_number": result.posting_number,
                "posting_status": result.posting_status,
                "logistics_status": result.logistics_status,
                "delivery" : {
                    "delivery_id": result.delivery_id,
                    "delivery_name": result.delivery_name,
                    "delivery_tpl_provider_type": result.delivery_tpl_provider_type,
                    "delivery_tpl_provider_id": result.delivery_tpl_provider_id,
                    "delivery_tpl_provider_name": result.delivery_tpl_provider_name,
                },
                "warehouse_id": result.warehouse_id,
                "warehouse_name": result.warehouse_name,
                "tracking_number": result.tracking_number,
                "customer_id": result.customer_id,
                "customer_name": result.customer_name,
                "address_city": result.address_city,
                "in_process_at": result.in_process_at,
                "shipment_date": result.shipment_date,
                "delivering_date": result.delivering_date,
                "cancel_reason": result.cancel_reason,
                "cancellation_type": result.cancellation_type,
                "currency_code": result.currency_code,
                "total_price": result.total_price,
                "system_status": result.system_status,
                "approval_time": result.approval_time,
                "dispatch_time": result.dispatch_time,
                "shop": {"id":result.shop.id, "name":result.shop.name},
                "owner": {"id":result.shop.owner.id, "name":result.shop.owner.username} if result.shop.owner else None,
                "create_time": result.create_time,
                "modify_time": result.modify_time,
                
                # 对应的采购的商品
                "purchase_products":[
                    {
                        "id": purchase_product.id,
                        "price": purchase_product.price,
                        "stock_in_date": purchase_product.stock_in_date,
                        "sku": purchase_product.sku,
                        "type": purchase_product.type,
                        "status": purchase_product.status,
                        "purchase_order_id": purchase_product.purchase_order_id,
                        "system_product_id": purchase_product.system_product_id,
                        "create_time": purchase_product.create_time,
                        "modify_time": purchase_product.modify_time,
                    } for purchase_product in result.purchase_products
                ],

                # 对应的ozon商品
                "products":[
                    {
                        "quantity": item.quantity,
                        "real_price":item.price,
                        "id": item.ozon_product.id,
                        "offer_id": item.ozon_product.offer_id,
                        "name": item.ozon_product.name,
                        "price": item.ozon_product.price,
                        "currency_code": item.ozon_product.currency_code,
                        "sku": item.ozon_product.sku,
                        "link": item.ozon_product.link,
                        "mandatory_mark": item.ozon_product.mandatory_mark,
                        "fbo_commission_percent": item.ozon_product.fbo_commission_percent,
                        "fbo_commission_value": item.ozon_product.fbo_commission_value,
                        "fbs_commission_percent": item.ozon_product.fbs_commission_percent,
                        "fbs_commission_value": item.ozon_product.fbs_commission_value,
                        "rfbs_commission_percent": item.ozon_product.rfbs_commission_percent,
                        "rfbs_commission_value": item.ozon_product.rfbs_commission_value,
                        "fbp_commission_percent": item.ozon_product.fbp_commission_percent,
                        "fbp_commission_value": item.ozon_product.fbp_commission_value,
                        "product_id": item.ozon_product.product_id,
                        "create_time": item.ozon_product.create_time,
                        "primary_image":item.ozon_product.primary_image,
                        "category_two_id":item.ozon_product.category_two_id,
                        "category_three_id":item.ozon_product.category_three_id,
                        "create_time": item.ozon_product.create_time,
                        "modify_time": item.ozon_product.modify_time,
                        "system_products":[
                            {
                                "id": system_products_msg.system_product.id,
                                "primary_image": system_products_msg.system_product.primary_image,
                                "system_sku": system_products_msg.system_product.system_sku,
                                "reference_weight": system_products_msg.system_product.reference_weight,
                                "reference_cost": system_products_msg.system_product.reference_cost,
                                "purchase_link": system_products_msg.system_product.purchase_link,
                                "supplier_name": system_products_msg.system_product.supplier_name,
                                "purchase_platform": system_products_msg.system_product.purchase_platform,
                                "creator": {"id":system_products_msg.system_product.creator_id, "name":system_products_msg.system_product.creator.username},
                                "create_time": system_products_msg.system_product.create_time,
                                "modify_time": system_products_msg.system_product.modify_time,
                                "quantity":system_products_msg.quantity,
                                "wait_for_purchase_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                                "in_basket_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                                "in_transit_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                                "stock_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                                "out_stock_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                                "loss_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.loss]),

                            } for system_products_msg in item.ozon_product.system_products_msg
                        ]
                    } for item in result.ozon_products_msg
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
            }), 4
    
# 根据国际运单号查询订单
# 管理员、部门管理员、打包可操作
@ozon_order_list.route('/getOzonOrderWithTrackingNumber', methods=['POST'])
@jwt_required()
@active_required
def getOzonOrderWithTrackingNumber():
    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:

        if current_user.is_admin:
            query = OzonOrder.query
        elif current_user.department and (current_user.is_department_admin or any(role.id == "3" for role in current_user.roles)):
            query = OzonOrder.query.join(Shop, OzonOrder.shop_id == Shop.id).join(User,Shop.owner_id == User.id).filter(User.department_id == current_user.department_id)
        else:
            return {"msg":"当前账户无操作权限！"},400
        
        data = request.get_json()

        if "tracking_number" in data:
            tracking_number = data['tracking_number']
        else:
            return jsonify({"msg":"国际运单号 不能为空！"}),401

        result = query.filter_by(tracking_number=tracking_number).first()

        if not result:
            return {"msg":f"找不到包含{tracking_number}国际运单号的ozon订单！"},400

        result = {
            "id": result.id,
            "order_id": result.order_id,
            "order_number": result.order_number,
            "posting_number": result.posting_number,
            "posting_status": result.posting_status,
            "logistics_status": result.logistics_status,
            "delivery" : {
                "delivery_id": result.delivery_id,
                "delivery_name": result.delivery_name,
                "delivery_tpl_provider_type": result.delivery_tpl_provider_type,
                "delivery_tpl_provider_id": result.delivery_tpl_provider_id,
                "delivery_tpl_provider_name": result.delivery_tpl_provider_name,
            },
            "warehouse_id": result.warehouse_id,
            "warehouse_name": result.warehouse_name,
            "tracking_number": result.tracking_number,
            "customer_id": result.customer_id,
            "customer_name": result.customer_name,
            "address_city": result.address_city,
            "in_process_at": result.in_process_at,
            "shipment_date": result.shipment_date,
            "delivering_date": result.delivering_date,
            "cancel_reason": result.cancel_reason,
            "cancellation_type": result.cancellation_type,
            "currency_code": result.currency_code,
            "total_price": result.total_price,
            "system_status": result.system_status,
            "approval_time": result.approval_time,
            "dispatch_time": result.dispatch_time,
            "shop": {"id":result.shop.id, "name":result.shop.name},
            "owner": {"id":result.shop.owner.id, "name":result.shop.owner.username} if result.shop.owner else None,
            "create_time": result.create_time,
            "modify_time": result.modify_time,
            
            # 对应的采购的商品
            "purchase_products":[
                    {
                        "id": purchase_product.id,
                        "price": purchase_product.price,
                        "stock_in_date": purchase_product.stock_in_date,
                        "sku": purchase_product.sku,
                        "type": purchase_product.type,
                        "status": purchase_product.status,
                        "purchase_order_id": purchase_product.purchase_order_id,
                        "system_product_id": purchase_product.system_product_id,
                        "create_time": purchase_product.create_time,
                        "modify_time": purchase_product.modify_time,
                    } for purchase_product in result.purchase_products
                ],

            # 对应的ozon商品
            "products":[
                {
                    "quantity": item.quantity,
                    "real_price":item.price,
                    "id": item.ozon_product.id,
                    "offer_id": item.ozon_product.offer_id,
                    "name": item.ozon_product.name,
                    "price": item.ozon_product.price,
                    "currency_code": item.ozon_product.currency_code,
                    "sku": item.ozon_product.sku,
                    "link": item.ozon_product.link,
                    "mandatory_mark": item.ozon_product.mandatory_mark,
                    "fbo_commission_percent": item.ozon_product.fbo_commission_percent,
                    "fbo_commission_value": item.ozon_product.fbo_commission_value,
                    "fbs_commission_percent": item.ozon_product.fbs_commission_percent,
                    "fbs_commission_value": item.ozon_product.fbs_commission_value,
                    "rfbs_commission_percent": item.ozon_product.rfbs_commission_percent,
                    "rfbs_commission_value": item.ozon_product.rfbs_commission_value,
                    "fbp_commission_percent": item.ozon_product.fbp_commission_percent,
                    "fbp_commission_value": item.ozon_product.fbp_commission_value,
                    "product_id": item.ozon_product.product_id,
                    "create_time": item.ozon_product.create_time,
                    "primary_image":item.ozon_product.primary_image,
                    "category_two_id":item.ozon_product.category_two_id,
                    "category_three_id":item.ozon_product.category_three_id,
                    "create_time": item.ozon_product.create_time,
                    "modify_time": item.ozon_product.modify_time,
                    "system_products":[
                        {
                            "id": system_products_msg.system_product.id,
                            "primary_image": system_products_msg.system_product.primary_image,
                            "system_sku": system_products_msg.system_product.system_sku,
                            "reference_weight": system_products_msg.system_product.reference_weight,
                            "reference_cost": system_products_msg.system_product.reference_cost,
                            "purchase_link": system_products_msg.system_product.purchase_link,
                            "supplier_name": system_products_msg.system_product.supplier_name,
                            "purchase_platform": system_products_msg.system_product.purchase_platform,
                            "creator": {"id":system_products_msg.system_product.creator_id, "name":system_products_msg.system_product.creator.username},
                            "create_time": system_products_msg.system_product.create_time,
                            "modify_time": system_products_msg.system_product.modify_time,
                            "quantity":system_products_msg.quantity,
                            "wait_for_purchase_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                            "in_basket_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                            "in_transit_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                            "stock_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                            "out_stock_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                            "loss_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.loss]),

                        } for system_products_msg in item.ozon_product.system_products_msg
                    ]
                } for item in result.ozon_products_msg
            ]
        } 

        return jsonify({
            "msg":"查询成功！",
            "data":result
        }), 200 
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 401

# 打印运单号
# 系统管理员、部门管理员 和 打包可操作
@ozon_order_list.route('/printThePackageLabel', methods=['POST'])
@jwt_required()
@active_required
def printThePackageLabel():
    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "posting_number" in data:
        posting_number = data['posting_number']
    else:
        return jsonify({"msg":"待打印装运号不能为空！"}),401

    if user:
        if (
            # 系统管理员
            user.is_admin
            # 部门管理员 
            or (user.is_department_admin and user.department)
            # 同部门打包
            or (any(role.id == "3" for role in user.roles))
        ):
            ozon_order = OzonOrder.query.filter_by(posting_number=posting_number).first()

            if ozon_order:

                res = GetPackageLabel(
                    api_id = ozon_order.shop.api_id,
                    api_key = ozon_order.shop.api_key,
                    posting_number = posting_number
                )

                if res["data"]:
                    data = io.BytesIO(res["data"])

                data.seek(0)  # 重置指针位置
                return send_file(data, as_attachment=True, download_name=f"{posting_number}出库单运单号", mimetype="application/pdf")    
                    
        else:
            return jsonify({
                "msg":"无产品国际运单打印权限！",
            }), 400 
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 401 

# 批量打印运单号
# 系统管理员、部门管理员 和 打包可操作
@ozon_order_list.route('/printThePackageLabels', methods=['POST'])
@jwt_required()
@active_required
def printThePackageLabels():
    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "posting_number_msgs" in data:
        posting_number_msgs = data['posting_number_msgs']
    else:
        return jsonify({"msg":"待打印装运号不能为空！"}),401

    if user:
        if (
            # 系统管理员
            user.is_admin
            # 部门管理员 
            or (user.is_department_admin and user.department)
            # 同部门打包
            or (any(role.id == "3" for role in user.roles))
        ):
            
            pdf_merger = PdfMerger()  # 初始化 PDF 合并工具

            for posting_number_msg in posting_number_msgs:
                api_id = posting_number_msg["api_id"]
                api_key = posting_number_msg["api_key"]
                posting_number = posting_number_msg["posting_number"]

                if not (api_id and api_key and posting_number):
                    continue  # 如果信息不完整，跳过此店铺

                res = GetPackageLabel(
                    api_id = api_id,
                    api_key = api_key,
                    posting_number = posting_number
                )

                if res["data"]:
                    pdf_merger.append(io.BytesIO(res["data"]))

            output_pdf = io.BytesIO()
            pdf_merger.write(output_pdf)
            pdf_merger.close()
            output_pdf.seek(0)  # 重置指针位置
            return send_file(output_pdf, as_attachment=True, download_name="ozon出库单运单号列表.pdf", mimetype="application/pdf")    
                    
        else:
            return jsonify({
                "msg":"无产品国际运单打印权限！",
            }), 400 
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 401    

# 订单出库
# 系统管理员、部门管理员 和 打包可操作
@ozon_order_list.route('/dispatchOzonOrder', methods=['POST'])
@jwt_required()
@active_required
def dispatchOzonOrder():
    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "order_id" in data:
        order_id = data['order_id']
    else:
        return jsonify({"msg":"order_id 不能为空！"}),401

    order = OzonOrder.query.filter_by(id=order_id).first()

    if not order:
        return {"msg":"找不到当前订单！"},401

    if user:
        if (
            # 系统管理员
            user.is_admin
            # 部门管理员 
            or (user.is_department_admin and user.department and order.shop.owner.department_id == user.department_id)
            # 同部门打包
            or (any(role.id == "3" for role in user.roles) and order.shop.owner.department_id == user.department_id)
        ):
            
            stock_out_Context = []
            
            # 出库系统内商品
            # for purchase_product in order.purchase_products:
            #     if not (purchase_product.status == PurchaseProductStatus.in_basket or purchase_product.status == PurchaseProductStatus.in_stock):
            #         return {"msg":f'商品 id:{purchase_product.id} sku:{purchase_product.sku} 当前状态为 {purchase_product.status},出库失败！'}, 400
            #     else:
            #         purchase_product.status == PurchaseProductStatus.out_stock
            #         purchase_product.stock_out_date = datetime.now()
            #         stock_out_Context.append(f'出库系统内商品id:{purchase_product.id},sku:{purchase_product.sku}')

            # 检查一下ozon订单关联的采购商品是不是全都出库了
            for purchase_product in order.purchase_products:
                if not purchase_product.status == PurchaseProductStatus.out_stock:
                    return {"msg":f'订单内采购商品 id:{purchase_product.id} sku:{purchase_product.sku} 当前状态为 {purchase_product.status} 订单无法出库！'}, 400

            # 出库ozon订单
            order.system_status = SystemStatus.outwardShippedPendingDispatch
            order.dispatch_time = datetime.now()
            stock_out_Context.append(f'出库ozon订单:{order.id}')

            try:
                db.session.commit()
                operate_log_writer_func(operateType=OperateType.ozonOrder, describe=f"操作人:{user.username}, 操作:订单出库, {stock_out_Context}")
                return {"msg":"订单出库成功！"}, 200  
            except Exception as e:
                return {"msg":"订单出库失败！"}, 400
                    
        else:
            return jsonify({
                "msg":"无该订单出库权限！",
            }), 400 
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 401

# 根据采购产品id 出库采购产品和订单 如果订单只包含这一个产品 直接出库 并打印单子  如果包含多个产品 显示剩余需要出库的产品
# 系统管理员、部门管理员 和 打包可操作
@ozon_order_list.route('/stockOutPurchaseProductWithPurchaseProductId', methods=['POST'])
@jwt_required()
@active_required
def stockOutPurchaseProductWithPurchaseProductId():
    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if current_user:

        if "purchase_product_id" in data:
            purchase_product_id = data['purchase_product_id']
        else:
            return jsonify({"msg":"产品id 不能为空！"}),401

        purchase_product = PurchaseProduct.query.filter_by(id = purchase_product_id).first()

        if purchase_product:
            ozon_order = purchase_product.ozon_order
        else:
            return jsonify({"msg":"找不到对应ID的采购商品！"}),401


        if current_user.is_admin:
            pass
        elif current_user.department and (current_user.is_department_admin or any(role.id == "3" for role in current_user.roles)):
            if current_user.department_id == ozon_order.shop.owner.department_id:
                pass
            else:
                return {"msg":"当前账户无操作权限！"},400
        else:
            return {"msg":"当前账户无操作权限！"},400
        
        
        #  出库采购商品
        if purchase_product.status == PurchaseProductStatus.in_basket or purchase_product.status == PurchaseProductStatus.in_stock:
            purchase_product.status = PurchaseProductStatus.out_stock
        else:
            return {"msg":f"当前采购商品状态{purchase_product.status} 无法出库！"},400

        # 如果这一个ozon订单只包含这一个采购商品，直接出库这个采购订单 返回ozon订单的打印pdf数据
        if len(ozon_order.purchase_products) == 1:
            if ozon_order.system_status == SystemStatus.stockPreparedPendingOutward:
                ozon_order.system_status = SystemStatus.outwardShippedPendingDispatch
                res = GetPackageLabel(
                    api_id = ozon_order.shop.api_id,
                    api_key = ozon_order.shop.api_key,
                    posting_number = ozon_order.posting_number
                )

                if res["data"]:
                    data = io.BytesIO(res["data"])
                    data.seek(0)  # 重置指针位置
                    data = data.getvalue()
                else:
                    return {"msg":f"获取ozon订单{ozon_order.id}面单失败!"}, 400
                try:
                    db.session.commit()
                    operate_log_writer_func(operateType=OperateType.ozonOrder, describe=f"操作人:{current_user.username}, 操作:订单出库, {ozon_order.id}")
                    operate_log_writer_func(operateType=OperateType.purchaseProduct, describe=f"操作人:{current_user.username}, 操作:采购商品出库, {purchase_product.id}")
                    
                    return {
                        "msg": "ozon订单、采购商品出库成功!",
                        "data": base64.b64encode(data).decode('utf-8'),
                        "type": "非组合订单"
                    }, 200  
                except Exception as e:
                    return {"msg": f"订单出库失败！{e}"}, 400
            else:
                return {"msg":f"当前ozon订单状态{ozon_order.system_status} 无法出库！"},400
            

        # 如果这一个ozon订单包含多个采购商品 并返回这个订单相关信息
        else:
            result = ozon_order

            result = {
                "id": result.id,
                "order_id": result.order_id,
                "order_number": result.order_number,
                "posting_number": result.posting_number,
                "posting_status": result.posting_status,
                "logistics_status": result.logistics_status,
                "delivery" : {
                    "delivery_id": result.delivery_id,
                    "delivery_name": result.delivery_name,
                    "delivery_tpl_provider_type": result.delivery_tpl_provider_type,
                    "delivery_tpl_provider_id": result.delivery_tpl_provider_id,
                    "delivery_tpl_provider_name": result.delivery_tpl_provider_name,
                },
                "warehouse_id": result.warehouse_id,
                "warehouse_name": result.warehouse_name,
                "tracking_number": result.tracking_number,
                "customer_id": result.customer_id,
                "customer_name": result.customer_name,
                "address_city": result.address_city,
                "in_process_at": result.in_process_at,
                "shipment_date": result.shipment_date,
                "delivering_date": result.delivering_date,
                "cancel_reason": result.cancel_reason,
                "cancellation_type": result.cancellation_type,
                "currency_code": result.currency_code,
                "total_price": result.total_price,
                "system_status": result.system_status,
                "approval_time": result.approval_time,
                "dispatch_time": result.dispatch_time,
                "shop": {"id":result.shop.id, "name":result.shop.name},
                "owner": {"id":result.shop.owner.id, "name":result.shop.owner.username} if result.shop.owner else None,
                "create_time": result.create_time,
                "modify_time": result.modify_time,
                
                # 对应的采购的商品
                "purchase_products":[
                        {
                            "id": purchase_product.id,
                            "price": purchase_product.price,
                            "stock_in_date": purchase_product.stock_in_date,
                            "sku": purchase_product.sku,
                            "type": purchase_product.type,
                            "status": purchase_product.status,
                            "purchase_order_id": purchase_product.purchase_order_id,
                            "system_product_id": purchase_product.system_product_id,
                            "create_time": purchase_product.create_time,
                            "modify_time": purchase_product.modify_time,
                        } for purchase_product in result.purchase_products
                    ],

                # 对应的ozon商品
                "products":[
                    {
                        "quantity": item.quantity,
                        "real_price":item.price,
                        "id": item.ozon_product.id,
                        "offer_id": item.ozon_product.offer_id,
                        "name": item.ozon_product.name,
                        "price": item.ozon_product.price,
                        "currency_code": item.ozon_product.currency_code,
                        "sku": item.ozon_product.sku,
                        "link": item.ozon_product.link,
                        "mandatory_mark": item.ozon_product.mandatory_mark,
                        "fbo_commission_percent": item.ozon_product.fbo_commission_percent,
                        "fbo_commission_value": item.ozon_product.fbo_commission_value,
                        "fbs_commission_percent": item.ozon_product.fbs_commission_percent,
                        "fbs_commission_value": item.ozon_product.fbs_commission_value,
                        "rfbs_commission_percent": item.ozon_product.rfbs_commission_percent,
                        "rfbs_commission_value": item.ozon_product.rfbs_commission_value,
                        "fbp_commission_percent": item.ozon_product.fbp_commission_percent,
                        "fbp_commission_value": item.ozon_product.fbp_commission_value,
                        "product_id": item.ozon_product.product_id,
                        "create_time": item.ozon_product.create_time,
                        "primary_image":item.ozon_product.primary_image,
                        "category_two_id":item.ozon_product.category_two_id,
                        "category_three_id":item.ozon_product.category_three_id,
                        "create_time": item.ozon_product.create_time,
                        "modify_time": item.ozon_product.modify_time,
                        "system_products":[
                            {
                                "id": system_products_msg.system_product.id,
                                "primary_image": system_products_msg.system_product.primary_image,
                                "system_sku": system_products_msg.system_product.system_sku,
                                "reference_weight": system_products_msg.system_product.reference_weight,
                                "reference_cost": system_products_msg.system_product.reference_cost,
                                "purchase_link": system_products_msg.system_product.purchase_link,
                                "supplier_name": system_products_msg.system_product.supplier_name,
                                "purchase_platform": system_products_msg.system_product.purchase_platform,
                                "creator": {"id":system_products_msg.system_product.creator_id, "name":system_products_msg.system_product.creator.username},
                                "create_time": system_products_msg.system_product.create_time,
                                "modify_time": system_products_msg.system_product.modify_time,
                                "quantity":system_products_msg.quantity,
                                "wait_for_purchase_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                                "in_basket_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                                "in_transit_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                                "stock_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                                "out_stock_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                                "loss_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.loss]),

                            } for system_products_msg in item.ozon_product.system_products_msg
                        ]
                    } for item in result.ozon_products_msg
                ]
            } 

            try:
                db.session.commit()
                operate_log_writer_func(operateType=OperateType.purchaseProduct, describe=f"操作人:{current_user.username}, 操作:采购商品出库, {purchase_product.id}")
                return jsonify({
                    "msg":"采购商品出库成功！",
                    "data":result,
                    "type":"组合订单"
                }), 200 
            except Exception as e:
                return {"msg":"采购商品出库失败！"}, 400
            
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 401
    
# 根据id获取订单数据
# 系统管理员、部门管理员、打包可操作
@ozon_order_list.route('/getDataWithOzonOrderId', methods=['POST'])
@jwt_required()
@active_required
def getDataWithOzonOrderId():
    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if current_user:

        if "ozon_order_id" in data:
            ozon_order_id = data['ozon_order_id']
        else:
            return jsonify({"msg":"订单id 不能为空！"}),401

        ozon_order = OzonOrder.query.filter_by(id = ozon_order_id).first()

        if not ozon_order:
            return jsonify({"msg":"找不到对应的ozon订单！"}),401

        if current_user.is_admin:
            pass
        elif current_user.department and (current_user.is_department_admin or any(role.id == "3" for role in current_user.roles)):
            if current_user.department_id == ozon_order.shop.owner.department_id:
                pass
            else:
                return {"msg":"当前账户无操作权限！"},400
        else:
            return {"msg":"当前账户无操作权限！"},400


        result = ozon_order
        results = {
            "id": result.id,
            "order_id": result.order_id,
            "order_number": result.order_number,
            "posting_number": result.posting_number,
            "posting_status": result.posting_status,
            "logistics_status": result.logistics_status,
            "delivery" : {
                "delivery_id": result.delivery_id,
                "delivery_name": result.delivery_name,
                "delivery_tpl_provider_type": result.delivery_tpl_provider_type,
                "delivery_tpl_provider_id": result.delivery_tpl_provider_id,
                "delivery_tpl_provider_name": result.delivery_tpl_provider_name,
            },
            "warehouse_id": result.warehouse_id,
            "warehouse_name": result.warehouse_name,
            "tracking_number": result.tracking_number,
            "customer_id": result.customer_id,
            "customer_name": result.customer_name,
            "address_city": result.address_city,
            "in_process_at": result.in_process_at,
            "shipment_date": result.shipment_date,
            "delivering_date": result.delivering_date,
            "cancel_reason": result.cancel_reason,
            "cancellation_type": result.cancellation_type,
            "currency_code": result.currency_code,
            "total_price": result.total_price,
            "system_status": result.system_status,
            "approval_time": result.approval_time,
            "dispatch_time": result.dispatch_time,
            "shop": {"id":result.shop.id, "name":result.shop.name},
            "owner": {"id":result.shop.owner.id, "name":result.shop.owner.username} if result.shop.owner else None,
            "create_time": result.create_time,
            "modify_time": result.modify_time,
            
            # 对应的采购的商品
            "purchase_products":[
                {
                    "id": purchase_product.id,
                    "price": purchase_product.price,
                    "stock_in_date": purchase_product.stock_in_date,
                    "sku": purchase_product.sku,
                    "type": purchase_product.type,
                    "status": purchase_product.status,
                    "purchase_order_id": purchase_product.purchase_order_id,
                    "system_product_id": purchase_product.system_product_id,
                    "create_time": purchase_product.create_time,
                    "modify_time": purchase_product.modify_time,
                } for purchase_product in result.purchase_products
            ],

            # 对应的ozon商品
            "products":[
                {
                    "quantity": item.quantity,
                    "real_price":item.price,
                    "id": item.ozon_product.id,
                    "offer_id": item.ozon_product.offer_id,
                    "name": item.ozon_product.name,
                    "price": item.ozon_product.price,
                    "currency_code": item.ozon_product.currency_code,
                    "sku": item.ozon_product.sku,
                    "link": item.ozon_product.link,
                    "mandatory_mark": item.ozon_product.mandatory_mark,
                    "fbo_commission_percent": item.ozon_product.fbo_commission_percent,
                    "fbo_commission_value": item.ozon_product.fbo_commission_value,
                    "fbs_commission_percent": item.ozon_product.fbs_commission_percent,
                    "fbs_commission_value": item.ozon_product.fbs_commission_value,
                    "rfbs_commission_percent": item.ozon_product.rfbs_commission_percent,
                    "rfbs_commission_value": item.ozon_product.rfbs_commission_value,
                    "fbp_commission_percent": item.ozon_product.fbp_commission_percent,
                    "fbp_commission_value": item.ozon_product.fbp_commission_value,
                    "product_id": item.ozon_product.product_id,
                    "create_time": item.ozon_product.create_time,
                    "primary_image":item.ozon_product.primary_image,
                    "category_two_id":item.ozon_product.category_two_id,
                    "category_three_id":item.ozon_product.category_three_id,
                    "create_time": item.ozon_product.create_time,
                    "modify_time": item.ozon_product.modify_time,
                    "system_products":[
                        {
                            "id": system_products_msg.system_product.id,
                            "primary_image": system_products_msg.system_product.primary_image,
                            "system_sku": system_products_msg.system_product.system_sku,
                            "reference_weight": system_products_msg.system_product.reference_weight,
                            "reference_cost": system_products_msg.system_product.reference_cost,
                            "purchase_link": system_products_msg.system_product.purchase_link,
                            "supplier_name": system_products_msg.system_product.supplier_name,
                            "purchase_platform": system_products_msg.system_product.purchase_platform,
                            "creator": {"id":system_products_msg.system_product.creator_id, "name":system_products_msg.system_product.creator.username},
                            "create_time": system_products_msg.system_product.create_time,
                            "modify_time": system_products_msg.system_product.modify_time,
                            "quantity":system_products_msg.quantity,
                            "wait_for_purchase_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                            "in_basket_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                            "in_transit_quantity": len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                            "stock_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                            "out_stock_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                            "loss_quantity":len([item for item in system_products_msg.system_product.purchase_products if item.status == PurchaseProductStatus.loss]),

                        } for system_products_msg in item.ozon_product.system_products_msg
                    ]
                } for item in result.ozon_products_msg
            ]
        } 

        return jsonify({
            "msg":"查询成功！",
            "data":results
        }), 200 
    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 4

# 根据采购产品id 出库采购产品和订单 如果订单只包含这一个产品 直接出库  如果包含多个产品 显示剩余需要出库的产品
# 系统管理员、部门管理员 和 打包可操作
@ozon_order_list.route('/stockOutPurchaseProductInOzonOrder', methods=['POST'])
@jwt_required()
@active_required
def stockOutPurchaseProductInOzonOrder():
    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if current_user:

        if "purchase_product_id" in data:
            purchase_product_id = data['purchase_product_id']
        else:
            return jsonify({"msg":"产品id 不能为空！"}),401

        purchase_product = PurchaseProduct.query.filter_by(id = purchase_product_id).first()

        if purchase_product:
            ozon_order = purchase_product.ozon_order
        else:
            return jsonify({"msg":"找不到对应ID的采购商品！"}),401
        
        if "ozon_order_id" in data:
            ozon_order_id = data['ozon_order_id']
            if not ozon_order_id == ozon_order.id:
                return jsonify({"msg":f"传入的采购商品id{purchase_product_id}对应的ozon订单与传入的ozon_order_id不符！"}),400
        else:
            return jsonify({"msg":"ozon订单id 不能为空！"}),401


        if current_user.is_admin:
            pass
        elif current_user.department and (current_user.is_department_admin or any(role.id == "3" for role in current_user.roles)):
            if current_user.department_id == ozon_order.shop.owner.department_id:
                pass
            else:
                return {"msg":"当前账户无操作权限！"},400
        else:
            return {"msg":"当前账户无操作权限！"},400
        
        
        #  出库采购商品
        if purchase_product.status == PurchaseProductStatus.in_basket or purchase_product.status == PurchaseProductStatus.in_stock:
            purchase_product.status = PurchaseProductStatus.out_stock
        else:
            return {"msg":f"当前采购商品状态{purchase_product.status} 无法出库！"},400

        # 判断这个订单绑定的其他商品是否全部都出库了 如果全部都出库了 返回ozon订单的打印pdf数据
        changeOzonOrder = False

        if all(item.status == PurchaseProductStatus.out_stock  for item in ozon_order.purchase_products):
            if ozon_order.system_status == SystemStatus.stockPreparedPendingOutward:
                ozon_order.system_status = SystemStatus.outwardShippedPendingDispatch
                res = GetPackageLabel(
                    api_id = ozon_order.shop.api_id,
                    api_key = ozon_order.shop.api_key,
                    posting_number = ozon_order.posting_number
                )

                if res["data"]:
                    data = io.BytesIO(res["data"])
                    data.seek(0)  # 重置指针位置
                    data = data.getvalue()
                else:
                    return {"msg":f"获取ozon订单{ozon_order.id}面单失败!"}, 400
                
                changeOzonOrder = True
            else:
                return {"msg":f"当前ozon订单状态{ozon_order.system_status} 无法出库！"},400

        try:
            db.session.commit()
            if changeOzonOrder:
                operate_log_writer_func(operateType=OperateType.ozonOrder, describe=f"操作人:{current_user.username}, 操作:订单出库, {ozon_order.id}")
                operate_log_writer_func(operateType=OperateType.purchaseProduct, describe=f"操作人:{current_user.username}, 操作:采购商品出库, {purchase_product.id}")
                return {
                    "msg": "ozon订单、采购商品出库成功!",
                    "data": base64.b64encode(data).decode('utf-8')
                }, 200  
            else:
                operate_log_writer_func(operateType=OperateType.purchaseProduct, describe=f"操作人:{current_user.username}, 操作:采购商品出库, {purchase_product.id}")
                return {
                    "msg": "采购商品出库成功！",
                    "data":None
                }, 200  
        except Exception as e:
            return {"msg":"出库失败！"}, 400
    else:
       return jsonify({
            "msg":"未找到对应用户！",
        }), 401