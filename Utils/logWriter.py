from functools import wraps
from flask_jwt_extended import get_jwt
from flask import jsonify
import uuid

from Models import db
from Models.Log.operate_log_model import OperateLog


# 操作日志记录函数
def operate_log_writer_func(operateType,describe,isSystem=False):
    
    log = OperateLog()
    log.id =  str(uuid.uuid1())
    log.operate_type = operateType
    log.describe = describe

    if not isSystem:
        current_user = get_jwt()
        log.operator_id = current_user["id"]

    try:
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"日志新增失败。错误代码：{e}")

# 操作日志记录装饰器
def operate_log_writer_dec(operateType,describe,isSystem=False):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):

            log = OperateLog()
            log.id =  str(uuid.uuid1())
            log.operate_type = operateType
            log.describe = describe

            if not isSystem:
                current_user = get_jwt()
                log.operator_id = current_user["id"]

            try:
                db.session.add(log)
                db.session.commit()
            except Exception as e:
                print(f"日志新增失败。错误代码：{e}")

            return fn(*args, **kwargs)

        return wrapper
    return decorator