# 运行单个策略
# 运行所有策略的示例代码在本项目github下：运行示例 文件夹

import multiprocessing
import sys
from time import sleep
from datetime import datetime, time
from logging import INFO

from xmpy.包_事件引擎 import 类_事件引擎
from xmpy.包_交易核心.模块_设置 import 全局设置
from xmpy.包_交易核心.模块_主引擎 import 类_主引擎
from xmpy_ctp import 类_CTP网关

from xmpy_ctastrategy import 类_CTA策略应用
from xmpy_ctastrategy.模块_基础 import 事件类型_CTA日志


全局设置["日志.启用"] = True
全局设置["日志.级别"] = INFO
全局设置["日志.控制台"] = True

ctp_设置 = {
    "用户名": "",
    "密码": "",
    "经纪商代码": "",
    "交易服务器": "",
    "行情服务器": "",
    "产品名称": "",
    "授权编码": "",
    "产品信息": ""
}

# 中国期货市场交易时段（日盘/夜盘）
日盘开始时间 = time(8, 45)
日盘结束时间 = time(15, 0)

夜盘开始时间 = time(20, 45)
夜盘结束时间 = time(2, 45)


def 检查交易时段():
    """检查是否在交易时段内"""
    当前时间 = datetime.now().time()

    是否交易时段 = False
    if (
            (当前时间 >= 日盘开始时间 and 当前时间 <= 日盘结束时间)
            or (当前时间 >= 夜盘开始时间)
            or (当前时间 <= 夜盘结束时间)
    ):
        是否交易时段 = True

    return 是否交易时段


def 运行子进程():
    """在子进程中运行的业务逻辑"""
    全局设置["日志.文件"] = True

    # 创建事件引擎
    事件引擎 = 类_事件引擎()

    # 创建主引擎
    主引擎 = 类_主引擎(事件引擎)
    主引擎.添加网关(类_CTP网关)

    # 添加CTA应用
    CTA引擎 = 主引擎.添加应用(类_CTA策略应用)
    主引擎.记录日志("主引擎创建成功")

    # 注册日志事件监听
    日志引擎 = 主引擎.获取引擎("日志")
    事件引擎.注册类型处理器(事件类型_CTA日志, 日志引擎.处理日志事件)
    主引擎.记录日志("注册日志事件监听")

    # 连接CTP接口
    主引擎.连接网关(ctp_设置, "CTP")
    主引擎.记录日志("连接CTP接口")

    # 等待10秒确保连接成功
    sleep(10)

    # 初始化CTA引擎
    CTA引擎.初始化引擎()
    主引擎.记录日志("CTA策略引擎初始化完成")

    # 初始化所有策略
    CTA引擎.初始化所有策略()
    sleep(10)  # 预留足够时间完成策略初始化
    主引擎.记录日志("CTA策略全部初始化")

    # 启动所有策略
    CTA引擎.启动所有策略()
    主引擎.记录日志("CTA策略全部启动")

    # 持续运行检查
    while True:
        sleep(10)

        # 检查交易时段
        是否交易时段 = 检查交易时段()
        if not 是否交易时段:
            print("关闭子进程")
            主引擎.关闭()
            sys.exit(0)


def 运行父进程():
    """在父进程中运行的守护逻辑"""
    print("启动CTA策略守护父进程")

    子进程 = None

    while True:
        # 持续检查交易时段
        是否交易时段 = 检查交易时段()

        # 交易时段启动子进程
        if 是否交易时段 and 子进程 is None:
            print("启动子进程")
            子进程 = multiprocessing.Process(target=运行子进程)
            子进程.start()
            print("子进程启动成功")

        # 非交易时段关闭子进程
        if not 是否交易时段 and 子进程 is not None:
            if not 子进程.is_alive():
                子进程 = None
                print("子进程关闭成功")

        sleep(5)


if __name__ == "__main__":
    运行父进程()