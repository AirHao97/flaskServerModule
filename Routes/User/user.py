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
from Utils.apiRightsDecorator import admin_required,admin_all_required,active_required
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType

from Models.User.user_model import User
from Models.User.role_model import Role
from Models.User.department_model import Department
from Models.Work.shop_model import Shop
from Models.User.team_model import Team


user_list = Blueprint('user', __name__, url_prefix='/user')

# 管理员账号初始化
@user_list.route('/initData', methods=['POST'])
def initData():
    admin = User()
    if not User.query.filter_by(username="admin").first():

        admin.id = str(uuid.uuid1())
        admin.username = "admin"
        admin.password = admin.set_password("123456")
        admin.is_active = True
        admin.is_admin = True

        db.session.add_all([admin])
        db.session.commit()
        return jsonify({"msg": "管理员账号初始化成功！"}), 200
    else:
        return jsonify({"msg": "已完成初始化，请勿重复操作！"}), 400

# 查询用户数据（多条）（系统、部门、小组管理员可操作）
@user_list.route('/getData', methods=['GET'])
@jwt_required()
@active_required
def getData():
    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()
    
    start = int(request.args.get('start', 0))
    limit = int(request.args.get('limit', 10))
    keyWord = str(request.args.get('keyWord', None))

    if keyWord:
        columns = [column.name for column in User.__table__.columns if column.name != 'id']
        filters = [getattr(User, col).like(f'%{keyWord}%') for col in columns]
        query = User.query.filter(or_(*filters))
    else:
        query = User.query
    
    # 判断是否是系统管理员
    if user and user.is_admin:
        count = query.order_by(User.create_time).count()
        results = query.order_by(User.create_time).offset(start).limit(limit).all()
    else:
        # 判断是否是部门管理员
        if user.is_department_admin and user.department:
            count = query.filter_by(department_id=user.department_id).order_by(User.create_time).count()
            results = query.filter_by(department_id=user.department_id).order_by(User.create_time).offset(start).limit(limit).all()
        else:
            # 判断是否是小组管理员
            if user.is_team_admin and user.team:
                count = query.filter_by(team_id=user.team_id).order_by(User.create_time).count()
                results = query.filter_by(team_id=user.team_id).order_by(User.create_time).offset(start).limit(limit).all()
            else:
                count = 1
                results = [user]

    results = [{
        "id": result.id,
        "username": result.username,
        "email": result.email,
        "telephone_number": result.telephone_number,
        "is_admin": result.is_admin,
        "is_department_admin": result.is_department_admin,
        "is_team_admin": result.is_team_admin,
        "is_active": result.is_active,
        "partners_orders": [{"id":partner_orders.username, "name":partner_orders.username} for partner_orders in  result.partners_orders],
        "partners_system_products": [{"id":partner_system_products.username, "name":partner_system_products.username} for partner_system_products in  result.partners_system_products],
        "roles":[{"id":role.id,"name":role.name} for role in user.roles],
        "shops":[{"id":shop.id,"name":shop.name} for shop in user.owner_shops],
        "department": {"id": result.department.id, "name":result.department.name} if result.department else {},
        "team": {"id": result.team.id, "name":result.team.name} if result.team else {},
        "last_login_time": result.last_login_time,
        "create_time": result.create_time,
        "modify_time": result.modify_time,
    } for result in results]


    return jsonify({
        "msg":"查询成功！",
        "data":results,
        "count":count
    }), 200 

# 新增用户数据（系统管理员可操作）
@user_list.route('/addData', methods=['POST'])
@jwt_required()
@active_required
@admin_required
def addData():
    return addDataFromDataBase(User,OperateType.user)

# 修改用户基础数据（管理员和用户本人可操作）
@user_list.route('/modifyData', methods=['POST'])
@jwt_required()
@active_required
def modifyData(): 
    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()

    # 判断是否是系统管理员
    if user and user.is_admin:
        
        data = request.get_json()

        if "user_id" in data:
            user_id = data['user_id']
        else:
            return {"msg":"user_id 不能为空！"},401

        user = User.query.filter_by(id=user_id).first()

    if user is None:
        return jsonify({"msg": "未找到对应的对象！"}), 401
    if "username" in data:
        user.username = data['username']
    if "email" in data:
        user.email = data['email']
    if "telephone_number" in data:
        user.telephone_number = data['telephone_number']

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.user, describe=f"操作人:{current_user['username']}, 操作:修改数据, id:{id}")
        return {"msg":"用户信息修改成功！"}, 200  
    except Exception as e:
        return {"msg":"用户信息修改失败！"}, 400 
    
