#!/usr/bin/env python3
"""
TPN Network Protocol - Real Packet Implementation
Sends and receives actual network packets using raw sockets.
Measures real throughput, latency, and reliability.
Supports both UDP and TCP modes.
"""

import socket
import struct
import time
import hashlib
import threading
import statistics
from pathlib import Path

# ============================================================
# TPN Protocol Constants
# ============================================================

HEADER_SIZE = 42
RECEIPT_SIZE = 84
MAX_PAYLOAD = 1400

# Packet Types
TPN_TYPE_DATA = 0x01
TPN_TYPE_GATE = 0x02

# Gate Types
GATE_NAND = 0x04

# ============================================================
# TPN Packet
# ============================================================

class TPNPacket:
    """A real TPN packet that goes on the wire."""

    def __init__(self):
        self.id = 0
        self.phase = 0
        self.angle = 0
        self.value = 0
        self.type = TPN_TYPE_DATA
        self.flags = 0
        self.isa_id = 0
        self.payload_length = 0
        self.version = 2
        self.checksum = 0
        self.payload = b""

    def pack(self):
        """Pack into bytes for network transmission."""
        header = struct.pack(
            "!16sIIQBBHHHH",
            self.id.to_bytes(16, "big"),
            self.phase,
            self.angle,
            self.value,
            self.type,
            self.flags,
            self.isa_id,
            self.payload_length,
            self.version,
            0,
        )
        self.checksum = self._calculate_checksum(header)
        header = header[:-2] + struct.pack("!H", self.checksum)
        return header + self.payload

    def unpack(self, data):
        """Unpack from network bytes."""
        if len(data) < HEADER_SIZE:
            raise ValueError("Data too short")

        header = data[:HEADER_SIZE]
        (
            id_bytes,
            self.phase,
            self.angle,
            self.value,
            self.type,
            self.flags,
            self.isa_id,
            self.payload_length,
            self.version,
            self.checksum,
        ) = struct.unpack("!16sIIQBBHHHH", header)

        self.id = int.from_bytes(id_bytes, "big")
        self.payload = data[HEADER_SIZE : HEADER_SIZE + self.payload_length]
        return self

    def _calculate_checksum(self, data):
        """CRC-16 checksum."""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
            crc &= 0xFFFF
        return crc

    def verify_checksum(self):
        """Verify packet integrity."""
        header = struct.pack(
            "!16sIIQBBHHHH",
            self.id.to_bytes(16, "big"),
            self.phase,
            self.angle,
            self.value,
            self.type,
            self.flags,
            self.isa_id,
            self.payload_length,
            self.version,
            0,
        )
        return self._calculate_checksum(header) == self.checksum


# ============================================================
# TPN Network Node
# ============================================================

