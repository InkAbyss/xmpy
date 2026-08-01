import json
import sys
from pathlib import Path
from typing import Callable, Optional, Union, Tuple
from decimal import Decimal
import requests
from bs4 import BeautifulSoup
import numpy as np
from time import sleep
from datetime import datetime, time, timedelta
import threading
import re
from zoneinfo import ZoneInfo
from typing import List, Dict, Any
from collections import deque
from copy import copy

from .模块_常数 import 类_周期
from .模块_对象 import 类_K线数据,类_行情数据

from xmpy.包_交易核心.模块_常数 import 类_交易所,类_方向, 类_开平

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

    # 检查是否存在.xmpy文件保存目录
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

def 保存文本文件(文件名称: str, 内容) -> None:
    """将任意内容保存为临时目录中的 .txt 文件"""
    文件路径: Path = 获取文件路径(文件名称 + ".txt")

    # 将内容转换为字符串
    if isinstance(内容, (dict, list, tuple)):
        # 如果是结构化数据，用 JSON 格式美化输出（便于阅读）
        内容字符串 = json.dumps(内容, indent=4, ensure_ascii=False)
    else:
        # 其他类型直接转为字符串
        内容字符串 = str(内容)

    with open(文件路径, mode="a", encoding="UTF-8") as 文件对象:
        文件对象.write(内容字符串 + "\n")

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

def 提取合约代码(合约_交易所: str) -> Tuple[str, '类_交易所']:
    """
    :return: (代码, 交易所)
    """

    代码, 交易所字符串 = 合约_交易所.rsplit(".", 1)
    return 代码, 类_交易所[交易所字符串]