# 重置密码（仅管理员可操作）
@user_list.route('/resetPassword', methods=['POST'])
@jwt_required()
@active_required
@admin_required
def resetPassword():
    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()
    if "user_id" in data:
        user_id = data['user_id']
    else:
        return {"msg":"user_id 不能为空！"},401

    if not user_id:
        return {"msg":"需要修改的对象id不能为空！"}, 400
    
    user = User.query.filter_by(id=user_id).first()

    if not user:
        return jsonify({"msg": "未找到对应的对象！"}), 401
    else:
        user.password = User.set_password("123456")
    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{current_user['username']}, 操作:给用户{user.username}重置密码为123456！")
        return {"msg":"密码重置成功！"}, 200  
    except Exception as e:
        return {"msg":"密码重置失败！"}, 400
        
# 删除用户数据（仅管理员可操作）
@user_list.route('/deleteData', methods=['POST'])
@jwt_required()
@active_required
@admin_required
def deleteData():
    return deleteDataFromDataBase(User,OperateType.user)

# 给用户全局管理员权限（仅系统管理员可以操作）
@user_list.route('/addAdmin', methods=['POST'])
@jwt_required()
@active_required
@admin_required
def addAdmin():
    current_user = get_jwt_identity()

    data = request.get_json()
    if "user_id" in data:
        user_id = data['user_id']
    else:
        return {"msg":"user_id 不能为空！"},401

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return {"msg":"找不到指定用户！"},401
    
    user.is_admin = True

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{current_user['username']}, 操作:给用户{user.username}添加部门管理员权限！")
        return {"msg":"权限添加成功！"}, 200  
    except Exception as e:
        return {"msg":"权限添加失败！"}, 400

# 给用户部门管理员权限(仅系统管理员可操作)
@user_list.route('/addDepartmentAdmin', methods=['POST'])
@jwt_required()
@active_required
@admin_required
def addDepartmentAdmin():
    current_user = get_jwt_identity()

    data = request.get_json()

    if "user_id" in data:
        user_id = data['user_id']
    else:
        return {"msg":"user_id 不能为空！"},401

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return {"msg":"找不到指定用户！"},401
    

    if user.department:
        user.is_department_admin = True
    else:
        return {"msg":"用户尚未设置部门！"},400

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{current_user['username']}, 操作:给用户{user.username}添加部门管理员权限！")
        return {"msg":"权限添加成功！"}, 200  
    except Exception as e:
        return {"msg":"权限添加失败！"}, 400

# 给用户小组管理员权限（仅系统管理员可以操作）
@user_list.route('/addTeamAdmin', methods=['POST'])
@jwt_required()
@active_required
@admin_required
def addTeamAdmin():
    current_user = get_jwt_identity()
    user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "user_id" in data:
        user_id = data['user_id']
    else:
        return {"msg":"user_id 不能为空！"},401

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return {"msg":"找不到指定用户！"},401
    
    if user.department:
        if user.team:
            user.is_team_admin = True
        else:
            return {"msg":"用户尚未设置小组！"},400
    else:
        return {"msg":"用户尚未设置部门！"},400

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{current_user['username']}, 操作:给用户{user.username}添加小组管理员权限！")
        return {"msg":"权限添加成功！"}, 200
    except Exception as e:
        return {"msg":"权限添加失败！"}, 400

# 给用户绑定角色权限（仅系统管理员可以操作）
@user_list.route('/addRoles', methods=['POST'])
@jwt_required()
@active_required
@admin_required
def addRoles():
    data = request.get_json()

    current_user = get_jwt_identity()

    if "user_id" in data:
        user_id = data['user_id']
    else:
        return {"msg":"user_id 不能为空！"},401
    
    if "role_ids" in data:
        role_ids = data['role_ids']
    else:
        return {"msg":"role_ids 不能为空！"},401

    user = User.query.filter_by(id=user_id).first()

    if not user:
        return {"msg":"找不到指定用户！"},401
    
    roles = Role.query.filter(Role.id.in_(role_ids)).all()
    user.roles = roles

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{current_user['username']}, 操作:给用户{user.username}绑定角色{[item.name for item in roles]}")
        return {"msg":"权限添加成功！"}, 200  
    except Exception as e:
        return {"msg":"权限添加失败！"}, 400

