'''
author:AHAO
createTime:2024/09/19
description: ozon订单模型
'''

from Models import db
import datetime
from Models.User.user_model import User
from Models.Work.purchase_order_model import PurchaseOrder
from Models.Work.ozon_product_model import OzonProductSystemProduct

class SystemProduct(db.Model):

    __tablename__ = 'system_product'
    
    id = db.Column(db.Text, primary_key=True, doc='系统生成id')
    primary_image = db.Column(db.Text, doc='产品主图')
    system_sku = db.Column(db.Text, unique=True, doc='系统生成的sku')

    reference_weight = db.Column(db.Text, doc='参考重量(手动)')
    reference_cost = db.Column(db.Text, doc='参考价格(手动)')
    
    purchase_link = db.Column(db.Text, doc='采购链接')
    purchase_platform = db.Column(db.Text, doc='商品采购平台')
    
    price = db.Column(db.Text, doc='采购价格')

    # 如果是1688的话还要关联下面的字段
    supplier_name = db.Column(db.Text, doc='供应商名字')
    productId_1688 = db.Column(db.Text, doc='1688产品id')
    specId_1688 = db.Column(db.Text, doc='1688款式id')
    skuId_1688 = db.Column(db.Text, doc='1688 sku')
    
    # 同一批生成的父类标识
    father_id = db.Column(db.Text, doc='同一批生成的标识id')

    # 关联部门
    department_id = db.Column(db.Text, db.ForeignKey('department.id'))
    # 关联采购订单
    purchase_orders = db.relationship('PurchaseOrder', backref='system_product')
    # 关联ozon产品
    ozon_products_msg = db.relationship('OzonProductSystemProduct', backref='system_product')
    # 关联采购的商品
    purchase_products = db.relationship('PurchaseProduct', backref='system_product')


    # 关联创建者
    creator = db.relationship('User', backref='system_products')
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))
    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')