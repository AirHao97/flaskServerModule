'''
author:AHAO
createTime:2024/05/30 8:56
description: 刀具CRUD接口
'''

from flask import Blueprint,jsonify,request
from Models import db
import uuid
from flask_jwt_extended import jwt_required,get_jwt_identity
from sqlalchemy import or_,and_, cast, Integer
import json

from Utils.crud import getDataFromDataBase_BaseData,addDataFromDataBase,modifyDataFromDataBase,deleteDataFromDataBase
from Utils.apiRightsDecorator import admin_required,operations_required,active_required
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType
from Utils.Constant.purchaseProductStatus import PurchaseProductStatus

from Models.Work.system_product_model import SystemProduct
from Models.Work.ozon_product_model import OzonProduct 
from Models.User.user_model import User

system_product_list = Blueprint('system_product', __name__, url_prefix='/system_product')

# 查询全部的产品数据
# 系统管理员、部门管理员、小组管理员 和 运营可操作
@system_product_list.route('/getData', methods=['GET'])
@jwt_required()
@active_required
def getData():
    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:
        start = int(request.args.get('start', 0))
        limit = int(request.args.get('limit', 10))
        keyWord = str(request.args.get('keyWord', None))

        if keyWord:
            columns = [column.name for column in SystemProduct.__table__.columns ]
            filters = [getattr(SystemProduct, col).like(f'%{keyWord}%') for col in columns]
            query = SystemProduct.query.filter(or_(*filters))
        else:
            query = SystemProduct.query

        if not current_user.is_admin:
            if not (current_user.is_department_admin):
                if not (current_user.is_team_admin):
                    if not any(role.id == "1" for role in current_user.roles):
                        return {"msg":"当前账户无操作权限！"},400

        results = query.order_by(SystemProduct.create_time).offset(start).limit(limit).all()
        count = query.order_by(SystemProduct.create_time).count()
            
        results = {
            "data" :[
            {

                "id": result.id,
                "primary_image": result.primary_image,
                "system_sku": result.system_sku,
                "reference_weight": result.reference_weight,
                "reference_cost": result.reference_cost,
                "purchase_link": result.purchase_link,
                "supplier_name": result.supplier_name,
                "purchase_platform": result.purchase_platform,
                "creator": {"id":result.creator_id, "name":result.creator.username},
                "create_time": result.create_time,
                "wait_for_purchase_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.wait_purchase]),
                "in_basket_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_basket]),
                "in_transit_quantity": len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_transit]),
                "stock_quantity":len([item for item in result.purchase_products if item.status == PurchaseProductStatus.in_stock]),
                "out_stock_quantity":len([item for item in result.purchase_products if item.status == PurchaseProductStatus.out_stock]),
                "loss_quantity":len([item for item in result.purchase_products if item.status == PurchaseProductStatus.loss]),
                "father_id": result.father_id,

                "productId_1688": result.productId_1688,
                "specId_1688": result.specId_1688,
                "skuId_1688": result.skuId_1688,
                
                "ozon_products":[
                    {
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

                        "shop": {"id":item.ozon_product.shop.id, "name":item.ozon_product.shop.name} if item.ozon_product.shop else {"id":"", "name":""},
                        "create_time": item.ozon_product.create_time,
                    } for item in result.ozon_products_msg
                ],

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

# 新增数据
# 系统管理员、部门管理员、小组管理员 和 运营可操作
@system_product_list.route('/addData', methods=['POST'])
@jwt_required()
@active_required
def addData():
    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()
    data = request.get_json()

    if not current_user.is_admin:
        if not (current_user.is_department_admin and current_user.department):
            if not (current_user.is_team_admin and current_user.team):
                if not any(role.id == "1" for role in current_user.roles):
                    return {"msg":"当前账户无操作权限！"},400

    modifyContext = []


    if "primary_image" in data:
        modifyContext.append(f"商品主图:{data['primary_image']})")
    else:
        return {"msg":"商品主图不能为空！"},400

    if "system_skus" in data:
        modifyContext.append(f"系统sku:({data['system_skus']})")
        system_skus = data['system_skus']
    else:
        return {"msg":"属性集不能为空！"},400
    
    if "reference_weight" in data:
        modifyContext.append(f"参考重量:({data['reference_weight']})")
    else:
        return {"msg":"参考重量不能为空！"},400
    
    if "reference_cost" in data:
        modifyContext.append(f"参考价格:({data['reference_cost']})")
    else:
        return {"msg":"参考价格不能为空！"},400
    
    if "purchase_link" in data:
        modifyContext.append(f"采购链接:({data['purchase_link']})")
    else:
        return {"msg":"采购链接不能为空！"},400
    
    if "purchase_platform" in data:
        modifyContext.append(f"商品采购平台:({data['purchase_platform']})")
    else:
        return {"msg":"商品采购平台不能为空！"},400
    
    if "supplier_name" in data:
        supplier_name = data["supplier_name"]
    else:
        supplier_name = "其他"
    
    modifyContext.append(f"供应商名称:({supplier_name})")

    if "productId_1688" in data:
        productId_1688 = data["productId_1688"]
    else:
        productId_1688 = ""
    modifyContext.append(f"productId_1688:({productId_1688})")

    if "specId_1688" in data:
        specId_1688 = data["specId_1688"]
    else:
        specId_1688 = ""
    modifyContext.append(f"specId_1688:({specId_1688})")

    if "skuId_1688" in data:
        skuId_1688 = data["skuId_1688"]
    else:
        skuId_1688 = ""
    modifyContext.append(f"skuId_1688:({skuId_1688})")
    
    if "sku_front" in data:
        modifyContext.append(f"系统sku前缀:({data['sku_front']})")
        sku_front = data['sku_front']
    else:
        return {"msg":"sku前缀不能为空！"},400


    if not current_user.department_id:
        return {"msg":"当前新建系统内产品用户 部门不能为空！"},400 

    system_products = []

    father_id = str(uuid.uuid1())
    for system_sku in system_skus:
        system_product = SystemProduct()
        system_products.append(system_product)
        system_product.id = str(uuid.uuid1())
        system_product.father_id = father_id
        system_product.creator_id = current_user.id
        modifyContext.append(f"商品id:{system_product.id})")

        system_product.system_sku = f"{sku_front}-{system_sku}"
        system_product.primary_image = data['primary_image']
        system_product.reference_weight = data['reference_weight']
        system_product.reference_cost = data['reference_cost']
        system_product.purchase_link = data['purchase_link']

        if supplier_name:
            system_product.supplier_name = supplier_name
        if productId_1688:
            system_product.productId_1688 = productId_1688
        if specId_1688:
            system_product.specId_1688 = specId_1688
        if skuId_1688:
            system_product.skuId_1688 = skuId_1688

        system_product.purchase_platform = data['purchase_platform']
        system_product.department_id = current_user.department_id
        
    try:
        db.session.add_all(system_products)
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.systemProduct, describe=f"操作人:{current_user.username}, 操作:新增系统内商品, id:{system_product.id}, 新增内容：{modifyContext}")
        return {"msg":"系统内商品新建成功！"}, 200
    except Exception as e:
        return {"msg":"系统内商品新建失败！"}, 400

