#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#================================================================
#
#          FILE: gpu-pcie-tuner.py
#
#         USAGE: sudo ./gpu-pcie-tuner.py
#
#   DESCRIPTION: Automatically tunes PCIe settings for AI GPUs to
#                optimize performance. Adjusts Completion Timeout
#                and Extended Tag Field settings.
#
#  REQUIREMENTS: lspci, setpci
#          BUGS: ---
#         NOTES: Run with sudo/root privileges.
#        AUTHOR: Zha0jf
#  ORGANIZATION: Skysolidiss
#       Modified: 2025-11-17
#      REVISION: 1.0
#
#================================================================

import subprocess
import sys
import os
import argparse
import re
from typing import List, Optional


def parse_completion_timeout(lines, label):
    """
    解析 lspci 输出的 Completion Timeout 信息，返回设备能力和当前配置
    """
    devcap2 = None
    devctl2 = None

    for line in lines:
        if "DevCap2" in line and "Completion Timeout" in line:
            devcap2 = line.strip()
        elif "DevCtl2" in line and "Completion Timeout" in line:
            devctl2 = line.strip()

    # ---------- 设备能力 ----------
    capability = "Unknown"
    if devcap2:
        if "Not Supported" in devcap2:
            capability = "Not support adjusting CTO Range"
        else:
            # 尝试提取 Range AB / Range XY
            match = re.search(r"Range\s+[A-Z]+", devcap2)
            if match:
                capability = f"Support {match.group(0)}"
            else:
                capability = "CTO Supported"

        if "TimeoutDis+" in devcap2:
            capability += ", TimeoutDis+ (support disable)"
        elif "TimeoutDis-" in devcap2:
            capability += ", TimeoutDis- (cannot disable)"

    # ---------- 当前配置 ----------
    status = "Unknown"
    range_info = None
    if devctl2:
        if "TimeoutDis+" in devctl2:
            status = "Disabled"
        elif "TimeoutDis-" in devctl2:
            status = "Enabled"

        # 更强健的匹配，支持 us/ms/s
        match = re.search(r"(\d+\s*(us|ms|s)\s*to\s*\d+\s*(us|ms|s))", devctl2)
        if match:
            range_info = match.group(1)

    if status == "Disabled":
        current_cfg = "CTO Disabled (time range ignored)"
    elif status == "Enabled":
        if range_info:
            current_cfg = f"CTO Enabled, Range = {range_info}"
        else:
            current_cfg = "CTO Enabled"
    else:
        current_cfg = "CTO status Unknown"

    return label, capability, current_cfg

def print_completion_timeout(result, label):
    lines = result.stdout.splitlines()
    label, capability, current_cfg = parse_completion_timeout(lines, label)
    print(f"{label}:")
    print(f"  Capability : {capability}")
    print(f"  CurrentCfg : {current_cfg}")

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
        "Moore Threads",
        "1ed5:",  # Moore Threads的PCI ID
        "Iluvatar",
        "1e3e:",  # Iluvatar的PCI ID
        "Hexaflake",
        "1faa:",  # Hexaflake的PCI ID
        "Denglin",
        "1e27:"   # 登临GPU的PCI ID
    ]

# 定义厂商对应的AI卡管理工具
VENDOR_TOOLS = {
    "NVIDIA": ["nvidia-smi"],
    "Huawei": ["npu-smi", "info"],
    "Enrigin": ["ersmi"],
    "MetaX": ["mx-smi"],
    "Moore Threads": ["mthreads-gmi"],
    "Iluvatar": ["ixsmi"],
    "Hexaflake": ["hxsmi"],
    "Denglin": ["dlsmi"]
}

