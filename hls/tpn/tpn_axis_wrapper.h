#ifndef TPN_AXIS_WRAPPER_H
#define TPN_AXIS_WRAPPER_H

#include <ap_int.h>
#include <hls_stream.h>

// TPN Packet Header (42 bytes = 336 bits)
struct tpn_header_axis {
    ap_uint<128> id;           // IPv6 address
    ap_uint<32> phase;         // IPv4 address
    ap_uint<32> angle;         // Phase difference
    ap_uint<64> value;         // Data value
    ap_uint<8> type;           // Packet type
    ap_uint<8> flags;          // Control flags
    ap_uint<16> isa_id;        // ISA identifier
    ap_uint<16> payload_length;// Payload length
    ap_uint<16> version;       // Protocol version
    ap_uint<16> checksum;      // Header checksum
};

// TPN Packet Types
#define TPN_TYPE_DEALLOC 0x00
#define TPN_TYPE_DATA    0x01
#define TPN_TYPE_GATE    0x02
#define TPN_TYPE_BRANCH  0x03
#define TPN_TYPE_RETURN  0x04
#define TPN_TYPE_CHAIN   0x05

// TPN Flags
#define TPN_FLAG_SELF_DESCRIBING 0x01
#define TPN_FLAG_CHAINED         0x02
#define TPN_FLAG_RETURN          0x04
#define TPN_FLAG_VERIFIED        0x08

// AXI4-Stream data width
#define AXIS_DATA_WIDTH 64
#define AXIS_KEEP_WIDTH (AXIS_DATA_WIDTH / 8)

// TPN Processing Functions
void tpn_parse_header(
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& axis_in,
    hls::stream<tpn_header_axis>& header_out,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& payload_out
);

void tpn_route_by_type(
    hls::stream<tpn_header_axis>& header_in,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& payload_in,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& data_out,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& gate_out,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& branch_out,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& return_out,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& chain_out
);

void tpn_process_data(
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& data_in,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& result_out
);

void tpn_execute_gate(
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& gate_in,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& result_out,
    ap_uint<32> angle
);

void tpn_generate_receipt(
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& result_in,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& receipt_out
);

void tpn_axis_top(
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& s_axis_rx,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& m_axis_tx
);

#endif // TPN_AXIS_WRAPPER_H