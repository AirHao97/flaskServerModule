
'''
author:AHAO
createTime:2024/09/19
description: ozon订单模型
'''

from Models import db
import datetime
from Models.Work.ozon_order_model import OzonOrder
from Models.Work.ozon_product_model import OzonProduct
from Models.User.user_model import User


class Shop(db.Model):

    __tablename__ = 'shop'
    
    id = db.Column(db.Text, primary_key=True, doc='店铺id')
    name = db.Column(db.Text, unique=True, doc='店铺名字')
    api_id = db.Column(db.Text, unique=True, nullable=False, doc='ozonApiId')
    api_key = db.Column(db.Text, unique=True, nullable=False, doc='ozonApiKey')

    # 关联ozon订单
    ozon_orders = db.relationship("OzonOrder", backref='shop')

    # 关联ozon产品
    ozon_products = db.relationship("OzonProduct", backref='shop')

    # 关联店铺拥有人
    owner_id = db.Column(db.Text, db.ForeignKey('user.id'))
    owner = db.relationship('User', backref='owner_shops',foreign_keys=[owner_id])


    # 关联创建者
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))
    creator = db.relationship('User', backref='create_shops',foreign_keys=[creator_id])


    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')