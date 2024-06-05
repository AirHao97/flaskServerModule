'''
author:AHAO
createTime:2024/05/30 13:29
description: 动态加载蓝图对象
'''

import os
import importlib.util

def add_blueprint(folder_path):
    BluePrintList = []
   # 遍历文件夹下的所有项
    for item in os.listdir(folder_path):
        # 检查项是否为文件夹
        if os.path.isdir(os.path.join(folder_path, item)):
            # 获取子文件夹的路径
            subfolder_path = os.path.join(folder_path, item)
            # 遍历子文件夹下的所有文件
            for filename in os.listdir(subfolder_path):
                # 检查文件是否为Python文件
                if filename.endswith('.py') and filename != '__init__.py':
                    # 构建模块名（去掉.py扩展名）
                    module_name = filename[:-3]
                    # 构建文件的完整路径
                    file_path = os.path.join(subfolder_path, filename)
                    # 导入模块
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    print(f'Imported {module_name} from {subfolder_path}')

                    if hasattr(module, module_name+"_list"):
                        var_value = getattr(module, module_name+"_list")
                        BluePrintList.append(var_value)
                    else:
                        print(f"No variable named {module_name+'_list'} found in {file_path}")

    return BluePrintList