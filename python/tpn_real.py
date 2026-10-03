#!/usr/bin/env python3
"""
TPN Real Network Protocol - Actual Implementation
Uses IPv4/IPv6 as multidimensional registers with trigonometric gate encoding.
Measures real throughput with the actual protocol design.
"""

import socket
import struct
import time
import hashlib
import math
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
GATE_AND = 0x01
GATE_OR = 0x02
GATE_XOR = 0x03
GATE_NAND = 0x04
GATE_NOR = 0x05
GATE_NOT = 0x06
GATE_BUF = 0x07
GATE_DFF = 0x08
GATE_LUT = 0x09

# ============================================================
# Trigonometric Gate Encoding
# ============================================================

def encode_gate_trigonometric(truth_table):
    """
    Encode a logic gate as a trigonometric function.
    
    truth_table: list of (input_tuple, output) pairs
    Returns: (gate_function, phase_signature, angle_signature)
    """
    n_inputs = len(truth_table[0][0])
    n_combinations = 2 ** n_inputs
    
    # Map each input combination to a phase
    phases = [2 * math.pi * k / n_combinations for k in range(n_combinations)]
    
    # Encode outputs as amplitudes (+1 for 1, -1 for 0)
    amplitudes = []
    for _, output in truth_table:
        amplitudes.append(1.0 if output == 1 else -1.0)
    
    # Define the gate function
    def gate_function(theta):
        result = 0.0
        for k in range(n_combinations):
            result += amplitudes[k] * math.cos(theta - phases[k])
        return result
    
    # Create signatures
    phase_signature = int(phases[0] * 1000000) % (2**32)
    angle_signature = int(sum(amplitudes) * 1000) % (2**32)
    
    return gate_function, phase_signature, angle_signature

def execute_gate_trigonometric(gate_function, input_phases):
    """
    Execute a gate with given input phases.
    
    gate_function: the encoded gate function
    input_phases: list of phase angles for each input
    
    Returns: 0 or 1
    """
    # Sum input phases
    theta_in = sum(input_phases)
    
    # Evaluate gate function
    result = gate_function(theta_in)
    
    # Output is 1 if result > 0, 0 otherwise
    return 1 if result > 0 else 0

# ============================================================
# Standard Gate Definitions
# ============================================================

def get_standard_gates():
    """Get all standard logic gates with their truth tables."""
    gates = {}
    
    # 1-input gates
    gates['NOT'] = [
        ((0,), 1),
        ((1,), 0),
    ]
    
    gates['BUF'] = [
        ((0,), 0),
        ((1,), 1),
    ]
    
    # 2-input gates
    gates['AND'] = [
        ((0, 0), 0),
        ((0, 1), 0),
        ((1, 0), 0),
        ((1, 1), 1),
    ]
    
    gates['OR'] = [
        ((0, 0), 0),
        ((0, 1), 1),
        ((1, 0), 1),
        ((1, 1), 1),
    ]
    
    gates['XOR'] = [
        ((0, 0), 0),
        ((0, 1), 1),
        ((1, 0), 1),
        ((1, 1), 0),
    ]
    
    gates['NAND'] = [
        ((0, 0), 1),
        ((0, 1), 1),
        ((1, 0), 1),
        ((1, 1), 0),
    ]
    
    gates['NOR'] = [
        ((0, 0), 1),
        ((0, 1), 0),
        ((1, 0), 0),
        ((1, 1), 0),
    ]
    
    gates['XNOR'] = [
        ((0, 0), 1),
        ((0, 1), 0),
        ((1, 0), 0),
        ((1, 1), 1),
    ]
    
    return gates

# ============================================================
# TPN Packet
# ============================================================

class TPNPacket:
    """A real TPN packet that goes on the wire."""

    def __init__(self):
        self.id = 0  # IPv6 (128-bit) - spatial register
        self.phase = 0  # IPv4 (32-bit) - temporal register
        self.angle = 0  # Derived phase difference - computational register
        self.value = 0  # 64-bit data value
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

    def __repr__(self):
        return (
            f"TPNPacket(id={self.id:#x}, phase={self.phase:#x}, "
            f"angle={self.angle:#x}, type={self.type:#x})"
        )


# ============================================================
# TPN Register (Multidimensional)
# ============================================================

