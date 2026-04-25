#!/usr/bin/env python3
import base64
import hashlib
import http.server
import json
import os
import socketserver
import struct
import threading

GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
HOST = '0.0.0.0'
PORT = 8000
rooms = {}
rooms_lock = threading.Lock()


def recv_exact(sock, n):
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def decode_frame(sock):
    header = recv_exact(sock, 2)
    if not header:
        return None
    b1, b2 = header[0], header[1]
    masked = b2 & 0x80
    payload_len = b2 & 0x7F
    if payload_len == 126:
        ext = recv_exact(sock, 2)
        if not ext:
            return None
        payload_len = struct.unpack('>H', ext)[0]
    elif payload_len == 127:
        ext = recv_exact(sock, 8)
        if not ext:
            return None
        payload_len = struct.unpack('>Q', ext)[0]
    mask = recv_exact(sock, 4) if masked else None
    payload = recv_exact(sock, payload_len) if payload_len else b''
    if payload is None:
        return None
    if mask:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return payload.decode('utf-8', errors='replace')


def encode_frame(message):
    data = message.encode('utf-8')
    header = bytearray()
    header.append(0x81)
    length = len(data)
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.append(126)
        header.extend(struct.pack('>H', length))
    else:
        header.append(127)
        header.extend(struct.pack('>Q', length))
    return bytes(header) + data


class WebSocketHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        if self.path == '/ws':
            self.handle_websocket()
        else:
            super().do_GET()

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def handle_websocket(self):
        key = self.headers.get('Sec-WebSocket-Key')
        if not key:
            self.send_error(400, 'Missing Sec-WebSocket-Key')
            return
        accept = base64.b64encode(hashlib.sha1((key + GUID).encode('utf-8')).digest()).decode('utf-8')
        self.send_response(101, 'Switching Protocols')
        self.send_header('Upgrade', 'websocket')
        self.send_header('Connection', 'Upgrade')
        self.send_header('Sec-WebSocket-Accept', accept)
        self.end_headers()
        self.wfile.flush()
        self.handle_ws_connection()

    def handle_ws_connection(self):
        conn = self.connection
        client = WebSocketClient(conn, self.client_address)
        try:
            client.run()
        except Exception as exc:
            print(f'WebSocket error: {exc}')
        finally:
            client.close()

    def log_message(self, format, *args):
        return


class WebSocketClient:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.room = None
        self.role = None
        self.player_id = None
        self.alive = True

    def run(self):
        while self.alive:
            message = decode_frame(self.conn)
            if message is None:
                break
            self.handle_message(message)

    def handle_message(self, text):
        try:
            msg = json.loads(text)
        except json.JSONDecodeError:
            print('Invalid JSON from', self.addr)
            return
        msg_type = msg.get('type')
        if msg_type in ('hostInit', 'playerInit'):
            self.room = msg.get('roomCode')
            self.role = 'host' if msg_type == 'hostInit' else 'player'
            self.player_id = msg.get('playerId')
            self.register()
            print(f'[{self.room}] {self.role} connected {self.player_id}')
            if msg_type == 'playerInit':
                self.notify_host_join(msg)
            return
        if not self.room:
            return
        self.broadcast(msg)

    def notify_host_join(self, msg):
        with rooms_lock:
            room = rooms.get(self.room)
            host = room.get('host') if room else None
        if host:
            payload = json.dumps({
                'type': 'playerJoin',
                'roomCode': self.room,
                'playerId': self.player_id,
                'name': msg.get('name'),
                'team': msg.get('team')
            })
            try:
                host.send(payload)
            except Exception:
                pass

    def register(self):
        if not self.room:
            return
        with rooms_lock:
            if self.room not in rooms:
                rooms[self.room] = {'host': None, 'players': set()}
            room = rooms[self.room]
            if self.role == 'host':
                room['host'] = self
            else:
                room['players'].add(self)

    def unregister(self):
        if not self.room:
            return
        with rooms_lock:
            room = rooms.get(self.room)
            if not room:
                return
            if self.role == 'host' and room.get('host') == self:
                room['host'] = None
            elif self.role == 'player':
                room['players'].discard(self)
            if not room.get('host') and not room.get('players'):
                del rooms[self.room]

    def broadcast(self, msg):
        data = json.dumps(msg)
        with rooms_lock:
            room = rooms.get(self.room)
            if not room:
                return
            targets = []
            if room.get('host'):
                targets.append(room['host'])
            targets.extend(room.get('players', []))
        for client in targets:
            if client is self:
                continue
            try:
                client.send(data)
            except Exception:
                pass

    def send(self, data):
        frame = encode_frame(data)
        self.conn.sendall(frame)

    def close(self):
        self.alive = False
        self.unregister()
        try:
            self.conn.close()
        except Exception:
            pass


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def main():
    root = os.path.abspath(os.path.dirname(__file__))
    os.chdir(root)
    server = ThreadedHTTPServer((HOST, PORT), WebSocketHandler)
    print(f'Serving HTTP + WebSocket on http://{HOST}:{PORT}/')
    print('Buka di browser atau HP lewat http://<IP>:%d/' % PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer dihentikan')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()