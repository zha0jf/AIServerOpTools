#!/bin/bash

#================================================================
#
#          FILE: ai-server-checklist.sh
#
#         USAGE: sudo ./ai-server-checklist.sh [markdown]
#
#   DESCRIPTION: Collects AI server info. Supports standard and
#                Markdown output formats. For AI servers, a
#                disabled IOMMU/SMMU is the expected state.
#
#  REQUIREMENTS: dmidecode, lspci, ethtool, docker, tuned-adm, gcc
#          BUGS: ---
#         NOTES: Run with sudo/root privileges.
#        AUTHOR: Zha0jf
#  ORGANIZATION: Skysolidiss
#       CREATED: 2025-08-17
#      REVISION: 2.1
#
#================================================================

# --- 模式和初始设置 ---

# 1. 检查Root权限
if [[ $EUID -ne 0 ]]; then
   echo "错误: 此脚本必须以root权限运行。请使用 'sudo ./ai-server-checklist.sh'"
   exit 1
fi

# 2. 设置输出模式
OUTPUT_MODE="standard"
if [[ "$1" == "markdown" ]]; then
    OUTPUT_MODE="markdown"
fi

# 3. 定义输出文件
if [ "$OUTPUT_MODE" == "markdown" ]; then
    OUTPUT_FILE="ai_checklist_$(hostname)_$(date +%Y%m%d).md"
else
    OUTPUT_FILE="ai_checklist_$(hostname)_$(date +%Y%m%d).txt"
fi

# 4. 定义颜色和Markdown表情符号
# 标准模式颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
# Markdown模式符号
MD_GREEN="✅"
MD_RED="❌"
MD_YELLOW="⚠️"

# 5. 重定向所有输出
exec &> >(tee -a "$OUTPUT_FILE")

# 6. 全局变量定义
AI_CARD_KEYWORDS="NVIDIA|10de:|Huawei|19e5:|Enrigin|1fbd:|MetaX|9999:|Iluvatar|1e3e:|Hexaflake|1faa:"
IF_KEYWORDS="Intel|8086:|Mellanox|15b3:|MUCSE|8848:|Wangxun|8088:|Corigine|1da8:|Nebula|1f0f:|metaScale|1f67:"
IP_LINK_FILTER="lo|vir|kube|cali|tunl|docker|veth|br-"

# --- 输出抽象函数 ---

# H1 大标题
print_h1() {
    if [ "$OUTPUT_MODE" == "markdown" ]; then
        echo -e "\n# $1"
    else
        echo -e "\n############################################################"
        echo "# $1"
        echo "############################################################"
    fi
    echo ""
}

# H2 小节标题
print_h2() {
    if [ "$OUTPUT_MODE" == "markdown" ]; then
        echo -e "\n## $1"
    else
        echo -e "\n--- $1 ---"
    fi
}

# H3 子章节标题
print_h3() {
    if [ "$OUTPUT_MODE" == "markdown" ]; then
        echo -e "\n### $1"
    else
        echo -e "\n--- $1 ---"
    fi
}

# 键值对
print_kv() {
    local key="$1"
    local value="$2"
    if [ "$OUTPUT_MODE" == "markdown" ]; then
        echo "**${key}:** ${value}"
    else
        echo "${key}: ${value}"
    fi
}

# 状态 (成功/失败/警告)
print_status() {
    local key="$1"
    local status="$2"
    local type="$3" # "ok", "error", "warn"
    if [ "$OUTPUT_MODE" == "markdown" ]; then
        local symbol=$MD_YELLOW
        [ "$type" == "ok" ] && symbol=$MD_GREEN
        [ "$type" == "error" ] && symbol=$MD_RED
        echo "**${key}:** ${symbol} ${status}"
    else
        local color=$YELLOW
        [ "$type" == "ok" ] && color=$GREEN
        [ "$type" == "error" ] && color=$RED
        echo -e "${key}: ${color}${status}${NC}"
    fi
}

# 代码块
print_code() {
    local lang="$1"
    shift
    local content="$@"
    if [ "$OUTPUT_MODE" == "markdown" ]; then
        echo -e "\`\`\`${lang}\n${content}\n\`\`\`"
    else
        echo -e "${content}"
    fi
}


# --- 脚本主流程 ---

if [ "$OUTPUT_MODE" == "markdown" ]; then
    echo "# AI 服务器配置检查清单"
    echo "> **主机名:** $(hostname)  "
    echo "> **报告生成于:** $(date)"
