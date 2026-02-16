import signal

# 设置 SIGINT 信号处理为默认，以实现 Ctrl+C 中断 recv
signal.signal(signal.SIGINT, signal.SIG_DFL)

# 心跳相关常量
心跳主题 = "heartbeat"
心跳间隔 = 10        # 心跳发送间隔（秒）
心跳容忍度 = 30      # 心跳丢失容忍时间（秒）