# 定义厂商对应的AI卡拓扑命令
VENDOR_TOPO_TOOLS = {
    "NVIDIA": ["nvidia-smi", "topo", "-m"],
    "Huawei": ["npu-smi", "info", "-t", "--topo"],
    "Enrigin": ["ersmi", "--topo"],
    "MetaX": ["mx-smi", "topo", "-m"],
    "Moore Threads": ["mthreads-gmi", "topo", "-m"],
    "Iluvatar": ["ixsmi", "topo", "-m"],
    "Hexaflake": ["hxsmi", "topo"],
    "Denglin": ["dlsmi", "topo", "-m"]
}

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
            if "Audio" in line:
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
                    elif "Moore Threads" in keyword or "1ed5:" in keyword:
                        vendors_found.add("Moore Threads")
                    elif "Iluvatar" in keyword or "1e3e:" in keyword:
                        vendors_found.add("Iluvatar")
                    elif "Hexaflake" in keyword or "1faa:" in keyword:
                        vendors_found.add("Hexaflake")
                    elif "Denglin" in keyword or "1e27:" in keyword:
                        vendors_found.add("Denglin")
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
        
        # 检查每个厂商的工具是否可用
        for vendor in vendors_found:
            if vendor in VENDOR_TOOLS:
                tool_cmd = VENDOR_TOOLS[vendor]
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
    
    try:
        # 使用lspci获取GPU设备列表
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
                    elif "Moore Threads" in keyword or "1ed5:" in keyword:
                        vendors_found.add("Moore Threads")
                    elif "Iluvatar" in keyword or "1e3e:" in keyword:
                        vendors_found.add("Iluvatar")
                    elif "Hexaflake" in keyword or "1faa:" in keyword:
                        vendors_found.add("Hexaflake")
                    elif "Denglin" in keyword or "1e27:" in keyword:
                        vendors_found.add("Denglin")
                    break
        
        # 检查每个厂商的工具是否可用并调用相应的topo命令
        topo_executed = False
        for vendor in vendors_found:
            if vendor in VENDOR_TOPO_TOOLS:
                tool_cmd = VENDOR_TOPO_TOOLS[vendor]
                tool_name = tool_cmd[0]
                
                # 检查工具是否存在
                if subprocess.run(['which', tool_name], capture_output=True).returncode == 0:
                    print(f"{vendor} GPU Topology:")
                    result = subprocess.run(tool_cmd, capture_output=True, text=True, check=True)
                    print(result.stdout)
                    topo_executed = True
                else:
                    print(f"Error: {vendor} AI card tool ({tool_name}) is not installed. Please install it first.")
                    continue
        
        # 如果没有找到任何厂商的AI卡或没有执行任何topo命令
        if not vendors_found or not topo_executed:
            print("No supported AI card tools found or executed.")
            sys.exit(1)
        
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
        # 使用 get_pci_path_to_root 获取从端设备到根端口的完整路径
        path = get_pci_path_to_root(pci_addr)
        
        # 检查路径是否存在且非空
        if not path:
            print(f"Error: Could not determine PCIe path for '{pci_addr}'")
            return None
        
        # 根端口是路径中的最后一个设备
        root_port = path[-1]
        return root_port
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
        # 1. IOMMU/SMMU 状态
        print("  IOMMU/SMMU Status:")
        try:
            # 检查/sys/class/iommu目录是否存在且非空
            if os.path.exists("/sys/class/iommu") and os.listdir("/sys/class/iommu"):
                # IOMMU已启用 - 对于AI服务器，这通常被视为错误
                print("    Status: Enabled - AI servers typically require it to be disabled")
            else:
                # IOMMU已禁用 - 这是期望的状态
                print("    Status: Disabled - Compliant with AI server configuration requirements")
        except Exception as e:
            print(f"    Error checking IOMMU status: {e}")
        
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
            
            # 2. 链接状态信息
            print("  Link Status:")
            # 根设备链接能力与状态
            root_lnkcap = [line for line in root_result.stdout.split('\n') if "LnkCap:" in line]
            root_lnksta = [line for line in root_result.stdout.split('\n') if "LnkSta:" in line]
            if root_lnkcap and root_lnksta:
                # 提取Speed和Width信息
                root_lnkcap_parts = root_lnkcap[0].split(",")
                root_lnkcap_speed = next((part for part in root_lnkcap_parts if "Speed" in part), "")
                root_lnkcap_width = next((part for part in root_lnkcap_parts if "Width" in part), "")
                print(f"    Root LnkCap: {root_lnkcap_speed.strip()}, {root_lnkcap_width.strip()}")
                
                root_lnksta_parts = root_lnksta[0].split(",")
                root_lnksta_speed = next((part for part in root_lnksta_parts if "Speed" in part), "").replace("LnkSta:", "").strip()
                root_lnksta_width = next((part for part in root_lnksta_parts if "Width" in part), "").replace("LnkSta:", "").strip()
                print(f"    Root LnkSta: {root_lnksta_speed}, {root_lnksta_width}")
            
            # AI卡设备链接能力与状态
            device_lnkcap = [line for line in device_result.stdout.split('\n') if "LnkCap:" in line]
            device_lnksta = [line for line in device_result.stdout.split('\n') if "LnkSta:" in line]
            if device_lnkcap and device_lnksta:
                # 提取Speed和Width信息
                device_lnkcap_parts = device_lnkcap[0].split(",")
                device_lnkcap_speed = next((part for part in device_lnkcap_parts if "Speed" in part), "")
                device_lnkcap_width = next((part for part in device_lnkcap_parts if "Width" in part), "")
                print(f"    Device LnkCap: {device_lnkcap_speed.strip()}, {device_lnkcap_width.strip()}")
                
                device_lnksta_parts = device_lnksta[0].split(",")
                device_lnksta_speed = next((part for part in device_lnksta_parts if "Speed" in part), "").replace("LnkSta:", "").strip()
                device_lnksta_width = next((part for part in device_lnksta_parts if "Width" in part), "").replace("LnkSta:", "").strip()
                print(f"    Device LnkSta: {device_lnksta_speed}, {device_lnksta_width}")
            
            # 3. MaxPayload信息
            print("  MaxPayload:")
            # 获取从设备到根端口的路径
            path = get_pci_path_to_root(pci_addr)
            if not path:
                print("    Error: Unable to get PCIe path.")
            else:
                # 遍历路径上所有端口并获取MaxPayload信息
                for port in path:
                    try:
                        port_detail_result = subprocess.run(['lspci', '-vvs', port], capture_output=True, text=True, check=True)
                        # 获取设备MaxPayload能力与状态
                        devcap_lines = [line for line in port_detail_result.stdout.split('\n') if "DevCap:" in line and "MaxPayload" in line]
                        maxpayload_lines = [line for line in port_detail_result.stdout.split('\n') if "MaxPayload" in line and "DevCap:" not in line]

                        # 输出设备信息
                        print(f"    Port {port}:")
                        for line in devcap_lines:
                            # 提取MaxPayload信息
                            maxpayload_info = line.split("MaxPayload", 1)[1].split(",")[0].strip() if "MaxPayload" in line else line.strip()
                            print(f"      DevCap: MaxPayload {maxpayload_info}")
                        for line in maxpayload_lines:
                            # 提取MaxPayload信息
                            maxpayload_info = line.split("MaxPayload", 1)[1].split(",")[0].strip() if "MaxPayload" in line else line.strip()
                            print(f"      DevCtl: MaxPayload {maxpayload_info}")
                    except subprocess.CalledProcessError as e:
                        print(f"    Error checking MaxPayload for port {port}: {e}")

            
            # 4. MaxReadReq信息
            print("  MaxReadReq:")
            # 根设备MaxReadReq能力与状态
            root_maxreadreq_lines = [line for line in root_result.stdout.split('\n') if "MaxReadReq" in line]
            for line in root_maxreadreq_lines:
                # 提取MaxReadReq信息
                maxreadreq_info = line.split("MaxReadReq", 1)[1].strip() if "MaxReadReq" in line else line.strip()
                print(f"    Root MaxReadReq {maxreadreq_info}")
            
            # AI卡设备MaxReadReq能力与状态
            device_maxreadreq_lines = [line for line in device_result.stdout.split('\n') if "MaxReadReq" in line]
            for line in device_maxreadreq_lines:
                # 提取MaxReadReq信息
                maxreadreq_info = line.split("MaxReadReq", 1)[1].strip() if "MaxReadReq" in line else line.strip()
                print(f"    Device MaxReadReq {maxreadreq_info}")
            
            # 5. Completion Timeout信息
            print("  Completion Timeout:")
            # 根设备Completion Timeout
            root_lines = root_result.stdout.splitlines()
            root_label, root_capability, root_current_cfg = parse_completion_timeout(root_lines, "Root")
            print(f"    {root_label}:")
            print(f"      Capability : {root_capability}")
            print(f"      CurrentCfg : {root_current_cfg}")
            
            # AI卡设备Completion Timeout
            device_lines = device_result.stdout.splitlines()
            device_label, device_capability, device_current_cfg = parse_completion_timeout(device_lines, "Device")
            print(f"    {device_label}:")
            print(f"      Capability : {device_capability}")
            print(f"      CurrentCfg : {device_current_cfg}")
            
            # 6. ASPM信息
            print("  ASPM:")
            # 根设备ASPM
            root_aspm_config = [line for line in root_result.stdout.split('\n') if "LnkCtl:" in line and "ASPM" in line]
            if root_aspm_config:
                # 提取ASPM状态信息，删除"; RCB 64 bytes Disabled- CommClk-"等内容
                aspm_info = root_aspm_config[0].strip()
                # 使用正则表达式提取ASPM状态
                match = re.search(r'(ASPM\s+[^;]+)', aspm_info)
                if match:
                    print(f"    Root {match.group(1)}")
                else:
                    print(f"    Root {aspm_info}")
            else:
                print("    Root 未找到相关信息")
            
            # AI卡设备ASPM
            device_aspm_config = [line for line in device_result.stdout.split('\n') if "LnkCtl:" in line and "ASPM" in line]
            if device_aspm_config:
                # 提取ASPM状态信息，删除"; RCB 64 bytes Disabled- CommClk-"等内容
                aspm_info = device_aspm_config[0].strip()
                # 使用正则表达式提取ASPM状态
                match = re.search(r'(ASPM\s+[^;]+)', aspm_info)
                if match:
                    print(f"    Device {match.group(1)}")
                else:
                    print(f"    Device {aspm_info}")
            else:
                print("    Device 未找到相关信息")
            
            # 7. ACS状态
            print("  ACS:")
            # 获取从设备到根端口的路径
            path = get_pci_path_to_root(pci_addr)
            if not path:
                print("    Error: Unable to get PCIe path.")
            else:
                acs_enabled_ports = []
                for port in path:
                    try:
                        port_detail_result = subprocess.run(['lspci', '-vvs', port], capture_output=True, text=True, check=True)
                        acs_lines = [line for line in port_detail_result.stdout.split('\n') if "ACSCtl:" in line]
                        if acs_lines:
                            acs_line = acs_lines[0]
                            if "+" in acs_line:
                                acs_enabled_ports.append(port)
                    except subprocess.CalledProcessError as e:
                        print(f"    Error checking ACS for port {port}: {e}")
                
                if acs_enabled_ports:
                    print(f"    Status: Enabled on ports: {', '.join(acs_enabled_ports)}")
                else:
                    print("    Status: Disabled on all ports in the path")
            
            # 8. PCIe扩展功能
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
    
    try:
        # 获取GPU列表
        gpu_lines = get_lspci_gpu_list()
        gpu_devices = []
        for line in gpu_lines:
            gpu_devices.append(line.split()[0])  # 获取PCI地址
        
        if not gpu_devices:
            print("No GPU devices found.")
            return
        
        success = True
        for pci_addr in gpu_lines:
            print(f"  Enabling ACS for {pci_addr}")
            # 调用configure_acs_for_upstream_ports函数启用ACS
            if not configure_acs_for_upstream_ports(pci_addr, 'enable'):
                success = False
        
        if success:
            print("ACS enabling completed successfully.")
        else:
            print("ACS enabling completed with some errors.")
        
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
    
    try:
        # 获取GPU列表
        gpu_lines = get_lspci_gpu_list()
        gpu_devices = []
        for line in gpu_lines:
            gpu_devices.append(line.split()[0])  # 获取PCI地址
        
        if not gpu_devices:
            print("No GPU devices found.")
            return
        
        success = True
        for pci_addr in gpu_lines:
            print(f"  Disabling ACS for {pci_addr}")
            # 调用configure_acs_for_upstream_ports函数禁用ACS
            if not configure_acs_for_upstream_ports(pci_addr, 'disable'):
                success = False
        
        if success:
            print("ACS disabling completed successfully.")
        else:
            print("ACS disabling completed with some errors.")
        
    except FileNotFoundError:
        print("Error: 'lspci' command not found. Please ensure it's installed and in PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing lspci command: {e}")
        sys.exit(1)


