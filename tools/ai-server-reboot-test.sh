#!/bin/bash

#================================================================
#
#          FILE: ai-server-reboot-test.sh
#
#         USAGE: sudo ./ai-server-reboot-test.sh [OPTIONS] <重启次数>
#
#   DESCRIPTION: 自动进行指定次数的重启测试，每次重启后验证AI卡
#                的识别状态。支持多种AI卡厂商(NVIDIA, Huawei,
#                Enrigin, MetaX, Iluvatar, Hexaflake)。
#                检查系统所有AI卡的链路带宽和运行状态。
#                支持reboot和IPMI reset两种重启方式。
#
#       OPTIONS: -r, --reboot         使用reboot命令重启 (默认)
#                -i, --ipmi           使用IPMI reset重启
#                -c, --card VENDOR    指定检查的AI卡厂商
#                -h, --help           显示帮助信息
#
#      EXAMPLES: ./ai-server-reboot-test.sh -r 5
#                ./ai-server-reboot-test.sh -i -c NVIDIA 3
#
#  REQUIREMENTS: lspci, systemctl, ipmitool (for IPMI mode),
#                AI card management tools (nvidia-smi, ersmi, etc.)
#          BUGS: ---
#         NOTES: 需要root权限运行。测试进度会自动保存，支持断点续传。
#                日志保存在 /root/ai_reboot_test.log
#        AUTHOR: zha0jf
#  ORGANIZATION: Skysolidiss
#       CREATED: 2025-09-02
#      REVISION: 1.0
#
#================================================================

# 有序的厂商列表（用于序号映射和帮助信息）
VENDOR_LIST=("NVIDIA" "Huawei" "Enrigin" "MetaX" "Iluvatar" "Hexaflake")

# 厂商配置信息（包含PCI ID、管理工具、拓扑命令）
declare -A VENDOR_CONFIG=(
    # NVIDIA配置
    ["NVIDIA_PCI"]="10de:"
    ["NVIDIA_TOOL"]="nvidia-smi"
    ["NVIDIA_TOPO"]="nvidia-smi topo -m"
    
    # Huawei配置
    ["Huawei_PCI"]="19e5:"
    ["Huawei_TOOL"]="npu-smi info"
    ["Huawei_TOPO"]="npu-smi info -t --topo"
    
    # Enrigin配置
    ["Enrigin_PCI"]="1fbd:"
    ["Enrigin_TOOL"]="ersmi"
    ["Enrigin_TOPO"]="ersmi --topo"
    
    # MetaX配置
    ["MetaX_PCI"]="9999:"
    ["MetaX_TOOL"]="mx-smi"
    ["MetaX_TOPO"]="mx-smi topo -m"
    
    # Iluvatar配置
    ["Iluvatar_PCI"]="1e3e:"
    ["Iluvatar_TOOL"]="ixsmi"
    ["Iluvatar_TOPO"]="ixsmi topo -m"
    
    # Hexaflake配置
    ["Hexaflake_PCI"]="1faa:"
    ["Hexaflake_TOOL"]="hxsmi"
    ["Hexaflake_TOPO"]="hxsmi topo"
)
# 帮助信息函数
show_help() {
    echo "AI Server Reboot Test Script (with progress save functionality)"
    echo "Function: Automatically perform specified number of reboot tests, verify AI card recognition status after each reboot"
    echo ""
    echo "Usage: $0 [OPTIONS] <reboot_count>"
    echo "Examples: $0 -r 5                  # Reboot 5 times using reboot command"
    echo "          $0 -i -c 1 3            # Reboot 3 times using IPMI reset, check only vendor #1 (${VENDOR_LIST[0]}) cards"
    echo ""
    echo "Options:"
    echo "  -r, --reboot          Use reboot command to restart (default)"
    echo "  -i, --ipmi            Use IPMI reset to restart"
    echo "  -c, --card NUMBER     Specify AI card vendor number to check:"
    
    # 动态生成厂商列表
    for i in "${!VENDOR_LIST[@]}"; do
        echo "                        $((i+1)): ${VENDOR_LIST[i]}"
    done
    
    echo "  -h, --help            Show help information"
    echo ""
    echo "Log file: Test results will be saved to /root/ai_reboot_test.log"
    echo "Progress file: Current test progress saved to /root/ai_test_progress"
    exit 0
}

