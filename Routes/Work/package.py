'''
author:AHAO
createTime:2024/05/30 8:56
description: 刀具CRUD接口
'''

from flask import Blueprint,jsonify,request
from Models import db
import uuid
from flask_jwt_extended import jwt_required,get_jwt
from sqlalchemy import or_
import datetime
import base64


from Utils.crud import getDataFromDataBase_BaseData,addDataFromDataBase,modifyDataFromDataBase,deleteDataFromDataBase
from Utils.apiRightsDecorator import admin_required,operations_required,active_required
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType
from Utils.purchase_product_label_print import generate_qrcodes_package_pdf

from Models.User.user_model import User
from Models.Work.package_model import Package



package_list = Blueprint('package', __name__, url_prefix='/package')

# 查询数据
@package_list.route('/getData', methods=['GET'])
@jwt_required()
@active_required
def getData():

    start = int(request.args.get('start', 0))
    limit = int(request.args.get('limit', 10))
    keyWord = str(request.args.get('keyWord', None))

    current_user = get_jwt()
    user = User.query.filter_by(id=current_user['id']).first()

    if keyWord:
        columns = [column.name for column in Package.__table__.columns ]
        filters = [getattr(Package, col).like(f'%{keyWord}%') for col in columns]
        query = Package.query.filter(or_(*filters))
    else:
        query = Package.query

    results = query.order_by(Package.create_time).offset(start).limit(limit).all()
    results = [{
       "id": result.id,
       "sku": result.sku,
       
       "create_time": result.create_time,
       "modify_time": result.modify_time,
       "purchase_products":[
           {
               "id": item.id,
               "price": item.price,
               "stock_in_date": item.stock_in_date,
               "stock_out_date": item.stock_out_date,
               "sku": item.sku,
               "type": item.type,
               "status": item.status,
           }  for item in result.purchase_products
       ],
       "creator": {"id":result.creator.id,"name":result.creator.username} if result.creator else {}
    } for result in results]

    return jsonify({
        "msg":"查询成功！",
        "data":{
            "data":results,
            "count":len(results)
        }
    }), 200 


# 管理员新增数据
@package_list.route('/addData', methods=['POST'])
@jwt_required()
@active_required
def addData():
    current_user = get_jwt()

    package = Package()
    package.id = str(uuid.uuid1())
    package.creator_id = current_user["id"]

    front_name = f"汇利-{datetime.datetime.now().strftime('%Y-%m-%d')}"

    results = Package.query.filter(
        Package.sku.ilike(f"%{front_name}%")
    ).all()

    package.sku = f"{front_name}-{len(results)+1}"
    
    try:
        db.session.add_all([package])
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.package,describe=f"操作人:{current_user['username']}, 操作:新增麻袋, id:{package.id} sku:{package.sku}")
        return {"msg":"新增成功！","sku":package.sku}, 200  
    except Exception as e:
        return {"msg":"新增失败！"}, 400 


# 管理员删除数据
@package_list.route('/deleteData', methods=['POST'])
@jwt_required()
@admin_required
@active_required
def deleteData():
    return deleteDataFromDataBase(Package,OperateType.package)

# 打印麻袋标签
@package_list.route('/printPackage', methods=['POST'])
@jwt_required()
@active_required
def printPackage():

    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "package_sku" in data:
        package_sku = data['package_sku']
    else:
        return jsonify({"msg":"麻袋sku 不能为空！"}),401

    if package_sku:
        package = Package.query.filter_by(sku = package_sku).first()

        if not package:
            return jsonify({"msg":"找不到对应sku的麻袋！"}),401
    else:
        package = None

    if package:
        pdf_byte_arr = generate_qrcodes_package_pdf([{"id":package.id,"sku":package.sku}])

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.package, describe=f"操作人:{current_user.username}, 操作:打印打包袋{package_sku}标签成功！")
        return jsonify({
            "msg":f"打印打包袋{package_sku}标签成功！",
            "data": base64.b64encode(pdf_byte_arr).decode('utf-8') if package else None
        }), 200
    except Exception as e:
        operate_log_writer_func(operateType=OperateType.package, describe=f"操作人:{current_user.username}, 操作:打印打包袋{package_sku}标签失败！, 报错：{e}")
        return {"msg":f"打印打包袋{package_sku}标签失败！"}, 400