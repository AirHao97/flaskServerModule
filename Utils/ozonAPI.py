import requests
import json

# api_id = '221854'
# api_key = '48d6d7e7-7842-4f21-a5a2-896dea7cd734'

# api_id = '767055'
# api_key = '02c837e4-abfa-4779-ba7b-0cd06a22c058'

max_wait_time = 60

# 根据订单id获取订单数据
def getOrderByOrderId(api_id,api_key,order_id):
    headers = {
        'Client-Id': api_id,
        'Api-Key': api_key,
        'Content-Type': 'application/json'
    }

    # 货件列表（第三版）
    url = 'https://api-seller.ozon.ru/v3/posting/fbs/list'

    data = {
        "dir": "ASC",
        "filter": {
            "since": "2024-01-01T00:00:00Z",
            "to": "2024-09-16T23:59:59Z",
            "order_id": order_id
        },
        "limit": 1,
        "offset": 0,
        "with": {
            "analytics_data": True,
            "financial_data": True
        }
    }

    # 发送请求
    response = requests.post(url, headers=headers, json=data, timeout=max_wait_time)

    # 检查响应状态码
    if response.status_code == 200:
        # 解析响应 JSON 数据
        orders = response.json()
        result = orders['result']['postings']
        offer_ids = []

        for index,item in enumerate(result):
            print(f"-----订单{index+1}-----")
            print(f"订单ID: {item['order_id']}")
            print(f"订单号: {item['order_number']}")
            print(f"货件号: {item['posting_number']}")
            print(f"货运状态: {item['status']}")
            print(f"发货子状态: {item['substatus']}")

            # 快递相关
            print(f"快递ID: {item['delivery_method']['id']}")
            print(f"快递名称: {item['delivery_method']['name']}")
            print(f"快递服务集成类型: {item['tpl_integration_type']}")
            print(f"快递服务ID: {item['delivery_method']['tpl_provider_id']}")
            print(f"快递服务名称: {item['delivery_method']['tpl_provider']}")
            print(f"仓库ID: {item['delivery_method']['warehouse_id']}")
            print(f"仓库名称: {item['delivery_method']['warehouse']}")
            print(f"货件跟踪号: {item['tracking_number']}")

            # 产品相关
            print(f"产品数量: {len(item['products'])}")

            for i in range(len(item['products'])):
                print(f"{i+1}号产品")
                print(f"  -产品货号: {item['products'][i]['offer_id']}")
                print(f"  -产品名称: {item['products'][i]['name']}")
                print(f"  -产品价格: {item['products'][i]['price']}")
                print(f"  -产品数量： {item['products'][i]['quantity']}")
                print(f"  -产品价格货币: {item['products'][i]['currency_code']}")
                print(f"  -产品SKU: {item['products'][i]['sku']}")
                print(f"  -产品强制性标签: {item['products'][i]['mandatory_mark']}")

                offer_ids.append(item['products'][i]['offer_id'])

        return offer_ids
        
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)

# 获取订单数据
def getOrders(api_id,api_key,sinceTime,toTime,limit=100,offset=0):

    headers = {
        'Client-Id': api_id,
        'Api-Key': api_key,
        'Content-Type': 'application/json'
    }
    
    # 货件列表（第三版）
    url = 'https://api-seller.ozon.ru/v3/posting/fbs/list'

    data = {
        "dir": "ASC",
        "filter": {
            "since": sinceTime,
            "to": toTime,
            # "status": "awaiting_packaging",
        },
        "limit": limit,
        "offset": offset,
        "with": {
            "analytics_data": True,
            "financial_data": True,
            "barcodes": True
        }
    }

    # 发送请求
    response = requests.post(url, headers=headers, json=data, timeout=max_wait_time)

    # 检查响应状态码
    if response.status_code == 200:
        # 解析响应 JSON 数据
        orders = response.json()
        result = orders['result']
        return {"data":result, "msg":"响应成功！","code":200}
        
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)
        return {"data":None, "msg":response.text, "code":400}


