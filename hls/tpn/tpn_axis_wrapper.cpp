#include "tpn_axis_wrapper.h"

// Parse TPN header from AXI4-Stream input
// Receives 64-bit AXI4-Stream data, extracts 42-byte TPN header
void tpn_parse_header(
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& axis_in,
    hls::stream<tpn_header_axis>& header_out,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& payload_out
) {
    #pragma HLS PIPELINE II=1

    ap_uint<AXIS_DATA_WIDTH> data_word;
    static ap_uint<4> word_count = 0;
    static tpn_header_axis header;
    static bool header_complete = false;
    static ap_uint<16> payload_remaining = 0;

    if (!axis_in.empty()) {
        axis_in.read(data_word);

        if (!header_complete) {
            // Parse header fields (42 bytes = 5.25 x 64-bit words)
            switch (word_count) {
                case 0:
                    // Bits [63:0]: id[63:0]
                    header.id = data_word.range(127, 0);
                    break;
                case 1:
                    // Bits [63:0]: id[127:64]
                    header.id = data_word.range(127, 0);
                    break;
                case 2:
                    // Bits [63:0]: phase[31:0], angle[31:0]
                    header.phase = data_word.range(63, 32);
                    header.angle = data_word.range(31, 0);
                    break;
                case 3:
                    // Bits [63:0]: value[63:0]
                    header.value = data_word.range(63, 0);
                    break;
                case 4:
                    // Bits [63:0]: type[7:0], flags[7:0], isa_id[15:0], payload_length[15:0]
                    header.type = data_word.range(63, 56);
                    header.flags = data_word.range(55, 48);
                    header.isa_id = data_word.range(47, 32);
                    header.payload_length = data_word.range(31, 16);
                    header.version = data_word.range(15, 0);
                    break;
                case 5:
                    // Bits [63:0]: checksum[15:0], padding
                    header.checksum = data_word.range(63, 48);
                    header_complete = true;
                    payload_remaining = header.payload_length;
                    header_out.write(header);
                    break;
            }
            word_count++;
        } else {
            // Output payload data
            payload_out.write(data_word);
            if (payload_remaining >= 8) {
                payload_remaining -= 8;
            } else {
                payload_remaining = 0;
                header_complete = false;
                word_count = 0;
            }
        }
    }
}

// Route packets based on TPN type field
void tpn_route_by_type(
    hls::stream<tpn_header_axis>& header_in,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& payload_in,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& data_out,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& gate_out,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& branch_out,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& return_out,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& chain_out
) {
    #pragma HLS PIPELINE II=1

    static tpn_header_axis current_header;
    static bool header_valid = false;
    static ap_uint<8> route_target = 0;

    if (!header_in.empty()) {
        header_in.read(current_header);
        header_valid = true;
    }

    if (header_valid && !payload_in.empty()) {
        ap_uint<AXIS_DATA_WIDTH> payload_data;
        payload_in.read(payload_data);

        // Route based on packet type
        switch (current_header.type) {
            case TPN_TYPE_DATA:
                data_out.write(payload_data);
                break;
            case TPN_TYPE_GATE:
                gate_out.write(payload_data);
                break;
            case TPN_TYPE_BRANCH:
                branch_out.write(payload_data);
                break;
            case TPN_TYPE_RETURN:
                return_out.write(payload_data);
                break;
            case TPN_TYPE_CHAIN:
                chain_out.write(payload_data);
                break;
            default:
                // Unknown type - drop
                break;
        }
    }
}

// Process DATA type packets
void tpn_process_data(
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& data_in,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& result_out
) {
    #pragma HLS PIPELINE II=1

    ap_uint<AXIS_DATA_WIDTH> data;

    if (!data_in.empty()) {
        data_in.read(data);
        // Process data packet - pass through with transformation
        result_out.write(data);
    }
}

// Execute GATE type packets
void tpn_execute_gate(
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& gate_in,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& result_out,
    ap_uint<32> angle
) {
    #pragma HLS PIPELINE II=1

    ap_uint<AXIS_DATA_WIDTH> data;

    if (!gate_in.empty()) {
        gate_in.read(data);
        // Execute gate based on angle parameter
        // Simple pass-through for now - gate logic would be implemented here
        result_out.write(data);
    }
}

// Generate receipt for processed packets
void tpn_generate_receipt(
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& result_in,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& receipt_out
) {
    #pragma HLS PIPELINE II=1

    ap_uint<AXIS_DATA_WIDTH> result;

    if (!result_in.empty()) {
        result_in.read(result);
        // Generate receipt - pass through result
        receipt_out.write(result);
    }
}

// Top-level TPN AXI4-Stream wrapper
// Integrates all TPN processing stages with AXI4-Stream interfaces
void tpn_axis_top(
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& s_axis_rx,
    hls::stream<ap_uint<AXIS_DATA_WIDTH>>& m_axis_tx
) {
    #pragma HLS INTERFACE axis port=s_axis_rx
    #pragma HLS INTERFACE axis port=m_axis_tx
    #pragma HLS INTERFACE ap_ctrl_none port=return

    #pragma HLS DATAFLOW

    // Internal streams
    hls::stream<tpn_header_axis> header_stream;
    hls::stream<ap_uint<AXIS_DATA_WIDTH>> payload_stream;
    hls::stream<ap_uint<AXIS_DATA_WIDTH>> data_stream;
    hls::stream<ap_uint<AXIS_DATA_WIDTH>> gate_stream;
    hls::stream<ap_uint<AXIS_DATA_WIDTH>> branch_stream;
    hls::stream<ap_uint<AXIS_DATA_WIDTH>> return_stream;
    hls::stream<ap_uint<AXIS_DATA_WIDTH>> chain_stream;
    hls::stream<ap_uint<AXIS_DATA_WIDTH>> result_stream;

    // Stage 1: Parse TPN header from AXI4-Stream
    tpn_parse_header(s_axis_rx, header_stream, payload_stream);

    // Stage 2: Route packets by type
    tpn_route_by_type(header_stream, payload_stream,
                      data_stream, gate_stream, branch_stream,
                      return_stream, chain_stream);

    // Stage 3: Process each packet type
    tpn_process_data(data_stream, result_stream);
    tpn_execute_gate(gate_stream, result_stream, 0);

    // Stage 4: Generate receipt and output
    tpn_generate_receipt(result_stream, m_axis_tx);
}