# 新增数据
# 系统管理员、部门管理员、小组管理员 和 运营可操作
@system_product_list.route('/addDataWith1688Data', methods=['POST'])
@jwt_required()
@active_required
def addDataWith1688Data():
    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()
    data = request.get_json()

    if not current_user.is_admin:
        if not (current_user.is_department_admin and current_user.department):
            if not (current_user.is_team_admin and current_user.team):
                if not any(role.id == "1" for role in current_user.roles):
                    return {"msg":"当前账户无操作权限！"},400

    modifyContext = []

    
    if "reference_weight" in data:
        modifyContext.append(f"参考重量:({data['reference_weight']})")
    else:
        return {"msg":"参考重量不能为空！"},400
    
    if "reference_cost" in data:
        modifyContext.append(f"参考价格:({data['reference_cost']})")
    else:
        return {"msg":"参考价格不能为空！"},400
    
    if "purchase_link" in data:
        modifyContext.append(f"采购链接:({data['purchase_link']})")
    else:
        return {"msg":"采购链接不能为空！"},400
    
    if "purchase_platform" in data:
        modifyContext.append(f"商品采购平台:({data['purchase_platform']})")
    else:
        return {"msg":"商品采购平台不能为空！"},400
    
    if "supplier_name" in data:
        modifyContext.append(f"供应商名称:({data['supplier_name']})")
    else:
        return {"msg":"供应商名称不能为空！"},400
    
    if "sku_front_name" in data:
        modifyContext.append(f"系统sku前缀:({data['sku_front_name']})")
        sku_front_name = data['sku_front_name']
    else:
        return {"msg":"sku前缀不能为空！"},400
    
    if "products" in data:
        modifyContext.append(f"1688商品数据:({data['products']})")
        products = data['products']
    else:
        return {"msg":"sku前缀不能为空！"},400


    if not current_user.department_id:
        return {"msg":"当前新建系统内产品用户 部门不能为空！"},400 

    system_products = []

    father_id = str(uuid.uuid1())

    for product in products:
        system_product = SystemProduct()
        system_products.append(system_product)
        system_product.id = str(uuid.uuid1())
        system_product.father_id = father_id
        
        system_product.creator_id = current_user.id
        modifyContext.append(f"商品id:{system_product.id})")

        system_product.system_sku = f"{sku_front_name}-{product['attr']}"
        system_product.primary_image = product["imageUrl"]
        system_product.reference_weight = data['reference_weight']
        system_product.reference_cost = data['reference_cost']
        system_product.purchase_link = data['purchase_link']


        system_product.supplier_name = data['supplier_name']
        system_product.productId_1688 = product["productId"]
        system_product.specId_1688 = product["specId"]
        system_product.skuId_1688 = product["skuId"]

        system_product.purchase_platform = data['purchase_platform']
        system_product.department_id = current_user.department_id
        
    try:
        db.session.add_all(system_products)
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.systemProduct, describe=f"操作人:{current_user.username}, 操作:新增系统内商品, id:{system_product.id}, 新增内容：{modifyContext}")
        return {"msg":"系统内商品新建成功！"}, 200
    except Exception as e:
        return {"msg":"系统内商品新建失败！"}, 400
    