# 根据序号获取厂商名称
get_vendor_by_number() {
    local number="$1"
    
    if [[ "$number" =~ ^[1-${#VENDOR_LIST[@]}]$ ]]; then
        echo "${VENDOR_LIST[$((number-1))]}"
    else
        echo ""
    fi
}

# 根据厂商名称获取序号
get_number_by_vendor() {
    local vendor="$1"
    
    for i in "${!VENDOR_LIST[@]}"; do
        if [[ "${VENDOR_LIST[i]}" == "$vendor" ]]; then
            echo "$((i+1))"
            return
        fi
    done
    echo ""
}

# 解析参数
REBOOT_TYPE="reboot"  # 默认使用reboot
SPECIFIC_VENDOR=""    # 默认检查所有厂商
TOTAL_REBOOTS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--reboot)
            REBOOT_TYPE="reboot"
            shift
            ;;
        -i|--ipmi)
            REBOOT_TYPE="ipmi"
            shift
            ;;
        -c|--card)
            VENDOR_NUMBER="$2"
            SPECIFIC_VENDOR=$(get_vendor_by_number "$VENDOR_NUMBER")
            if [ -z "$SPECIFIC_VENDOR" ]; then
                echo "Error: Invalid vendor number '$VENDOR_NUMBER', please use numbers between 1-${#VENDOR_LIST[@]}"
                echo "Use -h to view help information"
                exit 1
            fi
            shift 2
            ;;
        -h|--help)
            show_help
            ;;
        *)
            if [[ "$1" =~ ^[0-9]+$ ]]; then
                TOTAL_REBOOTS="$1"
                shift
            else
                echo "Error: Unknown parameter '$1'"
                show_help
                exit 1
            fi
            ;;
    esac
done
# 检查必需参数
if [ -z "$TOTAL_REBOOTS" ]; then
    echo "Error: Missing reboot count parameter"
    show_help
    exit 1
fi

# 注：厂商验证已在参数解析阶段完成

# 文件路径配置
SERVICE_NAME="ai-reboot-test"
LOG_FILE="/root/ai_reboot_test.log"
PROGRESS_FILE="/root/ai_test_progress"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
# 检查lspci命令是否存在
if ! command -v lspci &> /dev/null; then
    echo "Error: lspci command not found, please install pciutils package"
    exit 1
fi

# 如果指定了IPMI重启方式，检查ipmitool是否安装
if [ "$REBOOT_TYPE" = "ipmi" ]; then
    if ! command -v ipmitool &> /dev/null; then
        echo "Error: IPMI reboot mode specified, but ipmitool command not found, please install ipmitool package"
        echo "Or use -r parameter to switch to reboot command restart"
        exit 1
    fi
    echo "Detected ipmitool, will use IPMI reset method to restart"
fi

# 获取AI卡设备列表函数
get_ai_cards() {
    local cards=()
    
    # 使用lspci获取AI卡设备
    while read -r line; do
        # 跳过Audio设备
        if [[ "$line" == *"Audio device"* ]]; then
            continue
        fi
        
        # 检查是否匹配AI卡关键字（忽略大小写）
        for vendor in "${VENDOR_LIST[@]}"; do
            # 检查厂商名称
            if [[ "${line,,}" == *"${vendor,,}"* ]]; then
                cards+=("$line")
                break
            fi
            # 检查PCI ID
            local pci_id="${VENDOR_CONFIG["${vendor}_PCI"]}"
            if [[ -n "$pci_id" && "${line,,}" == *"${pci_id,,}"* ]]; then
                cards+=("$line")
                break
            fi
        done
    done < <(lspci 2>/dev/null)
    
    printf '%s\n' "${cards[@]}"
}

