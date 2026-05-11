"""
=============================================================
SUBSCRIBER 1: MONITOR (Dashboard Data Collector)
Role: Mengumpulkan semua data dari publisher untuk dashboard

Fitur MQTT yang didemonstrasikan:
  - Fitur 1: Subscribe dengan berbagai QoS
  - Fitur 2: Topic Wildcards (+ dan #)
  - Fitur 5: Retain Message (terima data terakhir saat connect)
  - Fitur 7: LWT Detection (deteksi publisher offline)
  - Fitur 9: Shared Subscriptions
  - Fitur 10: Flow Control
=============================================================
"""

import paho.mqtt.client as mqtt
import json
import time
import threading
import sys
import os
from datetime import datetime
from collections import deque
from config import *

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# =============================================
# KONFIGURASI
# =============================================
CLIENT_ID = "monitor-subscriber-001"

# Data store untuk dashboard
data_store = {
    "sensors": {},        # Data sensor terkini
    "security": {},       # Event keamanan
    "admin": [],          # Broadcast admin
    "online_status": {},  # Status online/offline publisher
    "activity_log": deque(maxlen=100),  # Log aktivitas
    "stats": {
        "total_messages": 0,
        "qos0_count": 0,
        "qos1_count": 0,
        "qos2_count": 0,
        "retained_count": 0,
        "topics_seen": set(),
    }
}
store_lock = threading.Lock()


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_activity(source, event, detail=""):
    """Catat aktivitas ke log"""
    entry = {
        "timestamp": get_timestamp(),
        "source": source,
        "event": event,
        "detail": detail
    }
    with store_lock:
        data_store["activity_log"].appendleft(entry)
    print(f"  [{source}] {event}: {detail}")