# 修改的系统内商品数据
# 系统管理员、部门管理员、小组管理员 和 运营可操作
# 系统管理员可修改全部数据
# 部门管理员可以修改本部门数据
# 小组管理员可以修改本小组数据
# 运营只能修改自己创建的和被授权的下的数据
@system_product_list.route('/modifyData', methods=['POST'])
@jwt_required()
@active_required
def modifyData():
    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()

    if not user:
        return {"msg":"找不到指定用户！"},401
        
    data = request.get_json()

    if "id" in data:
        system_product_id = data['id']
    else:
        return jsonify({"msg":"id 不能为空！"}),401

    system_product = SystemProduct.query.filter_by(id=system_product_id).first()

    if not system_product:
        return {"msg":f"找不到id为{system_product_id}的产品！"},401

    if (
        # 系统管理员
        user.is_admin
        # 部门管理员 
        or (user.is_department_admin and user.department and system_product.creator.department_id == user.department_id)
        # 小组管理员
        or (user.is_team_admin and user.team and system_product.creator.team_id == user.team_id)
        # ozon产品属于运营自己
        or (any(role.id == "1" for role in user.roles) and user.id == system_product.creator.id)
        # 当前账户属于 ozon产品的店铺的管理者的产品关联关系伙伴
        or (any(user.id == partner_system_products.id for partner_system_products in system_product.creator.partners_system_products))
    ):
        modifyContext = []

        if "primary_image" in data:
            modifyContext.append(f"商品主图:({system_product.primary_image} -> {data['primary_image']})")
            system_product.primary_image = data['primary_image']
        
        if "system_sku" in data:
            modifyContext.append(f"系统sku:({system_product.system_sku} -> {data['system_sku']})")
            system_product.system_sku = data['system_sku']
        
        if "reference_weight" in data:
            modifyContext.append(f"参考重量:({system_product.reference_weight} -> {data['reference_weight']})")
            system_product.reference_weight = data['reference_weight']
        
        if "reference_cost" in data:
            modifyContext.append(f"参考价格:({system_product.reference_cost} -> {data['reference_cost']})")
            system_product.reference_cost = data['reference_cost']
        
        if "purchase_link" in data:
            modifyContext.append(f"采购链接:({system_product.purchase_link} -> {data['purchase_link']})")
            system_product.purchase_link = data['purchase_link']

        if "purchase_platform" in data:
            modifyContext.append(f"商品采购平台:({system_product.purchase_platform} -> {data['purchase_platform']})")
            system_product.purchase_platform = data['purchase_platform']        

        if "supplier_name" in data:
            modifyContext.append(f"供应商名称:({system_product.supplier_name} -> {data['supplier_name']})")
            system_product.supplier_name = data['supplier_name']

        if "productId_1688" in data:
            modifyContext.append(f"1688产品ID:({system_product.productId_1688} -> {data['productId_1688']})")
            system_product.productId_1688 = data['productId_1688']

        if "specId_1688" in data:
            modifyContext.append(f"1688样式ID:({system_product.specId_1688} -> {data['specId_1688']})")
            system_product.specId_1688 = data['specId_1688']

        if "skuId_1688" in data:
            modifyContext.append(f"1688SKU:({system_product.skuId_1688} -> {data['skuId_1688']})")
            system_product.skuId_1688 = data['skuId_1688']
        
        if "is_all" in data:
            if data["is_all"]:
                modifyContext.append("同步修改采购平台、供应商名称、采购链接、参考重量、参考价格信息与同批次系统内商品")

                father_id = system_product.father_id

                system_products = SystemProduct.query.filter_by(father_id=father_id).all()
                
                
                for item in system_products:
                    word = f"修改变体{item.id}"

                    word += f"{item.reference_weight} -> {data['reference_weight']}"
                    item.reference_weight = data["reference_weight"]

                    word += f"{item.reference_cost} -> {data['reference_cost']}"
                    item.reference_cost = data["reference_cost"]

                    word += f"{item.purchase_platform} -> {data['purchase_platform']}"
                    item.purchase_platform = data["purchase_platform"]

                    word += f"{item.supplier_name} -> {data['supplier_name']}"
                    item.supplier_name = data["supplier_name"]

                    word += f"{item.purchase_link} -> {data['purchase_link']}"
                    item.purchase_link = data["purchase_link"]

                    modifyContext.append(word)

        try:
            db.session.commit()
            operate_log_writer_func(operateType=OperateType.ozonProduct,describe=f"操作人:{user.username}, 操作:修改信息 id:{system_product.id}, 修改内容：{modifyContext}")
            return {"msg":"系统内商品信息修改成功！"}, 200  
        except Exception as e:
            return {"msg":"系统内商品信息修改失败！"}, 400
    else:
        return {"msg":"当前账户无操作权限！"},400 


