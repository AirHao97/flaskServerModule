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


from Utils.crud import getDataFromDataBase_BaseData,addDataFromDataBase,modifyDataFromDataBase,deleteDataFromDataBase
from Utils.apiRightsDecorator import admin_required,operations_required,active_required
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType

from Models.User.user_model import User
from Models.Work.shop_model import Shop 


shop_list = Blueprint('shop', __name__, url_prefix='/shop')

# 店铺数据初始化
@shop_list.route('/initData', methods=['POST'])
def initAdminAccount():

    shop_data = [
        {
            "name":"店铺一号",
            "api_id": "221854",
            "api_key":"48d6d7e7-7842-4f21-a5a2-896dea7cd734"
        },
        {
            "name":"店铺二号",
            "api_id": "767055",
            "api_key":"02c837e4-abfa-4779-ba7b-0cd06a22c058"
        }
    ]
    add_shop_list = []

    for i in shop_data:
        shop= Shop()
        shop.id = str(uuid.uuid1())
        shop.name = i["name"]
        shop.api_id = i["api_id"]
        shop.api_key = i["api_key"]
        add_shop_list.append(shop)
    try:
        db.session.add_all(add_shop_list)
        db.session.commit()
        return jsonify({"msg": "店铺数据初始化成功！"}), 200
    except Exception as e:
        return jsonify({"msg": "已完成初始化，请勿重复操作！"}), 400


# 查询数据
@shop_list.route('/getData', methods=['GET'])
@jwt_required()
@active_required
@admin_required
def getData():

    start = int(request.args.get('start', 0))
    limit = int(request.args.get('limit', 10))
    keyWord = str(request.args.get('keyWord', None))

    current_user = get_jwt()
    user = User.query.filter_by(id=current_user['id']).first()

    if keyWord:
        columns = [column.name for column in Shop.__table__.columns ]
        filters = [getattr(Shop, col).like(f'%{keyWord}%') for col in columns]
        query = Shop.query.filter(or_(*filters))
    else:
        query = Shop.query

    if not user.is_admin:
        query = query.filter_by(owner_id=current_user['id'])

    results = query.order_by(Shop.create_time).offset(start).limit(limit).all()
    results = [{
       "id": result.id,
       "name": result.name,
       "api_id": result.api_id,
       "api_key": result.api_key,
       "create_time": result.create_time,
       "modify_time": result.modify_time,
       "owner": {"id":result.owner.id,"name":result.owner.username} if result.owner else {}
    } for result in results]

    return jsonify({
        "msg":"查询成功！",
        "data":{
            "data":results,
            "count":len(results)
        }
    }), 200 


# 管理员新增数据
@shop_list.route('/addData', methods=['POST'])
@jwt_required()
@admin_required
@active_required
def addData():
    return addDataFromDataBase(Shop,OperateType.shop) 


# 管理员修改数据
@shop_list.route('/modifyData', methods=['POST'])
@jwt_required()
@admin_required
@active_required
def modifyData():

    current_user = get_jwt() 
    user = User.query.filter_by(id=current_user['id']).first()

    if not user:
        return {"msg":"找不到指定用户！"},401
        
    data = request.get_json()

    if "id" in data:
        shop_id = data['id']
    else:
        return jsonify({"msg":"id 不能为空！"}),401

    shop = Shop.query.filter_by(id=shop_id).first()

    if not shop:
        return {"msg":f"找不到id为{shop_id}的店铺！"},401

    if (
        # 系统管理员
        user.is_admin
    ):
        modifyContext = []

        if "api_id" in data:
            modifyContext.append(f"api_id:({shop.api_id} -> {data['api_id']})")
            shop.api_id = data['api_id']
        if "api_key" in data:
            modifyContext.append(f"api_key:({shop.api_key} -> {data['api_key']})")
            shop.api_key = data['api_key']
        if "name" in data:
            modifyContext.append(f"name:({shop.name} -> {data['name']})")
            shop.name = data['name']

        try:
            db.session.commit()
            operate_log_writer_func(operateType=OperateType.shop,describe=f"操作人:{user.username}, 操作:修改信息 id:{shop.id}, 修改内容：{modifyContext}")
            return {"msg":"店铺信息修改成功！"}, 200  
        except Exception as e:
            return {"msg":"店铺信息修改失败！"}, 400
    else:
        return {"msg":"当前账户无操作权限！"},400



# 管理员删除数据
@shop_list.route('/deleteData', methods=['POST'])
@jwt_required()
@admin_required
@active_required
def deleteData():
    return deleteDataFromDataBase(Shop,OperateType.shop)