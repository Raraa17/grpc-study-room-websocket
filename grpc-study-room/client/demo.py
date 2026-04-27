"""
Demo Script - Smart Study Room Booking System
Mendemonstrasikan semua fitur secara otomatis
"""

import grpc
import threading
import time
import sys
from datetime import date

sys.path.insert(0, '.')
import study_room_pb2 as pb2
import study_room_pb2_grpc as pb2_grpc
from google.protobuf import empty_pb2

SERVER_ADDRESS = 'localhost:50051'

def get_stubs():
    channel = grpc.insecure_channel(SERVER_ADDRESS)
    return (
        pb2_grpc.RoomServiceStub(channel),
        pb2_grpc.BookingServiceStub(channel),
        pb2_grpc.NotificationServiceStub(channel)
    )

def divider(title):
    print(f"\n{'='*55}")
    print(f"  🧪 TEST: {title}")
    print(f"{'='*55}")

def ok(msg):   print(f"  ✅ {msg}")
def fail(msg): print(f"  ❌ {msg}")
def info(msg): print(f"  ℹ️  {msg}")

room_stub, booking_stub, notif_stub = get_stubs()
today = date.today().isoformat()

# =============================================
# Background streaming listeners
# =============================================
received_notifs       = []
received_room_updates = []

def listen_room_stream():
    try:
        for update in room_stub.WatchRoomAvailability(
                pb2.WatchRequest(client_id="DEMO_WATCHER")):
            if update.event_type not in ("HEARTBEAT", "INITIAL_STATUS"):
                received_room_updates.append(update)
                info(f"[STREAM] Room update: {update.room_name} → {update.event_type}")
    except grpc.RpcError:
        pass

def listen_notif_stream():
    try:
        for notif in notif_stub.SubscribeNotifications(
                pb2.SubscribeRequest(user_id="U001", user_name="Alice")):
            if notif.type not in ("HEARTBEAT", "SYSTEM"):
                received_notifs.append(notif)
                info(f"[NOTIF → Alice] {notif.title}: {notif.message[:55]}...")
    except grpc.RpcError:
        pass

threading.Thread(target=listen_room_stream,  daemon=True).start()
threading.Thread(target=listen_notif_stream, daemon=True).start()
time.sleep(1.5)

print("\n" + "="*55)
print("  SMART STUDY ROOM BOOKING SYSTEM — DEMO")
print("="*55)

# =============================================
# TEST 1: GetAllRooms (Unary)
# =============================================
divider("GET ALL ROOMS  [Unary · RoomService]")
resp = room_stub.GetAllRooms(empty_pb2.Empty())
if resp.success:
    ok(f"Berhasil mendapat {len(resp.rooms)} ruangan:")
    STATUS_LABEL = {
        pb2.AVAILABLE:   "Tersedia",
        pb2.OCCUPIED:    "Terisi",
        pb2.FULL:        "Penuh",
        pb2.MAINTENANCE: "Maintenance",
    }
    for r in resp.rooms:
        print(f"     [{r.room_id}] {r.name:<22} | kap: {r.capacity:>2} | {STATUS_LABEL.get(r.status,'?')}")
else:
    fail(f"Gagal: {resp.message}")

# =============================================
# TEST 2: GetRoomDetail (Unary)
# =============================================
divider("GET ROOM DETAIL  [Unary · RoomService]")

resp = room_stub.GetRoomDetail(pb2.RoomRequest(room_id="R001"))
if resp.success:
    ok(f"Detail ruangan: {resp.room.name}")
    print(f"     Lokasi   : {resp.room.location}")
    print(f"     Fasilitas: {', '.join(resp.room.facilities)}")
else:
    fail(f"Gagal: {resp.message}")

# error handling — room tidak ada (throws gRPC exception)
try:
    room_stub.GetRoomDetail(pb2.RoomRequest(room_id="INVALID"))
    fail("Seharusnya error!")
except grpc.RpcError as e:
    ok(f"Error handling NOT_FOUND: [{e.code()}] '{e.details()}'")

# =============================================
# TEST 3: BookRoom — Multi Client (Unary)
# =============================================
divider("BOOK ROOM — MULTI CLIENT  [Unary · BookingService]")

alice_booking_id = None
bob_booking_id   = None

