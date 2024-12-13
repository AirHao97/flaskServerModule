'''
author:AHAO
createTime:2024/05/30 8:56
description: 刀具CRUD接口
'''

from flask import Blueprint,jsonify,request
from Models import db
import uuid
from flask_jwt_extended import jwt_required,get_jwt_identity
from sqlalchemy import or_
from datetime import datetime,timedelta
import pytz
from decimal import Decimal
import json
import pandas as pd
from io import BytesIO

from Utils.crud import getDataFromDataBase_BaseData,addDataFromDataBase,modifyDataFromDataBase,deleteDataFromDataBase
from Utils.apiRightsDecorator import admin_required,operations_required,active_required
from Utils.logWriter import operate_log_writer_func,operate_log_writer_dec
from Utils.Constant.operateType import OperateType
from Utils.Constant.systemStatus import SystemStatus
from Utils.Constant.purchaseStatus import PurchaseStatus
from Utils.Constant.purchaseProductStatus import PurchaseProductStatus

from Models.User.user_model import User
from Models.Work.shop_model import Shop 
from Models.Work.ozon_order_model import OzonOrder 
from Models.Work.purchase_order_model import PurchaseOrder


general_list = Blueprint('general', __name__, url_prefix='/general')


# 查询财务分析数据
@general_list.route('/getFinaceAnalysisData', methods=['POST'])
@jwt_required()
@active_required
def getFinaceAnalysisData():

    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if not current_user:
        return jsonify({"msg": "未找到对应用户！"}), 400

    data = request.get_json()

    if "dateRange" in data:
        try:
            start_date = datetime.strptime(data['dateRange'][0], "%Y-%m-%d")
            end_date = datetime.strptime(data['dateRange'][1], "%Y-%m-%d")  + timedelta(days=1) - timedelta(seconds=1)
            
            utc = pytz.UTC
            start_date_utc =utc.localize(datetime.strptime(data['dateRange'][0], "%Y-%m-%d"))
            end_date_utc = utc.localize(datetime.strptime(data['dateRange'][1], "%Y-%m-%d")  + timedelta(days=1) - timedelta(seconds=1))

        except ValueError:
            return jsonify({"msg": "时间范围格式错误！"}), 400
    else:
        return jsonify({"msg": "时间范围不能为空！"}), 401


    if current_user.is_admin:
        OzonOrder_query = OzonOrder.query
        purchase_order_query = PurchaseOrder.query
    elif current_user.department and (current_user.is_department_admin or any(role.id == "4" for role in current_user.roles)):
        OzonOrder_query = OzonOrder.query.join(Shop, OzonOrder.shop_id == Shop.id).join(User,Shop.owner_id == User.id).filter(User.department_id == current_user.department_id)
        purchase_order_query = PurchaseOrder.query.filter_by(department_id=current_user.department_id)
    else:
        return {"msg":"当前账户无操作权限！"},400
    
    OzonOrders = OzonOrder_query.filter(
        OzonOrder.in_process_at.between(start_date_utc, end_date_utc),
        OzonOrder.system_status != SystemStatus.cancelled
    ).all()

    purchase_orders = purchase_order_query.filter(
        PurchaseOrder.create_time.between(start_date, end_date),
        PurchaseOrder.status != PurchaseStatus.cancelled
    ).all()

    # 拼接数据
    result = {
        # 总体数据
        "summary": {
            "ozonOrder":{
                "quantity_order": 0,
                "quantity_product": 0,
                "rmbData": Decimal(0),
                "usdData": Decimal(0),
            },
            "purchaseOrder":{
                "quantity_order": 0,
                "quantity_product": 0,
                "price": Decimal(0),
            }
        },
        # 销售趋势（天）
        "salesTrend": {},
        # 采购趋势（天）
        "purchaseTrend":{},
        # 店铺数据
        "shopSalesData":{},
        # 运营销售额排名
        "operationSalesgData":{},
        # 商品数据
        "ozonProductsData":{}
    }

    for ozon_order in OzonOrders:
        
        result["summary"]["ozonOrder"]["quantity_order"] += 1

        # 销售趋势（天）

        in_process_at = datetime.strptime(ozon_order.in_process_at, "%Y-%m-%dT%H:%M:%SZ")
        create_time = (in_process_at + timedelta(hours=8)).date().strftime("%Y-%m-%d")
        
        if create_time in result["salesTrend"]:
            result["salesTrend"][create_time]["quantity_order"] += 1
        else:
            result["salesTrend"][create_time] = {
                "rmbData": Decimal(0),
                "usdData": Decimal(0),
                "quantity_order": 1,
                "quantity_product": 0
            }
        # 店铺数据
        shop = ozon_order.shop
        if shop.id in result["shopSalesData"]:
            result["shopSalesData"][shop.id]["quantity_order"] += 1
        else:
            result["shopSalesData"][shop.id] = {
                "name": shop.name,
                "rmbData": Decimal(0),
                "usdData": Decimal(0),
                "quantity_order": 1,
                "quantity_product": 0
            }
        # 运营销售额排名
        owner = ozon_order.shop.owner
        if owner:
            if owner.id in result["operationSalesgData"]:
                result["operationSalesgData"][owner.id]["quantity_order"] += 1
            else:
                result["operationSalesgData"][owner.id] = {
                    "name": owner.username,
                    "rmbData": Decimal(0),
                    "usdData": Decimal(0),
                    "quantity_order": 1,
                    "quantity_product": 0
                }        
        
        if ozon_order.currency_code == "USD":
            result["summary"]["ozonOrder"]["usdData"] += Decimal(ozon_order.total_price)
            result["salesTrend"][create_time]["usdData"] += Decimal(ozon_order.total_price)
            result["shopSalesData"][shop.id]["usdData"] += Decimal(ozon_order.total_price)
            if owner:
                result["operationSalesgData"][owner.id]["usdData"] += Decimal(ozon_order.total_price)

        elif ozon_order.currency_code == "CNY":
            result["summary"]["ozonOrder"]["rmbData"] += Decimal(ozon_order.total_price)
            result["salesTrend"][create_time]["rmbData"] += Decimal(ozon_order.total_price)
            result["shopSalesData"][shop.id]["rmbData"] += Decimal(ozon_order.total_price)
            if owner:
                result["operationSalesgData"][owner.id]["rmbData"] += Decimal(ozon_order.total_price)

        for ozon_product_msg in ozon_order.ozon_products_msg:
            ozon_product = ozon_product_msg.ozon_product
            quantity = ozon_product_msg.quantity

            result["summary"]["ozonOrder"]["quantity_product"] += int(quantity)
            result["salesTrend"][create_time]["quantity_product"] += int(quantity)
            result["shopSalesData"][shop.id]["quantity_product"] += int(quantity)
            if owner:
                result["operationSalesgData"][owner.id]["quantity_product"] += int(quantity)

            if ozon_product.id in result["ozonProductsData"]:
                result["ozonProductsData"][ozon_product.id]["quantity_product"] += int(quantity)
            else:
                result["ozonProductsData"][ozon_product.id] = {
                    "name": ozon_product.name,
                    "offer_id": ozon_product.offer_id,
                    "sku": ozon_product.sku,
                    "rmbData":Decimal(0),
                    "usdData":Decimal(0),
                    "quantity_product": int(quantity)
                }
            
            if ozon_order.currency_code == "USD":
                result["ozonProductsData"][ozon_product.id]["usdData"] += Decimal(ozon_product.price)
            elif ozon_order.currency_code == "CNY":
                result["ozonProductsData"][ozon_product.id]["rmbData"] += Decimal(ozon_product.price)
        
    

    for purchase_order in purchase_orders:

        quantity = len([item for item in purchase_order.purchase_products if item.status != PurchaseProductStatus.loss])

        if purchase_order.price:
            result["summary"]["purchaseOrder"]["quantity_order"] += 1
            result["summary"]["purchaseOrder"]["quantity_product"] += int(quantity)
            result["summary"]["purchaseOrder"]["price"] += Decimal(purchase_order.price)

            # 采购趋势（天）
            create_time = purchase_order.create_time.strftime("%Y-%m-%d")
            if create_time in result["purchaseTrend"]:
                result["purchaseTrend"][create_time]["quantity_order"] += 1
                result["purchaseTrend"][create_time]["quantity_product"] += int(quantity)
                result["purchaseTrend"][create_time]["price"] += Decimal(purchase_order.price)
            else:
                result["purchaseTrend"][create_time] = {
                    "price": Decimal(purchase_order.price),
                    "quantity_order": 1,
                    "quantity_product": int(quantity)
                }
    print(result)

    return jsonify({
        "msg":"查询成功！",
        "data":result
    }), 200 