else
    echo "============================================================"
    echo "           AI 服务器配置检查清单脚本"
    echo "============================================================"
    echo "报告生成于: $(date)"
    echo "主机名: $(hostname)"
fi


# --- 第1部分: 硬件信息 ---
print_h1 "第1部分: 硬件信息"

print_h2 "1.1 CPU 信息"
print_kv "CPU 架构" "$(LC_ALL=C lscpu | grep "Architecture:" | awk '{print $2}')"
print_kv "CPU 型号" "$(LC_ALL=C lscpu | grep "Model name:" | sed 's/Model name: *//')"
print_kv "CPU 主频 (Max)" "$(LC_ALL=C lscpu | grep "CPU max MHz:" | awk '{print $4 " MHz"}')"

print_h2 "1.2 内存信息"
TOTAL_MEM=$(grep MemTotal /proc/meminfo | awk '{printf "%.2f GiB", $2/1024/1024}')
MEM_STICKS=$(dmidecode -t memory | grep -c "Volatile Size: .*[GM]B")
print_kv "内存总量" "$TOTAL_MEM"
print_kv "物理内存条数" "$MEM_STICKS"

# 获取内存类型和有效速率
MEM_TYPE=$(dmidecode -t memory | grep "DDR" | head -1 | awk '{print $2}')
MEM_SPEED=$(dmidecode -t memory | grep "Configured Memory Speed:" | head -1 | awk '{print $4, $5}')
print_kv "内存类型" "$MEM_TYPE"
print_kv "内存有效速率" "$MEM_SPEED"

# 只输出一条内存容量信息
MEM_SIZE=$(dmidecode -t memory | grep "Size:" | grep -v "No Module Installed" | head -1 | awk '{print $2, $3}')
print_kv "单条内存容量" "$MEM_SIZE"

print_h2 "1.3 主板信息"
print_code "text" "$(dmidecode -t baseboard | grep -E "Manufacturer:|Product Name:|Serial Number:" | sed 's/^[ \t]*//')"

print_h2 "1.4 BIOS/UEFI 信息"
print_code "text" "$(dmidecode -t bios | grep -E "Vendor:|Version:|Release Date:" | sed 's/^[ \t]*//')"

print_h2 "1.5 存储信息"
SYSTEM_DISK_PART=$(df / | awk 'NR==2 {print $1}')
SYSTEM_DISK=$(lsblk -no pkname "$SYSTEM_DISK_PART" 2>/dev/null || echo "$SYSTEM_DISK_PART" | sed 's/[0-9]*$//' | sed 's/p$//')
print_h2 "系统盘信息"
print_code "text" "$(lsblk -d -o NAME,MODEL,SIZE,TYPE | grep -w "$SYSTEM_DISK")"
print_h2 "数据盘信息"
print_code "text" "$(lsblk -d -o NAME,MODEL,SIZE,TYPE,ROTA | grep -v "NAME" | grep -v "$SYSTEM_DISK")\n(注: ROTA列为0表示SSD/NVMe, 1表示HDD)"

print_h2 "1.6 网卡信息"
print_h3 "物理网卡型号 (from lspci)"
# 获取物理网卡列表
NETWORK_CARDS=$(lspci -nn | grep -iE "$IF_KEYWORDS")
if [ -n "$NETWORK_CARDS" ]; then
    # 逐个处理每个网卡
    while IFS= read -r line; do
        # 打印网卡信息
        print_code "sh" "$line"
        
        # 提取PCI地址
        addr=$(echo "$line" | awk '{print $1}')
        
        # 获取网卡详细信息
        CARD_DETAILS=$(lspci -vvs $addr 2>/dev/null)
        if [ -n "$CARD_DETAILS" ]; then
            # 检查驱动
            DRIVER=$(echo "$CARD_DETAILS" | grep "Kernel driver in use:" | awk -F': ' '{print $2}')
            if [ -n "$DRIVER" ]; then
                print_kv "加载驱动" "$DRIVER"
            else
                print_status "加载驱动" "未加载驱动" "warn"
            fi
        else
            print_status "详细信息" "无法获取" "error"
        fi
        
        # 输出空行以提高可读性
        echo ""
        
    done <<< "$NETWORK_CARDS"
else
    print_status "物理网卡" "未检测到物理网卡" "warn"
