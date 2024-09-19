
'''
author:AHAO
createTime:2024/09/19
description: ozon订单模型
'''

from Models import db
import datetime
from Models.Work.ozon_order_model import OzonOrder
from Models.User.user_model import User


class Shop(db.Model):

    __tablename__ = 'shop'
    
    id = db.Column(db.Text, primary_key=True, doc='店铺id')
    name = total_price = db.Column(db.Text, unique=True, doc='店铺名字')
    api_id = total_price = db.Column(db.Text, doc='ozonApiId')
    api_key = total_price = db.Column(db.Text, doc='ozonApiKey')

    # 关联ozon订单
    ozon_orders = db.relationship("OzonOrder", backref='shop')

    # 关联创建者
    creator = db.relationship('User', backref='shops')
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))

    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')