"""交易平台基础数据结构"""

from dataclasses import dataclass, field
from datetime import datetime
from logging import INFO
from typing import Optional

# from .constant import Direction 方向, Exchange 交易所, Interval 周期, Offset 开平, Status 状态, Product 产品类型, OptionType 期权类型, OrderType 委托类型
from xmpy.包_交易核心.模块_常数 import 类_方向,类_交易所,类_周期,类_开平,类_状态,类_产品类型,类_期权类型,类_委托类型
活跃状态集合 = set([类_状态.提交中, 类_状态.未成交, 类_状态.部分成交])

@dataclass
class 基础数据:
    """所有数据类的基类，包含来源网关名称"""

    网关名称: str
    扩展信息: Optional[dict] = field(default=None, init=False)


@dataclass
class 类_行情数据(基础数据):
    """行情数据，包含最新成交、盘口快照及统计信息"""

    代码: str
    交易所: 类_交易所
    时间戳: datetime

    名称: str = ""
    成交量: float = 0
    成交额: float = 0
    持仓量: float = 0
    最新价: float = 0
    最新量: float = 0
    涨停价: float = 0
    跌停价: float = 0

    开盘价: float = 0
    最高价: float = 0
    最低价: float = 0
    昨收价: float = 0

    买一价: float = 0
    买二价: float = 0
    买三价: float = 0
    买四价: float = 0
    买五价: float = 0

    卖一价: float = 0
    卖二价: float = 0
    卖三价: float = 0
    卖四价: float = 0
    卖五价: float = 0

    买一量: float = 0
    买二量: float = 0
    买三量: float = 0
    买四量: float = 0
    买五量: float = 0

    卖一量: float = 0
    卖二量: float = 0
    卖三量: float = 0
    卖四量: float = 0
    卖五量: float = 0

    本地时间: datetime = None

    def __post_init__(self) -> None:
        """生成唯一标识"""
        self.代码_交易所: str = f"{self.代码}.{self.交易所.name}"

@dataclass
class 类_K线数据(基础数据):
    """K线柱状数据"""

    代码: str
    交易所: 类_交易所
    时间戳: datetime

    周期: 类_周期 = None
    成交量: float = 0
    成交额: float = 0
    持仓量: float = 0
    开盘价: float = 0
    最高价: float = 0
    最低价: float = 0
    收盘价: float = 0

    def __post_init__(self) -> None:
        """生成唯一标识"""
        self.代码_交易所: str = f"{self.代码}.{self.交易所.value}"

@dataclass
class 类_订单数据(基础数据):
    """委托状态跟踪数据"""

    代码: str
    交易所: 类_交易所
    订单编号: str

    类型: 类_委托类型 = 类_委托类型.限价单
    方向: 类_方向 = None
    开平: 类_开平 = 类_开平.NONE
    价格: float = 0
    数量: float = 0
    已成交: float = 0
    状态: 类_状态 = 类_状态.提交中
    时间戳: datetime = None
    参考号: str = ""

    def __post_init__(self) -> None:
        """生成唯一标识"""
        self.代码_交易所: str = f"{self.代码}.{self.交易所.value}"
        self.网关_订单编号: str = f"{self.网关名称}.{self.订单编号}"

    def 是否活跃(self) -> bool:
        """检查订单是否处于活跃状态"""
        return self.状态 in 活跃状态集合

    def 创建撤单请求(self) -> "类_撤单请求":
        """生成撤单请求对象"""
        return 类_撤单请求(
            订单编号=self.订单编号,
            代码=self.代码,
            交易所=self.交易所
        )


@dataclass
class 类_成交数据(基础数据):
    """订单成交明细数据"""

    代码: str
    交易所: 类_交易所
    订单编号: str
    成交编号: str
    方向: 类_方向 = None

    开平: 类_开平 = 类_开平.NONE
    价格: float = 0
    数量: float = 0
    时间戳: datetime = None

    def __post_init__(self) -> None:
        """生成唯一标识"""
        self.代码_交易所: str = f"{self.代码}.{self.交易所.value}"
        self.网关_订单编号: str = f"{self.网关名称}.{self.订单编号}"
        self.网关_成交编号: str = f"{self.网关名称}.{self.成交编号}"


@dataclass
class 类_持仓数据(基础数据):
    """持仓信息数据"""

    代码: str
    交易所: 类_交易所
    方向: 类_方向

    数量: float = 0
    冻结量: float = 0
    价格: float = 0
    盈亏: float = 0
    昨仓量: float = 0

    def __post_init__(self) -> None:
        """生成唯一标识"""
        self.代码_交易所: str = f"{self.代码}.{self.交易所.value}"
        self.持仓_方向: str = f"{self.网关名称}.{self.代码_交易所}.{self.方向.value}"



@dataclass
class 类_账户数据(基础数据):
    """账户资金数据"""

    账户编号: str
    余额: float = 0
    冻结金额: float = 0

    def __post_init__(self) -> None:
        """计算可用资金"""
        self.可用金额: float = self.余额 - self.冻结金额
        self.账户唯一标识: str = f"{self.网关名称}.{self.账户编号}"


@dataclass
class 类_日志数据(基础数据):
    """系统日志数据"""

    消息内容: str
    日志级别: int = INFO

    def __post_init__(self) -> None:
        """自动设置记录时间"""
        self.记录时间: datetime = datetime.now()


