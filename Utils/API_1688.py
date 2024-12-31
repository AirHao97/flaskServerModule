import requests
import zstandard as zstd
from io import BytesIO 
import re
import json
import chardet
import hashlib
import hmac
import urllib.parse


# 解析1688网页 获取商家、变体等相关数据
def get1688ProductMsg(url):


    # 使用正则表达式提取数字
    match = re.search(r'/offer/(\d+)\.html', url)

    product_id = None

    if match:
        product_id = match.group(1)
    else:
        print("没有找到匹配的内容")

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en;q=0.7,or;q=0.6,om;q=0.5,eu;q=0.4,ms;q=0.3,sa;q=0.2',
         # 'Cookie': 'arms_uid=c3565952-e07a-4ccb-9f27-bf18b0995f29; cna=HpSSHtk2vWMCAXr3nkN8eVqL; taklid=59b7fddbef9f4529b96c061ab4b404e2; _bl_uid=tLmCq24bjpOrp43XFcp3fvCbaRje; xlly_s=1; t=0f8e61c21b62e1cdb428ca1f7a241425; lid=aijay344; ali_apache_track=c_mid=b2b-22150125576829fc40|c_lid=aijay344|c_ms=1|c_mt=1; last_mid=b2b-22150125576829fc40; firstRefresh=1733648235808; aliwwLastRefresh=1733648235905; is_identity=buyer; lastRefresh=1733685964109; dnk=sjhuili8888; tracknick=aijay344; _cc_=URm48syIZQ%3D%3D; cookie2=1c49a704bdd403f7a7fd236700443413; _tb_token_=e1a17db6f33a3; cookie1=AC4I%2FUoOP%2BP26B5IVkFss4pksvZqZ54uLbHid7biitE%3D; cookie17=UUpgQymqFR371ze9Ww%3D%3D; sgcookie=E100%2FaWhVZyMh%2FPfQIGx5loFNH2hjSYVJsHuks0kjkaWrVOyCOn%2FZSuGCjQlwRaSbCqUAEfSv5bxoLLXz3WZ450DC2Nz8rBqrNEi2bsAQqt3OMJ9qBeKpC%2BFDgwINPNme5%2BS; sg=421; csg=f2e72e2d; unb=2215012557682; uc4=nk4=0%40AJNPBtNFexE83xD7Yp4%2FifZU0g%3D%3D&id4=0%40U2gqzJ9zhmeYp%2F3jgNhgtzVE2RbpZoKx; _nk_=aijay344; __cn_logon__=true; __cn_logon_id__=aijay344; _samesite_flag_=true; _csrf_token=1733721906788; mtop_partitioned_detect=1; _m_h5_tk=6a3d5be30e76abd1c2030c581df1b139_1733737147892; _m_h5_tk_enc=8b6b9696d47317b3369d052388047195; _m_h5_c=c975120bfa0021e37129fccf241087eb_1733739152007%3Bef9b1431b011a9524d669f01e228dc9f; x5sec=7b22733b32223a2264346234643064653961616636343634222c226c61707574613b32223a223138333164653935313761653437373235303161643438333834376164613730434b473832726f47454a576e334a6742476738794d6a45314d4445794e5455334e6a67794f7a4577397179704b673d3d227d; _user_vitals_session_data_={"user_line_track":true,"ul_session_id":"ta8haumgpff","last_page_id":"detail.1688.com%2Flvips792xdm"}; JSESSIONID=2E75D2FE373F0EB9D0BDAF72E271794A; tfstk=fGwZFrX7IOBwSe6Xhck2LkxYQPDOkxaVPP2jmmqYDn0iIRT0Tyq01jZmsBxnX2ws5lMiurzUDVMfXAX4gzUylj2jl-SqBJN6hV_t3o4S3a_5FTZTXbHcPawc1xXqBmoMScYX-2mXO2Sr3TZTXHxwogNhFERClq4morciKHmt-mvmorcHKm3HImvimejEJmDmjq00xXmo2EYmnrqhYm3noAX8mlJEVfjJgop-b16fE2qi8LrLwcfPelRXJeeEbfrlR2vmZJoZ_4qgBjmxMD2QLbGBcwk32WaiYYWwycP34Am4HgAqujytLmPd7CazWmqnTPsXMDP4m8HtUnXgYAuZZcl13izuYoVSTJsleAkiSSMTc37_YRz_XJrXmBDZCWlzQYXJSqNQ4-o4HZBUzoq8iXy27goBkDcgP-FwoIcivDu5YMywvZVTGEMlTIdxt9nEPGi6iIYJ3KOaUcdvMXjtY4ssA; isg=BIeGypjzrEgEsCmZ77pUhsX3FjtRjFtu03xnhlklLpUiyIiKe1h8vB7EboiWIDPm',
        "Cookie":'arms_uid=57c05663-5435-45b3-a3ea-0c7150991851; cna=AKXdH6ZqeycCAXPXKCZsE1xl; xlly_s=1; tfstk=fgHjLucSSZbXbNi7SSKzPXddxJe1hq9UHGZtxcBVX-eYfOin5myZXSCR2o4r3ro4HV1sR2ZaklCYyaE0AsIYkoCRyzgAQSuZCbXsxcD2mR-0nm2gBe8eLPimmRxl0XE-hgU8X0BADSQroEWaBe8eL_S8iEytu1X-68i8rlZTWs3Ty8UuAOeTk5QRwkU8WRetW8F8jl1YWtEA2ahPegZ9GrmX4q59duJcFmz5B9s3cSKzX1WhKYZbGAnYPurrFoNbJ7mmYLMxzcHqn7AlaRmrOVGtJU54kXZIPWlXRtgIol373vKMi7VtCAZoZF1_RfnqtfFWDKn7hrgIE4IOG-GtoANmGGxn2-3otyVvZUqS3vP_-7_Jk0o7kWGsuUXTuXi-PWkPz9yKt4M_9JIrp9zBMsC1VWX_Vy-WV1fZ4PvIQ6cbr9NYqoOeV3_xswXOQsHwVsc_MuqX73t5kXf..; isg=BLKy-DP_AZuvnT2nGgCYFwp_A_iUQ7bdjlsSZXyvwWVQD1UJZNBH7D8p_6uzfy51',
        'Priority': 'u=0, i',
        'Sec-CH-UA': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
    }

    response = requests.get(url, headers=headers)

    supplier_name = None
    
    if response.status_code == 200:
        if response.headers.get('Content-Encoding') == 'zstd':
            dctx = zstd.ZstdDecompressor()
            compressed_stream = BytesIO(response.content)
            
            decompressed_data = dctx.stream_reader(compressed_stream).read()

            detected_encoding = chardet.detect(decompressed_data)
            html_content = decompressed_data.decode(detected_encoding['encoding'])
            text = html_content
        else:
            text = response.text

        # 获取供应商名字
        pattern = r'companyName":\s*"([^"]+)"'
        matches = re.findall(pattern, text)
        if matches:
            supplier_name = matches[0]
        
        # 获取变体信息
        results = []
        # 找到 "skuModel" 字段的起始位置
        start_key = '"skuModel":'
        start_index = text.find(start_key)

        if start_index == -1:
            print("未找到 skuModel 字段")
        else:
            # 从 "skuModel" 后面找到第一个 '{' 的位置
            brace_start = text.find('{', start_index)
            if brace_start == -1:
                print("未找到 skuModel 对象的起始花括号")
            else:
                # 使用计数器来跟踪大括号匹配
                brace_count = 0
                end_index = brace_start
                for i in range(brace_start, len(text)):
                    char = text[i]
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                    
                    # 当大括号全部闭合时结束
                    if brace_count == 0 and i > brace_start:
                        end_index = i + 1
                        break
                
                sku_model_str = text[brace_start:end_index]

                # print(sku_model_str)
                # print("---")

                # 替换 HTML 转义字符
                sku_model_str = sku_model_str.replace('&gt;', '-')

                try:
                    sku_model_json = json.loads(sku_model_str)
                    # sku_props = sku_model_json["skuProps"]
                    sku_info_map = sku_model_json["skuInfoMap"] 

                    # Step 1: 提取颜色和对应的图片 URL
                    color_image_map = {}
                    for color_info in sku_model_json['skuProps'][0]['value']:
                        color_image_map[color_info['name']] = color_info['imageUrl']                   
                    
                    # for sku_prop in sku_props:
                    #     print(f"----可选属性 {sku_prop['prop']}----")
                    #     for index,item in enumerate(sku_prop["value"]):
                    #         print(f"{index+1}.{item['name']}")
                        
                    for key,value in sku_info_map.items():

                        color = key.split('-')[0].replace("&gt;", ">")
                        # 根据颜色找到对应的图片
                        image_url = color_image_map.get(color)

                        results.append({
                            "attr": key,
                            "productId": product_id,
                            "specId": value['specId'],
                            "skuId": value['skuId'],
                            "imageUrl": image_url if image_url else None
                        })

                except json.JSONDecodeError as e:
                    print("JSON解析失败:", e)
    
    return supplier_name,results

