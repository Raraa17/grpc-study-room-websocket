"""
Smart Study Room Booking System - gRPC Server
Implements: RoomService, BookingService, NotificationService
"""

import grpc
import time
import uuid
import random
import threading
from concurrent import futures
from datetime import datetime, timedelta
from google.protobuf import empty_pb2

import sys
sys.path.insert(0, '.')
import study_room_pb2 as pb2
import study_room_pb2_grpc as pb2_grpc

# =============================================
# IN-MEMORY STATE
# =============================================

# Data ruangan kampus
ROOMS = {
    "R001": {
        "room_id": "R001",
        "name": "Ruang Belajar A",
        "capacity": 10,
        "location": "Gedung A, Lt. 2",
        "facilities": ["AC", "Proyektor", "Whiteboard"],
        "status": pb2.AVAILABLE,
        "current_occupancy": 0
    },
    "R002": {
        "room_id": "R002",
        "name": "Lab Komputer B",
        "capacity": 20,
        "location": "Gedung B, Lt. 1",
        "facilities": ["AC", "Komputer", "Internet", "Proyektor"],
        "status": pb2.AVAILABLE,
        "current_occupancy": 0
    },
    "R003": {
        "room_id": "R003",
        "name": "Ruang Diskusi C",
        "capacity": 6,
        "location": "Gedung C, Lt. 3",
        "facilities": ["AC", "TV", "Whiteboard"],
        "status": pb2.AVAILABLE,
        "current_occupancy": 0
    },
    "R004": {
        "room_id": "R004",
        "name": "Auditorium Mini",
        "capacity": 50,
        "location": "Gedung D, Lt. 1",
        "facilities": ["AC", "Proyektor", "Sound System", "Mic"],
        "status": pb2.AVAILABLE,
        "current_occupancy": 0
    },
    "R005": {
        "room_id": "R005",
        "name": "Ruang Tenang E",
        "capacity": 8,
        "location": "Perpustakaan, Lt. 2",
        "facilities": ["AC", "Meja Individual", "Loker"],
        "status": pb2.MAINTENANCE,
        "current_occupancy": 0
    },
}

# State bookings: {booking_id: booking_data}
BOOKINGS = {}
# State user bookings: {user_id: [booking_id]}
USER_BOOKINGS = {}
# State notification history: {user_id: [notif]}
NOTIFICATION_HISTORY = {}

# Lock untuk thread-safe access
state_lock = threading.Lock()

# Queue untuk streaming: {user_id: queue}
room_watchers = {}   # room_id -> list of queues
notif_subscribers = {}  # user_id -> queue
watchers_lock = threading.Lock()

