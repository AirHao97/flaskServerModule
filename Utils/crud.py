'''
author:AHAO
createTime:2024/05/30 8:56
description: CRUD接口封装
'''

from flask import jsonify,request
from Models import db
import uuid
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import or_


# 查询数据
def getDataFromDataBase_BaseData(Obj):
    
    start = int(request.args.get('start', 0))
    limit = int(request.args.get('limit', 10))
    keyWord = str(request.args.get('keyWord', None))

    if keyWord:
        columns = [column.name for column in Obj.__table__.columns if column.name != 'id']
        filters = [getattr(Obj, col).like(f'%{keyWord}%') for col in columns]
        query = Obj.query.filter(or_(*filters))
    else:
        query = Obj.query

    results = query.order_by(Obj.create_time).offset(start).limit(limit).all()
    results = [{column.name: getattr(result, column.name) for column in Obj.__table__.columns} for result in results]

    return jsonify({
        "msg":"查询成功！",
        "data":results
    }), 200 


# 添加数据
def addDataFromDataBase(Obj):

    current_user = get_jwt_identity()
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
        return {"msg":"新增成功！"}, 200  
    except Exception as e:
        print(e)
        return {"msg":"新增失败！"}, 400 


# 修改数据
def modifyDataFromDataBase(Obj):

    data = request.get_json()
    id = data.get('id')

    if not id:
        return {"msg":"需要修改的对象id不能为空！"}, 400

    obj = Obj.query.filter_by(id=id).first()
    if obj is None:
        return jsonify({"msg": "未找到对应的对象！"}), 401
    
    current_user = get_jwt_identity()

    if not current_user["is_admin"]:
        if obj.creator.id != current_user["id"]:
            return jsonify({"msg": "无修改权限！"}), 400
    
    for key, value in data.items():
        if hasattr(obj, key):
            setattr(obj, key, value)
        else:
            print(f"属性 {key} 不存在于 对象 模型中。")
    try:
        db.session.commit()
        return {"msg":"修改成功！"}, 200  
    except Exception as e:
        return {"msg":"对象名字/对象行业通用标识 字段重复"}, 400 


# 删除数据
def deleteDataFromDataBase(Obj):

    data = request.get_json()
    id = data.get('id')

    if not id:
        return {"msg":"需要修改的对象id不能为空！"}, 400

    obj = Obj.query.filter_by(id=id).first()
    if obj is None:
        return jsonify({"msg": "未找到对应的对象！"}), 401
    
    current_user = get_jwt_identity()

    if not current_user["is_admin"]:
        if obj.creator.id != current_user["id"]:
            return jsonify({"msg": "无修改权限！"}), 400
    
    try:
        db.session.delete(obj)
        db.session.commit()
        return {"msg":"删除成功！"}, 200  
    except Exception as e:
        print(e)
        return {"msg":"删除失败！"}, 400 