"""
=============================================================
PUBLISHER 2: SECURITY (Keamanan Gedung)
Role: Mensimulasikan sistem keamanan gedung kampus

Fitur MQTT yang didemonstrasikan:
  - Fitur 1: Publish/Subscribe & QoS (terutama QoS 2 untuk keamanan)
  - Fitur 2: Topic Wildcards (publish ke topic hierarki)
  - Fitur 5: Retain Message (status keamanan terakhir)
  - Fitur 6: Message Expiry Interval (perintah kedaluwarsa)
  - Fitur 7: Last Will and Testament
  - Fitur 4: User Properties
=============================================================
"""

import paho.mqtt.client as mqtt
import json
import time
import random
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
CLIENT_ID = "security-publisher-002"
PUBLISH_INTERVAL = 7  # detik

# State simulasi keamanan
security_state = {
    "R001": {"pintu": "TERKUNCI", "gerakan": False, "terakhir_akses": None},
    "R002": {"pintu": "TERKUNCI", "gerakan": False, "terakhir_akses": None},
    "R003": {"pintu": "TERBUKA", "gerakan": True, "terakhir_akses": None},
}

# Daftar aksi simulasi
SIMULATED_EVENTS = [
    {"type": "PINTU_DIBUKA", "detail": "Kartu akses digunakan"},
    {"type": "PINTU_DITUTUP", "detail": "Pintu ditutup otomatis"},
    {"type": "GERAKAN_TERDETEKSI", "detail": "Sensor PIR aktif"},
    {"type": "TIDAK_ADA_GERAKAN", "detail": "Ruangan kosong selama 10 menit"},
    {"type": "AKSES_DITOLAK", "detail": "Kartu tidak dikenali"},
    {"type": "ALARM_AKTIF", "detail": "Percobaan akses tidak sah"},
]


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =============================================
# CALLBACKS
# =============================================

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"[SECURITY] ✅ Terhubung ke broker {MQTT_BROKER}:{MQTT_PORT}")
        
        # ---- Fitur 5: Retain Message ----
        # Kirim status keamanan awal dengan retain
        status_msg = json.dumps({
            "client_id": CLIENT_ID,
            "status": "ONLINE",
            "type": "security",
            "monitored_rooms": list(security_state.keys()),
            "security_level": "NORMAL",
            "timestamp": get_timestamp()
        })
        client.publish(TOPIC_LWT, payload=status_msg, qos=1, retain=True)
        print(f"[SECURITY] 📌 Retain status dikirim")
        
        # ---- Fitur 5: Retain Message untuk status keamanan keseluruhan ----
        security_overview = json.dumps({
            "system": "ARMED",
            "cameras_active": 4,
            "doors_monitored": len(security_state),
            "alert_level": "GREEN",
            "timestamp": get_timestamp()
        })
        client.publish(TOPIC_SECURITY_STATUS, payload=security_overview, qos=1, retain=True)
        
        # Subscribe untuk perintah admin (Fitur 8: Request-Response)
        client.subscribe(TOPIC_ADMIN_COMMAND, qos=2)
        print(f"[SECURITY] 📥 Subscribed ke {TOPIC_ADMIN_COMMAND}")
    else:
        print(f"[SECURITY] ❌ Gagal terhubung: {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties):
    print(f"[SECURITY] ⚠️ Terputus dari broker")


def on_message(client, userdata, msg):
    """Handle perintah dari admin (Fitur 8: Request-Response)"""
    try:
        payload = json.loads(msg.payload.decode())
        command = payload.get("command", "")
        
        print(f"[SECURITY] 📨 Perintah diterima: {command}")
        
        if command == "LOCK_ALL":
            for room_id in security_state:
                security_state[room_id]["pintu"] = "TERKUNCI"
            response = {"status": "OK", "message": "Semua pintu dikunci", "timestamp": get_timestamp()}
        elif command == "UNLOCK":
            room_id = payload.get("room_id", "R001")
            if room_id in security_state:
                security_state[room_id]["pintu"] = "TERBUKA"
                response = {"status": "OK", "message": f"Pintu {room_id} dibuka", "timestamp": get_timestamp()}
            else:
                response = {"status": "ERROR", "message": f"Ruangan {room_id} tidak ditemukan"}
        elif command == "STATUS":
            response = {
                "status": "OK",
                "security_state": {k: v["pintu"] for k, v in security_state.items()},
                "timestamp": get_timestamp()
            }
        else:
            response = {"status": "UNKNOWN", "message": f"Perintah tidak dikenal: {command}"}
        
        # Kirim response (Fitur 8)
        response["correlation_id"] = payload.get("correlation_id", "")
        client.publish(TOPIC_ADMIN_RESPONSE, payload=json.dumps(response), qos=2)
        
    except Exception as e:
        print(f"[SECURITY] Error: {e}")


# =============================================
# PUBLISH SECURITY EVENTS
# =============================================

def publish_security_events(client):
    """Publish event keamanan secara periodik"""
    cycle = 0
    
    while True:
        cycle += 1
        
        # Pilih ruangan dan event random
        room_id = random.choice(list(security_state.keys()))
        event = random.choice(SIMULATED_EVENTS)
        
        # Update state
        if event["type"] == "PINTU_DIBUKA":
            security_state[room_id]["pintu"] = "TERBUKA"
            security_state[room_id]["terakhir_akses"] = get_timestamp()
        elif event["type"] == "PINTU_DITUTUP":
            security_state[room_id]["pintu"] = "TERKUNCI"
        elif event["type"] == "GERAKAN_TERDETEKSI":
            security_state[room_id]["gerakan"] = True
        elif event["type"] == "TIDAK_ADA_GERAKAN":
            security_state[room_id]["gerakan"] = False
        
        # =============================================
        # Publish ke topic hierarki (Fitur 2: Topic Wildcards)
        # Subscriber bisa pakai wildcard untuk subscribe
        # =============================================
        
        # --- Event pintu: QoS 2 (perintah kritis, exactly once) ---
        if "PINTU" in event["type"] or "AKSES" in event["type"] or "ALARM" in event["type"]:
            pintu_topic = f"{BASE_TOPIC}/security/pintu/{room_id}"
            pintu_payload = json.dumps({
                "room_id": room_id,
                "event": event["type"],
                "detail": event["detail"],
                "pintu_status": security_state[room_id]["pintu"],
                "timestamp": get_timestamp(),
                # ---- Fitur 4: User Properties ----
                "user_properties": {
                    "device-id": f"DOOR-{room_id}",
                    "priority": "HIGH" if "ALARM" in event["type"] else "NORMAL",
                    "app-version": "2.0.0"
                }
            })
            
            properties = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
            properties.UserProperty = [
                ("device-id", f"DOOR-{room_id}"),
                ("priority", "HIGH" if "ALARM" in event["type"] else "NORMAL"),
                ("app-version", "2.0.0")
            ]
            
            # ---- Fitur 6: Message Expiry ----
            # Perintah pintu kedaluwarsa 10 detik (keamanan!)
            if "ALARM" in event["type"]:
                properties.MessageExpiryInterval = 10  # ALARM cepat expire
            else:
                properties.MessageExpiryInterval = 60
            
            client.publish(
                pintu_topic,
                payload=pintu_payload,
                qos=2,  # ← Fitur 1: QoS 2 untuk keamanan
                properties=properties
            )
            
            if "ALARM" in event["type"]:
                print(f"[SECURITY] 🚨 ALARM! {room_id}: {event['detail']}")
            else:
                print(f"[SECURITY] 🚪 {room_id}: {event['type']} - {event['detail']}")
        
        # --- Event gerakan: QoS 1 ---
        if "GERAKAN" in event["type"]:
            gerakan_topic = f"{BASE_TOPIC}/security/gerakan/{room_id}"
            gerakan_payload = json.dumps({
                "room_id": room_id,
                "event": event["type"],
                "detail": event["detail"],
                "motion_detected": security_state[room_id]["gerakan"],
                "timestamp": get_timestamp(),
                "user_properties": {
                    "device-id": f"PIR-{room_id}",
                    "sensor-type": "infrared"
                }
            })
            
            properties_motion = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
            properties_motion.UserProperty = [
                ("device-id", f"PIR-{room_id}"),
                ("sensor-type", "infrared")
            ]
            properties_motion.MessageExpiryInterval = 30
            
            client.publish(
                gerakan_topic,
                payload=gerakan_payload,
                qos=1,  # ← Fitur 1: QoS 1
                properties=properties_motion
            )
            print(f"[SECURITY] 👁️ {room_id}: {event['type']}")
        
        # Log ke shared topic (Fitur 9)
        log_payload = json.dumps({
            "source": "security",
            "room_id": room_id,
            "event": event["type"],
            "detail": event["detail"],
            "timestamp": get_timestamp()
        })
        client.publish(TOPIC_SHARED_LOG, payload=log_payload, qos=1)
        
        # Update retain status keamanan setiap 5 cycle (Fitur 5)
        if cycle % 5 == 0:
            overview = json.dumps({
                "system": "ARMED",
                "doors": {k: v["pintu"] for k, v in security_state.items()},
                "motion": {k: v["gerakan"] for k, v in security_state.items()},
                "alert_level": "RED" if any("ALARM" in str(e) for e in [event]) else "GREEN",
                "timestamp": get_timestamp()
            })
            client.publish(TOPIC_SECURITY_STATUS, payload=overview, qos=1, retain=True)
        
        time.sleep(PUBLISH_INTERVAL)


# =============================================
# MAIN
# =============================================

def main():
    print("=" * 60)
    print("  PUBLISHER 2: SECURITY (Keamanan Gedung)")
    print("  Role: Simulasi sistem keamanan kampus")
    print(f"  Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  Client ID: {CLIENT_ID}")
    print("=" * 60)
    print("  Fitur MQTT:")
    print("  ✓ Fitur 1: QoS 2 untuk keamanan")
    print("  ✓ Fitur 2: Topic Hierarchy (untuk wildcards)")
    print("  ✓ Fitur 4: User Properties")
    print("  ✓ Fitur 5: Retain Message")
    print("  ✓ Fitur 6: Message Expiry Interval")
    print("  ✓ Fitur 7: Last Will and Testament")
    print("  ✓ Fitur 8: Request-Response (command handler)")
    print("=" * 60)
    
    # ---- Fitur 7: Last Will and Testament ----
    lwt_payload = json.dumps({
        "client_id": CLIENT_ID,
        "status": "OFFLINE",
        "type": "security",
        "reason": "Unexpected disconnection - SECURITY SYSTEM DOWN!",
        "alert": "CRITICAL",
        "timestamp": get_timestamp()
    })
    
    client = mqtt.Client(
        client_id=CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        protocol=mqtt.MQTTv5
    )
    
    lwt_properties = mqtt.Properties(mqtt.PacketTypes.WILLMESSAGE)
    lwt_properties.WillDelayInterval = 2  # Security: delay minimal
    lwt_properties.MessageExpiryInterval = 600  # 10 menit
    lwt_properties.UserProperty = [("reason", "connection-lost"), ("device-type", "security")]
    
    client.will_set(
        topic=TOPIC_LWT,
        payload=lwt_payload,
        qos=2,  # QoS 2 untuk LWT security (kritis!)
        retain=True,
        properties=lwt_properties
    )
    
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    
    # ---- Fitur 10: Flow Control ----
    connect_properties = mqtt.Properties(mqtt.PacketTypes.CONNECT)
    connect_properties.ReceiveMaximum = 15
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE, properties=connect_properties)
    except Exception as e:
        print(f"[SECURITY] ❌ Gagal terhubung: {e}")
        return
    
    client.loop_start()
    time.sleep(2)
    
    try:
        publish_security_events(client)
    except KeyboardInterrupt:
        print("\n[SECURITY] 🛑 Shutting down...")
        offline_msg = json.dumps({
            "client_id": CLIENT_ID,
            "status": "OFFLINE",
            "type": "security",
            "reason": "Graceful shutdown",
            "timestamp": get_timestamp()
        })
        client.publish(TOPIC_LWT, payload=offline_msg, qos=1, retain=True)
        time.sleep(1)
        client.loop_stop()
        client.disconnect()
        print("[SECURITY] 👋 Disconnected.")


if __name__ == "__main__":
    main()
