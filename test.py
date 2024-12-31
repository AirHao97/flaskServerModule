import requests

response = requests.get("https://ifconfig.me/" ,timeout=10)

print(response.text)