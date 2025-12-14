from collections.abc import Callable
from itertools import product
from concurrent.futures import ProcessPoolExecutor
from random import random, choice
from time import perf_counter
from multiprocessing import get_context
from multiprocessing.context import BaseContext
from multiprocessing.managers import DictProxy
from _collections_abc import dict_keys, dict_values, Iterable

from deap import base, tools, algorithms       # type: ignore
from tqdm import tqdm

输出函数 = Callable[[str], None]

class 类_优化设置:
    """
    用于运行优化的设置
    """

    def __init__(self) -> None:
        """"""
        self.参数: Dict[str, List] = {}
        self.优化目标: str = ""

    def 添加参数(
        self,
        参数名: str,
        起始值: float,
        结束值: float = None,
        步长: float = None
    ) -> tuple[bool, str]:
        """"""
        if 结束值 is None and 步长 is None:
            self.参数[参数名] = [起始值]
            return True, "固定参数添加成功"

        if 起始值 >= 结束值:
            return False, "参数优化起始点必须小于终止点"

        if 步长 <= 0:
            return False, "参数优化步进必须大于0"

        当前值: float = 起始值
        值列表: List[float] = []

        while 当前值 <= 结束值 + 1e-12:
            值列表.append(round(当前值, 6))  # 保留 6 位小数
            当前值 += 步长

        self.参数[参数名] = 值列表

        return True, f"范围参数添加成功，数量{len(值列表)}"

    def 设置优化目标(self, 优化目标名称: str) -> None:
        """"""
        self.优化目标 = 优化目标名称

    def 生成参数组合(self) -> list[dict]:
        """"""
        键列表: dict_keys = self.参数.keys()
        值列表: dict_values = self.参数.values()
        组合列表: list = list(product(*值列表))

        参数组合: list = []
        for 组合 in 组合列表:
            参数设置: dict = dict(zip(键列表, 组合, strict=False))
            参数组合.append(参数设置)

        return 参数组合


def 检查优化设置(
    优化设置: 类_优化设置,
    输出函数: 输出函数 = print
) -> bool:
    """"""
    if not 优化设置.生成参数组合():
        输出函数("优化参数组合为空，请检查")
        return False

    if not 优化设置.优化目标:
        输出函数("优化目标未设置，请检查")
        return False

    return True