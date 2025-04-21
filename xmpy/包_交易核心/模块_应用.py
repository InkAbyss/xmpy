from abc import ABC
from pathlib import Path
from typing import Type, TYPE_CHECKING


if TYPE_CHECKING:
    from .模块_主引擎 import 基础引擎


class 类_基础应用(ABC):
    """应用基类"""

    应用名称: str = ""                          # 唯一应用标识（用于创建引擎和组件）
    应用模块: str = ""                         # 导入模块使用的字符串路径
    应用路径: Path = ""                        # 应用目录绝对路径
    显示名称: str = ""                         # 在菜单中显示的名称
    引擎类: Type["基础引擎"] = None            # 关联的引擎类
    组件名称: str = ""                        # 应用界面组件类名
    图标名称: str = ""                        # 应用图标文件名