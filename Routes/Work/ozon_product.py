'''
author:AHAO
createTime:2024/05/30 8:56
description: 刀具CRUD接口
'''
from flask import Blueprint,jsonify,request,current_app
from Models import db
import uuid
from flask_jwt_extended import jwt_required,get_jwt
from sqlalchemy import or_
import traceback
import threading
from datetime import datetime, timedelta


from Utils.crud import getDataFromDataBase_BaseData,addDataFromDataBase,modifyDataFromDataBase,deleteDataFromDataBase
from Utils.apiRightsDecorator import admin_required,operations_required,active_required
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType
from Utils.Constant.purchaseProductStatus import PurchaseProductStatus
from Utils.ozonAPI import getProductInfo,getProductAttributes

from Models.Work.system_product_model import SystemProduct
from Models.Work.ozon_product_model import OzonProduct 
from Models.Work.ozon_product_model import OzonProductSystemProduct 
from Models.User.user_model import User
from Models.Work.shop_model import Shop

ozon_product_list = Blueprint('ozon_product', __name__, url_prefix='/ozon_product')

updataRunning = False
updataMsg = {
    "msg": "", 
    "updataProgress": {
        "nowUpdata": 0, 
        "allCount": 0, 
    },
    "lastUpdataData": {
        "lastUpdataTime": None
    }
}

# 加载产品具体信息子线程
def updataProductDataThread(app):
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
                        updataMsg["msg"] = f"ozon商品{ozon_product.id}更新失败!错误信息：{e}"
                        operate_log_writer_func(operateType=OperateType.ozonProduct,describe=f"ozon商品{ozon_product.id}更新失败，错误信息：{e}",isSystem=True)
                else:
                    operate_log_writer_func(operateType=OperateType.ozonProduct,describe=f"ozon商品{ozon_product.id}更新失败，错误信息：{result['msg']}",isSystem=True)
                    updataMsg["msg"] = result["msg"]

            updataMsg["msg"] = "ozon商品信息更新完成!"
            updataMsg["lastUpdataData"]["lastUpdataTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")                        
            operate_log_writer_func(operateType=OperateType.ozonProduct,describe=f'ozon商品信息更新完成! 共更新商品数据{updataMsg["updataProgress"]["nowUpdata"]}',isSystem=True)
            updataRunning = False          

        except Exception as e:
            updataRunning = False  
            operate_log_writer_func(operateType=OperateType.ozonOrder,describe=f"ozon产品更新失败,错误信息”：{e}",isSystem=True)
            stack_trace = traceback.format_exc()
            updataMsg["msg"] =  f"ozon商品更新失败,错误信息”：{stack_trace}"
            return

# ozon商品信息加载
# 仅管理员可操作
@ozon_product_list.route('/updataData', methods=['POST'])
@jwt_required()
@active_required
@admin_required
def updataData():
    global updataRunning

    if not updataRunning:
        thread = threading.Thread(target=updataProductDataThread, args=(current_app._get_current_object(),))
        thread.start()
        operate_log_writer_func(operateType=OperateType.ozonOrder,describe="开始加载ozon商品!")
        return jsonify({"msg": "ozon商品信息更新已启动!"}), 200
    else:
        return jsonify({"msg": f"ozon商品信息更新正在进行中... {updataMsg['msg']}"}), 200
    
# 获取当前数据更新进度
# 登陆即可操作
@ozon_product_list.route('/progress', methods=['POST'])
@jwt_required()
@active_required
def getProgress():
    global updataMsg
    return jsonify(updataMsg), 200
    
