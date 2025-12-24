import os
from pathlib import Path

# src 根目录
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CMD_CONFIG_PATH =  BASE_DIR/ "../config/cmd_config.json"
CMD_RECORD_PATH = BASE_DIR/ "../config/cmd_record.json"

# 转换为字符串路径
CMD_CONFIG_PATH_STR = str(CMD_CONFIG_PATH)
CMD_RECORD_PATH_STR = str(CMD_RECORD_PATH)

# lldb 脚本名
LLDB_SCRIPT_NAME = "ιldb"

