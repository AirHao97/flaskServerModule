'''
author:AHAO
createTime:2024/05/30 10:17
description: 项目配置文件
'''

class Config(object):
    
    SECRET_KEY = 'hgznyjy'


    # 数据库位置   
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dataBase.db'
    # 动态追踪修改
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 显示生成的sql语句
    SQLALCHEMY_ECHO = True
    
    # 图片存储地址
    UPLOAD_FOLDER_PIC = "Public//Pic"