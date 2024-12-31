# 采购单状态
class PurchaseStatus:
    waitForPurchase = "待采购"
    waitForPay = "待付款"
    inTransit = "运输中"
    error = "有异常"
    finished = "已完成"
    cancelled = "已作废"

# 1688发货状态
class PurchaseStatus1688:
    waitbuyerpay = "等待买家付款",
    waitsellersend = "等待卖家发货",
    waitlogisticstakein = "等待物流公司揽件",
    waitbuyerreceive = "等待买家收货",
    waitbuyersign = "等待买家签收",
    signinsuccess = "买家已签收",
    confirm_goods = "已收货",
    success = "交易成功",
    cancel = "交易取消",
    terminated = "交易终止",