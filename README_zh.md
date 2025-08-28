# AIServerOpTools

## 项目简介

本项目是一个针对国产AI服务器的运维小工具合集，主要使用Python和Shell开发。这些工具旨在简化AI服务器的日常运维工作，提高运维效率。

## 工具说明

本项目目前包含三个工具：

1. **服务器信息收集工具** (`tools/server_info_collect.sh`)：一个bash脚本，用于收集全面的服务器信息，包括硬件（CPU、AI加速卡、内存、主板、BIOS、存储、网络）和软件（操作系统、编译器、AI库、Docker、调优配置、IOMMU/SMMU状态）的详细信息。它会生成一份详细的报告，用于AI服务器的诊断和对比。

2. **AI服务器检查清单工具** (`tools/ai-server-checklist.sh`)：一个bash脚本，用于对AI服务器进行全面检查，涵盖硬件（CPU、内存、主板、BIOS、存储、网卡、硬件拓扑、AI卡）和软件（操作系统、编译器、glibc、Docker、调优配置、IOMMU/SMMU状态、内核参数）等方面。它支持标准和Markdown两种输出格式，生成详细的报告用于AI服务器诊断和配置验证。

3. **InfiniBand流量监控工具** (`tools/ib_traffic_monitor.py`)：一个Python脚本，用于监控AI服务器上的InfiniBand（RDMA）网络流量。它能够实时显示所有或指定InfiniBand接口的发送和接收速率，帮助诊断网络性能问题。

4. **GPU PCIe调优工具** (`tools/gpu-pcie-tuner.py`)：一个Python脚本，用于诊断和解决GPU P2P、D2H和H2D通信中的阻塞或减速问题。它能够列出GPU设备、显示P2P拓扑结构、追踪问题根源，并提供多种PCIe配置选项，包括启用/禁用ACS、启用PCIe扩展功能、设置MaxPayload、MaxReadReq和Completion Timeout等。

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

## 贡献指南

欢迎提交Issue和Pull Request来改进本项目。

## 许可证

本项目采用MIT许可证。