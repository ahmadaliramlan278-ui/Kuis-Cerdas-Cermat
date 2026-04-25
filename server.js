const http = require('http');
const fs = require('fs');
const path = require('path');
const { Server } = require('socket.io');

const PUBLIC_DIR = path.join(__dirname);
const port = process.env.PORT || 8000;

const mimeTypes = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain'
};

const server = http.createServer((req, res) => {
  let filePath = req.url === '/' ? '/index.html' : req.url;
  filePath = decodeURIComponent(filePath.split('?')[0]);
  const fullPath = path.join(PUBLIC_DIR, filePath);

  if (!fullPath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403);
    return res.end('Forbidden');
  }

  fs.stat(fullPath, (err, stats) => {
    if (err || !stats.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      return res.end('404 Not Found');
    }

    const ext = path.extname(fullPath).toLowerCase();
    const contentType = mimeTypes[ext] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': contentType });
    fs.createReadStream(fullPath).pipe(res);
  });
});

const io = new Server(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

const rooms = new Map();

io.on('connection', (socket) => {
  console.log('User connected:', socket.id);

  socket.on('hostInit', (data) => {
    const { roomCode, playerId, name, team } = data;
    socket.roomCode = roomCode;
    socket.role = 'host';
    socket.playerId = playerId;
    socket.name = name;
    socket.team = team;

    if (!rooms.has(roomCode)) {
      rooms.set(roomCode, { host: socket, players: new Map() });
    } else {
      rooms.get(roomCode).host = socket;
    }
    console.log(`Host joined room ${roomCode}`);
  });

  socket.on('playerInit', (data) => {
    const { roomCode, playerId, name, team } = data;
    socket.roomCode = roomCode;
    socket.role = 'player';
    socket.playerId = playerId;
    socket.name = name;
    socket.team = team;

    if (!rooms.has(roomCode)) {
      rooms.set(roomCode, { host: null, players: new Map() });
    }
    rooms.get(roomCode).players.set(playerId, socket);

    // Notify host
    const room = rooms.get(roomCode);
    if (room.host) {
      room.host.emit('playerJoin', { roomCode, playerId, name, team });
    }
    console.log(`Player ${name} joined room ${roomCode}`);
  });

  socket.on('disconnect', () => {
    if (!socket.roomCode) return;
    const room = rooms.get(socket.roomCode);
    if (!room) return;

    if (socket.role === 'host') {
      room.host = null;
    } else if (socket.role === 'player') {
      room.players.delete(socket.playerId);
    }

    if (!room.host && room.players.size === 0) {
      rooms.delete(socket.roomCode);
    }
    console.log('User disconnected:', socket.id);
  });

  // Broadcast other messages
  socket.onAny((event, data) => {
    if (event === 'hostInit' || event === 'playerInit' || event === 'disconnect') return;
    if (!socket.roomCode) return;

    const room = rooms.get(socket.roomCode);
    if (!room) return;

    // Broadcast to all in room except sender
    if (room.host && room.host !== socket) {
      room.host.emit(event, data);
    }
    for (const player of room.players.values()) {
      if (player !== socket) {
        player.emit(event, data);
      }
    }
  });
});

server.listen(port, () => {
  console.log(`HTTP + Socket.io server running on http://0.0.0.0:${port}`);
});