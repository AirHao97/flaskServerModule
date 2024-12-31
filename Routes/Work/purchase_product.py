'''
author: AHAO
createTime: 2024/12/04 8:15
description: 采购商品接口
'''

from flask import Blueprint,jsonify,request
from Models import db
import uuid
from flask_jwt_extended import jwt_required,get_jwt
from sqlalchemy import or_,and_, cast, Integer
import json
import datetime
import random
import base64

from Utils.crud import getDataFromDataBase_BaseData,addDataFromDataBase,modifyDataFromDataBase,deleteDataFromDataBase
from Utils.apiRightsDecorator import admin_required,operations_required,active_required
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType
from Utils.Constant.purchaseProductStatus import PurchaseProductStatus
from Utils.Constant.purchaseProductType import PurchaseProductType
from Utils.purchase_product_label_print import generate_qrcodes_pdf


from Models.Work.system_product_model import SystemProduct
from Models.Work.purchase_product_model import PurchaseProduct
from Models.User.user_model import User
from Utils.Constant.purchaseProductStatus import PurchaseProductStatus

purchase_product_list = Blueprint('purchase_product', __name__, url_prefix='/purchase_product')


# 查询全部的采购商品数据
# 系统管理员、部门管理员、小组管理员 和 采购可操作
@purchase_product_list.route('/getData', methods=['GET'])
@jwt_required()
@active_required
def getData():
    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:
        start = int(request.args.get('start', 0))
        limit = int(request.args.get('limit', 10))
        keyWord = str(request.args.get('keyWord', None))

        if keyWord:
            columns = [column.name for column in PurchaseProduct.__table__.columns ]
            filters = [getattr(PurchaseProduct, col).like(f'%{keyWord}%') for col in columns]
            query = PurchaseProduct.query.filter(or_(*filters))
        else:
            query = PurchaseProduct.query

        if not current_user.is_admin:
            if not (current_user.is_department_admin):
                if not (current_user.is_team_admin):
                    if not any(role.id == "2" for role in current_user.roles):
                        return {"msg":"当前账户无操作权限！"},400

        results = query.order_by(PurchaseProduct.create_time).offset(start).limit(limit).all()
        count = query.order_by(PurchaseProduct.create_time).count()
            
        results = {
            "data" :[
            {
                "id": result.id,
                "price": result.price,
                "stock_in_date": result.stock_in_date,
                "stock_out_date": result.stock_out_date,

                "stock_in_person": {"id":result.stock_in_person.id,"username":result.stock_in_person.username } if result.stock_in_person else None,
                "stock_out_person": {"id":result.stock_out_person.id,"username":result.stock_out_person.username } if result.stock_out_person else None,

                "loss_date": result.loss_date,
                "sku": result.sku,
                "type": result.type,
                "status": result.status,
                "mark": result.mark,
                "purchase_order_id": result.purchase_order_id,
                "ozon_order_id": result.ozon_order_id,
                "system_product_id": result.system_product_id,
                "package_id": result.package_id,

                "create_time": result.create_time,
                "modify_time": result.modify_time,


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

# 新增数据
# 系统管理员、部门管理员、小组管理员 和 运营可操作
@purchase_product_list.route('/addData', methods=['POST'])
@jwt_required()
@active_required
def addData():
    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()
    data = request.get_json()

    if not current_user.is_admin:
        if not (current_user.is_department_admin and current_user.department):
            if not (current_user.is_team_admin and current_user.team):
                if not any(role.id == "2" for role in current_user.roles):
                    return {"msg":"当前账户无操作权限！"},400

    modifyContext = []
    
    if "price" in data:
        modifyContext.append(f"采购商品价格:({data['price']})")
        price = data["price"]
    else:
        return {"msg":"采购商品价格不能为空！"},400

    if "system_product_id" in data:
        modifyContext.append(f"采购商品对应的系统内商品id:({data['system_product_id']})")
        system_product_id = data['system_product_id']
        
        system_product = SystemProduct.query.filter_by(id = system_product_id).first()

        if not system_product:
            return {"msg":"找不到对应id的系统内商品！"},401

    else:
        return {"msg":"采购商品对应的系统内商品id不能为空！"},400

    purchase_product = PurchaseProduct()
    purchase_product.id = str(uuid.uuid1())
    purchase_product.sku = system_product.system_sku + "-" + str(random.randint(1000000, 9999999))
    purchase_product.price = price
    purchase_product.system_product_id = system_product_id
    purchase_product.stock_in_date = datetime.datetime.now()
    purchase_product.status = PurchaseProductStatus.in_stock
    purchase_product.type = PurchaseProductType.unmatched
        
    try:
        db.session.add_all([purchase_product])
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseProduct, describe=f"操作人:{current_user.username}, 操作:新增采购商品, id:{purchase_product.id}, 新增内容：{modifyContext}")
        return {"msg":"采购商品新增成功！"}, 200
    except Exception as e:
        return {"msg":"采购商品新增失败！"}, 400

# 手动修改采购订单的信息
# 系统管理员、部门管理员 和 采购 可操作
@purchase_product_list.route('/modifyData', methods=['POST'])
@jwt_required()
@active_required
def modifyData(): 
    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "id" in data:
        purchase_product_id = data['id']
    else:
        return jsonify({"msg":"id 不能为空！"}),401
    
    purchase_product = PurchaseProduct.query.filter_by(id = purchase_product_id).first()

    if not purchase_product:
        return {"msg":f"找不到id为{purchase_product_id}的采购产品！"},401
    
    # 权限校验
    if not current_user.is_admin:
        if not (current_user.is_department_admin and purchase_product.purchase_order.department_id == current_user.department_id):
            if not (any(role.id == "2" for role in current_user.roles) and purchase_product.purchase_order.department_id == current_user.department_id):
                return {"msg":"当前账户无操作权限！"},400
    
    modifyContext = []

    if "price" in data:
        modifyContext.append(f"价格:({purchase_product.price} -> {data['price']})")
        purchase_product.price = data['price']
    if "sku" in data:
        modifyContext.append(f"sku:({purchase_product.sku} -> {data['sku']})")
        purchase_product.sku = data['sku']
    if "type" in data:
        modifyContext.append(f"订单类型:({purchase_product.type} -> {data['type']})")
        purchase_product.type = data['type']
    if "status" in data:
        modifyContext.append(f"采购商品状态:({purchase_product.status} -> {data['status']})")
        purchase_product.status = data['status']
        if purchase_product.status == PurchaseProductStatus.loss:
            purchase_product.mark = ""
    if "mark" in data:
        if purchase_product.status == PurchaseProductStatus.loss:
            modifyContext.append(f"丢失件备注:({purchase_product.mark} -> {data['mark']})")
            purchase_product.mark = data['mark']
        else:
            if data['mark']:
                return {"msg": f"采购商品{purchase_product.id} 状态为{purchase_product.status} 无法更新丢失件备注！"}, 400

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseProduct,describe=f"操作人:{current_user.username}, 操作:修改信息 id:{purchase_product.id}, 修改内容：{modifyContext}")
        return {"msg":"采购订单信息修改成功！"}, 200  
    except Exception as e:
        return {"msg":"采购订单信息修改失败！"}, 400
    
# 采购产品出库
# 系统管理员、部门管理员 和 打包 可操作
@purchase_product_list.route('/dispatchThePurchaseProduct', methods=['POST'])
@jwt_required()
@active_required
def dispatchThePurchaseProduct():

    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if not current_user.is_admin:
        if not (current_user.is_department_admin):
            if not any(role.id == "3" for role in current_user.roles):
                return {"msg":"当前账户无操作权限！"},400
        
    data = request.get_json()

    if "purchase_product_id" in data:
        purchase_product_id = data['purchase_product_id']
    else:
        return jsonify({"msg":"purchase_product_id 不能为空！"}),401
    
    purchase_product = PurchaseProduct.query.filter_by(id = purchase_product_id).all()

    if not purchase_product:
        return {"msg":"找不到指定的采购商品！"},401
    else:
        purchase_product.status = PurchaseProductStatus.out_stock
    

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseProduct, describe=f"操作人:{current_user.username}, 操作:采购商品出库, id:{purchase_product.id}")
        return jsonify({
            "msg":"采购商品出库成功！"
        }), 200
    except Exception as e:
        operate_log_writer_func(operateType=OperateType.purchaseProduct, describe=f"操作人:{current_user.username}, 操作:采购商品出库, id:{purchase_product.id}, 报错：{e}")
        return {"msg":"采购商品出库失败！"}, 400

