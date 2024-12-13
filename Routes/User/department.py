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


from Utils.crud import getDataFromDataBase_BaseData,addDataFromDataBase,modifyDataFromDataBase,deleteDataFromDataBase
from Utils.apiRightsDecorator import admin_required
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType

from Models.User.user_model import User
from Models.User.department_model import Department 


department_list = Blueprint('department', __name__, url_prefix='/department')

# 部门数据初始化
@department_list.route('/initData', methods=['POST'])
def initAdminAccount():

    role_data = ["部门1号","部门2号"]
    add_role_list = []

    for i in role_data:
        role= Department()
        role.id = str(uuid.uuid1())
        role.name = i
        add_role_list.append(role)
    try:
        db.session.add_all(add_role_list)
        db.session.commit()
        return jsonify({"msg": "部门数据初始化成功！"}), 200
    except Exception as e:
        return jsonify({"msg": "已完成初始化，请勿重复操作！"}), 400


# 查询数据
@department_list.route('/getData', methods=['GET'])
@jwt_required()
@admin_required
def getData():
    start = int(request.args.get('start', 0))
    limit = int(request.args.get('limit', 10))
    keyWord = str(request.args.get('keyWord', None))

    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()

    if keyWord:
        columns = [column.name for column in Department.__table__.columns ]
        filters = [getattr(Department, col).like(f'%{keyWord}%') for col in columns]
        query = Department.query.filter(or_(*filters))
    else:
        query = Department.query

    if not user.is_admin:
        query = query.filter_by(owner_id=current_user['id'])

    results = query.order_by(Department.create_time).offset(start).limit(limit).all()
    results = [{
       "id": result.id,
       "name": result.name,
       "create_time": result.create_time,
       "modify_time": result.modify_time,
    } for result in results]

    return jsonify({
        "msg":"查询成功！",
        "data":{
            "data":results,
            "count":len(results)
        }
    }), 200 


# 新增数据
@department_list.route('/addData', methods=['POST'])
@jwt_required()
@admin_required
def addData():
    return addDataFromDataBase(Department,OperateType.department) 


# 修改数据
@department_list.route('/modifyData', methods=['POST'])
@jwt_required()
@admin_required
def modifyData(): 
    current_user = get_jwt_identity() 
    user = User.query.filter_by(id=current_user['id']).first()

    if not user:
        return {"msg":"找不到指定用户！"},401
        
    data = request.get_json()

    if "id" in data:
        department_id = data['id']
    else:
        return jsonify({"msg":"id 不能为空！"}),401

    department = Department.query.filter_by(id=department_id).first()

    if not department:
        return {"msg":f"找不到id为{department_id}的部门！"},401

    if (
        # 系统管理员
        user.is_admin
    ):
        modifyContext = []

        if "name" in data:
            modifyContext.append(f"name:({department.name} -> {data['name']})")
            department.name = data['name']

        try:
            db.session.commit()
            operate_log_writer_func(operateType=OperateType.department,describe=f"操作人:{user.username}, 操作:修改信息 id:{department.id}, 修改内容：{modifyContext}")
            return {"msg":"部门信息修改成功！"}, 200  
        except Exception as e:
            return {"msg":"部门信息修改失败！"}, 400
    else:
        return {"msg":"当前账户无操作权限！"},400


# 删除数据
@department_list.route('/deleteData', methods=['POST'])
@jwt_required()
@admin_required
def deleteData():
    return deleteDataFromDataBase(Department,OperateType.department)



