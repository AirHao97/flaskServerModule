'''
author:AHAO
createTime:2024/09/19
description: ozon订单模型
'''

from Models import db
import datetime
from Models.User.user_model import User

class PurchaseProduct(db.Model):

    __tablename__ = 'purchase_product'
    
    id = db.Column(db.Text, primary_key=True, doc='系统生成id')

    price = db.Column(db.Text, doc='价格')
    stock_in_date = db.Column(db.DateTime, doc='入库日期')
    stock_out_date = db.Column(db.DateTime, doc='出库日期')
    loss_date = db.Column(db.DateTime, doc='丢失时间')
    sku = db.Column(db.Text, index = True, doc='sku')

    # 非组合单/组合单/未配对
    type = db.Column(db.Text, doc='配对的ozon订单类型')
    
    # 待采购、在途、丢失、在篮、在库、出库
    status = db.Column(db.Text, doc='当前状态')

    # 丢失件备注
    mark = db.Column(db.Text, doc='丢失件的备注')

    # 关联采购订单
    purchase_order_id = db.Column(db.Text, db.ForeignKey('purchase_order.id'))
    # 关联ozon订单
    ozon_order_id = db.Column(db.Text, db.ForeignKey('ozon_order.id'))
    # 关联系统内商品
    system_product_id = db.Column(db.Text, db.ForeignKey('system_product.id'))

    # 关联创建者
    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')