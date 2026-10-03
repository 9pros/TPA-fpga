#!/usr/bin/env python3
"""
TPN FPGA Integration Test Suite
Tests the TPN protocol implementation for fpga-network-stack.
"""

import struct
import hashlib
import time
import json
from pathlib import Path

# ============================================================
# TPN Protocol Constants
# ============================================================

HEADER_SIZE = 42
RECEIPT_SIZE = 84
MAX_PAYLOAD = 1400

# Packet Types
TPN_TYPE_DEALLOC = 0x00
TPN_TYPE_DATA = 0x01
TPN_TYPE_GATE = 0x02
TPN_TYPE_BRANCH = 0x03
TPN_TYPE_RETURN = 0x04
TPN_TYPE_CHAIN = 0x05

# Flags
TPN_FLAG_SELF_DESCRIBING = 0x01
TPN_FLAG_CHAINED = 0x02
TPN_FLAG_RETURN = 0x04
TPN_FLAG_VERIFIED = 0x08

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
# TPN Packet Structure
# ============================================================

class TPNPacket:
    """Represents a TPN packet."""

    def __init__(self):
        self.id = 0  # 128-bit IPv6
        self.phase = 0  # 32-bit IPv4
        self.angle = 0  # 32-bit
        self.value = 0  # 64-bit
        self.type = TPN_TYPE_DATA
        self.flags = 0
        self.isa_id = 0
        self.payload_length = 0
        self.version = 2
        self.checksum = 0
        self.payload = b""

    def pack(self):
        """Pack the packet into bytes."""
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
            0,  # checksum placeholder
        )
        # Calculate checksum
        self.checksum = self._calculate_checksum(header)
        header = header[:-2] + struct.pack("!H", self.checksum)
        return header + self.payload

    def unpack(self, data):
        """Unpack bytes into a TPN packet."""
        if len(data) < HEADER_SIZE:
            raise ValueError("Data too short for TPN header")

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
        """Calculate CRC-16 checksum."""
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
        """Verify the packet checksum."""
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
            0,  # checksum placeholder
        )
        return self._calculate_checksum(header) == self.checksum

    def __repr__(self):
        return (
            f"TPNPacket(type={self.type:#x}, flags={self.flags:#x}, "
            f"version={self.version}, payload_len={self.payload_length})"
        )


# ============================================================
# TPN Receipt Structure
# ============================================================

class TPNReceipt:
    """Represents a TPN receipt."""

    def __init__(self):
        self.packet_id = 0
        self.timestamp = 0
        self.result = 0
        self.proof = b"\x00" * 32  # SHA-256
        self.signature = b"\x00" * 32  # Ed25519

    def pack(self):
        """Pack the receipt into bytes."""
        return struct.pack(
            "!IQ8s32s32s",
            self.packet_id,
            self.timestamp,
            self.result.to_bytes(8, "big"),
            self.proof,
            self.signature,
        )

    def unpack(self, data):
        """Unpack bytes into a TPN receipt."""
        if len(data) < RECEIPT_SIZE:
            raise ValueError("Data too short for TPN receipt")

        (
            self.packet_id,
            self.timestamp,
            result_bytes,
            self.proof,
            self.signature,
        ) = struct.unpack("!IQ8s32s32s", data)

        self.result = int.from_bytes(result_bytes, "big")
        return self

    def generate_proof(self, packet_data):
        """Generate SHA-256 proof of execution."""
        self.proof = hashlib.sha256(packet_data).digest()
        return self.proof

    def __repr__(self):
        return f"TPNReceipt(packet_id={self.packet_id}, timestamp={self.timestamp})"


# ============================================================
# TPN Simulator
# ============================================================

class TPNRegister:
    """Represents a TPN register at an IP address."""

    def __init__(self, ipv6, ipv4):
        self.id = ipv6
        self.phase = ipv4
        self.value = 0
        self.angle = 0
        self.isa = None
        self.receipts = []

    def execute(self, packet):
        """Execute a packet on this register."""
        if packet.type == TPN_TYPE_DATA:
            self.value = packet.value
        elif packet.type == TPN_TYPE_GATE:
            self.value = self._execute_gate(packet)
        elif packet.type == TPN_TYPE_RETURN:
            pass  # Return handled by network

        # Generate receipt
        receipt = TPNReceipt()
        receipt.packet_id = packet.id & 0xFFFFFFFF
        receipt.timestamp = int(time.time() * 1e9)
        receipt.result = self.value
        receipt.generate_proof(packet.pack())
        self.receipts.append(receipt)

        return receipt

    def _execute_gate(self, packet):
        """Execute a logic gate."""
        # Simplified gate execution
        return self.value


class TPNNetwork:
    """Simulates a TPN network."""

    def __init__(self):
        self.registers = {}
        self.packets_processed = 0
        self.receipts_generated = 0

    def create_register(self, ipv6, ipv4):
        """Create a new register."""
        reg = TPNRegister(ipv6, ipv4)
        self.registers[ipv6] = reg
        return reg

    def send_packet(self, packet):
        """Send a packet to a register."""
        if packet.id not in self.registers:
            raise ValueError(f"Register {packet.id:#x} not found")

        reg = self.registers[packet.id]
        receipt = reg.execute(packet)

        self.packets_processed += 1
        self.receipts_generated += 1

        return receipt

    def get_stats(self):
        """Get network statistics."""
        return {
            "registers": len(self.registers),
            "packets_processed": self.packets_processed,
            "receipts_generated": self.receipts_generated,
        }


