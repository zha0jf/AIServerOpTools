#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import os
import argparse
import re
from typing import List, Optional

# 定义AI卡关键字
AI_CARD_KEYWORDS = [
        "NVIDIA",
        "10de:",  # NVIDIA的PCI ID
        "Huawei",
        "19e5:",  # Huawei的PCI ID
        "Enrigin",
        "1fbd:",  # Enrigin的PCI ID
        "MetaX",
        "9999:",  # MetaX的PCI ID
        "Iluvatar",
        "1e3e:",  # Iluvatar的PCI ID
        "Hexaflake",
        "1faa:"   # Hexaflake的PCI ID
    ]

# --- 全局常量 (针对PCIe扩展功能) ---
# 要操作的目标寄存器
TARGET_REGISTER = "CAP_EXP+8.w"
# "Extended Tag Field Enable" 是Device Control Register的第8位
EXT_TAG_BIT_INDEX = 8
EXT_TAG_BIT_MASK = 1 << EXT_TAG_BIT_INDEX

def get_lspci_gpu_list():
    """使用lspci获取GPU设备列表"""
    try:
        # 使用lspci命令获取PCI设备信息
        result = subprocess.run(['lspci'], capture_output=True, text=True, check=True)
        lines = result.stdout.split('\n')
        
        # 过滤出AI卡
        gpu_devices = []
        for line in lines:
            # 跳过audio设备
            if "Audio device" in line:
                continue
            for keyword in AI_CARD_KEYWORDS:
                if keyword in line:
                    gpu_devices.append(line)
                    break
        
        return gpu_devices
        
    except FileNotFoundError:
        print("Error: 'lspci' command not found. Please ensure it's installed and in PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing lspci command: {e}")
        sys.exit(1)

def get_gpu_list():
    """获取GPU列表"""
    try:
        # 使用新函数获取GPU列表
        gpu_devices = get_lspci_gpu_list()
        
        # 记录找到的厂商
        vendors_found = set()
        for line in gpu_devices:
            for keyword in AI_CARD_KEYWORDS:
                if keyword in line:
                    # 记录厂商
                    if "NVIDIA" in keyword or "10de:" in keyword:
                        vendors_found.add("NVIDIA")
                    elif "Huawei" in keyword or "19e5:" in keyword:
                        vendors_found.add("Huawei")
                    elif "Enrigin" in keyword or "1fbd:" in keyword:
                        vendors_found.add("Enrigin")
                    elif "MetaX" in keyword or "9999:" in keyword:
                        vendors_found.add("MetaX")
                    elif "Iluvatar" in keyword or "1e3e:" in keyword:
                        vendors_found.add("Iluvatar")
                    elif "Hexaflake" in keyword or "1faa:" in keyword:
                        vendors_found.add("Hexaflake")
                    break
        
        # 打印通过lspci找到的GPU列表
        if gpu_devices:
            print("GPU List (from lspci):")
            for device in gpu_devices:
                print(f"  {device}")
        else:
            print("No GPU devices found by lspci.")
            
        # 使用厂商对应的AI卡管理工具获取AI卡列表
        print("\nGPU List (from vendor tools):")
        vendor_tools = {
            "NVIDIA": ["nvidia-smi"],
            "Huawei": ["npu-smi", "info"],
            "Enrigin": ["ersmi"],
            "MetaX": ["mx-smi"],
            "Iluvatar": ["ixsmi"],
            "Hexaflake": ["hxsmi"]
        }
        
        # 检查每个厂商的工具是否可用
        for vendor in vendors_found:
            if vendor in vendor_tools:
                tool_cmd = vendor_tools[vendor]
                tool_name = tool_cmd[0]
                
                # 检查工具是否存在
                if subprocess.run(['which', tool_name], capture_output=True).returncode == 0:
                    try:
                        result = subprocess.run(tool_cmd, capture_output=True, text=True, check=True)
                        print(f"  {vendor} GPUs (using {tool_name}):")
                        # 处理输出，每行一个GPU
                        for line in result.stdout.strip().split('\n'):
                            if line:  # 忽略空行
                                print(f"    {line}")
                    except subprocess.CalledProcessError as e:
                        print(f"  {vendor} GPUs (using {tool_name}): Error executing tool - {e}")
                else:
                    print(f"  Warning: {vendor} AI card tool is not installed, please install {tool_name} first")
        
        # 如果没有找到任何厂商的AI卡
        if not vendors_found:
            print("No AI card vendors found.")
            
    except FileNotFoundError:
        print("Error: 'lspci' command not found. Please ensure it's installed and in PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing lspci command: {e}")
        sys.exit(1)

