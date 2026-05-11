"""
WebSocket Bridge Server - Smart Study Room Booking System
Menjembatani komunikasi antara Browser (WebSocket) dengan gRPC Server.

Arsitektur:
    Browser <---(WebSocket :8765)---> Bridge <---(gRPC :50051)---> gRPC Server

Fitur:
    1. Meneruskan gRPC Streaming ke WebSocket (WatchRoomAvailability, SubscribeNotifications)
    2. Menerima command dari Browser dan memicu pemanggilan gRPC
    3. Server-Initiated Events: otomatis push data tanpa request dari browser
    4. Command & Control: booking, cancel, get_rooms, dll.
"""

import asyncio
import json
import threading
import logging
import grpc
import sys
import websockets
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Tambahkan root project ke path agar bisa import pb2
sys.path.insert(0, '.')
import study_room_pb2 as pb2
import study_room_pb2_grpc as pb2_grpc
from google.protobuf import empty_pb2

# =============================================
# KONFIGURASI
# =============================================
GRPC_ADDRESS = 'localhost:50052'
WS_HOST = 'localhost'
WS_PORT = 8765

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("WS-Bridge")

# =============================================
# STATE GLOBAL
# =============================================

# Set semua WebSocket client yang sedang terhubung
# Format: { websocket: { user_id, user_name, grpc_channel, grpc_stubs } }
connected_clients = {}
clients_lock = threading.Lock()

# Thread pool untuk operasi gRPC sinkron
executor = ThreadPoolExecutor(max_workers=20)


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =============================================
# HELPERS: gRPC CONNECTION
# =============================================

def make_stubs(channel):
    return {
        "room": pb2_grpc.RoomServiceStub(channel),
        "booking": pb2_grpc.BookingServiceStub(channel),
        "notif": pb2_grpc.NotificationServiceStub(channel),
    }


def room_status_label(status_int):
    labels = {
        pb2.AVAILABLE: "AVAILABLE",
        pb2.OCCUPIED: "OCCUPIED",
        pb2.FULL: "FULL",
        pb2.MAINTENANCE: "MAINTENANCE",
    }
    return labels.get(status_int, "UNKNOWN")


# =============================================
# HELPERS: JSON MESSAGES
# =============================================

def msg_response(action, data, success=True, error=""):
    return json.dumps({
        "type": "response",
        "action": action,
        "success": success,
        "data": data,
        "error": error,
        "ts": ts()
    })


def msg_room_update(update):
    return json.dumps({
        "type": "room_update",
        "data": {
            "room_id": update.room_id,
            "room_name": update.room_name,
            "status": room_status_label(update.status),
            "capacity": update.capacity,
            "current_occupancy": update.current_occupancy,
            "event_type": update.event_type,
            "timestamp": update.timestamp,
        },
        "ts": ts()
    })


def msg_notification(notif):
    return json.dumps({
        "type": "notification",
        "data": {
            "notif_id": notif.notif_id,
            "title": notif.title,
            "message": notif.message,
            "notif_type": notif.type,
            "room_id": notif.room_id,
            "booking_id": notif.booking_id,
            "timestamp": notif.timestamp,
            "user_id": notif.user_id,
        },
        "ts": ts()
    })


def msg_server_alert(title, message, alert_type="INFO"):
    """Server-Initiated Event: peringatan proaktif dari server"""
    return json.dumps({
        "type": "server_alert",
        "data": {
            "title": title,
            "message": message,
            "alert_type": alert_type,
            "timestamp": ts(),
        },
        "ts": ts()
    })


def msg_heartbeat():
    return json.dumps({
        "type": "heartbeat",
        "ts": ts()
    })


def msg_activity(action_desc, detail=""):
    return json.dumps({
        "type": "activity",
        "data": {
            "action": action_desc,
            "detail": detail,
            "timestamp": ts(),
        },
        "ts": ts()
    })


# =============================================
# GRPC STREAMING TASKS (async wrappers)
# =============================================

