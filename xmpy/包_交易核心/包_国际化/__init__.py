import gettext
from pathlib import Path

# 本地化文件存放路径
本地化目录: Path = Path(__file__).parent

# 创建GNUTranslations翻译对象
翻译对象: gettext.GNUTranslations = gettext.translation("xmpy", localedir=本地化目录, fallback=True)

# 创建便捷翻译函数
_ = 翻译对象.gettext