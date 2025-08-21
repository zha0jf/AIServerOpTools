# AIServerOpTools

## Project Introduction

This project is a collection of operation and maintenance tools for domestic AI servers, developed primarily using Python and Shell. These tools are designed to simplify daily O&M work for AI servers and improve operational efficiency.

## Tools

This project currently contains three tools:

1. **Server Information Collection Tool** (`tools/server_info_collect.sh`): A bash script that collects comprehensive server information including hardware (CPU, AI accelerator cards, memory, motherboard, BIOS, storage, network) and software (OS, compiler, AI libraries, Docker, tuned profiles, IOMMU/SMMU status) details. It generates a detailed report for AI server diagnostics and comparison.

2. **AI Server Checklist Tool** (`tools/ai-server-checklist.sh`): A bash script that performs comprehensive checks on AI servers, covering hardware (CPU, memory, motherboard, BIOS, storage, network cards, hardware topology, AI cards) and software (OS, compiler, glibc, Docker, tuned profiles, IOMMU/SMMU status, kernel parameters) aspects. It supports both standard and Markdown output formats, generating detailed reports for AI server diagnostics and configuration validation.

3. **InfiniBand Traffic Monitor** (`tools/ib_traffic_monitor.py`): A Python script that monitors InfiniBand (RDMA) network traffic on AI servers. It displays real-time transmission and reception rates for all or specified InfiniBand interfaces, helping diagnose network performance issues.

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

## Contribution Guide

Feel free to submit issues and pull requests to improve this project.

## License

This project is licensed under the MIT License.