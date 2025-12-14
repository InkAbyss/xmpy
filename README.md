# xmpy量化框架

xmpy—— 专为中文母语开发者打造的量化交易研发框架。

## 📖 项目背景

初衷：最初是为了编写一个交易策略，在对比多个框架后选择了[vnpy](https://github.com/vnpy/vnpy)。其文档详尽，但入门仍需较长时间阅读文档和源码。考虑到我无需图形化界面，并希望以中文提升后续策略开发与维护的友好性，决定基于examples/no_ui/run.py进行全面中文重构。

为满足中文开发者对代码可读性与可维护性的需求，本项目以[vnpy-3.9.4](https://github.com/vnpy/vnpy/tree/3.9.4)为基础，进行了全面优化与重构。

## 接口
* [CTP（ctp）](https://github.com/InkAbyss/xmpy_ctp)：国内期货、期权

* TTS_CTP：openctp，提供国内期货（仿真），7*24小时数据（暂未上传）

## 应用
* [xmpy_ctastrategy](https://github.com/InkAbyss/xmpy_ctastrategy)：CTA策略引擎模块

* [xmpy_datarecorder](https://github.com/InkAbyss/xmpy_datarecorder)：行情记录模块
* [模块_回测引擎](https://github.com/InkAbyss/xmpy_ctastrategy/blob/main/xmpy_ctastrategy/模块_回测引擎.py)：回测模块

## 数据库接口
* [xmpy_sqlite](https://github.com/InkAbyss/xmpy_sqlite)：轻量级单文件数据库，无需安装和配置数据服务程序

## 安装
```
1，需要先安装ta-lib
pip install TA-Lib

安装失败，可下载ta-lib安装包文件夹中的whl文件
pip install .\ta_lib-0.6.0-cp312-cp312-win_amd64.whl

2，安装xmpy
pip install xmpy
```
## 使用
1，在[SimNow](https://www.simnow.com.cn)注册CTP仿真账号，并在该页面获取经纪商代码以及交易行情服务器地址。

2，在任意目录下创建run.py，写入以下示例代码：
```
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

# 策略配置列表（可扩展添加多个策略）
策略配置列表 = [
    {
        "策略类名": "策略_1_基础教程",
        "策略名称": "示例策略",
        "合约标识": "c2509.大商所",
        "参数设置": {
            "初始手数": 1
        }
    }
]

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
    网关 = 主引擎.添加网关(类_CTP网关)

    # 添加CTA应用
    CTA引擎 = 主引擎.添加应用(类_CTA策略应用)
    主引擎.记录日志("主引擎创建成功")

    # 连接CTP接口
    主引擎.连接网关(ctp_设置, "CTP")
    主引擎.记录日志("连接CTP接口")
    
    while not 网关.交易接口.合约就绪:
        sleep(1)

    # 初始化CTA引擎
    CTA引擎.初始化引擎()
    主引擎.记录日志("CTA策略引擎初始化完成")

    # 循环处理所有策略配置
    for 策略配置 in 策略配置列表:
        策略名称 = 策略配置["策略名称"]

        if 策略名称 not in CTA引擎.运行策略字典:
            主引擎.记录日志(f"创建策略：{策略名称}")
            CTA引擎.添加策略(
                类名=策略配置["策略类名"],
                策略名称=策略名称,
                合约标识=策略配置["合约标识"],
                配置字典=策略配置["参数设置"]
            )
            # 初始化策略
            CTA引擎.初始化策略(策略名称)
            sleep(5)
            CTA引擎.启动策略(策略名称)
        else:
            主引擎.记录日志(f"更新策略参数：{策略名称}")
            CTA引擎.更新策略配置(策略名称=策略名称,配置字典=策略配置["参数设置"])
            # 初始化策略
            CTA引擎.初始化策略(策略名称)
            sleep(5)
            CTA引擎.启动策略(策略名称)

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
```

### 开发进度看板

| 模块        | 进度   | 预计完成时间 |
|:----------| :----- | :----------- |
| 事件引擎      | ✅ 100% | 已发布       |
| 主引擎       | ✅ 100% | 已发布       |
| CTA自动交易模块 | ✅ 100% | 已发布       |
| CTP接口     | ✅ 100% | 已发布       |
| 回测引擎      | ✅ 100% | 已发布       |
| 数据记录      | ✅ 100% | 已发布       |

## 🤝 贡献指南

欢迎提交中文命名的：

- 📝 文档翻译
- 🐛 Bug修复
- 🎯 功能增强
