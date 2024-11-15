'''
author:AHAO
createTime:2024/09/19
description: 登陆数据库模型
'''

from Models import db
import datetime
from Models.User.user_model import User
from Models.User.team_model import Team
from Models.Work.purchase_order_model import PurchaseOrder
from Models.Work.system_product_model import SystemProduct

class Department(db.Model):

    __tablename__ = 'department'

    id = db.Column(db.Text, primary_key=True, doc='部门id')
    name = db.Column(db.Text, unique=True, doc='部门名称')

    # 关联系统内产品
    system_products = db.relationship('SystemProduct', backref='department', foreign_keys='system_product.c.department_id')
    # 关联采购单
    purchase_orders = db.relationship('PurchaseOrder', backref='department', foreign_keys='purchase_order.c.department_id')
    # 关联用户
    users = db.relationship('User', backref='department', foreign_keys='user.c.department_id')
    # 关联小组
    teams = db.relationship('Team', backref='department', foreign_keys='team.c.department_id')
    # 关联创建者
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))
    creator = db.relationship('User', backref='departments',  foreign_keys=[creator_id])
    
    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')
