import logging
from logging import Logger
import smtplib
import os
import traceback
from abc import ABC
from pathlib import Path
from datetime import datetime
from email.message import EmailMessage
from queue import Empty, Queue
from threading import Thread
from typing import Any, Type, Dict, List, Optional

from xmpy.包_事件引擎 import 类_事件,类_事件引擎
from .模块_应用 import 类_基础应用
from .模块_事件类型 import (
    事件类型_行情,
    事件类型_订单,
    事件类型_成交,
    事件类型_持仓,
    事件类型_账户,
    事件类型_合约,
    事件类型_日志,
    事件类型_报价
)
from .模块_网关 import 类_基础网关
from .模块_对象 import (
    类_撤单请求,
    类_日志数据,
    类_委托请求,
    类_报价数据,
    类_报价请求,
    类_订阅请求,
    类_历史数据请求,
    类_委托数据,
    类_K线数据,
    类_行情数据,
    类_成交数据,
    类_持仓数据,
    类_账户数据,
    类_合约数据,
    类_交易所
)
from .模块_设置 import 全局设置
from .模块_工具 import 获取目录路径,交易目录
from .模块_转换器 import 类_持仓转换器
from xmpy.包_交易核心.包_国际化 import _


class 类_主引擎:
    """交易平台核心引擎"""

    def __init__(self, 事件引擎: 类_事件引擎 = None) -> None:
        if 事件引擎:
            self.事件引擎: 类_事件引擎 = 事件引擎
        else:
            self.事件引擎 = 类_事件引擎()
        self.事件引擎.启动引擎()

        self.网关字典: Dict[str, 类_基础网关] = {}
        self.引擎字典: Dict[str, 基础引擎] = {}
        self.应用字典: Dict[str, 类_基础应用] = {}
        self.交易所列表: List[类_交易所] = []

        os.chdir(交易目录)
        self.初始化引擎()

    def 添加引擎(self, 引擎类: Any) -> "基础引擎":
        """添加功能引擎"""
        引擎实例: 基础引擎 = 引擎类(self, self.事件引擎)
        self.引擎字典[引擎实例.引擎名称] = 引擎实例
        return 引擎实例

    def 添加网关(self, 网关类: Type[类_基础网关], 网关名称: str = "") -> 类_基础网关:
        """添加交易通道"""
        网关名称 = 网关名称 or 网关类.默认名称
        新网关: 类_基础网关 = 网关类(self.事件引擎, 网关名称)
        self.网关字典[网关名称] = 新网关

        for 交易所 in 新网关.支持交易所:
            if 交易所 not in self.交易所列表:
                self.交易所列表.append(交易所)
        return 新网关

    def 添加应用(self, 应用类: Type[类_基础应用]) -> "基础引擎":
        """添加功能应用"""
        应用实例: 类_基础应用 = 应用类()
        self.应用字典[应用实例.应用名称] = 应用实例

        引擎实例: 基础引擎 = self.添加引擎(应用实例.引擎类)
        return 引擎实例

    def 初始化引擎(self) -> None:
        """初始化所有引擎"""
        self.添加引擎(日志引擎)
        self.添加引擎(订单管理引擎)
        self.添加引擎(邮件引擎)

    def 记录日志(self, 消息: str, 来源: str = "") -> None:
        """记录日志事件"""
        日志记录: 类_日志数据 = 类_日志数据(消息内容=消息, 网关名称=来源)
        事件实例: 类_事件 = 类_事件(事件类型_日志, 日志记录)
        self.事件引擎.放入事件(事件实例)

    def 获取网关(self, 网关名称: str) -> 类_基础网关:
        """按名称获取网关"""
        网关实例: 类_基础网关 = self.网关字典.get(网关名称, None)
        if not 网关实例:
            self.记录日志(_("找不到底层接口：{}").format(网关名称))
        return 网关实例

    def 获取引擎(self, 引擎名称: str) -> "基础引擎":
        """按名称获取引擎"""
        引擎实例: 基础引擎 = self.引擎字典.get(引擎名称, None)
        if not 引擎实例:
            self.记录日志(_("找不到引擎：{}").format(引擎名称))
        return 引擎实例

    def 获取默认配置(self, 网关名称: str) -> Optional[Dict[str, Any]]:
        """获取网关默认配置"""
        网关实例: 类_基础网关 = self.获取网关(网关名称)
        return 网关实例.获取默认配置() if 网关实例 else None

    def 获取所有网关名称(self) -> List[str]:
        """获取全部网关名称"""
        return list(self.网关字典.keys())

    def 获取所有应用(self) -> List[类_基础应用]:
        """获取全部应用实例"""
        return list(self.应用字典.values())

    def 获取所有交易所(self) -> List[类_交易所]:
        """获取支持的所有交易所"""
        return self.交易所列表

    def 连接网关(self, 全局设置: dict, 网关名称: str) -> None:
        """连接指定网关"""
        网关实例: 类_基础网关 = self.获取网关(网关名称)
        if 网关实例:
            网关实例.连接(全局设置)

    def 订阅行情(self, 请求: 类_订阅请求, 网关名称: str) -> None:
        """订阅行情数据"""
        网关实例: 类_基础网关 = self.获取网关(网关名称)
        if 网关实例:
            网关实例.订阅行情(请求)

    def 发送委托(self, 请求: 类_委托请求, 网关名称: str) -> str:
        """委托下单"""
        网关实例: 类_基础网关 = self.获取网关(网关名称)
        return 网关实例.发送委托(请求) if 网关实例 else ""

    def 撤消订单(self, 请求: 类_撤单请求, 网关名称: str) -> None:
        """撤销订单"""
        网关实例: 类_基础网关 = self.获取网关(网关名称)
        if 网关实例:
            网关实例.撤消订单(请求)

    def 发送报价(self, 请求: 类_报价请求, 网关名称: str) -> str:
        """发送报价"""
        网关实例: 类_基础网关 = self.获取网关(网关名称)
        return 网关实例.发送报价(请求) if 网关实例 else ""

    def 撤消报价(self, 请求: 类_撤单请求, 网关名称: str) -> None:
        """撤销报价"""
        网关实例: 类_基础网关 = self.获取网关(网关名称)
        if 网关实例:
            网关实例.撤消报价(请求)

    def 查询历史(self, 请求: 类_历史数据请求, 网关名称: str) -> Optional[List[类_K线数据]]:
        """查询历史数据"""
        网关实例: 类_基础网关 = self.获取网关(网关名称)
        return 网关实例.查询历史(请求) if 网关实例 else None

    def 关闭(self) -> None:
        """关闭所有组件"""
        self.事件引擎.停止引擎()
        for 引擎 in self.引擎字典.values():
            引擎.关闭()
        for 网关 in self.网关字典.values():
            网关.断开连接()

