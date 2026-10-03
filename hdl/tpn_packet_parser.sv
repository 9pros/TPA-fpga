// TPN Packet Parser
// Parses TPN packet headers from AXI4-Stream data

`timescale 1ns / 1ps

module tpn_packet_parser #(
    parameter DATA_WIDTH = 64,
    parameter KEEP_WIDTH = DATA_WIDTH/8
)(
    input wire clk,
    input wire rst_n,

    // AXI4-Stream Input
    input wire [DATA_WIDTH-1:0] s_axis_rx_data,
    input wire [KEEP_WIDTH-1:0] s_axis_rx_keep,
    input wire s_axis_rx_last,
    input wire s_axis_rx_valid,
    output wire s_axis_rx_ready,

    // AXI4-Stream Output
    output wire [DATA_WIDTH-1:0] m_axis_tx_data,
    output wire [KEEP_WIDTH-1:0] m_axis_tx_keep,
    output wire m_axis_tx_last,
    output wire m_axis_tx_valid,
    input wire m_axis_tx_ready
);

    // TPN Header fields (42 bytes = 336 bits)
    // id: 128 bits (IPv6)
    // phase: 32 bits (IPv4)
    // angle: 32 bits
    // value: 64 bits
    // type: 8 bits
    // flags: 8 bits
    // isa_id: 16 bits
    // payload_length: 16 bits
    // version: 16 bits
    // checksum: 16 bits

    localparam HEADER_SIZE = 42;
    localparam HEADER_WORDS = (HEADER_SIZE * 8 + DATA_WIDTH - 1) / DATA_WIDTH;

    // State machine
    typedef enum {HEADER, PAYLOAD} state_t;
    state_t state = HEADER;

    reg [DATA_WIDTH-1:0] header_buffer [0:HEADER_WORDS-1];
    reg [3:0] header_word_count = 0;
    reg [15:0] payload_length = 0;
    reg [15:0] payload_count = 0;

    // Output assignments
    assign m_axis_tx_data = s_axis_rx_data;
    assign m_axis_tx_keep = s_axis_rx_keep;
    assign m_axis_tx_last = s_axis_rx_last;
    assign m_axis_tx_valid = s_axis_rx_valid;
    assign s_axis_rx_ready = m_axis_tx_ready;

endmodule
