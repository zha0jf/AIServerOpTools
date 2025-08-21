# AIServerOpTools

## 项目简介

本项目是一个针对国产AI服务器的运维小工具合集，主要使用Python和Shell开发。这些工具旨在简化AI服务器的日常运维工作，提高运维效率。

## 工具说明

本项目目前包含两个工具：

1. **服务器信息收集工具** (`tools/server_info_collect.sh`)：一个bash脚本，用于收集全面的服务器信息，包括硬件（CPU、AI加速卡、内存、主板、BIOS、存储、网络）和软件（操作系统、编译器、AI库、Docker、调优配置、IOMMU/SMMU状态）的详细信息。它会生成一份详细的报告，用于AI服务器的诊断和对比。

2. **AI服务器检查清单工具** (`tools/ai-server-checklist.sh`)：一个bash脚本，用于对AI服务器进行全面检查，涵盖硬件（CPU、内存、主板、BIOS、存储、网卡、硬件拓扑、AI卡）和软件（操作系统、编译器、glibc、Docker、调优配置、IOMMU/SMMU状态、内核参数）等方面。它支持标准和Markdown两种输出格式，生成详细的报告用于AI服务器诊断和配置验证。

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

## 贡献指南

欢迎提交Issue和Pull Request来改进本项目。

## 许可证

本项目采用MIT许可证。