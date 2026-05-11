"""
=============================================================
PUBLISHER 3: ADMIN (Manajemen & Perintah)
Role: Administrator sistem yang mengirim perintah dan broadcast

Fitur MQTT yang didemonstrasikan:
  - Fitur 1: Publish/Subscribe & QoS
  - Fitur 4: User Properties (metadata admin)
  - Fitur 5: Retain Message (pengumuman persist)
  - Fitur 6: Message Expiry Interval (perintah kadaluarsa)
  - Fitur 7: Last Will and Testament
  - Fitur 8: Request-Response Pattern (sebagai requester)
  - Fitur 9: Shared Subscriptions (kirim ke shared topic)
=============================================================
"""

import paho.mqtt.client as mqtt
import json
import time
import uuid
import threading
import sys
import os
from datetime import datetime
from config import *

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# =============================================
# KONFIGURASI
# =============================================
CLIENT_ID = "admin-publisher-003"

# Pending requests untuk Request-Response (Fitur 8)
pending_requests = {}
pending_lock = threading.Lock()


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def gen_correlation_id():
    return str(uuid.uuid4())[:8].upper()


# =============================================
# CALLBACKS
# =============================================

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"[ADMIN] ✅ Terhubung ke broker {MQTT_BROKER}:{MQTT_PORT}")
        
        # Retain status online (Fitur 5)
        status_msg = json.dumps({
            "client_id": CLIENT_ID,
            "status": "ONLINE",
            "type": "admin",
            "role": "administrator",
            "timestamp": get_timestamp()
        })
        client.publish(TOPIC_LWT, payload=status_msg, qos=1, retain=True)
        
        # Subscribe untuk responses (Fitur 8: Request-Response)
        client.subscribe(TOPIC_RESPONSE, qos=1)
        client.subscribe(TOPIC_ADMIN_RESPONSE, qos=1)
        print(f"[ADMIN] 📥 Subscribed ke response topics")
    else:
        print(f"[ADMIN] ❌ Gagal terhubung: {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties):
    print(f"[ADMIN] ⚠️ Terputus dari broker")


def on_message(client, userdata, msg):
    """
    Handle response dari Request-Response Pattern (Fitur 8)
    """
    try:
        payload = json.loads(msg.payload.decode())
        correlation_id = payload.get("correlation_id", "")
        
        with pending_lock:
            if correlation_id in pending_requests:
                req_info = pending_requests.pop(correlation_id)
                elapsed = time.time() - req_info["sent_at"]
                print(f"\n[ADMIN] 📨 Response diterima (correlation: {correlation_id})")
                print(f"        Topic: {msg.topic}")
                print(f"        Waktu respon: {elapsed:.2f}s")
                print(f"        Data: {json.dumps(payload, indent=2)}")
            else:
                print(f"[ADMIN] 📨 Pesan diterima dari {msg.topic}: {payload}")
    except Exception as e:
        print(f"[ADMIN] Error: {e}")


# =============================================
# FUNGSI-FUNGSI ADMIN
# =============================================

def send_broadcast(client, title, message, priority="NORMAL"):
    """
    Kirim broadcast ke semua subscriber
    Fitur 4: User Properties
    Fitur 5: Retain (opsional)
    Fitur 6: Message Expiry
    """
    payload = json.dumps({
        "type": "BROADCAST",
        "title": title,
        "message": message,
        "priority": priority,
        "sender": CLIENT_ID,
        "timestamp": get_timestamp(),
        "user_properties": {
            "sender-role": "admin",
            "priority": priority,
            "app-version": "2.0.0"
        }
    })
    
    properties = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
    # ---- Fitur 4: User Properties ----
    properties.UserProperty = [
        ("sender-role", "admin"),
        ("priority", priority),
        ("broadcast-type", "announcement"),
        ("app-version", "2.0.0")
    ]
    # ---- Fitur 6: Message Expiry ----
    properties.MessageExpiryInterval = 300  # 5 menit
    
    client.publish(
        TOPIC_ADMIN_BROADCAST,
        payload=payload,
        qos=1,
        retain=(priority == "HIGH"),  # Retain hanya untuk HIGH priority (Fitur 5)
        properties=properties
    )
    print(f"[ADMIN] 📢 Broadcast dikirim: {title}")
    
    # Log ke shared topic (Fitur 9)
    log_payload = json.dumps({
        "source": "admin",
        "event": "BROADCAST",
        "detail": title,
        "timestamp": get_timestamp()
    })
    client.publish(TOPIC_SHARED_LOG, payload=log_payload, qos=1)


def send_command(client, command, room_id="", extra_data=None):
    """
    Kirim perintah ke perangkat/security
    Fitur 6: Message Expiry (perintah berbahaya expire cepat)
    Fitur 8: Request-Response Pattern
    """
    correlation_id = gen_correlation_id()
    
    payload = {
        "command": command,
        "room_id": room_id,
        "correlation_id": correlation_id,  # ← Fitur 8: Correlation Data
        "sender": CLIENT_ID,
        "timestamp": get_timestamp()
    }
    if extra_data:
        payload.update(extra_data)
    
    properties = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
    properties.UserProperty = [
        ("sender-role", "admin"),
        ("command-type", command)
    ]
    
    # ---- Fitur 6: Message Expiry ----
    # Perintah "UNLOCK" berbahaya → expire cepat!
    if command in ("UNLOCK", "LOCK_ALL", "ALARM_OFF"):
        properties.MessageExpiryInterval = 10  # 10 detik saja!
        print(f"[ADMIN] ⚠️ Perintah kritis '{command}' - expire 10 detik")
    else:
        properties.MessageExpiryInterval = 120
    
    # Simpan pending request (Fitur 8)
    with pending_lock:
        pending_requests[correlation_id] = {
            "command": command,
            "sent_at": time.time()
        }
    
    client.publish(
        TOPIC_ADMIN_COMMAND,
        payload=json.dumps(payload),
        qos=2,  # QoS 2: perintah kritis harus exactly once
        properties=properties
    )
    print(f"[ADMIN] 📤 Perintah dikirim: {command} (correlation: {correlation_id})")
    return correlation_id


def request_sensor_data(client, room_id="R001"):
    """
    Fitur 8: Request-Response Pattern
    Admin meminta data sensor → sensor mengirim response
    """
    correlation_id = gen_correlation_id()
    
    payload = json.dumps({
        "room_id": room_id,
        "correlation_id": correlation_id,
        "requester": CLIENT_ID,
        "timestamp": get_timestamp()
    })
    
    properties = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
    # ---- Fitur 8: Response Topic ----
    properties.ResponseTopic = TOPIC_RESPONSE
    properties.CorrelationData = correlation_id.encode()
    properties.UserProperty = [("requester", "admin")]
    properties.MessageExpiryInterval = 30
    
    with pending_lock:
        pending_requests[correlation_id] = {
            "command": f"REQUEST_SENSOR_{room_id}",
            "sent_at": time.time()
        }
    
    client.publish(
        TOPIC_REQUEST,
        payload=payload,
        qos=1,
        properties=properties
    )
    print(f"[ADMIN] 📤 Request data sensor {room_id} (correlation: {correlation_id})")


# =============================================
# INTERACTIVE MENU
# =============================================

def admin_menu(client):
    """Menu interaktif untuk admin"""
    
    # Kirim broadcast awal otomatis
    time.sleep(3)
    send_broadcast(client, "🏫 Sistem Study Room Aktif",
                   "Semua sistem monitoring ruang belajar telah aktif dan berjalan normal.",
                   "HIGH")
    
    print("\n" + "=" * 60)
    print("  ADMIN MENU - Ketik perintah:")
    print("=" * 60)
    print("  1  → Broadcast pengumuman")
    print("  2  → Request data sensor (Fitur 8)")
    print("  3  → Kunci semua pintu (Fitur 6)")
    print("  4  → Buka pintu ruangan (Fitur 6)")
    print("  5  → Cek status keamanan (Fitur 8)")
    print("  6  → Broadcast darurat")
    print("  7  → Auto-demo (semua fitur)")
    print("  0  → Keluar")
    print("=" * 60)
    
    while True:
        try:
            choice = input("\n[ADMIN] Pilih menu > ").strip()
            
            if choice == "1":
                title = input("  Judul: ").strip() or "Pengumuman"
                message = input("  Pesan: ").strip() or "Ini adalah pengumuman dari admin."
                send_broadcast(client, title, message)
            
            elif choice == "2":
                room = input("  Room ID (R001/R002): ").strip() or "R001"
                request_sensor_data(client, room)
            
            elif choice == "3":
                send_command(client, "LOCK_ALL")
            
            elif choice == "4":
                room = input("  Room ID: ").strip() or "R001"
                send_command(client, "UNLOCK", room_id=room)
            
            elif choice == "5":
                send_command(client, "STATUS")
            
            elif choice == "6":
                send_broadcast(client, "🚨 PERINGATAN DARURAT",
                             "Semua penghuni harap segera menuju titik kumpul!",
                             "HIGH")
            
            elif choice == "7":
                run_auto_demo(client)
            
            elif choice == "0":
                break
            
            else:
                print("  Pilihan tidak valid.")
        
        except (EOFError, KeyboardInterrupt):
            break


def run_auto_demo(client):
    """Auto-demo semua fitur MQTT"""
    print("\n[ADMIN] 🎬 Memulai auto-demo semua fitur MQTT...")
    
    # Demo 1: Broadcast dengan User Properties (Fitur 1, 4)
    print("\n--- Demo 1: Broadcast + User Properties (Fitur 1 & 4) ---")
    send_broadcast(client, "📋 Jadwal Maintenance",
                   "Ruang R005 akan dimaintenance besok pukul 08:00-12:00",
                   "NORMAL")
    time.sleep(2)
    
    # Demo 2: Request-Response (Fitur 8)
    print("\n--- Demo 2: Request-Response Pattern (Fitur 8) ---")
    request_sensor_data(client, "R001")
    time.sleep(3)
    request_sensor_data(client, "R002")
    time.sleep(3)
    
    # Demo 3: Perintah Kritis dengan Expiry (Fitur 6)
    print("\n--- Demo 3: Command + Message Expiry (Fitur 6) ---")
    send_command(client, "STATUS")
    time.sleep(2)
    send_command(client, "UNLOCK", room_id="R002")
    time.sleep(3)
    send_command(client, "LOCK_ALL")
    time.sleep(2)
    
    # Demo 4: Broadcast Darurat (Fitur 5: Retain)
    print("\n--- Demo 4: Emergency Broadcast + Retain (Fitur 5) ---")
    send_broadcast(client, "🔔 Informasi Penting",
                   "Jam operasional hari ini diperpanjang hingga pukul 22:00",
                   "HIGH")
    time.sleep(2)
    
    # Demo 5: Shared Subscription Log (Fitur 9)
    print("\n--- Demo 5: Shared Subscription Log (Fitur 9) ---")
    for i in range(3):
        log_payload = json.dumps({
            "source": "admin",
            "event": f"DEMO_LOG_{i+1}",
            "detail": f"Auto-demo log entry #{i+1}",
            "timestamp": get_timestamp()
        })
        client.publish(TOPIC_SHARED_LOG, payload=log_payload, qos=1)
        time.sleep(1)
    
    print("\n[ADMIN] ✅ Auto-demo selesai!")


# =============================================
# MAIN
# =============================================

def main():
    print("=" * 60)
    print("  PUBLISHER 3: ADMIN (Manajemen & Perintah)")
    print("  Role: Administrator sistem study room")
    print(f"  Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  Client ID: {CLIENT_ID}")
    print("=" * 60)
    print("  Fitur MQTT:")
    print("  ✓ Fitur 1: QoS (0, 1, 2)")
    print("  ✓ Fitur 4: User Properties")
    print("  ✓ Fitur 5: Retain Message")
    print("  ✓ Fitur 6: Message Expiry Interval")
    print("  ✓ Fitur 7: Last Will and Testament")
    print("  ✓ Fitur 8: Request-Response Pattern")
    print("  ✓ Fitur 9: Shared Subscriptions")
    print("=" * 60)
    
    # ---- Fitur 7: LWT ----
    lwt_payload = json.dumps({
        "client_id": CLIENT_ID,
        "status": "OFFLINE",
        "type": "admin",
        "reason": "Admin disconnected unexpectedly",
        "timestamp": get_timestamp()
    })
    
    client = mqtt.Client(
        client_id=CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        protocol=mqtt.MQTTv5
    )
    
    lwt_properties = mqtt.Properties(mqtt.PacketTypes.WILLMESSAGE)
    lwt_properties.WillDelayInterval = 3
    lwt_properties.MessageExpiryInterval = 300
    lwt_properties.UserProperty = [("reason", "connection-lost"), ("device-type", "admin")]
    
    client.will_set(
        topic=TOPIC_LWT,
        payload=lwt_payload,
        qos=1,
        retain=True,
        properties=lwt_properties
    )
    
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    
    # ---- Fitur 10: Flow Control ----
    connect_properties = mqtt.Properties(mqtt.PacketTypes.CONNECT)
    connect_properties.ReceiveMaximum = 10
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE, properties=connect_properties)
    except Exception as e:
        print(f"[ADMIN] ❌ Gagal terhubung: {e}")
        return
    
    client.loop_start()
    time.sleep(2)
    
    try:
        admin_menu(client)
    except KeyboardInterrupt:
        pass
    
    print("\n[ADMIN] 🛑 Shutting down...")
    offline_msg = json.dumps({
        "client_id": CLIENT_ID,
        "status": "OFFLINE",
        "type": "admin",
        "reason": "Graceful shutdown",
        "timestamp": get_timestamp()
    })
    client.publish(TOPIC_LWT, payload=offline_msg, qos=1, retain=True)
    time.sleep(1)
    client.loop_stop()
    client.disconnect()
    print("[ADMIN] 👋 Disconnected.")


if __name__ == "__main__":
    main()
