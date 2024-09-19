'''
author:AHAO
createTime:2024/09/19
description: ozon订单模型
'''

from Models import db
import datetime
from Models.User.user_model import User

class PurchaseOrderSystemProduct(db.Model):

    __tablename__ = 'purchase_order_system_product'

    purchase_order_id = db.Column(db.Text, db.ForeignKey('purchase_order.id'), primary_key=True)
    system_product_id = db.Column(db.Text, db.ForeignKey('system_product.id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)  # 单个商品出售数量的字段


class PurchaseOrder(db.Model):

    __tablename__ = 'purchase_order'
    
    id = db.Column(db.Text, primary_key=True, doc='采购id')
    product_id = db.Column(db.Text, doc='采购单号')
    price = db.Column(db.Text, doc='产品价格')
    posting_number = db.Column(db.Text, doc='国内运单号')
    logistics_status = db.Column(db.Text, doc='物流状态')
    # 1688 pdd 线下
    type = db.Column(db.Text, doc='采购类型')
    
    # 关联系统中维护的商品表
    system_products_msg = db.relationship('PurchaseOrderSystemProduct', backref='purchase_order')


    # 关联创建者
    creator = db.relationship('User', backref='ozon_products')
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))
    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')