cmake_minimum_required(VERSION 3.0)
project(TPA-fpga)

# Find fpga-network-stack
set(FNS_PATH "" CACHE PATH "Path to fpga-network-stack")

if(NOT FNS_PATH)
    message(FATAL_ERROR "Please set FNS_PATH to fpga-network-stack directory")
endif()

# HLS modules
add_subdirectory(hls/tpn)

# HDL modules
add_subdirectory(hdl)
