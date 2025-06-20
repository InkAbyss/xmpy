from typing import Dict, List, TYPE_CHECKING
from copy import copy

from .模块_对象 import 类_合约数据, 类_订单数据, 类_成交数据, 类_持仓数据, 类_订单请求
from .模块_常数 import 类_方向, 类_开平, 类_交易所

if TYPE_CHECKING:
    from .模块_主引擎 import 类_主引擎


class 类_持仓转换器:
    """持仓转换管理器"""

    def __init__(self, 主引擎: "类_主引擎") -> None:
        self.持仓字典: Dict[str, "类_持仓明细"] = {}
        self.获取合约信息 = 主引擎.获取合约详情

    def 更新持仓(self, 持仓实例: 类_持仓数据) -> None:
        """更新持仓数据"""
        if not self.需要转换(持仓实例.代码_交易所):
            return
        持仓明细 = self.获取持仓明细(持仓实例.代码_交易所)
        持仓明细.更新持仓(持仓实例)

    def 更新成交(self, 成交实例: 类_成交数据) -> None:
        """更新成交记录"""
        if not self.需要转换(成交实例.代码_交易所):
            return
        持仓明细 = self.获取持仓明细(成交实例.代码_交易所)
        持仓明细.更新成交(成交实例)

    def 更新委托(self, 订单实例: 类_订单数据) -> None:
        """更新订单状态"""
        if not self.需要转换(订单实例.代码_交易所):
            return
        持仓明细 = self.获取持仓明细(订单实例.代码_交易所)
        持仓明细.更新委托(订单实例)

    def 更新委托请求(self, 请求: 类_订单请求, 订单标识: str) -> None:
        """处理委托请求更新"""
        if not self.需要转换(请求.代码_交易所):
            return
        持仓明细 = self.获取持仓明细(请求.代码_交易所)
        持仓明细.更新委托请求(请求, 订单标识)

    def 获取持仓明细(self, 合约标识: str) -> "类_持仓明细":
        """获取或创建持仓明细"""
        持仓明细 = self.持仓字典.get(合约标识)
        if not 持仓明细:
            合约信息 = self.获取合约信息(合约标识)
            持仓明细 = 类_持仓明细(合约信息)
            self.持仓字典[合约标识] = 持仓明细
        return 持仓明细

    def 转换委托请求(
            self,
            请求: 类_订单请求,
            锁定模式: bool,
            净仓模式: bool = False
    ) -> List[类_订单请求]:
        """转换委托请求类型"""
        if not self.需要转换(请求.代码_交易所):
            return [请求]

        持仓明细 = self.获取持仓明细(请求.代码_交易所)

        if 锁定模式:
            return 持仓明细.转换委托请求_锁定(请求)
        elif 净仓模式:
            return 持仓明细.转换委托请求_净仓(请求)
        elif 请求.交易所 in {类_交易所.上期所, 类_交易所.能源中心}:
            return 持仓明细.转换委托请求_上期所(请求)
        else:
            return [请求]

    def 需要转换(self, 合约标识: str) -> bool:
        """检查是否需要持仓转换"""
        合约信息 = self.获取合约信息(合约标识)
        return bool(合约信息 and not 合约信息.净持仓模式)


