'''
author:AHAO
createTime:2024/09/19
description: ozon订单模型
'''

from Models import db
import datetime
from Models.User.user_model import User


# ozon采购 ozon商品 中间表
class OzonOrderOzonProduct(db.Model):

    __tablename__ = 'ozon_order_ozon_product'

    order_id = db.Column(db.Text, db.ForeignKey('ozon_order.id'), primary_key=True)
    product_id = db.Column(db.Text, db.ForeignKey('ozon_product.id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)  # 单个商品出售数量的字段

class OzonOrder(db.Model):

    __tablename__ = 'ozon_order'
    
    id = db.Column(db.Text, primary_key=True, doc='系统生成id')
    # ozon订单信息赋值
    order_id = db.Column(db.Text, unique=True, doc='ozon中订单id')
    order_number = db.Column(db.Text, unique=True, doc='订单号')
    posting_number = db.Column(db.Text, doc='货件号')
    posting_status = db.Column(db.Text, doc='货运状态')
    logistics_status = db.Column(db.Text, doc='物流状态')
    delivery_id = db.Column(db.Text, doc='快递id')
    delivery_name = db.Column(db.Text, doc='快递名称')
    delivery_tpl_provider_type = db.Column(db.Text, doc='快递服务集成类型')
    delivery_tpl_provider_id = db.Column(db.Text, doc='快递服务id')
    delivery_tpl_provider_name = db.Column(db.Text, doc='快递服务名称')
    warehouse_id = db.Column(db.Text, doc='仓库id')
    warehouse_name = db.Column(db.Text, doc='仓库名称')
    tracking_number = db.Column(db.Text, doc='国际运单号')
    customer_id = db.Column(db.Text, doc='买家id')
    customer_name = db.Column(db.Text, doc='买家姓名')
    address_city = db.Column(db.Text, doc='快递城市')

    # 自定义字段
    total_price = db.Column(db.Text, doc='订单总价')
    system_status = db.Column(db.Text, doc='系统中状态')

    # 关联ozon产品
    ozon_products_msg = db.relationship('OzonOrderOzonProduct', backref='ozon_order')
    
    # 关联店铺
    shop_id = db.Column(db.Text, db.ForeignKey('shop.id'))

    # 关联创建者
    creator = db.relationship('User', backref='ozon_orders')
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))

    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')