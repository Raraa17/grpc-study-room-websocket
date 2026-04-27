"""
Smart Study Room Booking System - gRPC Client
Client interaktif dengan menu lengkap
"""

import grpc
import threading
import sys
import time
from datetime import datetime, date

sys.path.insert(0, '.')
import study_room_pb2 as pb2
import study_room_pb2_grpc as pb2_grpc
from google.protobuf import empty_pb2

# Konfigurasi
SERVER_ADDRESS = 'localhost:50051'

ROOM_STATUS_LABEL = {
    pb2.AVAILABLE: "✅ Tersedia",
    pb2.OCCUPIED: "🟡 Terisi",
    pb2.FULL: "🔴 Penuh",
    pb2.MAINTENANCE: "🔧 Maintenance",
}

def get_stubs():
    channel = grpc.insecure_channel(SERVER_ADDRESS)
    return (
        pb2_grpc.RoomServiceStub(channel),
        pb2_grpc.BookingServiceStub(channel),
        pb2_grpc.NotificationServiceStub(channel),
        channel
    )

def print_separator(title=""):
    print("\n" + "=" * 55)
    if title:
        print(f"  {title}")
        print("=" * 55)

def print_room(room):
    status = ROOM_STATUS_LABEL.get(room.status, "Unknown")
    print(f"  [{room.room_id}] {room.name}")
    print(f"      Lokasi   : {room.location}")
    print(f"      Kapasitas: {room.capacity} orang")
    print(f"      Fasilitas: {', '.join(room.facilities)}")
    print(f"      Status   : {status} ({room.current_occupancy}/{room.capacity} orang)")
    print()

# =============================================
# FITUR 1: Lihat Semua Ruangan
# =============================================
def menu_list_rooms(room_stub):
    print_separator("DAFTAR RUANGAN BELAJAR")
    try:
        resp = room_stub.GetAllRooms(empty_pb2.Empty())
        if resp.success:
            print(f"  Total: {len(resp.rooms)} ruangan\n")
            for room in resp.rooms:
                print_room(room)
        else:
            print(f"  Gagal: {resp.message}")
    except grpc.RpcError as e:
        print(f"  Error: {e.details()}")

# =============================================
# FITUR 2: Detail Ruangan
# =============================================
def menu_room_detail(room_stub):
    print_separator("DETAIL RUANGAN")
    room_id = input("  Masukkan Room ID (contoh: R001): ").strip().upper()
    try:
        resp = room_stub.GetRoomDetail(pb2.RoomRequest(room_id=room_id))
        if resp.success:
            print()
            print_room(resp.room)
            if resp.active_bookings:
                print(f"  Booking Aktif ({len(resp.active_bookings)}):")
                for b in resp.active_bookings:
                    print(f"    - [{b.booking_id}] {b.user_name}: {b.start_time} - {b.end_time}")
            else:
                print("  Tidak ada booking aktif saat ini")
        else:
            print(f"  Gagal: {resp.message}")
    except grpc.RpcError as e:
        print(f"  Error gRPC [{e.code()}]: {e.details()}")

# =============================================
# FITUR 3: Booking Ruangan
# =============================================
def menu_book_room(booking_stub, user_id, user_name):
    print_separator("BOOKING RUANGAN")
    print(f"  User: {user_name} ({user_id})\n")

    room_id = input("  Room ID (contoh: R001): ").strip().upper()
    today = date.today().isoformat()
    tanggal = input(f"  Tanggal [YYYY-MM-DD, default {today}]: ").strip() or today
    start_time = input("  Jam mulai [HH:MM, contoh 09:00]: ").strip()
    end_time = input("  Jam selesai [HH:MM, contoh 11:00]: ").strip()
    num_people = input("  Jumlah orang: ").strip()
    purpose = input("  Keperluan: ").strip()

    if not all([room_id, start_time, end_time, num_people]):
        print("  Field tidak boleh kosong!")
        return

    try:
        req = pb2.BookingRequest(
            user_id=user_id,
            user_name=user_name,
            room_id=room_id,
            date=tanggal,
            start_time=start_time,
            end_time=end_time,
            num_people=int(num_people),
            purpose=purpose
        )
        resp = booking_stub.BookRoom(req)
        if resp.success:
            print(f"\n  ✅ {resp.message}")
            print(f"  Booking ID     : {resp.booking_id}")
            print(f"  Kode Konfirmasi: {resp.confirmation_code}")
            print(f"  Ruangan        : {resp.room_name}")
        else:
            print(f"\n  ❌ Booking Gagal: {resp.message}")
    except grpc.RpcError as e:
        print(f"\n  Error gRPC [{e.code()}]: {e.details()}")
    except ValueError:
        print("  Jumlah orang harus berupa angka!")

