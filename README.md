# TPA-fpga: Temporal Packet Network FPGA Integration

Self-hosting network protocol for on-demand computing resources, integrated with the fpga-network-stack.

## Overview

TPA-fpga implements the TPN (Temporal Packet Network) protocol on top of the fpga-network-stack from ETH Zurich. The protocol enables:

- **Self-hosting packets** — each packet carries its own ISA
- **Arrival = execution** — packet arrival triggers computation
- **Cryptographic receipts** — verifiable proof of execution
- **IPv4/IPv6 duality** — temporal/spatial registers

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  TPN Protocol Layer                  │
│  (Self-hosting packets, arrival model, receipts)    │
├─────────────────────────────────────────────────────┤
│              fpga-network-stack                      │
│  (TCP/IP, RoCEv2, UDP/IP, AXI4-Stream, DMA)        │
├─────────────────────────────────────────────────────┤
│              FPGA Hardware                           │
│  (LUTs, BRAM, DSPs, HBM, network interfaces)        │
└─────────────────────────────────────────────────────┘
```

## Repository Structure

```
TPA-fpga/
├── hdl/                    # SystemVerilog modules
│   ├── tpn_top.sv         # Top-level TPN module
│   ├── tpn_packet_parser.sv
│   ├── tpn_gate_executor.sv
│   ├── tpn_receipt_generator.sv
│   └── tpn_testbench.sv
├── hls/                    # HLS C++ modules
│   └── tpn/
│       ├── tpn.cpp
│       └── tpn.h
├── python/                 # Python simulator and tests
│   ├── tpn_simulator.py
│   └── test_tpn.py
├── constraints/            # FPGA constraints
├── scripts/                # Build and test scripts
├── CMakeLists.txt
└── README.md
```

## Quick Start

### Python Simulator

```bash
cd python
python3 tpn_simulator.py
```

### FPGA Build

```bash
mkdir build && cd build
cmake .. -DFNS_PLATFORM=xilinx_u55c_gen3x16_xdma_3_202210_1 -DFNS_DATA_WIDTH=64
make
```

## License

Apache 2.0