def get_pcie_topology():
    """获取AI卡P2P拓扑信息"""
    # 根据不同的AI卡厂商使用对应的工具获取拓扑信息
    # NVIDIA: nvidia-smi topo -m
    # Huawei: npu-smi info -t
    # Enrigin: ersmi --topo
    # MetaX: mx-smi topo -m
    # Iluvatar: ixsmi topo -m
    # Hexaflake: hxsmi topo
    
    try:
        # 检查是否有NVIDIA GPU
        if subprocess.run(['which', 'nvidia-smi'], capture_output=True).returncode == 0:
            print("NVIDIA GPU Topology:")
            result = subprocess.run(['nvidia-smi', 'topo', '-m'], capture_output=True, text=True, check=True)
            print(result.stdout)
            return
        
        # 检查是否有Huawei NPU
        if subprocess.run(['which', 'npu-smi'], capture_output=True).returncode == 0:
            print("Huawei NPU Topology:")
            result = subprocess.run(['npu-smi', 'info', '-t'], capture_output=True, text=True, check=True)
            print(result.stdout)
            return
        
        # 检查是否有Enrigin GPU
        if subprocess.run(['which', 'ersmi'], capture_output=True).returncode == 0:
            print("Enrigin GPU Topology:")
            result = subprocess.run(['ersmi', '--topo'], capture_output=True, text=True, check=True)
            print(result.stdout)
            return
        
        # 检查是否有MetaX GPU
        if subprocess.run(['which', 'mx-smi'], capture_output=True).returncode == 0:
            print("MetaX GPU Topology:")
            result = subprocess.run(['mx-smi', 'topo', '-m'], capture_output=True, text=True, check=True)
            print(result.stdout)
            return
        
        # 检查是否有Iluvatar GPU
        if subprocess.run(['which', 'ixsmi'], capture_output=True).returncode == 0:
            print("Iluvatar GPU Topology:")
            result = subprocess.run(['ixsmi', 'topo', '-m'], capture_output=True, text=True, check=True)
            print(result.stdout)
            return
        
        # 检查是否有Hexaflake GPU
        if subprocess.run(['which', 'hxsmi'], capture_output=True).returncode == 0:
            print("Hexaflake GPU Topology:")
            result = subprocess.run(['hxsmi', 'topo'], capture_output=True, text=True, check=True)
            print(result.stdout)
            return
        
        print("No supported AI card tools found.")
        
    except FileNotFoundError:
        print("Error: AI card tool not found. Please ensure the appropriate tool for your AI card is installed and in PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing AI card tool: {e}")
        sys.exit(1)

def is_pci_bdf(bdf):
    """检查字符串是否是PCI BDF格式"""
    # PCI BDF格式: bus:device.function (e.g., 0000:01:00.0)
    pattern = r'^[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F]$'
    return re.match(pattern, bdf) is not None

def get_root_port(pci_addr):
    """根据AI卡的PCIe地址获取其接入的PCIe根设备地址"""
    try:
        device_symlink = f"/sys/bus/pci/devices/{pci_addr}"
        
        # 检查设备是否存在
        if not os.path.islink(device_symlink):
            print(f"Error: Device '{pci_addr}' does not exist.", file=sys.stderr)
            return None
        
        # 1. 获取设备的真实物理路径
        current_path = os.path.realpath(device_symlink)
        last_pci_device = os.path.basename(current_path)
        
        # 2. 循环向上遍历目录
        while True:
            parent_path = os.path.dirname(current_path)
            
            # 如果到达了根目录或不再是pci设备目录，则停止
            if parent_path == "/" or not os.path.isdir(parent_path):
                break
            
            parent_name = os.path.basename(parent_path)
            
            # 3. 检查父目录名是否是PCI BDF格式
            if is_pci_bdf(parent_name):
                # 如果是，更新最后已知的PCI设备并继续向上
                last_pci_device = parent_name
                current_path = parent_path
            else:
                # 如果父目录不再是PCI设备，则我们已经找到了根端口
                break
        
        return last_pci_device
    except Exception as e:
        print(f"Unexpected error getting root port for {pci_addr}: {e}")
        return None