def set_max_read_req(value):
    """为所有 GPU 设置 MaxReadReq"""

    # 值映射表 (PCIe Device Control [14:12])
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

    print(f"Setting GPU MaxReadReq to {value_map[value]}... (requires root)")

    try:
        # 获取 GPU PCIe 地址列表
        gpu_lines = get_lspci_gpu_list()
        gpu_devices = [line.split()[0] for line in gpu_lines]

        if not gpu_devices:
            print("No GPU devices found.")
            return

        for pci_addr in gpu_devices:
            # 读出当前 Device Control (CAP_EXP+0x08.w)
            reg_hex = subprocess.check_output(
                ["setpci", "-s", pci_addr, "CAP_EXP+8.w"], text=True
            ).strip()
            reg_val = int(reg_hex, 16)

            # 清除 MRRS 位 (14:12)
            reg_new = (reg_val & 0x8FFF) | (int(value) << 12)

            # 写回新值
            subprocess.run(
                ["setpci", "-s", pci_addr, f"CAP_EXP+8.w={reg_new:04x}"],
                check=True
            )

            print(f"  {pci_addr}: MRRS {value_map[value]} "
                  f"(reg {reg_val:04x} -> {reg_new:04x})")

    except FileNotFoundError:
        print("Error: 'setpci' not found. Please install pciutils.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing setpci: {e}")
        sys.exit(1)


