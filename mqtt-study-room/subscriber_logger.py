"""
=============================================================
SUBSCRIBER 2: LOGGER (Pencatat & Arsip)
Role: Mencatat semua aktivitas MQTT ke file log

Fitur MQTT yang didemonstrasikan:
  - Fitur 1: Subscribe dengan QoS
  - Fitur 2: Topic Wildcards (# untuk subscribe semua)
  - Fitur 5: Retain Message (flag detection)
  - Fitur 7: LWT (deteksi publisher offline)
  - Fitur 9: Shared Subscriptions (load balancing)
  - Fitur 10: Flow Control (backpressure)
=============================================================
"""

import paho.mqtt.client as mqtt
import json
import time
import os
import sys
import threading
from datetime import datetime
from config import *

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# =============================================
# KONFIGURASI
# =============================================
CLIENT_ID = "logger-subscriber-002"
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, f"mqtt_log_{datetime.now().strftime('%Y%m%d')}.log")

# Statistik
stats = {
    "total": 0,
    "by_topic": {},
    "by_qos": {0: 0, 1: 0, 2: 0},
    "retained": 0,
    "errors": 0,
    "start_time": None
}
stats_lock = threading.Lock()


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def write_log(log_entry):
    """Tulis log ke file"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[LOGGER] ❌ Error menulis log: {e}")


# =============================================
# CALLBACKS
# =============================================

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"[LOGGER] ✅ Terhubung ke broker {MQTT_BROKER}:{MQTT_PORT}")
        print(f"[LOGGER] 📁 Log file: {LOG_FILE}")
        
        with stats_lock:
            stats["start_time"] = get_timestamp()
        
        # =============================================
        # Fitur 2: Topic Wildcards
        # Subscribe ALL topics menggunakan multi-level wildcard #
        # =============================================
        
        # Subscribe semua topik study room (Fitur 2: Multi-level wildcard)
        client.subscribe(WILDCARD_ALL, qos=1)
        print(f"[LOGGER] 📥 Wildcard subscribe: {WILDCARD_ALL}")
        print(f"          → Menangkap SEMUA pesan di bawah {BASE_TOPIC}/")
        
        # ---- Fitur 9: Shared Subscription ----
        # Logger juga join shared group untuk load balancing
        client.subscribe(f"$share/logger_group/{TOPIC_SHARED_LOG}", qos=1)
        print(f"[LOGGER] 📥 Shared Subscribe: $share/logger_group/{TOPIC_SHARED_LOG}")
        
        print(f"\n[LOGGER] 📝 Mencatat semua pesan MQTT...")
        print("=" * 60)
        
        # Tulis header log
        write_log({
            "event": "LOGGER_STARTED",
            "timestamp": get_timestamp(),
            "client_id": CLIENT_ID,
            "broker": f"{MQTT_BROKER}:{MQTT_PORT}",
            "subscriptions": [WILDCARD_ALL, f"$share/logger_group/{TOPIC_SHARED_LOG}"]
        })
    else:
        print(f"[LOGGER] ❌ Gagal terhubung: {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties):
    print(f"[LOGGER] ⚠️ Terputus dari broker")
    write_log({
        "event": "LOGGER_DISCONNECTED",
        "timestamp": get_timestamp(),
        "reason_code": reason_code
    })


def on_message(client, userdata, msg):
    """
    Handler utama: catat semua pesan ke log file
    """
    try:
        # Parse payload
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {"raw": msg.payload.decode("utf-8", errors="replace")}
        
        topic = msg.topic
        qos = msg.qos
        retain = msg.retain
        
        # Update statistik
        with stats_lock:
            stats["total"] += 1
            stats["by_qos"][qos] += 1
            if retain:
                stats["retained"] += 1
            
            # Hitung per topic
            topic_base = "/".join(topic.split("/")[:4])  # Ambil 4 level pertama
            stats["by_topic"][topic_base] = stats["by_topic"].get(topic_base, 0) + 1
        
        # Buat log entry
        log_entry = {
            "timestamp": get_timestamp(),
            "topic": topic,
            "qos": qos,
            "retain": retain,
            "payload_size": len(msg.payload),
            "payload": payload
        }
        
        # ---- Fitur 4: User Properties ----
        # Catat user properties jika ada
        if hasattr(msg, 'properties') and msg.properties:
            props = msg.properties
            if hasattr(props, 'UserProperty') and props.UserProperty:
                log_entry["user_properties"] = dict(props.UserProperty)
            if hasattr(props, 'MessageExpiryInterval') and props.MessageExpiryInterval:
                log_entry["message_expiry"] = props.MessageExpiryInterval
            if hasattr(props, 'CorrelationData') and props.CorrelationData:
                log_entry["correlation_data"] = props.CorrelationData.decode("utf-8", errors="replace")
            if hasattr(props, 'ResponseTopic') and props.ResponseTopic:
                log_entry["response_topic"] = props.ResponseTopic
        
        # Tulis ke file
        write_log(log_entry)
        
        # Console output
        qos_labels = {0: "QoS0", 1: "QoS1", 2: "QoS2"}
        retain_tag = " [RETAIN]" if retain else ""
        
        # Determine icon based on topic
        if "/suhu" in topic:
            icon = "🌡️"
        elif "/kelembapan" in topic:
            icon = "💧"
        elif "/cahaya" in topic:
            icon = "💡"
        elif "/security/" in topic:
            icon = "🔒"
        elif "/admin/" in topic:
            icon = "👨‍💼"
        elif "/status/" in topic:
            icon = "📡"
        elif "/log/" in topic:
            icon = "📝"
        else:
            icon = "📨"
        
        with stats_lock:
            msg_num = stats["total"]
        
        print(f"  #{msg_num:04d} {icon} [{qos_labels[qos]}]{retain_tag} {topic}")
        
        # ---- Fitur 7: LWT Detection ----
        if topic == TOPIC_LWT:
            status = payload.get("status", "")
            client_name = payload.get("client_id", "unknown")
            device_type = payload.get("type", "")
            if status == "OFFLINE":
                print(f"        🔴 PUBLISHER OFFLINE: {device_type} ({client_name})")
                reason = payload.get("reason", "")
                if "Unexpected" in reason:
                    print(f"        ⚠️ PEMUTUSAN TIDAK TERDUGA - LWT AKTIF!")
            elif status == "ONLINE":
                print(f"        🟢 PUBLISHER ONLINE: {device_type} ({client_name})")
        
        # Alert untuk pesan kritis
        if isinstance(payload, dict):
            if payload.get("priority") == "HIGH":
                print(f"        🚨 HIGH PRIORITY: {payload.get('title', '')}")
            if "ALARM" in str(payload.get("event", "")):
                print(f"        🚨 ALARM DETECTED!")
        
    except Exception as e:
        with stats_lock:
            stats["errors"] += 1
        print(f"[LOGGER] ❌ Error: {e}")


# =============================================
# STATISTICS REPORTER
# =============================================

def stats_reporter():
    """Tampilkan statistik secara periodik"""
    while True:
        time.sleep(45)
        with stats_lock:
            s = dict(stats)
            s["by_topic"] = dict(s["by_topic"])
        
        print(f"\n{'─' * 60}")
        print(f"  📊 LOGGER STATISTIK - {get_timestamp()}")
        print(f"{'─' * 60}")
        print(f"  Mulai sejak    : {s['start_time']}")
        print(f"  Total pesan    : {s['total']}")
        print(f"  QoS 0          : {s['by_qos'][0]}")
        print(f"  QoS 1          : {s['by_qos'][1]}")
        print(f"  QoS 2          : {s['by_qos'][2]}")
        print(f"  Retained       : {s['retained']}")
        print(f"  Errors         : {s['errors']}")
        
        if s["by_topic"]:
            print(f"\n  📈 Pesan per Topic:")
            for topic, count in sorted(s["by_topic"].items(), key=lambda x: -x[1]):
                bar = "█" * min(count, 30)
                print(f"    {topic}: {count} {bar}")
        
        print(f"  📁 Log file: {LOG_FILE}")
        try:
            size = os.path.getsize(LOG_FILE) / 1024
            print(f"  📁 File size: {size:.1f} KB")
        except FileNotFoundError:
            pass
        print(f"{'─' * 60}\n")


# =============================================
# MAIN
# =============================================

def main():
    ensure_log_dir()
    
    print("=" * 60)
    print("  SUBSCRIBER 2: LOGGER (Pencatat & Arsip)")
    print("  Role: Mencatat semua aktivitas MQTT ke file")
    print(f"  Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  Client ID: {CLIENT_ID}")
    print(f"  Log File: {LOG_FILE}")
    print("=" * 60)
    print("  Fitur MQTT:")
    print("  ✓ Fitur 1: QoS (subscribe)")
    print("  ✓ Fitur 2: Topic Wildcards (# catch-all)")
    print("  ✓ Fitur 5: Retain Message detection")
    print("  ✓ Fitur 7: LWT detection")
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
    connect_properties.ReceiveMaximum = 50  # Logger bisa buffer banyak
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE, properties=connect_properties)
    except Exception as e:
        print(f"[LOGGER] ❌ Gagal terhubung: {e}")
        return
    
    # Start stats reporter
    reporter = threading.Thread(target=stats_reporter, daemon=True)
    reporter.start()
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[LOGGER] 🛑 Shutting down...")
        write_log({
            "event": "LOGGER_STOPPED",
            "timestamp": get_timestamp(),
            "total_messages": stats["total"]
        })
        client.disconnect()
        print(f"[LOGGER] 📁 Log tersimpan di: {LOG_FILE}")
        print("[LOGGER] 👋 Disconnected.")


if __name__ == "__main__":
    main()