class 基础引擎(ABC):
    """功能引擎基类"""

    def __init__(
        self,
        主引擎: 类_主引擎,
        事件引擎: 类_事件引擎,
        引擎名称: str,
    ) -> None:
        self.主引擎: 类_主引擎 = 主引擎
        self.事件引擎: 类_事件引擎 = 事件引擎
        self.引擎名称: str = 引擎名称

    def 关闭(self) -> None:
        pass

class 日志引擎(基础引擎):
    """处理日志事件"""

    def __init__(self, 主引擎: 类_主引擎, 事件引擎: 类_事件引擎) -> None:
        super().__init__(主引擎, 事件引擎, "日志")

        if not 全局设置["日志.启用"]:
            return

        self.日志级别: int = 全局设置["日志.级别"]
        self.日志记录器: Logger = logging.getLogger("veighna")
        self.日志记录器.setLevel(self.日志级别)

        self.格式器: logging.Formatter = logging.Formatter(
            "%(asctime)s  %(levelname)s: %(message)s"
        )

        self.添加空处理器()
        if 全局设置["日志.控制台"]:
            self.添加控制台处理器()
        if 全局设置["日志.文件"]:
            self.添加文件处理器()

        self.注册事件()

    def 添加空处理器(self) -> None:
        """防止无处理器错误"""
        self.日志记录器.addHandler(logging.NullHandler())

    def 添加控制台处理器(self) -> None:
        """控制台日志输出"""
        控制台处理器 = logging.StreamHandler()
        控制台处理器.setLevel(self.日志级别)
        控制台处理器.setFormatter(self.格式器)
        self.日志记录器.addHandler(控制台处理器)

    def 添加文件处理器(self) -> None:
        """文件日志输出"""
        当天日期 = datetime.now().strftime("%Y%m%d")
        日志目录:Path = 获取目录路径("log")
        文件路径:Path = 日志目录 / f"vt_{当天日期}.log"

        文件处理器 = logging.FileHandler(文件路径, mode="a", encoding="utf8")
        文件处理器.setLevel(self.日志级别)
        文件处理器.setFormatter(self.格式器)
        self.日志记录器.addHandler(文件处理器)

    def 注册事件(self) -> None:
        self.事件引擎.注册类型处理器(事件类型_日志, self.处理日志事件)

    def 处理日志事件(self, 事件: 类_事件) -> None:
        日志记录: 类_日志数据 = 事件.数据
        self.日志记录器.log(日志记录.日志级别, 日志记录.消息内容)

