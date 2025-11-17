#!/bin/bash

#================================================================
#
#          FILE: server_info_collect.sh
#
#         USAGE: ./server_info_collect.sh
#
#   DESCRIPTION: Collect comprehensive server information for comparison,
#                with robust IOMMU/SMMU status check.
#
#       OPTIONS: ---
#  REQUIREMENTS: dmidecode, lspci, ethtool, docker, tuned-adm
#          BUGS: ---
#         NOTES: Run this script with sudo/root privileges for full access.
#        AUTHOR: zha0jf
#  ORGANIZATION: Skysolidiss
#       CREATED: 2025-08-13
# LAST MODIFIED: 2025-11-17
#      REVISION: 1.0
#
#================================================================

# 定义全局变量
AI_CARD_KEYWORDS="10de:|19e5:|1fbd:|9999:|1e3e:|1faa:|1e27:|1ed5:"

# Output file
OUTPUT_FILE="server_info_$(hostname)_$(date +%Y%m%d).txt"

# Redirect all output to a log file and stdout
exec &> >(tee -a "$OUTPUT_FILE")

echo "============================================================"
echo "          Server Information Collection Script"
echo "============================================================"
echo "Report generated on: $(date)"
echo "Hostname: $(hostname)"
echo ""

# Function to print a section header
print_header() {
    echo ""
    echo "############################################################"
    echo "#"
    echo "#  $1"
    echo "#"
    echo "############################################################"
    echo ""
}


# --- Hardware Information ---

print_header "1. Hardware Information"

print_header "1.1 CPU Information"
lscpu

print_header "1.2 AI Accelerator Card Information"
echo ">>> Attempting to find AI card vendor tools..."
# Check for all supported AI card vendor tools
if command -v nvidia-smi &> /dev/null; then
    echo "Found NVIDIA SMI tool."
    nvidia-smi
    nvidia-smi -q
elif command -v npu-smi &> /dev/null; then
    echo "Found Huawei NPU SMI tool."
    npu-smi info
elif command -v ersmi &> /dev/null; then
    echo "Found Enrigin GPU SMI tool."
    ersmi info
elif command -v mx-smi &> /dev/null; then
    echo "Found MetaX GPU SMI tool."
    mx-smi
elif command -v mthreads-gmi &> /dev/null; then
    echo "Found Moore Threads GPU SMI tool."
    mthreads-gmi
elif command -v ixsmi &> /dev/null; then
    echo "Found Iluvatar GPU SMI tool."
    ixsmi
elif command -v hxsmi &> /dev/null; then
    echo "Found Hexaflake GPU SMI tool."
    hxsmi
elif command -v dlsmi &> /dev/null; then
    echo "Found Denglin GPU SMI tool."
    dlsmi
else
    echo "!!! AI card vendor tool not found. !!!"
fi

echo ""
echo ">>> Finding AI Card PCI Address for detailed checks..."
AI_CARD_ADDRESSES=$(lspci -nn | grep -iE "$AI_CARD_KEYWORDS" | grep -v -i "audio" | awk '{print $1}')

if [ -n "$AI_CARD_ADDRESSES" ]; then
    for addr in $AI_CARD_ADDRESSES; do
        echo "--- Detailed PCI info for AI Card at $addr ---"
        sudo lspci -vvs "$addr"
        echo ""
    done
else
    echo "!!! Could not automatically identify AI Card PCI address. !!!"
fi

print_header "1.3 Memory (RAM) Information"
sudo dmidecode -t memory

print_header "1.4 Motherboard Information"
sudo dmidecode -t baseboard

print_header "1.5 BIOS/UEFI Information"
sudo dmidecode -t bios

print_header "1.6 Storage Information"
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL
echo ""
df -hT

print_header "1.7 Network Information"
ip -c a
echo ""
lspci | grep -i ethernet
echo ""
for iface in $(ip -o link show | awk -F': ' '{print $2}' | grep -v 'lo'); do
    echo "--- Ethtool for $iface ---"
    ethtool "$iface"
    echo ""
done


# --- Software Information ---

print_header "2. Software Information"

print_header "2.1 Operating System"
cat /etc/os-release
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"

print_header "2.2 Compiler and Libc Version"
gcc --version
echo ""
ldd --version

print_header "2.3 AI-related Libraries (Example Check)"
if command -v python3 &> /dev/null; then
    echo ">>> Checking Python AI Libraries (if installed)..."
    python3 -c "
try:
    import torch; print(f'PyTorch version: {torch.__version__}')
    if torch.cuda.is_available(): print(f'PyTorch CUDA version: {torch.version.cuda}')
except ImportError: print('PyTorch not found.')
try:
    import tensorflow as tf; print(f'TensorFlow version: {tf.__version__}')
except ImportError: print('TensorFlow not found.')
"
fi

print_header "2.4 Docker Version"
if command -v docker &> /dev/null; then
    docker --version; echo ""; docker info
else
    echo "Docker command not found."
fi

print_header "2.5 Tuned Profile Information"
if command -v tuned-adm &> /dev/null; then
    echo ">>> Active Tuned Profile"; tuned-adm active; echo ""; echo ">>> Available Tuned Profiles"; tuned-adm list
else
    echo "tuned-adm command not found."
fi

print_header "2.6 IOMMU/SMMU Status"
echo "--- Definitive Status Check via /sys ---"
if [ -d /sys/class/iommu ] && [ -n "$(ls -A /sys/class/iommu)" ]; then
    echo "IOMMU/SMMU Status: 开启 (Enabled)"
    echo "Active IOMMU groups:"
    ls -l /sys/class/iommu/
    echo ""

    if [ -n "$AI_CARD_ADDRESSES" ]; then
        echo "Checking AI Card attachment to IOMMU..."
        for addr in $AI_CARD_ADDRESSES; do
            if [ -L "/sys/bus/pci/devices/$addr/iommu" ]; then
                echo "  - AI Card at $addr is ATTACHED to IOMMU group: $(readlink /sys/bus/pci/devices/$addr/iommu)"
            else
                echo "  - AI Card at $addr is NOT attached to IOMMU."
            fi
        done
    else
        echo "Could not check AI card attachment (PCI address not found)."
    fi
else
    echo "IOMMU/SMMU Status: 关闭 (Disabled)"
    echo "Reason: /sys/class/iommu directory does not exist or is empty."
fi
echo ""
echo "--- Contextual Information ---"
echo "Kernel Command Line:"
cat /proc/cmdline
echo ""
echo ""
echo "Related dmesg logs:"
dmesg | grep -i -E 'IOMMU|SMMU|DMAR|IVHD' || echo "No IOMMU/SMMU related messages found in dmesg."

print_header "2.7 Kernel Boot Parameters"
cat /proc/cmdline

print_header "2.8 System Control Parameters (sysctl)"
sysctl -a

print_header "2.9 Environment Variables"
echo "--- System-wide Environment (/etc/environment) ---"
cat /etc/environment
echo ""
echo "--- Root User Environment (for sudo execution) ---"
env

# --- Firmware and Dynamic Information ---

print_header "3. Firmware & Dynamic Info"

print_header "3.1 DMI Decode Full Dump"
sudo dmidecode

echo ""
echo "============================================================"
echo "          Script Finished"
echo "============================================================"
echo "Output has been saved to: $OUTPUT_FILE"
