import sys
from datetime import datetime
from pathlib import Path
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL

from loguru import logger

from xmpy.包_交易核心.模块_设置 import 全局设置
from xmpy.包_交易核心.模块_工具 import 获取目录路径


__all__ = [
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
    "logger",
]


# 日志格式
格式: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
    "| <level>{level}</level> "
    "| <cyan>{extra[网关名称]}</cyan> "
    "| <level>{message}</level>"
)


# 添加默认网关
logger.configure(extra={"网关名称": "默认日志"})


# 日志级别
级别: int = 全局设置["日志.级别"]


# 移除默认标准错误输出
logger.remove()


# 添加控制台输出
if 全局设置["日志.控制台"]:
    logger.add(sink=sys.stdout, level=级别, format=格式)


# 添加文件输出
if 全局设置["日志.文件"]:
    当天日期: str = datetime.now().strftime("%Y%m%d")
    日志目录: Path = 获取目录路径("log")
    文件名: str = f"vt_{当天日期}.log"
    文件路径: Path = 日志目录.joinpath(文件名)

    logger.add(sink=文件路径, level=级别, format=格式)