# 冻结用户（仅系统管理员可以操作）
@user_list.route('/freezeUser', methods=['POST'])
@jwt_required()
@active_required
@admin_required
def freezeUser():
    data = request.get_json()

    current_user = get_jwt_identity()

    if "user_id" in data:
        user_id = data['user_id']
    else:
        return {"msg":"user_id 不能为空！"},401

    user = User.query.filter_by(id=user_id).first()

    if not user:
        return {"msg":"找不到指定用户！"},401
    
    user.is_active = False

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{current_user['username']}, 操作:冻结账号，用户{user.username}")
        return {"msg":"冻结账号成功！"}, 200  
    except Exception as e:
        return {"msg":"冻结账号失败！"}, 400

# 解冻用户（仅系统管理员可以操作）
@user_list.route('/unfreezeUser', methods=['POST'])
@jwt_required()
@active_required
@admin_required
def unfreezeUser():
    data = request.get_json()

    current_user = get_jwt_identity()

    if "user_id" in data:
        user_id = data['user_id']
    else:
        return {"msg":"user_id 不能为空！"},401

    user = User.query.filter_by(id=user_id).first()

    if not user:
        return {"msg":"找不到指定用户！"},401
    
    user.is_active = True

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{current_user['username']}, 操作:解冻账号，用户{(user.username)}")
        return {"msg":"解冻账号成功！"}, 200  
    except Exception as e:
        return {"msg":"解冻账号失败！"}, 400

# 给用户绑定可处理订单的关系伙伴（系统管理员可操作全部 部门管理员可操作本部门 小组管理员可操作本小组）
@user_list.route('/addPartnersOrders', methods=['POST'])
@jwt_required()
@active_required
@admin_all_required
def addPartnersOrders():

    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "user_id" in data:
        user_id = data['user_id']
    else:
        return {"msg":"user_id 不能为空！"},401

    if "partners_orders_ids" in data:
        partners_orders_ids = data['partners_orders_ids']
    else:
        return {"msg":"partners_orders_ids 不能为空！"},401


    user = User.query.filter_by(id=user_id).first()

    if not user:
        return {"msg":"找不到指定用户！"},401
    
    partners_orders = User.query.filter(User.id.in_(partners_orders_ids)).all()

    if not current_user.is_admin:
        if not (current_user.is_department_admin and user.department.id == current_user.department.id and all(current_user.department.id == partner_system_products.department.id for partner_system_products in partners_orders)):
            if not (current_user.is_team_admin and user.team.id == current_user.team.id and all(current_user.team.id == partner_system_products.team.id for partner_system_products in partners_orders)):
                return {"msg":"当前账户无操作权限！"},400
    
    user.partners_orders = partners_orders

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{current_user.username}, 操作:给用户{user.username}绑定可处理订单的关系伙伴{[item.username for item in partners_orders]}")
        return {"msg":"订单伙伴添加成功！"}, 200
    except Exception as e:
        return {"msg":"订单伙伴添加失败！"}, 400
    

