#ifndef TPN_H
#define TPN_H

#include <ap_int.h>
#include <hls_stream.h>

// TPN Packet Header (42 bytes)
struct tpn_header {
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

// TPN Receipt (84 bytes)
struct tpn_receipt {
    ap_uint<32> packet_id;
    ap_uint<64> timestamp;
    ap_uint<64> result;
    ap_uint<256> proof;        // SHA-256
    ap_uint<256> signature;    // Ed25519
};

// TPN Processing Functions
void tpn_process_packet(
    hls::stream<ap_uint<64>>& input,
    hls::stream<ap_uint<64>>& output,
    tpn_header& header
);

void tpn_execute_gate(
    hls::stream<ap_uint<64>>& input,
    hls::stream<ap_uint<64>>& output,
    ap_uint<8> gate_type,
    ap_uint<32> angle
);

void tpn_generate_receipt(
    hls::stream<ap_uint<64>>& input,
    hls::stream<ap_uint<64>>& output,
    tpn_receipt& receipt
);

#endif // TPN_H
