'''
author:AHAO
createTime:2024/05/30
description: 登陆数据库模型
'''

from Models import db
import datetime


class OperateLog(db.Model):

    __tablename__ = 'operate_log'

    id = db.Column(db.Text, primary_key=True, doc='日志ID')
    operate_type = db.Column(db.Text, doc='操作类型')
    describe = db.Column(db.Text, doc='日志描述')

    # 关联操作人员    
    operator = db.relationship('User', backref='opertes')
    operator_id = db.Column(db.Text, db.ForeignKey('user.id'))

    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')