@general_list.route('/updateOzonOrdersWeightStandardWithExcel', methods=['POST'])
@jwt_required()
@active_required
def updateOzonOrdersWeightStandardWithExcel():

    current_user = get_jwt_identity()
    current_user = User.query.filter_by(id=current_user['id']).first()

    if current_user:

        if current_user.is_admin:
            pass
        elif current_user.department and (current_user.is_department_admin or any(role.id == "2" for role in current_user.roles)):
            query = query.filter_by(department_id = current_user.department_id)
        else:
            return {"msg":"当前账户无操作权限！"},400
        
        if 'file' not in request.files:
            return jsonify({'msg': '无上传文件！'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'msg': '无上传文件！'}), 400

        try:
            # 将文件内容解析为 pandas DataFrame
            file_stream = BytesIO(file.read())  # 读取文件内容到内存
            
            def safe_convert_to_decimal(value):
                try:
                    # return Decimal(value)  # 转换成功返回字符串
                    return int(value)
                except:
                    return None  # 无效值返回 None

            # 读取文件并应用转换
            df = pd.read_excel(file_stream, converters={'最小': safe_convert_to_decimal,'最大': safe_convert_to_decimal})

            processed_data = df.to_dict(orient='records')  # 将数据转为字典列表
            processed_data = processed_data

            json_data = {item['名称']: {'min': item['最小'], 'max': item['最大']} for item in processed_data}

            
            # 将字典写入JSON文件
            with open('Utils/Constant/shippingWeightStandard.json', 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            try:
                operate_log_writer_func(operateType=OperateType.ozonOrder, describe=f"操作人:{current_user.username}, 操作:更新ozon重量标准,当前标准：{json_data}")
                return jsonify({
                    "msg":f"ozon重量标准更新成功！",
                }), 200  
            except Exception as e:
                return {"msg":"ozon重量标准更新失败！"}, 400            
        except Exception as e:
            return jsonify({'msg': f'解析excel文件失败！: {str(e)}'}), 400
    else:
        return jsonify({
                    "msg":"未找到对应用户！",
                }), 400