fi
for iface in $(ip -o link show | awk -F': ' '{print $2}' | grep -v -E "$IP_LINK_FILTER"); do
    print_h3 "网卡接口: $iface"
    STATE=$(ip a show "$iface" 2>/dev/null | grep 'state' | awk '{print $9}')
    if [ "$STATE" == "UP" ]; then
        print_status "状态" "激活 (UP)" "ok"
        IP_INFO=$(ip -4 a show "$iface" 2>/dev/null | grep 'inet' | awk '{print "  - IPv4: " $2}')
        IP_INFO+="\n"
        IP_INFO+=$(ip -6 a show "$iface" 2>/dev/null | grep 'inet6' | awk '{print "  - IPv6: " $2}')
        print_kv "IP 地址" "$IP_INFO"
        print_kv "带宽 (协商速率)" "$(ethtool "$iface" 2>/dev/null | grep Speed | sed 's/^[ \t]*//')"
    else
        print_status "状态" "未激活 (DOWN)" "error"
    fi
done

print_h2 "1.7 硬件拓扑信息 (lspci -vt)"
print_code "sh" "$(lspci -vt)"

print_h2 "1.8 AI卡状态"
if command -v nvidia-smi &> /dev/null; then
    print_code "sh" "检测到 NVIDIA GPU 卡\n$(nvidia-smi)"
    print_code "sh" "NVIDIA GPU 拓扑矩阵\n$(nvidia-smi topo -m)"

elif command -v npu-smi &> /dev/null; then
    print_code "sh" "检测到 Huawei NPU 卡\n$(npu-smi info)"
    print_code "sh" "Huawei NPU 拓扑信息\n$(npu-smi info -t 2>/dev/null || echo '拓扑命令无法执行或不支持')"
elif command -v ersmi &> /dev/null; then
    print_code "sh" "检测到 Enrigin GPU 卡\n$(ersmi)"
    print_code "sh" "Enrigin GPU 拓扑信息\n$(ersmi --topo)"
elif command -v mx-smi &> /dev/null; then
    print_code "sh" "检测到 MetaX GPU 卡\n$(mx-smi)"
    print_code "sh" "MetaX GPU 拓扑信息\n$(mx-smi topo -m)"
elif command -v ixsmi &> /dev/null; then
    print_code "sh" "检测到 Iluvatar GPU 卡\n$(ixsmi)"
    print_code "sh" "Iluvatar GPU 拓扑信息\n$(ixsmi topo -m)"
elif command -v hxsmi &> /dev/null; then
    print_code "sh" "检测到 Hexaflake GPU 卡\n$(hxsmi)"
    print_code "sh" "Hexaflake GPU 拓扑信息\n$(hxsmi topo  2>/dev/null || echo '不支持拓扑命令')"
else
    print_status "AI卡状态" "未找到主流AI卡管理工具 (nvidia-smi, npu-smi, ersmi, mx-smi, ixsmi, hxsmi)" "warn"
fi

