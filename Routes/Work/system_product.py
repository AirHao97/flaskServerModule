'''
author:AHAO
createTime:2024/05/30 8:56
description: 刀具CRUD接口
'''

from flask import Blueprint,jsonify,request
from Models import db
import uuid
from flask_jwt_extended import jwt_required,get_jwt_identity
from sqlalchemy import or_
import json

from Utils.crud import getDataFromDataBase_BaseData,addDataFromDataBase,modifyDataFromDataBase,deleteDataFromDataBase
from Utils.apiRightsDecorator import admin_required,operations_required,active_required
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType
from Utils.API_1688 import get_supplier_name

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
            columns = [column.name for column in SystemProduct.__table__.columns if column.name != 'id']
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
                "purchase_mark": result.purchase_mark,
                "pack_mark": result.pack_mark,
                "purchase_link": result.purchase_link,
                "supplier_name": result.supplier_name,
                "stock_quantity": result.stock_quantity,
                "omitted_quantity": result.omitted_quantity,
                "in_transit_quantity": result.in_transit_quantity,
                "purchase_platform": result.purchase_platform,
                "creator": {"id":result.creator_id, "name":result.creator.username},
                "create_time": result.create_time,
                
                "ozon_products":[
                    {
                        "id": item.id,
                        "offer_id": item.offer_id,
                        "name": item.name,
                        "price": item.price,
                        "currency_code": item.currency_code,
                        "sku": item.sku,
                        
                        "link": item.link,
                        "mandatory_mark": item.mandatory_mark,
                        "primary_image": item.primary_image,
                        "product_id": item.product_id,

                        "shop": {"id":item.shop.id, "name":item.shop.name},
                        "create_time": item.create_time,
                    } for item in result.ozon_products
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

    def is_integer_value(value):
        if isinstance(value, int):
            return True
        elif isinstance(value, str) and value.isdigit():
            return True
        else:
            return False

    if "system_skus" in data:
        modifyContext.append(f"系统sku:({data['system_skus']})")
        system_skus = data['system_skus']
    else:
        return {"msg":"属性集不能为空！"},400
    
    supplier_name = None

    if "primary_image" in data:
        modifyContext.append(f"商品主图:{data['primary_image']})")
    else:
        return {"msg":"商品主图不能为空！"},400
    
    if "reference_weight" in data:
        modifyContext.append(f"参考重量:({data['reference_weight']})")
    else:
        return {"msg":"参考重量不能为空！"},400
    
    if "reference_cost" in data:
        modifyContext.append(f"参考价格:({data['reference_cost']})")
    else:
        return {"msg":"参考价格不能为空！"},400
    
    if "purchase_mark" in data:
        modifyContext.append(f"采购备注:({data['purchase_mark']})")
    else:
        return {"msg":"采购备注不能为空！"},400
    
    if "pack_mark" in data:
        modifyContext.append(f"打包备注:({data['pack_mark']})")
    else:
        return {"msg":"打包备注不能为空！"},400
    
    if "purchase_link" in data:
        modifyContext.append(f"采购链接:({data['purchase_link']})")
        try:
            pruchase_link_list = json.load(data['purchase_link'])
            supplier_name = get_supplier_name(url = pruchase_link_list[0])
        except:
            supplier_name = "其他"
        if supplier_name:
            modifyContext.append(f"供应商名称:({supplier_name})")
    else:
        return {"msg":"采购链接不能为空！"},400

    if "stock_quantity" in data:
        modifyContext.append(f"库存量:({data['stock_quantity']})")
        if not is_integer_value(data['stock_quantity']):
            return {"msg":"库存量必须为整数！"},400
    else:
        return {"msg":"库存量不能为空！"},400
        
    if "omitted_quantity" in data:
        modifyContext.append(f"缺货量:({data['omitted_quantity']})")
        if not is_integer_value(data['omitted_quantity']):
            return {"msg":"缺货量必须为整数！"},400
    else:
        return {"msg":"缺货量不能为空！"},400
        
    if "in_transit_quantity" in data:
        modifyContext.append(f"在途量:({data['in_transit_quantity']})")
        if not is_integer_value(data['in_transit_quantity']):
            return {"msg":"在途量必须为整数！"},400
    else:
        return {"msg":"在途量不能为空！"},400
        
    if "purchase_platform" in data:
        modifyContext.append(f"商品采购平台:({data['purchase_platform']})")
    else:
        return {"msg":"商品采购平台不能为空！"},400
    

    system_products = []

    for system_sku in system_skus:
        system_product = SystemProduct()
        system_products.append(system_product)
        system_product.id = str(uuid.uuid1())
        system_product.creator_id = current_user.id
        modifyContext.append(f"商品id:{system_product.id})")

        system_product.system_sku = system_sku
        system_product.primary_image = data['primary_image']
        system_product.reference_weight = data['reference_weight']
        system_product.reference_cost = data['reference_cost']
        system_product.purchase_mark = data['purchase_mark']
        system_product.pack_mark = data['pack_mark']
        system_product.purchase_link = data['purchase_link']

        if supplier_name:
            system_product.supplier_name = supplier_name

        system_product.stock_quantity = data['stock_quantity']
        system_product.omitted_quantity = data['omitted_quantity']
        system_product.in_transit_quantity = data['in_transit_quantity']
        system_product.purchase_platform = data['purchase_platform']

        
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
        jsonify({"msg":"id 不能为空！"}),401

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
        if "purchase_mark" in data:
            modifyContext.append(f"采购备注:({system_product.purchase_mark} -> {data['purchase_mark']})")
            system_product.purchase_mark = data['purchase_mark']
        if "pack_mark" in data:
            modifyContext.append(f"打包备注:({system_product.pack_mark} -> {data['pack_mark']})")
            system_product.pack_mark = data['pack_mark']
        if "purchase_link" in data:
            modifyContext.append(f"采购链接:({system_product.purchase_link} -> {data['purchase_link']})")
            system_product.purchase_link = data['purchase_link']

        if "supplier_name" in data:
            modifyContext.append(f"供应商名称:({system_product.supplier_name} -> {data['supplier_name']})")
            system_product.supplier_name = data['supplier_name']
            # try:
            #     pruchase_link_list = json.load(data['purchase_link'])
            #     supplier_name = get_supplier_name(url = pruchase_link_list[0])
            # except:
            #     supplier_name = None
            # if supplier_name:
            #     modifyContext.append(f"供应商名称:({system_product.supplier_name} -> {supplier_name})")
            #     system_product.supplier_name = supplier_name

        if "stock_quantity" in data:
            modifyContext.append(f"库存量:({system_product.stock_quantity} -> {data['stock_quantity']})")
            system_product.stock_quantity = data['stock_quantity']
        if "omitted_quantity" in data:
            modifyContext.append(f"缺货量:({system_product.omitted_quantity} -> {data['omitted_quantity']})")
            system_product.omitted_quantity = data['omitted_quantity']
        if "in_transit_quantity" in data:
            modifyContext.append(f"在途量:({system_product.in_transit_quantity} -> {data['in_transit_quantity']})")
            system_product.in_transit_quantity = data['in_transit_quantity']
        if "purchase_platform" in data:
            modifyContext.append(f"商品采购平台:({system_product.purchase_platform} -> {data['purchase_platform']})")
            system_product.purchase_platform = data['purchase_platform']

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
        jsonify({"msg":"system_product_id 不能为空！"}),401

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

# 产品出库
# 系统管理员、部门管理员 和 打包 可操作
@system_product_list.route('/dispatchTheSystemProduct', methods=['POST'])
@jwt_required()
@active_required
def dispatchTheSystemProduct():

    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if not current_user.is_admin:
        if not (current_user.is_department_admin):
            if not any(role.id == "3" for role in current_user.roles):
                return {"msg":"当前账户无操作权限！"},400
        
    data = request.get_json()

    if "system_product_id" in data:
        system_product_id = data['system_product_id']
    else:
        jsonify({"msg":"system_product_id 不能为空！"}),401
    
    system_product = SystemProduct.query.filter_by(id = system_product_id).all()

    if not system_product:
        return {"msg":"找不到指定的system_product"},401
    
    stock_quantity = int(system_product.stock_quantity) - 1

    if stock_quantity < 0:
        return jsonify({
            "msg":"出库后,产品库存数量小于0,请检查产品库存数量是否正确！"
        }), 200
    
    system_product.stock_quantity = stock_quantity

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:系统内产品出库, id:{system_product.id}")
        return jsonify({
            "msg":"产品出库成功！"
        }), 200
    except Exception as e:
        operate_log_writer_func(operateType=OperateType.purchaseOrder, describe=f"操作人:{current_user.username}, 操作:系统内产品出库, id:{system_product.id}, 报错：{e}")
        return {"msg":"产品出库失败！"}, 400