# 获取数据签名
def getSignature(api_info, data):
    """
    生成签名。

    :param api_info: API 信息字符串，格式为 protocol/apiVersion/namespace/apiName/appKey
    :param data: 请求参数字典，包括 queryString 和 request body 中的所有参数
    :return: 签名字符串
    """
    # 将所有参数值转成字符串，并确保复杂结构参数（dict、list）先转为 JSON 字符串
    ali_data = {}
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            # 使用无空格的分隔符，保证序列化一致性
            value = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        else:
            # 确保是字符串
            value = str(value)
        ali_data[key] = value

    # 对参数根据 key 进行排序（字典序）
    sorted_items = sorted(ali_data.items())
    ali_params = [f"{k}{v}" for k, v in sorted_items]
    sign_str = api_info + ''.join(ali_params)

    # 调试：打印签名字符串
    # print("签名字符串:", sign_str)

    # 生成 HMAC-SHA1 签名
    signature = hmac.new(
        APP_SECRET.encode('utf-8'),
        sign_str.encode('utf-8'),
        hashlib.sha1
    ).hexdigest().upper()

    # 调试：打印生成的签名
    # print("生成的签名:", signature)

    return sign_str,signature

APP_KEY = '3926173'
APP_SECRET = 'sHgOIHe9SqM'
ACCESS_TOKEN = 'af961af3-2fd7-4e05-b19b-f367ff88f217'