async def stream_room_availability(websocket, stubs, user_id):
    """
    Wrap gRPC WatchRoomAvailability streaming ke asyncio.
    Data yang diterima langsung di-push ke websocket.
    """

    loop = asyncio.get_event_loop()

    def grpc_watch():
        try:
            stream = stubs["room"].WatchRoomAvailability(
                pb2.WatchRequest(client_id=user_id)
            )
            for update in stream:
                if update.event_type == "HEARTBEAT":
                    continue
                asyncio.run_coroutine_threadsafe(
                    safe_send(websocket, msg_room_update(update)),
                    loop
                )
                if update.event_type not in ("INITIAL_STATUS",):
                    asyncio.run_coroutine_threadsafe(
                        safe_send(websocket, msg_activity(
                            f"Room {update.event_type}",
                            f"{update.room_name}: {update.current_occupancy}/{update.capacity} orang"
                        )),
                        loop
                    )
        except grpc.RpcError as e:
            if e.code() not in (grpc.StatusCode.CANCELLED, grpc.StatusCode.UNAVAILABLE):
                log.warning(f"[Room Stream] gRPC error: {e.details()}")
        except Exception as ex:
            log.warning(f"[Room Stream] Stream ended: {ex}")

    await loop.run_in_executor(executor, grpc_watch)


async def stream_notifications(websocket, stubs, user_id, user_name):
    """
    Wrap gRPC SubscribeNotifications streaming ke asyncio.
    Notifikasi langsung di-push ke websocket.
    """
    loop = asyncio.get_event_loop()

    def grpc_notif():
        try:
            stream = stubs["notif"].SubscribeNotifications(
                pb2.SubscribeRequest(user_id=user_id, user_name=user_name)
            )
            for notif in stream:
                if notif.type == "HEARTBEAT":
                    continue
                asyncio.run_coroutine_threadsafe(
                    safe_send(websocket, msg_notification(notif)),
                    loop
                )
                asyncio.run_coroutine_threadsafe(
                    safe_send(websocket, msg_activity(
                        f"Notif: {notif.title}",
                        notif.message
                    )),
                    loop
                )
        except grpc.RpcError as e:
            if e.code() not in (grpc.StatusCode.CANCELLED, grpc.StatusCode.UNAVAILABLE):
                log.warning(f"[Notif Stream] gRPC error: {e.details()}")
        except Exception as ex:
            log.warning(f"[Notif Stream] Stream ended: {ex}")

    await loop.run_in_executor(executor, grpc_notif)


# =============================================
# SERVER-INITIATED EVENTS
# Proaktif push data ke semua client terhubung
# tanpa request dari browser
# =============================================

async def server_initiated_events_loop():
    """
    Background task: push data proaktif ke semua browser terhubung.
    Ini adalah Server-Initiated Events (tanpa request dari klien).
    
    - Setiap 30 detik: kirim heartbeat
    - Setiap 60 detik: kirim status ringkasan ruangan ke semua client
    - Setiap 120 detik: kirim broadcast alert sistem
    """
    counter = 0
    while True:
        await asyncio.sleep(30)
        counter += 1

        with clients_lock:
            ws_list = list(connected_clients.keys())

        if not ws_list:
            continue

        # Setiap 30 detik: heartbeat ke semua client
        for ws in ws_list:
            await safe_send(ws, msg_heartbeat())

        # Setiap 60 detik (counter kelipatan 2): push stats ruangan
        if counter % 2 == 0:
            info = await get_room_summary_for_event()
            if info:
                alert_msg = json.dumps({
                    "type": "server_push",
                    "data": {
                        "title": "📊 Update Status Ruangan",
                        "message": info,
                        "timestamp": ts(),
                    },
                    "ts": ts()
                })
                for ws in ws_list:
                    await safe_send(ws, alert_msg)
                log.info(f"[Server-Push] Pushed room stats to {len(ws_list)} client(s)")

        # Setiap 120 detik (counter kelipatan 4): broadcast alert sistem
        if counter % 4 == 0:
            for ws in ws_list:
                await safe_send(ws, msg_server_alert(
                    "🔔 Sistem Berjalan Normal",
                    f"Server gRPC aktif. {len(ws_list)} pengguna terhubung. Waktu: {ts()}",
                    "SYSTEM"
                ))
            log.info(f"[Server-Alert] Sent system alert to {len(ws_list)} client(s)")