class 类_持仓明细:
    """单个合约的持仓明细管理"""

    def __init__(self, 合约信息: 类_合约数据) -> None:
        self.合约标识 = 合约信息.代码_交易所
        self.交易所 = 合约信息.交易所

        self.活跃委托字典: Dict[str, 类_订单数据] = {}

        # 多头持仓
        self.多头持仓: float = 0
        self.多头昨仓: float = 0
        self.多头今仓: float = 0

        # 空头持仓
        self.空头持仓: float = 0
        self.空头昨仓: float = 0
        self.空头今仓: float = 0

        # 冻结持仓
        self.多头冻结: float = 0
        self.多头昨冻: float = 0
        self.多头今冻: float = 0

        self.空头冻结: float = 0
        self.空头昨冻: float = 0
        self.空头今冻: float = 0

    def 更新持仓(self, 持仓实例: 类_持仓数据) -> None:
        """更新持仓基础数据"""
        if 持仓实例.方向 == 类_方向.做多:
            self.多头持仓 = 持仓实例.数量
            self.多头昨仓 = 持仓实例.昨仓量
            self.多头今仓 = self.多头持仓 - self.多头昨仓
        else:
            self.空头持仓 = 持仓实例.数量
            self.空头昨仓 = 持仓实例.昨仓量
            self.空头今仓 = self.空头持仓 - self.空头昨仓

    def 更新委托(self, 订单实例: 类_订单数据) -> None:
        """处理委托单更新"""
        if 订单实例.是否活跃():
            self.活跃委托字典[订单实例.网关_订单编号] = 订单实例
        else:
            self.活跃委托字典.pop(订单实例.网关_订单编号, None)
        self.计算冻结量()

    def 更新委托请求(self, 请求: 类_订单请求, 订单标识: str) -> None:
        """处理委托请求转换"""
        网关名称, 订单编号 = 订单标识.split(".")
        新订单 = 请求.生成订单数据(订单编号, 网关名称)
        self.更新委托(新订单)

    def 更新成交(self, 成交实例: 类_成交数据) -> None:
        """处理成交数据更新"""
        if 成交实例.方向 == 类_方向.做多:
            self.处理多头成交(成交实例)
        else:
            self.处理空头成交(成交实例)

        # 更新总持仓
        self.多头持仓 = self.多头今仓 + self.多头昨仓
        self.空头持仓 = self.空头今仓 + self.空头昨仓
        self.统计冻结总量()

    def 处理多头成交(self, 成交实例: 类_成交数据) -> None:
        """处理多头方向成交"""
        if 成交实例.开平 == 类_开平.开仓:
            self.多头今仓 += 成交实例.数量
        elif 成交实例.开平 == 类_开平.平今:
            self.空头今仓 -= 成交实例.数量
        elif 成交实例.开平 == 类_开平.平昨:
            self.空头昨仓 -= 成交实例.数量
        elif 成交实例.开平 == 类_开平.平仓:
            if 成交实例.交易所 in {类_交易所.上期所, 类_交易所.能源中心}:
                self.空头昨仓 -= 成交实例.数量
            else:
                self.空头今仓 -= 成交实例.数量
                if self.空头今仓 < 0:
                    self.空头昨仓 += self.空头今仓
                    self.空头今仓 = 0

    def 处理空头成交(self, 成交实例: 类_成交数据) -> None:
        """处理空头方向成交"""
        if 成交实例.开平 == 类_开平.开仓:
            self.空头今仓 += 成交实例.数量
        elif 成交实例.开平 == 类_开平.平今:
            self.多头今仓 -= 成交实例.数量
        elif 成交实例.开平 == 类_开平.平昨:
            self.多头昨仓 -= 成交实例.数量
        elif 成交实例.开平 == 类_开平.平仓:
            if 成交实例.交易所 in {类_交易所.上期所, 类_交易所.能源中心}:
                self.多头昨仓 -= 成交实例.数量
            else:
                self.多头今仓 -= 成交实例.数量
                if self.多头今仓 < 0:
                    self.多头昨仓 += self.多头今仓
                    self.多头今仓 = 0

    def 计算冻结量(self) -> None:
        """计算各仓位冻结数量"""
        self.重置冻结量()

        for 订单 in self.活跃委托字典.values():
            if 订单.开平 == 类_开平.开仓:
                continue

            冻结量 = 订单.数量 - 订单.已成交

            if 订单.方向 == 类_方向.做多:
                self.处理多头冻结(订单, 冻结量)
            else:
                self.处理空头冻结(订单, 冻结量)

        self.统计冻结总量()

    def 处理多头冻结(self, 订单: 类_订单数据, 冻结量: float) -> None:
        """处理多头方向冻结"""
        if 订单.开平 == 类_开平.平今:
            self.空头今冻 += 冻结量
        elif 订单.开平 == 类_开平.平昨:
            self.空头昨冻 += 冻结量
        elif 订单.开平 == 类_开平.平仓:
            self.空头今冻 += 冻结量
            if self.空头今冻 > self.空头今仓:
                self.空头昨冻 += (self.空头今冻 - self.空头今仓)
                self.空头今冻 = self.空头今仓

    def 处理空头冻结(self, 订单: 类_订单数据, 冻结量: float) -> None:
        """处理空头方向冻结"""
        if 订单.开平 == 类_开平.平今:
            self.多头今冻 += 冻结量
        elif 订单.开平 == 类_开平.平昨:
            self.多头昨冻 += 冻结量
        elif 订单.开平 == 类_开平.平仓:
            self.多头今冻 += 冻结量
            if self.多头今冻 > self.多头今仓:
                self.多头昨冻 += (self.多头今冻 - self.多头今仓)
                self.多头今冻 = self.多头今仓

    def 统计冻结总量(self) -> None:
        """统计并校验冻结总量"""
        self.多头今冻 = min(self.多头今冻, self.多头今仓)
        self.多头昨冻 = min(self.多头昨冻, self.多头昨仓)
        self.空头今冻 = min(self.空头今冻, self.空头今仓)
        self.空头昨冻 = min(self.空头昨冻, self.空头昨仓)

        self.多头冻结 = self.多头今冻 + self.多头昨冻
        self.空头冻结 = self.空头今冻 + self.空头昨冻

    def 重置冻结量(self) -> None:
        """重置所有冻结量为零"""
        self.多头冻结 = self.多头今冻 = self.多头昨冻 = 0
        self.空头冻结 = self.空头今冻 = self.空头昨冻 = 0

    def 转换委托请求_上期所(self, 请求: 类_订单请求) -> List[类_订单请求]:
        """上期所特殊平仓规则处理"""
        if 请求.开平 == 类_开平.开仓:
            return [请求]

        if 请求.方向 == 类_方向.做多:
            可用总量 = self.空头持仓 - self.空头冻结
            今仓可用 = self.空头今仓 - self.空头今冻
        else:
            可用总量 = self.多头持仓 - self.多头冻结
            今仓可用 = self.多头今仓 - self.多头今冻

        if 请求.数量 > 可用总量:
            return []
        elif 请求.数量 <= 今仓可用:
            今仓请求 = copy(请求)
            今仓请求.开平 = 类_开平.平今
            return [今仓请求]
        else:
            请求列表 = []
            if 今仓可用 > 0:
                今仓部分 = copy(请求)
                今仓部分.开平 = 类_开平.平今
                今仓部分.数量 = 今仓可用
                请求列表.append(今仓部分)

            昨仓部分 = copy(请求)
            昨仓部分.开平 = 类_开平.平昨
            昨仓部分.数量 = 请求.数量 - 今仓可用
            请求列表.append(昨仓部分)

            return 请求列表

    def 转换委托请求_锁定(self, 请求: 类_订单请求) -> List[类_订单请求]:
        """锁仓模式转换"""
        if 请求.方向 == 类_方向.做多:
            今仓数量 = self.空头今仓
            昨仓可用 = self.空头昨仓 - self.空头昨冻
        else:
            今仓数量 = self.多头今仓
            昨仓可用 = self.多头昨仓 - self.多头昨冻

        支持平昨交易所 = {类_交易所.上期所, 类_交易所.能源中心}

        if 今仓数量 and self.交易所 not in 支持平昨交易所:
            开仓请求 = copy(请求)
            开仓请求.开平 = 类_开平.开仓
            return [开仓请求]
        else:
            平仓量 = min(请求.数量, 昨仓可用)
            开仓量 = max(0, 请求.数量 - 昨仓可用)
            请求列表 = []

            if 平仓量:
                平仓请求 = copy(请求)
                if self.交易所 in 支持平昨交易所:
                    平仓请求.开平 = 类_开平.平昨
                else:
                    平仓请求.开平 = 类_开平.平仓
                平仓请求.数量 = 平仓量
                请求列表.append(平仓请求)

            if 开仓量:
                开仓请求 = copy(请求)
                开仓请求.开平 = 类_开平.开仓
                开仓请求.数量 = 开仓量
                请求列表.append(开仓请求)

            return 请求列表

    def 转换委托请求_净仓(self, 请求: 类_订单请求) -> List[类_订单请求]:
        """净仓模式转换"""
        if 请求.方向 == 类_方向.做多:
            可用总量 = self.空头持仓 - self.空头冻结
            今仓可用 = self.空头今仓 - self.空头今冻
            昨仓可用 = self.空头昨仓 - self.空头昨冻
        else:
            可用总量 = self.多头持仓 - self.多头冻结
            今仓可用 = self.多头今仓 - self.多头今冻
            昨仓可用 = self.多头昨仓 - self.多头昨冻

        if 请求.交易所 in {类_交易所.上期所, 类_交易所.能源中心}:
            return self.处理上期所净仓(请求, 可用总量, 今仓可用, 昨仓可用)
        else:
            return self.处理普通净仓(请求, 可用总量)

    def 处理上期所净仓(self, 请求: 类_订单请求, 可用总量: float, 今仓: float, 昨仓: float) -> List[类_订单请求]:
        """处理上期所净仓转换"""
        请求列表 = []
        剩余量 = 请求.数量

        if 今仓:
            今仓量 = min(今仓, 剩余量)
            剩余量 -= 今仓量
            今仓请求 = copy(请求)
            今仓请求.开平 = 类_开平.平今
            今仓请求.数量 = 今仓量
            请求列表.append(今仓请求)

        if 剩余量 and 昨仓:
            昨仓量 = min(昨仓, 剩余量)
            剩余量 -= 昨仓量
            昨仓请求 = copy(请求)
            昨仓请求.开平 = 类_开平.平昨
            昨仓请求.数量 = 昨仓量
            请求列表.append(昨仓请求)

        if 剩余量 > 0:
            开仓请求 = copy(请求)
            开仓请求.开平 = 类_开平.开仓
            开仓请求.数量 = 剩余量
            请求列表.append(开仓请求)

        return 请求列表

    def 处理普通净仓(self, 请求: 类_订单请求, 可用总量: float) -> List[类_订单请求]:
        """处理普通交易所净仓转换"""
        请求列表 = []
        剩余量 = 请求.数量

        if 可用总量:
            平仓量 = min(可用总量, 剩余量)
            剩余量 -= 平仓量
            平仓请求 = copy(请求)
            平仓请求.开平 = 类_开平.平仓
            平仓请求.数量 = 平仓量
            请求列表.append(平仓请求)

        if 剩余量 > 0:
            开仓请求 = copy(请求)
            开仓请求.开平 = 类_开平.开仓
            开仓请求.数量 = 剩余量
            请求列表.append(开仓请求)

        return 请求列表