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


from Models.User.role_model import Role 


role_list = Blueprint('role', __name__, url_prefix='/role')

# 无登陆都可以查到总数据  # 登陆后 都可以看到详情页
# 只有登陆后有某个领域权限的专家 才能新增该领域菜单下的工艺卡片（其他库只有管理员能新增）

# 角色数据初始化
@role_list.route('/initData', methods=['POST'])
def initAdminAccount():

    role_data = ["运营","采购","打包","财务"]
    add_role_list = []

    for index,item in enumerate(role_data):
        if not Role.query.filter_by(name=item).first():
            role= Role()
            role.id = str(index+1)
            role.name = item
            add_role_list.append(role)
    try:
        db.session.add_all(add_role_list)
        db.session.commit()
        return jsonify({"msg": "角色数据初始化成功！"}), 200
    except Exception as e:
        return jsonify({"msg": "已完成初始化，请勿重复操作！"}), 400


# 查询数据
@role_list.route('/getData', methods=['GET'])
@jwt_required()
@admin_required
def getData():

    # 可填写字段 start(从第几个数据开始，默认0) 
    # limit(取多少条，默认10) 
    # keyWord(模糊查询关键字 可以不传)
    return getDataFromDataBase_BaseData(Role)


# 新增数据
@role_list.route('/addData', methods=['POST'])
@jwt_required()
@admin_required
@operate_log_writer_dec(operateType=OperateType.role,describe="新增角色数据")
def addData():
    return addDataFromDataBase(Role,OperateType.role)


# 修改数据
@role_list.route('/modifyData', methods=['POST'])
@jwt_required()
@admin_required
@operate_log_writer_dec(operateType=OperateType.role,describe="修改角色数据")
def modifyData(): 
    return modifyDataFromDataBase(Role,OperateType.role)


# 删除数据
@role_list.route('/deleteData', methods=['POST'])
@jwt_required()
@admin_required
@operate_log_writer_dec(operateType=OperateType.role,describe="删除角色数据")
def deleteData():
    return deleteDataFromDataBase(Role,OperateType.role)



