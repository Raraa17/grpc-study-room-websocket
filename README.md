# 🏫 Smart Study Room — gRPC + MQTT

Proyek sistem ruang belajar kampus yang mengimplementasikan **dua protokol komunikasi berbeda**:

| Sub-Project | Protokol | Fokus |
|---|---|---|
| `grpc-study-room/` | gRPC + WebSocket | Booking & manajemen ruangan real-time |
| `mqtt-study-room/` | MQTT 5.0 | Monitoring sensor IoT & notifikasi |

---

## 📁 Struktur Proyek

```
Project-GRPC-AdindaC-ZahraH/
├── grpc-study-room/
│   ├── server/
│   │   └── server.py              # gRPC Server (port 50052)
│   ├── web/
│   │   ├── index.html             # Dashboard Web UI
│   │   ├── style.css              # Styling
│   │   └── app.js                 # WebSocket client logic
│   ├── websocket_bridge.py        # WebSocket Bridge (port 8765)
│   ├── study_room.proto           # Protobuf schema
│   ├── study_room_pb2.py          # Generated (auto)
│   ├── study_room_pb2_grpc.py     # Generated (auto)
│   └── requirements.txt
│
└── mqtt-study-room/
    ├── config.py                  # Konfigurasi broker & topik
    ├── publisher_sensor.py        # Publisher: Sensor IoT
    ├── publisher_security.py      # Publisher: Keamanan
    ├── publisher_admin.py         # Publisher: Admin
    ├── subscriber_monitor.py      # Subscriber: Monitor
    ├── subscriber_logger.py       # Subscriber: Logger
    ├── dashboard.py               # Dashboard Web (Flask + SocketIO)
    └── requirements.txt
```

---

## ⚙️ Prerequisites

- **Python 3.10+**
- Koneksi internet (untuk MQTT broker HiveMQ & Google Fonts)

---

## 🔷 Bagian 1 — gRPC Study Room (Booking Ruangan)

### Arsitektur

```
Browser (index.html)
    ↕ WebSocket ws://localhost:8765
websocket_bridge.py
    ↕ gRPC localhost:50052
server.py
```

### Install Dependencies

```bash
cd grpc-study-room
pip install -r requirements.txt
```

### Jalankan (3 terminal terpisah)

**Terminal 1 — gRPC Server:**
```bash
cd grpc-study-room
python server/server.py
```
> Server berjalan di port `50052`

**Terminal 2 — WebSocket Bridge:**
```bash
cd grpc-study-room
python websocket_bridge.py
```
> Bridge berjalan di `ws://localhost:8765`

**Terminal 3 — Buka Dashboard:**

Buka file langsung di browser:
```
grpc-study-room/web/index.html
```
Atau jika pakai Live Server (VS Code), klik kanan `index.html` → *Open with Live Server*.

### Fitur gRPC
- ✅ Lihat ketersediaan ruangan secara real-time (gRPC Streaming)
- ✅ Booking & batalkan booking
- ✅ Notifikasi real-time via WebSocket
- ✅ Server-Initiated Events (push otomatis setiap 30-120 detik)
- ✅ Dark / Light mode

---

## 🟢 Bagian 2 — MQTT Study Room (Monitoring IoT)

### Arsitektur

```
publisher_sensor.py   ──┐
publisher_security.py ──┤──► broker.hivemq.com ──► subscriber_monitor.py
publisher_admin.py    ──┘                           subscriber_logger.py
                                                           │
                                                     dashboard.py
                                                    (http://localhost:5000)
```

### Install Dependencies

```bash
cd mqtt-study-room
pip install -r requirements.txt
```

### Jalankan (6 terminal terpisah, urutan penting!)

**Terminal 1 — Dashboard Web:**
```bash
cd mqtt-study-room
python dashboard.py
```
> Buka browser: **http://localhost:5000**

**Terminal 2 — Subscriber Monitor:**
```bash
cd mqtt-study-room
python subscriber_monitor.py
```

**Terminal 3 — Subscriber Logger:**
```bash
cd mqtt-study-room
python subscriber_logger.py
```

**Terminal 4 — Publisher Sensor:**
```bash
cd mqtt-study-room
python publisher_sensor.py
```

**Terminal 5 — Publisher Security:**
```bash
cd mqtt-study-room
python publisher_security.py
```

**Terminal 6 — Publisher Admin:**
```bash
cd mqtt-study-room
python publisher_admin.py
```
> Di menu publisher admin, ketik `7` untuk **auto-demo semua fitur MQTT**.

### Urutan yang Disarankan
1. Jalankan `dashboard.py` → buka browser dulu
2. Jalankan kedua subscriber
3. Jalankan ketiga publisher
4. Di publisher admin ketik `7` untuk demo otomatis

### Fitur MQTT 5.0 (10 Fitur)
| # | Fitur | Keterangan |
|---|---|---|
| 1 | Pub/Sub & QoS | QoS 0, 1, 2 untuk tiap jenis data |
| 2 | Topic Wildcards | `+` single-level, `#` multi-level |
| 3 | Topic Alias | Efisiensi bandwidth |
| 4 | User Properties | Metadata device & lokasi |
| 5 | Retain Message | Status tersimpan di broker |
| 6 | Message Expiry | TTL per pesan |
| 7 | Last Will & Testament | Auto-OFFLINE saat publisher mati |
| 8 | Request-Response | Admin request → Sensor response |
| 9 | Shared Subscriptions | Load balancing subscriber |
| 10 | Flow Control | `ReceiveMaximum` backpressure |

---

## 👥 Tim Pengembang

- **Adinda Cahya Pramesti**
- **Zahra Hafizhah**
