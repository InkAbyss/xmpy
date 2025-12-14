import multiprocessing
import sys
from time import sleep
from datetime import datetime, time
from logging import INFO

from xmpy.包_事件引擎 import 类_事件引擎
from xmpy.包_交易核心.模块_设置 import 全局设置
from xmpy.包_交易核心.模块_主引擎 import 类_主引擎
from xmpy_ctp import 类_CTP网关

from xmpy_datarecorder import 类_数据记录应用


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
日盘开始时间 = time(8, 50)
日盘结束时间 = time(15, 2)

夜盘开始时间 = time(20, 50)
夜盘结束时间 = time(2, 32)


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
    # 创建事件引擎
    事件引擎 = 类_事件引擎()

    # 创建主引擎
    主引擎 = 类_主引擎(事件引擎)
    网关 = 主引擎.添加网关(类_CTP网关)
    # 连接CTP接口
    主引擎.连接网关(ctp_设置, "CTP")
    主引擎.记录日志("连接CTP接口")

    # 等待10秒确保连接成功
    sleep(5)

    while not 网关.交易接口.合约就绪:
        sleep(1)

    # 添加应用
    记录引擎 = 主引擎.添加应用(类_数据记录应用)
    主引擎.记录日志("记录引擎创建成功")

    # ---------------- 可选项 ----------------
    # 记录引擎.启动主力合约采集()     # 只采集主力合约，注意：不会采集 自选合约配置.json 里的合约
    # 记录引擎.清理过期自选合约()     # 清除 自选合约配置.json 文件里的过期合约
    # 记录引擎.启动自选合约采集()     # 启动已写入 自选合约配置.json 文件的合约采集，通过 添加自选Tick合约，添加自选K线合约 写入
    # ---------------- 可选项 ----------------


    记录引擎.添加自选Tick合约("rb2601.SHFE")
    记录引擎.添加自选K线合约("rb2601.SHFE")

    记录引擎.添加自选Tick合约("TA601.CZCE")
    记录引擎.添加自选K线合约("TA601.CZCE")

    记录引擎.添加自选Tick合约("m2601.DCE")
    记录引擎.添加自选K线合约("m2601.DCE")

    主引擎.记录日志("记录引擎开始记录数据")

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
            if 子进程.is_alive():
                print("检测到正在运行的子进程，强制终止")
                子进程.terminate()  # 发送SIGTERM信号
                子进程.join(timeout=5)  # 等待5秒正常退出

                if 子进程.is_alive():  # 如果仍未退出
                    print("子进程拒绝退出，强制杀死")
                    子进程.kill()  # 发送SIGKILL信号
                    子进程.join()
                    print("执行强制杀死完毕")

            if not 子进程.is_alive():
                子进程 = None
                print("子进程关闭成功")


        sleep(5)


if __name__ == "__main__":
    运行父进程()