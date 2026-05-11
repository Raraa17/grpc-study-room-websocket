"""
Konfigurasi MQTT Study Room System
Menggunakan broker publik HiveMQ untuk kemudahan demo tanpa hardware.
"""

# =============================================
# MQTT BROKER CONFIGURATION
# =============================================
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60

# =============================================
# TOPIC STRUCTURE (Hierarki Topik)
# =============================================
# Format: its/studyroom/{gedung}/{ruangan}/{data_type}
#
# Contoh:
#   its/studyroom/gedungA/R001/suhu
#   its/studyroom/gedungA/R001/kelembapan
#   its/studyroom/gedungB/R002/status
#   its/studyroom/security/pintu/R001
#   its/studyroom/admin/broadcast
#   its/studyroom/admin/command

BASE_TOPIC = "its/studyroom"

# ---- Publisher: Sensor (Suhu, Kelembapan, Cahaya) ----
TOPIC_SENSOR_SUHU       = f"{BASE_TOPIC}/gedungA/R001/suhu"
TOPIC_SENSOR_KELEMBAPAN = f"{BASE_TOPIC}/gedungA/R001/kelembapan"
TOPIC_SENSOR_CAHAYA     = f"{BASE_TOPIC}/gedungA/R001/cahaya"
TOPIC_SENSOR_SUHU_R002  = f"{BASE_TOPIC}/gedungB/R002/suhu"
TOPIC_SENSOR_KELEMBAPAN_R002 = f"{BASE_TOPIC}/gedungB/R002/kelembapan"

# ---- Publisher: Security (Pintu, Gerakan, CCTV) ----
TOPIC_SECURITY_PINTU    = f"{BASE_TOPIC}/security/pintu/R001"
TOPIC_SECURITY_GERAKAN  = f"{BASE_TOPIC}/security/gerakan/R001"
TOPIC_SECURITY_STATUS   = f"{BASE_TOPIC}/security/status"

# ---- Publisher: Admin (Broadcast, Command, Perintah) ----
TOPIC_ADMIN_BROADCAST   = f"{BASE_TOPIC}/admin/broadcast"
TOPIC_ADMIN_COMMAND     = f"{BASE_TOPIC}/admin/command"
TOPIC_ADMIN_RESPONSE    = f"{BASE_TOPIC}/admin/response"

# ---- Fitur 8: Request-Response ----
TOPIC_REQUEST           = f"{BASE_TOPIC}/request/status"
TOPIC_RESPONSE          = f"{BASE_TOPIC}/response/status"

# ---- Fitur 9: Shared Subscription ----
TOPIC_SHARED_LOG        = f"{BASE_TOPIC}/log/activity"

# ---- Fitur 7: Last Will and Testament ----
TOPIC_LWT               = f"{BASE_TOPIC}/status/online"

# =============================================
# WILDCARD EXAMPLES (Fitur 2)
# =============================================
# Single-level (+): its/studyroom/+/R001/suhu
#   → Match: its/studyroom/gedungA/R001/suhu
#   → Match: its/studyroom/gedungB/R001/suhu
#
# Multi-level (#): its/studyroom/security/#
#   → Match: its/studyroom/security/pintu/R001
#   → Match: its/studyroom/security/gerakan/R001
#   → Match: its/studyroom/security/status

WILDCARD_SINGLE_SENSOR = f"{BASE_TOPIC}/+/R001/suhu"       # Fitur 2: Single-level wildcard
WILDCARD_MULTI_SECURITY = f"{BASE_TOPIC}/security/#"        # Fitur 2: Multi-level wildcard
WILDCARD_ALL_SENSORS = f"{BASE_TOPIC}/+/+/suhu"             # Semua sensor suhu
WILDCARD_ALL = f"{BASE_TOPIC}/#"                             # Semua topik

# =============================================
# TOPIC ALIAS MAP (Fitur 3)
# =============================================
# Mapping topic panjang → integer ID (efisiensi bandwidth)
TOPIC_ALIAS_MAP = {
    1: TOPIC_SENSOR_SUHU,
    2: TOPIC_SENSOR_KELEMBAPAN,
    3: TOPIC_SENSOR_CAHAYA,
    4: TOPIC_SECURITY_PINTU,
    5: TOPIC_SECURITY_GERAKAN,
    6: TOPIC_ADMIN_BROADCAST,
}

# =============================================
# FLASK DASHBOARD
# =============================================
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000