# 查询全部的产品数据
# 系统管理员、部门管理员、小组管理员 和 运营可操作
# 系统管理员可查询全部数据
# 部门管理员可以查询本部门数据
# 小组管理员可以查询本小组数据
# 运营只能查询自己店铺 和 被授权的下的数据
@ozon_product_list.route('/getData', methods=['GET'])
@jwt_required()
@active_required
def getData():
    current_user = get_jwt()
    user = User.query.filter_by(id=current_user['id']).first()
    if user:
        start = int(request.args.get('start', 0))
        limit = int(request.args.get('limit', 10))
        keyWord = str(request.args.get('keyWord', None))

        if keyWord:
            product_columns = [column.name for column in OzonProduct.__table__.columns ]
            product_filters = [getattr(OzonProduct, col).like(f'%{keyWord}%') for col in product_columns]
            shop_columns = [column.name for column in Shop.__table__.columns]
            shop_filters = [getattr(Shop, col).like(f'%{keyWord}%') for col in shop_columns]

            filters = or_(*product_filters, *shop_filters)

            query = (
                OzonProduct.query
                .outerjoin(Shop, Shop.id == OzonProduct.shop_id)
                .filter(filters)
            )
        else:
            query = OzonProduct.query

        if user.is_admin:
            results = query.order_by(OzonProduct.create_time).offset(start).limit(limit).all()
            count = query.order_by(OzonProduct.create_time).count()
        elif user.is_department_admin and user.department:
            shop_ids = []
            users = User.query.filter_by(department_id = user.department_id).all()
            # 本部门
            for i in users:
                for j in i.owner_shops:
                    shop_ids.append(j.id)
            # 自己关联的
            for i in user.partners_system_products:
                for j in i.owner_shops:
                    shop_ids.append(j.id)
            query = query.filter(OzonProduct.shop_id.in_(shop_ids)).order_by(OzonProduct.create_time)
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
            for i in user.partners_system_products:
                for j in i.owner_shops:
                    shop_ids.append(j.id)
            query = query.filter(OzonProduct.shop_id.in_(shop_ids)).order_by(OzonProduct.create_time)
            results = query.offset(start).limit(limit).all()
            count = query.count()
        else:
            if not any(role.id == "1" for role in user.roles):
                return {"msg":"当前账户无操作权限！"},400
            # 自己店铺下的id
            shop_ids = [item.id for item in user.owner_shops]
            # 可处理订单的关系伙伴下的店铺id
            for i in user.partners_system_products:
                for j in i.owner_shops:
                    shop_ids.append(j.id)
            query = query.filter(OzonProduct.shop_id.in_(shop_ids)).order_by(OzonProduct.create_time)
            results = query.offset(start).limit(limit).all()
            count = query.count()

        results = {
            "data" :[
            {
                "id": result.id,
                "offer_id": result.offer_id,
                "name": result.name,
                "price": result.price,
                "currency_code": result.currency_code,
                "sku": result.sku,
                
                "link": result.link,
                "mandatory_mark": result.mandatory_mark,
                "primary_image": result.primary_image,
                "product_id": result.product_id,
                "fbo_commission_percent": result.fbo_commission_percent,
                "fbo_commission_value": result.fbo_commission_value,
                "fbs_commission_percent": result.fbs_commission_percent,
                "fbs_commission_value": result.fbs_commission_value,
                "rfbs_commission_percent": result.rfbs_commission_percent,
                "rfbs_commission_value": result.rfbs_commission_value,
                "fbp_commission_percent": result.fbp_commission_percent,
                "fbp_commission_value": result.fbp_commission_value,

                "shop": {"id":result.shop.id, "name":result.shop.name},
                "owner": {"id":result.shop.owner.id, "name":result.shop.owner.username} if result.shop.owner else None,
                "create_time": result.create_time,
                
                "system_products":[
                    {
                        "id": item.system_product.id,
                        "primary_image": item.system_product.primary_image,
                        "system_sku": item.system_product.system_sku,
                        "reference_weight": item.system_product.reference_weight,
                        "reference_cost": item.system_product.reference_cost,
                        "purchase_link": item.system_product.purchase_link,
                        "supplier_name": item.system_product.supplier_name,
                        "purchase_platform": item.system_product.purchase_platform,
                        "creator": {"id":item.system_product.creator_id, "name":item.system_product.creator.username},
                        "create_time": item.system_product.create_time,
                        "quantity":item.quantity,
                        "wait_for_purchase_quantity": len([item for item in item.system_product.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                        "in_basket_quantity": len([item for item in item.system_product.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                        "in_transit_quantity": len([item for item in item.system_product.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                        "stock_quantity":len([item for item in item.system_product.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                        "out_stock_quantity":len([item for item in item.system_product.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                        "loss_quantity":len([item for item in item.system_product.purchase_products if item.status == PurchaseProductStatus.loss]),

                    } for item in result.system_products_msg
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

# 给指定的ozon产品绑定系统内 产品
# 系统管理员、部门管理员、小组管理员 和 运营可操作
# 系统管理员可管理全部数据
# 部门管理员可以管理本部门数据
# 小组管理员可以管理本小组数据
# 运营只能管理自己店铺的产品数据 和 被授权 产品管理的人员 店铺下的数据
@ozon_product_list.route('/bindSystemProducts', methods=['POST'])
@jwt_required()
@active_required
def bindSystemProducts():
    current_user = get_jwt()
    user = User.query.filter_by(id=current_user['id']).first()
    
    if not user:
        return {"msg":"找不到指定用户！"},401
        
    data = request.get_json()

    if "ozon_product_id" in data:
        ozon_product_id = data['ozon_product_id']
    else:
        return jsonify({"msg":"ozon_product_id 不能为空！"}),401
    
    if "system_products_msg" in data:
        system_products_msg = data['system_products_msg']
    else:
        return jsonify({"msg":"待绑定的系统内产品信息 不能为空！"}),401
    
    ozon_product = OzonProduct.query.filter_by(id=ozon_product_id).first()
    if not ozon_product:
        return {"msg":"找不到指定的ozon_product"},401

    if (
        # 系统管理员
        user.is_admin
        # 部门管理员 
        or (user.is_department_admin and user.department and ozon_product.shop.owner.department_id == user.department_id)
        # 小组管理员
        or (user.is_team_admin and user.team and ozon_product.shop.owner.team_id == user.team_id)
        # ozon产品属于运营自己
        or (any(role.id == "1" for role in user.roles) and user.id == ozon_product.shop.owner.id)
        # 当前账户属于 ozon产品的店铺的管理者的产品关联关系伙伴
        or (any(user.id == partner_system_products.id for partner_system_products in ozon_product.shop.owner.partners_system_products))
    ):
        
        # 去掉所有原来关联的
        OzonProductSystemProduct.query.filter_by(ozon_product_id=ozon_product_id).delete()

        # 添加新的
        addList_relation = []

        for system_product_msg in system_products_msg:
            system_product = SystemProduct.query.filter_by(id=system_product_msg["id"]).first()

            if not system_product:
                return {"msg":f'找不到对应的系统内产品id={system_product_msg["id"]}！'},400
            
            itemRelation = OzonProductSystemProduct()
            itemRelation.ozon_product_id = ozon_product.id
            itemRelation.system_product_id = system_product_msg["id"]
            addList_relation.append(itemRelation)
            itemRelation.quantity = system_product_msg["quantity"]

        try:
            
            db.session.add_all(addList_relation)
            db.session.commit()
            operate_log_writer_func(operateType=OperateType.ozonProduct,describe=f"操作人:{user.username}, 操作:给ozon商品 id:{ozon_product.id} name:{ozon_product.name} 绑定系统内商品{system_products_msg}")
            return {"msg":"系统内商品绑定成功！"}, 200  
        except Exception as e:
            return {"msg":"系统内商品绑定失败！"}, 400
    else:
        return {"msg":"当前账户无操作权限！"},400 


