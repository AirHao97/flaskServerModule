'''
author:AHAO
createTime:2024/10/23 14:32
description: 采购订单接口
'''

from flask import Blueprint,jsonify,request
from Models import db
import uuid
from flask_jwt_extended import jwt_required,get_jwt_identity
from sqlalchemy import or_


from Utils.crud import getDataFromDataBase_BaseData,addDataFromDataBase,modifyDataFromDataBase,deleteDataFromDataBase
from Utils.apiRightsDecorator import admin_required,operations_required,active_required
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType
from Utils.Constant.purchaseStatus import PurchaseStatus
from Utils.Constant.systemStatus import SystemStatus

from Models.Work.purchase_order_model import PurchaseOrder
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

    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:
        start = int(request.args.get('start', 0))
        limit = int(request.args.get('limit', 10))
        keyWord = str(request.args.get('keyWord', None))
        purchase_platform = str(request.args.get('purchase_platform',None))
        status = str(request.args.get('status',None))

        if keyWord:
            columns = [column.name for column in PurchaseOrder.__table__.columns if column.name != 'id']
            filters = [getattr(PurchaseOrder, col).like(f'%{keyWord}%') for col in columns]
            query = PurchaseOrder.query.filter(or_(*filters))
        else:
            query = PurchaseOrder.query

        if status:
            if status == "全部":
                pass
            else:
               query = query.filter_by(status=status)
        
        if purchase_platform:
            query = query.filter_by(purchase_platform=purchase_platform)
        else:
            return {"msg":"平台选择不能为空！"},400

        if current_user.is_admin:
            pass
        elif current_user.department and (current_user.is_department_admin or any(role.id == "4" for role in current_user.roles)):
            query = query.filter_by("department_id" == current_user.department_id)
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
                "quantity":result.quantity,
                "order_id": result.order_id,
                "posting_numbers": result.posting_numbers,
                "logistics_status": result.logistics_status,
                "purchase_platform": result.purchase_platform,
                "status": result.status,
                
                "system_product": {
                    "id": result.system_product.id,
                    "primary_image": result.system_product.primary_image,
                    "system_sku": result.system_product.system_sku,
                    "reference_weight": result.system_product.reference_weight,
                    "reference_cost": result.system_product.reference_cost,
                    "purchase_mark": result.system_product.purchase_mark,
                    "pack_mark": result.system_product.pack_mark,
                    "purchase_link": result.system_product.purchase_link,
                    "supplier_name": result.system_product.supplier_name,
                    "stock_quantity": result.system_product.stock_quantity,
                    "omitted_quantity": result.system_product.omitted_quantity,
                    "in_transit_quantity": result.system_product.in_transit_quantity,
                    "purchase_platform": result.system_product.purchase_platform,
                    "create_time": result.system_product.create_time,
                } if  result.system_product  else None
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

