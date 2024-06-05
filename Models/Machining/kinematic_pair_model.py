'''
author:AHAO
createTime:2024/06/03 08:58
description: 运动副模型
'''

from Models import db
import datetime
from Models.Machining.process_parameters_model import ProcessParameters
from Models.Login.user_model import User


# 运动副及工艺参数 中间表
machining_kinematic_pairs_machining_process_parameters_association = db.Table(
    'machining_kinematic_pairs_process_parameters',
    db.Column('machining_kinematic_pair_id', db.Text, db.ForeignKey('machining_kinematic_pair.id'), primary_key=True),
    db.Column('machining_process_parameters_id', db.Text, db.ForeignKey('machining_process_parameters.id'), primary_key=True)
)

class KinematicPair(db.Model):

    __tablename__ = 'machining_kinematic_pair'

    id = db.Column(db.Text, primary_key=True, doc='运动副ID')
    name = db.Column(db.Text, unique=True, doc='运动副名称')
    label = db.Column(db.Text, unique=True, nullable=True, doc='运动副行业通用标识')
    mark = db.Column(db.Text, doc='备注')
    pic_address = db.Column(db.Text, nullable=True, doc='图片地址')

    # 关联的工艺参数
    machining_process_parameters = db.relationship(
        'ProcessParameters', secondary = machining_kinematic_pairs_machining_process_parameters_association,
        backref=db.backref('machining_kinematic_pairs', lazy='dynamic')
    )

    # 关联创建者
    creator = db.relationship('User', backref='kinematicPairs')
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))

    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')