class 订单管理引擎(基础引擎):
    """订单管理系统"""

    def __init__(self, 主引擎: 类_主引擎, 事件引擎: 类_事件引擎) -> None:
        super().__init__(主引擎, 事件引擎, "订单管理")

        self.行情字典: Dict[str, 类_行情数据] = {}
        self.订单字典: Dict[str, 类_委托数据] = {}
        self.成交字典: Dict[str, 类_成交数据] = {}
        self.持仓字典: Dict[str, 类_持仓数据] = {}
        self.账户字典: Dict[str, 类_账户数据] = {}
        self.合约字典: Dict[str, 类_合约数据] = {}
        self.报价字典: Dict[str, 类_报价数据] = {}

        self.活跃订单字典: Dict[str, 类_委托数据] = {}
        self.活跃报价字典: Dict[str, 类_报价数据] = {}

        self.仓位转换器字典: Dict[str, 类_持仓转换器] = {}

        self.绑定查询功能()
        self.注册事件()

    def 绑定查询功能(self) -> None:
        """将查询功能绑定到主引擎"""
        self.主引擎.获取最新行情 = self.获取最新行情
        self.主引擎.获取订单详情 = self.获取订单详情
        self.主引擎.获取成交详情 = self.获取成交详情
        self.主引擎.获取持仓详情 = self.获取持仓详情
        self.主引擎.获取账户详情 = self.获取账户详情
        self.主引擎.获取合约详情 = self.获取合约详情
        self.主引擎.获取报价详情 = self.获取报价详情

        self.主引擎.获取所有行情 = self.获取所有行情
        self.主引擎.获取所有订单 = self.获取所有订单
        self.主引擎.获取所有成交 = self.获取所有成交
        self.主引擎.获取所有持仓 = self.获取所有持仓
        self.主引擎.获取所有账户 = self.获取所有账户
        self.主引擎.获取所有合约 = self.获取所有合约
        self.主引擎.获取所有报价 = self.获取所有报价
        self.主引擎.获取活跃订单 = self.获取活跃订单
        self.主引擎.获取活跃报价 = self.获取活跃报价

        self.主引擎.更新委托请求 = self.更新委托请求
        self.主引擎.转换委托请求 = self.转换委托请求
        self.主引擎.获取仓位转换器 = self.获取仓位转换器

    def 注册事件(self) -> None:
        self.事件引擎.注册类型处理器(事件类型_行情, self.处理行情事件)
        self.事件引擎.注册类型处理器(事件类型_订单, self.处理订单事件)
        self.事件引擎.注册类型处理器(事件类型_成交, self.处理成交事件)
        self.事件引擎.注册类型处理器(事件类型_持仓, self.处理持仓事件)
        self.事件引擎.注册类型处理器(事件类型_账户, self.处理账户事件)
        self.事件引擎.注册类型处理器(事件类型_合约, self.处理合约事件)
        self.事件引擎.注册类型处理器(事件类型_报价, self.处理报价事件)

    def 处理行情事件(self, 事件: 类_事件) -> None:
        行情:类_行情数据 = 事件.数据
        self.行情字典[行情.唯一标识] = 行情

    def 处理订单事件(self, 事件: 类_事件) -> None:
        订单 = 事件.数据
        self.订单字典[订单.订单唯一标识] = 订单

        if 订单.是否活跃():
            self.活跃订单字典[订单.订单唯一标识] = 订单
        elif 订单.订单唯一标识 in self.活跃订单字典:
            self.活跃订单字典.pop(订单.订单唯一标识)

        转换器 = self.仓位转换器字典.get(订单.网关名称)
        if 转换器:
            转换器.更新委托(订单)

    def 处理成交事件(self, 事件: 类_事件) -> None:
        成交 = 事件.数据
        self.成交字典[成交.成交唯一标识] = 成交

        转换器 = self.仓位转换器字典.get(成交.网关名称)
        if 转换器:
            转换器.更新成交(成交)

    def 处理持仓事件(self, 事件: 类_事件) -> None:
        持仓 = 事件.数据
        self.持仓字典[持仓.持仓唯一标识] = 持仓

        转换器 = self.仓位转换器字典.get(持仓.网关名称)
        if 转换器:
            转换器.更新持仓(持仓)

    def 处理账户事件(self, 事件: 类_事件) -> None:
        账户:类_账户数据 = 事件.数据
        self.账户字典[账户.账户唯一标识] = 账户

    def 处理合约事件(self, 事件: 类_事件) -> None:
        合约: 类_合约数据 = 事件.数据
        self.合约字典[合约.唯一标识] = 合约

        if 合约.网关名称 not in self.仓位转换器字典:
            self.仓位转换器字典[合约.网关名称] = 类_持仓转换器(self)

    def 处理报价事件(self, 事件: 类_事件) -> None:
        报价 = 事件.数据
        self.报价字典[报价.报价唯一标识] = 报价

        if 报价.是否活跃():
            self.活跃报价字典[报价.报价唯一标识] = 报价
        elif 报价.报价唯一标识 in self.活跃报价字典:
            self.活跃报价字典.pop(报价.报价唯一标识)

    # 以下为查询方法（保留原有功能，中文方法名）
    def 获取最新行情(self, 合约标识: str) -> Optional[类_行情数据]:
        return self.行情字典.get(合约标识)

    def 获取订单详情(self, 订单标识: str) -> Optional[类_委托数据]:
        return self.订单字典.get(订单标识)

    def 获取成交详情(self, 成交标识: str) -> Optional[类_成交数据]:
        return self.成交字典.get(成交标识)

    def 获取持仓详情(self, 持仓标识: str) -> Optional[类_持仓数据]:
        return self.持仓字典.get(持仓标识)

    def 获取账户详情(self, 账户标识: str) -> Optional[类_账户数据]:
        return self.账户字典.get(账户标识)

    def 获取合约详情(self, 合约标识: str) -> Optional[类_合约数据]:
        return self.合约字典.get(合约标识, None)

    def 获取报价详情(self, 报价标识: str) -> Optional[类_报价数据]:
        return self.报价字典.get(报价标识)

    def 获取所有行情(self) -> List[类_行情数据]:
        return list(self.行情字典.values())

    def 获取所有订单(self) -> List[类_委托数据]:
        return list(self.订单字典.values())

    def 获取所有成交(self) -> List[类_成交数据]:
        return list(self.成交字典.values())

    def 获取所有持仓(self) -> List[类_持仓数据]:
        return list(self.持仓字典.values())

    def 获取所有账户(self) -> List[类_账户数据]:
        return list(self.账户字典.values())

    def 获取所有合约(self) -> List[类_合约数据]:
        return list(self.合约字典.values())

    def 获取所有报价(self) -> List[类_报价数据]:
        return list(self.报价字典.values())

    def 获取活跃订单(self, 合约标识: str = "") -> List[类_委托数据]:
        if not 合约标识:
            return list(self.活跃订单字典.values())
        return [订单 for 订单 in self.活跃订单字典.values() if 订单.唯一标识 == 合约标识]

    def 获取活跃报价(self, 合约标识: str = "") -> List[类_报价数据]:
        if not 合约标识:
            return list(self.活跃报价字典.values())
        return [报价 for 报价 in self.活跃报价字典.values() if 报价.唯一标识 == 合约标识]

    def 更新委托请求(self, 请求: 类_委托请求, 订单标识: str, 网关名称: str) -> None:
        转换器 = self.仓位转换器字典.get(网关名称)
        if 转换器:
            转换器.更新委托请求(请求, 订单标识)

    def 转换委托请求(
        self,
        请求: 类_委托请求,
        网关名称: str,
        锁定: bool,
        净额: bool = False
    ) -> List[类_委托请求]:
        转换器 = self.仓位转换器字典.get(网关名称)
        return 转换器.转换委托请求(请求, 锁定, 净额) if 转换器 else [请求]

    def 获取仓位转换器(self, 网关名称: str) -> 类_持仓转换器:
        return self.仓位转换器字典.get(网关名称)


