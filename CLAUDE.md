# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository implements a machine learning approach to TCP FlightSize estimation using kernel-space monitoring and user-space prediction. The system integrates a patched Linux kernel with XGBoost models for real-time TCP flight size prediction in network testbeds.

## Key Commands

### Data Collection and Training
```bash
# Collect training data using Mahimahi traces
python3 collection_mahimahi.py

# Train the XGBoost model
python3 xgbtrain.py

# Run cross-validation and feature analysis
python3 non_sequential_CV.py
```

### Building Components
```bash
# Build kernel modules (requires patched kernel)
cd kmod_sysfs
make
cd tcp_monitor
make
cd ../..

# Compile ML model for real-time inference
cd C_ml_model
python3 xgb2.py  # Starts the ML prediction service
```

### Running Experiments
```bash
# Start the system in virtualized environment
./boot_kvm_script.sh

# Enable/disable ML-based flight size prediction
./mLlfs_enable.sh
./mLlfs_disable.sh
```

## Architecture Components

### Core Directories
- **`kmod_sysfs/`**: Kernel modules for TCP monitoring and sysfs interface
  - `ml_tcp_sysfs.c`: Main kernel module for ML integration
  - `tcp_monitor/`: TCP stack monitoring functionality
- **`C_ml_model/`**: Real-time ML prediction engine using compiled XGBoost model
- **`Mininet_testbed/`**: Network emulation and integration testing framework
- **`traces/`**: Mahimahi network traces for data collection

### Key Scripts
- **`collection_mahimahi.py`**: Automated data collection using network trace replay
- **`xgbtrain.py`**: XGBoost model training with GroupShuffleSplit validation
- **`C_ml_model/xgb2.py`**: Real-time prediction service with performance monitoring
- **`utils.py`**: Common utilities for subprocess execution and network management

### Control Files
The system uses simple text files for runtime configuration:
- `cca_control`: Congestion control algorithm setting
- `reorder_control`: Packet reordering parameters
- `bw_control`: Bandwidth configuration
- `rtt_control`: RTT settings  
- `ML_control`: ML prediction parameters
- `ml_flight_size`: Output file for ML predictions (read by kernel)
- `socket_info`: TCP socket information (written by kernel, read by ML service)

## Data Flow Architecture

1. **Kernel Module** (`kmod_sysfs/`) monitors TCP connections and exports socket information
2. **ML Prediction Service** (`C_ml_model/xgb2.py`) reads socket info, runs XGBoost inference, writes predictions
3. **Kernel Integration** reads ML predictions via sysfs and replaces default Linux flight size calculations
4. **Network Testbeds** (Mininet/Mahimahi) provide controlled environments for data collection and testing

## Important Path Dependencies

Several scripts contain hardcoded paths that may need updating:
- Kernel source: `/home/ubuntu/FlightSize/linux`
- Socket info file: `/home/ubuntu/FlightSize/socket_info`
- ML predictions file: `/home/ubuntu/FlightSize/ml_flight_size`
- Compiled model: `/home/ubuntu/FlightSize/C_ml_model/libxgb.so`

These paths appear in `utils.py`, `C_ml_model/xgb2.py`, and kernel module makefiles.

## Data Processing Pipeline

Training data is collected from CSV files in the `csvs/` directory, with each flow assigned a unique `flow_id`. The model uses GroupShuffleSplit to ensure no flow data leaks between training and test sets. Key features exclude timing information (`Time`, `Sequence`) and the target variables (`FlightSizeRef`, `FlightSizeLin`) to prevent data leakage.