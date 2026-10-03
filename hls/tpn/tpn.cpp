#include "tpn.h"

void tpn_process_packet(
    hls::stream<ap_uint<64>>& input,
    hls::stream<ap_uint<64>>& output,
    tpn_header& header
) {
    #pragma HLS PIPELINE II=1

    ap_uint<64> data;

    if (!input.empty()) {
        input.read(data);
        // Process packet data
        output.write(data);
    }
}

void tpn_execute_gate(
    hls::stream<ap_uint<64>>& input,
    hls::stream<ap_uint<64>>& output,
    ap_uint<8> gate_type,
    ap_uint<32> angle
) {
    #pragma HLS PIPELINE II=1

    ap_uint<64> data;

    if (!input.empty()) {
        input.read(data);
        // Execute gate based on type and angle
        output.write(data);
    }
}

void tpn_generate_receipt(
    hls::stream<ap_uint<64>>& input,
    hls::stream<ap_uint<64>>& output,
    tpn_receipt& receipt
) {
    #pragma HLS PIPELINE II=1

    ap_uint<64> data;

    if (!input.empty()) {
        input.read(data);
        // Generate receipt
        output.write(data);
    }
}