# 获取入库历史
# 系统管理员、部门管理员 和 打包 可操作
@purchase_product_list.route('/getDataInStockHistrory', methods=['GET'])
@jwt_required()
@active_required
def getDataInStockHistrory():
    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:
        start = int(request.args.get('start', 0))
        limit = int(request.args.get('limit', 10))
        keyWord = str(request.args.get('keyWord', None))

        if keyWord:
            columns = [column.name for column in PurchaseProduct.__table__.columns ]
            filters = [getattr(PurchaseProduct, col).like(f'%{keyWord}%') for col in columns]
            query = PurchaseProduct.query.filter(or_(*filters))
        else:
            query = PurchaseProduct.query
        
        query = query.filter(
            or_(
                PurchaseProduct.status == PurchaseProductStatus.in_stock,
                PurchaseProduct.status == PurchaseProductStatus.in_basket,
                PurchaseProduct.status == PurchaseProductStatus.wait_for_back,
                PurchaseProduct.status == PurchaseProductStatus.out_stock
            )
        )

        if current_user.is_admin:
            pass
        elif current_user.department and  current_user.is_department_admin:                
            query = query.join(User,User.id == PurchaseProduct.stock_in_id).filter(User.department_id == current_user.department_id)
        elif any(role.id == "3" for role in current_user.roles):
            query = query.join(User,User.id == PurchaseProduct.stock_in_id).filter(User.id == current_user.id)
        else:
            return {"msg":"当前账户无操作权限！"},400


        results = query.order_by(PurchaseProduct.stock_in_date.desc()).offset(start).limit(limit).all()
        count = query.order_by(PurchaseProduct.create_time).count()
            
        results = {
            "data" :[
            {
                "id": result.id,
                "price": result.price,
                "stock_in_date": result.stock_in_date,
                "stock_out_date": result.stock_out_date,

                "stock_in_person": {"id":result.stock_in_person.id,"username":result.stock_in_person.username } if result.stock_in_person else None,
                "stock_out_person": {"id":result.stock_out_person.id,"username":result.stock_out_person.username } if result.stock_out_person else None,

                "loss_date": result.loss_date,
                "sku": result.sku,
                "type": result.type,
                "status": result.status,
                "mark": result.mark,
                "purchase_order_id": result.purchase_order_id,
                "ozon_order_id": result.ozon_order_id,
                "system_product_id": result.system_product_id,
                "package_id": result.package_id,

                "create_time": result.create_time,
                "modify_time": result.modify_time,


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

# 获取出库历史
# 系统管理员、部门管理员 和 打包 可操作
@purchase_product_list.route('/getDataOutStockHistrory', methods=['GET'])
@jwt_required()
@active_required
def getDataOutStockHistrory():
    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:
        start = int(request.args.get('start', 0))
        limit = int(request.args.get('limit', 10))
        keyWord = str(request.args.get('keyWord', None))

        if keyWord:
            columns = [column.name for column in PurchaseProduct.__table__.columns ]
            filters = [getattr(PurchaseProduct, col).like(f'%{keyWord}%') for col in columns]
            query = PurchaseProduct.query.filter(or_(*filters))
        else:
            query = PurchaseProduct.query
        
        query = query.filter_by(status = PurchaseProductStatus.out_stock)

        if current_user.is_admin:
            pass
        elif current_user.department and  current_user.is_department_admin:                
            query = query.join(User,User.id == PurchaseProduct.stock_out_id).filter(User.department_id == current_user.department_id)
        elif any(role.id == "3" for role in current_user.roles):
            query = query.join(User,User.id == PurchaseProduct.stock_out_id).filter(User.id == current_user.id)
        else:
            return {"msg":"当前账户无操作权限！"},400


        results = query.order_by(PurchaseProduct.stock_out_date.desc()).offset(start).limit(limit).all()
        count = query.order_by(PurchaseProduct.create_time).count()
            
        results = {
            "data" :[
            {
                "id": result.id,
                "price": result.price,
                "stock_in_date": result.stock_in_date,
                "stock_out_date": result.stock_out_date,

                "stock_in_person": {"id":result.stock_in_person.id,"username":result.stock_in_person.username } if result.stock_in_person else None,
                "stock_out_person": {"id":result.stock_out_person.id,"username":result.stock_out_person.username } if result.stock_out_person else None,

                "loss_date": result.loss_date,
                "sku": result.sku,
                "type": result.type,
                "status": result.status,
                "mark": result.mark,
                "purchase_order_id": result.purchase_order_id,
                "ozon_order_id": result.ozon_order_id,
                "system_product_id": result.system_product_id,
                "package_id": result.package_id,

                "create_time": result.create_time,
                "modify_time": result.modify_time,


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
    
# 打印采购产品单
# 系统管理员、部门管理员 和 打包 可操作
@purchase_product_list.route('/printThePurchaseProduct', methods=['POST'])
@jwt_required()
@active_required
def printThePurchaseProduct():

    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if not current_user.is_admin:
        if not (current_user.is_department_admin):
            if not any(role.id == "3" for role in current_user.roles):
                return {"msg":"当前账户无操作权限！"},400
        
    data = request.get_json()

    if "purchase_product_id" in data:
        purchase_product_id = data['purchase_product_id']
    else:
        return jsonify({"msg":"purchase_product_id 不能为空！"}),401
    
    purchase_product = PurchaseProduct.query.filter_by(id = purchase_product_id).first()

    products = []

    if not purchase_product:
        return {"msg":"找不到指定的采购商品！"},401
    else:
        products.append(
            {
                'id': purchase_product.id,
                'sku': purchase_product.sku,
                'price': purchase_product.price,
                'product_type': purchase_product.type,
                'stock_in_date': purchase_product.stock_in_date
            }
        )

        pdf_byte_arr = generate_qrcodes_pdf(products)

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseProduct, describe=f"操作人:{current_user.username}, 操作:打印采购商品入库单, id:{purchase_product.id}")
        return jsonify({
                "msg":f"采购订单{purchase_product.id}打印入库单成功！",
                "data": base64.b64encode(pdf_byte_arr).decode('utf-8') if products else None
            }), 200
    except Exception as e:
        operate_log_writer_func(operateType=OperateType.purchaseProduct, describe=f"操作人:{current_user.username}, 操作:打印采购商品入库单, id:{purchase_product.id}, 报错：{e}")
        return {"msg":f"采购商品出库采购订单{purchase_product.id}打印入库单失败！","data":None}, 400