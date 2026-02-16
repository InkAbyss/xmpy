import threading
import traceback
from time import time
from collections.abc import Callable

import zmq

from .模块_公共 import 心跳主题, 心跳间隔


class 类_RPC服务端:
    """RPC 服务器类"""

    def __init__(self) -> None:
        """
        构造函数
        """
        # 保存函数字典：键为函数名，值为函数对象
        self._函数字典: dict[str, Callable] = {}

        # Zmq 端口相关
        self._上下文: zmq.Context = zmq.Context()

        # 回复套接字（请求-回复模式）    服务器使用。它接收客户端的请求，处理完后发送回复。一次接收必须对应一次发送。
        self._回复套接字: zmq.Socket = self._上下文.socket(zmq.REP)

        # 发布套接字（发布-订阅模式）    发布者使用。它只管不停地发布消息，不需要知道有哪些订阅者
        self._发布套接字: zmq.Socket = self._上下文.socket(zmq.PUB)

        # 工作线程相关
        self._活跃: bool = False                          # Rpc服务器状态
        self._线程: threading.Thread | None = None        # Rpc服务器线程
        self._锁: threading.Lock = threading.Lock()

        # 心跳相关
        self._心跳时间: float | None = None

    def 是否活跃(self) -> bool:
        """返回服务器是否处于活跃状态"""
        return self._活跃

    def 启动(
        self,
        回复地址: str,
        发布地址: str,
    ) -> None:
        """
        启动 Rpc 服务器
        """
        if self._活跃:
            return

        # 绑定套接字地址
        self._回复套接字.bind(回复地址)
        self._发布套接字.bind(发布地址)

        # 设置服务器状态为活跃
        self._活跃 = True

        # 启动服务器线程
        self._线程 = threading.Thread(target=self.运行)
        self._线程.start()

        # 初始化心跳发布时间戳
        self._心跳时间 = time() + 心跳间隔

    def 停止(self) -> None:
        """
        停止 Rpc 服务器
        """
        if not self._活跃:
            return

        # 设置服务器状态为不活跃
        self._活跃 = False

    def 等待(self) -> None:
        """等待服务器线程退出"""
        if self._线程 and self._线程.is_alive():
            self._线程.join()
        self._线程 = None

    def 运行(self) -> None:
        """
        运行 Rpc 服务器主循环
        """
        while self._活跃:
            # 轮询回复套接字 1 秒
            消息数: int = self._回复套接字.poll(1000)
            self.检查心跳()

            if not 消息数:
                continue

            # 从回复套接字接收请求数据
            请求数据 = self._回复套接字.recv_pyobj()

            # 解析函数名和参数
            函数名, 参数, 关键字参数 = 请求数据

            # 尝试获取并执行函数，失败时捕获异常
            try:
                函数对象: Callable = self._函数字典[函数名]
                结果: object = 函数对象(*参数, **关键字参数)
                响应: list = [True, 结果]
            except Exception as e:  # noqa
                响应 = [False, traceback.format_exc()]

            # 通过回复套接字发送响应
            self._回复套接字.send_pyobj(响应)

        # 关闭套接字
        self._发布套接字.close()
        self._回复套接字.close()

    def 发布(self, 主题: str, 数据: object) -> None:
        """
        发布数据到指定主题
        """
        with self._锁:
            self._发布套接字.send_pyobj([主题, 数据])

    def 注册函数(self, 函数: Callable) -> None:
        """
        注册可调用的函数
        """
        self._函数字典[函数.__name__] = 函数

    def 检查心跳(self) -> None:
        """
        检查是否需要发送心跳
        """
        当前时间: float = time()

        if self._心跳时间 and 当前时间 >= self._心跳时间:
            # 发布心跳
            self.发布(心跳主题, 当前时间)

            # 更新下一次心跳时间
            self._心跳时间 = 当前时间 + 心跳间隔