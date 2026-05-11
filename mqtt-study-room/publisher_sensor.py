"""
=============================================================
PUBLISHER 1: SENSOR (Suhu, Kelembapan, Cahaya)
Role: Mensimulasikan sensor IoT di ruang belajar

Fitur MQTT yang didemonstrasikan:
  - Fitur 1: Publish/Subscribe & QoS (0, 1, 2)
  - Fitur 3: Topic Alias (efisiensi bandwidth)
  - Fitur 4: User Properties (metadata)
  - Fitur 5: Retain Message (pesan terakhir disimpan)
  - Fitur 6: Message Expiry Interval (waktu kedaluwarsa)
  - Fitur 7: Last Will and Testament (offline detection)
  - Fitur 10: Flow Control (Receive Maximum)
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

# Fix Windows encoding untuk emoji
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# =============================================
# KONFIGURASI PUBLISHER SENSOR
# =============================================
CLIENT_ID = "sensor-publisher-001"
PUBLISH_INTERVAL = 5  # detik

# Pemetaan ruangan ke gedung
ROOM_GEDUNG = {
    "R001": "gedungA", "R002": "gedungA", "R003": "gedungA",
    "R004": "gedungB", "R005": "gedungB",
}

# Simulasi data sensor – 5 ruangan
sensor_data = {
    "R001": {"suhu": 25.0, "kelembapan": 60.0, "cahaya": 300},
    "R002": {"suhu": 26.0, "kelembapan": 55.0, "cahaya": 280},
    "R003": {"suhu": 24.5, "kelembapan": 58.0, "cahaya": 320},
    "R004": {"suhu": 27.0, "kelembapan": 62.0, "cahaya": 250},
    "R005": {"suhu": 23.5, "kelembapan": 65.0, "cahaya": 310},
}

# Counter untuk Topic Alias (Fitur 3)
alias_counter = {}


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =============================================
# CALLBACK FUNCTIONS
# =============================================

def on_connect(client, userdata, flags, reason_code, properties):
    """Callback saat terhubung ke broker"""
    if reason_code == 0:
        print(f"[SENSOR] ✅ Terhubung ke broker {MQTT_BROKER}:{MQTT_PORT}")
        print(f"[SENSOR] Client ID: {CLIENT_ID}")
        
        # ---- Fitur 5: Retain Message ----
        # Kirim status online dengan retain=True
        # Subscriber baru akan langsung menerima status ini
        status_msg = json.dumps({
            "client_id": CLIENT_ID,
            "status": "ONLINE",
            "type": "sensor",
            "rooms": ["R001", "R002"],
            "timestamp": get_timestamp()
        })
        client.publish(
            TOPIC_LWT,
            payload=status_msg,
            qos=1,
            retain=True  # ← Fitur 5: Retain Message
        )
        print(f"[SENSOR] 📌 Retain message dikirim ke {TOPIC_LWT}")

        # ---- Fitur 8: Subscribe untuk Request-Response ----
        client.subscribe(TOPIC_REQUEST, qos=1)
        print(f"[SENSOR] 📥 Subscribed ke {TOPIC_REQUEST} (untuk request-response)")
    else:
        print(f"[SENSOR] ❌ Gagal terhubung, kode: {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties):
    """Callback saat terputus"""
    print(f"[SENSOR] ⚠️ Terputus dari broker. Kode: {reason_code}")


def on_publish(client, userdata, mid, reason_code, properties):
    """Callback saat pesan berhasil dikirim"""
    pass  # Bisa di-log jika perlu


def on_message(client, userdata, msg):
    """
    Callback saat menerima pesan (untuk Request-Response Pattern - Fitur 8)
    Sensor menerima request status dan mengirim response
    """
    try:
        payload = json.loads(msg.payload.decode())
        if msg.topic == TOPIC_REQUEST:
            print(f"[SENSOR] 📨 Request diterima: {payload}")
            
            # ---- Fitur 8: Request-Response Pattern ----
            # Kirim response dengan correlation_data
            room_id = payload.get("room_id", "R001")
            correlation_id = payload.get("correlation_id", "unknown")
            
            response = json.dumps({
                "correlation_id": correlation_id,  # ← Fitur 8: Correlation Data
                "room_id": room_id,
                "data": sensor_data.get(room_id, {}),
                "timestamp": get_timestamp(),
                "responder": CLIENT_ID
            })
            
            # Response Topic (Fitur 8)
            client.publish(
                TOPIC_RESPONSE,
                payload=response,
                qos=1
            )
            print(f"[SENSOR] 📤 Response dikirim untuk correlation_id: {correlation_id}")
    except Exception as e:
        print(f"[SENSOR] Error handling message: {e}")


# =============================================
# FUNGSI PUBLISH SENSOR DATA
# =============================================

def simulate_sensor_change():
    """Simulasi perubahan data sensor secara realistis"""
    for room_id in sensor_data:
        # Suhu berfluktuasi ±0.5°C
        sensor_data[room_id]["suhu"] += random.uniform(-0.5, 0.5)
        sensor_data[room_id]["suhu"] = round(max(18, min(35, sensor_data[room_id]["suhu"])), 1)
        
        # Kelembapan berfluktuasi ±2%
        sensor_data[room_id]["kelembapan"] += random.uniform(-2, 2)
        sensor_data[room_id]["kelembapan"] = round(max(30, min(90, sensor_data[room_id]["kelembapan"])), 1)
        
        # Cahaya berfluktuasi ±20 lux
        sensor_data[room_id]["cahaya"] += random.randint(-20, 20)
        sensor_data[room_id]["cahaya"] = max(0, min(1000, sensor_data[room_id]["cahaya"]))


def publish_sensor_data(client):
    """
    Publish data sensor dengan berbagai fitur MQTT
    """
    cycle = 0
    
    while True:
        simulate_sensor_change()
        cycle += 1
        
        for room_id, data in sensor_data.items():
            # =============================================
            # Fitur 1: QoS Levels (0, 1, 2)
            # =============================================
            
            # Bangun topic dinamis berdasarkan room_id & gedung (Fitur 2: Topic Hierarchy)
            gedung = ROOM_GEDUNG.get(room_id, "gedungA")

            # --- QoS 0: At most once (suhu) ---
            suhu_topic = f"{BASE_TOPIC}/{gedung}/{room_id}/suhu"
            suhu_payload = json.dumps({
                "room_id": room_id,
                "sensor": "suhu",
                "value": data["suhu"],
                "unit": "°C",
                "qos_level": 0,
                "timestamp": get_timestamp(),
                "user_properties": {
                    "app-version": "2.0.0",
                    "device-id": f"SENSOR-{room_id}-TEMP",
                    "unit": "celsius",
                    "location": f"ITS-DTI-{room_id}"
                }
            })
            properties = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
            properties.UserProperty = [
                ("app-version", "2.0.0"),
                ("device-id", f"SENSOR-{room_id}-TEMP"),
                ("unit", "celsius"),
                ("location", f"ITS-DTI-{room_id}")
            ]
            properties.MessageExpiryInterval = 30
            client.publish(suhu_topic, payload=suhu_payload, qos=0, properties=properties)

            # --- QoS 1: At least once (kelembapan) ---
            kelembapan_topic = f"{BASE_TOPIC}/{gedung}/{room_id}/kelembapan"
            kelembapan_payload = json.dumps({
                "room_id": room_id,
                "sensor": "kelembapan",
                "value": data["kelembapan"],
                "unit": "%",
                "qos_level": 1,
                "timestamp": get_timestamp(),
                "user_properties": {
                    "app-version": "2.0.0",
                    "device-id": f"SENSOR-{room_id}-HUM",
                    "unit": "percent",
                    "location": f"ITS-DTI-{room_id}"
                }
            })
            properties_hum = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
            properties_hum.UserProperty = [
                ("app-version", "2.0.0"),
                ("device-id", f"SENSOR-{room_id}-HUM"),
                ("unit", "percent")
            ]
            properties_hum.MessageExpiryInterval = 60
            client.publish(kelembapan_topic, payload=kelembapan_payload, qos=1, properties=properties_hum)

            # --- QoS 2: Exactly once (cahaya) ---
            cahaya_topic = f"{BASE_TOPIC}/{gedung}/{room_id}/cahaya"
            cahaya_payload = json.dumps({
                "room_id": room_id,
                "sensor": "cahaya",
                "value": data["cahaya"],
                "unit": "lux",
                "qos_level": 2,
                "timestamp": get_timestamp(),
                "user_properties": {
                    "app-version": "2.0.0",
                    "device-id": f"SENSOR-{room_id}-LUX",
                    "unit": "lux"
                }
            })
            properties_lux = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
            properties_lux.UserProperty = [
                ("app-version", "2.0.0"),
                ("device-id", f"SENSOR-{room_id}-LUX"),
                ("unit", "lux")
            ]
            properties_lux.MessageExpiryInterval = 120
            client.publish(cahaya_topic, payload=cahaya_payload, qos=2, properties=properties_lux)
        
        # Log setiap 3 cycle
        if cycle % 3 == 0:
            rooms_str = " | ".join(
                f"{rid}=[{d['suhu']}°C, {d['kelembapan']}%, {d['cahaya']}lux]"
                for rid, d in sensor_data.items()
            )
            print(f"[SENSOR] 📊 Cycle {cycle}: {rooms_str}")
        
        # ---- Fitur 5: Retain Message (update status retain setiap 10 cycle) ----
        if cycle % 10 == 0:
            retain_msg = json.dumps({
                "client_id": CLIENT_ID,
                "status": "ONLINE",
                "type": "sensor",
                "rooms": list(sensor_data.keys()),
                "last_data": {rid: d for rid, d in sensor_data.items()},
                "uptime_cycles": cycle,
                "timestamp": get_timestamp()
            })
            client.publish(TOPIC_LWT, payload=retain_msg, qos=1, retain=True)
        
        time.sleep(PUBLISH_INTERVAL)


# =============================================
# MAIN
# =============================================

def main():
    print("=" * 60)
    print("  PUBLISHER 1: SENSOR (Suhu, Kelembapan, Cahaya)")
    print("  Role: Simulasi sensor IoT ruang belajar")
    print(f"  Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  Client ID: {CLIENT_ID}")
    print("=" * 60)
    print("  Fitur MQTT:")
    print("  ✓ Fitur 1: QoS 0, 1, 2")
    print("  ✓ Fitur 3: Topic Alias")
    print("  ✓ Fitur 4: User Properties")
    print("  ✓ Fitur 5: Retain Message")
    print("  ✓ Fitur 6: Message Expiry Interval")
    print("  ✓ Fitur 7: Last Will and Testament")
    print("  ✓ Fitur 8: Request-Response (responder)")
    print("  ✓ Fitur 10: Flow Control")
    print("=" * 60)
    
    # =============================================
    # Fitur 7: Last Will and Testament (LWT)
    # Jika publisher mati tiba-tiba, broker akan
    # otomatis publish pesan "OFFLINE" ke topic LWT
    # =============================================
    lwt_payload = json.dumps({
        "client_id": CLIENT_ID,
        "status": "OFFLINE",
        "type": "sensor",
        "reason": "Unexpected disconnection",
        "timestamp": get_timestamp()
    })
    
    # Buat MQTT Client v5
    client = mqtt.Client(
        client_id=CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        protocol=mqtt.MQTTv5
    )
    
    # Set Last Will and Testament (Fitur 7)
    lwt_properties = mqtt.Properties(mqtt.PacketTypes.WILLMESSAGE)
    lwt_properties.WillDelayInterval = 5  # Delay 5 detik sebelum LWT dikirim
    lwt_properties.MessageExpiryInterval = 300  # LWT kedaluwarsa 5 menit
    lwt_properties.UserProperty = [
        ("reason", "connection-lost"),
        ("device-type", "sensor")
    ]
    
    client.will_set(
        topic=TOPIC_LWT,
        payload=lwt_payload,
        qos=1,
        retain=True,  # LWT juga retain agar subscriber baru tahu status offline
        properties=lwt_properties
    )
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    client.on_message = on_message
    
    # =============================================
    # Fitur 10: Flow Control (Receive Maximum)
    # Membatasi jumlah pesan in-flight
    # =============================================
    connect_properties = mqtt.Properties(mqtt.PacketTypes.CONNECT)
    connect_properties.ReceiveMaximum = 20  # Maksimal 20 pesan in-flight
    
    # Hubungkan ke broker
    try:
        client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            MQTT_KEEPALIVE,
            properties=connect_properties
        )
    except Exception as e:
        print(f"[SENSOR] ❌ Gagal terhubung: {e}")
        return
    
    # Jalankan loop MQTT di background thread
    client.loop_start()
    
    # Tunggu koneksi
    time.sleep(2)
    
    # Mulai publish data sensor
    try:
        publish_sensor_data(client)
    except KeyboardInterrupt:
        print("\n[SENSOR] 🛑 Shutting down...")
        
        # Kirim status offline sebelum disconnect
        offline_msg = json.dumps({
            "client_id": CLIENT_ID,
            "status": "OFFLINE",
            "type": "sensor",
            "reason": "Graceful shutdown",
            "timestamp": get_timestamp()
        })
        client.publish(TOPIC_LWT, payload=offline_msg, qos=1, retain=True)
        time.sleep(1)
        
        client.loop_stop()
        client.disconnect()
        print("[SENSOR] 👋 Disconnected.")


if __name__ == "__main__":
    main()