# 获取产品详情
def getProductInfo(api_id,api_key,sku):

    headers = {
        'Client-Id': api_id,
        'Api-Key': api_key,
        'Content-Type': 'application/json'
    }

    url = 'https://api-seller.ozon.ru/v2/product/info'

    data = {
        "sku": sku
    }

    response = requests.post(url, headers=headers, json=data, timeout=max_wait_time)

    if response.status_code == 200:
        # 解析响应 JSON 数据
        result = response.json()

        return {"data":result, "msg":"响应成功！","code":200}
        
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)
        return {"data":None, "msg":response.text, "code":400}


# 订单装配/分装 申请国际运单号
def orderShip(api_id,api_key,posting_number,packages):

    headers = {
        'Client-Id': api_id,
        'Api-Key': api_key,
        'Content-Type': 'application/json'
    }

    url = 'https://api-seller.ozon.ru/v4/posting/fbs/ship'

    data = {
        "posting_number": posting_number,
        "packages":packages,
        # "posting_number": "0180237425-0001-1",
        # "packages": [
        #     {
        #         "products": [
        #             {
        #                 "product_id": 1415100530,
        #                 "quantity": 4
        #             }
        #         ]
        #     },
        #     {
        #         "products": [
        #             {
        #                 "product_id": 1524550949,
        #                 "quantity": 1
        #             }
        #         ]
        #     }
        # ],
        "with": {
            "additional_data": True
        }
    }

    response = requests.post(url, headers=headers, json=data, timeout=max_wait_time)

    if response.status_code == 200:
        # 解析响应 JSON 数据
        result = response.json()

        return {"data":result, "msg":"响应成功！","code":200}
        
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)
        return {"data":None, "msg":response.text, "code":400}


# 获取属性指南
def getAttribute(api_id,api_key):

    headers = {
        'Client-Id': api_id,
        'Api-Key': api_key,
        'Content-Type': 'application/json'
    }

    url = 'https://api-seller.ozon.ru/v1/description-category/attribute'


    data = {
        "description_category_id": 7117,
        "language": "ZH_HANS",
        "type_id": 1
    }

    response = requests.post(url, headers=headers, json=data, timeout=max_wait_time)

    if response.status_code == 200:
        # 解析响应 JSON 数据
        orders = response.json()
        print(orders)


    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)


def getProductAttributes(api_id,api_key,offer_id):

    headers = {
        'Client-Id': api_id,
        'Api-Key': api_key,
        'Content-Type': 'application/json'
    }

    url = 'https://api-seller.ozon.ru/v3/products/info/attributes'

    data = {
        "filter": {
            "offer_id": [
                offer_id
            ],
        "visibility": "ALL"
        },
        "limit": 1,
        "sort_dir": "ASC"
    }

    response = requests.post(url, headers=headers, json=data, timeout=max_wait_time)

    if response.status_code == 200:
        # 解析响应 JSON 数据
        result = response.json()

        return {"data":result, "msg":"响应成功！","code":200}
        
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)
        return {"data":None, "msg":response.text, "code":400}


if __name__ == "__main__":
    # api_id = "767055"
    # api_key = "02c837e4-abfa-4779-ba7b-0cd06a22c058"
    getOrders(
        api_id = "1892609",
        api_key = "c89ecffa-4fef-471c-a5c2-068cd2321754",
        sinceTime="2024-10-01T00:00:00Z", 
        toTime="2024-10-18T23:59:59Z",
        limit=1000,
        offset=0
    )
    # getProductInfo(
    #     api_id = "221854",
    #     api_key = "48d6d7e7-7842-4f21-a5a2-896dea7cd734",
    #     # sku = "1409365448"
    #     sku = "1409365448"
    # )
    # getAttribute(
    #     api_id = "221854",
    #     api_key = "48d6d7e7-7842-4f21-a5a2-896dea7cd734",
    # )
    # getProductAttributes(
    #     api_id = "221854",
    #     api_key = "48d6d7e7-7842-4f21-a5a2-896dea7cd734",
    #     offer_id = "BCO-0805-qxnk"
    # )
    # orderShip(
    #     api_id = "767055",
    #     api_key = "02c837e4-abfa-4779-ba7b-0cd06a22c058",
    #     packages = []
    # )
    pass