def 合约_交易所转英文(合约_交易所) -> str:
    代码, 交易所 = 提取合约代码(合约_交易所)
    return f"{代码}.{交易所.value}"

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
        周期类型: 类_周期 = 类_周期.分钟,
        日结束时间: time = None,
        回测=False
    ) -> None:
        self.当前K线: Optional[类_K线数据] = None
        self.K线回调 = K线回调

        self.周期类型 = 周期类型
        self.周期计数: int = 0

        self.小时K线缓存: Optional[类_K线数据] = None
        self.日K线缓存: Optional[类_K线数据] = None

        self.窗口大小 = 窗口周期
        self.窗口K线缓存: Optional[类_K线数据] = None
        self.窗口回调 = 窗口回调

        self.最后Tick缓存: Optional[类_行情数据] = None
        self.日结束时间 = 日结束时间

        if self.周期类型 == 类_周期.日线 and not self.日结束时间:
            raise ValueError("日线合成必须指定收盘时间")

        self.回测 = 回测
        self.收盘定时器 = None
        self.日盘收盘已触发 = False
        self.开盘已触发 = False
        self.收盘已触发 = False
        self.获取收盘时间 = False

        self.夜盘小时 = None
        self.夜盘分钟 = None
        self.日盘小时 = None
        self.日盘分钟 = None

        self.昨收废弃价 = False

        from .模块_设置 import 全局设置
        self.数据库时区 = ZoneInfo(全局设置["数据库.时区"])

        # 加载收盘时间配置
        try:
            self.收盘时间 = 加载json文件("收盘时间.json")
        except Exception as e:
            print(f"加载收盘时间配置文件失败: {e}")
            self.收盘时间 = {}

        # 品种前缀将在第一次 tick 时确定
        self.品种前缀 = None

    def _获取品种前缀(self, tick: 类_行情数据) -> str:
        """从 tick 代码中提取品种前缀（如 'rb', 'au' 等）"""
        if self.品种前缀 is None:
            match = re.match(r'[A-Za-z]+', tick.代码)
            self.品种前缀 = match.group() if match else ""
        return self.品种前缀

    def _获取收盘时间(self, tick: 类_行情数据, 是否夜盘: bool, 是否回测: bool = False) -> tuple[int, int]:
        """
        获取日盘或夜盘的收盘时间（小时, 分钟）
        如果配置缺失则返回默认值
        """
        默认时间 = {
            "夜盘": (23, 0),
            "日盘": (15, 0),
            "实盘夜盘": (22, 59)
        }

        # 实盘时间映射
        实盘时间映射 = {
            "23:00": "22:59",
            "1:00": "0:59",
            "2:30": "2:29",
            "15:00": "14:59",
            "15:15": "15:14"
        }

        品种前缀 = self._获取品种前缀(tick)
        时间配置 = self.收盘时间.get(品种前缀, {})

        # 根据回测和夜盘状态确定时间字符串
        if 是否回测:
            if 是否夜盘:
                时间字符串 = 时间配置.get("夜盘收盘时间") or "23:00"
                默认小时, 默认分钟 = 默认时间["夜盘"]
            else:
                时间字符串 = 时间配置.get("日盘收盘时间") or "15:00"
                默认小时, 默认分钟 = 默认时间["日盘"]
        else:
            if 是否夜盘:
                时间字符串 = 时间配置.get("夜盘收盘时间") or "23:00"
                时间字符串 = 实盘时间映射.get(时间字符串, 时间字符串)
                默认小时, 默认分钟 = 默认时间["实盘夜盘"]
            else:
                时间字符串 = 时间配置.get("日盘收盘时间") or "15:00"
                时间字符串 = 实盘时间映射.get(时间字符串, 时间字符串)
                默认小时, 默认分钟 = 默认时间["日盘"]

        # 解析时间
        try:
            小时, 分钟 = map(int, 时间字符串.split(':'))
        except (ValueError, AttributeError):
            print(f"解析收盘时间失败: {时间字符串}，使用默认值")
            小时, 分钟 = 默认小时, 默认分钟

        return 小时, 分钟

    def _设置收盘定时器(self, 目标时间: datetime, 午盘 = False, 夜盘 = False) -> None:
        """启动一个定时器，在目标时间执行收盘回调"""
        if self.收盘定时器 is not None:
            return

        def 收盘完成():
            if self.当前K线:
                if 夜盘:
                    目标小时 = self.夜盘小时
                    目标分钟 = self.夜盘分钟

                    目标分钟 += 1
                    if 目标分钟 >= 60:
                        目标小时 += 1
                        目标分钟 -= 60
                    self.当前K线.时间戳 = self.最后Tick缓存.时间戳.replace(hour=目标小时, minute=目标分钟, second=0, microsecond=0)
                elif 午盘:
                    目标小时 = 11
                    目标分钟 = 30
                    self.当前K线.时间戳 = self.最后Tick缓存.时间戳.replace(hour=目标小时, minute=目标分钟, second=0,microsecond=0)
                else:
                    目标小时 = self.日盘小时
                    目标分钟 = self.日盘分钟

                    目标分钟 += 1
                    if 目标分钟 >= 60:
                        目标小时 += 1
                        目标分钟 -= 60
                    self.当前K线.时间戳 = self.最后Tick缓存.时间戳.replace(hour=目标小时, minute=目标分钟, second=0, microsecond=0)
                self.K线回调(self.当前K线)
                self.当前K线 = None
            self.收盘定时器 = None
            self.昨收废弃价 = False

        当前时间 = datetime.now()
        if 当前时间 >= 目标时间:
            收盘完成()
        else:
            等待秒数 = (目标时间 - 当前时间).total_seconds()
            self.收盘定时器 = threading.Timer(等待秒数, 收盘完成)
            self.收盘定时器.start()

    def _更新K线数据(self, tick: 类_行情数据, 是否新周期=False) -> None:
        if not self.当前K线:
            return

        if 是否新周期:
            if self.最后Tick缓存:
                成交量变动 = max(tick.成交量 - self.最后Tick缓存.成交量, 0)
                self.当前K线.成交量 += 成交量变动

                成交额变动 = max(tick.成交额 - self.最后Tick缓存.成交额, 0)
                self.当前K线.成交额 += 成交额变动

            self.最后Tick缓存 = tick
            return

        # 更新极值时同时考虑 tick 的 最高价/最低价 字段
        self.当前K线.最高价 = max(self.当前K线.最高价, tick.最新价)
        if tick.最高价 > self.最后Tick缓存.最高价:
            self.当前K线.最高价 = max(self.当前K线.最高价, tick.最高价)

        self.当前K线.最低价 = min(self.当前K线.最低价, tick.最新价)
        if tick.最低价 < self.最后Tick缓存.最低价:
            self.当前K线.最低价 = min(self.当前K线.最低价, tick.最低价)

        self.当前K线.收盘价 = tick.最新价
        self.当前K线.持仓量 = tick.持仓量
        self.当前K线.时间戳 = tick.时间戳

        # 处理成交量（需考虑 tick 之间可能的重传情况）
        if self.最后Tick缓存:
            成交量变动 = max(tick.成交量 - self.最后Tick缓存.成交量, 0)
            self.当前K线.成交量 += 成交量变动

            成交额变动 = max(tick.成交额 - self.最后Tick缓存.成交额, 0)
            self.当前K线.成交额 += 成交额变动

        self.最后Tick缓存 = tick

    def _获取日盘夜盘收盘时间(self, tick: 类_行情数据):
        if self.回测:
            self.夜盘小时, self.夜盘分钟 = self._获取收盘时间(tick, 是否夜盘=True, 是否回测=True)
            self.日盘小时, self.日盘分钟 = self._获取收盘时间(tick, 是否夜盘=False, 是否回测=True)
        else:
            self.夜盘小时, self.夜盘分钟 = self._获取收盘时间(tick, 是否夜盘=True)
            self.日盘小时, self.日盘分钟 = self._获取收盘时间(tick, 是否夜盘=False)

    def _处理回测模式(self, tick: 类_行情数据) -> bool:
        """
        回测模式下的特殊逻辑
        返回 True 表示已经处理完毕（无需继续普通流程），False 表示继续
        """
        # if not self.回测:
        #     return False

        # 09:00 时强制更新但不产生新 K 线（特殊处理）
        if self.当前K线 and tick.时间戳.hour == 9 and tick.时间戳.minute == 0:
            self._更新K线数据(tick)
            return True

        # 10:15临休
        if self.当前K线 and tick.时间戳.hour == 10 and 15 <= tick.时间戳.minute <= 16:
            self._更新K线数据(tick)
            self.当前K线.时间戳 = self.最后Tick缓存.时间戳.replace(hour=10, minute=15, second=0, microsecond=0)
            self.K线回调(self.当前K线)
            self.当前K线 = None
            return True

        # 11:30午休
        if self.当前K线 and tick.时间戳.hour == 11 and 30 <= tick.时间戳.minute <= 35:
            self._更新K线数据(tick)
            self.当前K线.时间戳 = self.最后Tick缓存.时间戳.replace(hour=11, minute=30, second=0, microsecond=0)
            self.K线回调(self.当前K线)
            self.当前K线 = None
            return True

        # 日盘收盘（15:00 或 15:15后不再接受新数据）
        if self.当前K线 and tick.时间戳.hour == self.日盘小时 and 0 <= tick.时间戳.minute <= self.日盘分钟 + 6:
            self._更新K线数据(tick)
            self.日盘收盘已触发 = True
            return True

        # 夜盘收盘（23:00 或 2:30）
        if self.当前K线 and (tick.时间戳.hour == self.夜盘小时 and tick.时间戳.minute == self.夜盘分钟):
            if not self.收盘已触发:
                self.收盘已触发 = True
                self._更新K线数据(tick)
                # 强制将时间戳设为 23:00:00 或 2:30:00
                self.当前K线.时间戳 = self.最后Tick缓存.时间戳.replace(hour=self.夜盘小时, minute=self.夜盘分钟, second=0, microsecond=0)
                self.K线回调(self.当前K线)
                self.当前K线 = None
            return True

        # 日盘收盘后，等待夜盘或次日开盘，重新生成 K 线时调整时间戳
        if self.日盘收盘已触发:
            if self.当前K线 and tick.时间戳.hour in (20, 21, 8, 9):
                if not self.开盘已触发:
                    self.开盘已触发 = True
                    self.当前K线.时间戳 = self.最后Tick缓存.时间戳.replace(hour=self.日盘小时, minute=self.日盘分钟, second=0, microsecond=0)
                    self.K线回调(self.当前K线)
                    self.当前K线 = None
            # 离开相关时段时重置标志
            if tick.时间戳.hour not in (20, 21, 8, 9):
                self.开盘已触发 = False
                self.收盘已触发 = False
                self.日盘收盘已触发 = False

        return False

    def _处理实时模式(self, tick: 类_行情数据) -> bool:
        """
        实时模式下的收盘逻辑
        返回 True 表示已经处理完毕，False 表示继续
        """
        # if self.回测:
        #     return False

        if not self.昨收废弃价:
            过滤时间 = datetime.now(self.数据库时区)
            时间差 = timedelta(seconds=60)
            tick时间差 = abs(tick.时间戳 - 过滤时间)

            if abs(tick时间差) >= 时间差:
                self.昨收废弃价 = True
                # print(f'接收到昨天废弃收盘价，丢弃 {tick}')
                return True

        # 09:00 时强制更新但不产生新 K 线（特殊处理）
        if self.当前K线 and tick.时间戳.hour == 9 and tick.时间戳.minute == 0:
            self._更新K线数据(tick)
            return True

        if self.收盘定时器:
            self._更新K线数据(tick)
            return True

        # 10:15临休
        if self.当前K线 and tick.时间戳.hour == 10 and 15 <= tick.时间戳.minute <= 16:
            self._更新K线数据(tick)
            self.当前K线.时间戳 = self.最后Tick缓存.时间戳.replace(hour=10, minute=15, second=0, microsecond=0)
            self.K线回调(self.当前K线)
            self.当前K线 = None
            return True

        # 11:30午休
        if self.当前K线 and tick.时间戳.hour == 11 and tick.时间戳.minute == 29:
            if self.收盘定时器 is None:
                目标小时 = 11
                目标分钟 = 29

                目标分钟 += 7
                if 目标分钟 >= 60:
                    目标小时 += 1
                    目标分钟 -= 60
                目标时间 = datetime.now().replace(hour=目标小时, minute=目标分钟, second=0, microsecond=0)
                self._设置收盘定时器(目标时间, 午盘 = True)
                return False

        # 日盘收盘
        if self.当前K线 and tick.时间戳.hour == self.日盘小时 and tick.时间戳.minute == self.日盘分钟:
            if self.收盘定时器 is None:
                目标小时 = self.日盘小时
                目标分钟 = self.日盘分钟

                目标分钟 += 7
                if 目标分钟 >= 60:
                    目标小时 += 1
                    目标分钟 -= 60
                目标时间 = datetime.now().replace(hour=目标小时, minute=目标分钟, second=0, microsecond=0)
                self._设置收盘定时器(目标时间)
                # 定时器触发后会回调，这里继续更新 K 线数据
                # print(f'看一下3：{tick}')
                return False

        # 夜盘收盘
        if self.当前K线 and tick.时间戳.hour == self.夜盘小时 and tick.时间戳.minute == self.夜盘分钟:
            if self.收盘定时器 is None:
                目标小时 = self.夜盘小时
                目标分钟 = self.夜盘分钟

                目标分钟 += 2
                if 目标分钟 >= 60:
                    目标小时 += 1
                    目标分钟 -= 60
                目标时间 = datetime.now().replace(hour=目标小时, minute=目标分钟, second=0, microsecond=0)
                # print(f'看一下：{self.夜盘小时}   {self.夜盘分钟}')
                # print(f'看一下2：{tick}')
                self._设置收盘定时器(目标时间, 夜盘=True)
                return False

        return False

    def 更新Tick(self, tick: 类_行情数据) -> None:
        """处理 Tick 更新"""
        if not tick.最新价:
            return

        if self.回测:
            if self._处理回测模式(tick):
                return
        else:
            if self._处理实时模式(tick):
                return

        # 正常周期判断
        基准时间 = tick.时间戳.replace(second=0, microsecond=0) + timedelta(minutes=1)
        新周期标志 = False

        if not self.当前K线:
            新周期标志 = True
        else:
            # 分钟变化或小时变化（跨小时）视为新周期
            if (self.当前K线.时间戳.minute != tick.时间戳.minute or
                self.当前K线.时间戳.hour != tick.时间戳.hour):
                新周期标志 = True

        if 新周期标志:
            # 先保存旧K线（如果有）
            if self.当前K线:
                self.当前K线.时间戳 = 基准时间 - timedelta(minutes=1)  # 显示为周期起始时间
                self.K线回调(self.当前K线)

            # 创建新K线（开盘价用第一个有效tick的最新价）
            self.当前K线 = 类_K线数据(
                代码=tick.代码,
                交易所=tick.交易所,
                周期=类_周期.分钟,
                时间戳=基准时间 - timedelta(minutes=1),  # K线起始时间
                网关名称=tick.网关名称,
                开盘价=tick.最新价,
                最高价=tick.最新价,  # 初始化用tick的最高价
                最低价=tick.最新价,  # 初始化用tick的最低价
                收盘价=tick.最新价,
                持仓量=tick.持仓量,
                成交量=0,
                成交额=0
            )
            self._更新K线数据(tick, 是否新周期=True)

            if not self.获取收盘时间:
                self.获取收盘时间 = True
                self._获取日盘夜盘收盘时间(tick)
        else:
            self._更新K线数据(tick)

    def 更新K线(self, bar: 类_K线数据) -> None:
        """处理K线更新"""
        if self.周期类型 == 类_周期.分钟:
            self._处理分钟窗口(bar)
        elif self.周期类型 == 类_周期.小时:
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
        self.窗口K线缓存.时间戳 = bar.时间戳.replace(second=0, microsecond=0)

        if not (bar.时间戳.minute) % self.窗口大小:
            self.窗口回调(self.窗口K线缓存)
            self.窗口K线缓存 = None

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
            self.日K线缓存.时间戳 = bar.时间戳.replace(hour=0, minute=0, second=0, microsecond=0)
            self.窗口回调(self.日K线缓存)
            self.日K线缓存 = None

    def 立即生成(self) -> Optional[类_K线数据]:
        """强制生成当前K线"""
        if self.当前K线:
            self.当前K线.时间戳 = self.当前K线.时间戳.replace(second=0, microsecond=0)
            self.K线回调(self.当前K线)
            result = self.当前K线
            self.当前K线 = None
            return result
        return None


