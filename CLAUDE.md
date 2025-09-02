# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains source code and experiment scripts for "Towards Accurate TCP FlightSize Estimation: A History-Aware Learning Approach" (IEEE IPCCC 2025). The project implements a machine learning approach to estimate TCP flight size using kernel modules, user-space ML prediction, and network simulation testbeds.

## Key Commands

### Building Kernel Modules
```bash
# Build the main ML TCP sysfs module
cd kmod_sysfs
make

# Build the TCP monitor module  
cd kmod_sysfs/tcp_monitor
make
```

### Running Experiments

**Single Experiment:**
```bash
# Run a single test with current control file settings
./boot_kvm_script.sh
```

**Batch Experiments:**
```bash
# Run 100 iterations across different parameter combinations
./run100.sh
```

**Manual Control:**
```bash
# Enable/disable ML flight size estimation
./mLlfs_enable.sh
./mLlfs_disable.sh

# Update XGBoost flight size model
./update_xgb_fs.sh
```

### ML Model Commands
```bash
# Run C-based ML prediction (requires tl2cgen and compiled model)
cd C_ml_model
python3 cgb2.py
```

### Network Testing
```bash
# Mahimahi-based network emulation
python3 mahimahi.py

# Mininet testbed experiments
python3 mininetscript.py
python3 compare_two_methods_reorder.py
```

## Architecture

### Core Components

**Kernel Modules (`kmod_sysfs/`)**
- `ml_tcp_sysfs.c`: Kernel module providing sysfs interface for ML flight size predictions
- `tcp_monitor/`: TCP monitoring kernel module for data collection

**ML Prediction (`C_ml_model/`)**
- `cgb2.py`: C-based XGBoost model inference using tl2cgen
- Requires compiled model at `/home/ubuntu/FlightSize/C_ml_model/libxgb.so`

**Network Testbeds**
- `Mininet_testbed/`: Mininet-based network simulation framework
- `mahimahi.py`: Mahimahi network emulation scripts
- Integration with both approaches for controlled testing

**Experiment Control**
- Control files: `cca_control`, `reorder_control`, `bw_control`, `rtt_control`, `ML_control`
- Parameter sweep automation via `run100.sh`
- Virtualization through `virtme` for isolated kernel testing

### Data Flow

1. **Kernel Module** (`tcp_monitor`) collects TCP socket information
2. **ML Predictor** (`cgb2.py`) reads socket info, makes predictions
3. **Sysfs Interface** (`ml_tcp_sysfs`) provides kernel-userspace communication
4. **Experiments** use Mininet/Mahimahi to create controlled network conditions
5. **Analysis** compares ML-based vs traditional flight size estimation

## Important Paths

- Kernel source: `/home/ubuntu/FlightSize/linux` (configured in Makefiles)
- Socket info: `/home/ubuntu/FlightSize/socket_info`
- ML predictions: `/home/ubuntu/FlightSize/ml_flight_size`
- Compiled ML model: `/home/ubuntu/FlightSize/C_ml_model/libxgb.so`

## Dependencies

- **virtme**: For kernel virtualization and testing
- **tl2cgen**: For compiled XGBoost model inference
- **Mininet**: Network simulation framework
- **Mahimahi**: Network emulation tool
- **Standard Python packages**: numpy, pandas, matplotlib, psutil