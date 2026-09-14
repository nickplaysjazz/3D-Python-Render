import queue
import socket
import threading

from shared_state import InputState, decode_packet, encode_packet


class NetworkManager:
    def __init__(self, host, port):
        self.server_address = (host, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(0.25)
        self.incoming = queue.SimpleQueue()
        self.running = False
        self.thread = None
        self.player_id = None
        self._sequence = 0

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.thread.start()
        self._send({"version": 1, "type": "hello"})

    def _send(self, packet):
        self.socket.sendto(encode_packet(packet), self.server_address)

    def send_input(self, forward, backward, left, right, yaw, pitch):
        self._sequence += 1
        input_state = InputState(
            self._sequence, forward, backward, left, right, yaw, pitch
        )
        self._send(input_state.to_packet())

    def poll(self):
        packets = []
        while True:
            try:
                packets.append(self.incoming.get_nowait())
            except queue.Empty:
                return packets

    def _receive_loop(self):
        while self.running:
            try:
                data, _ = self.socket.recvfrom(65535)
                self.incoming.put(decode_packet(data))
            except socket.timeout:
                continue
            except OSError:
                return

    def close(self):
        if not self.running:
            return
        self._send({"version": 1, "type": "leave"})
        self.running = False
        self.socket.close()