# ============================================================
# Test Suite
# ============================================================

def test_packet_packing():
    """Test packet packing and unpacking."""
    print("=" * 60)
    print("TEST 1: PACKET PACKING/UNPACKING")
    print("=" * 60)

    packet = TPNPacket()
    packet.id = 0x20010DB8000000000000000000000001
    packet.phase = 0xC0A80101
    packet.angle = 0x00000000
    packet.value = 0x123456789ABCDEF0
    packet.type = TPN_TYPE_GATE
    packet.flags = TPN_FLAG_SELF_DESCRIBING
    packet.isa_id = 0
    packet.payload_length = 4
    packet.version = 2
    packet.payload = b"\x01\x02\x03\x04"

    packed = packet.pack()
    print(f"Packed packet: {len(packed)} bytes")
    print(f"Header: {packed[:HEADER_SIZE].hex()}")
    print(f"Payload: {packed[HEADER_SIZE:].hex()}")

    unpacked = TPNPacket().unpack(packed)
    print(f"Unpacked: {unpacked}")
    print(f"Checksum valid: {unpacked.verify_checksum()}")

    assert unpacked.id == packet.id
    assert unpacked.phase == packet.phase
    assert unpacked.value == packet.value
    assert unpacked.type == packet.type
    assert unpacked.payload == packet.payload

    print("PASS: Packet packing/unpacking works correctly")
    return True


def test_receipt_generation():
    """Test receipt generation."""
    print("\n" + "=" * 60)
    print("TEST 2: RECEIPT GENERATION")
    print("=" * 60)

    receipt = TPNReceipt()
    receipt.packet_id = 12345
    receipt.timestamp = int(time.time() * 1e9)
    receipt.result = 0xDEADBEEF

    proof = receipt.generate_proof(b"test data")
    print(f"Proof (SHA-256): {proof.hex()}")

    packed = receipt.pack()
    print(f"Packed receipt: {len(packed)} bytes")

    unpacked = TPNReceipt().unpack(packed)
    print(f"Unpacked: {unpacked}")

    assert unpacked.packet_id == receipt.packet_id
    assert unpacked.timestamp == receipt.timestamp
    assert unpacked.result == receipt.result
    assert unpacked.proof == receipt.proof

    print("PASS: Receipt generation works correctly")
    return True


def test_network_simulation():
    """Test network simulation."""
    print("\n" + "=" * 60)
    print("TEST 3: NETWORK SIMULATION")
    print("=" * 60)

    network = TPNNetwork()

    # Create registers
    reg1 = network.create_register(0x20010DB8000000000000000000000001, 0xC0A80101)
    reg2 = network.create_register(0x20010DB8000000000000000000000002, 0xC0A80102)

    print(f"Created {len(network.registers)} registers")

    # Send packets
    for i in range(10):
        packet = TPNPacket()
        packet.id = 0x20010DB8000000000000000000000001
        packet.phase = 0xC0A80101
        packet.type = TPN_TYPE_DATA
        packet.value = i * 100
        packet.payload_length = 0
        packet.version = 2

        receipt = network.send_packet(packet)
        print(f"  Packet {i}: value={packet.value}, receipt_id={receipt.packet_id}")

    stats = network.get_stats()
    print(f"\nNetwork stats: {stats}")

    assert stats["registers"] == 2
    assert stats["packets_processed"] == 10
    assert stats["receipts_generated"] == 10

    print("PASS: Network simulation works correctly")
    return True


def test_checksum():
    """Test checksum calculation."""
    print("\n" + "=" * 60)
    print("TEST 4: CHECKSUM VERIFICATION")
    print("=" * 60)

    packet = TPNPacket()
    packet.id = 0x20010DB8000000000000000000000001
    packet.phase = 0xC0A80101
    packet.angle = 0
    packet.value = 0
    packet.type = TPN_TYPE_DATA
    packet.flags = 0
    packet.isa_id = 0
    packet.payload_length = 0
    packet.version = 2

    packed = packet.pack()
    unpacked = TPNPacket().unpack(packed)

    print(f"Original checksum: {packet.checksum:#06x}")
    print(f"Unpacked checksum: {unpacked.checksum:#06x}")
    print(f"Checksum valid: {unpacked.verify_checksum()}")

    assert unpacked.verify_checksum()

    # Test corruption detection
    corrupted = bytearray(packed)
    corrupted[20] ^= 0xFF  # Flip bits in angle field
    corrupted_unpacked = TPNPacket().unpack(bytes(corrupted))
    if corrupted_unpacked.verify_checksum():
        print("FAIL: Corruption not detected")
        return False
    else:
        print("Corruption detected: checksum verification failed as expected")

    print("PASS: Checksum verification works correctly")
    return True


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("TPN FPGA INTEGRATION TEST SUITE")
    print("=" * 60)

    results = {}

    try:
        results["packet_packing"] = test_packet_packing()
    except Exception as e:
        print(f"FAIL: {e}")
        results["packet_packing"] = False

    try:
        results["receipt_generation"] = test_receipt_generation()
    except Exception as e:
        print(f"FAIL: {e}")
        results["receipt_generation"] = False

    try:
        results["network_simulation"] = test_network_simulation()
    except Exception as e:
        print(f"FAIL: {e}")
        results["network_simulation"] = False

    try:
        results["checksum"] = test_checksum()
    except Exception as e:
        print(f"FAIL: {e}")
        results["checksum"] = False

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(results.values())
    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")

    # Save results
    with open("/tmp/TPA-fpga/test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