def 爬取主力合约表格():
    # 固定文件名
    文件名称 = "主力合约记录.json"

    # 获取当天日期
    今天日期 = datetime.now().strftime("%Y-%m-%d")

    try:
        # 尝试加载现有JSON文件
        现有数据 = 加载json文件(文件名称)

        # 检查日期是否为今天
        if 现有数据 and 现有数据.get("日期") == 今天日期:
            print(f"今天({今天日期})的数据已存在，跳过爬取")
            return
    except Exception as e:
        # 文件不存在或其他错误，继续执行爬取
        print(f"加载现有文件失败: {e}，开始爬取新数据")

    # 执行爬取
    网址 = "http://openctp.cn/fees.html"

    try:
        # 发送请求获取网页内容
        响应 = requests.get(网址)
        响应.encoding = 'utf-8'  # 设置编码

        if 响应.status_code == 200:
            解析器 = BeautifulSoup(响应.text, 'html.parser')

            # 找到表格
            表格 = 解析器.find('table', {'id': 'fees_table'})

            if 表格:
                # 获取黄色背景的行数据
                合约代码列表 = []
                表格主体 = 表格.find('tbody')

                for 行 in 表格主体.find_all('tr'):
                    单元格列表 = 行.find_all('td')

                    # 确保有足够的列
                    if len(单元格列表) > 1:
                        交易所 = 单元格列表[0].text.strip()  # 第一列是交易所
                        合约代码单元格 = 单元格列表[1]  # 第二列是合约代码

                        # 只检查合约代码单元格是否有黄色背景
                        单元格样式 = 合约代码单元格.get('style')
                        if 单元格样式 and 'background-color:yellow' in 单元格样式:
                            合约代码 = 合约代码单元格.text.strip()
                            拼接结果 = f"{合约代码}.{交易所}"
                            合约代码列表.append({
                                "合约代码": 合约代码,
                                "交易所": 交易所,
                                "完整代码": 拼接结果
                            })

                # 按交易所分组
                分组数据 = {}
                for 合约 in 合约代码列表:
                    交易所 = 合约["交易所"]
                    if 交易所 not in 分组数据:
                        分组数据[交易所] = []
                    分组数据[交易所].append(合约["完整代码"])

                # 构建输出数据
                输出数据 = {
                    "日期": 今天日期,
                    "数据": 分组数据
                }

                # 打印结果
                if 合约代码列表:
                    # 调用外部保存函数
                    保存json文件(文件名称, 输出数据)
                    print(f"\n今日主力合约数据已保存到: {文件名称}")
                else:
                    print("未找到符合条件的合约数据")

            else:
                print("未找到表格")
        else:
            print(f"请求失败，状态码: {响应.status_code}")

    except Exception as 异常:
        print(f"发生错误: {异常}")

