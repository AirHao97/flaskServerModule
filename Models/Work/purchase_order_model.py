'''
author:AHAO
createTime:2024/09/19
description: ozon订单模型
'''

from Models import db
import datetime
from Models.User.user_model import User

class PurchaseOrder(db.Model):

    __tablename__ = 'purchase_order'
    
    id = db.Column(db.Text, primary_key=True, doc='采购id')
    purchase_id = db.Column(db.Text, doc='采购单号')
    quantity = db.Column(db.Text, doc='产品数量')
    price = db.Column(db.Text, doc='产品价格')
    order_id = db.Column(db.Text, doc='暂不使用')
    posting_numbers = db.Column(db.Text, doc='国内运单号')
    logistics_status = db.Column(db.Text, doc='物流状态')
    # 1688 pdd 线下
    purchase_platform = db.Column(db.Text, doc='采购平台')
    # 采购状态
    status = db.Column(db.Text, doc='采购状态')

    # 关联系统中维护的商品表
    system_product_id = db.Column(db.Text, db.ForeignKey('system_product.id'))
    # 关联部门
    department_id = db.Column(db.Text, db.ForeignKey('department.id'))

    # 关联创建者
    creator = db.relationship('User', backref='purchase_orders')
    creator_id = db.Column(db.Text, db.ForeignKey('user.id'))
    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')