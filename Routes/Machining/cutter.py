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

from Models.Machining.cutter_model import Cutter 
from Models.Machining.device_model import Device
from Models.Machining.kinematic_pair_model import KinematicPair
from Models.Machining.machining_features_model import MachiningFeatures
from Models.Machining.size_parameters_model import SizeParameters
from Models.Machining.process_parameters_model import ProcessParameters
from Models.Machining.material_model import Material


cutter_list = Blueprint('cutter', __name__, url_prefix='/cutter')

# 无登陆都可以查到总数据  # 登陆后 都可以看到详情页
# 只有登陆后有某个领域权限的专家 才能新增该领域菜单下的工艺卡片（其他库只有管理员能新增）

# 查询数据
@cutter_list.route('/getData', methods=['GET'])
@jwt_required()
def getData():

    # 可填写字段 start(从第几个数据开始，默认0) 
    # limit(取多少条，默认10) 
    # keyWord(模糊查询关键字 可以不传)
    return getDataFromDataBase_BaseData(Cutter)


# 新增数据
@cutter_list.route('/addData', methods=['POST'])
@jwt_required()
def addData():

    # 可填写字段 name label mark (含义查询cutter类)
    return addDataFromDataBase(Cutter) 


# 修改数据
@cutter_list.route('/modifyData', methods=['POST'])
@jwt_required()
def modifyData(): 

    # 可填写字段 id name label mark
    return modifyDataFromDataBase(Cutter)


# 删除数据
@cutter_list.route('/deleteData', methods=['POST'])
@jwt_required()
def deleteData():

    # 可填写字段 id
    return deleteDataFromDataBase(Cutter)



