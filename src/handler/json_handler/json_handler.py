import threading
import json
import os
from typing import Union, Dict, List, Any, Optional

"""
    类功能：JSON 处理
    
"""
class JSONHandler:
    _instance = None        # 单例对象
    _lock = threading.Lock()  # 线程锁

    def __new__(cls, *args, **kwargs):
        with cls._lock:  # 加锁确保唯一实例
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # 初始化通用配置
            self._encoding = "utf-8"  # 统一编码格式
            self._indent = 4  # JSON 格式化缩进
            self._ensure_ascii = False  # 支持中文（不转义）
            self._initialized = True

    
    def parse_json_file(self, json_file_path: str) -> Union[Dict[str, Any], List[Any]]:
        """
        从 JSON 文件中加载 JSON 对象（线程安全，增强异常处理）
        :param json_file_path: JSON 文件路径
        :return: 解析后的 JSON 对象（dict/list）
        :raise: FileNotFoundError/ PermissionError/ json.JSONDecodeError/ IOError
        """

        # 前置校验：路径为空/非字符串
        if not isinstance(json_file_path, str) or len(json_file_path.strip()) == 0:
            raise ValueError("JSON 文件路径不能为空且必须为字符串")

        # 校验文件是否存在
        if not os.path.exists(json_file_path):
            raise FileNotFoundError(f"JSON 文件不存在：{json_file_path}")

        # 校验是否是文件（而非目录）
        if not os.path.isfile(json_file_path):
            raise IsADirectoryError(f"路径不是有效文件：{json_file_path}")

        try:
            with open(json_file_path, 'r', encoding=self._encoding) as f:
                # 读取前先校验文件是否为空（避免 json.load 解析空文件报错）
                file_content = f.read().strip()
                if not file_content:
                    raise json.JSONDecodeError("空文件无法解析", "", 0)
                data = json.loads(file_content)  # 先读字符串再解析，便于空文件校验
            return data
        except PermissionError as e:
            raise PermissionError(f"无权限读取文件：{json_file_path}，错误：{e}") from e
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON 文件格式错误：{json_file_path}，错误：{e}", e.doc, e.pos) from e
        except IOError as e:
            raise IOError(f"读取文件失败：{json_file_path}，错误：{e}") from e

        
    def parse_json(self, json_str: str) -> Union[Dict[str, Any], List[Any]]:
        """
        解析 JSON 字符串（增强空值/格式校验）
        :param json_str: JSON 字符串
        :return: 解析后的 JSON 对象（dict/list）
        :raise: ValueError/ json.JSONDecodeError
        """
        # 前置校验：非字符串/空字符串
        if not isinstance(json_str, str):
            raise TypeError(f"JSON 字符串必须为 str 类型，输入类型：{type(json_str)}")
        json_str_stripped = json_str.strip()
        if not json_str_stripped:
            raise ValueError("JSON 字符串不能为空")

        try:
            data = json.loads(json_str_stripped)
            # 确保解析结果是 JSON 核心类型（避免解析出单个字符串/数字）
            if not isinstance(data, (dict, list)):
                raise ValueError(f"JSON 字符串解析结果非字典/列表，而是：{type(data)}")
            return data
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON 字符串格式错误：{e}", e.doc, e.pos) from e
        
    
    def store_json(self, json_data: Union[str, dict, list], json_file_path: str) -> None:
        """
        将 JSON 数据存储到文件中（兼容字符串/字典/列表输入，增强健壮性）
        :param json_data: JSON 数据（支持字符串/字典/列表）
        :param json_file_path: JSON 文件路径
        :return: None
        :raise: ValueError/ IOError/ PermissionError/ IsADirectoryError
        """
        # 前置校验：文件路径为空
        if not isinstance(json_file_path, str) or len(json_file_path.strip()) == 0:
            raise ValueError("JSON 文件路径不能为空且必须为字符串")

        # 统一处理输入，转换为可序列化的字典/列表
        parsed_data: Union[dict, list]
        if isinstance(json_data, (dict, list)):
            parsed_data = json_data
        elif isinstance(json_data, str):
            # 复用 parse_json 函数，减少重复逻辑
            parsed_data = self.parse_json(json_data)
        else:
            raise TypeError(f"仅支持 str/dict/list 类型，输入类型：{type(json_data)}")

        # 确保目标目录存在（多级目录自动创建）
        dir_path = os.path.dirname(json_file_path)
        if dir_path and not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
            except PermissionError as e:
                raise PermissionError(f"无权限创建目录：{dir_path}，错误：{e}") from e

        # 写入文件（增强异常捕获）
        try:
            with open(json_file_path, 'w', encoding=self._encoding) as f:
                json.dump(
                    parsed_data,
                    f,
                    ensure_ascii=self._ensure_ascii,
                    indent=self._indent,
                    sort_keys=False  # 保留原数据顺序
                )
            # print(f"JSON 数据已写入：{json_file_path}")
        except PermissionError as e:
            raise PermissionError(f"无权限写入文件：{json_file_path}，错误：{e}") from e
        except IsADirectoryError as e:
            raise IsADirectoryError(f"路径是目录，无法写入文件：{json_file_path}，错误：{e}") from e
        except IOError as e:
            raise IOError(f"写入文件失败：{json_file_path}，错误：{e}") from e