def set_completion_timeout_disable(value): 
    """设置 GPU 以及其 Root Port 的 Completion Timeout Disable 位"""

    # 映射表：0=disable CTO disable（即启用CTO功能），1=enable CTO disable（即禁用CTO功能）
    value_map = {
        '0': 'CTO Enabled (TimeoutDis-)',
        '1': 'CTO Disabled (TimeoutDis+)'
    }

    if value not in value_map:
        print(f"Invalid value for Completion Timeout Disable: {value}. Valid values are 0 or 1.")
        return

    target_bit = int(value)  # 0 or 1

    print(f"Setting Device and RC Completion Timeout Disable -> {value_map[value]}")
    print("Note: This operation requires root privileges and direct hardware access.\n")

    try:
        # 获取 GPU 列表
        gpu_lines = get_lspci_gpu_list()
        gpu_devices = [line.split()[0] for line in gpu_lines]

        if not gpu_devices:
            print("No GPU devices found.")
            return

        for gpu_bdf in gpu_devices:
            print(f"Processing GPU {gpu_bdf} ...")

            # 找到 RC
            rc_bdf = get_root_port(gpu_bdf)
            if not rc_bdf:
                print(f"  [Skip] Cannot find Root Port for GPU {gpu_bdf}")
                continue

            # 遍历 GPU 和 RC
            for dev_name, bdf in [("GPU", gpu_bdf), ("RC", rc_bdf)]:
                reg = "CAP_EXP+28.w"

                old_val = _run_setpci_read(bdf, reg)
                if old_val is None:
                    print(f"  [Error] Failed to read {dev_name} ({bdf}) register {reg}")
                    continue

                # 修改 bit4
                new_val = (old_val & ~(1 << 4)) | (target_bit << 4)

                if new_val == old_val:
                    print(f"  {dev_name} {bdf}: Already {value_map[value]}")
                    continue

                ok = _run_setpci_write(bdf, reg, new_val)
                if ok:
                    print(f"  {dev_name} {bdf}: Set {value_map[value]} (reg {reg}, old=0x{old_val:04x}, new=0x{new_val:04x})")
                else:
                    print(f"  [Error] Failed to write {dev_name} ({bdf}) register {reg}")

            print("")  # 换行分隔设备

    except FileNotFoundError:
        print("Error: 'lspci' command not found. Please ensure it's installed and in PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing lspci command: {e}")
        sys.exit(1)

