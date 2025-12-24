import lldb
import re
import os
import shlex
import threading

from src.handler.data_handler import DataHandler

class Utils:
    _data_handler = None
    
    @classmethod
    def swapEndian(cls, hex_str):
        """[ 将大端序的十六进制字符串转换为小端序 ]"""
        # 移除可能的前缀
        if hex_str.startswith('0x'):
            hex_str = hex_str[2:]
        
        # 确保长度为8个字符（32位）
        if len(hex_str) != 8:
            # print(f"[ 警告: 机器码长度应为8个字符，当前为{len(hex_str)} ]")
            # 如果长度不足，在前面补0
            hex_str = hex_str.zfill(8)
        
        # 分割为两个字节一组，然后反转顺序
        # 例如：1f2003d5 -> ['1f', '20', '03', 'd5'] -> ['d5', '03', '20', '1f'] -> 'd503201f'
        little_endian = ''.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)][::-1])
        
        return '0x' + little_endian
    
    @classmethod
    def ensure_hex_prefix(cls, hex_string):
        """[ 判断字符串前两位是否是0x，如果不是则添加0x前缀 ]"""
        # 检查输入是否为字符串
        if not isinstance(hex_string, str):
            return hex_string
        
        # 去除首尾空白字符
        hex_string = hex_string.strip()
        
        # 判断是否已经有0x前缀
        if hex_string.lower().startswith('0x'):
            return hex_string
        else:
            # 添加0x前缀
            return '0x' + hex_string

        
    @classmethod
    def getMainModuleName(cls):
        """[ 获取主二进制模块名 ]"""
        
        cls._data_handler = cls._data_handler if cls._data_handler is not None else DataHandler()
        
        # 初始化变量
        main_binary_name = ""

        if cls._data_handler.main_module_name == "":
            # 获取断点
            interpreter = lldb.debugger.GetCommandInterpreter()
            
            # 保存结果
            return_obj = lldb.SBCommandReturnObject()
            
            # 获取主模块的信息
            interpreter.HandleCommand('image list -o -f', return_obj)
            
            # 获取所有返回值
            output = return_obj.GetOutput()
            
            # 提取第一行
            first_line = output.splitlines()[0]
            
            # 用正则把路径提取出来（从第一个 / 开始，到 (0x 出现为止）
            # 匹配从斜杠开始，直到 (0x 结束的完整路径
            path_match = re.search(r'(\/[^(]+)\(0x', first_line)
            if path_match:
                full_path = path_match.group(1).strip()
                # 从路径中取最后一个斜杠后的文件名
                main_binary_name = full_path.split('/')[-1]
            else:
                main_binary_name = ""
            
            if main_binary_name == "":
                # print('[ Failed to get main module. ]')
                print('[ 获取主二进制模块失败 ]')
            else :
                # print('[ main module：%s. ]' % main_binary_name)
                cls._data_handler.main_module_name = main_binary_name
                print('[ 主二进制模块：%s. ]' % main_binary_name)
            
        else:
            # 如果已经获取过主模块名，直接使用
            main_binary_name = cls._data_handler.main_module_name     
            
        return main_binary_name
         
    @classmethod
    def getASLR(cls):
        """[ 获取 ASLR 偏移地址. ]"""
        
        cls._data_handler = cls._data_handler if cls._data_handler is not None else DataHandler()

        # 获取当前使用的模块名
        module_name = cls._data_handler.module_name

        # 默认使用主二进制模块
        if module_name == "":
            module_name = cls.getMainModuleName()

        # 检查模块名是否存在于 ASLR 字典中
        if module_name in cls._data_handler.aslr_dict:
            return cls._data_handler.aslr_dict.get(module_name) 
        else:
            # 模块名不存在于 ASLR 字典中，尝试获取 ASLR 偏移地址
            # 获取断点
            interpreter = lldb.debugger.GetCommandInterpreter()
            
            # 保存结果
            return_obj = lldb.SBCommandReturnObject()
            
            # 获取模块的信息
            exec_command = 'image list -o "%s"' % module_name
            interpreter.HandleCommand(exec_command, return_obj)
            
            # 获取所有返回值
            output = return_obj.GetOutput()
            
            if output is None or output == "":
                # print("[ Failed to obtain the ASLR offset address of the module, module name: %s. ]" % module_name)
                print("[ 获取模块 %s 的 ASLR 偏移地址失败. ]" % module_name)
                return None
            
            # 提取第一行
            first_line = output.splitlines()[0]
            
            # 使用正则表达式匹配地址
            match = re.search(r'0x[0-9a-fA-F]+', first_line)

            address = None

            if match:
                address = match.group(0)
                # print('[ ASLR offset address of the %s module: %s ]' % (module_name, address))
                print('[ 模块 %s 的 ASLR 偏移地址为：%s ]' % (module_name, address))
            else:
                # print("[ Failed to obtain the ASLR offset address of the module, module name: %s. ]" % module_name)
                print("[ 获取模块 %s 的 ASLR 偏移地址失败. ]" % module_name)
            
            if address is not None:  
                cls._data_handler.aslr_dict[module_name] = address
            
            return address
        
    @classmethod
    def extractAddressesFromCommand(cls, command):
        """[ 从命令字符串中提取地址列表 ]
        支持空格分隔的多个地址
        """
        if command is None or command.strip() == "":
            return []
        
        # 分割命令获取所有地址参数
        addresses = shlex.split(command)
        
        # 确保每个地址都有0x前缀
        return [cls.ensure_hex_prefix(addr) for addr in addresses]

    @classmethod
    def get_pc_value(cls,exe_ctx):
        # 获取当前线程
        thread = exe_ctx.GetThread()
        if not thread.IsValid():
            # print("[Invalid thread]")
            print("[ 无效线程. ]")
            return None
        
        # 获取当前帧（一般是最顶层的当前栈帧）
        frame = thread.GetFrameAtIndex(0)
        if not frame.IsValid():
            # print("[Invalid frame]")
            print("[ 无效帧. ]")
            return None

        # 通过寄存器名“pc”或者“rip”（x86_64）获取寄存器值
        # 注意不同架构寄存器名可能不同，如 ARM 是“pc”，x86_64 是“rip”
        
        pc_value = None
        
        # 先尝试通用名称"pc"
        reg = frame.FindRegister("pc")
        if reg.IsValid():
            pc_value = reg.GetValueAsUnsigned()
        else:
            # 备用尝试x86_64架构rip寄存器
            reg = frame.FindRegister("rip")
            if reg.IsValid():
                pc_value = reg.GetValueAsUnsigned()
        
        if pc_value is None:
            # print("[Failed to get PC register value]")
            print("[ 获取 PC 寄存器值失败. ]")
            return None
        
        return pc_value


    