@dataclass
class 类_合约数据(基础数据):
    """合约基本信息数据"""

    代码: str
    交易所: 类_交易所
    名称: str
    产品类型: 类_产品类型
    合约乘数: float
    最小价位: float

    最小数量: float = 1  # 最小交易手数
    最大数量: float = None  # 最大交易手数
    支持止损单: bool = False  # 是否支持止损单
    净持仓模式: bool = False  # 是否使用净持仓
    支持历史数据: bool = False  # 是否提供历史数据

    期权行权价: float = 0
    标的合约: str = ""  # 标的合约唯一标识
    期权类型: 类_期权类型 = None
    上市日期: datetime = None
    到期日期: datetime = None
    期权组合: str = ""
    期权索引: str = ""  # 相同行权价的期权标识

    def __post_init__(self) -> None:
        """生成唯一标识"""
        self.代码_交易所: str = f"{self.代码}.{self.交易所.value}"


@dataclass
class 类_报价数据(基础数据):
    """做市商报价数据"""

    代码: str
    交易所: 类_交易所
    报价编号: str

    买方价: float = 0.0
    买方量: int = 0
    卖方价: float = 0.0
    卖方量: int = 0
    买开平: 类_开平 = 类_开平.NONE
    卖开平: 类_开平 = 类_开平.NONE
    状态: 类_状态 = 类_状态.提交中
    时间戳: datetime = None
    参考号: str = ""

    def __post_init__(self) -> None:
        """生成唯一标识"""
        self.代码_交易所: str = f"{self.代码}.{self.交易所.value}"
        self.网关_报价编号: str = f"{self.网关名称}.{self.报价编号}"

    def 是否活跃(self) -> bool:
        """检查报价是否处于活跃状态"""
        return self.状态 in 活跃状态集合

    def 创建撤单请求(self) -> "类_撤单请求":
        """生成撤单请求对象"""
        return 类_撤单请求(
            订单编号=self.报价编号,
            代码=self.代码,
            交易所=self.交易所
        )


@dataclass
class 类_订阅请求:
    """行情订阅请求"""

    代码: str
    交易所: 类_交易所

    def __post_init__(self) -> None:
        """生成唯一标识"""
        self.代码_交易所: str = f"{self.代码}.{self.交易所.value}"


@dataclass
class 类_订单请求:
    """新订单请求"""

    代码: str
    交易所: 类_交易所
    方向: 类_方向
    类型: 类_委托类型
    数量: float
    价格: float = 0
    开平: 类_开平 = 类_开平.NONE
    参考号: str = ""

    def __post_init__(self) -> None:
        """生成唯一标识"""
        self.代码_交易所: str = f"{self.代码}.{self.交易所.value}"

    def 生成订单数据(self, 委托编号: str, 网关名称: str) -> 类_订单数据:
        """创建委托数据对象"""
        return 类_订单数据(
            代码=self.代码,
            交易所=self.交易所,
            订单编号=委托编号,
            类型=self.类型,
            方向=self.方向,
            开平=self.开平,
            价格=self.价格,
            数量=self.数量,
            参考号=self.参考号,
            网关名称=网关名称,
        )


@dataclass
class 类_撤单请求:
    """订单撤单请求"""

    订单编号: str
    代码: str
    交易所: 类_交易所

    def __post_init__(self) -> None:
        """生成唯一标识"""
        self.代码_交易所: str = f"{self.代码}.{self.交易所.value}"


@dataclass
class 类_历史数据请求:
    """历史数据查询请求"""

    代码: str
    交易所: 类_交易所
    开始时间: datetime
    结束时间: datetime = None
    周期: 类_周期 = None

    def __post_init__(self) -> None:
        """生成唯一标识"""
        self.代码_交易所: str = f"{self.代码}.{self.交易所.value}"


@dataclass
class 类_报价请求:
    """新报价请求"""

    代码: str
    交易所: 类_交易所
    买方价: float
    买方量: int
    卖方价: float
    卖方量: int
    买开平: 类_开平 = 类_开平.NONE
    卖开平: 类_开平 = 类_开平.NONE
    参考号: str = ""

    def __post_init__(self) -> None:
        """生成唯一标识"""
        self.代码_交易所: str = f"{self.代码}.{self.交易所.value}"

    def 生成报价数据(self, 报价编号: str, 网关名称: str) -> 类_报价数据:
        """创建报价数据对象"""
        return 类_报价数据(
            代码=self.代码,
            交易所=self.交易所,
            报价编号=报价编号,
            买方价=self.买方价,
            买方量=self.买方量,
            卖方价=self.卖方价,
            卖方量=self.卖方量,
            买开平=self.买开平,
            卖开平=self.卖开平,
            参考号=self.参考号,
            网关名称=网关名称,
        )


# 新添加

# @dataclass
# class 类_条件单:
#     """ 条件单 """
#     策略名称: str
#     代码_交易所: str
#     方向: Direction
#     开平: Offset
#     价格: float
#     数量: float
#     条件: 类_条件类型
#     执行价格类型: 类_执行价格类型 = 类_执行价格类型.设定价
#     分组: str = ""
#     创建时间: datetime = datetime.now()
#     触发时间: datetime = None
#     条件单编号: str = ""  # 条件单编号
#     状态: 类_条件单状态 = 类_条件单状态.等待中
#
#     def __post_init__(self):
#         """  """
#         if not self.条件单编号:
#             self.条件单编号 = datetime.now().strftime("%m%d%H%M%S%f")[:13]