def set_completion_timeout_range(value):
    """
    根据PCIe Gen5规范设置GPU和其上游根端口（Root Port）的Completion Timeout Range。
    此版本使用 A_1, A_2 等索引格式作为输入参数。
    """
    # 范围描述映射表，用于打印英文信息
    range_description_map = {
        'Default': 'Default Range (40ms~50ms@FM, 50us~50ms@NFM)',
        'A_1': 'Range A (50us~100us)',
        'A_2': 'Range A (1ms~10ms)',
        'B_1': 'Range B (16ms~55ms)',
        'B_2': 'Range B (65ms~210ms)',
        'C_1': 'Range C (260ms~900ms)',
        'C_2': 'Range C (1s~3.5s)',
        'D_1': 'Range D (4s~13s)',
        'D_2': 'Range D (17s~64s)',
    }

    # Device Control 2 寄存器 (CAP_EXP+28h) 中 Completion Timeout Value 字段的正确编码值
    # 这是根据规范需要写入寄存器的确切值
    register_value_map = {
        'Default': 0b0000,
        'A_1':     0b0001,
        'A_2':     0b0010,
        'B_1':     0b0101,
        'B_2':     0b0110,
        'C_1':     0b1001,
        'C_2':     0b1010,
        'D_1':     0b1101,
        'D_2':     0b1110,
    }

    # Device Capabilities 2 寄存器中，Completion Timeout Ranges Supported 字段的位定义
    # 用于检查设备是否支持某个主范围 (A, B, C, D)
    support_bit_map = {
        'A': 0b0001,  # Bit 0 for Range A
        'B': 0b0010,  # Bit 1 for Range B
        'C': 0b0100,  # Bit 2 for Range C
        'D': 0b1000   # Bit 3 for Range D
    }

    if value not in register_value_map:
        print(f"Error: Invalid value '{value}' for Completion Timeout Range.")
        print("Valid values are: " + ", ".join(sorted(register_value_map.keys())))
        return

    print(f"Preparing to set Completion Timeout Range to: {range_description_map[value]}...")
    print("Note: This operation requires root privileges.")

    try:
        gpu_lines = get_lspci_gpu_list()
        gpu_devices = [line.split()[0] for line in gpu_lines]

        if not gpu_devices:
            print("No GPU devices found.")
            return

        for pci_addr in gpu_devices:
            print(f"\nProcessing GPU {pci_addr} and its Root Port...")
            root_port = get_root_port(pci_addr)
            
            devices_to_configure = []
            if root_port:
                devices_to_configure.append((root_port, "Root Port"))
            devices_to_configure.append((pci_addr, "GPU Device"))

            for dev, dev_type in devices_to_configure:
                # 步骤1: 读取 Device Capabilities 2 寄存器，判断是否支持可编程的CTO
                cap_val = _run_setpci_read(dev, "CAP_EXP+24.L")
                if cap_val is None:
                    print(f"  -> {dev_type} {dev}: Cannot read Device Capabilities 2 register.")
                    continue

                supported_mask = cap_val & 0xF  # bits 3:0 是支持范围的掩码
                if supported_mask == 0 and value != 'Default':
                    print(f"  -> {dev_type} {dev}: Does not support programmable Completion Timeout (fixed to Default Range).")
                    continue

                # 步骤2: 检查设备是否支持用户指定的目标主范围
                if value != 'Default':
                    # 从 'A_1' 这样的键中提取出主范围 'A'
                    general_range = value.split('_')[0]
                    if not (supported_mask & support_bit_map.get(general_range, 0)):
                        print(f"  -> {dev_type} {dev}: Does not support target main Range '{general_range}'. Supported mask=0x{supported_mask:X}.")
                        continue
                
                # 步骤3: 读取 Device Control 2 寄存器
                ctl_val = _run_setpci_read(dev, "CAP_EXP+28.L")
                if ctl_val is None:
                    print(f"  -> {dev_type} {dev}: Cannot read Device Control 2 register.")
                    continue

                # 步骤4: 检查Completion Timeout是否被禁用 (bit 4)
                if (ctl_val >> 4) & 0x1:
                    print(f"  -> {dev_type} {dev}: Completion Timeout is disabled. Cannot configure range.")
                    continue

                # 步骤5: 计算新的寄存器值并写入
                target_register_code = register_value_map[value]
                new_val = (ctl_val & ~0xF) | target_register_code

                success = _run_setpci_write(dev, "CAP_EXP+28.L", new_val)
                if success:
                    print(f"  -> {dev_type} {dev}: Successfully set Completion Timeout Range to '{value}' ({range_description_map[value]}).")
                else:
                    print(f"  -> {dev_type} {dev}: Failed to set Completion Timeout Range.")

    except FileNotFoundError:
        print("Error: 'lspci' or 'setpci' command not found. Please ensure pciutils is installed and in the system's PATH.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to execute external command: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def configure_acs_for_upstream_ports(pci_addr: str, target_state: str) -> bool:
    """
    配置指定设备PCIE链路上的所有上行PCIE端口的ACS为目标状态
    
    Args:
        pci_addr: 设备PCIe地址
        target_state: ACS目标状态 ('enable' 或 'disable')
    
    Returns:
        bool: 配置是否成功
    """
    # 1. 判断pcie地址是否为有效地址
    if not is_pci_bdf(pci_addr):
        print(f"Error: Input '{pci_addr}' is not a valid BDF format.")
        return False
    
    # 2. 获取PCIE链路
    path = get_pci_path_to_root(pci_addr)
    if not path:
        print(f"Error: Could not get PCIe path for device {pci_addr}")
        return False
    
    # 3. 针对链路上的每个设备
    success = True
    for i, bdf in enumerate(path):
        # 跳过端设备本身
        if i == 0:
            continue
            
        # 跳过根设备
        if i == len(path) - 1:
            continue
            
        # 4. 直接检查设备是否包含"ACSCtl:"关键字
        try:
            # 使用lspci -vvs PCIE地址获取设备详细信息
            acs_check = subprocess.run(['lspci', '-vvs', bdf], capture_output=True, text=True, check=True)
            # 检查输出中是否包含ACSCtl关键字
            if "ACSCtl:" in acs_check.stdout:
                # 具有ACSCtl关键字，配置ACS功能
                print(f"  Configuring upstream port {bdf} for ACS {target_state}")
                
                # 确定目标值
                target_value = 0x1d if target_state.lower() == 'enable' else 0x00
                
                # 使用setpci配置ACS
                hex_value = f"{target_value:02x}"
                command = ['sudo', 'setpci', '-s', bdf, f'ECAP_ACS+6.b={hex_value}']
                try:
                    subprocess.run(command, capture_output=True, text=True, check=True)
                    print(f"    Successfully set ACS to {hex_value} for {bdf}")
                except subprocess.CalledProcessError as e:
                    print(f"    Failed to set ACS for {bdf}: {e}")
                    success = False
            else:
                # 没有ACSCtl关键字，不配置
                print(f"    Device {bdf} does not support ACS, skipping.")
        except subprocess.CalledProcessError as e:
            print(f"    Error checking ACS capability for {bdf}: {e}")
            success = False
    
    # 5. 返回配置状态
    return success


# ===== 工具/映射 ===== 
_MPS_CODE_TO_BYTES = {0:128, 1:256, 2:512, 3:1024, 4:2048, 5:4096} 
_BYTES_TO_MPS_CODE = {v:k for k, v in _MPS_CODE_TO_BYTES.items()} 

def _has_pcie_cap(bdf: str) -> bool: 
    """ 
    通过读取 PCIe Capability 的某个寄存器来判断设备是否具备 PCIe Cap。 
    读 CAP_EXP+2.w（PCIe Capabilities Register）非 0 视为存在。 
    """ 
    v = _run_setpci_read(bdf, "CAP_EXP+2.w") 
    return v is not None and v != 0 

def _get_mps_cap_code(bdf: str) -> Optional[int]: 
    """ 
    读取设备支持的最大 MPS 的编码值 (Device Capabilities @ CAP_EXP+0x04.l, bits[2:0]) 
    返回编码 0..5（对应 128B..4096B）；无效则返回 None。 
    """ 
    if not _has_pcie_cap(bdf): 
        return None 
    reg = _run_setpci_read(bdf, "CAP_EXP+4.l") 
    if reg is None or reg == 0: 
        return None 
    return reg & 0x7  # bits[2:0] 

def _get_mps_current_code(bdf: str) -> Optional[int]: 
    """ 
    读取设备当前配置的 MPS 编码值 (Device Control @ CAP_EXP+0x08.w, bits[7:5]) 
    """ 
    if not _has_pcie_cap(bdf): 
        return None 
    reg = _run_setpci_read(bdf, "CAP_EXP+8.w") 
    if reg is None: 
        return None 
    return (reg >> 5) & 0x7 

def _set_mps_code(bdf: str, code: int) -> bool: 
    """ 
    设置设备的 MPS 编码值 (Device Control @ CAP_EXP+0x08.w, bits[7:5])，并校验写回。 
    """ 
    if not (0 <= code <= 5): 
        return False 
    if not _has_pcie_cap(bdf): 
        return False 

    reg = _run_setpci_read(bdf, "CAP_EXP+8.w") 
    if reg is None: 
        return False 

    new_val = (reg & ~(0x7 << 5)) | (code << 5) 
    if not _run_setpci_write(bdf, "CAP_EXP+8.w", new_val): 
        return False 

    # 读回校验 
    rb = _get_mps_current_code(bdf) 
    return rb == code 

# ===== 主函数：为所有 GPU 配置 MPS ===== 
def set_max_payload(value_code: int) -> int: 
    """ 
    为系统中所有 GPU 及其链路上的所有 PCIe 设备设置 MaxPayload。 
    - value_code: 0..5，分别为 128/256/512/1024/2048/4096B 
    规则： 
      1) 在配置前检查该 GPU 的整条链路(仅包含具备 PCIe Cap 的设备)之 MPS Cap 最小值； 
      2) 如果请求值 > 链路最小 Cap，则跳过该 GPU（不做任何写入），报告错误； 
      3) 否则将链路上的每个设备的 MPS 都设置为请求值。 
    返回：0 全部成功；非 0 表示存在失败或被跳过的 GPU。 
    """ 
    # 兼容传入字符串 
    try: 
        code = int(value_code) 
    except Exception: 
        print(f"Invalid MPS code: {value_code}. Valid: 0..5") 
        return 2 

    if code not in _MPS_CODE_TO_BYTES: 
        print(f"Invalid MPS code: {value_code}. Valid: 0..5") 
        return 2 

    req_bytes = _MPS_CODE_TO_BYTES[code] 
    print(f"Setting GPU MaxPayload to {req_bytes} bytes... (requires root)") 

    gpu_lines = get_lspci_gpu_list()  # 已实现：返回包含 BDF 的字符串行 
    gpu_bdfs = [line.split()[0] for line in gpu_lines if line.strip()] 
    if not gpu_bdfs: 
        print("No GPU devices found.") 
        return 1 

    overall_ok = True 

    for gpu in gpu_bdfs: 
        print(f"\nConfiguring GPU {gpu}:") 
        path: Optional[List[str]] = get_pci_path_to_root(gpu)  # 已实现 
        if not path: 
            print(f"  Error: cannot get PCIe path for {gpu}") 
            overall_ok = False 
            continue 

        # 仅保留具备 PCIe 能力的设备（排除 Host Bridge 等没有 PCIe Cap 的 BDF） 
        devs = [d for d in path if _has_pcie_cap(d)] 
        if not devs: 
            print("  Error: no PCIe-capable devices found on the path; skip.") 
            overall_ok = False 
            continue 

        # 读取链路上每个设备的 MPS Cap（编码值），求最小 
        caps: List[int] = [] 
        for d in devs: 
            cap_code = _get_mps_cap_code(d) 
            if cap_code is None: 
                print(f"  Warning: skip {d} (no valid PCIe Cap or read failed)") 
                continue 
            caps.append(cap_code) 

        if not caps: 
            print("  Error: could not read MPS Cap on any device in the path; skip.") 
            overall_ok = False 
            continue 

        min_cap_code = min(caps) 
        link_max_bytes = _MPS_CODE_TO_BYTES[min_cap_code] 
        print(f"  Link supports maximum MaxPayload={link_max_bytes}") 

        # 若请求值超过链路可支持的最大值：直接跳过该 GPU，不做写入 
        if code > min_cap_code: 
            print(f"  Requested {req_bytes}B > link max {link_max_bytes}B; " 
                  f"skip configuration for this GPU.") 
            overall_ok = False 
            continue 

        # 正式配置：对链路上所有设备写入相同的 MPS 
        print("  Writing MPS on devices:") 
        ok_all = True 
        for d in devs: 
            ok = _set_mps_code(d, code) 
            cur_code = _get_mps_current_code(d) 
            cur_bytes = _MPS_CODE_TO_BYTES[cur_code] if cur_code is not None else None 
            if ok: 
                print(f"    {d}: OK, current MaxPayload={cur_bytes}") 
            else: 
                print(f"    {d}: FAILED, current MaxPayload={cur_bytes}") 
                ok_all = False 

        overall_ok = overall_ok and ok_all 

    return 0 if overall_ok else 2

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="A tool that can diagnose and resolve issues of p2p, d2h and h2d blockage or slowdown.")
    parser.add_argument('--topo', action='store_true', help='AI card P2P topology.')
    parser.add_argument('-l', '--list', action='store_true', help='List GPU.')
    parser.add_argument('--trace', action='store_true', help='Identify the factors causing p2p, d2h and h2d blockage or slowdown.')
    parser.add_argument('--enable-acs', action='store_true', help='Enable ACS.')
    parser.add_argument('--disable-acs', action='store_true', help='Disable ACS.')
    parser.add_argument('--enable-extend', action='store_true', help='Enable the PCIe extend capability.')
    parser.add_argument('--set-mps', type=str, help='Set GPU MaxPayload.(E.g., 0: 128B; 1: 256B; 2: 512B; 3: 1024B; 4: 2048B; 5: 4096B.)')
    parser.add_argument('--set-mrrs', type=str, help='Set GPU MaxReadReq.(E.g., 0: 128B; 1: 256B; 2: 512B; 3: 1024B; 4: 2048B; 5: 4096B.)')
    parser.add_argument('--set-timeoutDis', type=str, help='Set GPU And RC Completion Timeout Disable.(E.g., 0: disable; 1: enable.)')

    timeoutRange_helptext = """Set GPU and RC Completion Timeout Range.
Valid options are:
  Default: Default Range (40ms~50ms@FM, 50us~50ms@NFM)
  A_1:     Range A (50us~100us)
  A_2:     Range A (1ms~10ms)
  B_1:     Range B (16ms~55ms)
  B_2:     Range B (65ms~210ms)
  C_1:     Range C (260ms~900ms)
  C_2:     Range C (1s~3.5s)
  D_1:     Range D (4s~13s)
  D_2:     Range D (17s~64s)"""
    parser.add_argument('--set-timeoutRange', type=str, help=timeoutRange_helptext)

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
    elif args.set_timeoutRange:
        set_completion_timeout_range(args.set_timeoutRange)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()