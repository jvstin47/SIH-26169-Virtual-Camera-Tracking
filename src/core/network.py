"""
Phoenix-X Aerospace UDP Packet Transport Layer
Problem Statement ID: SIH 26169 (ISRO / SAC)

Provides transparent datagram fragmentation and reassembly for high-bandwidth
optical video streaming over UDP sockets without size limits.
Handles 10% - 30% Salt & Pepper noise payloads (>65 KB) cleanly across network nodes.
"""

import socket
import struct
from typing import Optional, Tuple

HEADER_MAGIC = b"PX01"  # Phoenix-X Protocol v1
HEADER_FORMAT = ">4sIII"  # Magic (4B), FrameID (4B), ChunkIdx (4B), TotalChunks (4B)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
CHUNK_PAYLOAD_SIZE = 8192  # Safe size below macOS/Linux default socket buffers

class UDPSender:
    def __init__(self, sock: socket.socket, target_addr: Tuple[str, int]):
        self.sock = sock
        self.target_addr = target_addr
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 524288)
        except Exception:
            pass

    def send_frame(self, frame_id: int, payload: bytes):
        """Fragments payload into multiple UDP datagrams if needed."""
        total_chunks = max(1, (len(payload) + CHUNK_PAYLOAD_SIZE - 1) // CHUNK_PAYLOAD_SIZE)
        for chunk_idx in range(total_chunks):
            start = chunk_idx * CHUNK_PAYLOAD_SIZE
            end = min(len(payload), start + CHUNK_PAYLOAD_SIZE)
            chunk_data = payload[start:end]
            header = struct.pack(HEADER_FORMAT, HEADER_MAGIC, frame_id, chunk_idx, total_chunks)
            try:
                self.sock.sendto(header + chunk_data, self.target_addr)
            except Exception:
                pass

class UDPReceiver:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 524288)
        except Exception:
            pass
        self.buffers = {}  # frame_id -> {chunk_idx: bytes}
        self.max_saved_frames = 5

    def receive_frame(self) -> Optional[Tuple[int, bytes]]:
        """
        Receives UDP packets and reassembles fragmented frames.
        Returns (frame_id, complete_payload) or None on timeout/partial frame.
        """
        try:
            packet, _ = self.sock.recvfrom(65535)
        except socket.timeout:
            return None

        if len(packet) < HEADER_SIZE:
            return None

        magic, frame_id, chunk_idx, total_chunks = struct.unpack(HEADER_FORMAT, packet[:HEADER_SIZE])
        if magic != HEADER_MAGIC:
            return None

        chunk_data = packet[HEADER_SIZE:]

        if frame_id not in self.buffers:
            self.buffers[frame_id] = {}
            # Prune old frames to avoid memory leak
            if len(self.buffers) > self.max_saved_frames:
                oldest = min(self.buffers.keys())
                del self.buffers[oldest]

        self.buffers[frame_id][chunk_idx] = chunk_data

        if len(self.buffers[frame_id]) == total_chunks:
            # All chunks received! Reassemble in order
            ordered_chunks = [self.buffers[frame_id][i] for i in range(total_chunks)]
            full_payload = b"".join(ordered_chunks)
            del self.buffers[frame_id]
            return frame_id, full_payload

        return None
