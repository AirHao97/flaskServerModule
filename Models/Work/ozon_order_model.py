'''
author:AHAO
createTime:2024/09/19
description: ozon订单模型
'''

from Models import db
import datetime
from Models.User.user_model import User
from Models.Work.purchase_product_model import PurchaseProduct


# ozon采购 ozon商品 中间表
class OzonOrderOzonProduct(db.Model):

    __tablename__ = 'ozon_order_ozon_product'

    order_id = db.Column(db.Text, db.ForeignKey('ozon_order.id'), primary_key=True)
    product_id = db.Column(db.Text, db.ForeignKey('ozon_product.id'), primary_key=True)
    price = db.Column(db.Text, nullable=False, doc='单个商品此时的售价')
    quantity = db.Column(db.Integer, nullable=False, doc="单个商品出售数量")

class OzonOrder(db.Model):

    __tablename__ = 'ozon_order'
    
    id = db.Column(db.Text, primary_key=True, doc='系统生成id')
    # ozon订单信息赋值
    order_id = db.Column(db.Text, doc='ozon中订单id')
    order_number = db.Column(db.Text, doc='订单号')
    posting_number = db.Column(db.Text, unique=True, doc='货件号')
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
    in_process_at = db.Column(db.Text, doc='开始处理货件的日期和时间')
    shipment_date = db.Column(db.Text, doc='必须收取货件的日期和时间')
    delivering_date = db.Column(db.Text, doc='货件交付物流的时间')
    cancel_reason = db.Column(db.Text, doc='订单取消原因')
    cancellation_type = db.Column(db.Text, doc='取消类型 客户/ozon/卖家')
    currency_code = db.Column(db.Text, doc='价格货币')
    
    # 自定义字段
    total_price = db.Column(db.Text, doc='订单总价')
    system_status = db.Column(db.Text, doc='系统中状态')
    approval_time = db.Column(db.DateTime, doc='通过运营审核时间')
    dispatch_time = db.Column(db.DateTime, doc='出库时间')

    # 关联ozon产品
    ozon_products_msg = db.relationship('OzonOrderOzonProduct', backref='ozon_order')
    # 关联店铺
    shop_id = db.Column(db.Text, db.ForeignKey('shop.id'))

    # 关联采购商品
    purchase_products = db.relationship('PurchaseProduct', backref='ozon_order')

    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')