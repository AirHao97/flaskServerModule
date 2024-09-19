'''
author:AHAO
createTime:2024/06/13 16:46
description: 获取静态资源
'''

from flask import Blueprint,make_response,render_template
from flask_jwt_extended import jwt_required
import config

static_list = Blueprint('static', __name__)

@static_list.route('/pic/<filename>')
def uploaded_file(filename):
    # 根据文件名返回图片
    with open(config.Config.UPLOAD_FOLDER_PIC+ '/' + filename, 'rb') as img_file:
            img_data = img_file.read()
    response = make_response(img_data)
    response.headers['Content-Type'] = 'image/jpeg'
    return response