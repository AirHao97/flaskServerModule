'''
author:AHAO
createTime:2024/06/03 11:05
description: 加工特征模型
'''

from Models import db
import datetime
from Models.Machining.size_parameters_model import SizeParameters
from Models.Login.user_model import User

# 加工特征与尺寸参数 中间表
machining_machining_features_machining_size_parameters_association = db.Table(
    'machining_machining_features_size_parameters',
    db.Column('machining_machining_features_id', db.Text, db.ForeignKey('machining_machining_features.id'), primary_key=True),
    db.Column('machining_size_parameters_id', db.Text, db.ForeignKey('machining_size_parameters.id'), primary_key=True)
)


class MachiningFeatures(db.Model):

    __tablename__ = 'machining_machining_features'

    id = db.Column(db.Text, primary_key=True, doc='加工特征ID')
    name = db.Column(db.Text, unique=True, doc='加工特征名称')
    label = db.Column(db.Text, unique=True, nullable=True, doc='加工特征行业通用标识')
    mark = db.Column(db.Text, doc='备注')
    pic_address = db.Column(db.Text, nullable=True, doc='图片地址')

    # 关联的尺寸参数
    machining_size_parameters = db.relationship(
        'SizeParameters', secondary = machining_machining_features_machining_size_parameters_association,
        backref=db.backref('machining_machining_features', lazy='dynamic')
    )

    # 关联创建者
    creator = db.relationship('User', backref='machiningFeatures')
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))

    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')