# 检查指定厂商的AI卡状态
check_vendor_cards() {
    local vendor="$1"
    local tool="${VENDOR_CONFIG["${vendor}_TOOL"]}"
    
    if [ -z "$tool" ]; then
        echo "    Management tool for $vendor is not defined"
        return 1
    fi
    
    local tool_name="${tool%% *}"  # 获取命令名
    
    if ! command -v "$tool_name" &> /dev/null; then
        echo "    Warning: $vendor AI card management tool ($tool_name) not installed"
        return 1
    fi
    
    echo "    $vendor AI card status (using $tool_name):"
    if $tool 2>/dev/null; then
        return 0
    else
        echo "      Error: Failed to execute $tool"
        return 1
    fi
}

# 检查AI卡拓扑信息
check_vendor_topology() {
    local vendor="$1"
    local topo_cmd="${VENDOR_CONFIG["${vendor}_TOPO"]}"
    
    if [ -z "$topo_cmd" ]; then
        echo "    Topology command for $vendor is not defined"
        return 1
    fi
    
    local tool_name="${topo_cmd%% *}"  # 获取命令名
    
    if ! command -v "$tool_name" &> /dev/null; then
        echo "    Warning: $vendor AI card management tool ($tool_name) not installed"
        return 1
    fi
    
    echo "    $vendor AI card topology information:"
    if $topo_cmd 2>/dev/null; then
        return 0
    else
        echo "      Error: Failed to execute $topo_cmd"
        return 1
    fi
}

# 初始化或读取进度文件
if [ -f "$PROGRESS_FILE" ]; then
    CURRENT_REBOOT=$(cat $PROGRESS_FILE)
    echo "Detected incomplete test progress: $CURRENT_REBOOT/$TOTAL_REBOOTS"
else
    CURRENT_REBOOT=0
    echo "Initializing new test progress"
    echo $CURRENT_REBOOT > $PROGRESS_FILE

    # 初始化日志文件
    echo "AI Server Reboot Test Log" > $LOG_FILE
    echo "Test start time: $(date)" >> $LOG_FILE
    echo "Total reboots: $TOTAL_REBOOTS" >> $LOG_FILE
    echo "Reboot type: $REBOOT_TYPE" >> $LOG_FILE
    if [ -n "$SPECIFIC_VENDOR" ]; then
        echo "Specified AI card vendor: $SPECIFIC_VENDOR" >> $LOG_FILE
    else
        echo "Check all AI card vendors" >> $LOG_FILE
    fi
    echo "" >> $LOG_FILE
    echo "Test count, Test time:" >> $LOG_FILE
    echo "AI card device information" >> $LOG_FILE
    echo "              Link status" >> $LOG_FILE
    echo "AI card management tool output" >> $LOG_FILE
    echo "AI card topology information" >> $LOG_FILE
    echo "" >> $LOG_FILE
fi

# 创建Systemd服务文件（用于自动重启）
create_service() {
    echo "Creating Systemd service..."
    
    # 构建命令参数
    local cmd_args=""
    if [ "$REBOOT_TYPE" = "ipmi" ]; then
        cmd_args="$cmd_args -i"
    fi
    if [ -n "$SPECIFIC_VENDOR" ]; then
        # 使用函数将厂商名称转换回序号
        local vendor_number=$(get_number_by_vendor "$SPECIFIC_VENDOR")
        cmd_args="$cmd_args -c $vendor_number"
    fi
    cmd_args="$cmd_args $TOTAL_REBOOTS"
    
    sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=AI Server Reboot Test Service
After=network.target

[Service]
Type=simple
ExecStart=$(pwd)/$(basename $0) $cmd_args
Restart=no
User=$USER
WorkingDirectory=$(pwd)

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable ${SERVICE_NAME}.service
    echo "Boot auto-start has been set"
}

# 取消Systemd服务
cancel_service() {
    echo "Canceling auto-restart service..."
    sudo systemctl disable ${SERVICE_NAME}.service
    sudo rm -f $SERVICE_FILE
    sudo systemctl daemon-reload
    rm -f $PROGRESS_FILE
    echo "Auto-restart setting has been canceled"
}

