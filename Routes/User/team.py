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
from Utils.apiRightsDecorator import admin_required,active_required,admin_all_required
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType

from Models.User.team_model import Team
from Models.User.user_model import User
from Models.User.department_model import Department


team_list = Blueprint('team', __name__, url_prefix='/team')

# 部门数据初始化
@team_list.route('/initData', methods=['POST'])
def initAdminAccount():

    team_data = ["小组1号","小组2号"]
    add_team_list = []

    for i in team_data:
        team= Team()
        team.id = str(uuid.uuid1())
        team.name = i
        add_team_list.append(team)
    try:
        db.session.add_all(add_team_list)
        db.session.commit()
        return jsonify({"msg": "小组数据初始化成功！"}), 200
    except Exception as e:
        return jsonify({"msg": "已完成初始化，请勿重复操作！"}), 400


# 查询数据（多条）（系统管理员、部门管理员）
@team_list.route('/getData', methods=['GET'])
@jwt_required()
@active_required
def getData():
    current_user = get_jwt()
    user = User.query.filter_by(id=current_user['id']).first()
    
    start = int(request.args.get('start', 0))
    limit = int(request.args.get('limit', 10))
    keyWord = str(request.args.get('keyWord', None))

    if keyWord:
        columns = [column.name for column in Team.__table__.columns ]
        filters = [getattr(Team, col).like(f'%{keyWord}%') for col in columns]
        query = Team.query.filter(or_(*filters))
    else:
        query = Team.query
    
    # 判断是否是系统管理员
    if user and user.is_admin:
        results = query.order_by(Team.create_time).offset(start).limit(limit).all()
        length = query.count()
    else:
        # 判断是否是部门管理员
        if user.is_department_admin and user.department:
            results = query.filter_by(department_id=user.department_id).order_by(Team.create_time).offset(start).limit(limit).all()
            length = query.filter_by(department_id=user.department_id).count()
        else:
            return jsonify({"msg": "当前账号无权限查看！"}), 400
        
    results = [{
        "id": result.id,
        "name": result.name,
        "create_time": result.create_time,
        "modify_time": result.modify_time,
        "department": {"id":result.department.id, "name":result.department.name} if result.department else {"id":"","name":""},
        "creator": {"id": result.creator.id, "username": result.creator.username} if result.creator else {"id":"","name":""},
        "users": [{"id":user_in_team.id,"username":user_in_team.username} for user_in_team in result.users]
    } for result in results]


    return jsonify({
        "msg":"查询成功！",
        "data":{
            "data":results,
            "count":length
        }
    }), 200 

# 根据部门获取小组
@team_list.route('/getDataFromDepartment', methods=['POST'])
@jwt_required()
@active_required
def getDataFromDepartment():
    current_user = get_jwt()
    user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "department_id" in data:
        department_id = data['department_id']
    else:
        return jsonify({"msg":"department_id 不能为空！"}),401
    
    # 判断是否是系统管理员
    if user and user.is_admin:
        query = Team.query.filter_by(department_id = department_id)
        results = query.order_by(Team.create_time).all()
    else:
        return jsonify({"msg": "当前账号无权限查看！"}), 400
        
    results = [{
        "id": result.id,
        "name": result.name,
        "create_time": result.create_time,
        "modify_time": result.modify_time,
        "department": {"id":result.department.id, "name":result.department.name} if result.department else {"id":"","name":""},
        "creator": {"id": result.creator.id, "username": result.creator.username} if result.creator else {"id":"","name":""},
        "users": [{"id":user_in_team.id,"username":user_in_team.username} for user_in_team in result.users]
    } for result in results]


    return jsonify({
        "msg":"查询成功！",
        "data":{
            "data":results,
            "count":query.count()
        }
    }), 200 

