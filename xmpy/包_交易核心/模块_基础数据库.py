from abc import ABC, abstractmethod
from datetime import datetime
from types import ModuleType
from typing import List
from dataclasses import dataclass
from importlib import import_module
from zoneinfo import ZoneInfo

from .模块_常数 import 类_周期, 类_交易所
from .模块_对象 import 类_K线数据, 类_行情数据
from .模块_设置 import 全局设置
from .包_国际化 import _

# 数据库时区配置
数据库时区 = ZoneInfo(全局设置["数据库.时区"])


def 转换时区(时间对象: datetime) -> datetime:
    """将时间对象转换为数据库时区"""
    转换后时间 = 时间对象.astimezone(数据库时区)
    return 转换后时间.replace(tzinfo=None)


@dataclass
class 类_K线概览:
    """K线数据存储概览"""
    代码: str = ""
    交易所: 类_交易所 = None
    周期: 类_周期 = None
    数量: int = 0
    开始时间: datetime = None
    结束时间: datetime = None


@dataclass
class 类_Tick概览:
    """Tick数据存储概览"""
    代码: str = ""
    交易所: 类_交易所 = None
    数量: int = 0
    开始时间: datetime = None
    结束时间: datetime = None


class 类_基础数据库(ABC):
    """数据库操作基类"""

    @abstractmethod
    def 保存K线数据(self, K线列表: List[类_K线数据], 流式存储: bool = False) -> bool:
        """保存K线数据到数据库"""
        pass

    @abstractmethod
    def 保存Tick数据(self, Tick列表: List[类_行情数据], 流式存储: bool = False) -> bool:
        """保存Tick数据到数据库"""
        pass

    @abstractmethod
    def 加载K线数据(
            self,
            代码: str,
            交易所: 类_交易所,
            周期: 类_周期,
            开始时间: datetime,
            结束时间: datetime
    ) -> List[类_K线数据]:
        """从数据库加载K线数据"""
        pass

    @abstractmethod
    def 加载Tick数据(
            self,
            代码: str,
            交易所: 类_交易所,
            开始时间: datetime,
            结束时间: datetime
    ) -> List[类_行情数据]:
        """从数据库加载Tick数据"""
        pass

    @abstractmethod
    def 删除K线数据(
            self,
            代码: str,
            交易所: 类_交易所,
            周期: 类_周期
    ) -> int:
        """删除指定K线数据"""
        pass

    @abstractmethod
    def 删除Tick数据(
            self,
            代码: str,
            交易所: 类_交易所
    ) -> int:
        """删除指定Tick数据"""
        pass

    @abstractmethod
    def 获取K线概览(self) -> List[类_K线概览]:
        """获取所有K线数据概览"""
        pass

    @abstractmethod
    def 获取Tick概览(self) -> List[类_Tick概览]:
        """获取所有Tick数据概览"""
        pass


# 全局数据库实例
数据库实例: 类_基础数据库 = None


def 获取数据库() -> 类_基础数据库:
    """获取数据库单例实例"""
    global 数据库实例

    if 数据库实例:
        return 数据库实例

    # 从配置获取数据库类型
    数据库类型: str = 全局设置["数据库.类型"]
    模块名称: str = f"xmpy_{数据库类型}"

    try:
        驱动模块 = import_module(模块名称)
    except ModuleNotFoundError:
        print(_("找不到数据库驱动{}，使用默认的SQLite数据库").format(模块名称))
        驱动模块 = import_module("xmpy_sqlite")

    # 实例化数据库对象
    数据库实例 = 驱动模块.Database()
    return 数据库实例