# 获取订单数据
# 一次最多返回50条
def get1688OrderList(start_time,end_time,page,pageSize):

    url = 'https://gw.open.1688.com/openapi'
    api_info = f'param2/1/com.alibaba.trade/alibaba.trade.getBuyerOrderList/{APP_KEY}'

    data = {
        "createEndTime": end_time,
        "createStartTime": start_time,
        "isHis": "false",
        "page": page,
        "pageSize": pageSize,
        "needBuyerAddressAndPhone": "true",
        "needMemoInfo": "true",
        "access_token": ACCESS_TOKEN
    }
    sign_str,signature = getSignature(api_info,data)

    data["_aop_signature"] = signature

    response = requests.post(url+"/"+api_info, data=data)

    if response.status_code == 200:
        formatted_response = json.dumps(response.json(), indent=4, ensure_ascii=False)
        # print(formatted_response)
        
        with open("data.json", 'w', encoding='utf-8') as f:
            json.dump(response.json(), f, ensure_ascii=False, indent=4)
        
        return {"data":response.json(), "msg":response.text, "code":200}
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)
        return {"data":None, "msg":response.text, "code":400}

# 获取 订单详情数据
def get1688OrderDetail(order_id):

    url = 'https://gw.open.1688.com/openapi'
    api_info = f'param2/1/com.alibaba.trade/alibaba.trade.get.buyerView/{APP_KEY}'

    data = {
        "webSite": "1688",
        "orderId": order_id,
        "includeFields": "NativeLogistics",
        "access_token": ACCESS_TOKEN
    }

    sign_str,signature = getSignature(api_info,data)

    data["_aop_signature"] = signature

    response = requests.post(url+"/"+api_info, data=data)

    if response.status_code == 200:
        data = response.json()
        formatted_response = json.dumps(data, indent=4, ensure_ascii=False)
        # print(formatted_response)
        
        results = []
        if "logisticsItems" in data["result"]["nativeLogistics"]:
            for item in data["result"]["nativeLogistics"]["logisticsItems"]:
                results.append(item["logisticsBillNo"])
        
        refundStatus = ""

        if "refundStatus" in data["result"]["baseInfo"]:
            refundStatus = data["result"]["baseInfo"]["refundStatus"]
            dic = {
                "waitselleragree":"等待卖家同意",
                "waitbuyermodify":"待买家修改",
                "waitbuyersend":"等待买家退货",
                "waitsellerreceive":"等待卖家确认收货",
                "refundsuccess":"退款成功",
                "refundclose":"退款失败"
            }
            refundStatus = dic[refundStatus]
        
        return {"data":results, "refundStatus":refundStatus, "msg":response.text, "code":200}
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)
        return {"data":None, "msg":response.text, "code":400}
    
