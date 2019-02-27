import os
import time
import logging


###
# 1. 创建logger实例，如果参数为空则返回 root logger
###

logger = logging.getLogger('spider')
# 设置总日志级别, 也可以给不同的handler设置不同的日志级别
logger.setLevel(logging.DEBUG)

###
# 2. 创建Handler, 输出日志到控制台和文件
###

# 控制台日志和日志文件使用同一个Formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')

# 日志文件FileHandler
basedir = os.path.abspath(os.path.dirname(__file__))
log_dest = os.path.join(basedir, 'logs')  # 日志文件所在目录
if not os.path.isdir(log_dest):
    os.mkdir(log_dest)
filename = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(time.time())) + '.log'  # 日志文件名，以当前时间命名
file_handler = logging.FileHandler(os.path.join(log_dest, filename), encoding='utf-8')  # 创建日志文件handler
file_handler.setFormatter(formatter)  # 设置Formatter
# file_handler.setLevel(logging.INFO)  # 单独设置日志文件的日志级别，注释掉则使用总日志级别

# 控制台日志StreamHandler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.CRITICAL)  # 保持控制台清爽，只输出总信息和进度条

###
# 3. 将handler添加到logger中
###

logger.addHandler(file_handler)
logger.addHandler(stream_handler)