def ts():
    """Get current timestamp string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def gen_id(prefix=""):
    return prefix + str(uuid.uuid4())[:8].upper()

def broadcast_room_update(room_id, event_type):
    """Push room status update ke semua watcher"""
    room = ROOMS.get(room_id)
    if not room:
        return
    update = pb2.RoomStatusUpdate(
        room_id=room_id,
        room_name=room["name"],
        status=room["status"],
        capacity=room["capacity"],
        current_occupancy=room["current_occupancy"],
        timestamp=ts(),
        event_type=event_type
    )
    with watchers_lock:
        to_remove = []
        for watcher_id, q in room_watchers.items():
            try:
                q.put(update)
            except Exception:
                to_remove.append(watcher_id)
        for w in to_remove:
            del room_watchers[w]

def push_notification(user_id, title, message, notif_type, room_id="", booking_id=""):
    """Push notifikasi ke subscriber dan simpan ke history"""
    notif = pb2.Notification(
        notif_id=gen_id("N"),
        user_id=user_id,
        title=title,
        message=message,
        type=notif_type,
        timestamp=ts(),
        room_id=room_id,
        booking_id=booking_id
    )
    # Simpan ke history
    with state_lock:
        if user_id not in NOTIFICATION_HISTORY:
            NOTIFICATION_HISTORY[user_id] = []
        NOTIFICATION_HISTORY[user_id].append(notif)

    # Push ke subscriber jika online
    with watchers_lock:
        if user_id in notif_subscribers:
            try:
                notif_subscribers[user_id].put(notif)
            except Exception:
                pass

    # Broadcast ke subscriber global (user_id="*")
    with watchers_lock:
        if "*" in notif_subscribers:
            try:
                notif_subscribers["*"].put(notif)
            except Exception:
                pass

# =============================================
# ROOM SERVICE
# =============================================
class RoomServiceServicer(pb2_grpc.RoomServiceServicer):

    def GetAllRooms(self, request, context):
        print(f"[RoomService] GetAllRooms dipanggil")
        with state_lock:
            rooms = []
            for r in ROOMS.values():
                rooms.append(pb2.RoomInfo(
                    room_id=r["room_id"],
                    name=r["name"],
                    capacity=r["capacity"],
                    location=r["location"],
                    facilities=r["facilities"],
                    status=r["status"],
                    current_occupancy=r["current_occupancy"]
                ))
        return pb2.RoomListResponse(rooms=rooms, success=True, message=f"{len(rooms)} ruangan ditemukan")

    def GetRoomDetail(self, request, context):
        print(f"[RoomService] GetRoomDetail: {request.room_id}")
        with state_lock:
            room = ROOMS.get(request.room_id)
            if not room:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Ruangan {request.room_id} tidak ditemukan")
                return pb2.RoomDetailResponse(success=False, message="Ruangan tidak ditemukan")

            room_info = pb2.RoomInfo(
                room_id=room["room_id"],
                name=room["name"],
                capacity=room["capacity"],
                location=room["location"],
                facilities=room["facilities"],
                status=room["status"],
                current_occupancy=room["current_occupancy"]
            )

            # Cari booking aktif untuk ruangan ini
            active_bookings = []
            for b in BOOKINGS.values():
                if b["room_id"] == request.room_id and b["status"] == "ACTIVE":
                    active_bookings.append(pb2.BookingSlot(
                        booking_id=b["booking_id"],
                        user_id=b["user_id"],
                        user_name=b["user_name"],
                        start_time=b["start_time"],
                        end_time=b["end_time"]
                    ))

        return pb2.RoomDetailResponse(
            room=room_info,
            active_bookings=active_bookings,
            success=True,
            message="OK"
        )

    def WatchRoomAvailability(self, request, context):
        """Server-side streaming: kirim update ketersediaan ruangan secara real-time"""
        import queue
        client_id = request.client_id or gen_id("C")
        print(f"[RoomService] Client {client_id} mulai watching room availability")

        q = queue.Queue()
        with watchers_lock:
            room_watchers[client_id] = q

        # Kirim status awal semua ruangan
        with state_lock:
            for room in ROOMS.values():
                yield pb2.RoomStatusUpdate(
                    room_id=room["room_id"],
                    room_name=room["name"],
                    status=room["status"],
                    capacity=room["capacity"],
                    current_occupancy=room["current_occupancy"],
                    timestamp=ts(),
                    event_type="INITIAL_STATUS"
                )

        # Loop: tunggu update
        try:
            while True:
                if not context.is_active():
                    break
                try:
                    update = q.get(timeout=30)
                    yield update
                except Exception:
                    # Heartbeat jika tidak ada update
                    yield pb2.RoomStatusUpdate(
                        room_id="*",
                        room_name="",
                        timestamp=ts(),
                        event_type="HEARTBEAT"
                    )
        finally:
            with watchers_lock:
                room_watchers.pop(client_id, None)
            print(f"[RoomService] Client {client_id} berhenti watching")


# =============================================
# BOOKING SERVICE
# =============================================
class BookingServiceServicer(pb2_grpc.BookingServiceServicer):

    def BookRoom(self, request, context):
        print(f"[BookingService] Booking dari {request.user_name} untuk ruangan {request.room_id}")

        with state_lock:
            # Validasi ruangan
            room = ROOMS.get(request.room_id)
            if not room:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Ruangan tidak ditemukan")
                return pb2.BookingResponse(
                    success=False,
                    message=f"Ruangan {request.room_id} tidak ditemukan"
                )

            # Validasi status ruangan
            if room["status"] == pb2.MAINTENANCE:
                return pb2.BookingResponse(
                    success=False,
                    message=f"Ruangan {room['name']} sedang dalam maintenance"
                )

            if room["status"] == pb2.FULL:
                return pb2.BookingResponse(
                    success=False,
                    message=f"Ruangan {room['name']} sudah penuh"
                )

            # Validasi kapasitas
            if request.num_people > room["capacity"]:
                return pb2.BookingResponse(
                    success=False,
                    message=f"Jumlah orang ({request.num_people}) melebihi kapasitas ruangan ({room['capacity']})"
                )

            # Cek konflik jadwal
            start_dt = datetime.strptime(f"{request.date} {request.start_time}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{request.date} {request.end_time}", "%Y-%m-%d %H:%M")

            if end_dt <= start_dt:
                return pb2.BookingResponse(
                    success=False,
                    message="Waktu selesai harus lebih besar dari waktu mulai"
                )

            for b in BOOKINGS.values():
                if b["room_id"] == request.room_id and b["status"] == "ACTIVE" and b["date"] == request.date:
                    b_start = datetime.strptime(f"{b['date']} {b['start_time']}", "%Y-%m-%d %H:%M")
                    b_end = datetime.strptime(f"{b['date']} {b['end_time']}", "%Y-%m-%d %H:%M")
                    # Cek overlap
                    if not (end_dt <= b_start or start_dt >= b_end):
                        return pb2.BookingResponse(
                            success=False,
                            message=f"Jadwal bentrok dengan booking {b['booking_id']} ({b['start_time']}-{b['end_time']})"
                        )

            # Buat booking
            booking_id = gen_id("BK")
            confirm_code = gen_id("CONF")

            booking = {
                "booking_id": booking_id,
                "user_id": request.user_id,
                "user_name": request.user_name,
                "room_id": request.room_id,
                "room_name": room["name"],
                "date": request.date,
                "start_time": request.start_time,
                "end_time": request.end_time,
                "num_people": request.num_people,
                "purpose": request.purpose,
                "status": "ACTIVE",
                "confirmation_code": confirm_code,
                "created_at": ts()
            }

            BOOKINGS[booking_id] = booking

            if request.user_id not in USER_BOOKINGS:
                USER_BOOKINGS[request.user_id] = []
            USER_BOOKINGS[request.user_id].append(booking_id)

            # Update occupancy ruangan
            room["current_occupancy"] += request.num_people
            if room["current_occupancy"] >= room["capacity"]:
                room["status"] = pb2.FULL
                event = "FULL"
            else:
                room["status"] = pb2.OCCUPIED
                event = "BOOKED"

        # Broadcast update ruangan
        broadcast_room_update(request.room_id, event)

        # Kirim notifikasi ke user
        push_notification(
            user_id=request.user_id,
            title="Booking Berhasil! 🎉",
            message=f"Booking ruangan {room['name']} pada {request.date} pukul {request.start_time}-{request.end_time} berhasil. Kode: {confirm_code}",
            notif_type="BOOKING_CONFIRMED",
            room_id=request.room_id,
            booking_id=booking_id
        )

        # Jika ruangan penuh, notifikasi broadcast
        if room["status"] == pb2.FULL:
            push_notification(
                user_id="*",
                title=f"Ruangan Penuh: {room['name']}",
                message=f"Ruangan {room['name']} telah penuh pada {request.date}",
                notif_type="ROOM_FULL",
                room_id=request.room_id
            )

        print(f"[BookingService] Booking {booking_id} berhasil dibuat")
        return pb2.BookingResponse(
            success=True,
            booking_id=booking_id,
            message=f"Booking berhasil! Ruangan {room['name']} dipesan untuk {request.date} pukul {request.start_time}-{request.end_time}",
            room_name=room["name"],
            confirmation_code=confirm_code
        )

    def CancelBooking(self, request, context):
        print(f"[BookingService] CancelBooking: {request.booking_id} oleh {request.user_id}")

        with state_lock:
            booking = BOOKINGS.get(request.booking_id)

            if not booking:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return pb2.CancelResponse(
                    success=False,
                    message=f"Booking {request.booking_id} tidak ditemukan"
                )

            if booking["user_id"] != request.user_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                return pb2.CancelResponse(
                    success=False,
                    message="Anda tidak memiliki izin untuk membatalkan booking ini"
                )

            if booking["status"] == "CANCELLED":
                return pb2.CancelResponse(
                    success=False,
                    message="Booking sudah dibatalkan sebelumnya"
                )

            # Update status booking
            booking["status"] = "CANCELLED"
            booking["cancel_reason"] = request.reason

            # Update room occupancy
            room = ROOMS.get(booking["room_id"])
            if room:
                room["current_occupancy"] = max(0, room["current_occupancy"] - booking["num_people"])
                if room["current_occupancy"] == 0:
                    room["status"] = pb2.AVAILABLE
                else:
                    room["status"] = pb2.OCCUPIED

        # Broadcast update
        broadcast_room_update(booking["room_id"], "CANCELLED")

        # Kirim notifikasi
        push_notification(
            user_id=request.user_id,
            title="Booking Dibatalkan",
            message=f"Booking ruangan {booking['room_name']} pada {booking['date']} pukul {booking['start_time']}-{booking['end_time']} telah dibatalkan.",
            notif_type="BOOKING_CANCELLED",
            room_id=booking["room_id"],
            booking_id=request.booking_id
        )

        return pb2.CancelResponse(
            success=True,
            message=f"Booking {request.booking_id} berhasil dibatalkan",
            booking_id=request.booking_id
        )

    def GetBookingStatus(self, request, context):
        with state_lock:
            booking = BOOKINGS.get(request.booking_id)
            if not booking:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return pb2.BookingStatusResponse(
                    success=False,
                    message=f"Booking {request.booking_id} tidak ditemukan"
                )
            return pb2.BookingStatusResponse(
                success=True,
                booking_id=booking["booking_id"],
                status=booking["status"],
                room_name=booking["room_name"],
                user_name=booking["user_name"],
                start_time=f"{booking['date']} {booking['start_time']}",
                end_time=f"{booking['date']} {booking['end_time']}",
                message="OK"
            )

    def GetUserBookings(self, request, context):
        with state_lock:
            booking_ids = USER_BOOKINGS.get(request.user_id, [])
            bookings = []
            for bid in booking_ids:
                b = BOOKINGS.get(bid)
                if b:
                    bookings.append(pb2.BookingInfo(
                        booking_id=b["booking_id"],
                        room_id=b["room_id"],
                        room_name=b["room_name"],
                        date=b["date"],
                        start_time=b["start_time"],
                        end_time=b["end_time"],
                        status=b["status"],
                        purpose=b["purpose"],
                        confirmation_code=b["confirmation_code"]
                    ))
        return pb2.UserBookingsResponse(
            success=True,
            bookings=bookings,
            total=len(bookings)
        )


# =============================================
# NOTIFICATION SERVICE
# =============================================
class NotificationServiceServicer(pb2_grpc.NotificationServiceServicer):

    def SubscribeNotifications(self, request, context):
        """Server-side streaming: kirim notifikasi real-time ke user"""
        import queue
        user_id = request.user_id
        print(f"[NotificationService] User {request.user_name} ({user_id}) subscribe notifikasi")

        q = queue.Queue()
        with watchers_lock:
            notif_subscribers[user_id] = q

        # Kirim welcome notif
        yield pb2.Notification(
            notif_id=gen_id("N"),
            user_id=user_id,
            title="Terhubung! 🔔",
            message=f"Halo {request.user_name}! Anda akan menerima notifikasi booking secara real-time.",
            type="SYSTEM",
            timestamp=ts()
        )

        try:
            while True:
                if not context.is_active():
                    break
                try:
                    notif = q.get(timeout=30)
                    yield notif
                except Exception:
                    # Heartbeat
                    yield pb2.Notification(
                        notif_id="HB",
                        user_id=user_id,
                        type="HEARTBEAT",
                        timestamp=ts()
                    )
        finally:
            with watchers_lock:
                notif_subscribers.pop(user_id, None)
            print(f"[NotificationService] User {user_id} unsubscribe")

    def SendNotification(self, request, context):
        """Admin send notifikasi manual"""
        push_notification(
            user_id=request.target_user_id if request.target_user_id else "*",
            title=request.title,
            message=request.message,
            notif_type=request.type,
            room_id=request.room_id
        )
        print(f"[NotificationService] Notifikasi dikirim: {request.title}")
        return pb2.SendNotifResponse(success=True, message="Notifikasi terkirim", recipients=1)

    def GetNotificationHistory(self, request, context):
        with state_lock:
            history = NOTIFICATION_HISTORY.get(request.user_id, [])
        return pb2.NotificationHistoryResponse(
            success=True,
            notifications=list(history),
            total=len(history)
        )


# =============================================
# BACKGROUND TASK: AUTO-EXPIRE BOOKINGS
# =============================================
def booking_expiry_checker():
    """
    Background thread: setiap 15 detik cek booking yang sudah expired.
    Jika waktu booking (date + end_time) sudah lewat, otomatis:
    - Ubah status booking ke COMPLETED
    - Kurangi occupancy ruangan
    - Update status ruangan (AVAILABLE jika kosong)
    - Broadcast room update ke semua watcher (real-time)
    - Kirim notifikasi ke user
    """
    print("[Expiry Checker] Background task aktif — cek setiap 15 detik")
    while True:
        time.sleep(15)
        now = datetime.now()
        expired_bookings = []

        with state_lock:
            for booking_id, b in BOOKINGS.items():
                if b["status"] != "ACTIVE":
                    continue
                try:
                    end_dt = datetime.strptime(f"{b['date']} {b['end_time']}", "%Y-%m-%d %H:%M")
                    if now >= end_dt:
                        expired_bookings.append(booking_id)
                except (ValueError, KeyError):
                    continue

            # Process expired bookings
            for booking_id in expired_bookings:
                b = BOOKINGS[booking_id]
                b["status"] = "COMPLETED"
                room = ROOMS.get(b["room_id"])
                if room:
                    room["current_occupancy"] = max(0, room["current_occupancy"] - b["num_people"])
                    if room["current_occupancy"] == 0:
                        room["status"] = pb2.AVAILABLE
                    else:
                        room["status"] = pb2.OCCUPIED
                print(f"[Expiry Checker] Booking {booking_id} expired — {b['room_name']} "
                      f"({b['date']} {b['start_time']}-{b['end_time']})")

        # Broadcast updates OUTSIDE the state_lock to avoid deadlocks
        for booking_id in expired_bookings:
            b = BOOKINGS[booking_id]
            broadcast_room_update(b["room_id"], "BOOKING_EXPIRED")
            push_notification(
                user_id=b["user_id"],
                title="⏰ Booking Selesai",
                message=f"Booking ruangan {b['room_name']} ({b['start_time']}-{b['end_time']}) telah selesai. Ruangan kembali tersedia.",
                notif_type="BOOKING_COMPLETED",
                room_id=b["room_id"],
                booking_id=booking_id
            )

        if expired_bookings:
            print(f"[Expiry Checker] {len(expired_bookings)} booking expired pada {ts()}")


# =============================================
# SERVER MAIN
# =============================================
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))

    pb2_grpc.add_RoomServiceServicer_to_server(RoomServiceServicer(), server)
    pb2_grpc.add_BookingServiceServicer_to_server(BookingServiceServicer(), server)
    pb2_grpc.add_NotificationServiceServicer_to_server(NotificationServiceServicer(), server)

    server.add_insecure_port('[::]:50052')
    server.start()

    print("=" * 60)
    print("  Smart Study Room Booking System - gRPC Server")
    print("  Port: 50052")
    print("  Services: RoomService, BookingService, NotificationService")
    print("=" * 60)
    print(f"  Ruangan tersedia: {len(ROOMS)}")
    print(f"  Server aktif: {ts()}")
    print("=" * 60)

    # Start background expiry checker thread
    expiry_thread = threading.Thread(target=booking_expiry_checker, daemon=True)
    expiry_thread.start()
    print("  [✓] Booking expiry checker aktif (setiap 15 detik)")
    print("=" * 60)

    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        print("\n[Server] Shutting down...")
        server.stop(0)

if __name__ == '__main__':
    serve()