def 处理合约信息(交易所名称: str = "全部") -> None:
    """
    处理合约数据

    参数:
        交易所名称: 交易所名称，默认为"全部"，可选CZCE、GFEX、CFFEX、DCE、SHFE、INE

    返回:
        主力合约列表
    """
    # 加载JSON文件
    文件名称 = "主力合约记录.json"
    现有数据 = 加载json文件(文件名称)
    数据字典 = 现有数据['数据']

    # 验证交易所名称
    if 交易所名称 != "全部" and 交易所名称 not in 数据字典:
        raise ValueError(f"错误: 未找到交易所 {交易所名称}。可选的交易所有: {', '.join(数据字典.keys())}")

    # 选择要处理的交易所
    目标交易所列表 = [交易所名称] if 交易所名称 != "全部" else 数据字典.keys()

    # 收集合约代码
    主力合约列表 = []
    for 交易所 in 目标交易所列表:
        合约列表 = 数据字典[交易所]
        主力合约列表.extend(合约列表)

    return 主力合约列表


def 生成交易对(交易列表: list) -> List[Dict[str, Any]]:
    """
    将买卖交易列表配对生成开平仓交易对。
    正确区分 开/平 标志，按时间顺序进行 FIFO 配对。
    """
    # 按时间戳排序
    交易列表 = sorted(交易列表, key=lambda t: t.时间戳)

    # 多头和空头持仓队列，每个元素为 {"时间戳", "价格", "数量"}
    多头交易列表 = deque()
    空头交易列表 = deque()

    交易对列表 = []

    for 当前交易 in 交易列表:
        # 拷贝以防修改原数据
        交易 = copy(当前交易)
        方向 = 交易.方向
        开平 = 交易.开平
        价格 = 交易.价格
        数量 = 交易.数量
        时间戳 = 交易.时间戳

        if 方向 == 类_方向.做多 and 开平 == 类_开平.开仓:
            # 多头开仓，加入持仓队列
            多头交易列表.append({
                "时间戳": 时间戳,
                "价格": 价格,
                "数量": 数量
            })

        elif 方向 == 类_方向.做空 and 开平 == 类_开平.开仓:
            # 空头开仓，加入持仓队列
            空头交易列表.append({
                "时间戳": 时间戳,
                "价格": 价格,
                "数量": 数量
            })

        elif 方向 == 类_方向.做多 and 开平 == 类_开平.平仓:
            # 买入平空（平空头持仓）
            平仓数量 = 数量
            while 平仓数量 > 0 and 空头交易列表:
                开仓记录 = 空头交易列表[0]
                匹配数量 = min(开仓记录["数量"], 平仓数量)

                交易对列表.append({
                    "开仓时间": 开仓记录["时间戳"] + timedelta(minutes=1),
                    "开仓价格": 开仓记录["价格"],
                    "平仓时间": 时间戳 + timedelta(minutes=1),
                    "平仓价格": 价格,
                    "开仓方向": 类_方向.做空,  # 平空，开仓方向是空
                    "平仓方向": 类_方向.做多,  # 平仓方向是多
                    "数量": 匹配数量
                })

                开仓记录["数量"] -= 匹配数量
                平仓数量 -= 匹配数量

                if 开仓记录["数量"] == 0:
                    空头交易列表.popleft()

        elif 方向 == 类_方向.做空 and 开平 == 类_开平.平仓:
            # 卖出平多（平多头持仓）
            平仓数量 = 数量
            while 平仓数量 > 0 and 多头交易列表:
                开仓记录 = 多头交易列表[0]
                匹配数量 = min(开仓记录["数量"], 平仓数量)

                交易对列表.append({
                    "开仓时间": 开仓记录["时间戳"] + timedelta(minutes=1),
                    "开仓价格": 开仓记录["价格"],
                    "平仓时间": 时间戳 + timedelta(minutes=1),
                    "平仓价格": 价格,
                    "开仓方向": 类_方向.做多,  # 平多，开仓方向是多
                    "平仓方向": 类_方向.做空,  # 平仓方向是空
                    "数量": 匹配数量
                })

                开仓记录["数量"] -= 匹配数量
                平仓数量 -= 匹配数量

                if 开仓记录["数量"] == 0:
                    多头交易列表.popleft()

    # ---- 处理剩余未平仓持仓 ----
    for 持仓 in 多头交易列表:
        if 持仓["数量"] > 0:
            交易对列表.append({
                "开仓时间": 持仓["时间戳"] + timedelta(minutes=1),
                "开仓价格": 持仓["价格"],
                "平仓时间": None,  # 尚未平仓
                "平仓价格": None,
                "开仓方向": 类_方向.做多,
                "平仓方向": None,
                "数量": 持仓["数量"]
            })

    for 持仓 in 空头交易列表:
        if 持仓["数量"] > 0:
            交易对列表.append({
                "开仓时间": 持仓["时间戳"] + timedelta(minutes=1),
                "开仓价格": 持仓["价格"],
                "平仓时间": None,
                "平仓价格": None,
                "开仓方向": 类_方向.做空,
                "平仓方向": None,
                "数量": 持仓["数量"]
            })

    return 交易对列表

if __name__ == "__main__":
    # 使用示例
    合约_交易所 = "TA506.郑商所"
    代码, 交易所 = 提取合约代码(合约_交易所)
    print(f"代码: {代码}, 交易所对应字符串: {交易所}")