# =============================================
# FITUR 4: Batalkan Booking
# =============================================
def menu_cancel_booking(booking_stub, user_id):
    print_separator("BATALKAN BOOKING")
    booking_id = input("  Booking ID yang ingin dibatalkan: ").strip().upper()
    reason = input("  Alasan pembatalan: ").strip()
    try:
        resp = booking_stub.CancelBooking(pb2.CancelRequest(
            booking_id=booking_id,
            user_id=user_id,
            reason=reason
        ))
        if resp.success:
            print(f"\n  ✅ {resp.message}")
        else:
            print(f"\n  ❌ Gagal: {resp.message}")
    except grpc.RpcError as e:
        print(f"\n  Error gRPC [{e.code()}]: {e.details()}")

# =============================================
# FITUR 5: Cek Status Booking
# =============================================
def menu_booking_status(booking_stub):
    print_separator("CEK STATUS BOOKING")
    booking_id = input("  Booking ID: ").strip().upper()
    try:
        resp = booking_stub.GetBookingStatus(pb2.BookingStatusRequest(booking_id=booking_id))
        if resp.success:
            STATUS_ICON = {"ACTIVE": "✅", "CANCELLED": "❌", "COMPLETED": "✔️"}
            icon = STATUS_ICON.get(resp.status, "?")
            print(f"\n  Booking ID : {resp.booking_id}")
            print(f"  Status     : {icon} {resp.status}")
            print(f"  Ruangan    : {resp.room_name}")
            print(f"  Pemesan    : {resp.user_name}")
            print(f"  Waktu      : {resp.start_time} s/d {resp.end_time}")
        else:
            print(f"\n  ❌ {resp.message}")
    except grpc.RpcError as e:
        print(f"\n  Error gRPC [{e.code()}]: {e.details()}")

# =============================================
# FITUR 6: Lihat Semua Booking Saya
# =============================================
def menu_my_bookings(booking_stub, user_id, user_name):
    print_separator(f"BOOKING SAYA - {user_name}")
    try:
        resp = booking_stub.GetUserBookings(pb2.UserRequest(user_id=user_id))
        if resp.success:
            if resp.total == 0:
                print("  Belum ada booking")
            else:
                print(f"  Total: {resp.total} booking\n")
                for b in resp.bookings:
                    STATUS_ICON = {"ACTIVE": "✅", "CANCELLED": "❌", "COMPLETED": "✔️"}
                    icon = STATUS_ICON.get(b.status, "?")
                    print(f"  {icon} [{b.booking_id}] {b.room_name}")
                    print(f"     Tanggal : {b.date} | {b.start_time} - {b.end_time}")
                    print(f"     Keperluan: {b.purpose}")
                    print(f"     Kode    : {b.confirmation_code}")
                    print()
    except grpc.RpcError as e:
        print(f"\n  Error gRPC [{e.code()}]: {e.details()}")

# =============================================
# FITUR 7: Watch Room Availability (Server Streaming)
# =============================================
def menu_watch_rooms(room_stub, user_id):
    print_separator("LIVE MONITORING RUANGAN")
    print("  Menampilkan update ketersediaan ruangan secara real-time...")
    print("  Tekan Ctrl+C untuk berhenti\n")

    def watch():
        try:
            stream = room_stub.WatchRoomAvailability(pb2.WatchRequest(client_id=user_id))
            for update in stream:
                if update.event_type == "HEARTBEAT":
                    continue
                STATUS_ICON = {
                    pb2.AVAILABLE: "✅", pb2.OCCUPIED: "🟡",
                    pb2.FULL: "🔴", pb2.MAINTENANCE: "🔧"
                }
                icon = STATUS_ICON.get(update.status, "?")
                if update.event_type == "INITIAL_STATUS":
                    print(f"  {icon} [{update.room_id}] {update.room_name} — {update.current_occupancy}/{update.capacity} orang")
                else:
                    print(f"\n  🔔 UPDATE [{update.timestamp}]")
                    print(f"     Ruangan : {update.room_name} ({update.room_id})")
                    print(f"     Event   : {update.event_type}")
                    print(f"     Status  : {icon} {update.current_occupancy}/{update.capacity} orang")
        except grpc.RpcError as e:
            if e.code() != grpc.StatusCode.CANCELLED:
                print(f"\n  Stream error: {e.details()}")

    t = threading.Thread(target=watch, daemon=True)
    t.start()

    try:
        input("\n  [Tekan ENTER untuk kembali ke menu...]\n")
    except KeyboardInterrupt:
        pass

