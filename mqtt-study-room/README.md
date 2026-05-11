# 🏫 MQTT Smart Study Room - Implementasi 10 Fitur MQTT

Proyek implementasi MQTT untuk monitoring ruang belajar kampus ITS.
Menggunakan broker publik HiveMQ (tanpa hardware).

## 📋 Arsitektur Sistem

```
┌─────────────────────┐
│  Publisher 1: SENSOR │──── its/studyroom/gedungA/R001/suhu (QoS 0)
│  (Suhu, Kelembapan,  │──── its/studyroom/gedungA/R001/kelembapan (QoS 1)
│   Cahaya)            │──── its/studyroom/gedungA/R001/cahaya (QoS 2)
└──────────┬──────────┘
           │
┌──────────▼──────────┐     ┌──────────────────────┐
│                      │     │  Subscriber 1: MONITOR│
│   HiveMQ Broker      │────▶│  (Dashboard Collector)│
│   broker.hivemq.com  │     └──────────────────────┘
│   Port: 1883         │
│                      │     ┌──────────────────────┐
│                      │────▶│  Subscriber 2: LOGGER │
└──────────▲──────────┘     │  (File Archiver)      │
           │                 └──────────────────────┘
┌──────────┴──────────┐
│  Publisher 2:        │──── its/studyroom/security/pintu/R001 (QoS 2)
│  SECURITY            │──── its/studyroom/security/gerakan/R001 (QoS 1)
└─────────────────────┘
           │
┌──────────┴──────────┐
│  Publisher 3: ADMIN  │──── its/studyroom/admin/broadcast (QoS 1)
│  (Perintah & Notif)  │──── its/studyroom/admin/command (QoS 2)
└─────────────────────┘
```

## ✅ 10 Fitur MQTT yang Diimplementasikan

| No | Fitur | Implementasi | File |
|----|-------|-------------|------|
| 1 | **Pub/Sub & QoS** | QoS 0 (suhu), QoS 1 (kelembapan), QoS 2 (keamanan) | Semua publisher |
| 2 | **Topic Wildcards** | `+` single-level, `#` multi-level | subscriber_monitor.py |
| 3 | **Topic Alias** | Mapping topic panjang ke integer ID | publisher_sensor.py, config.py |
| 4 | **User Properties** | Metadata: app-version, device-id, unit, location | publisher_sensor.py, publisher_security.py |
| 5 | **Retain Message** | Status online/offline tersimpan di broker | Semua publisher |
| 6 | **Message Expiry** | Suhu 30s, perintah UNLOCK 10s, broadcast 5min | publisher_sensor.py, publisher_admin.py |
| 7 | **Last Will & Testament** | Auto-publish "OFFLINE" saat publisher mati | Semua publisher |
| 8 | **Request-Response** | Admin request → Sensor response + correlation_id | publisher_admin.py, publisher_sensor.py |
| 9 | **Shared Subscriptions** | `$share/monitor_group/topic` load balancing | subscriber_monitor.py, subscriber_logger.py |
| 10 | **Flow Control** | `ReceiveMaximum` di connect properties | Semua file |

## 🚀 Cara Menjalankan

### 1. Install Dependencies
```bash
cd mqtt-study-room
pip install -r requirements.txt
```

### 2. Jalankan setiap komponen di terminal terpisah

**Terminal 1 — Dashboard Monitoring (Web UI):**
```bash
python dashboard.py
```
Buka browser: http://localhost:5000

**Terminal 2 — Subscriber Monitor:**
```bash
python subscriber_monitor.py
```

**Terminal 3 — Subscriber Logger:**
```bash
python subscriber_logger.py
```

**Terminal 4 — Publisher Sensor:**
```bash
python publisher_sensor.py
```

**Terminal 5 — Publisher Security:**
```bash
python publisher_security.py
```

**Terminal 6 — Publisher Admin:**
```bash
python publisher_admin.py
```
Pilih menu `7` untuk auto-demo semua fitur.

### 3. Urutan yang Disarankan
1. Jalankan `dashboard.py` dulu (buka http://localhost:5000)
2. Jalankan kedua subscriber
3. Jalankan ketiga publisher
4. Di publisher admin, ketik `7` untuk auto-demo

## 📊 Dashboard Monitoring
Dashboard web menampilkan:
- **Statistik real-time**: Total pesan, QoS breakdown, retained count
- **Data sensor**: Suhu, kelembapan, cahaya per ruangan
- **Status publisher**: Online/offline via LWT (Fitur 7)
- **Event keamanan**: Pintu, gerakan, alarm
- **Broadcast admin**: Pengumuman dan perintah
- **Activity log**: Semua pesan MQTT yang masuk

## 📁 Struktur File
```
mqtt-study-room/
├── config.py              # Konfigurasi broker, topic, wildcard
├── publisher_sensor.py    # Publisher 1: Sensor IoT
├── publisher_security.py  # Publisher 2: Keamanan
├── publisher_admin.py     # Publisher 3: Admin
├── subscriber_monitor.py  # Subscriber 1: Monitor
├── subscriber_logger.py   # Subscriber 2: Logger
├── dashboard.py           # Dashboard Web (Flask + MQTT)
├── requirements.txt       # Dependencies
└── README.md              # Dokumentasi
```