class TPNRegister:
    """
    A multidimensional register at an IP address.
    
    The register has:
    - id (IPv6): spatial dimension
    - phase (IPv4): temporal dimension
    - angle: computational dimension (derived)
    - value: data
    """

    def __init__(self, ipv6, ipv4):
        self.id = ipv6  # Spatial register
        self.phase = ipv4  # Temporal register
        self.value = 0
        self.angle = 0  # Derived from phase difference
        self.isa = None
        self.receipts = []
        self.gate_cache = {}  # Cache encoded gates

    def compute_angle(self):
        """Compute angle from phase difference between IPv4 and IPv6."""
        # Convert IPv4 to a phase angle (0 to 2π)
        ipv4_phase = (self.phase / 0xFFFFFFFF) * 2 * math.pi
        
        # Convert IPv6 to a phase angle (0 to 2π)
        ipv6_phase = (self.id / (2**128 - 1)) * 2 * math.pi
        
        # Angle is the difference
        self.angle = int((ipv4_phase - ipv6_phase) % (2 * math.pi) * 1000000) % (2**32)
        return self.angle

    def execute(self, packet):
        """Execute a packet on this register."""
        # Compute angle from packet
        self.angle = packet.angle
        
        if packet.type == TPN_TYPE_DATA:
            self.value = packet.value
        elif packet.type == TPN_TYPE_GATE:
            self.value = self._execute_gate(packet)
        
        # Generate receipt
        receipt = self._generate_receipt(packet)
        self.receipts.append(receipt)
        
        return receipt

    def _execute_gate(self, packet):
        """Execute a logic gate using trigonometric encoding."""
        # Get gate type from payload
        if len(packet.payload) < 1:
            return self.value
        
        gate_type = packet.payload[0]
        
        # Get or create gate function
        if gate_type not in self.gate_cache:
            self.gate_cache[gate_type] = self._create_gate_function(gate_type)
        
        gate_func = self.gate_cache[gate_type]
        
        # Execute gate with angle as input
        result = execute_gate_trigonometric(gate_func, [self.angle])
        
        return result

    def _create_gate_function(self, gate_type):
        """Create a gate function from standard gates."""
        gates = get_standard_gates()
        
        # Map gate type to gate name
        gate_map = {
            GATE_AND: 'AND',
            GATE_OR: 'OR',
            GATE_XOR: 'XOR',
            GATE_NAND: 'NAND',
            GATE_NOR: 'NOR',
            GATE_NOT: 'NOT',
            GATE_BUF: 'BUF',
        }
        
        gate_name = gate_map.get(gate_type)
        if gate_name and gate_name in gates:
            return encode_gate_trigonometric(gates[gate_name])[0]
        
        # Default: return identity
        return lambda x: 1.0 if x > 0 else -1.0

    def _generate_receipt(self, packet):
        """Generate a cryptographic receipt."""
        receipt = TPNReceipt()
        receipt.packet_id = packet.id & 0xFFFFFFFF
        receipt.timestamp = int(time.time() * 1e9)
        receipt.result = self.value
        receipt.generate_proof(packet.pack())
        return receipt


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
# TPN Network Node
# ============================================================

class TPNNode:
    """A real TPN network node that sends and receives packets."""

    def __init__(self, host="127.0.0.1", port=9999):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.packets_sent = 0
        self.packets_received = 0
        self.latencies = []
        self.lock = threading.Lock()
        self.registers = {}  # IPv6 -> TPNRegister

    def start(self):
        """Start the TPN node."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.settimeout(0.1)
        self.running = True

        # Start receiver thread
        self.receiver_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receiver_thread.start()

        print(f"TPN Node started on {self.host}:{self.port}")

    def stop(self):
        """Stop the TPN node."""
        self.running = False
        if self.socket:
            self.socket.close()
        print(f"TPN Node stopped. Sent: {self.packets_sent}, Received: {self.packets_received}")

    def create_register(self, ipv6, ipv4):
        """Create a new multidimensional register."""
        reg = TPNRegister(ipv6, ipv4)
        reg.compute_angle()
        self.registers[ipv6] = reg
        return reg

    def send_packet(self, packet, dest_host, dest_port):
        """Send a real packet over the network."""
        data = packet.pack()
        start_time = time.time()

        try:
            self.socket.sendto(data, (dest_host, dest_port))
            with self.lock:
                self.packets_sent += 1
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False

    def _receive_loop(self):
        """Background thread to receive packets."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)
                receive_time = time.time()

                packet = TPNPacket().unpack(data)

                with self.lock:
                    self.packets_received += 1

                # Process packet
                self._process_packet(packet, addr)

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Receive error: {e}")

    def _process_packet(self, packet, addr):
        """Process a received packet."""
        # Find or create register
        if packet.id not in self.registers:
            self.create_register(packet.id, packet.phase)

        reg = self.registers[packet.id]
        receipt = reg.execute(packet)

        # Send receipt back
        receipt_data = receipt.pack()
        self.socket.sendto(receipt_data, addr)

    def get_stats(self):
        """Get network statistics."""
        with self.lock:
            return {
                "packets_sent": self.packets_sent,
                "packets_received": self.packets_received,
                "registers": len(self.registers),
            }