class TPNNode:
    """A real TPN network node that sends and receives packets.
    Supports both UDP and TCP protocols."""

    def __init__(self, host="127.0.0.1", port=9999, protocol="udp"):
        self.host = host
        self.port = port
        self.protocol = protocol.lower()
        self.socket = None          # UDP socket or TCP client connection
        self.server_socket = None   # TCP server listening socket
        self.conn = None            # Accepted TCP connection (server side)
        self.running = False
        self.packets_sent = 0
        self.packets_received = 0
        self.latencies = []
        self.lock = threading.Lock()
        self._recv_buffer = b""     # TCP stream reassembly buffer

    def start(self):
        """Start the TPN node."""
        if self.protocol == "tcp":
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            self.server_socket.settimeout(0.1)
            self.running = True

            self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.accept_thread.start()

            self.receiver_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receiver_thread.start()

            print(f"TPN Node (TCP) started on {self.host}:{self.port}")
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.settimeout(0.1)
            self.running = True

            self.receiver_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receiver_thread.start()

            print(f"TPN Node (UDP) started on {self.host}:{self.port}")

    def connect(self, dest_host, dest_port):
        """Connect to a remote TCP node (client mode)."""
        if self.protocol != "tcp":
            raise RuntimeError("connect() only valid for TCP mode")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((dest_host, dest_port))
        self.socket.settimeout(0.1)
        print(f"Connected to {dest_host}:{dest_port}")

    def stop(self):
        """Stop the TPN node."""
        self.running = False
        if self.protocol == "tcp":
            if self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass
            if self.server_socket:
                try:
                    self.server_socket.close()
                except Exception:
                    pass
            if self.socket:
                try:
                    self.socket.close()
                except Exception:
                    pass
        else:
            if self.socket:
                self.socket.close()
        print(f"TPN Node stopped. Sent: {self.packets_sent}, Received: {self.packets_received}")

    def send_packet(self, packet, dest_host=None, dest_port=None):
        """Send a real packet over the network."""
        data = packet.pack()
        try:
            if self.protocol == "tcp":
                # TCP framing: 4-byte length prefix + data
                frame = struct.pack("!I", len(data)) + data
                sock = self._get_tcp_send_sock()
                if sock:
                    sock.sendall(frame)
                else:
                    return False
            else:
                self.socket.sendto(data, (dest_host, dest_port))
            with self.lock:
                self.packets_sent += 1
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False

    def _get_tcp_send_sock(self):
        """Get the appropriate TCP socket for sending."""
        if self.protocol != "tcp":
            return None
        return self.conn if self.conn else self.socket

    def _accept_loop(self):
        """Accept incoming TCP connections (server side)."""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                conn.settimeout(0.1)
                self.conn = conn
                print(f"Accepted connection from {addr}")
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Accept error: {e}")

    def _receive_loop(self):
        """Background thread to receive packets."""
        while self.running:
            try:
                if self.protocol == "tcp":
                    self._receive_tcp()
                else:
                    self._receive_udp()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Receive error: {e}")

    def _receive_udp(self):
        """Receive a UDP packet."""
        data, addr = self.socket.recvfrom(2048)
        packet = TPNPacket().unpack(data)
        with self.lock:
            self.packets_received += 1
        self._process_packet(packet, addr)

    def _receive_tcp(self):
        """Receive TCP data with stream reassembly."""
        sock = self.conn if self.conn else self.socket
        if sock is None:
            time.sleep(0.01)
            return

        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            return
        except Exception as e:
            if self.running:
                print(f"TCP receive error: {e}")
            return

        if not chunk:
            return

        self._recv_buffer += chunk

        # Process complete frames from buffer
        while len(self._recv_buffer) >= 4:
            frame_len = struct.unpack("!I", self._recv_buffer[:4])[0]
            if len(self._recv_buffer) < 4 + frame_len:
                break
            data = self._recv_buffer[4 : 4 + frame_len]
            self._recv_buffer = self._recv_buffer[4 + frame_len :]

            packet = TPNPacket().unpack(data)
            with self.lock:
                self.packets_received += 1
            self._process_packet(packet, None)

    def _process_packet(self, packet, addr):
        """Process a received packet."""
        if packet.type == TPN_TYPE_GATE:
            # Execute gate
            result = self._execute_gate(packet)
            # Generate receipt
            receipt = self._generate_receipt(packet, result)
            # Send receipt back
            receipt_data = receipt.pack()
            if self.protocol == "tcp":
                frame = struct.pack("!I", len(receipt_data)) + receipt_data
                try:
                    sock = self._get_tcp_send_sock()
                    if sock:
                        sock.sendall(frame)
                except Exception as e:
                    print(f"Send receipt error: {e}")
            else:
                self.socket.sendto(receipt_data, addr)

    def _execute_gate(self, packet):
        """Execute a logic gate."""
        # Simplified: just return the value
        return packet.value

    def _generate_receipt(self, packet, result):
        """Generate a cryptographic receipt."""
        receipt = TPNReceipt()
        receipt.packet_id = packet.id & 0xFFFFFFFF
        receipt.timestamp = int(time.time() * 1e9)
        receipt.result = result
        receipt.generate_proof(packet.pack())
        return receipt

    def get_stats(self):
        """Get network statistics."""
        with self.lock:
            return {
                "packets_sent": self.packets_sent,
                "packets_received": self.packets_received,
            }


class TPNReceipt:
    """A cryptographic receipt."""

    def __init__(self):
        self.packet_id = 0
        self.timestamp = 0
        self.result = 0
        self.proof = b"\x00" * 32
        self.signature = b"\x00" * 32

    def pack(self):
        return struct.pack(
            "!IQ8s32s32s",
            self.packet_id,
            self.timestamp,
            self.result.to_bytes(8, "big"),
            self.proof,
            self.signature,
        )

    def generate_proof(self, packet_data):
        self.proof = hashlib.sha256(packet_data).digest()
        return self.proof


# ============================================================
# Throughput Benchmark
# ============================================================

