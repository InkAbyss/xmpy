import json
import sys
from pathlib import Path
from typing import Callable, Optional, Union, Tuple
from decimal import Decimal


import numpy as np

import talib
from datetime import datetime, time, timedelta
from .模块_常数 import 类_周期
from .模块_对象 import 类_K线数据,类_行情数据

# from .模块_常数 import 类_交易所,类_周期
from xmpy.包_交易核心.模块_常数 import 类_交易所

if sys.version_info >= (3, 9):
    from zoneinfo import ZoneInfo, available_timezones              # noqa
else:
    from backports.zoneinfo import ZoneInfo, available_timezones    # noqa

def _获取交易目录(文件夹名称: str) -> Tuple[Path, Path]:
    """获取交易平台运行时目录"""
    # 获取当前工作目录
    当前路径: Path = Path.cwd()

    # 拼接临时目录路径
    临时路径: Path = 当前路径.joinpath(文件夹名称)

    # 检查是否存在.vntrader目录
    if 临时路径.exists():
        return 当前路径, 临时路径

    # 获取用户主目录
    用户目录: Path = Path.home()
    临时路径 = 用户目录.joinpath(文件夹名称)

    # 创建不存在的目录
    if not 临时路径.exists():
        临时路径.mkdir()

    return 用户目录, 临时路径


# 初始化目录配置
交易目录, 临时目录 = _获取交易目录(".xmpy文件保存")
sys.path.append(str(交易目录))  # 添加至Python路径


def 获取文件路径(文件名称: str) -> Path:
    """获取临时目录下的文件完整路径"""
    return 临时目录.joinpath(文件名称)


def 加载json文件(文件名称: str) -> dict:
    """从临时目录加载JSON文件数据"""
    文件路径: Path = 获取文件路径(文件名称)

    if 文件路径.exists():
        with open(文件路径, mode="r", encoding="UTF-8") as 文件对象:
            数据字典: dict = json.load(文件对象)
        return 数据字典
    else:
        # 文件不存在时创建空文件
        保存json文件(文件名称, {})
        return {}


def 保存json文件(文件名称: str, 数据字典: dict) -> None:
    """保存数据到临时目录的JSON文件"""
    文件路径: Path = 获取文件路径(文件名称)
    with open(文件路径, mode="w+", encoding="UTF-8") as 文件对象:
        json.dump(
            数据字典,
            文件对象,
            indent=4,           # 4空格缩进
            ensure_ascii=False  # 支持非ASCII字符
        )


def 获取目录路径(目录名称: str) -> Path:
    """获取临时目录下的指定子目录路径"""
    目录路径: Path = 临时目录.joinpath(目录名称)

    if not 目录路径.exists():
        目录路径.mkdir()

    return 目录路径

def 虚拟方法(func: Callable) -> Callable:
    """
    标记函数为"可重写"的虚拟方法
    所有基类应使用此装饰器或@abstractmethod来标记子类可重写的方法
    """
    return func

def 提取合约代码(合约标识: str) -> Tuple[str, '类_交易所']:
    """
    :return: (代码, 交易所)
    """

    代码, 交易所字符串 = 合约标识.rsplit(".", 1)
    return 代码, 类_交易所[交易所字符串]

def 四舍五入到指定值(数值: float, 目标值: float) -> float:
    """
    根据目标值四舍五入价格。
    将价格按最小变动单位四舍五入

    :param 数值: 需要处理的价格数值
    :param 目标值: 最小价格变动单位（如0.5）
    :return: 四舍五入后的标准价格
    """
    数值: Decimal = Decimal(str(数值))
    目标值: Decimal = Decimal(str(目标值))
    四舍五入结果: float = float(int(round(数值 / 目标值)) * 目标值)
    return 四舍五入结果

def 提取合约前缀(合约代码: str) -> str:
    """从合约代码中提取品种部分（去掉数字）"""
    # 使用正则表达式匹配字母部分
    match = re.match(r'([a-zA-Z]+)', 合约代码)
    if match:
        return match.group(1)

