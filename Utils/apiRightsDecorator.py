from functools import wraps
from flask_jwt_extended import get_jwt
from flask import jsonify,request

from Models.User.user_model import User

def has_role(user, role_id):
    return any(role.id == role_id for role in user.roles)

# 系统启用用户
def active_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user = get_jwt()
        user = User.query.filter_by(id=current_user['id']).first()
        if user and user.is_active:
            return fn(*args, **kwargs)
        else:
            return jsonify({'msg': '该账号未被启用，请联系管理员！'}), 400
    return wrapper

# 系统管理员权限
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user = get_jwt()
        user = User.query.filter_by(id=current_user['id']).first()
        if user and user.is_admin:
            return fn(*args, **kwargs)
        else:
            return jsonify({'msg': '仅管理员可操作!本账号暂无操作权限！'}), 400
    return wrapper

# 系统管理员 + 部门管理员 + 小组管理员权限
def admin_all_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user = get_jwt()
        data = request.get_json()
        user_id = data['user_id']

        user_request = User.query.filter_by(id=current_user['id']).first()
        user = User.query.filter_by(id=user_id).first()
        
        # 判断是否是系统管理员
        if user_request and user_request.is_admin:
            return fn(*args, **kwargs)
        else:
            # 判断是否是部门管理员
            if user_request.is_department_admin and user_request.department and user.department and user_request.department.id == user.department.id:
                return fn(*args, **kwargs)
            else:
                # 判断是否是小组管理员
                if user_request.is_team_admin and user_request.team and user.team and user_request.team.id == user.team.id:
                    return  fn(*args, **kwargs)
                else:
                    return jsonify({'msg': '仅管理员可操作!本账号暂无操作权限！'}), 400
    return wrapper

# 运营权限
def operations_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user = get_jwt()
        user = User.query.filter_by(id=current_user['id']).first()
        if user and (user.is_admin or has_role(user,"1")):
            return fn(*args, **kwargs)
        else:
            return jsonify({'msg': '仅管理员或运营权限可操作!本账号暂无操作权限！'}), 400
    return wrapper

# 采购权限
def purchasing_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user = get_jwt()
        user = User.query.filter_by(id=current_user['id']).first()
        if user and (user.is_admin or has_role(user,"2")):
            return fn(*args, **kwargs)
        else:
            return jsonify({'msg': '仅管理员或采购权限可操作!本账号暂无操作权限！'}), 400
    return wrapper

# 打包权限
def packaging_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user = get_jwt()
        user = User.query.filter_by(id=current_user['id']).first()
        if user and (user.is_admin or has_role(user,"3")):
            return fn(*args, **kwargs)
        else:
            return jsonify({'msg': '仅管理员或打包权限可操作!本账号暂无操作权限！'}), 400
    return wrapper

# 财务权限
def finance_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user = get_jwt()
        user = User.query.filter_by(id=current_user['id']).first()
        if user and (user.is_admin or has_role(user,"4")):
            return fn(*args, **kwargs)
        else:
            return jsonify({'msg': '仅管理员或财务权限可操作!本账号暂无操作权限！'}), 400
    return wrapper