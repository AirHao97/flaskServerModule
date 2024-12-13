'''
author:AHAO
createTime:2024/06/13 16:46
description: 获取静态资源
'''

from flask import Blueprint,jsonify,request
from Models import db
import uuid
from flask_jwt_extended import jwt_required,get_jwt_identity
from sqlalchemy import or_,desc


from Utils.crud import getDataFromDataBase_BaseData,addDataFromDataBase,modifyDataFromDataBase,deleteDataFromDataBase
from Utils.apiRightsDecorator import admin_required
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType


from Models.Log.operate_log_model import OperateLog 


log_list = Blueprint('log', __name__, url_prefix='/log')

# 查询数据
@log_list.route('/getData', methods=['GET'])
@jwt_required()
@admin_required
def getData():
    # 可填写字段 start(从第几个数据开始，默认0) 
    # limit(取多少条，默认10) 
    # keyWord(模糊查询关键字 可以不传)
    start = int(request.args.get('start', 0))
    limit = int(request.args.get('limit', 10))
    keyWord = str(request.args.get('keyWord', None))

    if keyWord:
        columns = [column.name for column in OperateLog.__table__.columns ]
        filters = [getattr(OperateLog, col).like(f'%{keyWord}%') for col in columns]
        query = OperateLog.query.filter(or_(*filters))
    else:
        query = OperateLog.query

    results = query.order_by(desc(OperateLog.create_time)).offset(start).limit(limit).all()
    results = [{column.name: getattr(result, column.name) for column in OperateLog.__table__.columns} for result in results]

    return jsonify({
        "msg":"查询成功！",
        "data":{
            "data":results,
            "count": query.count()
        }
    }), 200 