# =============================================
# CALLBACKS
# =============================================

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"[MONITOR] ✅ Terhubung ke broker {MQTT_BROKER}:{MQTT_PORT}")
        print(f"[MONITOR] Client ID: {CLIENT_ID}")
        print()
        
        # =============================================
        # Fitur 2: Topic Wildcards
        # Subscribe menggunakan wildcard + dan #
        # =============================================
        
        # --- Wildcard #: Multi-level (semua data sensor) ---
        # its/studyroom/+/+/suhu → semua sensor suhu di semua gedung
        client.subscribe(WILDCARD_ALL_SENSORS, qos=1)
        print(f"[MONITOR] 📥 Wildcard subscribe: {WILDCARD_ALL_SENSORS}")
        print(f"          → Match: its/studyroom/gedungA/R001/suhu")
        print(f"          → Match: its/studyroom/gedungB/R002/suhu")
        
        # --- Wildcard #: Semua data security ---
        # its/studyroom/security/# → semua event keamanan
        client.subscribe(WILDCARD_MULTI_SECURITY, qos=2)
        print(f"[MONITOR] 📥 Wildcard subscribe: {WILDCARD_MULTI_SECURITY}")
        print(f"          → Match: its/studyroom/security/pintu/R001")
        print(f"          → Match: its/studyroom/security/gerakan/R001")
        print(f"          → Match: its/studyroom/security/status")
        
        # --- Subscribe spesifik ---
        # Kelembapan semua ruangan
        client.subscribe(f"{BASE_TOPIC}/+/+/kelembapan", qos=1)
        print(f"[MONITOR] 📥 Wildcard subscribe: {BASE_TOPIC}/+/+/kelembapan")
        
        # Cahaya
        client.subscribe(TOPIC_SENSOR_CAHAYA, qos=2)
        print(f"[MONITOR] 📥 Subscribe: {TOPIC_SENSOR_CAHAYA}")
        
        # Admin broadcast
        client.subscribe(TOPIC_ADMIN_BROADCAST, qos=1)
        print(f"[MONITOR] 📥 Subscribe: {TOPIC_ADMIN_BROADCAST}")
        
        # ---- Fitur 7: LWT Detection ----
        # Subscribe ke topic status online/offline
        client.subscribe(TOPIC_LWT, qos=1)
        print(f"[MONITOR] 📥 Subscribe LWT: {TOPIC_LWT}")
        
        # ---- Fitur 9: Shared Subscription ----
        # Format: $share/nama_grup/topic
        # Pesan akan di-load balance ke subscriber dalam grup yang sama
        client.subscribe(f"$share/monitor_group/{TOPIC_SHARED_LOG}", qos=1)
        print(f"[MONITOR] 📥 Shared Subscribe: $share/monitor_group/{TOPIC_SHARED_LOG}")
        
        # Juga subscribe langsung ke shared log (fallback jika broker tidak support $share)
        client.subscribe(TOPIC_SHARED_LOG, qos=1)
        
        print(f"\n[MONITOR] 🎯 Menunggu pesan dari publisher...")
        print("=" * 60)
    else:
        print(f"[MONITOR] ❌ Gagal terhubung: {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties):
    print(f"[MONITOR] ⚠️ Terputus dari broker")


def on_message(client, userdata, msg):
    """
    Handler utama untuk semua pesan yang diterima
    Demonstrasi berbagai fitur MQTT
    """
    try:
        payload = json.loads(msg.payload.decode())
        topic = msg.topic
        qos = msg.qos
        retain = msg.retain
        
        with store_lock:
            data_store["stats"]["total_messages"] += 1
            data_store["stats"]["topics_seen"].add(topic)
            
            if qos == 0:
                data_store["stats"]["qos0_count"] += 1
            elif qos == 1:
                data_store["stats"]["qos1_count"] += 1
            elif qos == 2:
                data_store["stats"]["qos2_count"] += 1
            
            if retain:
                data_store["stats"]["retained_count"] += 1
        
        # ---- Fitur 5: Retain Message Detection ----
        if retain:
            print(f"\n[MONITOR] 📌 RETAIN MESSAGE diterima dari {topic}")
            print(f"          Data ini disimpan oleh broker untuk subscriber baru")
        
        # =============================================
        # ROUTING berdasarkan topic
        # =============================================
        
        # --- Sensor Data ---
        if "/suhu" in topic or "/kelembapan" in topic or "/cahaya" in topic:
            handle_sensor_data(topic, payload, qos, retain)
        
        # --- Security Events ---
        elif "/security/" in topic:
            handle_security_event(topic, payload, qos, retain)
        
        # --- Admin Broadcast ---
        elif topic == TOPIC_ADMIN_BROADCAST:
            handle_admin_broadcast(payload, retain)
        
        # --- Online/Offline Status (Fitur 7: LWT) ---
        elif topic == TOPIC_LWT:
            handle_lwt_status(payload, retain)
        
        # --- Shared Log (Fitur 9) ---
        elif topic == TOPIC_SHARED_LOG:
            handle_shared_log(payload)
        
        # --- Properties info (Fitur 4) ---
        if hasattr(msg, 'properties') and msg.properties:
            props = msg.properties
            if hasattr(props, 'UserProperty') and props.UserProperty:
                user_props = dict(props.UserProperty)
                if user_props:
                    log_activity("PROPS", "User Properties", f"Topic: {topic}, Props: {user_props}")
        
    except json.JSONDecodeError:
        print(f"[MONITOR] ⚠️ Pesan non-JSON dari {msg.topic}: {msg.payload.decode()[:100]}")
    except Exception as e:
        print(f"[MONITOR] Error: {e}")


# =============================================
# MESSAGE HANDLERS
# =============================================

def handle_sensor_data(topic, payload, qos, retain):
    """Handle data sensor (suhu, kelembapan, cahaya)"""
    room_id = payload.get("room_id", "unknown")
    sensor_type = payload.get("sensor", "unknown")
    value = payload.get("value", 0)
    unit = payload.get("unit", "")
    
    with store_lock:
        if room_id not in data_store["sensors"]:
            data_store["sensors"][room_id] = {}
        data_store["sensors"][room_id][sensor_type] = {
            "value": value,
            "unit": unit,
            "qos": qos,
            "timestamp": payload.get("timestamp", ""),
            "retain": retain
        }
    
    qos_label = ["At most once", "At least once", "Exactly once"][qos]
    log_activity("SENSOR", f"{sensor_type.upper()} {room_id}",
                 f"{value}{unit} (QoS {qos}: {qos_label})")
    
    # Alert jika suhu terlalu tinggi
    if sensor_type == "suhu" and value > 32:
        print(f"  ⚠️ PERINGATAN: Suhu {room_id} tinggi! {value}°C")
    
    # Alert jika kelembapan terlalu tinggi
    if sensor_type == "kelembapan" and value > 80:
        print(f"  ⚠️ PERINGATAN: Kelembapan {room_id} tinggi! {value}%")


def handle_security_event(topic, payload, qos, retain):
    """Handle event keamanan"""
    room_id = payload.get("room_id", "unknown")
    event_type = payload.get("event", payload.get("system", "STATUS"))
    
    with store_lock:
        data_store["security"][f"{room_id}_{event_type}"] = {
            "event": event_type,
            "room_id": room_id,
            "data": payload,
            "qos": qos,
            "timestamp": payload.get("timestamp", ""),
            "retain": retain
        }
    
    if "ALARM" in str(event_type):
        log_activity("SECURITY", f"🚨 ALARM {room_id}", str(payload.get("detail", "")))
    elif "PINTU" in str(event_type):
        log_activity("SECURITY", f"🚪 {event_type} {room_id}", 
                     payload.get("detail", ""))
    elif "GERAKAN" in str(event_type):
        log_activity("SECURITY", f"👁️ {event_type} {room_id}",
                     payload.get("detail", ""))
    else:
        log_activity("SECURITY", f"📋 Status Update", f"QoS={qos}")


def handle_admin_broadcast(payload, retain):
    """Handle broadcast admin"""
    title = payload.get("title", "Tanpa Judul")
    message = payload.get("message", "")
    priority = payload.get("priority", "NORMAL")
    
    with store_lock:
        data_store["admin"].append({
            "title": title,
            "message": message,
            "priority": priority,
            "timestamp": payload.get("timestamp", ""),
            "retain": retain
        })
    
    icon = "🚨" if priority == "HIGH" else "📢"
    log_activity("ADMIN", f"{icon} Broadcast", f"{title}: {message}")
    
    if retain:
        print(f"  📌 Broadcast ini adalah RETAIN (akan diterima subscriber baru)")


def handle_lwt_status(payload, retain):
    """
    Handle status online/offline publisher (Fitur 7: LWT)
    Ketika publisher mati, broker otomatis kirim pesan LWT
    """
    client_id = payload.get("client_id", "unknown")
    status = payload.get("status", "UNKNOWN")
    device_type = payload.get("type", "unknown")
    
    with store_lock:
        data_store["online_status"][client_id] = {
            "status": status,
            "type": device_type,
            "timestamp": payload.get("timestamp", ""),
            "retain": retain
        }
    
    if status == "ONLINE":
        log_activity("LWT", f"✅ ONLINE", f"{device_type} ({client_id})")
    elif status == "OFFLINE":
        reason = payload.get("reason", "Unknown")
        log_activity("LWT", f"❌ OFFLINE", f"{device_type} ({client_id}) - {reason}")
        if "Unexpected" in reason or "connection-lost" in reason:
            print(f"  🚨 PERINGATAN: {device_type} terputus tiba-tiba!")


def handle_shared_log(payload):
    """Handle shared subscription log (Fitur 9)"""
    source = payload.get("source", "unknown")
    event = payload.get("event", "")
    detail = payload.get("detail", "")
    log_activity("SHARED", f"📝 {source}: {event}", detail)


# =============================================
# STATUS REPORTER
# =============================================

def status_reporter():
    """Thread yang menampilkan statistik secara periodik"""
    while True:
        time.sleep(30)
        with store_lock:
            stats = data_store["stats"]
            sensors = data_store["sensors"]
            online = data_store["online_status"]
        
        print(f"\n{'=' * 60}")
        print(f"  📊 MONITOR STATUS REPORT - {get_timestamp()}")
        print(f"{'=' * 60}")
        print(f"  Total Pesan Diterima : {stats['total_messages']}")
        print(f"  QoS 0 (At most once): {stats['qos0_count']}")
        print(f"  QoS 1 (At least once): {stats['qos1_count']}")
        print(f"  QoS 2 (Exactly once): {stats['qos2_count']}")
        print(f"  Retained Messages    : {stats['retained_count']}")
        print(f"  Topics Unik         : {len(stats['topics_seen'])}")
        
        if sensors:
            print(f"\n  📡 Data Sensor Terkini:")
            for room_id, data in sensors.items():
                parts = []
                for sensor_type, info in data.items():
                    parts.append(f"{sensor_type}={info['value']}{info['unit']}")
                print(f"    {room_id}: {', '.join(parts)}")
        
        if online:
            print(f"\n  🟢 Status Publisher:")
            for cid, info in online.items():
                icon = "🟢" if info["status"] == "ONLINE" else "🔴"
                print(f"    {icon} {info['type']} ({cid}): {info['status']}")
        
        print(f"{'=' * 60}\n")


# =============================================
# MAIN
# =============================================

def main():
    print("=" * 60)
    print("  SUBSCRIBER 1: MONITOR (Dashboard Data Collector)")
    print("  Role: Mengumpulkan semua data untuk dashboard")
    print(f"  Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  Client ID: {CLIENT_ID}")
    print("=" * 60)
    print("  Fitur MQTT:")
    print("  ✓ Fitur 1: QoS 0, 1, 2 (subscribe)")
    print("  ✓ Fitur 2: Topic Wildcards (+ dan #)")
    print("  ✓ Fitur 5: Retain Message (detection)")
    print("  ✓ Fitur 7: LWT Detection")
    print("  ✓ Fitur 9: Shared Subscriptions")
    print("  ✓ Fitur 10: Flow Control")
    print("=" * 60)
    
    client = mqtt.Client(
        client_id=CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        protocol=mqtt.MQTTv5
    )
    
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    
    # ---- Fitur 10: Flow Control ----
    connect_properties = mqtt.Properties(mqtt.PacketTypes.CONNECT)
    connect_properties.ReceiveMaximum = 30  # Monitor bisa terima banyak
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE, properties=connect_properties)
    except Exception as e:
        print(f"[MONITOR] ❌ Gagal terhubung: {e}")
        return
    
    # Start status reporter thread
    reporter_thread = threading.Thread(target=status_reporter, daemon=True)
    reporter_thread.start()
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[MONITOR] 🛑 Shutting down...")
        client.disconnect()
        print("[MONITOR] 👋 Disconnected.")


if __name__ == "__main__":
    main()
