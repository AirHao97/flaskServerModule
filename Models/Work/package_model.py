
'''
author:AHAO
createTime:2024/09/19
description: 麻袋模型
'''

from Models import db
import datetime
from Models.Work.purchase_product_model import PurchaseProduct
from Models.User.user_model import User


class Package(db.Model):

    __tablename__ = 'package'
    
    id = db.Column(db.Text, primary_key=True, doc='麻袋id')
    sku = db.Column(db.Text, unique=True, doc='麻袋sku')

    # 关联采购商品
    purchase_products = db.relationship("PurchaseProduct", backref='package')

    # 关联创建者
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))
    creator = db.relationship('User', backref='packages',foreign_keys=[creator_id])

    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')