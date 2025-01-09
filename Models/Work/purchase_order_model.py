'''
author:AHAO
createTime:2024/09/19
description: ozon订单模型
'''

from Models import db
import datetime
from Models.User.user_model import User
from Models.Work.purchase_product_model import PurchaseProduct

class PurchaseOrder(db.Model):

    __tablename__ = 'purchase_order'
    
    id = db.Column(db.Text, primary_key=True, doc='采购id')
    purchase_id = db.Column(db.Text, doc='采购单号')
    fill_purchase_id_time = db.Column(db.DateTime, doc='采购单号回填时间')
        
    price = db.Column(db.Text, doc='订单价格')
    shipping_fee = db.Column(db.Text, doc='运费')
    back_fee = db.Column(db.Text, doc='退货费')

    posting_numbers = db.Column(db.Text, doc='国内运单号')

    # 物流
    logistics_status = db.Column(db.Text, doc='物流状态')


    packer_msg = db.Column(db.Text, doc='打包入库异常留言')
    packer_msg_date = db.Column(db.DateTime, doc='打包入库异常留言时间')

    mark = db.Column(db.Text, doc='采购自己的备注')


    # 1688 pdd 线下
    purchase_platform = db.Column(db.Text, doc='采购平台')
    # 采购状态
    status = db.Column(db.Text, doc='采购状态')
    # 采购子状态
    platform_status = db.Column(db.Text, doc='采购平台状态')

    is_error = db.Column(db.Boolean, default=False, doc='采购/入库 是否有异常')
    error_words = db.Column(db.Text, doc='采购咨询运营异常留言')
    
    now_turn = db.Column(db.Text, doc='当前留言的人是谁  运营/采购')

    # 关联订单采购人
    purchaser_id = db.Column(db.Text, db.ForeignKey('user.id'))
    purchaser = db.relationship('User', backref='purchase_orders',foreign_keys=[purchaser_id])



    # 关联系统中维护的商品表
    system_product_id = db.Column(db.Text, db.ForeignKey('system_product.id'))
    # 关联部门
    department_id = db.Column(db.Text, db.ForeignKey('department.id'))
    # 关联采购的具体商品
    purchase_products = db.relationship('PurchaseProduct', backref='purchase_order', cascade='all, delete-orphan')

    # 关联创建者
    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')