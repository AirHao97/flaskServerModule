import requests
import zstandard as zstd
from io import BytesIO 
import re

def get_supplier_name(url):
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en;q=0.7,or;q=0.6,om;q=0.5,eu;q=0.4,ms;q=0.3,sa;q=0.2',
        'Cookie': 'cna=HpSSHtk2vWMCAXr3nkN8eVqL; taklid=59b7fddbef9f4529b96c061ab4b404e2; lid=z6477557; ali_apache_track=c_mid=b2b-1935512352|c_lid=z6477557|c_ms=1; isg=BBISyPFsoF7ma9zaqsWp9QhQY9j0Ixa9f-K-rdxrVkWw77PpxLKKzFJMW0tTmo5V; tfstk=f1bidh0jOG-1vDoHtk8_mLNor_qp5fTXFt3vHEp4YpJBBKF1MMYeZCk20RTOo9X5dNpwWE3cmNBdkG3AgjAVpF-fXKp9nEffEWe8yzC11Etze8UJ7P27lUgq_nkvLpRfNgZMAzC11Xli37IUymAaxXS23t-wYeRyLVlN3doUtIRxQmuN3WfedIHq_K8VTXRv_I82ut5UtIGoefJPui7UCBU-L-68RaRMjK0vKq2gMC-MU1J3n-bn3hvP_p00FkxgdKvCzJEhOTINBB60rJYPV9bD4E4iFCjFZeJ9zPc6UNdcwifuExdCbObemwFbf6bDI37wxrVJ8FAV3njQE4dMWMxlSGNjL1WJIg81Mb2Ot3jHVB-Eic8O2_QX4NziFpKWi9xRj80GUgJtY0k56qOUMwojchRBtLUORUwIMAboyWVnVitwOQv8tWmjchRBtLF3t0wXbBOke',
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
            html_content = decompressed_data.decode('utf-8')
            text = html_content
        else:
            text = response.text
        
        pattern = r'companyName":\s*"([^"]+)"'
        matches = re.findall(pattern, text)
        if matches:
            supplier_name = matches[0]
    
    return supplier_name
    
    


if __name__ == "__main__":
    url = "https://detail.1688.com/offer/824296098423.html?offerId=824296098423&extStr=0.0351642370223999..0.0025149285793304443..0.0020..0.0209..fI2ISwg..126562002..0..0..1..9..78475a50-6b35-495d-a494-8e6956acca14..offer..824296098423..2..671119611549..97..125380001..1038378..organic..0..fI2ISwg..0....long..0..1.0935263498570792E-7..6....1.0E-10..26966706575-1033511___2..58..9439c427bab0e2fc84956600cd82fd60..1000003..na61..1007.50972.375248.0.._....78..commonScene_78..gul_213e387617295599861065748e21b6_824296098423_1211192226&object_id=824296098423&object_type=offer&object_sub_type=normal&serverTrackId=gul_213e387617295599861065748e21b6_824296098423_1211192226&hotSaleSkuId=5708855346156&tpp_expodata=824296098423..213e387617295599861065748e21b6..78475a50-6b35-495d-a494-8e6956acca14..1729559986..78....1007.38042.291243.0..businessType:normal&traceId=213e387617295599861065748e21b6&spm=a260k.home2024.recommendpart.9&scm=1007.50972.375248.0"
    print(get_supplier_name(url))