'''
author:AHAO
createTime:2024/09/19
description: ozon产品模型
'''

from Models import db
import datetime
from Models.User.user_model import User
from Models.Work.system_product_model import SystemProduct
from Models.Work.ozon_order_model import OzonOrderOzonProduct

ozon_product_system_product = db.Table('ozon_product_system_product',
    db.Column('ozon_product_id', db.Text, db.ForeignKey('ozon_product.id')),
    db.Column('system_product_id', db.Text, db.ForeignKey('system_product.id'))
)

class OzonProduct(db.Model):

    __tablename__ = 'ozon_product'
    
    id = db.Column(db.Text, primary_key=True, doc='系统生成id')
    # ozon订单信息赋值
    offer_id = db.Column(db.Text, unique=True, doc='产品货号')
    name = db.Column(db.Text, unique=True, doc='产品名称')
    price = db.Column(db.Text, doc='产品价格')

    currency_code = db.Column(db.Text, doc='产品价格货币')
    sku = db.Column(db.Text, doc='产品Sku')
    link = db.Column(db.Text, doc='产品链接')
    mandatory_mark = db.Column(db.Text, doc='产品属性标签')
    primary_image = db.Column(db.Text, doc='产品主图')
    product_id = db.Column(db.Text, doc='ozon中产品id')

    # 关联ozon订单
    ozon_orders_msg = db.relationship('OzonOrderOzonProduct', backref='ozon_product')

    # 关联系统中创建的商品
    system_products = db.relationship('SystemProduct', secondary=ozon_product_system_product, backref='ozon_products')

    # 关联创建者
    creator = db.relationship('User', backref='ozon_products')
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))
    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')