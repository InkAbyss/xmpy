from abc import ABC
from types import ModuleType
from typing import Optional, List, Callable
from importlib import import_module

from .模块_对象 import 类_历史数据请求, 类_行情数据, 类_K线数据
from .模块_设置 import 全局设置
from .包_国际化 import _


class 类_基础数据服务(ABC):
    """数据服务基类，用于对接不同数据源"""

    def 初始化(self, 输出函数: Callable = print) -> bool:
        """初始化数据服务连接"""
        pass

    def 查询K线历史(self, 请求: 类_历史数据请求, 输出函数: Callable = print) -> Optional[List[类_K线数据]]:
        """查询历史K线数据"""
        输出函数(_("查询K线数据失败：没有正确配置数据服务"))

    def 查询Tick历史(self, 请求: 类_历史数据请求, 输出函数: Callable = print) -> Optional[List[类_行情数据]]:
        """查询历史Tick数据"""
        输出函数(_("查询Tick数据失败：没有正确配置数据服务"))


# 全局数据服务实例
数据服务实例: 类_基础数据服务 = None


def 获取数据服务() -> 类_基础数据服务:
    """获取数据服务单例"""
    global 数据服务实例

    # 如果已经初始化则直接返回
    if 数据服务实例:
        return 数据服务实例

    # 从全局配置读取数据服务名称
    数据服务名称: str = 全局设置["数据服务.名称"]

    if not 数据服务名称:
        # 未配置时使用基础类
        数据服务实例 = 类_基础数据服务()
        print(_("没有配置要使用的数据服务，请修改全局配置中的datafeed相关内容"))
    else:
        # 构建模块名称
        模块名称: str = f"xmpy_{数据服务名称}"

        try:
            # 尝试导入数据服务模块
            模块: ModuleType = import_module(模块名称)

            # 从模块创建数据服务实例
            数据服务实例 = 模块.Datafeed()
        except ModuleNotFoundError:
            # 导入失败时回退到基础类
            数据服务实例 = 类_基础数据服务()
            print(_("无法加载数据服务模块，请运行 pip install {} 尝试安装").format(模块名称))

    return 数据服务实例