# Alice booking R001
info("Alice booking R001 (09:00–11:00, 4 orang)...")
try:
    r = booking_stub.BookRoom(pb2.BookingRequest(
        user_id="U001", user_name="Alice",
        room_id="R001", date=today,
        start_time="09:00", end_time="11:00",
        num_people=4, purpose="Belajar kelompok Integrasi Sistem"
    ))
    if r.success:
        ok(f"Alice berhasil! ID: {r.booking_id}  Kode: {r.confirmation_code}")
        alice_booking_id = r.booking_id
    else:
        fail(f"Alice gagal: {r.message}")
except grpc.RpcError as e:
    fail(f"Alice error: {e.details()}")

# Bob booking R002
info("Bob booking R002 (10:00–12:00, 15 orang)...")
try:
    r = booking_stub.BookRoom(pb2.BookingRequest(
        user_id="U002", user_name="Bob",
        room_id="R002", date=today,
        start_time="10:00", end_time="12:00",
        num_people=15, purpose="Praktikum Pemrograman"
    ))
    if r.success:
        ok(f"Bob berhasil! ID: {r.booking_id}")
        bob_booking_id = r.booking_id
    else:
        fail(f"Bob gagal: {r.message}")
except grpc.RpcError as e:
    fail(f"Bob error: {e.details()}")

# Charlie — jadwal BENTROK dengan Alice
info("Charlie booking R001 (10:00–12:00) — seharusnya BENTROK...")
try:
    r = booking_stub.BookRoom(pb2.BookingRequest(
        user_id="U003", user_name="Charlie",
        room_id="R001", date=today,
        start_time="10:00", end_time="12:00",
        num_people=2, purpose="Meeting"
    ))
    if not r.success:
        ok(f"Error handling jadwal bentrok: '{r.message}'")
    else:
        fail("Seharusnya ditolak!")
except grpc.RpcError as e:
    ok(f"Error handling jadwal bentrok: [{e.code()}] '{e.details()}'")

# Diana — ruangan MAINTENANCE
info("Diana booking R005 (maintenance) — seharusnya DITOLAK...")
try:
    r = booking_stub.BookRoom(pb2.BookingRequest(
        user_id="U004", user_name="Diana",
        room_id="R005", date=today,
        start_time="13:00", end_time="15:00",
        num_people=3, purpose="Tugas"
    ))
    if not r.success:
        ok(f"Error handling maintenance: '{r.message}'")
    else:
        fail("Seharusnya ditolak!")
except grpc.RpcError as e:
    ok(f"Error handling maintenance: [{e.code()}] '{e.details()}'")

# Eve — melebihi KAPASITAS
info("Eve booking R003 (kapasitas 6) dengan 10 orang — seharusnya DITOLAK...")
try:
    r = booking_stub.BookRoom(pb2.BookingRequest(
        user_id="U005", user_name="Eve",
        room_id="R003", date=today,
        start_time="14:00", end_time="16:00",
        num_people=10, purpose="Kelebihan kapasitas"
    ))
    if not r.success:
        ok(f"Error handling over-kapasitas: '{r.message}'")
    else:
        fail("Seharusnya ditolak!")
except grpc.RpcError as e:
    ok(f"Error handling over-kapasitas: [{e.code()}] '{e.details()}'")

# =============================================
# TEST 4: GetBookingStatus (Unary)
# =============================================
divider("GET BOOKING STATUS  [Unary · BookingService]")
if alice_booking_id:
    try:
        r = booking_stub.GetBookingStatus(
            pb2.BookingStatusRequest(booking_id=alice_booking_id))
        if r.success:
            ok(f"Status: {r.status} | {r.room_name} | {r.start_time} s/d {r.end_time}")
    except grpc.RpcError as e:
        fail(f"Error: {e.details()}")

# booking ID tidak ada
try:
    booking_stub.GetBookingStatus(pb2.BookingStatusRequest(booking_id="INVALID"))
    fail("Seharusnya error!")
except grpc.RpcError as e:
    ok(f"Error handling booking tdk ada: [{e.code()}] '{e.details()}'")

# =============================================
# TEST 5: GetUserBookings (Unary)
# =============================================
divider("GET USER BOOKINGS  [Unary · BookingService]")
try:
    r = booking_stub.GetUserBookings(pb2.UserRequest(user_id="U001"))
    ok(f"Alice punya {r.total} booking:")
    for b in r.bookings:
        print(f"     [{b.booking_id}] {b.room_name} | {b.date} {b.start_time}–{b.end_time} | {b.status}")
except grpc.RpcError as e:
    fail(f"Error: {e.details()}")