class 类_K线生成器:
    """
    K线合成器功能：
    1. 从Tick数据合成1分钟K线
    2. 从基础K线合成多周期K线（分钟/小时/日线）
    注意：
    1. 分钟周期必须为60的约数
    2. 小时周期可为任意整数
    """

    def __init__(
        self,
        K线回调: Callable,
        窗口周期: int = 0,
        窗口回调: Callable = None,
        周期类型: 类_周期 = 类_周期.一分钟,
        日结束时间: time = None
    ) -> None:
        self.当前K线: 类_K线数据 = None
        self.K线回调 = K线回调

        self.周期类型 = 周期类型
        self.周期计数: int = 0

        self.小时K线缓存: 类_K线数据 = None
        self.日K线缓存: 类_K线数据 = None

        self.窗口大小 = 窗口周期
        self.窗口K线缓存: 类_K线数据 = None
        self.窗口回调 = 窗口回调

        self.最后Tick缓存:类_行情数据  = None
        self.日结束时间 = 日结束时间

        if self.周期类型 == 类_周期.日线 and not self.日结束时间:
            raise ValueError("日线合成必须指定收盘时间")

    def 更新Tick(self, tick: 类_行情数据) -> None:
        """处理Tick更新"""
        新周期标志 = False

        if not tick.最新价:
            return

        if not self.当前K线:
            新周期标志 = True
        elif (
                (self.当前K线.时间戳.minute != tick.时间戳.minute)
                or (self.当前K线.时间戳.hour != tick.时间戳.hour)
        ):
            self.当前K线.时间戳 = self.当前K线.时间戳.replace(second=0, microsecond=0)
            self.K线回调(self.当前K线)
            新周期标志 = True

        if 新周期标志:
            self.当前K线 = 类_K线数据(
                代码=tick.代码,
                交易所=tick.交易所,
                周期=类_周期.一分钟,
                时间戳=tick.时间戳,
                网关名称=tick.网关名称,
                开盘价=tick.最新价,
                最高价=tick.最新价,
                最低价=tick.最新价,
                收盘价=tick.最新价,
                持仓量=tick.持仓量
            )
        else:
            self.当前K线.最高价 = max(self.当前K线.最高价, tick.最新价)
            if tick.最高价 > self.最后Tick缓存.最高价:
                self.当前K线.最高价 = max(self.当前K线.最高价, tick.最高价)

            self.当前K线.最低价 = min(self.当前K线.最低价, tick.最新价)
            if tick.最低价 < self.最后Tick缓存.最低价:
                self.当前K线.最低价 = min(self.当前K线.最低价, tick.最低价)

            self.当前K线.收盘价 = tick.最新价
            self.当前K线.持仓量 = tick.持仓量
            self.当前K线.时间 = tick.时间戳

        if self.最后Tick缓存:
            成交量变动 = max(tick.成交量 - self.最后Tick缓存.成交量, 0)
            self.当前K线.成交量 += 成交量变动

            成交额变动 = max(tick.成交额 - self.最后Tick缓存.成交额, 0)
            self.当前K线.成交额 += 成交额变动

        self.最后Tick缓存 = tick

    def 更新K线(self, bar: 类_K线数据) -> None:
        """处理K线更新"""
        if self.周期类型 == 类_周期.一分钟:
            self._处理分钟窗口(bar)
        elif self.周期类型 == 类_周期.一小时:
            self._处理小时窗口(bar)
        else:
            self._处理日线窗口(bar)

    def _处理分钟窗口(self, bar: 类_K线数据) -> None:
        """分钟级窗口处理"""
        if not self.窗口K线缓存:
            基准时间: datetime = bar.时间戳.replace(second=0, microsecond=0)
            self.窗口K线缓存 = 类_K线数据(
                代码=bar.代码,
                交易所=bar.交易所,
                时间戳=基准时间,
                网关名称=bar.网关名称,
                开盘价=bar.开盘价,
                最高价=bar.最高价,
                最低价=bar.最低价
            )
        else:
            self.窗口K线缓存.最高价 = max(self.窗口K线缓存.最高价, bar.最高价)
            self.窗口K线缓存.最低价 = min(self.窗口K线缓存.最低价, bar.最低价)

        self.窗口K线缓存.收盘价 = bar.收盘价
        self.窗口K线缓存.成交量 += bar.成交量
        self.窗口K线缓存.成交额 += bar.成交额
        self.窗口K线缓存.持仓量 = bar.持仓量

        if not (bar.时间戳.minute + 1) % self.窗口大小:
            self.窗口回调(self.窗口K线缓存)
            self.窗口K线缓存 = None

    # 日内对齐等交易时长K线，未完成，先注释
    # def _更新K线数据(self, tick: 类_行情数据, 是否新周期=False) -> None:
    #     """将tick信息更新进当前K线"""
    #     if not self.当前K线:
    #         return
    #
    #     if 是否新周期:
    #         if self.最后Tick缓存:
    #             成交量变动 = max(tick.成交量 - self.最后Tick缓存.成交量, 0)
    #             self.当前K线.成交量 += 成交量变动
    #
    #             成交额变动 = max(tick.成交额 - self.最后Tick缓存.成交额, 0)
    #             self.当前K线.成交额 += 成交额变动
    #
    #         self.最后Tick缓存 = tick
    #         return
    #
    #         # 更新极值时同时考虑tick的high/low字段
    #     self.当前K线.最高价 = max(self.当前K线.最高价, tick.最新价)
    #     if tick.最高价 > self.最后Tick缓存.最高价:
    #         self.当前K线.最高价 = max(self.当前K线.最高价, tick.最高价)
    #
    #     self.当前K线.最低价 = min(self.当前K线.最低价, tick.最新价)
    #     if tick.最低价 < self.最后Tick缓存.最低价:
    #         self.当前K线.最低价 = min(self.当前K线.最低价, tick.最低价)
    #
    #     self.当前K线.收盘价 = tick.最新价
    #     self.当前K线.持仓量 = tick.持仓量
    #     self.当前K线.时间戳 = tick.时间戳
    #
    #     # 处理成交量（需考虑tick之间可能的重传情况）
    #     if self.最后Tick缓存:
    #         成交量变动 = max(tick.成交量 - self.最后Tick缓存.成交量, 0)
    #         self.当前K线.成交量 += 成交量变动
    #
    #         成交额变动 = max(tick.成交额 - self.最后Tick缓存.成交额, 0)
    #         self.当前K线.成交额 += 成交额变动
    #
    #     self.最后Tick缓存 = tick
    #
    # def 更新Tick(self, tick: 类_行情数据) -> None:
    #     """处理Tick更新"""
    #     新周期标志 = False
    #     if not tick.最新价:
    #         return
    #
    #     # 生成基准时间戳（自然分钟结束点）
    #     基准时间 = tick.时间戳.replace(second=0, microsecond=0) + timedelta(minutes=1)
    #
    #     # 新周期判断条件
    #     if not self.当前K线:  # 初始化
    #         新周期标志 = True
    #     else:
    #         if (self.当前K线.时间戳.minute != tick.时间戳.minute) or (self.当前K线.时间戳.hour != tick.时间戳.hour):
    #             新周期标志 = True
    #
    #     收盘时间集 = {(10, 15), (11, 30), (15, 0), (2, 30)}
    #
    #     # 收盘tick应直接更新K线并推送
    #     if self.当前K线 and (tick.时间戳.hour, tick.时间戳.minute) in 收盘时间集:
    #         self._更新K线数据(tick)
    #         self.当前K线.时间戳 = 基准时间 - timedelta(minutes=1)
    #
    #         # # 大商所15点收盘后，过3-4分钟还会推送一条tick数据，将它归类到15点这根K线
    #         # if self.当前K线.交易所.value == 'DCE' and (tick.时间戳.hour, tick.时间戳.minute) in (15, 0):
    #         #     self.大商所收盘计数 += 1
    #         #     if self.大商所收盘计数 == 2:
    #         #         print('=== 推送大商所收盘时间集')
    #         #         self.K线回调(self.当前K线)
    #         #         self.当前K线 = None
    #         #         self.大商所收盘计数 = 0
    #         #         return
    #         #     else:
    #         #         return
    #
    #         self.K线回调(self.当前K线)
    #         self.当前K线 = None
    #         return
    #
    #     特殊收盘时间集 = {(23, 0)}
    #     if self.当前K线 and self.当前K线.交易所.value != 'SHFE' and (
    #     tick.时间戳.hour, tick.时间戳.minute) in 特殊收盘时间集:
    #         self._更新K线数据(tick)
    #         self.当前K线.时间戳 = 基准时间 - timedelta(minutes=1)
    #
    #         print('=== 推送特殊收盘时间集')
    #         self.K线回调(self.当前K线)
    #         self.当前K线 = None
    #         return
    #
    #     if 新周期标志:
    #         # 先保存旧K线（如果有）
    #         if self.当前K线:
    #             self.当前K线.时间戳 = 基准时间 - timedelta(minutes=1)  # 显示为周期起始时间
    #             self.K线回调(self.当前K线)
    #
    #         # 创建新K线（开盘价用第一个有效tick的最新价）
    #         self.当前K线 = 类_K线数据(
    #             代码=tick.代码,
    #             交易所=tick.交易所,
    #             周期=类_周期.一分钟,
    #             时间戳=基准时间 - timedelta(minutes=1),  # K线起始时间
    #             网关名称=tick.网关名称,
    #             开盘价=tick.最新价,
    #             最高价=tick.最新价,  # 初始化用tick的最高价
    #             最低价=tick.最新价,  # 初始化用tick的最低价
    #             收盘价=tick.最新价,
    #             持仓量=tick.持仓量,
    #             成交量=0,
    #             成交额=0
    #         )
    #         self._更新K线数据(tick, 是否新周期=True)
    #     else:
    #         self._更新K线数据(tick)
    #
    # def 更新K线(self, bar: 类_K线数据) -> None:
    #     """处理K线更新"""
    #     if self.周期类型 == 类_周期.一分钟:
    #         self._处理分钟窗口(bar)
    #     elif self.周期类型 == 类_周期.一小时:
    #         self._处理小时窗口(bar)
    #     else:
    #         self._处理日线窗口(bar)
    #
    # def _处理分钟窗口(self, bar: 类_K线数据) -> None:
    #     """分钟级窗口处理"""
    #     if not self.窗口K线缓存:
    #         基准时间: datetime = bar.时间戳.replace(second=0, microsecond=0) + timedelta(minutes=1)
    #         self.窗口K线缓存 = 类_K线数据(
    #             代码=bar.代码,
    #             交易所=bar.交易所,
    #             时间戳=基准时间,
    #             网关名称=bar.网关名称,
    #             开盘价=bar.开盘价,
    #             最高价=bar.最高价,
    #             最低价=bar.最低价
    #         )
    #     else:
    #         self.窗口K线缓存.最高价 = max(self.窗口K线缓存.最高价, bar.最高价)
    #         self.窗口K线缓存.最低价 = min(self.窗口K线缓存.最低价, bar.最低价)
    #
    #     self.窗口K线缓存.收盘价 = bar.收盘价
    #     self.窗口K线缓存.成交量 += bar.成交量
    #     self.窗口K线缓存.成交额 += bar.成交额
    #     self.窗口K线缓存.持仓量 = bar.持仓量
    #
    #     if not (bar.时间戳.minute) % self.窗口大小:
    #         self.窗口回调(self.窗口K线缓存)
    #         self.窗口K线缓存 = None

    def _处理小时窗口(self, bar: 类_K线数据) -> None:
        """小时级窗口处理"""
        if not self.小时K线缓存:
            基准时间: datetime = bar.时间戳.replace(minute=0, second=0, microsecond=0)
            self.小时K线缓存 = 类_K线数据(
                代码=bar.代码,
                交易所=bar.交易所,
                时间戳=基准时间,
                网关名称=bar.网关名称,
                开盘价=bar.开盘价,
                最高价=bar.最高价,
                最低价=bar.最低价,
                收盘价=bar.收盘价,
                成交量=bar.成交量,
                成交额=bar.成交额,
                持仓量=bar.持仓量
            )
            return

        完成K线 = None

        if bar.时间戳.minute == 59:
            self.小时K线缓存.最高价 = max(self.小时K线缓存.最高价, bar.最高价)
            self.小时K线缓存.最低价 = min(self.小时K线缓存.最低价, bar.最低价)
            self.小时K线缓存.收盘价 = bar.收盘价
            self.小时K线缓存.成交量 += bar.成交量
            self.小时K线缓存.成交额 += bar.成交额
            self.小时K线缓存.持仓量 = bar.持仓量

            完成K线 = self.小时K线缓存
            self.小时K线缓存 = None
        elif bar.时间戳.hour != self.小时K线缓存.时间戳.hour:
            完成K线 = self.小时K线缓存
            基准时间: datetime = bar.时间戳.replace(minute=0, second=0, microsecond=0)
            self.小时K线缓存 = 类_K线数据(
                代码=bar.代码,
                交易所=bar.交易所,
                时间戳=基准时间,
                网关名称=bar.网关名称,
                开盘价=bar.开盘价,
                最高价=bar.最高价,
                最低价=bar.最低价,
                收盘价=bar.收盘价,
                成交量=bar.成交量,
                成交额=bar.成交额,
                持仓量=bar.持仓量
            )
        else:
            self.小时K线缓存.最高价 = max(self.小时K线缓存.最高价, bar.最高价)
            self.小时K线缓存.最低价 = min(self.小时K线缓存.最低价, bar.最低价)
            self.小时K线缓存.收盘价 = bar.收盘价
            self.小时K线缓存.成交量 += bar.成交量
            self.小时K线缓存.成交额 += bar.成交额
            self.小时K线缓存.持仓量 = bar.持仓量

        if 完成K线:
            self._处理完成小时K线(完成K线)

    def _处理完成小时K线(self, bar: 类_K线数据) -> None:
        """完成小时K线后续处理"""
        if self.窗口大小 == 1:
            self.窗口回调(bar)
        else:
            if not self.窗口K线缓存:
                self.窗口K线缓存 = 类_K线数据(
                    代码=bar.代码,
                    交易所=bar.交易所,
                    时间戳=bar.时间戳,
                    网关名称=bar.网关名称,
                    开盘价=bar.开盘价,
                    最高价=bar.最高价,
                    最低价=bar.最低价
                )
            else:
                self.窗口K线缓存.最高价 = max(self.窗口K线缓存.最高价, bar.最高价)
                self.窗口K线缓存.最低价 = min(self.窗口K线缓存.最低价, bar.最低价)

            self.窗口K线缓存.收盘价 = bar.收盘价
            self.窗口K线缓存.成交量 += bar.成交量
            self.窗口K线缓存.成交额 += bar.成交额
            self.窗口K线缓存.持仓量 = bar.持仓量

            self.周期计数 += 1
            if not self.周期计数 % self.窗口大小:
                self.周期计数 = 0
                self.窗口回调(self.窗口K线缓存)
                self.窗口K线缓存 = None

    def _处理日线窗口(self, bar: 类_K线数据) -> None:
        """日线级窗口处理"""
        if not self.日K线缓存:
            self.日K线缓存 = 类_K线数据(
                代码=bar.代码,
                交易所=bar.交易所,
                时间戳=bar.时间戳,
                网关名称=bar.网关名称,
                开盘价=bar.开盘价,
                最高价=bar.最高价,
                最低价=bar.最低价
            )
        else:
            self.日K线缓存.最高价 = max(self.日K线缓存.最高价, bar.最高价)
            self.日K线缓存.最低价 = min(self.日K线缓存.最低价, bar.最低价)

        self.日K线缓存.收盘价 = bar.收盘价
        self.日K线缓存.成交量 += bar.成交量
        self.日K线缓存.成交额 += bar.成交额
        self.日K线缓存.持仓量 = bar.持仓量

        if bar.时间戳.time() == self.日结束时间:
            self.日K线缓存.时间 = bar.时间戳.replace(hour=0, minute=0, second=0, microsecond=0)
            self.窗口回调(self.日K线缓存)
            self.日K线缓存 = None

    def 立即生成(self) -> Optional[类_K线数据]:
        """强制生成当前K线"""
        if self.当前K线:
            self.当前K线.时间 = self.当前K线.时间.replace(second=0, microsecond=0)
            self.K线回调(self.当前K线)
            result = self.当前K线
            self.当前K线 = None
            return result
        return None

