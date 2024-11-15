'''
author:AHAO
createTime:2024/09/19
description: 登陆数据库模型
'''

from Models import db
import datetime
from Models.User.user_model import User

user_role = db.Table('user_roles',
    db.Column('user_id', db.Text, db.ForeignKey('user.id')),
    db.Column('role_id', db.Text, db.ForeignKey('role.id'))
)

class Role(db.Model):

    __tablename__ = 'role'

    id = db.Column(db.Text, primary_key=True, doc='权限ID')
    name = db.Column(db.Text, unique=True, index=True, doc='权限名称')
    
    users = db.relationship('User', secondary=user_role, backref='roles')

    # 关联创建者    
    creator = db.relationship('User', backref='create_roles')
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))

    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')