print_h2 "1.9 AI卡详细信息 (lspci)"
# 获取AI卡的PCI地址
AI_CARD_ADDRESSES=$(lspci -nn | grep -iE "$AI_CARD_KEYWORDS" | awk '{print $1}')
if [ -n "$AI_CARD_ADDRESSES" ]; then
    for addr in $AI_CARD_ADDRESSES; do
        print_h3 "AI卡 (PCI地址: $addr)"
        # 使用lspci -vvs获取详细信息
        CARD_DETAILS=$(lspci -vvs $addr 2>/dev/null)
        if [ -n "$CARD_DETAILS" ]; then
            # 检查PCIE带宽是否降级
            LNKCAP=$(echo "$CARD_DETAILS" | grep "LnkCap:" | sed 's/^[ \t]*//')
            LNKSTA=$(echo "$CARD_DETAILS" | grep "LnkSta:" | sed 's/^[ \t]*//')
            print_kv "PCIE链路能力" "$LNKCAP"
            print_kv "PCIE链路状态" "$LNKSTA"
            
            # 检查驱动
            DRIVER=$(echo "$CARD_DETAILS" | grep "Kernel driver in use:" | awk -F': ' '{print $2}')
            if [ -n "$DRIVER" ]; then
                print_kv "加载驱动" "$DRIVER"
            else
                print_status "加载驱动" "未找到" "warn"
            fi
            
            # 检查PCIE ASPM配置
            ASPM_CONFIG=$(echo "$CARD_DETAILS" | grep "LnkCtl:.*ASPM" | sed 's/^[ \t]*//')
            if [ -n "$ASPM_CONFIG" ]; then
                print_kv "PCIE ASPM配置" "$ASPM_CONFIG"
            else
                print_kv "PCIE ASPM配置" "未找到相关信息"
            fi
            
            # 检查Completion Timeout配置 (支持配置在DevCap2中，生效配置在DevCtl2中)
            COMPLETION_TIMEOUT_SUPPORTED=$(echo "$CARD_DETAILS" | grep -E "DevCap2:.*Completion Timeout: Range [A-Z]+, TimeoutDis\+" | sed 's/^[ \t]*//')
            # 生效配置在DevCtl2中 (只需检测是否同时存在DevCtl2:、Completion Timeout:和TimeoutDis)
            COMPLETION_TIMEOUT_ENABLED=$(echo "$CARD_DETAILS" | grep -E "DevCtl2:.*Completion Timeout:.*TimeoutDis[+-]" | sed 's/^[ \t]*//')
            if [ -n "$COMPLETION_TIMEOUT_SUPPORTED" ]; then
                print_kv "Completion Timeout支持" "$COMPLETION_TIMEOUT_SUPPORTED"
            else
                print_kv "Completion Timeout支持" "未找到相关信息"
            fi
            if [ -n "$COMPLETION_TIMEOUT_ENABLED" ]; then
                print_kv "Completion Timeout生效配置" "$COMPLETION_TIMEOUT_ENABLED"
                
                # 检查延迟检测状态
                if echo "$COMPLETION_TIMEOUT_ENABLED" | grep -q "TimeoutDis-"; then
                    TIMEOUT_STATUS="开启"
                elif echo "$COMPLETION_TIMEOUT_ENABLED" | grep -q "TimeoutDis+"; then
                    TIMEOUT_STATUS="关闭"
                else
                    TIMEOUT_STATUS="未知"
                fi
                
                # 获取CPU型号并判断是否为5000+系列
                CPU_MODEL=$(LC_ALL=C lscpu | grep "Model name:" | sed 's/Model name: *//')
                if echo "$CPU_MODEL" | grep -q "5000" && [ "$TIMEOUT_STATUS" = "关闭" ]; then
                    print_status "PCIE延迟检测" "已关闭" "ok"
                elif echo "$CPU_MODEL" | grep -q "5000" && [ "$TIMEOUT_STATUS" = "开启" ]; then
                    print_status "PCIE延迟检测" "FT5000C CPU不支持延迟检测阈值调整，必要时建议关闭" "warn"
                fi
            else
                print_kv "Completion Timeout生效配置" "未找到相关信息"
            fi
            
            # 检查MaxPayload配置 (遵循lspci惯例: 支持配置在devcap中，生效配置直接搜索特定格式行)
            MAX_PAYLOAD_SUPPORTED=$(echo "$CARD_DETAILS" | grep -i "devcap" | grep -i "MaxPayload" | sed 's/^[ \t]*//')
            # 直接搜索包含MaxPayload和MaxReadReq的行作为生效配置
            MAX_PAYLOAD_ENABLED=$(echo "$CARD_DETAILS" | grep -E "MaxPayload [0-9]+ bytes, MaxReadReq [0-9]+ bytes" | sed 's/^[ \t]*//') 
            if [ -n "$MAX_PAYLOAD_SUPPORTED" ]; then
                print_kv "MaxPayload支持" "$MAX_PAYLOAD_SUPPORTED"
            else
                print_kv "MaxPayload支持" "未找到相关信息"
            fi
            if [ -n "$MAX_PAYLOAD_ENABLED" ]; then
                print_kv "MaxPayload生效配置" "$MAX_PAYLOAD_ENABLED"
            else
                print_kv "MaxPayload生效配置" "未找到相关信息"
            fi
        else
            print_status "详细信息" "无法获取" "error"
        fi
    done
else
    print_status "AI卡详细信息" "未检测到AI卡" "warn"
fi


# --- 第2部分: 软件信息 ---
print_h1 "第2部分: 软件信息"

print_h2 "2.1 操作系统"
print_code "sh" "$(cat /etc/os-release)"
print_kv "当前运行内核" "$(uname -r)"

print_h2 "2.2 编译器 (GCC) 和 Glibc (ldd) 版本"
print_h3 "GCC Version"
if command -v gcc &> /dev/null; then
    print_kv "GCC Version" "$(gcc --version | head -n1 | awk '{print $NF}')"
else
    print_status "GCC" "未安装" "error"
fi
print_h3 "Glibc (ldd) Version"
if command -v ldd &> /dev/null; then
    print_kv "Glibc (ldd) Version" "$(ldd --version | head -n1 | awk '{print $NF}')"
else
    print_status "Glibc (ldd)" "未找到" "error"
