import lldb
import re
import os
import shlex

from src.core.lldb_script_handler import LLDBScriptHandler
from src.handler.data_handler import DataHandler

def usingModule(debugger, command, exe_ctx, result, internal_dict):
    """[ 指定模块 —— 后续使用 mark 命令添加断点等操作都将基于该模块 ]
>> 使用方法：using <module_name>
>> 例如：using libloader"""
    LLDBScriptHandler.usingModule(debugger, command, exe_ctx, result, internal_dict)

def markBreakPointByOffsetAddress(debugger, command, exe_ctx, result, internal_dict):
    """[ 基于 module_name 模块打断点 ]
>> 使用方法：mark <offset_address>
>> 例如：mark 0x234
>> 支持多个地址: mark 0x234 0x567 0x89a"""
    LLDBScriptHandler.markBreakPointByOffsetAddress(debugger, command, exe_ctx, result, internal_dict)

def markBreakPointByDynamicAddress(debugger, command, exe_ctx, result, internal_dict):
    """[ 在动态地址上打断点 ]
>> 使用方法：markd <dynamic_address>
>> 例如：markd 0x1063c2c10"""
    LLDBScriptHandler.markBreakPointByDynamicAddress(debugger, command, exe_ctx, result, internal_dict)
    
def calcDynamicMemoryAddress(debugger, command, exe_ctx, result, internal_dict):
    """[ 基于 module_name 模块，计算动态内存地址 ]
>> 使用方法：dy <offset_address>
>> 例如：dy 0x4567"""    
    LLDBScriptHandler.calcDynamicMemoryAddress(debugger, command, exe_ctx, result, internal_dict)
    
def calcStaticOffsetAddress(debugger, command, exe_ctx, result, internal_dict):
    """[ 基于 module_name 模块，计算静态偏移地址 ]
>> 使用方法：offset <address>
>> 例如：offset 0x1063c2c10
>> 如果直接输入 offset，则会计算当前 pc 寄存器的偏移（该命令基于 using 命令指定的模块计算偏移地址）"""
    LLDBScriptHandler.calcStaticOffsetAddress(debugger, command, exe_ctx, result, internal_dict)

def writeMemory(debugger, command, exe_ctx, result, internal_dict):
    """[ 对指定地址进行内存修改，默认会执行端序转换，所以只需要输入大端序机器码 ]
>> 使用方法：memwrite <address> <big_endian_code>
>> 例如：memwrite 0x1063c2c10 1f2003d5
>> 注意：地址和机器码不一定要以 0x 开头"""    
    LLDBScriptHandler.writeMemory(debugger, command, exe_ctx, result, internal_dict)

def readMemory(debugger, command, exe_ctx, result, internal_dict):
    """[ 内存读取 ]
使用方法：
1. memread <addr1> <addr2> ... - 读取多个地址的内存内容
2. memread -ptr <addr_expr1> -ptr <addr_expr2> ... - 先从指定地址获取指针，再读取该指针指向的内存
3. memread [options] <addr> - 支持选项：-c/--count 指定读取字节数
举例：
- memread $x8 0x12345678
- memread -ptr ($x8 + 0x20)
- memread -c 0x100 $x8
- memread --count 0x200 0x12345678
"""
    LLDBScriptHandler.readMemory(debugger, command, exe_ctx, result, internal_dict)

def nopMemory(debugger, command, exe_ctx, result, internal_dict):
    """[ 将指定地址或地址范围的内存修改为NOP指令（ARM64 NOP指令（小端序）: D503201F）
支持以下格式:
1. 单个地址: nop 0x1063c2c10
2. 多个地址: nop 0x1063c2c10 1063c2c18 0x1063c2c20
3. 地址范围: nop [0x1063c2c10, 0x1063c2c20]
>> 注意：nop 地址范围时，地址一定要以 0x 开头，nop 单个地址和多个地址时，地址不一定要以 0x 开头"""
    
    LLDBScriptHandler.nopMemory(debugger, command, exe_ctx, result, internal_dict)