# 执行测试
perform_test() {
    CURRENT_REBOOT=$((CURRENT_REBOOT + 1))
    echo $CURRENT_REBOOT > $PROGRESS_FILE

    echo "Performing test #$CURRENT_REBOOT..."
    
    # 记录测试结果
    echo -e "RUN #$CURRENT_REBOOT  $(date +'%Y-%m-%d %H:%M:%S'):" >> $LOG_FILE
    
    # 获取AI卡设备列表
    ai_cards=$(get_ai_cards)
    
    if [ -z "$ai_cards" ]; then
        echo "Warning: No AI card devices found" | tee -a $LOG_FILE
    else
        echo "AI Card Device List (lspci):" >> $LOG_FILE
        echo "$ai_cards" >> $LOG_FILE
        echo "" >> $LOG_FILE
        
        # 检查PCIe链路状态
        echo "PCIe Link Status:" >> $LOG_FILE
        while IFS= read -r card; do
            if [ -n "$card" ]; then
                # 直接获取每行的第一个字段（PCI地址），兼容两种格式
                pci_address=$(echo "$card" | awk '{print $1}')
                # 验证PCI地址格式是否正确（支持3段式呈4段式）
                if [[ "$pci_address" =~ ^([0-9a-fA-F]{4}:)?[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9]$ ]]; then
                    # 使用PCI地址精确查询单张卡的信息
                    lspci -vvs "$pci_address" | grep -v Subsystem | grep "$pci_address\|LnkCap:\|LnkSta:" >> $LOG_FILE
                fi
            fi
        done <<< "$ai_cards"
        echo "" >> $LOG_FILE
    fi
    
    # 检查指定厂商的AI卡状态
    if [ -n "$SPECIFIC_VENDOR" ]; then
        echo "$SPECIFIC_VENDOR AI Card Status:" >> $LOG_FILE
        check_vendor_cards "$SPECIFIC_VENDOR" >> $LOG_FILE 2>&1
        echo "" >> $LOG_FILE
        
        echo "$SPECIFIC_VENDOR AI Card Topology Information:" >> $LOG_FILE
        check_vendor_topology "$SPECIFIC_VENDOR" >> $LOG_FILE 2>&1
        echo "" >> $LOG_FILE
    else
        # 检查所有厂商的AI卡
        vendors_found=()
        while IFS= read -r card; do
            if [ -n "$card" ]; then
                for vendor in "${VENDOR_LIST[@]}"; do
                    # 检查厂商名称
                    if [[ "${card,,}" == *"${vendor,,}"* ]]; then
                        # 检查是否已经添加过这个厂商
                        if [[ ! " ${vendors_found[@]} " =~ " ${vendor} " ]]; then
                            vendors_found+=("$vendor")
                        fi
                        break
                    fi
                    # 检查PCI ID
                    local pci_id="${VENDOR_CONFIG["${vendor}_PCI"]}"
                    if [[ -n "$pci_id" && "${card,,}" == *"${pci_id,,}"* ]]; then
                        # 检查是否已经添加过这个厂商
                        if [[ ! " ${vendors_found[@]} " =~ " ${vendor} " ]]; then
                            vendors_found+=("$vendor")
                        fi
                        break
                    fi
                done
            fi
        done <<< "$ai_cards"
        
        for vendor in "${vendors_found[@]}"; do
            echo "$vendor AI Card Status:" >> $LOG_FILE
            check_vendor_cards "$vendor" >> $LOG_FILE 2>&1
            echo "" >> $LOG_FILE
            
            echo "$vendor AI Card Topology Information:" >> $LOG_FILE
            check_vendor_topology "$vendor" >> $LOG_FILE 2>&1
            echo "" >> $LOG_FILE
        done
    fi
    
    echo "===========================================" >> $LOG_FILE
    echo "" >> $LOG_FILE
    
    echo "Test #$CURRENT_REBOOT completed."

    if [ $CURRENT_REBOOT -ge $TOTAL_REBOOTS ]; then
        echo "All tests completed!"
        cancel_service
        echo "Test end time: $(date)" >> $LOG_FILE
        exit 0
    else
        if [ "$REBOOT_TYPE" = "ipmi" ]; then
            echo "Preparing to reset system via IPMI..."
            create_service
            sleep 3
            ipmitool power reset
        else
            echo "Preparing to restart system..."
            create_service
            sleep 3
            reboot
        fi
    fi
}

# 主执行逻辑
if [ $CURRENT_REBOOT -eq 0 ]; then
    echo "First run, creating service file..."
    create_service
fi

perform_test
