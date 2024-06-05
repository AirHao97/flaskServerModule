'''
author:AHAO
createTime:2024/05/31 16:21
description: 设备模型
'''

from Models import db
import datetime
from Models.Login.user_model import User


class Device(db.Model):

    __tablename__ = 'machining_device'

    id = db.Column(db.Text, primary_key=True, doc='设备ID')
    name = db.Column(db.Text, unique=True, doc='设备名称')
    label = db.Column(db.Text, unique=True, nullable=True, doc='设备行业通用标识')
    mark = db.Column(db.Text, doc='备注')
    pic_address = db.Column(db.Text, nullable=True, doc='图片地址')

    # 关联创建者
    creator = db.relationship('User', backref='devices')
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))

    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')
