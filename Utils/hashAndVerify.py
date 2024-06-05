'''
author:AHAO
createTime:2024/05/31 12:15
description: 哈希加密 验证
'''

from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(password):
    return generate_password_hash(password)

def verify_password(hashed_password, password):
    return check_password_hash(hashed_password, password)

if __name__ == "__main__":
    print(hash_password("123456"))
    print("---")
    print(verify_password(hash_password("123456"),"123456"))
