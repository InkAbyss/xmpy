import threading
from time import time
from functools import lru_cache
from typing import Any

import zmq

from .模块_公共 import 心跳主题, 心跳容忍度


class 类_远程异常(Exception):
    """
    RPC 远程调用异常
    """

    def __init__(self, 值: Any) -> None:
        """
        构造函数
        """
        self._值: Any = 值

    def __str__(self) -> str:
        """
        输出错误信息
        """
        return str(self._值)


class 类_RPC客户端:
    """"""

    def __init__(self) -> None:
        """构造函数"""
        # zmq 端口相关
        self._上下文: zmq.Context = zmq.Context()

        # 请求套接字（请求-回复模式）    客户端使用。它发送一个请求，然后等待服务器的回复。一次请求必须对应一次回复，不能连续发多次请求而不接收回复
        self._请求套接字: zmq.Socket = self._上下文.socket(zmq.REQ)

        # 订阅套接字（发布-订阅模式）    订阅者使用。它可以订阅感兴趣的主题，只有匹配主题的消息才会被接收
        self._订阅套接字: zmq.Socket = self._上下文.socket(zmq.SUB)

        # 设置套接字保活选项
        for 套接字 in [self._请求套接字, self._订阅套接字]:        # 开启 TCP Keepalive 机制
            套接字.setsockopt(zmq.TCP_KEEPALIVE, 1)            # 设为 1 表示启用 TCP 保活
            套接字.setsockopt(zmq.TCP_KEEPALIVE_IDLE, 60)      # 设为 60 表示如果连接空闲 60 秒后开始发送保活探测包

        # 工作线程相关，用于处理服务器推送的数据
        self._活跃: bool = False                 # Rpc客户端状态
        self._线程: threading.Thread | None = None      # Rpc客户端线程
        self._锁: threading.Lock = threading.Lock()

        self._最后心跳时间: float = time()

    @lru_cache(100)  # noqa
    def __getattr__(self, 名称: str) -> Any:
        """
        实现远程调用功能
        """
        # 执行远程调用的内部函数
        def 执行远程调用(*参数: Any, **关键字参数: Any) -> Any:
            # 从关键字参数中获取超时值，默认为 30 秒
            超时: int = 关键字参数.pop("timeout", 30000)

            # 构建请求
            请求: list = [名称, 参数, 关键字参数]

            # 发送请求并等待响应
            with self._锁:
                self._请求套接字.send_pyobj(请求)

                # 轮询直到超时或有数据到达
                消息数: int = self._请求套接字.poll(超时)     # 检查 self._请求套接字 在指定超时时间内是否有 可读事件（例如是否有响应数据到达），返回事件数量。
                if not 消息数:
                    消息: str = f"请求 {请求} 在 {超时}ms 内超时"
                    raise 类_远程异常(消息)

                响应 = self._请求套接字.recv_pyobj()

            # 如果成功则返回结果，失败则抛出异常
            if 响应[0]:
                return 响应[1]
            else:
                raise 类_远程异常(响应[1])

        return 执行远程调用

    def 启动(
        self,
        请求地址: str,
        订阅地址: str
    ) -> None:
        """
        启动 Rpc 客户端
        """
        if self._活跃:
            return

        # 连接 zmq 端口
        self._请求套接字.connect(请求地址)
        self._订阅套接字.connect(订阅地址)

        # 设置客户端状态为活跃
        self._活跃 = True

        # 启动客户端线程
        self._线程 = threading.Thread(target=self.运行)
        self._线程.start()

        self._最后心跳时间 = time()

    def 停止(self) -> None:
        """
        停止 Rpc 客户端
        """
        if not self._活跃:
            return

        # 设置客户端状态为不活跃
        self._活跃 = False

    def 等待(self) -> None:
        """等待客户端线程退出"""
        if self._线程 and self._线程.is_alive():
            self._线程.join()
        self._线程 = None

    def 运行(self) -> None:
        """
        运行 Rpc 客户端主循环
        """
        轮询超时: int = 心跳容忍度 * 1000

        while self._活跃:
            if not self._订阅套接字.poll(轮询超时):
                self.连接断开时()
                continue

            # 从订阅套接字接收数据
            主题, 数据 = self._订阅套接字.recv_pyobj(flags=zmq.NOBLOCK)

            if 主题 == 心跳主题:
                self._最后心跳时间 = 数据
            else:
                # 通过可调用函数处理数据
                self.回调(主题, 数据)

        # 关闭套接字
        self._请求套接字.close()
        self._订阅套接字.close()

    def 回调(self, 主题: str, 数据: Any) -> None:
        """
        可调用的处理函数，子类应重写此方法
        """
        raise NotImplementedError

    def 订阅主题(self, 主题: str) -> None:
        """
        订阅指定主题的数据
        """
        self._订阅套接字.setsockopt_string(zmq.SUBSCRIBE, 主题)

    def 连接断开时(self) -> None:
        """
        心跳丢失时的回调函数
        """
        消息: str = f"Rpc服务器在 {心跳容忍度} 秒内无响应，请检查连接。"
        print(消息)