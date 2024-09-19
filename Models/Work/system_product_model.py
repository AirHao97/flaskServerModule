'''
author:AHAO
createTime:2024/09/19
description: ozon订单模型
'''

from Models import db
import datetime
from Models.User.user_model import User
from Models.Work.purchase_order_model import PurchaseOrderSystemProduct

class SystemProduct(db.Model):

    __tablename__ = 'system_product'
    
    id = db.Column(db.Text, primary_key=True, doc='系统生成id')
    primary_image = db.Column(db.Text, doc='产品主图')
    system_sku = db.Column(db.Text, doc='系统生成的sku,规则:属性1+ +属性2+ +属性3')

    reference_weight = db.Column(db.Text, unique=True, doc='参考重量(手动)')
    reference_cost = db.Column(db.Text, unique=True, doc='参考价格(手动)')
    
    purchase_mark = db.Column(db.Text, doc='采购备注')
    pack_mark = db.Column(db.Text, doc='打包备注')
    purchase_link = db.Column(db.Text, doc='采购链接')
    supplier_name = db.Column(db.Text, doc='库存量')
    omitted_quantity = db.Column(db.Text, doc='缺货量')
    in_transit_quantity = db.Column(db.Text, doc='在途量')
    purchase_platform = db.Column(db.Text, doc='商品采购平台')

    # 关联ozon产品
    purchase_orders_msg = db.relationship('PurchaseOrderSystemProduct', backref='system_product')

    # 关联创建者
    creator = db.relationship('User', backref='ozon_products')
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))
    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')