fi

print_h2 "2.3 Docker 版本"
if command -v docker &> /dev/null; then
    print_kv "Docker Version" "$(docker --version)"
    
    # 检查 docker-compose 命令
    if command -v docker-compose &> /dev/null; then
        print_kv "Docker Compose Version (docker-compose)" "$(docker-compose --version)"
    else
        print_status "Docker Compose Version (docker-compose)" "未安装" "warn"
    fi
    
    # 检查 docker compose 命令
    if docker compose version &> /dev/null; then
        print_kv "Docker Compose Version (docker compose)" "$(docker compose version)"
    else
        print_status "Docker Compose Version (docker compose)" "未安装" "warn"
    fi
else
    print_status "Docker" "未安装" "warn"
fi

print_h2 "2.4 Tuned 性能调优配置"
if command -v tuned-adm &> /dev/null; then
    print_kv "当前激活的Tuned Profile" "$(tuned-adm active | cut -d ' ' -f 4)"
else
    print_status "Tuned" "未安装" "warn"
fi

print_h2 "2.5 IOMMU/SMMU 状态"
# *** MODIFIED LOGIC: For AI servers, DISABLED is the desired state (OK). ***
if [ -d /sys/class/iommu ] && [ -n "$(ls -A /sys/class/iommu)" ]; then
    # IOMMU IS ENABLED - This is now considered an ERROR for AI servers.
    print_status "IOMMU/SMMU 状态" "已开启 (Enabled) - AI服务器通常要求关闭" "error"
    
    # 使用更有限的关键词集来检查IOMMU绑定状态
    IOMMU_AI_CARD_KEYWORDS="NVIDIA|10de:|Huawei|19e5:|Enrigin|1fbd:"
    AI_CARD_ADDRESSES=$(lspci -nn | grep -iE "$IOMMU_AI_CARD_KEYWORDS" | awk '{print $1}')
    if [ -n "$AI_CARD_ADDRESSES" ]; then
        print_h3 "AI 卡与 IOMMU 绑定状态 (诊断信息)"
        for addr in $AI_CARD_ADDRESSES; do
            if [ -L "/sys/bus/pci/devices/0000:$addr/iommu" ]; then
                GROUP=$(readlink "/sys/bus/pci/devices/0000:$addr/iommu" | rev | cut -d'/' -f1 | rev)
                print_status "AI卡 (PCI地址 ${addr})" "已绑定到 IOMMU 组 ${GROUP}" "warn"
            else
                print_status "AI卡 (PCI地址 ${addr})" "未绑定到 IOMMU" "ok"
            fi
        done
    fi
else
    # IOMMU IS DISABLED - This is the desired state.
    print_status "IOMMU/SMMU 状态" "已关闭 (Disabled) - 符合AI服务器配置要求" "ok"
fi
print_h2 "2.6 内核启动参数"
print_kv "内核启动参数" "$(cat /proc/cmdline)"

print_h2 "2.7 内核版本一致性 (Kernel vs Devel/Headers)"
CURRENT_KERNEL=$(uname -r)
print_kv "当前运行内核" "$CURRENT_KERNEL"
if command -v dpkg &> /dev/null; then # Debian/Ubuntu
    MATCHING_HEADERS=$(dpkg-query -W -f='${Status}\n' "linux-headers-${CURRENT_KERNEL}" 2>/dev/null | grep "install ok installed")
    if [ -n "$MATCHING_HEADERS" ]; then
        print_status "内核头文件 (linux-headers)" "已安装, 版本匹配" "ok"
    else
        print_status "内核头文件 (linux-headers)" "未安装或版本不匹配! (编译驱动程序可能失败)" "error"
    fi
elif command -v rpm &> /dev/null; then # RHEL/CentOS
    if rpm -q "kernel-devel-${CURRENT_KERNEL}" > /dev/null; then
        print_status "内核开发包 (kernel-devel)" "已安装, 版本匹配" "ok"
    else
        print_status "内核开发包 (kernel-devel)" "未安装或版本不匹配! (编译驱动程序可能失败)" "error"
    fi
else
    print_status "内核版本一致性检查" "无法确定包管理器, 跳过" "warn"
fi


if [ "$OUTPUT_MODE" == "markdown" ]; then
    echo -e "\n---\n*报告由 ai-server-checklist.sh 生成*"
else
    echo ""
    echo "============================================================"
    echo "          检查清单脚本执行完毕"
    echo "============================================================"
fi
echo "输出已保存至文件: $OUTPUT_FILE"