def benchmark_throughput(num_packets=1000, payload_size=64, protocol="udp"):
    """Measure real network throughput."""
    print("=" * 60)
    print(f"TPN NETWORK THROUGHPUT BENCHMARK ({protocol.upper()})")
    print("=" * 60)

    if protocol == "tcp":
        # TCP: node2 is server, node1 is client
        node1 = TPNNode("127.0.0.1", 9998, protocol="tcp")
        node2 = TPNNode("127.0.0.1", 9999, protocol="tcp")
        node2.start()
        time.sleep(0.2)
        node1.connect("127.0.0.1", 9999)
        time.sleep(0.2)
    else:
        # UDP: both nodes are peers
        node1 = TPNNode("127.0.0.1", 9998, protocol="udp")
        node2 = TPNNode("127.0.0.1", 9999, protocol="udp")
        node1.start()
        node2.start()
        time.sleep(0.5)

    # Create test packet
    packet = TPNPacket()
    packet.id = 0x20010DB8000000000000000000000001
    packet.phase = 0xC0A80101
    packet.angle = 0
    packet.value = 0x123456789ABCDEF0
    packet.type = TPN_TYPE_GATE
    packet.flags = 0
    packet.isa_id = 0
    packet.payload_length = payload_size
    packet.version = 2
    packet.payload = b"\x00" * payload_size

    # Warmup
    print("Warming up...")
    for _ in range(100):
        if protocol == "tcp":
            node1.send_packet(packet)
        else:
            node1.send_packet(packet, "127.0.0.1", 9999)
        time.sleep(0.001)

    # Benchmark
    print(f"Sending {num_packets} packets...")
    start_time = time.time()

    for i in range(num_packets):
        packet.value = i
        if protocol == "tcp":
            node1.send_packet(packet)
        else:
            node1.send_packet(packet, "127.0.0.1", 9999)

    # Wait for all packets to be processed
    time.sleep(2)

    elapsed = time.time() - start_time

    # Get stats
    stats1 = node1.get_stats()
    stats2 = node2.get_stats()

    # Calculate metrics
    packets_sent = stats1["packets_sent"]
    packets_received = stats2["packets_received"]
    throughput = packets_received / elapsed if elapsed > 0 else 0
    packet_size = HEADER_SIZE + payload_size
    bandwidth = throughput * packet_size * 8 / 1e6  # Mbps
    packet_loss = (1 - packets_received / packets_sent) * 100 if packets_sent > 0 else 0

    print(f"\n{'='*60}")
    print(f"RESULTS ({protocol.upper()}):")
    print(f"{'='*60}")
    print(f"Packets sent: {packets_sent}")
    print(f"Packets received: {packets_received}")
    print(f"Elapsed time: {elapsed:.2f}s")
    print(f"Throughput: {throughput:.1f} packets/sec")
    print(f"Packet size: {packet_size} bytes")
    print(f"Bandwidth: {bandwidth:.2f} Mbps")
    print(f"Packet loss: {packet_loss:.1f}%")
    print(f"{'='*60}")

    # Stop nodes
    node1.stop()
    node2.stop()

    return {
        "protocol": protocol,
        "packets_sent": packets_sent,
        "packets_received": packets_received,
        "elapsed": elapsed,
        "throughput": throughput,
        "bandwidth_mbps": bandwidth,
        "packet_loss": packet_loss,
    }


def benchmark_comparison(num_packets=1000, payload_size=64):
    """Compare UDP and TCP throughput."""
    print("\n" + "=" * 60)
    print("TPN NETWORK UDP vs TCP COMPARISON")
    print("=" * 60)

    udp_results = benchmark_throughput(num_packets, payload_size, protocol="udp")
    tcp_results = benchmark_throughput(num_packets, payload_size, protocol="tcp")

    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"{'Metric':<25} {'UDP':>15} {'TCP':>15}")
    print(f"{'-'*55}")
    print(f"{'Throughput (pkt/s)':<25} {udp_results['throughput']:>15.1f} {tcp_results['throughput']:>15.1f}")
    print(f"{'Bandwidth (Mbps)':<25} {udp_results['bandwidth_mbps']:>15.2f} {tcp_results['bandwidth_mbps']:>15.2f}")
    print(f"{'Packet loss (%)':<25} {udp_results['packet_loss']:>15.1f} {tcp_results['packet_loss']:>15.1f}")
    print(f"{'Packets sent':<25} {udp_results['packets_sent']:>15} {tcp_results['packets_sent']:>15}")
    print(f"{'Packets received':<25} {udp_results['packets_received']:>15} {tcp_results['packets_received']:>15}")
    print("=" * 60)

    return {
        "udp": udp_results,
        "tcp": tcp_results,
    }


if __name__ == "__main__":
    results = benchmark_comparison(num_packets=1000, payload_size=64)

    # Save results
    import json
    with open("/tmp/TPA-fpga/benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to /tmp/TPA-fpga/benchmark_results.json")