async def get_room_summary_for_event():
    """Ambil ringkasan ruangan dari gRPC untuk server-push event."""
    try:
        # Ambil channel dari client pertama yang ada
        with clients_lock:
            if not connected_clients:
                return None
            client_data = next(iter(connected_clients.values()))
            stubs = client_data.get("stubs")

        if not stubs:
            return None

        loop = asyncio.get_event_loop()

        def get_rooms():
            resp = stubs["room"].GetAllRooms(empty_pb2.Empty(), timeout=3)
            avail = sum(1 for r in resp.rooms if r.status == pb2.AVAILABLE)
            occupied = sum(1 for r in resp.rooms if r.status == pb2.OCCUPIED)
            full = sum(1 for r in resp.rooms if r.status == pb2.FULL)
            maint = sum(1 for r in resp.rooms if r.status == pb2.MAINTENANCE)
            return f"Tersedia: {avail} | Terisi: {occupied} | Penuh: {full} | Maintenance: {maint}"

        return await loop.run_in_executor(executor, get_rooms)
    except Exception as e:
        log.warning(f"[Room Summary] Error: {e}")
        return None


# =============================================
# COMMAND HANDLERS
# Menerima instruksi dari Browser dan memanggil gRPC
# =============================================

async def handle_login(websocket, data, loop):
    user_id = data.get("user_id", "").strip()
    user_name = data.get("user_name", "").strip()

    if not user_id or not user_name:
        await safe_send(websocket, msg_response("login", {}, success=False, error="user_id dan user_name wajib diisi"))
        return

    # Buat koneksi gRPC baru untuk client ini
    channel = grpc.insecure_channel(GRPC_ADDRESS)
    stubs = make_stubs(channel)

    # Test koneksi
    try:
        loop2 = asyncio.get_event_loop()
        await loop2.run_in_executor(executor, lambda: stubs["room"].GetAllRooms(empty_pb2.Empty(), timeout=3))
    except grpc.RpcError as e:
        await safe_send(websocket, msg_response("login", {}, success=False,
                         error=f"Tidak dapat terhubung ke gRPC server: {e.details()}"))
        return

    with clients_lock:
        connected_clients[websocket] = {
            "user_id": user_id,
            "user_name": user_name,
            "channel": channel,
            "stubs": stubs,
        }

    log.info(f"[Login] {user_name} ({user_id}) terhubung")

    # Kirim respon login sukses
    await safe_send(websocket, msg_response("login", {
        "user_id": user_id,
        "user_name": user_name,
        "message": f"Selamat datang, {user_name}!"
    }))

    # Server-Initiated: Kirim alert sambutan
    await safe_send(websocket, msg_server_alert(
        f"👋 Selamat Datang, {user_name}!",
        f"Anda terhubung ke Smart Study Room Booking System. Notifikasi dan update ruangan akan tampil secara real-time.",
        "WELCOME"
    ))

    # Mulai streaming gRPC → WebSocket secara paralel
    asyncio.create_task(stream_room_availability(websocket, stubs, user_id))
    asyncio.create_task(stream_notifications(websocket, stubs, user_id, user_name))
    asyncio.create_task(safe_send(websocket, msg_activity("Login", f"{user_name} bergabung ke sistem")))


async def handle_get_rooms(websocket, data, loop):
    with clients_lock:
        client = connected_clients.get(websocket)
    if not client:
        await safe_send(websocket, msg_response("get_rooms", {}, success=False, error="Belum login"))
        return

    stubs = client["stubs"]
    try:
        resp = await loop.run_in_executor(executor, lambda: stubs["room"].GetAllRooms(empty_pb2.Empty()))
        rooms = []
        for r in resp.rooms:
            rooms.append({
                "room_id": r.room_id,
                "name": r.name,
                "capacity": r.capacity,
                "location": r.location,
                "facilities": list(r.facilities),
                "status": room_status_label(r.status),
                "current_occupancy": r.current_occupancy,
            })
        await safe_send(websocket, msg_response("get_rooms", {"rooms": rooms}))
        await safe_send(websocket, msg_activity("Get Rooms", f"{len(rooms)} ruangan dimuat"))
    except grpc.RpcError as e:
        await safe_send(websocket, msg_response("get_rooms", {}, success=False, error=e.details()))