# 订单前预览数据（获取flow）
def create1688OrderPreview(cargoParamList):

    url = 'https://gw.open.1688.com/openapi'
    api_info = f'param2/1/com.alibaba.trade/alibaba.createOrder.preview/{APP_KEY}'

    data = {
        "addressParam":{
            "fullName": "唐女士",
            "mobile": "86-0574-15857446133",
            "phone": "13777948242",
            "cityText": "宁波市",
            "provinceText": "浙江省",
            "areaText": "江北区",
            "townText": "洪塘街道",
            "address": "同济路121号亿天中心1620室"
        },
        # "cargoParamList": [
        #     {
        #         "offerId": "693785593567",
        #         "specId": "4c111b2355f3f5d2c63a4a30216ca53e",
        #         "quantity": "2"
        #     },
        #     {
        #         "offerId": "693785593567",
        #         "specId": "607082d05e24a3325a4beab87fbec890",
        #         "quantity": "1"
        #     },
        #     {
        #         "offerId": "735154872608",
        #         "specId": "482dac7d0a541570f0961e16a22e7cb7",
        #         "quantity": "2"
        #     }
        # ],
        "cargoParamList": cargoParamList,
        "access_token": ACCESS_TOKEN
    }

    sign_str,signature = getSignature(api_info,data)

    # 1. 拆分基础路径与其余部分
    path, rest = sign_str.split("access_token", 1)

    # 2. 提取access_token
    token, rest = rest.split("addressParam", 1)

    # 3. 提取addressParam的JSON字符串与cargoParamList的JSON字符串
    address_param_str, cargo_str = rest.split("cargoParamList", 1)

    # 4. URL编码需要传递的JSON参数
    address_param_encoded = urllib.parse.quote(address_param_str, safe='')
    cargo_param_list_encoded = urllib.parse.quote(cargo_str, safe='')

    # 5. 拼接最终URL
    final_url = (
        f"{url}/{api_info}"
        f"?addressParam={address_param_encoded}"
        f"&cargoParamList={cargo_param_list_encoded}"
        f"&access_token={token}"
        f"&_aop_signature={signature}"
    )

    response = requests.get(final_url)

    if response.status_code == 200:
        # formatted_response = json.dumps(response.json(), indent=4, ensure_ascii=False)
        # print(formatted_response)
        data = response.json()
        if "errorMsg" in data:
            return {"data":None, "msg": data["errorMsg"], "code":400}

        else: 
            return {"data":data, "msg":response.text, "code":200}
    else:
        return {"data":None, "msg":response.text, "code":400}

# 下单
def create1688Order(flow,cargoParamList):

    url = 'https://gw.open.1688.com/openapi'
    api_info = f'param2/1/com.alibaba.trade/alibaba.trade.fastCreateOrder/{APP_KEY}'

    data = {
        "flow": flow,
        "addressParam": {
            "fullName": "唐女士",
            "mobile": "86-0574-15857446133",
            "phone": "13777948242",
            "cityText": "宁波市",
            "provinceText": "浙江省",
            "areaText": "江北区",
            "townText": "洪塘街道",
            "address": "同济路121号亿天中心1620室"
        },
        # "cargoParamList": [
        #     {
        #         "offerId": "693785593567",
        #         "specId": "4c111b2355f3f5d2c63a4a30216ca53e",
        #         "quantity": "1"
        #     },
        #     {
        #         "offerId": "693785593567",
        #         "specId": "607082d05e24a3325a4beab87fbec890",
        #         "quantity": "1"
        #     },
        #     {
        #         "offerId": "735154872608",
        #         "specId": "482dac7d0a541570f0961e16a22e7cb7",
        #         "quantity": "2"
        #     }
        # ],
        "cargoParamList": cargoParamList,
        "access_token": ACCESS_TOKEN
    }

    sign_str,signature = getSignature(api_info,data)

    path, rest = sign_str.split("access_token", 1)

    token, rest = rest.split("addressParam", 1)

    address_param_str, rest = rest.split("cargoParamList", 1)
    
    cargo_str, rest = rest.split("flow", 1)

    address_param_encoded = urllib.parse.quote(address_param_str, safe='')
    cargo_param_list_encoded = urllib.parse.quote(cargo_str, safe='')

    final_url = (
        f"{url}/{api_info}"
        f"?addressParam={address_param_encoded}"
        f"&cargoParamList={cargo_param_list_encoded}"
        f"&flow={flow}"
        f"&access_token={token}"
        f"&_aop_signature={signature}"
    )
    response = requests.get(final_url)

    if response.status_code == 200:
        formatted_response = json.dumps(response.json(), indent=4, ensure_ascii=False)
        print(formatted_response)
        return {"data":response.json(), "msg":response.text, "code":200}
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)
        return {"data":None, "msg":response.text, "code":400}

if __name__ == "__main__":
    # url = "https://detail.1688.com/offer/693785593567.html?spm=a26352.13672862.offerlist.58.13cc1e62DVX98d"
    # supplier_name,results = get1688ProductMsg(url)
    # print(supplier_name)
    # print(results)
    
    # 获取订单数据
    # get1688OrderList("20241220000000000+0800","20241220235959000+0800",1,50)
    # 获取订单详情数据
    # print(get1688OrderDetail(order_id=2413606586102558276)) 
    # print(get1688OrderDetail(order_id=2407038637508558276))
    # 下单
    flow = create1688OrderPreview("")["data"]["orderPreviewResuslt"][0]["flowFlag"]
    # print(create1688Order(flow)["data"])