class 类_数组管理器:
    """
    时间序列管理与技术指标计算
    功能：
    1. 维护K线时间序列
    2. 计算各类技术指标
    """

    def __init__(self, 容量: int = 100) -> None:
        self.数据计数: int = 0
        self.最大容量 = 容量
        self.就绪标志: bool = False

        # 初始化存储数组
        self.开盘序列 = np.zeros(容量)
        self.最高序列 = np.zeros(容量)
        self.最低序列 = np.zeros(容量)
        self.收盘序列 = np.zeros(容量)
        self.成交量序列 = np.zeros(容量)
        self.成交额序列 = np.zeros(容量)
        self.持仓量序列 = np.zeros(容量)

    def 更新K线(self, bar: 类_K线数据) -> None:
        """更新新K线数据"""
        self.数据计数 += 1
        if not self.就绪标志 and self.数据计数 >= self.最大容量:
            self.就绪标志 = True

        # 滚动更新数组
        self.开盘序列[:-1] = self.开盘序列[1:]
        self.最高序列[:-1] = self.最高序列[1:]
        self.最低序列[:-1] = self.最低序列[1:]
        self.收盘序列[:-1] = self.收盘序列[1:]
        self.成交量序列[:-1] = self.成交量序列[1:]
        self.成交额序列[:-1] = self.成交额序列[1:]
        self.持仓量序列[:-1] = self.持仓量序列[1:]

        # 填充最新数据
        self.开盘序列[-1] = bar.开盘价
        self.最高序列[-1] = bar.最高价
        self.最低序列[-1] = bar.最低价
        self.收盘序列[-1] = bar.收盘价
        self.成交量序列[-1] = bar.成交量
        self.成交额序列[-1] = bar.成交额
        self.持仓量序列[-1] = bar.持仓量

    @property
    def 开盘价(self) -> np.ndarray:
        return self.开盘序列

    @property
    def 最高价(self) -> np.ndarray:
        return self.最高序列

    @property
    def 最低价(self) -> np.ndarray:
        return self.最低序列

    @property
    def 收盘价(self) -> np.ndarray:
        return self.收盘序列

    @property
    def 成交量(self) -> np.ndarray:
        return self.成交量序列

    @property
    def 成交额(self) -> np.ndarray:
        return self.成交额序列

    @property
    def 持仓量(self) -> np.ndarray:
        return self.持仓量序列

    def 简单移动平均(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.SMA(self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 指数移动平均(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.EMA(self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 自适应均线(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.KAMA(self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 加权移动平均(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.WMA(self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 绝对价格振荡(self, 快周期: int, 慢周期: int, 移动平均类型: int = 0, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.APO(self.收盘价, 快周期, 慢周期, 移动平均类型)
        return 结果 if 数组模式 else 结果[-1]

    def 钱德动量摆动(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.CMO(self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 动量指标(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.MOM(self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 价格振荡百分比(self, 快周期: int, 慢周期: int, 移动平均类型: int = 0, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.PPO(self.收盘价, 快周期, 慢周期, 移动平均类型)
        return 结果 if 数组模式 else 结果[-1]

    def 变动率(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.ROC(self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 变动率比(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.ROCR(self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 变动率百分比(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.ROCP(self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 变动率比100(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.ROCR100(self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 三重指数均线(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.TRIX(self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 标准差(self, 周期: int, 偏差: int = 1, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.STDDEV(self.收盘价, 周期, 偏差)
        return 结果 if 数组模式 else 结果[-1]

    def 能量潮指标(self, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.OBV(self.收盘价, self.成交量)
        return 结果 if 数组模式 else 结果[-1]

    def 商品通道指数(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.CCI(self.最高价, self.最低价, self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 平均真实波幅(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.ATR(self.最高价, self.最低价, self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 归一化波幅(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.NATR(self.最高价, self.最低价, self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 相对强弱指数(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.RSI(self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def MACD指标(
        self,
        快周期: int,
        慢周期: int,
        信号周期: int,
        数组模式: bool = False
    ) -> Union[Tuple[float, float, float], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        macd, 信号线, 柱状图 = talib.MACD(self.收盘价, 快周期, 慢周期, 信号周期)
        return (macd, 信号线, 柱状图) if 数组模式 else (macd[-1], 信号线[-1], 柱状图[-1])

    def 平均趋向指数(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.ADX(self.最高价, self.最低价, self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 平均趋向指数评级(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.ADXR(self.最高价, self.最低价, self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 趋向指数(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.DX(self.最高价, self.最低价, self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 负向指标(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.MINUS_DI(self.最高价, self.最低价, self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 正向指标(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.PLUS_DI(self.最高价, self.最低价, self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 威廉指标(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.WILLR(self.最高价, self.最低价, self.收盘价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 终极振荡器(
        self,
        周期1: int = 7,
        周期2: int = 14,
        周期3: int = 28,
        数组模式: bool = False
    ) -> Union[float, np.ndarray]:
        结果 = talib.ULTOSC(self.最高价, self.最低价, self.收盘价, 周期1, 周期2, 周期3)
        return 结果 if 数组模式 else 结果[-1]

    def 真实波动幅度(self, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.TRANGE(self.最高价, self.最低价, self.收盘价)
        return 结果 if 数组模式 else 结果[-1]

    def 布林通道(
        self,
        周期: int,
        标准差倍数: float,
        数组模式: bool = False
    ) -> Union[Tuple[float, float], Tuple[np.ndarray, np.ndarray]]:
        中轨 = self.简单移动平均(周期, 数组模式)
        标准差 = self.标准差(周期, 1, 数组模式)
        上轨 = 中轨 + 标准差 * 标准差倍数
        下轨 = 中轨 - 标准差 * 标准差倍数
        return (上轨, 下轨)

    def 肯特纳通道(
        self,
        周期: int,
        波幅倍数: float,
        数组模式: bool = False
    ) -> Union[Tuple[float, float], Tuple[np.ndarray, np.ndarray]]:
        中轨 = self.简单移动平均(周期, 数组模式)
        波幅 = self.平均真实波幅(周期, 数组模式)
        上轨 = 中轨 + 波幅 * 波幅倍数
        下轨 = 中轨 - 波幅 * 波幅倍数
        return (上轨, 下轨)

    def 唐奇安通道(
        self,
        周期: int,
        数组模式: bool = False
    ) -> Union[Tuple[float, float], Tuple[np.ndarray, np.ndarray]]:
        上轨 = talib.MAX(self.最高价, 周期)
        下轨 = talib.MIN(self.最低价, 周期)
        return (上轨, 下轨) if 数组模式 else (上轨[-1], 下轨[-1])

    def 阿隆指标(
        self,
        周期: int,
        数组模式: bool = False
    ) -> Union[Tuple[float, float], Tuple[np.ndarray, np.ndarray]]:
        阿隆上, 阿隆下 = talib.AROON(self.最高价, self.最低价, 周期)
        return (阿隆上, 阿隆下) if 数组模式 else (阿隆上[-1], 阿隆下[-1])

    def 阿隆振荡器(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.AROONOSC(self.最高价, self.最低价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 负向动向指标(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.MINUS_DM(self.最高价, self.最低价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 正向动向指标(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.PLUS_DM(self.最高价, self.最低价, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 资金流量指数(self, 周期: int, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.MFI(self.最高价, self.最低价, self.收盘价, self.成交量, 周期)
        return 结果 if 数组模式 else 结果[-1]

    def 累积分布指标(self, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.AD(self.最高价, self.最低价, self.收盘价, self.成交量)
        return 结果 if 数组模式 else 结果[-1]

    def 累积振荡指标(
        self,
        快周期: int,
        慢周期: int,
        数组模式: bool = False
    ) -> Union[float, np.ndarray]:
        结果 = talib.ADOSC(self.最高价, self.最低价, self.收盘价, self.成交量, 快周期, 慢周期)
        return 结果 if 数组模式 else 结果[-1]

    def 均势指标(self, 数组模式: bool = False) -> Union[float, np.ndarray]:
        结果 = talib.BOP(self.开盘价, self.最高价, self.最低价, self.收盘价)
        return 结果 if 数组模式 else 结果[-1]

    def 随机指标(
        self,
        快K周期: int,
        慢K周期: int,
        慢K类型: int,
        慢D周期: int,
        慢D类型: int,
        数组模式: bool = False
    ) -> Union[Tuple[float, float], Tuple[np.ndarray, np.ndarray]]:
        K值, D值 = talib.STOCH(
            self.最高价,
            self.最低价,
            self.收盘价,
            快K周期,
            慢K周期,
            慢K类型,
            慢D周期,
            慢D类型
        )
        return (K值, D值) if 数组模式 else (K值[-1], D值[-1])

    def 抛物线指标(
        self,
        加速因子: float,
        极限值: float,
        数组模式: bool = False
    ) -> Union[float, np.ndarray]:
        结果 = talib.SAR(self.最高价, self.最低价, 加速因子, 极限值)
        return 结果 if 数组模式 else 结果[-1]



if __name__ == "__main__":
    # 使用示例
    合约标识 = "TA506.郑商所"
    代码, 交易所 = 提取合约代码(合约标识)
    print(f"代码: {代码}, 交易所对应字符串: {交易所}")