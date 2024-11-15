'''
author:AHAO
createTime:2024/05/30 8:56
description: 刀具CRUD接口
'''

from flask import Blueprint,jsonify,request,current_app
from Models import db
import uuid
from flask_jwt_extended import jwt_required,get_jwt_identity
from sqlalchemy import or_
from datetime import datetime, timedelta
import time
import threading
from decimal import Decimal, getcontext
import traceback

from Utils.crud import getDataFromDataBase_BaseData,addDataFromDataBase,modifyDataFromDataBase,deleteDataFromDataBase
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.apiRightsDecorator import admin_required,operations_required,active_required
from Utils.ozonAPI import getOrders,orderShip,getProductInfo,getProductAttributes
from Utils.Constant.operateType import OperateType
from Utils.Constant.systemStatus import SystemStatus

from Models.Work.ozon_order_model import OzonOrder,OzonOrderOzonProduct
from Models.Work.ozon_product_model import OzonProduct
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
            three_months_ago = today - timedelta(days=120)
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
                                # ---对应 已作废---
                                elif itemOrders["status"]  == "cancelled":
                                    ozon_order.system_status = SystemStatus.cancelled
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
                                ozon_product.price = itemProduct["price"]
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

                            ozon_order.total_price = float(total_price)

                            try:
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
        return jsonify({"msg": "ozon订单更新正在进行中..."}), 200


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

        if keyWord:
            columns = [column.name for column in OzonOrder.__table__.columns if column.name != 'id']
            filters = [getattr(OzonOrder, col).like(f'%{keyWord}%') for col in columns]
            query = OzonOrder.query.filter(or_(*filters))
        else:
            query = OzonOrder.query

        if system_status:
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
                "shipping_time": result.shipping_time,
                "cancel_time": result.cancel_time,
                "shop": {"id":result.shop.id, "name":result.shop.name},
                "owner": {"id":result.shop.owner.id, "name":result.shop.owner.username} if result.shop.owner else None,
                "creator": {"id":result.creator_id, "name":result.creator.username} if result.creator else None,
                "create_time": result.create_time,
                
                "products":[
                    {
                        "quantity": item.quantity,
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
                        "primary_image":item.ozon_product.primary_image
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
        jsonify({"msg":"posting_number 不能为空！"}),401
    
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
                order.approval_time = datetime.now

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
                            for itemProduct in item["products"]:

                                total_price = total_price + Decimal(itemProduct["price"]) * Decimal(itemProduct["quantity"])
                                ozon_product = OzonProduct.query.filter_by(sku=itemProduct["sku"]).first()                                
                                itemRelation = OzonOrderOzonProduct.query.filter_by(order_id=order.id, product_id=ozon_product.id).first()
                                itemRelation.quantity = itemProduct["quantity"]

                            order.total_price = float(total_price)
                        else:
                            ozon_order = OzonOrder()
                            ozon_order.id = str(uuid.uuid1())
                            ozon_order.posting_number = item["posting_number"]
                            ozon_order.system_status = SystemStatus.reviewedPendingStock
                            ozon_order.approval_time = datetime.now
                            addList_order.append(ozon_order)
                        
                            total_price = Decimal(0.0)

                            for itemProduct in item["products"]:
                                total_price = total_price + Decimal(itemProduct["price"]) * Decimal(itemProduct["quantity"])
                                ozon_product = OzonProduct.query.filter_by(sku=itemProduct["sku"]).first()
                                itemRelation = OzonOrderOzonProduct()

                                itemRelation.order_id = ozon_order.id
                                itemRelation.product_id = ozon_product.id
                                itemRelation.quantity = itemProduct["quantity"]
                                addList_relation.append(itemRelation)

                            order.total_price = float(total_price)
                try:
                    db.session.add_all(addList_order)
                    db.session.add_all(addList_relation)
                    db.session.commit()
                    operate_log_writer_func(operateType=OperateType.ozonOrder, describe=f"操作人:{user.username}, 操作:审核订单, id:{order.id}")
                    return {"msg":"订单审核成功！"}, 200  
                except Exception as e:
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
        jsonify({"msg":"order_id 不能为空！"}),401

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
                operate_log_writer_func(operateType=OperateType.ozonOrder, describe=f"操作人:{user.username}, 操作:作废订单, id:{order.id}")
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
            ozon_orders = OzonOrder.query.filter_by(system_status = SystemStatus.reviewedPendingStock)
        elif (current_user.is_department_admin and current_user.department) or any(role.id == "4" for role in current_user.roles):
            ozon_orders = OzonOrder.query.filter_by(system_status = SystemStatus.createdPendingReview).join(Shop, OzonOrder.shop_id == Shop.id).join(User,Shop.owner_id == User.id).filter(User.department_id == current_user.department_id)
        else:
            return {"msg":"当前账户无操作权限！"},400

        # 已审核待备货 本部门 ozon订单 根据生成时间排序
        ozon_orders = ozon_orders.order_by(OzonOrder.create_time).all()
        
        # 算法生成产品可以满足 同时出库的订单  -按时间顺序从早到晚
        # 获取所有订单中涉及到的产品ID
        ozon_products_ids = set()
        for ozon_order in ozon_orders:
            for ozon_product_msg in ozon_order.ozon_products_msg:
                ozon_products_ids.add(ozon_product_msg.ozon_product.id)

        # 初始化一个全局字典来跟踪产品的虚拟库存量
        inventory = {ozon_product.id: int(ozon_product.stock_quantity) for ozon_product in OzonProduct.query.filter(OzonProduct.id.in_(ozon_products_ids)).all()}
        
        # 检查订单中的所有产品是否有足够的库存量
        def can_fulfill_order(order):
            for ozon_product_msg in order.ozon_products_msg:
                product_id = ozon_product_msg.ozon_product.id
                required_quantity = int(ozon_product_msg.quantity)
                if inventory[product_id] < required_quantity:
                    return False
                # 减少已分配的库存量
                inventory[product_id] -= required_quantity
            return True
        
        # 存储可以同时发货的订单
        results = []

        for ozon_order in ozon_orders:
            if can_fulfill_order(ozon_order):
                results.append(ozon_order)

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
                "shipping_time": result.shipping_time,
                "cancel_time": result.cancel_time,
                "shop": {"id":result.shop.id, "name":result.shop.name},
                "owner": {"id":result.shop.owner.id, "name":result.shop.owner.username} if result.shop.owner else None,
                "creator": {"id":result.creator_id, "name":result.creator.username} if result.creator else None,
                "create_time": result.create_time,
                
                "products":[
                    {
                        "quantity": item.quantity,
                        "id": item.ozon_product.id,
                        "offer_id": item.ozon_product.offer_id,
                        "name": item.ozon_product.name,
                        "price": item.ozon_product.price,
                        "currency_code": item.ozon_product.currency_code,
                        "sku": item.ozon_product.sku,
                        "link": item.ozon_product.link,
                        "mandatory_mark": item.ozon_product.mandatory_mark,
                        "primary_image": item.ozon_product.primary_image,
                        "product_id": item.ozon_product.product_id,
                        "create_time": item.ozon_product.create_time,
                    } for item in result.ozon_products_msg
                ]
            } 
            for result in results],
            "count":len(results)
        }

        return jsonify({
            "msg":"可打包订单生成成功！",
            "data":results
        }), 200 

    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 400 

# 订单出库
# 系统管理员、部门管理员 和 打包可操作
@ozon_order_list.route('/dispatchOrder', methods=['POST'])
@jwt_required()
@active_required
def dispatchOrder():
    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "order_id" in data:
        order_id = data['order_id']
    else:
        jsonify({"msg":"order_id 不能为空！"}),401

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
            order.system_status = SystemStatus.outwardShippedPendingDispatch

            try:
                db.session.commit()
                operate_log_writer_func(operateType=OperateType.ozonOrder, describe=f"操作人:{user.username}, 操作:订单出库, id:{order.id}")
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