'''
author:AHAO
createTime:2024/06/13 16:46
description: 获取静态资源
'''

from flask import Blueprint,jsonify,request
from Models import db
import uuid
from flask_jwt_extended import jwt_required,get_jwt
from sqlalchemy import or_,desc


from Utils.crud import getDataFromDataBase_BaseData,addDataFromDataBase,modifyDataFromDataBase,deleteDataFromDataBase
from Utils.apiRightsDecorator import admin_required,active_required
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType


from Models.Log.operate_log_model import OperateLog 
from Models.User.user_model import User
from Models.Work.ozon_order_model import OzonOrder
from Models.Work.ozon_product_model import OzonProduct


log_list = Blueprint('log', __name__, url_prefix='/log')


# 查询数据
@log_list.route('/getData', methods=['GET'])
@jwt_required()
@active_required
@admin_required
def getData():
    
    start = int(request.args.get('start', 0))
    limit = int(request.args.get('limit', 10))
    keyWord = request.args.get('keyWord', "")

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

# 普通用户查询数据
@log_list.route('/userGetData', methods=['GET'])
@jwt_required()
@active_required
def userGetData():

    current_user = get_jwt()
    current_user = User.query.filter_by(id=current_user['id']).first()

    # 可填写字段 start(从第几个数据开始，默认0) 
    # limit(取多少条，默认10) 
    # keyWord(模糊查询关键字 可以不传)
    start = int(request.args.get('start', 0))
    limit = int(request.args.get('limit', 10))
    keyWord = request.args.get('keyWord', "")
    ozon_order_id = request.args.get('ozon_order_id', "")
    ozon_product_id = request.args.get('ozon_product_id', "")

    userName = current_user.username
    id = current_user.id


    if keyWord:
        columns = [column.name for column in OperateLog.__table__.columns ]
        filters = [getattr(OperateLog, col).like(f'%{keyWord}%') for col in columns]
        query = OperateLog.query.filter(or_(*filters))
    else:
        query = OperateLog.query

    if ozon_order_id or ozon_product_id:
        
        if ozon_order_id:

            ozon_order = OzonOrder.query.filter_by(id = ozon_order_id).first()

            if not ozon_order:
                return {"msg":f"找不到ID{ozon_order_id} 对应的ozon订单！"},401
            if current_user.is_admin:
                pass
            elif current_user.is_department_admin and current_user.department:
                if not ozon_order.shop.owner.department_id == current_user.department.id:
                    return {"msg":"当前账户无操作权限！"},400
                
            elif any(role.id == "1" for role in current_user.roles):
                if not ozon_order.shop.owner.id == current_user.id:
                    return {"msg":"当前账户无操作权限！"},400
            else:
                return {"msg":"当前账户无操作权限！"},400
            
            columns = [column.name for column in OperateLog.__table__.columns ]
            filters = [getattr(OperateLog, col).like(f'%{ozon_order_id}%') for col in columns]
            query = query.filter(or_(*filters))
        
        if ozon_product_id:

            ozon_product = OzonProduct.query.filter_by(id = ozon_product_id).first()

            if not ozon_product:
                return {"msg":f"找不到ID{ozon_product} 对应的ozon商品！"},401
            
            if current_user.is_admin:
                pass
            elif current_user.is_department_admin and current_user.department:
                if not ozon_product.shop.owner.department_id == current_user.department.id:
                    return {"msg":"当前账户无操作权限！"},400
            elif any(role.id == "1" for role in current_user.roles):
                if not ozon_product.shop.owner.id == current_user.id:
                    return {"msg":"当前账户无操作权限！"},400
            else:
                return {"msg":"当前账户无操作权限！"},400
            
            columns = [column.name for column in OperateLog.__table__.columns ]
            filters = [getattr(OperateLog, col).like(f'%{ozon_product_id}%') for col in columns]
            query = query.filter(or_(*filters))

    else:
        columns = [column.name for column in OperateLog.__table__.columns ]
        filters = [getattr(OperateLog, col).like(f'%{userName}%') for col in columns] + [getattr(OperateLog, col).like(f'%{id}%') for col in columns]
        query = query.filter(or_(*filters))


    results = query.order_by(desc(OperateLog.create_time)).offset(start).limit(limit).all()
    results = [{column.name: getattr(result, column.name) for column in OperateLog.__table__.columns} for result in results]

    return jsonify({
        "msg":"查询成功！",
        "data":{
            "data":results,
            "count": query.count()
        }
    }), 200 