async def handle_book_room(websocket, data, loop):
    with clients_lock:
        client = connected_clients.get(websocket)
    if not client:
        await safe_send(websocket, msg_response("book_room", {}, success=False, error="Belum login"))
        return

    stubs = client["stubs"]
    user_id = client["user_id"]
    user_name = client["user_name"]

    try:
        req = pb2.BookingRequest(
            user_id=user_id,
            user_name=user_name,
            room_id=data.get("room_id", ""),
            date=data.get("date", ""),
            start_time=data.get("start_time", ""),
            end_time=data.get("end_time", ""),
            num_people=int(data.get("num_people", 1)),
            purpose=data.get("purpose", "")
        )
        resp = await loop.run_in_executor(executor, lambda: stubs["booking"].BookRoom(req))
        result = {
            "success": resp.success,
            "booking_id": resp.booking_id,
            "message": resp.message,
            "room_name": resp.room_name,
            "confirmation_code": resp.confirmation_code,
        }
        await safe_send(websocket, msg_response("book_room", result, success=resp.success,
                          error="" if resp.success else resp.message))
        if resp.success:
            await safe_send(websocket, msg_activity("Booking Berhasil",
                f"{user_name} memesan {resp.room_name} — kode: {resp.confirmation_code}"))
    except grpc.RpcError as e:
        await safe_send(websocket, msg_response("book_room", {}, success=False, error=e.details()))
    except ValueError:
        await safe_send(websocket, msg_response("book_room", {}, success=False, error="num_people harus angka"))


async def handle_cancel_booking(websocket, data, loop):
    with clients_lock:
        client = connected_clients.get(websocket)
    if not client:
        await safe_send(websocket, msg_response("cancel_booking", {}, success=False, error="Belum login"))
        return

    stubs = client["stubs"]
    user_id = client["user_id"]

    try:
        req = pb2.CancelRequest(
            booking_id=data.get("booking_id", "").strip().upper(),
            user_id=user_id,
            reason=data.get("reason", "")
        )
        resp = await loop.run_in_executor(executor, lambda: stubs["booking"].CancelBooking(req))
        await safe_send(websocket, msg_response("cancel_booking", {
            "success": resp.success,
            "message": resp.message,
            "booking_id": resp.booking_id,
        }, success=resp.success, error="" if resp.success else resp.message))
        if resp.success:
            await safe_send(websocket, msg_activity("Booking Dibatalkan",
                f"Booking {resp.booking_id} berhasil dibatalkan"))
    except grpc.RpcError as e:
        await safe_send(websocket, msg_response("cancel_booking", {}, success=False, error=e.details()))


async def handle_get_my_bookings(websocket, data, loop):
    with clients_lock:
        client = connected_clients.get(websocket)
    if not client:
        await safe_send(websocket, msg_response("get_my_bookings", {}, success=False, error="Belum login"))
        return

    stubs = client["stubs"]
    user_id = client["user_id"]

    try:
        resp = await loop.run_in_executor(executor,
            lambda: stubs["booking"].GetUserBookings(pb2.UserRequest(user_id=user_id)))
        bookings = []
        for b in resp.bookings:
            bookings.append({
                "booking_id": b.booking_id,
                "room_id": b.room_id,
                "room_name": b.room_name,
                "date": b.date,
                "start_time": b.start_time,
                "end_time": b.end_time,
                "status": b.status,
                "purpose": b.purpose,
                "confirmation_code": b.confirmation_code,
            })
        await safe_send(websocket, msg_response("get_my_bookings", {
            "bookings": bookings,
            "total": resp.total
        }))
        await safe_send(websocket, msg_activity("Lihat Booking Saya", f"{resp.total} booking ditemukan"))
    except grpc.RpcError as e:
        await safe_send(websocket, msg_response("get_my_bookings", {}, success=False, error=e.details()))


async def handle_send_notification(websocket, data, loop):
    """Admin: kirim notifikasi manual ke semua user (Server-Initiated Event trigger)"""
    with clients_lock:
        client = connected_clients.get(websocket)
    if not client:
        await safe_send(websocket, msg_response("send_notification", {}, success=False, error="Belum login"))
        return

    stubs = client["stubs"]
    try:
        req = pb2.SendNotifRequest(
            target_user_id=data.get("target_user_id", "*"),
            title=data.get("title", ""),
            message=data.get("message", ""),
            type=data.get("notif_type", "BROADCAST"),
            room_id=data.get("room_id", "")
        )
        resp = await loop.run_in_executor(executor, lambda: stubs["notif"].SendNotification(req))
        await safe_send(websocket, msg_response("send_notification", {
            "success": resp.success,
            "message": resp.message,
            "recipients": resp.recipients,
        }))
        await safe_send(websocket, msg_activity("Notifikasi Dikirim",
            f"Admin mengirim: {data.get('title', '')}"))
    except grpc.RpcError as e:
        await safe_send(websocket, msg_response("send_notification", {}, success=False, error=e.details()))


