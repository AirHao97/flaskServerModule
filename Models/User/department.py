'''
author:AHAO
createTime:2024/09/19
description: 登陆数据库模型
'''

from Models import db
import datetime
from Models.User.user_model import User


class Department(db.Model):

    __tablename__ = 'department'

    id = db.Column(db.Text, primary_key=True, doc='部门id')
    name = db.Column(db.Text, unique=True, doc='部门名称')

    # 关联用户
    users = db.relationship('User', backref='department')
    # 关联创建者
    creator = db.relationship('User', backref='departments')
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))
    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')
