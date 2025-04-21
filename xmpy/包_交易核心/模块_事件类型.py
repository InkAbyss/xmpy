"""
在交易平台中使用的事件类型字符串。
"""

from xmpy.包_事件引擎 import 事件类型_定时

# 核心事件类型
事件类型_行情 = "eTick"
事件类型_成交 = "eTrade"
事件类型_订单 = "eOrder"
事件类型_持仓 = "ePosition"
事件类型_账户 = "eAccount"
事件类型_报价 = "eQuote"
事件类型_合约 = "eContract"
事件类型_日志 = "eLog"