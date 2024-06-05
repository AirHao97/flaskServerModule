'''
author:AHAO
createTime:2024/05/30 9:59
description: 入口文件 配置实例
'''
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from datetime import timedelta


import config
# from routes import init_routes
from Models import db
from Utils import addBluePrint

def create_app():
    app = Flask(__name__)

    # 跨域配置
    CORS(app, supports_credentials=True)

    # JWT配置
    app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # 用于加密token的密钥
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1) 
    JWTManager(app)

    # 配置数据库
    app.config.from_object(config.Config)
    print()
    # 实例化sqlalchemy对象，传⼊app
    db.init_app(app)
    
    # 数据库迁移配置
    Migrate(app, db)

    # 注册路由(在Model中注册的表单类必须在Routes中被import了至少一次 migrations才会生成对应的表单)
    routes = addBluePrint.add_blueprint("Routes")
    for i in routes:
        app.register_blueprint(i)


    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True,host='0.0.0.0',port=3000)