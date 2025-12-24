import threading
from typing import Dict, List, Any, Optional

# 使用相对导入
from ..json_handler.json_handler import JSONHandler
from src.config import CMD_CONFIG_PATH_STR, CMD_RECORD_PATH_STR, LLDB_SCRIPT_NAME

class DataHandler:
    # cmd_config json 相关字段
    cmd_script: Dict[str, str] = {}
    cmd_alias: Dict[str, str] = {}
    cus_cmd: List[str] = []
    cmd_notes: List[str] = []

    # cmd_record json 相关字段
    cmd_record_list: List[Dict[str, str]] = []

    # lldb 预处理的命令列表
    lldb_add_cmd_list: List[str] = []

    # 帮助列表
    help_list: str = ""

    # 主模块名
    main_module_name: str = ""

    # 当前使用的模块名
    module_name: str = ""

    # ASLR 偏移字典
    aslr_dict: dict[str, str] = {}

    # 单例类变量
    _instance = None

    # 实例私有属性
    _json_handler = None
    
    # 线程锁
    _lock = threading.Lock()      

    def __new__(cls, *args, **kwargs):
        # 加锁确保唯一实例
        with cls._lock:  
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.parse_json()
            self.parse_lldb_cmd()
            self._initialized = True

    # 解析 json 文件
    def parse_json(self):
        self._json_handler = JSONHandler()
        
        cmd_config = self._json_handler.parse_json_file(CMD_CONFIG_PATH_STR)
        
        # 解析 cmd_config json 相关字段
        self.cmd_script = cmd_config.get('cmd_script', {})
        self.cmd_alias = cmd_config.get('cmd_alias', {})
        self.cus_cmd = cmd_config.get('cus_cmd', [])
        self.cmd_notes = cmd_config.get('cmd_notes', [])
        
        # 解析 cmd_record json 相关字段
        self.cmd_record_list = self._json_handler.parse_json_file(CMD_RECORD_PATH_STR)
        
        # print(self.cmd_record_list)
        # print(self.cmd_script)
        # print(self.cmd_alias)
        # print(self.cus_cmd)

    def parse_lldb_cmd(self) -> Optional[list]:
        
        # 拼接 command script add -f 命令
        lldb_add_script_cmd_list = []
        for func_name, cmd_name in self.cmd_script.items():
            add_script_cmd = f"command script add -f {LLDB_SCRIPT_NAME}.{func_name} {cmd_name}"
            lldb_add_script_cmd_list.append(add_script_cmd)
            
        # 拼接 command alias 命令
        lldb_add_alias_cmd_list = []
        for cmd_name, alias_name in self.cmd_alias.items():
            add_alias_cmd = f"command alias {alias_name} {cmd_name}"
            lldb_add_alias_cmd_list.append(add_alias_cmd)
        
        # 将所有命令合并到一个列表中
        self.lldb_add_cmd_list = lldb_add_script_cmd_list + lldb_add_alias_cmd_list + self.cus_cmd
    
    def save_cmd_record(self):
        """将 cmd_record_list 保存到 JSON 文件"""
        if not self._json_handler:
            self._json_handler = JSONHandler()
        
        # 将 cmd_record_list 保存到文件
        self._json_handler.store_json(self.cmd_record_list, CMD_RECORD_PATH_STR)
    
    def save_cmd_config(self):
        """将 cmd_config 相关字段保存到 JSON 文件"""
        if not self._json_handler:
            self._json_handler = JSONHandler()
        
        # 构建 cmd_config 字典
        cmd_config = {
            "cmd_script": self.cmd_script,
            "cmd_alias": self.cmd_alias,
            "cus_cmd": self.cus_cmd,
            "cmd_notes": self.cmd_notes
        }
        
        # 将 cmd_config 保存到文件
        self._json_handler.store_json(cmd_config, CMD_CONFIG_PATH_STR)

