// TPN Top-Level Module for fpga-network-stack
// Integrates TPN protocol with AXI4-Stream interfaces

`timescale 1ns / 1ps

module tpn_top #(
    parameter DATA_WIDTH = 64,
    parameter KEEP_WIDTH = DATA_WIDTH/8
)(
    // Clock and Reset
    input wire clk,
    input wire rst_n,

    // AXI4-Stream Input (from network stack)
    input wire [DATA_WIDTH-1:0] s_axis_rx_data,
    input wire [KEEP_WIDTH-1:0] s_axis_rx_keep,
    input wire s_axis_rx_last,
    input wire s_axis_rx_valid,
    output wire s_axis_rx_ready,

    // AXI4-Stream Output (to network stack)
    output wire [DATA_WIDTH-1:0] m_axis_tx_data,
    output wire [KEEP_WIDTH-1:0] m_axis_tx_keep,
    output wire m_axis_tx_last,
    output wire m_axis_tx_valid,
    input wire m_axis_tx_ready,

    // Configuration
    input wire [15:0] reg_tpn_port,        // TPN port number
    input wire [31:0] reg_tpn_version,     // Protocol version

    // Status
    output wire [31:0] reg_tpn_packets_processed,
    output wire [31:0] reg_tpn_receipts_generated,
    output wire [31:0] reg_tpn_errors
);

    // Internal signals
    wire [DATA_WIDTH-1:0] parsed_data;
    wire [KEEP_WIDTH-1:0] parsed_keep;
    wire parsed_last;
    wire parsed_valid;
    wire parsed_ready;

    wire [DATA_WIDTH-1:0] result_data;
    wire [KEEP_WIDTH-1:0] result_keep;
    wire result_last;
    wire result_valid;
    wire result_ready;

    // Packet parser instance
    tpn_packet_parser #(
        .DATA_WIDTH(DATA_WIDTH)
    ) packet_parser (
        .clk(clk),
        .rst_n(rst_n),
        .s_axis_rx_data(s_axis_rx_data),
        .s_axis_rx_keep(s_axis_rx_keep),
        .s_axis_rx_last(s_axis_rx_last),
        .s_axis_rx_valid(s_axis_rx_valid),
        .s_axis_rx_ready(s_axis_rx_ready),
        .m_axis_tx_data(parsed_data),
        .m_axis_tx_keep(parsed_keep),
        .m_axis_tx_last(parsed_last),
        .m_axis_tx_valid(parsed_valid),
        .m_axis_tx_ready(parsed_ready)
    );

    // Gate executor instance
    tpn_gate_executor #(
        .DATA_WIDTH(DATA_WIDTH)
    ) gate_executor (
        .clk(clk),
        .rst_n(rst_n),
        .s_axis_rx_data(parsed_data),
        .s_axis_rx_keep(parsed_keep),
        .s_axis_rx_last(parsed_last),
        .s_axis_rx_valid(parsed_valid),
        .s_axis_rx_ready(parsed_ready),
        .m_axis_tx_data(result_data),
        .m_axis_tx_keep(result_keep),
        .m_axis_tx_last(result_last),
        .m_axis_tx_valid(result_valid),
        .m_axis_tx_ready(result_ready)
    );

    // Receipt generator instance
    tpn_receipt_generator #(
        .DATA_WIDTH(DATA_WIDTH)
    ) receipt_generator (
        .clk(clk),
        .rst_n(rst_n),
        .s_axis_rx_data(result_data),
        .s_axis_rx_keep(result_keep),
        .s_axis_rx_last(result_last),
        .s_axis_rx_valid(result_valid),
        .s_axis_rx_ready(result_ready),
        .m_axis_tx_data(m_axis_tx_data),
        .m_axis_tx_keep(m_axis_tx_keep),
        .m_axis_tx_last(m_axis_tx_last),
        .m_axis_tx_valid(m_axis_tx_valid),
        .m_axis_tx_ready(m_axis_tx_ready)
    );

    // Status registers
    reg [31:0] packets_processed = 0;
    reg [31:0] receipts_generated = 0;
    reg [31:0] errors = 0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            packets_processed <= 0;
            receipts_generated <= 0;
            errors <= 0;
        end else begin
            if (parsed_valid && parsed_ready)
                packets_processed <= packets_processed + 1;
            if (result_valid && result_ready)
                receipts_generated <= receipts_generated + 1;
        end
    end

    assign reg_tpn_packets_processed = packets_processed;
    assign reg_tpn_receipts_generated = receipts_generated;
    assign reg_tpn_errors = errors;

endmodule