# 获取待采购订单的供应商列表
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/getWaitForPurchaseOrderSupplier', methods=['GET'])
@jwt_required()
@active_required
def getWaitForPurchaseOrderSupplier():

    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:

        if current_user.is_admin:
            pass
        elif current_user.department and (current_user.is_department_admin or any(role.id == "4" for role in current_user.roles)):
            query = query.filter_by("department_id" == current_user.department_id)
        else:
            return {"msg":"当前账户无操作权限！"},400

        purchase_platform = str(request.args.get('purchase_platform',None))

        if purchase_platform == "None":
            return jsonify({"msg":"平台选项不能为空！"}),401

        supplier_names = (
            db.session.query(SystemProduct.supplier_name)
            .join(PurchaseOrder, PurchaseOrder.system_product_id == SystemProduct.id)
            .filter(
                PurchaseOrder.purchase_platform == purchase_platform,
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

    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:

        if current_user.is_admin:
            pass
        elif current_user.department and (current_user.is_department_admin or any(role.id == "4" for role in current_user.roles)):
            query = query.filter_by("department_id" == current_user.department_id)
        else:
            return {"msg":"当前账户无操作权限！"},400


        purchase_platform = str(request.args.get('purchase_platform',None))
        supplier_name =  str(request.args.get('supplier_name',None))

        if purchase_platform == "None":
            return jsonify({"msg":"平台选项不能为空！"}),401
        
        if supplier_name == "None":
            return jsonify({"msg":"供应商名字不能为空！"}),401


        query = PurchaseOrder.query.filter_by(purchase_platform = purchase_platform).join(SystemProduct,PurchaseOrder.system_product_id == SystemProduct.id).filter(SystemProduct.supplier_name == supplier_name)

        results = query.order_by(PurchaseOrder.create_time).all()
        count = query.order_by(PurchaseOrder.create_time).count()
            
        results = {
            "data" :[
            {

                "id": result.id,
                "purchase_id": result.purchase_id,
                "price": result.price,
                "quantity":result.quantity,
                "order_id": result.order_id,
                "posting_numbers": result.posting_numbers,
                "logistics_status": result.logistics_status,
                "purchase_platform": result.purchase_platform,
                "status": result.status,
                
                "system_product": {
                    "id": result.system_product.id,
                    "primary_image": result.system_product.primary_image,
                    "system_sku": result.system_product.system_sku,
                    "reference_weight": result.system_product.reference_weight,
                    "reference_cost": result.system_product.reference_cost,
                    "purchase_mark": result.system_product.purchase_mark,
                    "pack_mark": result.system_product.pack_mark,
                    "purchase_link": result.system_product.purchase_link,
                    "supplier_name": result.system_product.supplier_name,
                    "stock_quantity": result.system_product.stock_quantity,
                    "omitted_quantity": result.system_product.omitted_quantity,
                    "in_transit_quantity": result.system_product.in_transit_quantity,
                    "purchase_platform": result.system_product.purchase_platform,
                    "create_time": result.system_product.create_time,
                } if  result.system_product  else None
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
# 尚未出库的ozon订单  包含的产品 - 库存 - 在途 = 需要采购
@purchase_order_list.route('/updateData', methods=['POST'])
@jwt_required()
@active_required
def updateData():
    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:
        if current_user.is_admin:
            # 未出库ozon订单
            ozon_orders = OzonOrder.query.filter_by(dispatch_time = None).all()
            # 已有的待采购采购单
            purchase_orders_query = PurchaseOrder.query.filter_by(status = PurchaseStatus.waitForPurchase)
        elif current_user.department and (current_user.is_department_admin or any(role.id == "4" for role in current_user.roles)):
            ozon_orders = OzonOrder.query.filter_by(dispatch_time = None).join(Shop, OzonOrder.shop_id == Shop.id).join(User,Shop.owner_id == User.id).filter(User.department_id == current_user.department_id).all()
            # 已有的待采购采购单
            purchase_orders_query = PurchaseOrder.query.filter_by(status = PurchaseStatus.waitForPurchase, department_id = current_user.department_id)
        else:
            return {"msg":"当前账户无操作权限！"},400
        
        
        # 更新当前未出库订单每个产品需要的数量
        need_system_product_msg = {}

        for ozon_order in ozon_orders:
            
            for ozon_products_msg in ozon_order.ozon_products_msg:
                quantity = int(ozon_products_msg.quantity)
                ozon_product = ozon_products_msg.ozon_product

                for system_product in ozon_product.system_products:
                    if system_product.id in need_system_product_msg:
                        need_system_product_msg[system_product.id]["quantity"] += quantity
                    else:
                        need_system_product_msg[system_product.id] = {"system_product":system_product,"quantity":quantity}

        # 更新采购单
        for system_product_id ,system_product_msg in need_system_product_msg.items():
            
            add_pruchase_orders = []
            
            purchase_order = purchase_orders_query.filter_by(system_product_id = system_product_id).first()
            
            quantity = int(system_product_msg["quantity"]) - int(system_product_msg["system_product"].stock_quantity) - int(system_product_msg["system_product"].in_transit_quantity)
            if quantity < 0:
                print(f"id:{system_product_id} 产品数量足够，无需采购")
                continue

            # 已有采购单 -更新采购单采购数量
            if purchase_order:
                old_quantity = purchase_order.quantity
            # 没有采购单 -生成新采购单
            else:
                purchase_order = PurchaseOrder()
                purchase_order.id = str(uuid.uuid1())
                purchase_order.type = system_product["system_product"].purchase_platform
                purchase_order.status = PurchaseStatus.waitForPurchase
                purchase_order.system_product_id = system_product_id
                purchase_order.department_id = current_user.department_id
                add_pruchase_orders.append(purchase_order)
            
            purchase_order.quantity = str(quantity)
            
            if add_pruchase_orders:
                operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:新增采购单, id:{purchase_order.id}")
            else:
                if old_quantity != quantity:
                    operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:更新采购单, id:{purchase_order.id}, 采购数量:{old_quantity} -> {quantity}")

            try:
                db.session.add_all(add_pruchase_orders)
                db.session.commit()
            except Exception as e:
                operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:更新采购单, id:{purchase_order.id}, 报错：{e}")
                return {"msg":"采购单更新失败！"}, 400
        
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:更新采购单")
        return jsonify({
            "msg":"采购单更新成功！"
        }), 200

    else:
       return jsonify({
                "msg":"未找到对应用户！",
            }), 400 

# 批量给采购订单填写国内运单号
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/fillThePostingNumber', methods=['POST'])
@jwt_required()
@active_required
def fillThePostingNumber(): 
    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if not current_user.is_admin:
        if not (current_user.is_department_admin):
                if not any(role.id == "4" for role in current_user.roles):
                    return {"msg":"当前账户无操作权限！"},400
        
    data = request.get_json()

    if "purchase_order_ids" in data:
        purchase_order_ids = data['purchase_order_ids']
    else:
        return jsonify({"msg":"purchase_order_ids 不能为空！"}),401

    if "posting_number" in data:
        posting_number = data['posting_number']
    else:
        return jsonify({"msg":"posting_number 不能为空！"}),401
    
    purchase_orders = PurchaseOrder.query.filter((PurchaseOrder.id.in_(purchase_order_ids))).all()

    for purchase_order in purchase_orders:
        if not current_user.is_admin:
            if purchase_order.department_id != current_user.department_id:
                return jsonify({"msg": f"采购单{purchase_order.id} 不在当前账号部门！"}),400
        
        # 填写运单号
        purchase_order.posting_number = posting_number
        # 更改采购单状态
        purchase_order.statues = PurchaseStatus.inTransit
        # 采购单内产品 在途量 增加库存
        purchase_order.system_product.in_transit_quantity = str(int(purchase_order.system_product.in_transit_quantity) + int(purchase_order.quantity))
    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:采购单添加国内运单号, ids:{[purchase_order.id for purchase_order in purchase_orders]} 运单号：{posting_number}")
        return jsonify({
            "msg":"采购单添加国内运单号成功！"
        }), 200
    except Exception as e:
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:采购单添加国内运单号, id:{purchase_order.id}, 报错：{e}")
        return {"msg":"采购单添加国内运单号失败！"}, 400

# 手动修改采购订单的信息
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/modifyData', methods=['POST'])
@jwt_required()
@active_required
def modifyData(): 
    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if not current_user.is_admin:
        if not (current_user.is_department_admin):
                if not any(role.id == "4" for role in current_user.roles):
                    return {"msg":"当前账户无操作权限！"},400
        
    data = request.get_json()

    if "id" in data:
        purchase_order_id = data['id']
    else:
        return jsonify({"msg":"id 不能为空！"}),401
    
    purchase_order = PurchaseOrder.query.filter_by(id = purchase_order_id).first()

    if not purchase_order:
        return {"msg":f"找不到id为{purchase_order_id}的产品！"},401
    
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
    if "quantity" in data:
        modifyContext.append(f"采购数量:({purchase_order.quantity} -> {data['quantity']})")
        purchase_order.quantity = data['quantity']
    if "status" in data:
        modifyContext.append(f"采购状态:({purchase_order.status} -> {data['status']})")
        purchase_order.status = data['status']

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseOrder,describe=f"操作人:{current_user.username}, 操作:修改信息 id:{purchase_order.id}, 修改内容：{modifyContext}")
        return {"msg":"采购订单信息修改成功！"}, 200  
    except Exception as e:
        return {"msg":"采购订单信息修改失败！"}, 400
    
# 采购单作废
# 系统管理员、部门管理员 和 采购 可操作
@purchase_order_list.route('/cancleThePurchaseOrder', methods=['POST'])
@jwt_required()
@active_required
def cancleThePostingNumber(): 

    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if not current_user.is_admin:
        if not (current_user.is_department_admin):
                if not any(role.id == "4" for role in current_user.roles):
                    return {"msg":"当前账户无操作权限！"},400
        
    data = request.get_json()

    if "purchase_order_id" in data:
        purchase_order_id = data['purchase_order_id']
    else:
        jsonify({"msg":"purchase_order_id 不能为空！"}),401
    
    purchase_order = PurchaseOrder.query.filter_by(id = purchase_order_id).first()

    if not purchase_order:
        return {"msg":"找不到对应采购订单！"},401

    if not current_user.is_admin:
        if not purchase_order.department_id == current_user.department_id:
            return jsonify({"msg": f"采购单{purchase_order.id} 不在当前账号部门！"}),400
    
    if purchase_order.status == PurchaseStatus.waitForPurchase:
        purchase_order.status = PurchaseStatus.cancelled
    
    elif purchase_order.status == PurchaseStatus.inTransit:
        # 更改采购单状态
        purchase_order.status = PurchaseStatus.cancelled
        # 采购单内产品 在途量 返回库存
        in_transit_quantity = int(purchase_order.system_product.in_transit_quantity) - int(purchase_order.quantity)
        
        if in_transit_quantity < 0:
            return jsonify({
                "msg":"采购订单取消后,产品在途数量小于0,请检查产品在途数量是否正确！"
            }), 200
    
        purchase_order.system_product.in_transit_quantity = in_transit_quantity
    elif purchase_order.status == PurchaseStatus.finished:
        # 更改采购单状态
        purchase_order.status = PurchaseStatus.cancelled
        # 采购单内产品 库存量 返回库存
        stock_quantity = int(purchase_order.system_product.stock_quantity) - int(purchase_order.quantity)
        
        if stock_quantity < 0:
            return jsonify({
                "msg":"采购订单取消后,产品库存数量小于0,请检查产品库存数量是否正确！"
            }), 200
    
        purchase_order.system_product.stock_quantity = stock_quantity
    else:
        return jsonify({
            "msg":"当前订单状态，无法作废！"
        }), 200
    
    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:采购单作废, id:{purchase_order.id}")
        return jsonify({
            "msg":"采购订单作废成功！"
        }), 200
    except Exception as e:
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:采购单作废, id:{purchase_order.id}, 报错：{e}")
        return {"msg":"采购订单作废失败！"}, 400

# 采购单签收 产品入库
# 系统管理员、部门管理员 和 打包 可操作
@purchase_order_list.route('/signThePurchaseOrder', methods=['POST'])
@jwt_required()
@active_required
def signThePurchaseOrder():

    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if not current_user.is_admin:
        if not (current_user.is_department_admin):
            if not any(role.id == "3" for role in current_user.roles):
                return {"msg":"当前账户无操作权限！"},400
        
    data = request.get_json()

    if "posting_number" in data:
        posting_number = data['posting_number']
    else:
        jsonify({"msg":"posting_number 不能为空！"}),401
    
    purchase_orders = PurchaseOrder.query.filter_by(posting_number = posting_number).all()

    if not purchase_orders:
        jsonify({"msg":"无对应当前国内运单号的采购单！请检查运单号输入！"}),401
    
    for purchase_order in purchase_orders:
        
        if not current_user.is_admin:
            if not purchase_order.department_id == current_user.department_id:
                return jsonify({"msg": f"采购单{purchase_order.id} 不在当前账号部门！"}),400
        
        if purchase_order.status == PurchaseStatus.inTransit:
            # 更改采购单状态
            purchase_order.status = PurchaseStatus.finished
            # 采购单内产品 在途量 返回库存
            in_transit_quantity = int(purchase_order.system_product.in_transit_quantity) - int(purchase_order.quantity)
            if in_transit_quantity < 0:
                return jsonify({
                    "msg":"采购订单签收后,产品在途数量小于0,请检查产品在途数量是否正确！"
                }), 200
            purchase_order.system_product.in_transit_quantity = in_transit_quantity
            # 采购单内产品 库存量 返回库存
            stock_quantity = int(purchase_order.system_product.stock_quantity) + int(purchase_order.quantity)
            if stock_quantity < 0:
                return jsonify({
                    "msg":"采购订单签收后,产品库存数量小于0,请检查产品库存数量是否正确！"
                }), 200
        
            purchase_order.system_product.stock_quantity = stock_quantity
        else:
            jsonify({"msg":f"采购订单{purchase_order.id}的状态为{purchase_order.status}，无法签收，请检查采购订单状态！"}),400

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:采购单作废, id:{purchase_order.id}")
        return jsonify({
            "msg":"采购订单签收成功！"
        }), 200
    except Exception as e:
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:采购单作废, id:{purchase_order.id}, 报错：{e}")
        return {"msg":"采购订单签收失败！"}, 400