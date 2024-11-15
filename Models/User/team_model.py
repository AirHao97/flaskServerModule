'''
author:AHAO
createTime:2024/09/19
description: 登陆数据库模型
'''

from Models import db
import datetime
from Models.User.user_model import User


class Team(db.Model):

    __tablename__ = 'team'

    id = db.Column(db.Text, primary_key=True, doc='小组id')
    name = db.Column(db.Text, unique=True, doc='小组名称')

    # 关联用户
    users = db.relationship('User', backref='team', foreign_keys='user.c.team_id')
    # 关联部门
    department_id = db.Column(db.Text, db.ForeignKey('department.id'))

    # 关联创建者
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))
    creator = db.relationship('User', backref='teams',  foreign_keys=[creator_id])
    
    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')
