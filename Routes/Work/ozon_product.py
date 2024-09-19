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

from Models.Work.ozon_product_model import OzonProduct 


work_ozon_product_list = Blueprint('work_ozon_product', __name__, url_prefix='/work/ozon_product')

# 无登陆都可以查到总数据  # 登陆后 都可以看到详情页
# 只有登陆后有某个领域权限的专家 才能新增该领域菜单下的工艺卡片（其他库只有管理员能新增）

# 查询数据
@work_ozon_product_list.route('/getData', methods=['GET'])
@jwt_required()
def getData():

    # 可填写字段 start(从第几个数据开始，默认0) 
    # limit(取多少条，默认10) 
    # keyWord(模糊查询关键字 可以不传)
    return getDataFromDataBase_BaseData(OzonProduct)


# 新增数据
@work_ozon_product_list.route('/addData', methods=['POST'])
@jwt_required()
def addData():
    return addDataFromDataBase(OzonProduct) 


# 修改数据
@work_ozon_product_list.route('/modifyData', methods=['POST'])
@jwt_required()
def modifyData(): 
    return modifyDataFromDataBase(OzonProduct)


# 删除数据
@work_ozon_product_list.route('/deleteData', methods=['POST'])
@jwt_required()
def deleteData():
    return deleteDataFromDataBase(OzonProduct)



