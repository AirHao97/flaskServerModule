'''
author:AHAO
createTime:2024/06/13 16:46
description: 获取静态资源
'''

from flask import Blueprint,make_response,render_template, request, jsonify
from flask_jwt_extended import jwt_required
import config
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import config

static_list = Blueprint('static', __name__)

# 图片上传接口
@static_list.route('/pic/upload', methods=['POST'])
def upload_file():
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    if 'file' not in request.files:
        return jsonify({"code": 400, "msg": "没有发现文件"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"code": 400, "msg": "未选择文件"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # 使用时间戳生成唯一文件名，避免重名
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(config.Config.UPLOAD_FOLDER_PIC, new_filename)
        # 保存文件到上传目录
        file.save(file_path)
        # 返回图片 URL
        file_url = f"/pic/{new_filename}"

        return jsonify({"code": 200, "msg": "上传成功", "data": {"url": file_url}})

    return jsonify({"code": 400, "msg": "文件类型不允许"}), 400


@static_list.route('/pic/<filename>')
def uploaded_file(filename):
    # 根据文件名返回图片
    try:
        with open(config.Config.UPLOAD_FOLDER_PIC+ '/' + filename, 'rb') as img_file:
            img_data = img_file.read()
        response = make_response(img_data)
        response.headers['Content-Type'] = 'image/jpeg'
        return response
    except Exception as e:
        return "None"