# AIServerOpTools

## Project Introduction

This project is a collection of operation and maintenance tools for domestic AI servers, developed primarily using Python and Shell. These tools are designed to simplify daily O&M work for AI servers and improve operational efficiency.

## Tools

This project currently contains five tools:

1. **Server Information Collection Tool** (`tools/server_info_collect.sh`): A bash script that collects comprehensive server information including hardware (CPU, AI accelerator cards, memory, motherboard, BIOS, storage, network) and software (OS, compiler, AI libraries, Docker, tuned profiles, IOMMU/SMMU status) details. It generates a detailed report for AI server diagnostics and comparison.

2. **AI Server Checklist Tool** (`tools/ai-server-checklist.sh`): A bash script that performs comprehensive checks on AI servers, covering hardware (CPU, memory, motherboard, BIOS, storage, network cards, hardware topology, AI cards) and software (OS, compiler, glibc, Docker, tuned profiles, IOMMU/SMMU status, kernel parameters) aspects. It supports both standard and Markdown output formats, generating detailed reports for AI server diagnostics and configuration validation.

3. **InfiniBand Traffic Monitor** (`tools/ib_traffic_monitor.py`): A Python script that monitors InfiniBand (RDMA) network traffic on AI servers. It displays real-time transmission and reception rates for all or specified InfiniBand interfaces, helping diagnose network performance issues.

4. **GPU PCIe Tuner** (`tools/gpu-pcie-tuner.py`): A Python script designed to diagnose and resolve issues of GPU P2P, D2H, and H2D blockage or slowdown. It can list GPU devices, display P2P topology, trace the root causes of issues, and provide various PCIe configuration options, including enabling/disabling ACS, enabling PCIe extend capability, setting MaxPayload, MaxReadReq, and Completion Timeout.

5. **AI Server Reboot Test Tool** (`tools/ai-server-reboot-test.sh`): A bash script that performs automated reboot testing for AI servers with progress saving capability. It conducts specified number of reboot cycles and verifies AI card recognition status after each reboot. The tool supports multiple AI card vendors (NVIDIA, Huawei, Enrigin, MetaX, Iluvatar, Hexaflake), checks link bandwidth and operational status of all AI cards in the system, and supports both reboot command and IPMI reset restart methods.

## Installation and Usage

```bash
git clone <repository-url>
cd AIServerOpTools
# Install dependencies according to specific tool requirements
```

### AI Server Checklist Tool Usage

The AI Server Checklist Tool (`tools/ai-server-checklist.sh`) requires root privileges to run and has the following usage options:

```bash
# Run with standard output format
sudo ./tools/ai-server-checklist.sh

# Run with Markdown output format
sudo ./tools/ai-server-checklist.sh markdown
```

The tool will generate a report file in the current directory with the naming convention `ai_checklist_<hostname>_<date>.txt` for standard format or `ai_checklist_<hostname>_<date>.md` for Markdown format.

### InfiniBand Traffic Monitor Usage

The InfiniBand Traffic Monitor (`tools/ib_traffic_monitor.py`) requires the `ibstat` and `perfquery` tools to be installed and accessible. It has the following usage options:

```bash
# Monitor all InfiniBand interfaces with 1 second interval (default)
python3 ./tools/ib_traffic_monitor.py

# Monitor all InfiniBand interfaces with custom interval
python3 ./tools/ib_traffic_monitor.py -i 2

# Monitor specific InfiniBand interface
python3 ./tools/ib_traffic_monitor.py -I mlx5_0
```

Press `Ctrl+C` to stop monitoring.

### GPU PCIe Tuner Usage

The GPU PCIe Tuner (`tools/gpu-pcie-tuner.py`) requires the `lspci` and `setpci` tools to be installed and accessible. It has the following usage options:

```bash
# List GPU devices
python3 ./tools/gpu-pcie-tuner.py -l

# Display AI card P2P topology
python3 ./tools/gpu-pcie-tuner.py --topo

# Trace the root causes of issues
python3 ./tools/gpu-pcie-tuner.py --trace

# Enable ACS
sudo python3 ./tools/gpu-pcie-tuner.py --enable-acs

# Disable ACS
sudo python3 ./tools/gpu-pcie-tuner.py --disable-acs

# Enable PCIe extend capability
sudo python3 ./tools/gpu-pcie-tuner.py --enable-extend

# Set GPU MaxPayload to 256B
sudo python3 ./tools/gpu-pcie-tuner.py --set-mps 1

# Set GPU MaxReadReq to 512B
sudo python3 ./tools/gpu-pcie-tuner.py --set-mrrs 2

# Set GPU Completion Timeout Disable to enable
sudo python3 ./tools/gpu-pcie-tuner.py --set-timeoutDis 1

# Set GPU Completion Timeout Range to A (50 µs – 100 µs)
sudo python3 ./tools/gpu-pcie-tuner.py --set-timeoutRange A_1
```

### AI Server Reboot Test Tool Usage

The AI Server Reboot Test Tool (`tools/ai-server-reboot-test.sh`) requires root privileges to run and has the following usage options:

```bash
# Perform 5 reboot cycles using reboot command (default)
sudo ./tools/ai-server-reboot-test.sh -r 5

# Perform 3 reboot cycles using IPMI reset, checking only NVIDIA cards
sudo ./tools/ai-server-reboot-test.sh -i -c 1 3

# Check all AI card vendors with 10 reboot cycles
sudo ./tools/ai-server-reboot-test.sh 10

# Display help information
./tools/ai-server-reboot-test.sh -h
```

The tool supports the following options:
- `-r, --reboot`: Use reboot command for restart (default)
- `-i, --ipmi`: Use IPMI reset for restart (requires ipmitool)
- `-c, --card NUMBER`: Specify AI card vendor to check (1-6 for different vendors)
- `-h, --help`: Display help information

The tool automatically saves test progress to `/root/ai_test_progress` and logs all results to `/root/ai_reboot_test.log`. It supports resuming interrupted tests and validates AI card status after each reboot cycle.

## Contribution Guide

Feel free to submit issues and pull requests to improve this project.

## License

This project is licensed under the MIT License.