# =============================================
# FITUR 8: Notifikasi Real-time (Server Streaming)
# =============================================
def menu_subscribe_notif(notif_stub, user_id, user_name):
    print_separator("NOTIFIKASI REAL-TIME")
    print("  Menerima notifikasi secara real-time...")
    print("  Tekan ENTER untuk kembali ke menu\n")

    stop_event = threading.Event()
    
    def listen():
        try:
            stream = notif_stub.SubscribeNotifications(pb2.SubscribeRequest(
                user_id=user_id,
                user_name=user_name
            ))
            for notif in stream:
                if stop_event.is_set():
                    break
                if notif.type == "HEARTBEAT":
                    continue
                ICONS = {
                    "BOOKING_CONFIRMED": "✅", "BOOKING_CANCELLED": "❌",
                    "ROOM_FULL": "🔴", "REMINDER": "⏰",
                    "SYSTEM": "🔔", "BROADCAST": "📢"
                }
                icon = ICONS.get(notif.type, "🔔")
                print(f"\n  {icon} [{notif.timestamp}] {notif.title}")
                print(f"     {notif.message}")
        except grpc.RpcError as e:
            if not stop_event.is_set():
                print(f"\n  Error stream: {e.details()}")

    t = threading.Thread(target=listen, daemon=True)
    t.start()

    input("  [Tekan ENTER untuk kembali ke menu...]\n")
    stop_event.set()

# =============================================
# FITUR 9: Riwayat Notifikasi
# =============================================
def menu_notif_history(notif_stub, user_id):
    print_separator("RIWAYAT NOTIFIKASI")
    try:
        resp = notif_stub.GetNotificationHistory(pb2.UserRequest(user_id=user_id))
        if resp.total == 0:
            print("  Belum ada notifikasi")
        else:
            print(f"  Total: {resp.total} notifikasi\n")
            for n in reversed(resp.notifications):
                if n.type == "HEARTBEAT":
                    continue
                print(f"  [{n.timestamp}] {n.title}")
                print(f"    {n.message}\n")
    except grpc.RpcError as e:
        print(f"  Error gRPC: {e.details()}")

# =============================================
# MAIN MENU
# =============================================
def main():
    print_separator("SMART STUDY ROOM BOOKING SYSTEM")
    print("  Selamat datang! Silakan login terlebih dahulu.\n")

    user_id = input("  Masukkan NIM/User ID: ").strip()
    user_name = input("  Masukkan Nama Anda : ").strip()

    if not user_id or not user_name:
        print("  User ID dan Nama tidak boleh kosong!")
        sys.exit(1)

    print(f"\n  Login berhasil! Halo, {user_name} 👋")

    try:
        room_stub, booking_stub, notif_stub, channel = get_stubs()
        # Test koneksi
        room_stub.GetAllRooms(empty_pb2.Empty(), timeout=3)
    except grpc.RpcError as e:
        print(f"\n  ❌ Tidak dapat terhubung ke server: {SERVER_ADDRESS}")
        print(f"  Pastikan server sudah berjalan!")
        sys.exit(1)

    print(f"  ✅ Terhubung ke server {SERVER_ADDRESS}\n")

    MENU = {
        "1": ("📋 Lihat Semua Ruangan", lambda: menu_list_rooms(room_stub)),
        "2": ("🔍 Detail Ruangan", lambda: menu_room_detail(room_stub)),
        "3": ("📅 Booking Ruangan", lambda: menu_book_room(booking_stub, user_id, user_name)),
        "4": ("❌ Batalkan Booking", lambda: menu_cancel_booking(booking_stub, user_id)),
        "5": ("🔎 Cek Status Booking", lambda: menu_booking_status(booking_stub)),
        "6": ("📋 Booking Saya", lambda: menu_my_bookings(booking_stub, user_id, user_name)),
        "7": ("📡 Live Monitor Ruangan (Streaming)", lambda: menu_watch_rooms(room_stub, user_id)),
        "8": ("🔔 Notifikasi Real-time (Streaming)", lambda: menu_subscribe_notif(notif_stub, user_id, user_name)),
        "9": ("📜 Riwayat Notifikasi", lambda: menu_notif_history(notif_stub, user_id)),
        "0": ("🚪 Keluar", None),
    }

    while True:
        print_separator("MENU UTAMA")
        for key, (label, _) in MENU.items():
            print(f"  [{key}] {label}")
        print()

        choice = input("  Pilih menu: ").strip()

        if choice == "0":
            print("\n  Terima kasih sudah menggunakan sistem ini. Sampai jumpa! 👋\n")
            break
        elif choice in MENU:
            _, action = MENU[choice]
            if action:
                action()
                input("\n  [Tekan ENTER untuk lanjut...]")
        else:
            print("  Pilihan tidak valid, coba lagi.")

if __name__ == '__main__':
    main()
