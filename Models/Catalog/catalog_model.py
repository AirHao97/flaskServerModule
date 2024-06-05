'''
author:AHAO
createTime:2024/06/05 08:32
description: 目录模型
'''

from Models import db
import datetime


class Catalog(db.Model):

    __tablename__ = 'catalog'

    id = db.Column(db.Text, primary_key=True, doc='子目录ID')
    name = db.Column(db.Text, unique=True, doc='子目录名称')
    label = db.Column(db.Text, unique=True, doc='子目录通用标识')
    
    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')