# =============================================
# TEST 6: CancelBooking (Unary)
# =============================================
divider("CANCEL BOOKING  [Unary · BookingService]")

if alice_booking_id:
    info(f"Alice membatalkan booking {alice_booking_id}...")
    try:
        r = booking_stub.CancelBooking(pb2.CancelRequest(
            booking_id=alice_booking_id,
            user_id="U001",
            reason="Ada keperluan mendadak"
        ))
        if r.success:
            ok(f"Pembatalan berhasil: {r.message}")
        else:
            fail(r.message)
    except grpc.RpcError as e:
        fail(f"Error: {e.details()}")

    # Double cancel
    info("Alice coba cancel lagi (sudah dibatalkan) — seharusnya DITOLAK...")
    try:
        r = booking_stub.CancelBooking(pb2.CancelRequest(
            booking_id=alice_booking_id, user_id="U001", reason="Test"
        ))
        if not r.success:
            ok(f"Error handling double-cancel: '{r.message}'")
        else:
            fail("Seharusnya ditolak!")
    except grpc.RpcError as e:
        ok(f"Error handling double-cancel: [{e.code()}] '{e.details()}'")

# Cancel booking milik orang lain (PERMISSION_DENIED)
if bob_booking_id:
    info("Alice coba cancel booking Bob — seharusnya PERMISSION_DENIED...")
    try:
        r = booking_stub.CancelBooking(pb2.CancelRequest(
            booking_id=bob_booking_id, user_id="U001", reason="Unauthorized"
        ))
        if not r.success:
            ok(f"Error handling unauthorized: '{r.message}'")
        else:
            fail("Seharusnya ditolak!")
    except grpc.RpcError as e:
        ok(f"Error handling unauthorized: [{e.code()}] '{e.details()}'")

# =============================================
# TEST 7: SendNotification (Unary)
# =============================================
divider("SEND NOTIFICATION  [Unary · NotificationService]")
try:
    r = notif_stub.SendNotification(pb2.SendNotifRequest(
        target_user_id="U001",
        title="Pengumuman Penting 📢",
        message="Perpustakaan akan tutup lebih awal hari ini pukul 17.00",
        type="BROADCAST"
    ))
    ok(f"Notifikasi terkirim ke 1 user: {r.message}")
except grpc.RpcError as e:
    fail(f"Error: {e.details()}")

# =============================================
# TEST 8: GetNotificationHistory (Unary)
# =============================================
divider("NOTIFICATION HISTORY  [Unary · NotificationService]")
time.sleep(0.5)
try:
    r = notif_stub.GetNotificationHistory(pb2.UserRequest(user_id="U001"))
    ok(f"Alice punya {r.total} notifikasi:")
    for n in r.notifications:
        if n.type != "HEARTBEAT":
            print(f"     [{n.type:<22}] {n.title}")
except grpc.RpcError as e:
    fail(f"Error: {e.details()}")

# =============================================
# STREAMING SUMMARY
# =============================================
divider("SERVER-SIDE STREAMING SUMMARY")
time.sleep(1)
ok(f"Room update diterima via WatchRoomAvailability  : {len(received_room_updates)} event")
ok(f"Notifikasi diterima via SubscribeNotifications  : {len(received_notifs)} notif")

if received_room_updates:
    print()
    print("  Room events yang diterima:")
    for u in received_room_updates:
        print(f"     🔔 {u.room_name:<22} → {u.event_type}  ({u.current_occupancy}/{u.capacity} orang)")

# =============================================
# FINAL CHECKLIST
# =============================================
print("\n" + "="*55)
print("  ✅ SEMUA TEST SELESAI — CHECKLIST FITUR WAJIB:")
print()
print("  ✔  Unary gRPC              (8 RPC methods)")
print("  ✔  Server-side Streaming   (WatchRoomAvailability +")
print("                              SubscribeNotifications)")
print("  ✔  Error Handling          (NOT_FOUND, PERMISSION_DENIED,")
print("                              jadwal bentrok, maintenance,")
print("                              over-kapasitas, double-cancel)")
print("  ✔  State Management        (In-memory: ROOMS, BOOKINGS,")
print("                              USER_BOOKINGS, NOTIF_HISTORY)")
print("  ✔  Multi Client            (Alice, Bob, Charlie, Diana, Eve)")
print("  ✔  3 Services              (RoomService, BookingService,")
print("                              NotificationService)")
print("="*55 + "\n")
