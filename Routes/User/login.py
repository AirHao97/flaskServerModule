'''
author:AHAO
createTime:2024/05/30 8:56
description: 登陆模块接口
'''

from flask import Blueprint,request
from flask import jsonify
from flask_jwt_extended import create_access_token,create_refresh_token,jwt_required,get_jwt_identity
import uuid
import datetime

from Models import db
from Models.User.user_model import User
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType


login_list = Blueprint('login', __name__)

# 账号登陆 返回token令牌
@login_list.route('/login', methods=['POST'])
def login():

    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400
    
    data = request.get_json()

    username = data.get('username')
    password = data.get('password')

    if not username:
        return jsonify({"msg": "账号不能为空！"}), 400
    if not password:
        return jsonify({"msg": "密码不能为空！"}), 400
    
    user = User.query.filter_by(username=username).first()

    if user is None:
        return jsonify({"msg": "未找到对应的用户！"}), 401
    
    if not user.check_password(password):
        return jsonify({"msg": "密码错误"}), 401
    
    if not user.is_active:
        return jsonify({"msg": "该账号已被冻结，请联系管理员处理！"}), 401
    
    user.last_login_time = datetime.datetime.now()

    try:
        db.session.add_all([user])
        db.session.commit()
        print("修改成功！")  
    except Exception as e:
        print ("修改失败！")

    access_token = create_access_token(identity={"id":user.id,
                                                 "username":user.username,
                                                 "passward":user.password,
                                                 "email":user.email,
                                                 "telephone_number":user.telephone_number,
                                                 "is_admin":user.is_admin,
                                                 "is_department_admin":user.is_department_admin,
                                                 "is_team_admin":user.is_team_admin,
                                                 "is_active":user.is_active,
                                                 "last_login_time":user.last_login_time,
                                                 "create_time":user.create_time,
                                                 "modify_time":user.modify_time,
                                                 })
    
    operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{user.username}, 操作: 登陆系统", isSystem=True)
        
    return jsonify(access=access_token), 200


# token鉴权 返回用户名
@login_list.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()

    user = User.query.filter_by(id=current_user['id']).first()

    data = {
        "id":user.id,
        "username":user.username,
        "passward":user.password,
        "email":user.email,
        "telephone_number":user.telephone_number,
        "is_admin":user.is_admin,
        "is_department_admin":user.is_department_admin,
        "is_team_admin":user.is_team_admin,
        "is_active":user.is_active,
        "last_login_time":user.last_login_time,
        "create_time":user.create_time,
        "modify_time":user.modify_time,
    }
    access_token = create_refresh_token(identity=data)

    operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{user.username}, 操作: 登陆系统")


    return jsonify({"logged_in_as":data, "access_token":access_token}), 200



# 用户注册
@login_list.route('/registration', methods=['POST'])
def registration():

    data = request.get_json()
    
    user = User()
    if not User.query.filter_by(username=data.get('username')).first():

        user.id = str(uuid.uuid1())
        user.username = data['username']
        user.password = user.set_password(data['password'])

        if "email" in data:
            user.email = data['email']
        
        if "telephone_number" in data:
            user.telephone_number = data['telephone_number']

        user.is_active = True
        user.is_admin = False
        user.is_department_admin = False
        user.is_team_admin = False

        db.session.add_all([user])
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{user.username}, 操作: 用户注册",isSystem=True)
        
        return jsonify({"msg": "注册成功！"}), 200
    else:
        return jsonify({"msg": "账号已存在！"}), 400

# 修改密码
@login_list.route('/modifyPassword', methods=['POST'])
def modifyPassword():

    current_user = get_jwt_identity()
    data = request.get_json()
    
    user =  User.query.filter_by(username=current_user["username"]).first()

    if user:
        if "password" in data:
            password = data["password"]
            if User.check_password(password):
                if "new_password" in data:
                    if data["new_password"]:
                        if len(data["new_password"] >= 6):
                            user.password = user.set_password(data['new_password'])
                        else:
                            return jsonify({"msg": "新密码数量不能少于6位！"}), 400
                    else:
                        return jsonify({"msg": "new_password 字段不能为空！"}), 400
                else:
                    jsonify({"msg": "new_password 字段不能为空！"}), 400
            else:
                jsonify({"msg": "旧密码错误！"}), 400
        else:
            jsonify({"msg": "password 字段不能为空！"}), 400

        try:
            db.session.add_all([user])
            db.session.commit()
            operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{user.username}, 操作: 修改密码")
            return jsonify({"msg": "修改密码成功！"}), 200
        except Exception:
            return jsonify({"msg": "修改密码失败！"}), 400
    else:
        return jsonify({"msg": "找不到对应用户！"}), 400