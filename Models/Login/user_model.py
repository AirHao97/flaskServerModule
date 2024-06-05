'''
author:AHAO
createTime:2024/05/30 10:16
description: 登陆数据库模型
'''

from Models import db
import datetime
import Utils.hashAndVerify as hashAndVerify

class User(db.Model):

    __tablename__ = 'user'

    id = db.Column(db.Text, primary_key=True, doc='用户ID')
    username = db.Column(db.Text, unique=True, doc='用户账号')
    passward = db.Column(db.Text, doc='用户密码')
    email = db.Column(db.Text, unique=True, doc='用户邮箱')
    telephone_number = db.Column(db.Text, unique=True, doc='用户手机号')

    is_admin = db.Column(db.Boolean, default=False, doc='是否为管理员')
    is_active = db.Column(db.Boolean, default=True, doc='账户是否激活')
    power_arange = db.Column(db.Text, nullable=True, doc='修改权限范围')

    last_login_time = db.Column(db.DateTime, doc='上一次登陆时间')
    create_time = db.Column(db.DateTime, default = datetime.datetime.now, doc='创建时间')
    modify_time = db.Column(db.DateTime, onupdate = datetime.datetime.now, doc='修改时间')

    def set_password(self, password):
        """设置用户密码"""
        self.passward = hashAndVerify.hash_password(password)

    def check_password(self, password):
        """检查密码是否正确"""
        return hashAndVerify.verify_password(self.passward, password)