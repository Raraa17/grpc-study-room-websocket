# Smart Study Room Booking System 🏫
### Implementasi gRPC - Integrasi Sistem

---

## 📋 Deskripsi Proyek

Sistem booking ruang belajar kampus berbasis **gRPC** yang memungkinkan mahasiswa
memesan ruangan secara real-time, memonitor ketersediaan, dan menerima notifikasi.

---

## ✅ Fitur Wajib yang Dipenuhi

| Fitur | Implementasi |
|-------|-------------|
| **Unary gRPC** | `BookRoom`, `CancelBooking`, `GetAllRooms`, `GetRoomDetail`, `GetBookingStatus`, `GetUserBookings`, `SendNotification`, `GetNotificationHistory` |
| **Server-side Streaming** | `WatchRoomAvailability` (live update ruangan) & `SubscribeNotifications` (notifikasi real-time) |
| **Error Handling** | `NOT_FOUND`, `PERMISSION_DENIED`, jadwal bentrok, ruangan maintenance, dll |
| **State Management** | In-memory: `ROOMS`, `BOOKINGS`, `USER_BOOKINGS`, `NOTIFICATION_HISTORY` |
| **Multi Client** | Thread-safe dengan `threading.Lock`, mendukung banyak client simultan |
| **3 Services** | `RoomService`, `BookingService`, `NotificationService` |

---

## 🏗️ Arsitektur

```
┌─────────────────────────────────────────────────────────────────┐
│                        gRPC Server (:50051)                     │
│                                                                 │
│  ┌─────────────┐  ┌─────────────────┐  ┌──────────────────────┐│
│  │ RoomService │  │ BookingService  │  │ NotificationService  ││
│  │             │  │                 │  │                      ││
│  │ GetAllRooms │  │ BookRoom        │  │ SubscribeNotifs      ││
│  │ GetRoom     │  │ CancelBooking   │  │ SendNotification     ││
│  │ WatchRooms* │  │ GetStatus       │  │ GetHistory           ││
│  └─────────────┘  │ GetUserBookings │  └──────────────────────┘│
│                   └─────────────────┘                           │
│                                                                 │
│  In-Memory State: ROOMS | BOOKINGS | USER_BOOKINGS | NOTIFS     │
└─────────────────────────────────────────────────────────────────┘
          ↑↑↑ gRPC (Protocol Buffers) ↑↑↑
┌──────────────────────────────────────────────────────────────────┐
│  Client A (Alice)  │  Client B (Bob)  │  Client C (Charlie)     │
│  - Book Room       │  - Book Room     │  - Watch Stream         │
│  - Cancel Booking  │  - View Bookings │  - Subscribe Notifs     │
└──────────────────────────────────────────────────────────────────┘
```

### Alur Streaming:
```
Client ──WatchRoomAvailability()──→ Server (tetap terhubung)
Server ──RoomStatusUpdate stream──→ Client (setiap ada perubahan)

Client ──SubscribeNotifications()──→ Server (tetap terhubung)
Server ──Notification stream──→ Client (saat ada notif baru)
```

---

## 📁 Struktur File

```
grpc-study-room/
│
├── protos/
│   └── study_room.proto         # Definisi semua service & message
│
├── study_room_pb2.py            # Auto-generated dari proto
├── study_room_pb2_grpc.py       # Auto-generated dari proto
│
├── server/
│   └── server.py                # Server dengan 3 service
│
├── client/
│   ├── client.py                # Client interaktif (menu)
│   └── demo.py                  # Demo otomatis semua fitur
│
├── requirements.txt
└── README.md
```

---

## 🚀 Cara Menjalankan

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. (Opsional) Regenerate Proto
```bash
python -m grpc_tools.protoc \
  -I protos \
  -I $(python -c "import grpc_tools; import os; print(os.path.join(os.path.dirname(grpc_tools.__file__), '_proto'))") \
  --python_out=. \
  --grpc_python_out=. \
  protos/study_room.proto
```

### 3. Jalankan Server (Terminal 1)
```bash
python server/server.py
```

### 4. Jalankan Client Interaktif (Terminal 2, 3, dst...)
```bash
python client/client.py
```
Setiap terminal = 1 client berbeda (simulasi multi-user)

### 5. Atau Jalankan Demo Otomatis
```bash
# Terminal 1: server sudah jalan
python client/demo.py
```

---

## 🔌 Proto & Services

### RoomService
```protobuf
service RoomService {
  rpc GetAllRooms(Empty) returns (RoomListResponse);          // Unary
  rpc GetRoomDetail(RoomRequest) returns (RoomDetailResponse); // Unary
  rpc WatchRoomAvailability(WatchRequest)                     // Server-side Streaming
      returns (stream RoomStatusUpdate);
}
```

### BookingService
```protobuf
service BookingService {
  rpc BookRoom(BookingRequest) returns (BookingResponse);      // Unary
  rpc CancelBooking(CancelRequest) returns (CancelResponse);   // Unary
  rpc GetBookingStatus(BookingStatusRequest) returns (...);    // Unary
  rpc GetUserBookings(UserRequest) returns (...);              // Unary
}
```

### NotificationService
```protobuf
service NotificationService {
  rpc SubscribeNotifications(SubscribeRequest)                 // Server-side Streaming
      returns (stream Notification);
  rpc SendNotification(SendNotifRequest) returns (...);        // Unary
  rpc GetNotificationHistory(UserRequest) returns (...);       // Unary
}
```

---

## 🛡️ Error Handling

| Kondisi Error | gRPC Status Code | Response |
|---------------|-----------------|---------|
| Ruangan tidak ditemukan | `NOT_FOUND` | `success=false, message=...` |
| Cancel booking orang lain | `PERMISSION_DENIED` | `success=false, message=...` |
| Ruangan maintenance | - | `success=false, message=...` |
| Jadwal bentrok | - | `success=false, message=...` |
| Melebihi kapasitas | - | `success=false, message=...` |
| Cancel booking yg sudah cancel | - | `success=false, message=...` |

---

## 👥 Anggota Kelompok

- [Nama 1] - [NIM]
- [Nama 2] - [NIM]
- [Nama 3] - [NIM]
