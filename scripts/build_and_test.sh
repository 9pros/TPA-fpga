#!/bin/bash
# Build and test TPA-fpga

set -e

echo "=========================================="
echo "TPA-fpga Build and Test"
echo "=========================================="

# Run Python tests
echo ""
echo "Running Python simulator tests..."
cd python
python3 test_tpn.py
cd ..

# Build HLS modules (if Vivado HLS is available)
if command -v vitis_hls &> /dev/null; then
    echo ""
    echo "Building HLS modules..."
    mkdir -p build
    cd build
    cmake .. -DFNS_PLATFORM=xilinx_u55c_gen3x16_xdma_3_202210_1 -DFNS_DATA_WIDTH=64
    make
    cd ..
else
    echo ""
    echo "Vivado HLS not found, skipping HLS build"
fi

echo ""
echo "=========================================="
echo "Build and test complete!"
echo "=========================================="
