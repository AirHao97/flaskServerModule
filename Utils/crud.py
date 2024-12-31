'''
author:AHAO
createTime:2024/05/30 8:56
description: CRUD接口封装
'''

from flask import jsonify,request
from Models import db
import uuid
from flask_jwt_extended import get_jwt
from sqlalchemy import or_

from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType

# 查询全部数据
def getDataFromDataBase_BaseData(Obj):

    start = int(request.args.get('start', 0))
    limit = int(request.args.get('limit', 10))
    keyWord = str(request.args.get('keyWord', None))

    if keyWord:
        columns = [column.name for column in Obj.__table__.columns ]
        filters = [getattr(Obj, col).like(f'%{keyWord}%') for col in columns]
        query = Obj.query.filter(or_(*filters))
    else:
        query = Obj.query

    results = query.order_by(Obj.create_time).offset(start).limit(limit).all()
    results = [{column.name: getattr(result, column.name) for column in Obj.__table__.columns} for result in results]

    return jsonify({
        "msg":"查询成功！",
        "data":{
            "data":results,
            "count": query.count()
        }
    }), 200 

# 根据Id查询数据
def getDataFromDataBaseById_BaseData(Obj,id):
    
    obj = Obj.query.filter_by(id=id).first()
    result = {column.name: getattr(obj, column.name) for column in Obj.__table__.columns}

    return jsonify({
        "msg":"查询成功！",
        "data":result
    }), 200 

# 添加数据
def addDataFromDataBase(Obj,ObjType):

    current_user = get_jwt()
    data = request.get_json()

    obj = Obj()
    obj.id = str(uuid.uuid1())
    obj.creator_id = current_user["id"]
    for key, value in data.items():
        if hasattr(obj, key):
            setattr(obj, key, value)
        else:
            print(f"属性 {key} 不存在于 对象 模型中。")
    try:
        db.session.add_all([obj])
        db.session.commit()
        operate_log_writer_func(operateType=ObjType,describe=f"操作人:{current_user['username']}, 操作:添加数据, id:{obj.id}")
        return {"msg":"新增成功！"}, 200  
    except Exception as e:
        print(e)
        return {"msg":"新增失败！"}, 400 


# 修改数据
def modifyDataFromDataBase(Obj,ObjType):

    current_user = get_jwt()

    data = request.get_json()
    id = data.get('id')

    if not id:
        return {"msg":"需要修改的对象id不能为空！"}, 400

    obj = Obj.query.filter_by(id=id).first()
    if obj is None:
        return jsonify({"msg": "未找到对应的对象！"}), 401
    
    for key, value in data.items():
        if hasattr(obj, key):
            setattr(obj, key, value)
        else:
            print(f"属性 {key} 不存在于 对象 模型中。")
    try:
        db.session.commit()
        operate_log_writer_func(operateType=ObjType,describe=f"操作人:{current_user['username']}, 操作:修改数据, id:{id}")
        return {"msg":"修改成功！"}, 200  
    except Exception as e:
        return {"msg":"修改失败！"}, 400 


# 删除数据
def deleteDataFromDataBase(Obj,ObjType):

    current_user = get_jwt()

    data = request.get_json()
    id = data.get('id')

    if not id:
        return {"msg":"需要修改的对象id不能为空！"}, 400

    obj = Obj.query.filter_by(id=id).first()
    if obj is None:
        return jsonify({"msg": "未找到对应的对象！"}), 401

    try:
        db.session.delete(obj)
        db.session.commit()
        operate_log_writer_func(operateType=ObjType,describe=f"操作人:{current_user['username']}, 操作:删除数据, id:{id}")
        return {"msg":"删除成功！"}, 200  
    except Exception as e:
        print(e)
        return {"msg":"删除失败！"}, 400 