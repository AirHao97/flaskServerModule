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

    # 可填写字段 start(从第几个数据开始，默认0) 
    # limit(取多少条，默认10) 
    # keyWord(模糊查询关键字 可以不传)
    return getDataFromDataBase_BaseData(Department)


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
    return modifyDataFromDataBase(Department,OperateType.department)


# 删除数据
@department_list.route('/deleteData', methods=['POST'])
@jwt_required()
@admin_required
def deleteData():
    return deleteDataFromDataBase(Department,OperateType.department)