def get_pci_path_to_root(endpoint_bdf: str) -> Optional[List[str]]:
    """获取从端设备到其根端口的完整PCIe设备路径列表。"""
    if not is_pci_bdf(endpoint_bdf):
        print(f"Error: Input '{endpoint_bdf}' is not a valid BDF format.")
        return None

    symlink_path = f"/sys/bus/pci/devices/{endpoint_bdf}"
    if not os.path.lexists(symlink_path):
        print(f"Error: Device '{endpoint_bdf}' does not exist in /sys/bus/pci/devices/.")
        return None

    try:
        real_path = os.path.realpath(symlink_path)
        path_components = []
        current_path = real_path
        
        while current_path != "/" and "pci" in current_path:
            basename = os.path.basename(current_path)
            if is_pci_bdf(basename):
                path_components.append(basename)
            parent_path = os.path.dirname(current_path)
            if parent_path == current_path:
                break
            current_path = parent_path
            
        if not path_components:
            print(f"Error: Could not find any PCIe path components for '{endpoint_bdf}'.")
            return None
            
        return path_components
    except Exception as e:
        print(f"Error occurred while finding PCIe path: {e}")
        return None

def _run_setpci_read(bdf: str, register: str) -> Optional[int]:
    """
    【通用函数】执行setpci读命令并返回寄存器的整数值。
    """
    command = ['sudo', 'setpci', '-s', bdf, register]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=5)
        return int(result.stdout.strip(), 16)
    except FileNotFoundError:
        print("Error: 'sudo' or 'setpci' command not found. Please ensure pciutils is installed and you have sudo privileges.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"  -> Failed to read register {register} of device {bdf}: {e.stderr.strip()}")
        return None
    except ValueError:
        print(f"  -> Failed to read register {register} of device {bdf}: Unable to parse setpci output.")
        return None

def _run_setpci_write(bdf: str, register: str, value: int) -> bool:
    """
    【通用函数】执行setpci写命令。
    """
    hex_value = f"{value:04x}"
    command = ['sudo', 'setpci', '-s', bdf, f"{register}={hex_value}"]
    try:
        subprocess.run(command, capture_output=True, text=True, check=True, timeout=5)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    -> Failed to write register {register} of device {bdf}: {e.stderr.strip()}")
        return False

def get_extend_status(endpoint_bdf: str) -> Optional[bool]:
    """
    【专用函数】获取指定AI端设备整个链路上所有设备的 Extended Tag Field 状态。
    此函数硬编码操作 'CAP_EXP+8.w' 寄存器。
    """
    path = get_pci_path_to_root(endpoint_bdf)
    if not path:
        return None

    # 只检查端设备和根设备
    endpoint_value = _run_setpci_read(endpoint_bdf, TARGET_REGISTER)
    root_bdf = path[-1]  # 根设备是路径中的最后一个设备
    root_value = _run_setpci_read(root_bdf, TARGET_REGISTER)
    
    # 如果无法读取端设备或根设备的状态，则返回 None
    if endpoint_value is None or root_value is None:
        return None
    
    # 只有当端设备和根设备都启用了 extend 时，才返回 True
    endpoint_enabled = bool(endpoint_value & EXT_TAG_BIT_MASK)
    root_enabled = bool(root_value & EXT_TAG_BIT_MASK)
    
    status = endpoint_enabled and root_enabled
    
    # 输出格式与其他 trace 部分保持一致
    if status:
        print("    Status: Enabled")
    else:
        print("    Status: Disabled")
        
    return status

def trace_issues():
    """追踪问题"""
    try:
        # 获取GPU列表
        gpu_lines = get_lspci_gpu_list()
        gpu_devices = []
        for line in gpu_lines:
            gpu_devices.append(line)  # 保存完整行信息
        
        if not gpu_devices:
            print("No GPU devices found.")
            return
        
        print("Tracing GPU PCIe issues:")
        for line in gpu_devices:
            parts = line.split(' ', 1)  # 分割PCI地址和设备描述
            pci_addr = parts[0]
            device_name = parts[1] if len(parts) > 1 else "Unknown Device"
            
            # 输出AI卡设备章节标题
            print(f"\n===== AI Card: {device_name} ({pci_addr}) =====")
            
            # 获取根设备地址
            root_port = get_root_port(pci_addr)
            if not root_port:
                print(f"  Error: Could not determine root port for {pci_addr}")
                continue
            
            print(f"  Root Port: {root_port}")
            
            # 获取根设备和AI卡设备的详细信息
            try:
                root_result = subprocess.run(['lspci', '-s', root_port, '-vv'], capture_output=True, text=True, check=True)
                device_result = subprocess.run(['lspci', '-s', pci_addr, '-vv'], capture_output=True, text=True, check=True)
            except subprocess.CalledProcessError as e:
                print(f"  Error getting device details: {e}")
                continue
            
            # 1. 链接状态信息
            print("  Link Status:")
            # 根设备链接能力与状态
            root_lnkcap = [line for line in root_result.stdout.split('\n') if "LnkCap:" in line]
            root_lnksta = [line for line in root_result.stdout.split('\n') if "LnkSta:" in line]
            if root_lnkcap and root_lnksta:
                print(f"    Root LnkCap: {root_lnkcap[0].strip()}")
                print(f"    Root LnkSta: {root_lnksta[0].strip()}")
            
            # AI卡设备链接能力与状态
            device_lnkcap = [line for line in device_result.stdout.split('\n') if "LnkCap:" in line]
            device_lnksta = [line for line in device_result.stdout.split('\n') if "LnkSta:" in line]
            if device_lnkcap and device_lnksta:
                print(f"    Device LnkCap: {device_lnkcap[0].strip()}")
                print(f"    Device LnkSta: {device_lnksta[0].strip()}")
            
            # 2. MaxPayload信息
            print("  MaxPayload:")
            # 根设备MaxPayload能力与状态
            root_payload_lines = [line for line in root_result.stdout.split('\n') if "MaxPayload" in line]
            for line in root_payload_lines:
                print(f"    Root {line.strip()}")
            
            # AI卡设备MaxPayload能力与状态
            device_payload_lines = [line for line in device_result.stdout.split('\n') if "MaxPayload" in line]
            for line in device_payload_lines:
                print(f"    Device {line.strip()}")
            
            # 3. MaxReadReq信息
            print("  MaxReadReq:")
            # 根设备MaxReadReq能力与状态
            root_readreq_lines = [line for line in root_result.stdout.split('\n') if "MaxReadReq" in line]
            for line in root_readreq_lines:
                print(f"    Root {line.strip()}")
            
            # AI卡设备MaxReadReq能力与状态
            device_readreq_lines = [line for line in device_result.stdout.split('\n') if "MaxReadReq" in line]
            for line in device_readreq_lines:
                print(f"    Device {line.strip()}")
            
            # 4. Completion Timeout信息
            print("  Completion Timeout:")
            # 根设备Completion Timeout
            root_timeout_lines = [line for line in root_result.stdout.split('\n') if "Completion Timeout:" in line]
            for line in root_timeout_lines:
                print(f"    Root {line.strip()}")
            
            # AI卡设备Completion Timeout
            device_timeout_lines = [line for line in device_result.stdout.split('\n') if "Completion Timeout:" in line]
            for line in device_timeout_lines:
                print(f"    Device {line.strip()}")
            
            # 5. ASPM信息
            print("  ASPM:")
            # 根设备ASPM
            root_aspm_lines = [line for line in root_result.stdout.split('\n') if "ASPM:" in line]
            for line in root_aspm_lines:
                print(f"    Root {line.strip()}")
            
            # AI卡设备ASPM
            device_aspm_lines = [line for line in device_result.stdout.split('\n') if "ASPM:" in line]
            for line in device_aspm_lines:
                print(f"    Device {line.strip()}")
            
            # 6. ACS状态
            print("  ACS:")
            try:
                root_detail_result = subprocess.run(['lspci', '-vvs', root_port], capture_output=True, text=True, check=True)
                acs_lines = [line for line in root_detail_result.stdout.split('\n') if "ACSCtl:" in line]
                if acs_lines:
                    acs_line = acs_lines[0]
                    if "+" in acs_line:
                        print(f"    Status: Enabled (via root port {root_port})")
                    else:
                        print(f"    Status: Disabled (via root port {root_port})")
                else:
                    print(f"    Status: Not supported or not found (via root port {root_port})")
            except subprocess.CalledProcessError as e:
                print(f"    Error checking ACS: {e}")
            
            # 7. PCIe扩展功能
            print("  PCIe Extend Capability:")
            # 检查整个链路上所有设备的Extended Tag Field状态
            get_extend_status(pci_addr)
        

    
    except FileNotFoundError:
        print("Error: 'lspci' command not found. Please ensure it's installed and in PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing lspci command: {e}")
        sys.exit(1)

def extend_enable(endpoint_bdf: str):
    """
    【专用函数】启用指定AI端设备整个链路上所有设备的 Extended Tag Field。
    此函数硬编码操作 'CAP_EXP+8.w' 寄存器。
    """
    print(f"\n--- Enabling Extended Tag Field (Register: {TARGET_REGISTER}, Path starts at {endpoint_bdf}) ---")
    
    path = get_pci_path_to_root(endpoint_bdf)
    if not path:
        return

    for bdf in path:
        print(f"  Processing device: {bdf}")
        # 调用通用的读函数，传入固定的目标寄存器
        current_value = _run_setpci_read(bdf, TARGET_REGISTER)
        if current_value is None:
            print("    -> Skipped, unable to read current value.")
            continue

        if not (current_value & EXT_TAG_BIT_MASK):
            print(f"    Current status: Disabled (Value: {current_value:04x}). Attempting to enable...")
            new_value = current_value | EXT_TAG_BIT_MASK
            # 调用通用的写函数，传入固定的目标寄存器
            if _run_setpci_write(bdf, TARGET_REGISTER, new_value):
                print(f"    Successfully written new value: {new_value:04x}")
            else:
                print("    Write failed!")
        else:
            print(f"    Current status: Enabled (Value: {current_value:04x}). No action needed.")

    print("\n--- Operation completed, starting verification of final status ---")
    # 调用专用的状态检查函数，它内部也知道要检查哪个寄存器
    get_extend_status(endpoint_bdf)

def enable_pcie_extend():
    """启用PCIe扩展功能"""
    print("Enabling PCIe extend capability for all GPUs...")
    print("Note: This operation requires root privileges and direct hardware access.")

    try:
        # 获取GPU列表
        gpu_lines = get_lspci_gpu_list()
        gpu_devices = []
        for line in gpu_lines:
            gpu_devices.append(line.split()[0])  # 获取PCI地址
        
        if not gpu_devices:
            print("No GPU devices found.")
            return
        
        for pci_addr in gpu_devices:
            print("")
            print(f"=== Checking Device {pci_addr} ===")
            # 首先检查extend状态
            status = get_extend_status(pci_addr)
            if status:
                print(f"  {pci_addr}: Already enabled, skipping.")
                continue
            
            # 如果现在是disabled状态，则配置启用
            # 配置过程不输出信息
            path = get_pci_path_to_root(pci_addr)
            if not path:
                print(f"  {pci_addr}: Failed to get PCIe path, skipping.")
                continue
            
            for bdf in path:
                # 调用通用的读函数，传入固定的目标寄存器
                current_value = _run_setpci_read(bdf, TARGET_REGISTER)
                if current_value is None:
                    continue
                
                if not (current_value & EXT_TAG_BIT_MASK):
                    new_value = current_value | EXT_TAG_BIT_MASK
                    # 调用通用的写函数，传入固定的目标寄存器
                    _run_setpci_write(bdf, TARGET_REGISTER, new_value)
            
            # 配置完成后，再次检查状态
            final_status = get_extend_status(pci_addr)
            if final_status:
                print(f"  {pci_addr}: Successfully enabled.")
            else:
                print(f"  {pci_addr}: Failed to enable, still disabled.")
                continue
        
    except FileNotFoundError:
        print("Error: 'lspci' command not found. Please ensure it's installed and in PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing lspci command: {e}")
        sys.exit(1)


def enable_acs():
    """启用ACS"""
    print("Enabling ACS for all GPUs...")
    print("Note: This operation requires root privileges and direct hardware access.")
    print("Implementation would involve using setpci to modify PCIe configuration space.")
    
    try:
        # 获取GPU列表
        gpu_lines = get_lspci_gpu_list()
        gpu_devices = []
        for line in gpu_lines:
            gpu_devices.append(line.split()[0])  # 获取PCI地址
        
        if not gpu_devices:
            print("No GPU devices found.")
            return
        
        for pci_addr in gpu_devices:
            # 启用ACS的命令 (示例，实际实现需要根据硬件调整)
            # setpci -v -s $pci_addr CAP_ACS+6.w=0x000f
            print(f"  Enabling ACS for {pci_addr} (would use setpci in actual implementation)")
        
    except FileNotFoundError:
        print("Error: 'lspci' command not found. Please ensure it's installed and in PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing lspci command: {e}")
        sys.exit(1)


def disable_acs():
    """禁用ACS"""
    print("Disabling ACS for all GPUs...")
    print("Note: This operation requires root privileges and direct hardware access.")
    print("Implementation would involve using setpci to modify PCIe configuration space.")
    
    try:
        # 获取GPU列表
        gpu_lines = get_lspci_gpu_list()
        gpu_devices = []
        for line in gpu_lines:
            gpu_devices.append(line.split()[0])  # 获取PCI地址
        
        if not gpu_devices:
            print("No GPU devices found.")
            return
        
        for pci_addr in gpu_devices:
            # 禁用ACS的命令 (示例，实际实现需要根据硬件调整)
            # setpci -v -s $pci_addr CAP_ACS+6.w=0x0000
            print(f"  Disabling ACS for {pci_addr} (would use setpci in actual implementation)")
        
    except FileNotFoundError:
        print("Error: 'lspci' command not found. Please ensure it's installed and in PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing lspci command: {e}")
        sys.exit(1)


def set_max_payload(value):
    """设置GPU MaxPayload"""
    # 值映射表
    value_map = {
        '0': '128B',
        '1': '256B',
        '2': '512B',
        '3': '1024B',
        '4': '2048B',
        '5': '4096B'
    }
    
    if value not in value_map:
        print(f"Invalid value for MaxPayload: {value}. Valid values are 0-5.")
        return
    
    print(f"Setting GPU MaxPayload to {value_map[value]}...")
    print("Note: This operation requires root privileges and direct hardware access.")
    print("Implementation would involve using setpci to modify PCIe configuration space.")
    
    try:
        # 获取GPU列表
        gpu_lines = get_lspci_gpu_list()
        gpu_devices = []
        for line in gpu_lines:
            gpu_devices.append(line.split()[0])  # 获取PCI地址
        
        if not gpu_devices:
            print("No GPU devices found.")
            return
        
        for pci_addr in gpu_devices:
            # 设置MaxPayload的命令 (示例，实际实现需要根据硬件调整)
            # setpci -v -s $pci_addr CAP_EXP+10.w=<value>
            print(f"  Setting MaxPayload for {pci_addr} to {value_map[value]} (would use setpci in actual implementation)")
            
    except FileNotFoundError:
        print("Error: 'lspci' command not found. Please ensure it's installed and in PATH.")


def set_max_read_req(value):
    """设置GPU MaxReadReq"""
    # 值映射表
    value_map = {
        '0': '128B',
        '1': '256B',
        '2': '512B',
        '3': '1024B',
        '4': '2048B',
        '5': '4096B'
    }
    
    if value not in value_map:
        print(f"Invalid value for MaxReadReq: {value}. Valid values are 0-5.")
        return
    
    print(f"Setting GPU MaxReadReq to {value_map[value]}...")
    print("Note: This operation requires root privileges and direct hardware access.")
    print("Implementation would involve using setpci to modify PCIe configuration space.")
    
    try:
        # 获取GPU列表
        gpu_lines = get_lspci_gpu_list()
        gpu_devices = []
        for line in gpu_lines:
            gpu_devices.append(line.split()[0])  # 获取PCI地址
        
        if not gpu_devices:
            print("No GPU devices found.")
            return
        
        for pci_addr in gpu_devices:
            # 设置MaxReadReq的命令 (示例，实际实现需要根据硬件调整)
            # setpci -v -s $pci_addr CAP_EXP+12.w=<value>
            print(f"  Setting MaxReadReq for {pci_addr} to {value_map[value]} (would use setpci in actual implementation)")
            
    except FileNotFoundError:
        print("Error: 'lspci' command not found. Please ensure it's installed and in PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing lspci command: {e}")
        sys.exit(1)


def set_completion_timeout_disable(value):
    """设置GPU Completion Timeout Disable"""
    # 值映射表
    value_map = {
        '0': 'disable',
        '1': 'enable'
    }
    
    if value not in value_map:
        print(f"Invalid value for Completion Timeout Disable: {value}. Valid values are 0-1.")
        return
    
    print(f"Setting GPU Completion Timeout Disable to {value_map[value]}...")
    print("Note: This operation requires root privileges and direct hardware access.")
    print("Implementation would involve using setpci to modify PCIe configuration space.")
    
    try:
        # 获取GPU列表
        gpu_lines = get_lspci_gpu_list()
        gpu_devices = []
        for line in gpu_lines:
            gpu_devices.append(line.split()[0])  # 获取PCI地址
        
        if not gpu_devices:
            print("No GPU devices found.")
            return
        
        for pci_addr in gpu_devices:
            # 设置Completion Timeout Disable的命令 (示例，实际实现需要根据硬件调整)
            # setpci -v -s $pci_addr CAP_EXP+14.w=<value>
            print(f"  Setting Completion Timeout Disable for {pci_addr} to {value_map[value]} (would use setpci in actual implementation)")
            
    except FileNotFoundError:
        print("Error: 'lspci' command not found. Please ensure it's installed and in PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing lspci command: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="A tool that can diagnose and resolve issues of p2p, d2h and h2d blockage or slowdown.")
    parser.add_argument('--topo', action='store_true', help='AI card P2P topology.')
    parser.add_argument('-l', '--list', action='store_true', help='List GPU.')
    parser.add_argument('--trace', action='store_true', help='Identify the factors causing p2p, d2h and h2d blockage or slowdown.')
    parser.add_argument('--enable-acs', action='store_true', help='Enable ACS.')
    parser.add_argument('--disable-acs', action='store_true', help='Disable ACS.')
    parser.add_argument('--enable-extend', action='store_true', help='Enable the PCIe extend capability.')
    parser.add_argument('--set-mps', type=str, help='Set GPU MaxPayload.(E.g., 0: 128B; 1: 256B.)')
    parser.add_argument('--set-mrrs', type=str, help='Set GPU MaxReadReq.(E.g., 0: 128B; 1: 256B; 2: 512B; 3: 1024B; 4: 2048B; 5: 4096B.)')
    parser.add_argument('--set-timeoutDis', type=str, help='Set GPU Completion Timeout Disable.(E.g., 0: disable; 1: enable.)')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0')
    
    args = parser.parse_args()
    
    # 根据参数执行相应功能
    if args.list:
        get_gpu_list()
    elif args.topo:
        get_pcie_topology()
    elif args.trace:
        trace_issues()
    elif args.enable_acs:
        enable_acs()
    elif args.disable_acs:
        disable_acs()
    elif args.enable_extend:
        enable_pcie_extend()
    elif args.set_mps:
        set_max_payload(args.set_mps)
    elif args.set_mrrs:
        set_max_read_req(args.set_mrrs)
    elif args.set_timeoutDis:
        set_completion_timeout_disable(args.set_timeoutDis)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()