class 邮件引擎(基础引擎):
    """提供邮件发送功能"""

    def __init__(self, 主引擎: 类_主引擎, 事件引擎: 类_事件引擎) -> None:
        super().__init__(主引擎, 事件引擎, "邮件")

        # 邮件发送线程
        self.发送线程: Thread = Thread(target=self.运行)
        self.邮件队列: Queue = Queue()
        self.运行状态: bool = False

        # 将发送方法暴露给主引擎
        self.主引擎.发送邮件 = self.发送邮件

    def 发送邮件(self, 主题: str, 内容: str, 收件人: str = "") -> None:
        """将邮件放入发送队列"""
        # 首次发送时启动线程
        if not self.运行状态:
            self.启动()

        # 使用默认收件人
        if not 收件人:
            收件人: str = 全局设置["邮件.收件人"]

        # 构建邮件消息
        邮件消息 = EmailMessage()
        邮件消息["From"] = 全局设置["邮件.发件人"]
        邮件消息["To"] = 收件人
        邮件消息["Subject"] = 主题
        邮件消息.set_content(内容)

        self.邮件队列.put(邮件消息)

    def 运行(self) -> None:
        """邮件发送线程主循环"""
        服务器地址 = 全局设置["邮件.服务器"]
        端口号 = 全局设置["邮件.端口"]
        用户名 = 全局设置["邮件.用户名"]
        密码 = 全局设置["邮件.密码"]

        while self.运行状态:
            try:
                # 从队列获取邮件
                待发邮件 = self.邮件队列.get(block=True, timeout=1)

                try:
                    # 建立安全连接
                    with smtplib.SMTP_SSL(服务器地址, 端口号) as 邮件连接:
                        邮件连接.login(用户名, 密码)
                        邮件连接.send_message(待发邮件)
                except Exception as 异常:
                    # 记录发送失败日志
                    错误信息 = traceback.format_exc()
                    self.主引擎.记录日志(_("邮件发送失败: {}").format(错误信息), "邮件")

            except Empty:  # 空队列异常
                pass

    def 启动(self) -> None:
        """启动邮件发送线程"""
        self.运行状态 = True
        self.发送线程.start()

    def 关闭(self) -> None:
        """安全关闭邮件服务"""
        if not self.运行状态:
            return

        self.运行状态 = False
        self.发送线程.join()