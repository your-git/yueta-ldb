import lldb
import re
import os
import shlex
from src.utils import Utils
from src.handler.data_handler import DataHandler

class LLDBScriptHandler:
    _data_handler = None
    
    @classmethod
    def usingModule(cls, debugger, command, exe_ctx, result, internal_dict):
        """[ 指定模块 —— 后续使用 mark 命令添加断点等操作都将基于该模块 ]
    >> 使用方法：using <module_name>
    >> 例如：using libloader"""

        cls._data_handler = cls._data_handler if cls._data_handler is not None else DataHandler()
        
        # 暂存模块名
        old_module_name = cls._data_handler.module_name
        
        # 如果没有指定模块，则使用主二进制模块
        if command is None or command == "":
            cls._data_handler.module_name = Utils.getMainModuleName()
        else:
            cls._data_handler.module_name = command.strip()
        
        aslr = Utils.getASLR()
        
        if aslr:
            # result.PutCString('[ Using %s successfully. ]' % module_name)
            result.PutCString('[ 成功切换到 %s 模块. ]' % cls._data_handler.module_name)
            
        else:
            cls._data_handler.module_name = old_module_name
    
    @classmethod
    def markBreakPointByOffsetAddress(cls, debugger, command, exe_ctx, result, internal_dict):
        """[ 基于 module_name 模块打断点 ]
    >> 使用方法：mark <offset_address>
    >> 例如：mark 0x234
    >> 支持多个地址: mark 0x234 0x567 0x89a"""

        # 提取地址列表
        offsets = Utils.extractAddressesFromCommand(command)
        
        if not offsets:
            # result.PutCString('[ Please input at least one offset address. ]')
            print('[ 请输入至少一个偏移地址. ]')
            return
        
        # 获取 aslr
        aslr = Utils.getASLR()

        if not aslr:
            # 获取不到 ASLR ，所以标记断点失败
            # result.PutCString('[ Unable to retrieve ASLR, breakpoint marking failed. ]')
            print('[ 无法获取 ASLR 偏移地址，断点标记失败. ]')
            return
        
        # 循环处理每个地址
        success_count = 0
        for offset in offsets:
            # 设置断点
            exec_command = 'breakpoint set --address "%s+%s"' % (aslr, offset)
            debugger.HandleCommand(exec_command)
            success_count += 1
        
        # result.PutCString('[ Successfully set breakpoints at %d offset addresses. ]' % success_count)
        print('[ 成功设置 %d 个偏移地址的断点. ]' % success_count)

    @classmethod
    def markBreakPointByDynamicAddress(cls, debugger, command, exe_ctx, result, internal_dict):
        """[ 在动态地址上打断点 ]
    >> 使用方法：markd <dynamic_address>
    >> 例如：markd 0x1063c2c10"""

        # 提取地址列表
        addresses = Utils.extractAddressesFromCommand(command)
        
        if not addresses:
            # result.PutCString('[ Please input at least one dynamic address. ]')
            print('[ 请输入至少一个动态地址. ]')
            return

        # 循环处理每个地址
        success_count = 0
        for address in addresses:
            exec_command = 'breakpoint set --address %s' % (address)
            debugger.HandleCommand(exec_command)
            success_count += 1
        
        # result.PutCString('[ Successfully set breakpoints at %d dynamic addresses. ]' % success_count)
        print('[ 成功设置 %d 个动态地址的断点. ]' % success_count)

    @classmethod
    def calcDynamicMemoryAddress(cls, debugger, command, exe_ctx, result, internal_dict):
        """[ 基于 module_name 模块，计算动态内存地址 ]
    >> 使用方法：dy <offset_address>
    >> 例如：dy 0x4567"""
        
        # 获取 ASLR
        aslr = Utils.getASLR()

        if aslr:
            # 如果没有指定，则计算 pc 寄存器的偏移
            if command is None or command == "":
                print("[ 请输入偏移地址. 例如：dy 0x4567 ]")
                return
                
            else:
                # 内存地址列表
                address_list = shlex.split(command)
                dy_addr = [hex(int(addr, 16) + int(aslr,16)) for addr in address_list]
                print(dy_addr)
        

    @classmethod   
    def calcStaticOffsetAddress(cls, debugger, command, exe_ctx, result, internal_dict):
        """[ 基于 module_name 模块，计算静态偏移地址 ]
    >> 使用方法：offset <address>
    >> 例如：offset 0x1063c2c10
    >> 如果直接输入 offset，则会计算当前 pc 寄存器的偏移（该命令基于 using 命令指定的模块计算偏移地址）"""
        
        # 获取 ASLR
        aslr = Utils.getASLR()
        
        if aslr:
            # 如果没有指定，则计算 pc 寄存器的偏移
            if command is None or command == "":
                pc_address = Utils.get_pc_value(exe_ctx)
                print(hex(pc_address - int(aslr, 16)))
                
            else:
                # 内存地址列表
                address_list = shlex.split(command)
                offsets = [hex(int(addr, 16) - int(aslr,16)) for addr in address_list]
                print(offsets)
    
    @classmethod  
    def writeMemory(cls, debugger, command, exe_ctx, result, internal_dict):
        """[ 对指定地址进行内存修改，默认会执行端序转换，所以只需要输入大端序机器码 ]
    >> 使用方法：memwrite <address> <big_endian_code>
    >> 例如：memwrite 0x1063c2c10 1f2003d5
    >> 注意：地址和机器码不一定要以 0x 开头"""
        # 解析命令参数
        args = shlex.split(command)
        if len(args) < 2:
            result.PutCString('[ 请提供地址和要修改的大端序机器码（"0x" 可以要可以不要，默认是十六进制），例如: memwrite 0x1063c2c10 1f2003d5 ]')
            return
        
        # 获取地址和机器码
        address = args[0]
        big_endian_code = args[1]
        
        # 确保地址以0x开头
        address = Utils.ensure_hex_prefix(address)
        
        # 转换为小端序
        little_endian_code = Utils.swapEndian(big_endian_code)
        
        # 执行内存写入命令
        # 使用4字节宽度（-s 4）
        exec_command = f'memory write -s 4 {address} {little_endian_code}'
        print(f"[ 执行命令: {exec_command} ]")
        print(f"[ 大端序: {big_endian_code} -> 小端序: {little_endian_code} ]")
        
        # 执行命令
        debugger.HandleCommand(exec_command)
        
        # 验证写入是否成功
        verify_command = f'memory read -s 4 -f x {address}'
        return_obj = lldb.SBCommandReturnObject()
        debugger.GetCommandInterpreter().HandleCommand(verify_command, return_obj)
        
        if return_obj.Succeeded():
            print(f"[ 验证结果: {return_obj.GetOutput().strip()} ]")
        else:
            print(f"[ 验证失败: {return_obj.GetError()} ]")

    @classmethod  
    def readMemory(cls, debugger, command, exe_ctx, result, internal_dict):
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
        # 检查是否提供了参数
        if not command or not command.strip():
            print("[ 请提供要读取的内存地址，例如: memread $x8 或 memread -ptr ($x8 + 0x20) ]")
            return
        
        try:
            # 分割命令参数
            args = shlex.split(command)
            
            # 获取命令解释器
            interpreter = debugger.GetCommandInterpreter()
            
            # 解析参数，识别 -ptr、-c、--count 选项和普通地址
            ptr_expressions = []  # 存储需要先获取指针的地址表达式
            direct_addresses = []  # 存储直接读取的地址
            count_value = None  # 存储读取字节数
            
            i = 0
            while i < len(args):
                if args[i] == '-ptr' and i + 1 < len(args):
                    # 找到 -ptr 选项，收集其后的地址表达式
                    ptr_expr = []
                    i += 1  # 跳过 -ptr
                    while i < len(args) and args[i] != '-ptr' and args[i] != '-c' and args[i] != '--count':
                        ptr_expr.append(args[i])
                        i += 1
                    if ptr_expr:
                        ptr_expressions.append(' '.join(ptr_expr))
                elif (args[i] == '-c' or args[i] == '--count') and i + 1 < len(args):
                    # 找到 -c 或 --count 选项，获取其后的值
                    count_value = args[i + 1]
                    i += 2  # 跳过选项和值
                else:
                    # 普通地址参数
                    direct_addresses.append(args[i])
                    i += 1
            
            # 处理所有 -ptr 表达式
            for addr_expr in ptr_expressions:
                # print(f"[ 先获取地址 {addr_expr} 中的指针值 ]")
                
                pointer_addr = cls.getPointer(debugger, addr_expr, exe_ctx, result, internal_dict)
                
                if pointer_addr is not None:
                    pointer_addr = Utils.ensure_hex_prefix(pointer_addr)
                    # print(f"[ 获取到指针值: {pointer_addr} ]")
                    # 使用获取到的指针值执行内存读取
                    if count_value:
                        memread_command = f'memory read --force -c {count_value} {pointer_addr}'
                    else:
                        memread_command = f'memory read --force -c 0x50 {pointer_addr}'
                    # print(f"[ 执行内存读取命令: {memread_command} ]")
                    
                    # 使用临时的 result 对象，避免覆盖主 result
                    temp_result = lldb.SBCommandReturnObject()
                    interpreter.HandleCommand(memread_command, temp_result)
                    
                    if temp_result.Succeeded():
                        print(temp_result.GetOutput().strip() + "\n")
                    else:
                        print(f"[ 错误: {temp_result.GetError().strip()} ]")
                else:
                    print(f"[ 错误: 无法获取指针地址 {addr_expr} ]")

            
            # 处理所有直接地址
            total_operations = len(ptr_expressions) + len(direct_addresses)
            for addr in direct_addresses:
                if count_value:
                    memread_command = f'memory read --force -c {count_value} {addr}'
                else:
                    memread_command = f'memory read --force -c 0x50 {addr}'
                # print(f"[ 执行内存读取命令: {memread_command} ]")
                
                # 对于多个操作或多个地址，使用临时的 result 对象
                if total_operations > 1 or len(direct_addresses) > 1:
                    temp_result = lldb.SBCommandReturnObject()
                    interpreter.HandleCommand(memread_command, temp_result)
                    
                    if temp_result.Succeeded():
                        print(temp_result.GetOutput().strip() + "\n")
                    else:
                        print(f"[ 错误: {temp_result.GetError().strip()} ]")
                else:
                    # 单个操作且单个地址时使用主 result
                    interpreter.HandleCommand(memread_command, result)
                        
        except Exception as e:
            print(f"[ 内存读取失败: {e} ]")

    @classmethod  
    def nopMemory(cls, debugger, command, exe_ctx, result, internal_dict):
        """[ 将指定地址或地址范围的内存修改为NOP指令（ARM64 NOP指令（小端序）: D503201F）
    支持以下格式:
    1. 单个地址: nop 0x1063c2c10
    2. 多个地址: nop 0x1063c2c10 1063c2c18 0x1063c2c20
    3. 地址范围: nop [0x1063c2c10, 0x1063c2c20]
    >> 注意：nop 地址范围时，地址一定要以 0x 开头，nop 单个地址和多个地址时，地址不一定要以 0x 开头"""
        # 默认NOP指令小端序
        little_endian_nop = "0xD503201F"
        
        # 解析命令参数
        command = command.strip()
        
        # 检查是否是地址范围格式 [start, end]
        range_match = re.search(r'\[(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+)\]', command)
        if range_match:
            # 处理地址范围
            # 在正则表达式中， 捕获组 是通过括号 () 括起来的部分，用于从匹配的字符串中提取特定部分的数据。捕获组从左到右编号，从1开始。
            start_addr = int(range_match.group(1), 16)
            end_addr = int(range_match.group(2), 16)
            
            # 验证范围
            if start_addr > end_addr:
                result.PutCString(f"[ 错误: 起始地址 {hex(start_addr)} 大于结束地址 {hex(end_addr)} ]")
                return
            
            # 确保地址对齐到4字节（ARM64指令宽度）
            start_addr = start_addr & ~0x3
            end_addr = (end_addr + 0x3) & ~0x3
            
            print(f"[ 处理地址范围: {hex(start_addr)} 到 {hex(end_addr)} ]")
            
            # 计算需要写入的次数
            count = (end_addr + 1 - start_addr) // 4
            # print(f"[ 将写入 {count} 个NOP指令 ]")
            
            # 遍历地址范围，每次递增4字节
            current_addr = start_addr
            success_count = 0
            while current_addr <= end_addr:
                exec_command = f'memory write -s 4 {hex(current_addr)} {little_endian_nop}'
                # 执行命令
                debugger.HandleCommand(exec_command)
                
                # 验证写入是否成功
                verify_command = f'memory read -s 4 -f x {hex(current_addr)}'
                return_obj = lldb.SBCommandReturnObject()
                debugger.GetCommandInterpreter().HandleCommand(verify_command, return_obj)
                
                if return_obj.Succeeded():
                    success_count += 1
                
                current_addr += 4
            
            print(f"[ 地址范围NOP操作完成，成功写入 {success_count} 个NOP指令 ]")
            return
        
        # 处理多个地址
        args = shlex.split(command)
        if not args:
            result.PutCString('[ 请提供至少一个地址，支持单个地址、多个地址或地址范围格式 ]')
            return
        
        success_count = 0
        # 遍历所有地址
        for i, address_str in enumerate(args):
            # 确保地址以0x开头
            address = Utils.ensure_hex_prefix(address_str)
            
            # 执行内存写入命令
            exec_command = f'memory write -s 4 {address} {little_endian_nop}'
            # print(f"[ 地址 {i+1}: 执行命令: {exec_command} ]")
            
            # 执行命令
            debugger.HandleCommand(exec_command)
            
            # 验证写入是否成功
            verify_command = f'memory read -s 4 -f x {address}'
            return_obj = lldb.SBCommandReturnObject()
            debugger.GetCommandInterpreter().HandleCommand(verify_command, return_obj)
            
            if return_obj.Succeeded():
                success_count += 1
                # print(f"[ 地址 {i+1} 验证结果: {return_obj.GetOutput().strip()} ]")
            else:
                print(f"[ 地址 {i+1} 验证失败: {return_obj.GetError()} ]")
        
        print(f"[ 多地址NOP操作完成，共处理 {len(args)} 个地址, 成功写入 {success_count} 个NOP指令 ]")

    @classmethod  
    def getPointer(cls, debugger, command, exe_ctx, result, internal_dict):
        """[ 获取地址中的指针地址 ]
    使用方法：ptr <reg_name> 或者 ptr <addr>
    举例：ptr ($x8 + 0x8) ($x8 + 0x20) 或者 ptr 0x12345678"""
        # 检查是否提供了参数
        if not command or not command.strip():
            print("[ 请提供要获取指针地址的地址或寄存器表达式，例如: ptr ($x8 + 0x8) 或 ptr 0x12345678 ]")
            return
        
        try:
            # 分割命令参数
            args = shlex.split(command)
            
            # 处理每个地址参数
            for addr_expr in args:
                
                if addr_expr.startswith('$') is False:
                    # 地址表达式，确保以0x开头
                    addr_expr = Utils.ensure_hex_prefix(addr_expr)
                
                # 构建 LLDB 命令获取指针地址
                lldb_command = f'memory read -c 1 -s 8 -f x {addr_expr}'
                
                # print(f"[ 执行命令: {lldb_command} ]")
                
                # 执行命令并获取结果
                return_obj = lldb.SBCommandReturnObject()
                interpreter = debugger.GetCommandInterpreter()
                interpreter.HandleCommand(lldb_command, return_obj)
                
                # 获取命令输出
                output = return_obj.GetOutput()
                error = return_obj.GetError()
                print(f"[ {output.strip()} ]")
                
                if return_obj.Succeeded():
                    # 使用正则表达式提取所有地址
                    matches = re.findall(r'(0x[a-fA-F0-9]+)', output)
                    if len(matches) >= 2:
                        # 返回第二个地址（指针值）
                        pointer_addr = matches[1]
                        # 输出提取的地址
                        # print(pointer_addr)
                        return pointer_addr
                    elif len(matches) == 1:
                        # 如果只有一个地址，返回它
                        pointer_addr = matches[0]
                        # print(pointer_addr)
                        return pointer_addr
                    else:
                        print(f"[ 错误: 无法从输出中提取地址: {output.strip()} ]")
                        return None
                else:
                    # 输出错误信息
                    print(f"[ 错误: {error.strip()} ]")
                    return None
                    
        except Exception as e:
            print(f"[ 获取指针地址失败: {e} ]")

    @classmethod  
    def saveCmd(cls, debugger, command, exe_ctx, result, internal_dict): 
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
        # 初始化 DataHandler
        cls._data_handler = cls._data_handler if cls._data_handler is not None else DataHandler()
        
        # 执行history命令获取命令历史
        return_obj = lldb.SBCommandReturnObject()
        debugger.GetCommandInterpreter().HandleCommand('history', return_obj)
        
        # 获取命令输出
        output = return_obj.GetOutput()
        if not output:
            print("[ 无法获取命令历史. ]")
            return
        
        # 解析历史命令，构建序号到命令的映射
        history_dict = {}
        
        # 获取 saveCmd 在 lldb 中的名字
        save_cmd_name = cls._data_handler.cmd_script.get("saveCmd")
        
        if not save_cmd_name:
            print("[ 无法获取 saveCmd 在 lldb 中的名字. ]")
            return
        
        for line in output.strip().split('\n'):
            match = re.search(r'(\d+):\s+(.*)', line)
            if match:
                index = int(match.group(1))
                cmd = match.group(2)
                if save_cmd_name in cmd:
                    continue
                
                history_dict[index] = cmd
        
        
        # 要保存的命令记录列表
        records_to_save = []
        
        # 处理命令参数
        if not command or not command.strip():
            # 情况1: save - 保存最近一条命令，描述为空
            if history_dict:
                max_index = max(history_dict.keys())
                recent_cmd = history_dict[max_index]
                records_to_save.append({"command": recent_cmd, "desc": ""})
        else:
            # 使用shlex.split处理命令参数，更安全地分割带引号的参数
            try:
                args = shlex.split(command)
                
                # 解析参数，处理序号和描述
                i = 0
                while i < len(args):
                    # 检查当前参数是数字（序号）还是字符串（描述）
                    if args[i].isdigit():
                        # 这是一个序号
                        index = int(args[i])
                        if index in history_dict:
                            cmd = history_dict[index]
                            # 检查下一个参数是否是描述（不是数字）
                            desc = ""
                            if i + 1 < len(args) and not args[i+1].isdigit():
                                desc = args[i+1]
                                i += 1  # 跳过描述参数
                            records_to_save.append({"command": cmd, "desc": desc})
                        else:
                            print(f"[ 警告: 序号 {index} 的命令不存在. ]")
                    else:
                        # 这是一个描述，应用于最近一条命令
                        if history_dict:
                            max_index = max(history_dict.keys())
                            recent_cmd = history_dict[max_index]
                            records_to_save.append({"command": recent_cmd, "desc": args[i]})
                    
                    i += 1
                
                if not records_to_save:
                    print("[ 没有找到有效的命令序号. ]")
                    return
                    
            except ValueError as e:
                print(f"[ 错误: 解析命令参数失败 - {e} ]")
                return
        
        # 将新记录添加到现有的 cmd_record_list
        cls._data_handler.cmd_record_list.extend(records_to_save)
        
        # 保存到 JSON 文件
        try:
            cls._data_handler.save_cmd_record()
            
            # 输出保存结果
            if len(records_to_save) == 1:
                print(f"[ 命令: \"{records_to_save[0]['command']}\" 已保存，描述: \"{records_to_save[0]['desc']}\" ]")
            else:
                print(f"[ 已成功保存 {len(records_to_save)} 条命令到 cmd_record.json 中 ]")
                for i, record in enumerate(records_to_save):
                    print(f"  {i+1}. {record['command']} - {record['desc']}")
                    
        except Exception as e:
            print(f"[ 保存命令到文件失败: {e} ]")
       
    @classmethod  
    def showCmd(cls, debugger, command, exe_ctx, result, internal_dict):
        """[显示保存在 cmd_record.json 中的所有命令]
    >> 使用方法：showCmd
    >> 功能：从缓存中读取保存的命令，并以序号形式输出所有命令及其描述
    """
        cls._data_handler = cls._data_handler if cls._data_handler is not None else DataHandler()
    
        # 检查是否有命令记录
        if not cls._data_handler.cmd_record_list:
            print("[ 命令列表为空. ]")
            return
        
        try:
            # 输出命令列表
            print("[ 命令列表 ]")
            
            # 获取命令别名字典，用于显示命令别名
            cmd_alias = cls._data_handler.cmd_alias
            
            # 遍历命令记录
            for i, record in enumerate(cls._data_handler.cmd_record_list):
                cmd = record.get("command", "")
                desc = record.get("desc", "")
                
                # 显示命令序号、别名和描述
                if cmd:
                    print(f"{i}. {cmd} —— {desc}")
                
        except Exception as e:
            print(f"[ 显示命令列表失败: {e} ]")

    @classmethod 
    def removeCmd(cls, debugger, command, exe_ctx, result, internal_dict):
        """[根据序号删除 cmd_record.json 中的指定命令]
    >> 使用方法：rm <index1> <index2> ...
    >> 功能：根据 showCmd 命令显示的序号删除对应的命令记录
    >> 例如：rm 1 3 - 删除序号为1和3的命令
    """
        cls._data_handler = cls._data_handler if cls._data_handler is not None else DataHandler()
        
        # 检查是否有命令记录
        if not cls._data_handler.cmd_record_list:
            print("[ 没有可删除的命令记录. ]")
            return
        
        # 检查是否提供了序号参数
        if not command or not command.strip():
            print("[ 请提供要删除的命令序号，例如: rm 1 3 ]")
            return
        
        try:
            # 解析要删除的序号
            try:
                # 序号从0开始，直接使用
                indices = [int(idx) for idx in shlex.split(command)]
            except ValueError:
                print("[ 错误: 请提供有效的命令序号. ]")
                return
            
            # 验证序号有效性
            valid_indices = []
            invalid_indices = []
            for idx in indices:
                if 0 <= idx < len(cls._data_handler.cmd_record_list):
                    valid_indices.append(idx)
                else:
                    invalid_indices.append(idx)
            
            # 显示无效序号警告
            if invalid_indices:
                print(f"[ 警告: 序号 {', '.join(map(str, invalid_indices))} 超出有效范围(0-{len(cls._data_handler.cmd_record_list)-1}). ]")
            
            if not valid_indices:
                print("[ 没有有效的序号可供删除. ]")
                return
            
            # 去重并降序排序，确保删除时不会影响后续索引
            valid_indices = sorted(list(set(valid_indices)), reverse=True)
            
            # 记录要删除的命令
            remove_commands = []
            for idx in valid_indices:
                remove_commands.append(cls._data_handler.cmd_record_list[idx])
                cls._data_handler.cmd_record_list.pop(idx)
            
            # 保存到 JSON 文件
            cls._data_handler.save_cmd_record()
            
            # 显示删除结果
            deleted_count = len(remove_commands)
            if deleted_count == 1:
                cmd = remove_commands[0]["command"]
                desc = remove_commands[0]["desc"]
                print(f"[ 已成功删除命令: {cmd} - {desc} ]")
            else:
                print(f"[ 已成功删除 {deleted_count} 条命令 ]")
                for i, record in enumerate(remove_commands):
                    print(f"  {i+1}. {record['command']} - {record['desc']}")
            
            # 删除后显示当前命令列表
            print("\n更新后的命令列表:")
            cls.showCmd(debugger, "", exe_ctx, result, internal_dict)
                
        except Exception as e:
            print(f"[ 删除命令失败: {e} ]")

    @classmethod 
    def execCmd(cls, debugger, command, exe_ctx, result, internal_dict):
        """[根据序号执行 cmd_record.json 中的命令]
    >> 使用方法：exec <index>
    >> 功能：根据 showCmd 命令显示的序号执行对应的命令（每次只执行一条）
    >> 例如：exec 1 - 执行序号为1的命令
    """
        cls._data_handler = cls._data_handler if cls._data_handler is not None else DataHandler()
        
        # 检查是否有命令记录
        if not cls._data_handler.cmd_record_list:
            print("[ 没有可执行的命令记录. ]")
            return
        
        # 检查是否提供了序号参数
        if not command or not command.strip():
            print("[ 请提供要执行的命令序号，例如: exec 1 ]")
            return
        
        try:
            # 解析序号参数
            try:
                # 序号从0开始，直接使用
                indices = [int(idx) for idx in shlex.split(command)]
            except ValueError:
                print("[ 错误: 请提供有效的命令序号. ]")
                return
            
            # 只取第一个序号，忽略其他
            if len(indices) > 1:
                print(f"[ 提示: 只会执行第一个序号 {indices[0]} 的命令，忽略其他序号. ]")
            
            index = indices[0]
            
            # 验证序号有效性
            if 0 <= index < len(cls._data_handler.cmd_record_list):
                # 获取要执行的命令记录
                record = cls._data_handler.cmd_record_list[index]
                command_to_exec = record.get("command", "")
                desc = record.get("desc", "")
                
                # 显示命令和描述
                print(f"[ 执行命令: {command_to_exec} ]")
                if desc:
                    print(f"[ 命令描述: {desc} ]")
                
                # 执行命令
                debugger.HandleCommand(command_to_exec)
                
            else:
                print(f"[ 错误: 序号 {index} 超出有效范围(0-{len(cls._data_handler.cmd_record_list)-1}). ]")
                return
                
        except Exception as e:
            print(f"[ 执行命令失败: {e} ]")


    @classmethod
    def parseSwiftString(cls, debugger, command, exe_ctx, result, internal_dict):
        """[解析 Swift String 字符串]
    >> 使用方法：ss <register_or_address>
    >> 例如：ss $x0
    >> 功能：解析 Swift 字符串，支持小字符串和大字符串格式"""
        
        # 检查是否提供了参数
        if not command or not command.strip():
            print("[ 请提供寄存器或地址，例如: ss $x0 ]")
            return
        
        # 解析命令参数
        args = shlex.split(command)
        if len(args) != 1:
            print("[ 请提供单个寄存器或地址参数，例如: ss $x0 ]")
            return
            
        target = args[0]
        
        try:
            # 判断是寄存器还是地址
            if target.startswith('$'):
                # 处理寄存器
                # 提取寄存器编号
                reg_num = target[2:]
                if not reg_num.isdigit():
                    print(f"[ 无效的寄存器格式: {target} ]")
                    return
                    
                reg_num = int(reg_num)
                
                # 确定要读取的两个寄存器
                reg1 = f"x{reg_num}"
                reg2 = f"x{reg_num + 1}"
                print(f"[ 要读取的寄存器: {reg1} 和 {reg2} ]")
                # 读取寄存器值
                cmd = f"register read ${reg1} ${reg2}"
                return_obj = lldb.SBCommandReturnObject()
                debugger.GetCommandInterpreter().HandleCommand(cmd, return_obj)
                
                if not return_obj.Succeeded():
                    print(f"[ 读取寄存器失败: {return_obj.GetError()} ]")
                    return
                
                output = return_obj.GetOutput()
                
                # 解析寄存器值
                reg_values = {}
                for line in output.split('\n'):
                    if '=' in line:
                        parts = line.split('=')
                        if len(parts) == 2:
                            reg_name = parts[0].strip()
                            reg_value_full = parts[1].strip()
                            
                            # 使用正则表达式提取第一个 0x 开头的值
                            match = re.search(r'(0x[a-fA-F0-9]+)', reg_value_full)
                            if match:
                                reg_value = match.group(1)
                                reg_values[reg_name] = reg_value
                            
                print(f"[ 寄存器值解析结果: {reg_values} ]")
                if reg1 not in reg_values or reg2 not in reg_values:
                    print(f"[ 无法解析寄存器值 ]")
                    return
                
                # 获取寄存器值
                low_reg_value = reg_values[reg1]
                high_reg_value = reg_values[reg2]
                
                # 去掉 0x 前缀
                low_hex = low_reg_value.replace("0x", "")
                high_hex = high_reg_value.replace("0x", "")
                
                # 检查是否是小字符串（高位寄存器以 e 开头）
                if high_hex.startswith('e'):
                    # 获取字符串长度（e 后面的第一位）
                    if len(high_hex) < 2:
                        print("[ 无法正确解析为 Swift 的字符串 ]")
                        return
                        
                    length_char = high_hex[1]
                    try:
                        str_length = int(length_char, 16)
                    except ValueError:
                        print("[ 无法正确解析为 Swift 的字符串 ]")
                        return
                    
                    # 检查是否是空字符串
                    if str_length == 0:
                        # 验证是否是空字符串格式（低位寄存器全0，高位寄存器为 e000000000000000）
                        if low_hex == "0" * len(low_hex) and high_hex == "e" + "0" * (len(high_hex) - 1):
                            print("[ 解析结果: \"\" (空字符串) ]")
                            return
                        else:
                            print("[ 无法正确解析为 Swift 的字符串 ]")
                            return
                    
                    # 拼接高位和低位寄存器值
                    combined_hex = high_hex + low_hex
                    
                    # 从后往前截取 2*str_length 位字符
                    if len(combined_hex) < 2 * str_length:
                        print("[ 无法正确解析为 Swift 的字符串 ]")
                        return
                        
                    str_hex = combined_hex[-(2 * str_length):]
                    
                    # 字节逆转（每两个字符一组进行反转）
                    bytes_list = [str_hex[i:i+2] for i in range(0, len(str_hex), 2)]
                    reversed_bytes = bytes_list[::-1]
                    reversed_hex = ''.join(reversed_bytes)
                    
                    # 转换为 ASCII 字符串
                    try:
                        result_str = bytes.fromhex(reversed_hex).decode('ascii')
                        print(f"[ 解析结果: \"{result_str}\" ]")
                        return
                    except (ValueError, UnicodeDecodeError):
                        print("[ 无法正确解析为 Swift 的字符串 ]")
                        return
                else:
                    # 不是小字符串，尝试作为大字符串处理
                    # 使用高位寄存器的值作为地址，偏移 0x20
                    address = high_hex
                    
                    # 确保地址以 0x 开头
                    address = Utils.ensure_hex_prefix(address)
                    
                    # 读取字符串
                    cmd = f"memory read -f s {address}+0x20"
                    return_obj = lldb.SBCommandReturnObject()
                    debugger.GetCommandInterpreter().HandleCommand(cmd, return_obj)
                    
                    if not return_obj.Succeeded():
                        print(f"[ 执行的命令: {cmd} ]")
                        print(f"[ 读取内存失败: {return_obj.GetError()} ]")
                        return
                    
                    output = return_obj.GetOutput()
                    
                    # 解析输出，提取字符串内容
                    lines = output.split('\n')
                    for line in lines:
                        if ':' in line and '"' in line:
                            # 提取引号内的内容
                            start = line.find('"')
                            end = line.rfind('"')
                            if start != -1 and end != -1 and end > start:
                                str_content = line[start+1:end]
                                print(f"[ 解析结果: \"{str_content}\" ]")
                                return
                    
                    print("[ 无法正确解析为 Swift 的字符串 ]")
            else:
                # 处理地址
                # 直接读取指定地址的字符串
                
                # 确保地址以 0x 开头
                address = Utils.ensure_hex_prefix(target)
                
                cmd = f"memory read -f s {address}+0x20"
                return_obj = lldb.SBCommandReturnObject()
                debugger.GetCommandInterpreter().HandleCommand(cmd, return_obj)
                
                if not return_obj.Succeeded():
                    print(f"[ 执行的命令: {cmd} ]")
                    print(f"[ 读取内存失败: {return_obj.GetError()} ]")
                    return
                
                output = return_obj.GetOutput()
                
                # 解析输出，提取字符串内容
                lines = output.split('\n')
                for line in lines:
                    if ':' in line and '"' in line:
                        # 提取引号内的内容
                        start = line.find('"')
                        end = line.rfind('"')
                        if start != -1 and end != -1 and end > start:
                            str_content = line[start+1:end]
                            print(f"[ 解析结果: \"{str_content}\" ]")
                            return
                
                print("[ 无法正确解析为 Swift 的字符串 ]")
                
        except Exception as e:
            print(f"[ 解析 Swift 字符串失败: {e} ]")
            
            
            
    @classmethod
    def parseSwiftData(cls, debugger, command, exe_ctx, result, internal_dict):
        """[解析 Swift Data 数据]
    >> 使用方法：sd <register>
    >> 例如：sd $x0
    >> 功能：解析 Swift Data，支持小数据和大数据格式"""
        
        # 检查是否提供了参数
        if not command or not command.strip():
            print("[ 请提供寄存器，例如: sd $x0 ]")
            return
        
        # 解析命令参数
        args = shlex.split(command)
        if len(args) != 1:
            print("[ 请提供单个寄存器参数，例如: sd $x0 ]")
            return
            
        target = args[0]
        
        try:
            # 判断是寄存器还是地址
            if target.startswith('$'):
                # 处理寄存器
                # 提取寄存器编号
                reg_num = target[2:]
                if not reg_num.isdigit():
                    print(f"[ 无效的寄存器格式: {target} ]")
                    return
                    
                reg_num = int(reg_num)
                
                # 确定要读取的两个寄存器
                reg1 = f"x{reg_num}"
                reg2 = f"x{reg_num + 1}"
                print(f"[ 要读取的寄存器: {reg1} 和 {reg2} ]")
                
                # 读取寄存器值
                cmd = f"register read ${reg1} ${reg2}"
                return_obj = lldb.SBCommandReturnObject()
                debugger.GetCommandInterpreter().HandleCommand(cmd, return_obj)
                
                if not return_obj.Succeeded():
                    print(f"[ 读取寄存器失败: {return_obj.GetError()} ]")
                    return
                
                output = return_obj.GetOutput()
                
                # 解析寄存器值
                reg_values = {}
                for line in output.split('\n'):
                    if '=' in line:
                        parts = line.split('=')
                        if len(parts) == 2:
                            reg_name = parts[0].strip()
                            reg_value_full = parts[1].strip()
                            
                            # 使用正则表达式提取第一个 0x 开头的值
                            match = re.search(r'(0x[a-fA-F0-9]+)', reg_value_full)
                            if match:
                                reg_value = match.group(1)
                                reg_values[reg_name] = reg_value
                
                print(f"[ 寄存器值解析结果: {reg_values} ]")
                if reg1 not in reg_values or reg2 not in reg_values:
                    print(f"[ 无法解析寄存器值 ]")
                    return
                
                # 获取寄存器值
                value_0 = reg_values[reg1]
                value_1 = reg_values[reg2]
                
                # 去掉 0x 前缀
                hex_0 = value_0.replace("0x", "")
                hex_1 = value_1.replace("0x", "")
                
                # 尝试解析为小Data
                # 小Data的长度存在于x1中，从x1的值中提取长度
                if len(hex_1) >= 4:
                    # 提取x1中的长度（前4位）
                    length_hex = hex_1[:4]
                    try:
                        data_length = int(length_hex, 16)
                        if data_length > 0 and data_length <= 0x1000:  # 合理的长度范围
                            # 拼接x1和x0的值
                            combined_hex = hex_1 + hex_0
                            
                            # 从后往前截取 2*data_length 位字符
                            if len(combined_hex) >= 2 * data_length:
                                data_hex = combined_hex[-(2 * data_length):]
                                
                                # 字节逆转（每两个字符一组进行反转）
                                bytes_list = [data_hex[i:i+2] for i in range(0, len(data_hex), 2)]
                                reversed_bytes = bytes_list[::-1]
                                reversed_hex = ''.join(reversed_bytes)
                                
                                                                # 输出数组格式
                                byte_values = [f"0x{b}" for b in bytes_list[::-1]]
                                print(f"[ 小Data解析结果(数组): [{','.join(byte_values)}] ]")

                                # 输出十六进制格式（无空格）
                                print(f"[ 小Data解析结果(十六进制): {reversed_hex} ]")
                                
                                # 尝试转换为字符串
                                try:
                                    result_str = bytes.fromhex(reversed_hex).decode('ascii')
                                    print(f"[ 小Data解析结果(字符串): \"{result_str}\" ]")
                                except (ValueError, UnicodeDecodeError):
                                    print(f"[ 小Data解析结果(字符串): 无法解析为ASCII字符串 ]")
                                

                                return
                    except ValueError:
                        pass  # 如果解析失败，继续尝试大Data
                
                # 尝试解析为大Data
                # 大Data的长度存在于x0中，第7位和第8位组成一个十六进制字节
                if len(hex_0) >= 16:
                    # 提取第7位和第8位（索引6和7）
                    length_hex = hex_0[6:8]
                    try:
                        data_length = int(length_hex, 16)
                        if data_length > 0 and data_length <= 0x1000:  # 合理的长度范围
                            # 使用x1的值作为地址，加上0x10偏移
                            address = value_1
                            address = Utils.ensure_hex_prefix(address)
                            addr_expr = f"{address}+0x10"
                            
                            # 获取指针地址
                            pointer_addr = cls.getPointer(debugger, addr_expr, exe_ctx, result, internal_dict)
                            
                            if pointer_addr is not None:
                                pointer_addr = Utils.ensure_hex_prefix(pointer_addr)
                                print(f"[ 获取到指针值: {pointer_addr} ]")
                                
                                # 读取数据
                                memread_command = f'memory read -c 0x{data_length:x} -s 1 -f x {pointer_addr}'
                                return_obj = lldb.SBCommandReturnObject()
                                debugger.GetCommandInterpreter().HandleCommand(memread_command, return_obj)
                                
                                if return_obj.Succeeded():
                                    output = return_obj.GetOutput()
                                    
                                    # 解析输出，只提取每行中冒号后面的0x值
                                    hex_values = []
                                    for line in output.split('\n'):
                                        if ':' in line:
                                            # 分割冒号前后的内容
                                            parts = line.split(':', 1)
                                            if len(parts) == 2:
                                                # 只处理冒号后面的部分
                                                data_part = parts[1]
                                                # 提取所有0x开头的值
                                                matches = re.findall(r'(0x[a-fA-F0-9]+)', data_part)
                                                for match in matches:
                                                    hex_values.append(match.replace("0x", ""))
                                    
                                    if hex_values:
                                        # 拼接所有值
                                        combined_hex = ''.join(hex_values)
                                        
                                        # 输出十六进制格式（无空格）
                                        print(f"[ 大Data解析结果(十六进制): {combined_hex} ]")
                                        
                                        # 输出数组格式
                                        byte_values = [f"0x{h}" for h in hex_values]
                                        print(f"[ 大Data解析结果(数组): [{','.join(byte_values)}] ]")
                                        
                                        # 尝试转换为字符串
                                        try:
                                            result_str = bytes.fromhex(combined_hex).decode('ascii')
                                            print(f"[ 大Data解析结果(字符串): \"{result_str}\" ]")
                                        except (ValueError, UnicodeDecodeError):
                                            print(f"[ 大Data解析结果(字符串): 无法解析为ASCII字符串 ]")
                                        
                                        return
                                    else:
                                        print(f"[ 无法从内存读取结果中提取数据 ]")
                                else:
                                    print(f"[ 读取内存失败: {return_obj.GetError()} ]")
                            else:
                                print(f"[ 无法获取指针地址 ]")
                        else:
                            print(f"[ 解析的Data长度({data_length})超出合理范围 ]")
                    except ValueError:
                        print(f"[ 无法解析Data长度 ]")
                else:
                    print(f"[ x0寄存器值长度不足，无法解析为大Data ]")
                
                print("[ 无法正确解析为 Swift Data ]")
            else:
                print("[ 当前只支持寄存器输入，不支持直接地址输入 ]")
                
        except Exception as e:
            print(f"[ 解析 Swift Data 失败: {e} ]")