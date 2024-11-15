# ozon中货件状态
class ozonStatus:

    '''
    createdPendingReview = "已创建待审核"
    waitForOzon = "等待国际运单号同步"
    reviewedPendingStock = "已审核待备货"
    stockPreparedPendingOutward = "已备货待出库"
    outwardShippedPendingDispatch = "已出库待发货"
    dispatchedPendingSignatureConfirmation = "已发货待签收"
    arbitration = "仲裁中"
    signedforReceived = "已完成"
    Cancelled = "已作废"
    '''

    # ---对应 已创建待审核---
    # 还未申请运单号
    awaiting_packaging = "等待包装"

    # ---对应 等待国际运单号同步---
    # 已经申请了运单号 等待运单号出来 
    awaiting_registration = "等待注册"

    # ---对应 已审核待备货---
    awaiting_deliver = "等待装运"

    # ---对应 已发货待签收---
    acceptance_in_progress = "正在验收"
    driver_pickup = "司机处"
    delivering = "运输中"

    # ---对应 已作废---
    cancelled = "已取消"
    # ---对应 已完成---
    delivered = "已完成"

    # --- 对应 仲裁中 --- 
    arbitration = "仲裁"
    client_arbitration = "快递客户仲裁"
    
    # --- 对应 未知状态 ---
    sent_by_seller = "由卖家发货"
    awaiting_approve = "等待确认"
    not_accepted = "分拣中心未接受"
    awaiting_verification  = "已创建"
    
