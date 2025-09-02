# AIServerOpTools

## 项目简介

本项目是一个针对国产AI服务器的运维小工具合集，主要使用Python和Shell开发。这些工具旨在简化AI服务器的日常运维工作，提高运维效率。

## 工具说明

本项目目前包含五个工具：

1. **服务器信息收集工具** (`tools/server_info_collect.sh`)：一个bash脚本，用于收集全面的服务器信息，包括硬件（CPU、AI加速卡、内存、主板、BIOS、存储、网络）和软件（操作系统、编译器、AI库、Docker、调优配置、IOMMU/SMMU状态）的详细信息。它会生成一份详细的报告，用于AI服务器的诊断和对比。

2. **AI服务器检查清单工具** (`tools/ai-server-checklist.sh`)：一个bash脚本，用于对AI服务器进行全面检查，涵盖硬件（CPU、内存、主板、BIOS、存储、网卡、硬件拓扑、AI卡）和软件（操作系统、编译器、glibc、Docker、调优配置、IOMMU/SMMU状态、内核参数）等方面。它支持标准和Markdown两种输出格式，生成详细的报告用于AI服务器诊断和配置验证。

3. **InfiniBand流量监控工具** (`tools/ib_traffic_monitor.py`)：一个Python脚本，用于监控AI服务器上的InfiniBand（RDMA）网络流量。它能够实时显示所有或指定InfiniBand接口的发送和接收速率，帮助诊断网络性能问题。

4. **GPU PCIe调优工具** (`tools/gpu-pcie-tuner.py`)：一个Python脚本，用于诊断和解决GPU P2P、D2H和H2D通信中的阻塞或减速问题。它能够列出GPU设备、显示P2P拓扑结构、追踪问题根源，并提供多种PCIe配置选项，包括启用/禁用ACS、启用PCIe扩展功能、设置MaxPayload、MaxReadReq和Completion Timeout等。

5. **AI服务器重启测试工具** (`tools/ai-server-reboot-test.sh`)：一个bash脚本，用于对AI服务器进行自动化重启测试，具备进度保存功能。它可以进行指定次数的重启循环，每次重启后验证AI卡的识别状态。该工具支持多种AI卡厂商（NVIDIA, Huawei, Enrigin, MetaX, Iluvatar, Hexaflake），检查系统中所有AI卡的链路带宽和运行状态，支持reboot命令和IPMI reset两种重启方式。

## 安装使用

```bash
git clone <repository-url>
cd AIServerOpTools
# 根据具体工具要求安装依赖
```

### AI服务器检查清单工具使用说明

AI服务器检查清单工具 (`tools/ai-server-checklist.sh`) 需要以root权限运行，具有以下使用选项：

```bash
# 以标准格式运行
sudo ./tools/ai-server-checklist.sh

# 以Markdown格式运行
sudo ./tools/ai-server-checklist.sh markdown
```

工具将在当前目录生成报告文件，标准格式命名为 `ai_checklist_<主机名>_<日期>.txt`，Markdown格式命名为 `ai_checklist_<主机名>_<日期>.md`。

### InfiniBand流量监控工具使用说明

InfiniBand流量监控工具 (`tools/ib_traffic_monitor.py`) 需要安装并可访问 `ibstat` 和 `perfquery` 工具。它具有以下使用选项：

```bash
# 以1秒间隔监控所有InfiniBand接口（默认）
python3 ./tools/ib_traffic_monitor.py

# 以自定义间隔监控所有InfiniBand接口
python3 ./tools/ib_traffic_monitor.py -i 2

# 监控指定的InfiniBand接口
python3 ./tools/ib_traffic_monitor.py -I mlx5_0
```

按 `Ctrl+C` 停止监控。

### GPU PCIe调优工具使用说明

GPU PCIe调优工具 (`tools/gpu-pcie-tuner.py`) 需要安装并可访问 `lspci` 和 `setpci` 工具。它具有以下使用选项：

```bash
# 列出GPU设备
python3 ./tools/gpu-pcie-tuner.py -l

# 显示AI卡P2P拓扑
python3 ./tools/gpu-pcie-tuner.py --topo

# 追踪问题根源
python3 ./tools/gpu-pcie-tuner.py --trace

# 启用ACS
sudo python3 ./tools/gpu-pcie-tuner.py --enable-acs

# 禁用ACS
sudo python3 ./tools/gpu-pcie-tuner.py --disable-acs

# 启用PCIe扩展功能
sudo python3 ./tools/gpu-pcie-tuner.py --enable-extend

# 设置GPU MaxPayload为256B
sudo python3 ./tools/gpu-pcie-tuner.py --set-mps 1

# 设置GPU MaxReadReq为512B
sudo python3 ./tools/gpu-pcie-tuner.py --set-mrrs 2

# 设置GPU Completion Timeout Disable为enable
sudo python3 ./tools/gpu-pcie-tuner.py --set-timeoutDis 1

# 设置GPU Completion Timeout Range为A (50 µs – 100 µs)
sudo python3 ./tools/gpu-pcie-tuner.py --set-timeoutRange A_1
```

### AI服务器重启测试工具使用说明

AI服务器重启测试工具 (`tools/ai-server-reboot-test.sh`) 需要以root权限运行，具有以下使用选项：

```bash
# 使用reboot命令进行5次重启测试（默认方式）
sudo ./tools/ai-server-reboot-test.sh -r 5

# 使用IPMI reset进行3次重启测试，仅检查NVIDIA卡
sudo ./tools/ai-server-reboot-test.sh -i -c 1 3

# 检查所有AI卡厂商，进行10次重启测试
sudo ./tools/ai-server-reboot-test.sh 10

# 显示帮助信息
./tools/ai-server-reboot-test.sh -h
```

工具支持以下选项：
- `-r, --reboot`：使用reboot命令重启（默认）
- `-i, --ipmi`：使用IPMI reset重启（需要安装ipmitool）
- `-c, --card NUMBER`：指定检查的AI卡厂商序号（1-6对应不同厂商）
- `-h, --help`：显示帮助信息

工具会自动将测试进度保存到 `/root/ai_test_progress` 文件，所有测试结果记录到 `/root/ai_reboot_test.log` 文件中。支持中断后继续测试，每次重启后都会验证AI卡状态。

## 贡献指南

欢迎提交Issue和Pull Request来改进本项目。

## 许可证

本项目采用MIT许可证。