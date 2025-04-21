from collections import defaultdict
from queue import Empty, Queue
from threading import Thread
from time import sleep
from typing import Any, Callable, List

# 事件类型常量
事件类型_定时 = "eTimer"

class 类_事件:
    """事件对象：包含类型标识和携带数据"""
    def __init__(self, 类型: str, 数据: Any = None) -> None:
        self.类型: str = 类型    # 事件类型标识
        self.数据: Any = 数据    # 事件关联数据

# 类型别名定义
处理器类型 = Callable[[类_事件], None]

class 类_事件引擎:
    """事件驱动核心引擎，负责事件分发和定时触发"""
    def __init__(self, 间隔秒数: int = 1) -> None:
        self._间隔: int = 间隔秒数          # 定时事件间隔
        self._事件队列: Queue = Queue()     # 事件存储队列
        self._运行状态: bool = False        # 引擎运行标志
        self._事件处理线程: Thread = Thread(target=self._运行循环)    # 主处理线程
        self._定时器线程: Thread = Thread(target=self._生成定时事件)  # 定时事件线程
        self._类型处理器映射: defaultdict = defaultdict(list)       # 按类型分类的处理器    _类型处理器字典/列表
        self._通用处理器列表: List = []

    def _运行循环(self) -> None:
        """事件处理主循环"""
        while self._运行状态:
            try:
                # 获取事件（阻塞1秒避免忙等待）
                当前事件: 类_事件 = self._事件队列.get(block=True, timeout=1)
                self._处理事件(当前事件)
            except Empty:  # 空队列异常处理
                pass

    def _处理事件(self, 事件对象: 类_事件) -> None:
        """执行事件分发逻辑"""
        # 处理特定类型订阅者
        if 事件对象.类型 in self._类型处理器映射:
            [处理器函数(事件对象) for 处理器函数 in self._类型处理器映射[事件对象.类型]]

        # 处理全局订阅者
        if self._通用处理器列表:
            [处理器函数(事件对象) for 处理器函数 in self._通用处理器列表]

    def _生成定时事件(self) -> None:
        """定时事件生成器"""
        while self._运行状态:
            sleep(self._间隔)  # 等待间隔时间
            定时事件对象: 类_事件 = 类_事件(事件类型_定时)  # 创建定时事件
            self.放入事件(定时事件对象)  # 加入处理队列

    def 启动引擎(self) -> None:
        """启动事件处理服务"""
        self._运行状态 = True
        self._事件处理线程.start()  # 启动主线程
        self._定时器线程.start()  # 启动定时器

    def 停止引擎(self) -> None:
        """安全停止事件服务"""
        self._运行状态 = False
        self._定时器线程.join()  # 等待定时器终止
        self._事件处理线程.join()  # 等待主线程终止

    def 放入事件(self, 事件对象: 类_事件) -> None:
        """添加事件到处理队列"""
        self._事件队列.put(事件对象)

    def 注册类型处理器(self, 事件类型: str, 处理器函数: 处理器类型) -> None:
        """注册特定事件类型的处理函数"""
        处理器列表: list = self._类型处理器映射[事件类型]
        if 处理器函数 not in 处理器列表:  # 避免重复注册
            处理器列表.append(处理器函数)

    def 注销类型处理器(self, 事件类型: str, 处理器函数: 处理器类型) -> None:
        """移除指定事件类型的处理函数"""
        处理器列表: list = self._类型处理器映射[事件类型]
        if 处理器函数 in 处理器列表:
            处理器列表.remove(处理器函数)
        if not 处理器列表:  # 清理空列表
            self._类型处理器映射.pop(事件类型)

    def 注册通用处理器(self, 处理器函数: 处理器类型) -> None:
        """注册全局事件处理函数"""
        if 处理器函数 not in self._通用处理器列表:
            self._通用处理器列表.append(处理器函数)

    def 注销通用处理器(self, 处理器函数: 处理器类型) -> None:
        """移除全局事件处理函数"""
        if 处理器函数 in self._通用处理器列表:
            self._通用处理器列表.remove(处理器函数)