# 新增数据（系统管理员、部门管理员可操作）
@team_list.route('/addData', methods=['POST'])
@jwt_required()
@active_required
def addData():
    current_user = get_jwt()
    user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "name" in data:
        name = data["name"]
    else:
        {"msg":"name 不能为空！"},401

    team = Team()
    team.id = str(uuid.uuid1())
    team.name = name
    team.creator_id = current_user["id"]

    if user and user.is_admin:
        if "department_id" in data:
            department_id = data["department_id"]
            if Department.query.filter_by(id=department_id).first():
                team.department_id = department_id

            else:
                return jsonify({"msg": "未找到对应的部门！"}), 400
        else:
            {"msg":"department_id 不能为空！"},401
    else:
        # 判断是否是部门管理员
        if user.is_department_admin and user.department:
            team.department_id = user.department.id

    try:
        db.session.add_all([team])
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.team, describe=f"操作人:{user.username}, 操作:添加小组, id:{team.id} name:{team.name}")
        return {"msg":"新增小组成功！"}, 200  
    except Exception as e:
        print(e)
        return {"msg":"新增小组失败！"}, 400 

# 修改数据（系统管理员、部门管理员、小组管理员可操作）
@team_list.route('/modifyData', methods=['POST'])
@jwt_required()
@active_required
def modifyData(): 
    current_user = get_jwt()
    user = User.query.filter_by(id=current_user['id']).first()
    data = request.get_json()

    # 判断是否是系统管理员
    if user and user.is_admin:
        if "id" in data:
            team_id = data["id"]
        else:
            {"msg":"team_id 不能为空！"},401

        team = Team.query.filter_by(id=team_id).first()

        if not team:
            return jsonify({"msg": "未找到对应的对象！"}), 400
        
    else:
        # 判断是否是部门管理员
        if user.is_department_admin and user.department:
            
            if "team_id" in data:
                team_id = data["team_id"]
            else:
                {"msg":"team_id 不能为空！"},401

            team = Team.query.filter_by(id=team_id).first()

            if not team:
                return jsonify({"msg": "未找到对应的小组！"}), 400
            
            if not team.department_id == user.department_id:
                return jsonify({"msg": "当前账号无权限修改！"}), 400
        else:
            # 判断是否是小组管理员
            if user.is_team_admin and user.team:
                team = user.team
            else:
                return jsonify({"msg": "当前账号无权限修改！"}), 400
    
    if "name" in data:
        team.name = data["name"]
    if "department_id" in data:
        if Department.query.filter_by(id=data["department_id"]).first():
            team.department_id = data["department_id"]
            for user in team.users:
                user.department_id = data["department_id"]
        else:
            return jsonify({"msg": "未找到对应的部门！"}), 400

    try:
        db.session.add_all([team])
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.team, describe=f"操作人:{user.username}, 操作:修改小组信息, id:{team.id} name:{team.name}")
        return {"msg":"修改小组信息成功！"}, 200  
    except Exception as e:
        print(e)
        return {"msg":"修改小组信息失败！"}, 400


# 删除数据（系统管理员、部门管理员可操作）
@team_list.route('/deleteData', methods=['POST'])
@jwt_required()
@active_required
def deleteData():
    current_user = get_jwt()
    user = User.query.filter_by(id=current_user['id']).first()
    data = request.get_json()

    # 判断是否是系统管理员
    if user and user.is_admin:
        if "id" in data:
            team_id = data["id"]
        else:
            {"msg":"team_id 不能为空！"},401

        team = Team.query.filter_by(id=team_id).first()

        if not team:
            return jsonify({"msg": "未找到对应的对象！"}), 400
        
    else:
        # 判断是否是部门管理员
        if user.is_department_admin and user.department:
            
            if "team_id" in data:
                team_id = data["team_id"]
            else:
                {"msg":"team_id 不能为空！"},401

            team = Team.query.filter_by(id=team_id).first()

            if not team:
                return jsonify({"msg": "未找到对应的小组！"}), 400
            
            if not team.department_id == user.department_id:
                return jsonify({"msg": "当前账号无权限修改！"}), 400
        else:
            return jsonify({"msg": "当前账号无权限修改！"}), 400
                
    try:
        db.session.delete(team)
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.team, describe=f"操作人:{user.username}, 操作:删除小组, id:{team.id} name:{team.name}")
        return {"msg":"删除小组成功！"}, 200  
    except Exception as e:
        print(e)
        return {"msg":"删除小组失败！"}, 400