# ============================================================
# Throughput Benchmark
# ============================================================

def benchmark_throughput(num_packets=1000, payload_size=64):
    """Measure real network throughput with TPN protocol."""
    print("=" * 60)
    print("TPN NETWORK THROUGHPUT BENCHMARK")
    print("=" * 60)

    # Create two nodes
    node1 = TPNNode("127.0.0.1", 9998)
    node2 = TPNNode("127.0.0.1", 9999)

    node1.start()
    node2.start()

    time.sleep(0.5)

    # Create test packet with gate encoding
    packet = TPNPacket()
    packet.id = 0x20010DB8000000000000000000000001  # IPv6
    packet.phase = 0xC0A80101  # IPv4
    packet.angle = 0
    packet.value = 0x123456789ABCDEF0
    packet.type = TPN_TYPE_GATE
    packet.flags = 0
    packet.isa_id = 0
    packet.payload_length = payload_size
    packet.version = 2
    packet.payload = bytes([GATE_NAND]) + b"\x00" * (payload_size - 1)

    # Warmup
    print("Warming up...")
    for _ in range(100):
        node1.send_packet(packet, "127.0.0.1", 9999)
        time.sleep(0.001)

    # Benchmark
    print(f"Sending {num_packets} packets...")
    start_time = time.time()

    for i in range(num_packets):
        packet.value = i
        node1.send_packet(packet, "127.0.0.1", 9999)

    time.sleep(2)

    elapsed = time.time() - start_time

    # Get stats
    stats1 = node1.get_stats()
    stats2 = node2.get_stats()

    # Calculate metrics
    packets_sent = stats1["packets_sent"]
    packets_received = stats2["packets_received"]
    throughput = packets_received / elapsed
    packet_size = HEADER_SIZE + payload_size
    bandwidth = throughput * packet_size * 8 / 1e6  # Mbps

    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"{'='*60}")
    print(f"Packets sent: {packets_sent}")
    print(f"Packets received: {packets_received}")
    print(f"Elapsed time: {elapsed:.2f}s")
    print(f"Throughput: {throughput:.1f} packets/sec")
    print(f"Packet size: {packet_size} bytes")
    print(f"Bandwidth: {bandwidth:.2f} Mbps")
    print(f"Packet loss: {(1 - packets_received/packets_sent)*100:.1f}%")
    print(f"Registers created: {stats2['registers']}")
    print(f"{'='*60}")

    # Stop nodes
    node1.stop()
    node2.stop()

    return {
        "packets_sent": packets_sent,
        "packets_received": packets_received,
        "elapsed": elapsed,
        "throughput": throughput,
        "bandwidth_mbps": bandwidth,
        "packet_loss": (1 - packets_received/packets_sent)*100,
        "registers": stats2['registers'],
    }


def test_gate_encoding():
    """Test the trigonometric gate encoding."""
    print("=" * 60)
    print("GATE ENCODING TEST")
    print("=" * 60)

    gates = get_standard_gates()
    all_passed = True

    for gate_name, truth_table in gates.items():
        print(f"\n--- {gate_name} ---")
        
        gate_func, phase_sig, angle_sig = encode_gate_trigonometric(truth_table)
        
        n_inputs = len(truth_table[0][0])
        passed = 0
        total = 0
        
        for input_tuple, expected_output in truth_table:
            # Map input bits to phases (0 -> 0, 1 -> π/2)
            input_phases = [bit * math.pi / 2 for bit in input_tuple]
            
            actual_output = execute_gate_trigonometric(gate_func, input_phases)
            
            if actual_output == expected_output:
                passed += 1
            else:
                print(f"  FAIL: input={input_tuple}, expected={expected_output}, got={actual_output}")
            
            total += 1
        
        status = "PASS" if passed == total else "FAIL"
        print(f"  {status}: {passed}/{total} tests passed")
        
        if passed != total:
            all_passed = False
    
    print(f"\n{'='*60}")
    print(f"OVERALL: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print(f"{'='*60}")
    
    return all_passed


if __name__ == "__main__":
    # Test gate encoding first
    gate_test_passed = test_gate_encoding()
    
    if gate_test_passed:
        # Run throughput benchmark
        results = benchmark_throughput(num_packets=1000, payload_size=64)
        
        # Save results
        import json
        with open("/tmp/TPA-fpga/benchmark_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to /tmp/TPA-fpga/benchmark_results.json")
    else:
        print("Gate encoding tests failed, skipping benchmark")