# 系统管理员、部门管理员、小组管理员 和 运营可操作
# 系统管理员可删除全部数据
# 部门管理员可以删除本部门数据
# 小组管理员可以删除本小组数据
# 运营只能删除自己创建的和被授权的下的数据
@system_product_list.route('/deleteData', methods=['POST'])
@jwt_required()
@active_required
def deleteData():
    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()

    if not user:
        return {"msg":"找不到指定用户！"},401
        
    data = request.get_json()

    if "system_product_id" in data:
        system_product_id = data['system_product_id']
    else:
        return jsonify({"msg":"system_product_id 不能为空！"}),400

    system_product = SystemProduct.query.filter_by(id=system_product_id).first()

    if not system_product:
        return {"msg":"找不到指定的system_product"},401

    if (
        # 系统管理员
        user.is_admin
        # 部门管理员 
        or (user.is_department_admin and user.department and system_product.creator.department_id == user.department_id)
        # 小组管理员
        or (user.is_team_admin and user.team and system_product.creator.team_id == user.team_id)
        # ozon产品属于运营自己
        or (any(role.id == "1" for role in user.roles) and user.id == system_product.creator.id)
        # 当前账户属于 ozon产品的店铺的管理者的产品关联关系伙伴
        or (any(user.id == partner_system_products.id for partner_system_products in system_product.creator.partners_system_products))
    ):
        if system_product.purchase_products:
            return jsonify({"msg":f"当前系统内商品{system_product.id} 已经绑定了采购商品，无法删除！"}),400

        try:
            db.session.delete(system_product)
            db.session.commit()
            operate_log_writer_func(operateType=OperateType.systemProduct,describe=f"操作人:{user.username}, 操作:删除数据, id:{system_product_id}")
            return {"msg":"删除成功！"}, 200  
        except Exception as e:
            print(e)
            return {"msg":"删除失败！"}, 400 
    else:
        return {"msg":"当前账户无操作权限！"},400