# 给用户绑定可处理系统内商品的关系伙伴（系统管理员可操作全部 部门管理员可操作本部门 小组管理员可操作本小组）
@user_list.route('/addPartnersSystemProducts', methods=['POST'])
@jwt_required()
@active_required
@admin_all_required
def addPartnersSystemProducts():

    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    data = request.get_json()

    if "user_id" in data:
        user_id = data['user_id']
    else:
        return {"msg":"user_id 不能为空！"},401

    if "partners_system_products_ids" in data:
        partners_system_products_ids = data['partners_system_products_ids']
    else:
        return {"msg":"partners_orders_ids 不能为空！"},401


    user = User.query.filter_by(id=user_id).first()

    if not user:
        return {"msg":"找不到指定用户！"},401
    
    partners_system_products = User.query.filter(User.id.in_(partners_system_products_ids)).all()

    if not current_user.is_admin:
        if not (current_user.is_department_admin and user.department.id == current_user.department.id and all(current_user.department.id == partner_system_products.department.id for partner_system_products in partners_system_products)):
            if not (current_user.is_team_admin and user.team.id == current_user.team.id and all(current_user.team.id == partner_system_products.team.id for partner_system_products in partners_system_products)):
                return {"msg":"当前账户无操作权限！"},400

    user.partners_system_products = partners_system_products

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{current_user.username}, 操作:给用户{user.username}绑定可处理系统内商品的关系伙伴{[item.username for item in partners_system_products]}")
        return {"msg":"系统内商品伙伴添加成功！"}, 200  
    except Exception as e:
        return {"msg":"系统内商品伙伴添加失败！"}, 400
    
# 给用户绑定部门(触发绑定部门操作 部门管理员权限、小组管理员权限改为False)(仅系统管理员可操作)
@user_list.route('/addDepartment', methods=['POST'])
@jwt_required()
@active_required
@admin_required
def addDepartment():

    current_user = get_jwt_identity()

    data = request.get_json()

    if "user_id" in data:
        user_id = data['user_id']
    else:
        return {"msg":"user_id 不能为空！"},401
    
    if "department_id" in data:
        department_id = data['department_id']
    else:
        return {"msg":"department_id 不能为空！"},401

    department = Department.query.filter_by(id=department_id).first()

    if department:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return {"msg":"找不到指定用户！"},401
        
        user.department_id = department_id
        user.is_department_admin = False
        user.is_team_admin = False
    else:
        return {"msg":"部门不存在！"}, 200

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{current_user['username']}, 操作:给用户{user.username}绑定部门{(department.id,department.name)},部门管理员、小组管理员权限重置！")
        return {"msg":"绑定部门成功！"}, 200  
    except Exception as e:
        return {"msg":"绑定部门失败！"}, 400

# 给用户绑定小组（仅运营权限有小组）（仅系统管理员可操作）
@user_list.route('/addTeam', methods=['POST'])
@jwt_required()
@active_required
@admin_required
def addTeam():

    current_user = get_jwt_identity()

    data = request.get_json()

    if "user_id" in data:
        user_id = data['user_id']
    else:
        return {"msg":"user_id 不能为空！"},401
    
    if "team_id" in data:
        team_id = data['team_id']
    else:
        return {"msg":"team_id 不能为空！"},401

    team = Team.query.filter_by(id=team_id).first()

    if team:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return {"msg":"找不到指定用户！"},401
        
        if not any(role.id == "1" for role in user.roles):
            return {"msg":"只有运营权限用户可以绑定小组！"},400
        
        user.team_id = team_id
        user.is_team_admin = False
    else:
        return {"msg":"小组不存在！"}, 200

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{current_user['username']}, 操作:给用户{user.username}绑定小组{(team.id,team.name)}，小组管理员权限重置！")
        return {"msg":"绑定小组成功！"}, 200
    except Exception as e:
        return {"msg":"绑定小组失败！"}, 400

# 给用户绑定店铺（仅系统管理员可操作）
@user_list.route('/addShops', methods=['POST'])
@jwt_required()
@active_required
@admin_required
def addShops():
    
    current_user = get_jwt_identity()

    data = request.get_json()

    if "user_id" in data:
        user_id = data['user_id']
    else:
        return {"msg":"user_id 不能为空！"},401
    
    if "shop_ids" in data:
        shop_ids = data['shop_ids']
    else:
        return {"msg":"shop_ids 不能为空！"},401

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return {"msg":"找不到指定用户！"},401

    shops = Shop.query.filter(Shop.id.in_(shop_ids)).all()

    user.owner_shops = shops

    try:
        db.session.commit()
        operate_log_writer_func(operateType=OperateType.user,describe=f"操作人:{current_user['username']}, 操作:给用户{user.username}绑定店铺{[(item.id,item.name) for item in shops]}")

        return {"msg":"绑定店铺成功！"}, 200
    except Exception as e:
        return {"msg":"绑定店铺失败！"}, 400