def getPointer(debugger, command, exe_ctx, result, internal_dict):
    """[ 获取地址中的指针地址 ]
使用方法：ptr <reg_name> 或者 ptr <addr>
举例：ptr ($x8 + 0x8) ($x8 + 0x20) 或者 ptr 0x12345678"""    
    LLDBScriptHandler.getPointer(debugger, command, exe_ctx, result, internal_dict)

def saveCmd(debugger, command, exe_ctx, result, internal_dict): 
    """[保存命令到 cmd_record.json 文件]
支持以下用法：
1. save - 保存最近一条命令，描述为空
2. save "描述" - 保存最近一条命令，并添加描述
3. save <序号> "描述" <序号> "描述" ... - 保存指定序号的历史命令，并添加描述
例如：
    save - 保存最近一条命令
    save "这是最近一条命令" - 保存最近一条命令并添加描述
    save 0 "这是序号0的命令" 2 "这是序号2的命令" - 保存序号0和2的命令并添加描述
    save 0 2 "这是命令" - 保存序号0和2的命令，只有序号2的命令有描述
"""
    LLDBScriptHandler.saveCmd(debugger, command, exe_ctx, result, internal_dict)

def showCmd(debugger, command, exe_ctx, result, internal_dict):
    """[显示保存在 cmd_record.json 中的所有命令]
>> 使用方法：showCmd
>> 功能：从缓存中读取保存的命令，并以序号形式输出所有命令及其描述
"""
    LLDBScriptHandler.showCmd(debugger, command, exe_ctx, result, internal_dict)

def removeCmd(debugger, command, exe_ctx, result, internal_dict):
    """[根据序号删除 cmd_record.json 中的指定命令]
>> 使用方法：rm <index1> <index2> ...
>> 功能：根据 showCmd 命令显示的序号删除对应的命令记录
>> 例如：rm 1 3 - 删除序号为1和3的命令
"""
    LLDBScriptHandler.removeCmd(debugger, command, exe_ctx, result, internal_dict)

def execCmd(debugger, command, exe_ctx, result, internal_dict):
    """[根据序号执行 cmd_record.json 中的命令]
>> 使用方法：exec <index>
>> 功能：根据 showCmd 命令显示的序号执行对应的命令（每次只执行一条）
>> 例如：exec 1 - 执行序号为1的命令
"""
    LLDBScriptHandler.execCmd(debugger, command, exe_ctx, result, internal_dict)


def parseSwiftString(debugger, command, exe_ctx, result, internal_dict):
    """[解析 Swift String 字符串]
>> 使用方法：ss <register>
>> 例如：ss $x0
>> 功能：解析 Swift 字符串，支持小字符串和大字符串格式"""
    LLDBScriptHandler.parseSwiftString(debugger, command, exe_ctx, result, internal_dict)


def parseSwiftData(debugger, command, exe_ctx, result, internal_dict):
    """[解析 Swift 数据类型]
>> 使用方法：sd <register>
>> 例如：sd $x0
>> 功能：解析 Swift 数据类型，支持 Int、UInt、Float、Double 等"""
    LLDBScriptHandler.parseSwiftData(debugger, command, exe_ctx, result, internal_dict)



def help(debugger, command, exe_ctx, result, internal_dict):
    """[ ιldb 脚本的帮助文档 ]"""
    data_handler = DataHandler()
    print(data_handler.help_list)

def __lldb_init_module(debugger, internal_dict):
    data_handler = DataHandler()
    
    ret_content = '\n[ notes ]\n'
    for note in data_handler.cmd_notes:
        ret_content += note + '\n'
    ret_content += "\n[ 已导入 ιldb.py 脚本，并成功注册命令. ]\n"
    
    # 遍历命令列表
    for exec_command in data_handler.lldb_add_cmd_list:
        debugger.HandleCommand(exec_command)
        ret_content += '>> %s\n' % exec_command
        
    data_handler.help_list = ret_content
    print(ret_content)