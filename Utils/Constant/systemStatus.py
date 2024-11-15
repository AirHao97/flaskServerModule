# 系统内状态类型
class SystemStatus:
    createdPendingReview = "已创建待审核"
    waitForOzon = "等待国际运单号同步"
    reviewedPendingStock = "已审核待备货"
    stockPreparedPendingOutward = "已备货待出库"
    outwardShippedPendingDispatch = "已出库待发货"
    dispatchedPendingSignatureConfirmation = "已发货待签收"
    arbitration = "仲裁中"
    signedforReceived = "已完成"
    other = "未知状态"
    cancelled = "已取消"
    freeze = "已冻结"