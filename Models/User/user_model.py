'''
author:AHAO
createTime:2024/05/30
description: 登陆数据库模型
'''

from Models import db
import datetime
import Utils.hashAndVerify as hashAndVerify

partners_orders_association = db.Table('partners_orders',
    db.Column('user_id', db.Text, db.ForeignKey('user.id'), primary_key=True),
    db.Column('partner_id', db.Text, db.ForeignKey('user.id'), primary_key=True)
)

partners_system_products_association = db.Table('partners_system_products',
    db.Column('user_id', db.Text, db.ForeignKey('user.id'), primary_key=True),
    db.Column('partner_id', db.Text, db.ForeignKey('user.id'), primary_key=True)
)

class User(db.Model):

    __tablename__ = 'user'

    id = db.Column(db.Text, primary_key=True, doc='用户ID')
    username = db.Column(db.Text, unique=True, doc='用户账号')
    passwo9rd = db.Column(db.Text, doc='用户密码')
    email = db.Column(db.Text, doc='用户邮箱')
    telephone_number = db.Column(db.Text, doc='用户手机号')
    is_admin = db.Column(db.Boolean, default=False, doc='是否为管理员')
    is_active = db.Column(db.Boolean, default=True, doc='账户是否激活')

    # 关联关系伙伴
    partners_orders = db.relationship(
        'User', secondary=partners_orders_association, 
        primaryjoin='User.id == partners_orders_association.user_id',
        secondaryjoin='User.id == partners_orders_association.partner_id',
        backref='partner_orders_of'
    )
    
    partners_system_products = db.relationship(
        'User', secondary=partners_system_products_association, 
        primaryjoin='User.id == partners_system_products_association.user_id',
        secondaryjoin='User.id == partners_system_products_association.partner_id',
        backref='partner_system_products_of'
    )

    # 关联部门
    department_id = db.Column(db.Text, db.ForeignKey('department.id'))

    last_login_time = db.Column(db.DateTime, doc='上一次登陆时间')
    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')

    def set_password(self, password):
        """设置用户密码"""
        self.password = hashAndVerify.hash_password(password)

    def check_password(self, password):
        """检查密码是否正确"""
        return hashAndVerify.verify_password(self.passward, password)