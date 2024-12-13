from datetime import datetime, timedelta

# 获取当前日期和时间
now = datetime.now()

# 生成今天的日期和时间，然后设置为11时59分59秒
today = now.replace(hour=11, minute=59, second=59, microsecond=0)

# 生成半个月前的日期和时间，设置为00时00分00秒
half_month_ago = now - timedelta(days=15)
half_month_ago = half_month_ago.replace(hour=0, minute=0, second=0, microsecond=0)

# 格式化日期和时间为指定格式
# 格式说明：YYYYMMDDHHMMSSmmm+ZZZZ
# 其中mmm为毫秒，ZZZZ为时区偏移量（东八区为+0800）
today_str = today.strftime('%Y%m%d%H%M%S%f')[:-3] + '+0800'
half_month_ago_str = half_month_ago.strftime('%Y%m%d%H%M%S%f')[:-3] + '+0800'

# 输出结果
print("今天的日期和时间（11时59分59秒）:", today_str)
print("半个月前的日期和时间（00时00分00秒）:", half_month_ago_str)