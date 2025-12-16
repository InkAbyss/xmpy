import json
import sys
from pathlib import Path
from typing import Callable, Optional, Union, Tuple
from decimal import Decimal
import requests
from bs4 import BeautifulSoup
import numpy as np
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


if __name__ == "__main__":
    # 使用示例
    合约标识 = "TA506.郑商所"
    代码, 交易所 = 提取合约代码(合约标识)
    print(f"代码: {代码}, 交易所对应字符串: {交易所}")