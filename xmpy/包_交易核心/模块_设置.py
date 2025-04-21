"""交易平台全局配置"""

from logging import CRITICAL
from typing import Dict, Any
from tzlocal import get_localzone_name

from .模块_工具 import 加载json文件


# 全局配置字典
全局设置: Dict[str, Any] = {
    "字体.族": "微软雅黑",
    "字体.大小": 12,

    "日志.启用": True,
    "日志.级别": CRITICAL,
    "日志.控制台": True,
    "日志.文件": True,

    "邮件.服务器": "smtp.qq.com",
    "邮件.端口": 465,
    "邮件.用户名": "",
    "邮件.密码": "",
    "邮件.发件人": "",
    "邮件.收件人": "",

    "数据服务.名称": "",
    "数据服务.用户名": "",
    "数据服务.密码": "",

    "数据库.时区": get_localzone_name(),
    "数据库.类型": "sqlite",
    "数据库.文件名": "database.db",
    "数据库.主机": "",
    "数据库.端口": 0,
    "数据库.用户": "",
    "数据库.密码": ""
}


# 从JSON文件加载配置
设置文件名: str = "vt_setting.json"
全局设置.update(加载json文件(设置文件名))


def 获取配置项(前缀: str = "") -> Dict[str, Any]:
    """根据前缀筛选配置项"""
    前缀长度: int = len(前缀)
    筛选配置 = {
        键[前缀长度:]: 值
        for 键, 值 in 全局设置.items()
        if 键.startswith(前缀)
    }
    return 筛选配置