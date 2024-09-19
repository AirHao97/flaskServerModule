'''
author:AHAO
createTime:2024/05/30 8:56
description: 登陆模块接口
'''

from flask import Blueprint,request
from Models.User.user_model import User
from flask import jsonify
from flask_jwt_extended import create_access_token,jwt_required,get_jwt_identity


user_login_list = Blueprint('user_login', __name__,  url_prefix='/user/login')

# 账号登陆 返回token令牌
@user_login_list.route('/login', methods=['POST'])
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
    
    if not user.passward == password:
        return jsonify({"msg": "密码错误"}), 401

    access_token = create_access_token(identity={"id":user.id,
                                                 "username":user.username,
                                                 "passward":user.passward,
                                                 "email":user.email,
                                                 "telephone_number":user.telephone_number,
                                                 "is_admin":user.is_admin,
                                                 "is_active":user.is_active,
                                                 "power_arange":user.power_arange,
                                                 "last_login_time":user.last_login_time,
                                                 "create_time":user.create_time,
                                                 "modify_time":user.modify_time,
                                                 })
    
    return jsonify(access_token=access_token), 200


# token鉴权 返回用户名
@user_login_list.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