async def handle_get_room_detail(websocket, data, loop):
    with clients_lock:
        client = connected_clients.get(websocket)
    if not client:
        await safe_send(websocket, msg_response("get_room_detail", {}, success=False, error="Belum login"))
        return

    stubs = client["stubs"]
    room_id = data.get("room_id", "")
    try:
        resp = await loop.run_in_executor(executor,
            lambda: stubs["room"].GetRoomDetail(pb2.RoomRequest(room_id=room_id)))
        if resp.success:
            r = resp.room
            room_data = {
                "room_id": r.room_id,
                "name": r.name,
                "capacity": r.capacity,
                "location": r.location,
                "facilities": list(r.facilities),
                "status": room_status_label(r.status),
                "current_occupancy": r.current_occupancy,
                "active_bookings": [
                    {"booking_id": b.booking_id, "user_name": b.user_name,
                     "start_time": b.start_time, "end_time": b.end_time}
                    for b in resp.active_bookings
                ]
            }
            await safe_send(websocket, msg_response("get_room_detail", room_data))
        else:
            await safe_send(websocket, msg_response("get_room_detail", {}, success=False, error=resp.message))
    except grpc.RpcError as e:
        await safe_send(websocket, msg_response("get_room_detail", {}, success=False, error=e.details()))


# =============================================
# SAFE SEND (mencegah crash jika WS sudah tutup)
# =============================================

async def safe_send(websocket, message):
    try:
        await websocket.send(message)
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        log.debug(f"[SafeSend] Error: {e}")


# =============================================
# MAIN HANDLER: per WebSocket connection
# =============================================

async def ws_handler(websocket):
    client_ip = websocket.remote_address
    log.info(f"[Connect] Client baru: {client_ip}")

    # Kirim pesan selamat datang (Server-Initiated: tanpa request dari client)
    await safe_send(websocket, msg_server_alert(
        "🌐 Terhubung ke WebSocket Bridge",
        "Silakan login untuk memulai. Data ruangan akan diperbarui secara real-time.",
        "CONNECT"
    ))

    loop = asyncio.get_event_loop()

    try:
        async for raw_msg in websocket:
            try:
                msg = json.loads(raw_msg)
            except json.JSONDecodeError:
                await safe_send(websocket, json.dumps({"type": "error", "error": "Pesan harus berformat JSON"}))
                continue

            action = msg.get("action", "")
            data = msg.get("data", {})

            log.info(f"[CMD] action={action} from {client_ip}")

            # Routing command → handler gRPC
            if action == "login":
                await handle_login(websocket, data, loop)
            elif action == "get_rooms":
                await handle_get_rooms(websocket, data, loop)
            elif action == "get_room_detail":
                await handle_get_room_detail(websocket, data, loop)
            elif action == "book_room":
                await handle_book_room(websocket, data, loop)
            elif action == "cancel_booking":
                await handle_cancel_booking(websocket, data, loop)
            elif action == "get_my_bookings":
                await handle_get_my_bookings(websocket, data, loop)
            elif action == "send_notification":
                await handle_send_notification(websocket, data, loop)
            elif action == "ping":
                await safe_send(websocket, msg_heartbeat())
            else:
                await safe_send(websocket, json.dumps({
                    "type": "error",
                    "error": f"Action tidak dikenal: {action}"
                }))

    except websockets.exceptions.ConnectionClosedOK:
        pass
    except websockets.exceptions.ConnectionClosedError as e:
        log.warning(f"[Disconnect] {client_ip} putus: {e}")
    finally:
        # Cleanup: hapus dari registry dan tutup channel gRPC
        with clients_lock:
            client = connected_clients.pop(websocket, None)
        if client:
            try:
                client["channel"].close()
            except Exception:
                pass
            log.info(f"[Disconnect] {client.get('user_name', client_ip)} keluar. "
                     f"Sisa client: {len(connected_clients)}")


# =============================================
# ENTRY POINT
# =============================================

async def main():
    print("=" * 60)
    print("  Smart Study Room - WebSocket Bridge")
    print(f"  WebSocket  : ws://{WS_HOST}:{WS_PORT}")
    print(f"  gRPC Target: {GRPC_ADDRESS}")
    print("=" * 60)
    print(f"  Bridge aktif: {ts()}")
    print("  Buka web/index.html di browser untuk membuka UI")
    print("=" * 60)

    # Jalankan server-initiated events sebagai background task
    asyncio.create_task(server_initiated_events_loop())

    # Jalankan WebSocket server
    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        log.info(f"WebSocket Bridge mendengarkan di ws://{WS_HOST}:{WS_PORT}")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Bridge] Shutting down...")
