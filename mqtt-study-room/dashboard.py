"""
<<<<<<< HEAD
Dashboard Monitoring MQTT - Flask + SocketIO
Subscriber sekaligus web server untuk monitoring real-time
"""

import sys
import os
# Fix Windows encoding untuk emoji
=======
Dashboard Monitoring MQTT - Flask + SocketIO (Enhanced Interactive)
"""
import sys, os
>>>>>>> 8296d15 (update)
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import paho.mqtt.client as mqtt
<<<<<<< HEAD
import json
import time
import threading
=======
import json, threading
>>>>>>> 8296d15 (update)
from datetime import datetime
from collections import deque
from flask import Flask, render_template_string
from flask_socketio import SocketIO
from config import *

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mqtt-study-room-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

<<<<<<< HEAD
# Data store
dashboard_data = {
    "sensors": {},
    "security_events": deque(maxlen=50),
    "admin_broadcasts": deque(maxlen=20),
    "online_status": {},
    "activity_log": deque(maxlen=100),
    "stats": {"total": 0, "qos0": 0, "qos1": 0, "qos2": 0, "retained": 0}
}
data_lock = threading.Lock()

def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# =============================================
# MQTT CALLBACKS
# =============================================
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"[DASHBOARD] ✅ MQTT terhubung ke {MQTT_BROKER}")
        client.subscribe(WILDCARD_ALL, qos=2)           # QoS 2 agar tidak di-downgrade
        client.subscribe(WILDCARD_MULTI_SECURITY, qos=2)
        client.subscribe(TOPIC_LWT, qos=1)
        client.subscribe(TOPIC_SHARED_LOG, qos=1)
        print(f"[DASHBOARD] 📥 Subscribed ke semua topik (QoS 2)")

=======
dashboard_data = {
    "sensors": {}, "sensor_history": {},
    "security_events": deque(maxlen=50), "admin_broadcasts": deque(maxlen=20),
    "online_status": {}, "activity_log": deque(maxlen=100),
    "stats": {"total":0,"qos0":0,"qos1":0,"qos2":0,"retained":0}
}
data_lock = threading.Lock()

def ts(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"[DASHBOARD] MQTT terhubung ke {MQTT_BROKER}")
        client.subscribe(WILDCARD_ALL, qos=2)
        client.subscribe(WILDCARD_MULTI_SECURITY, qos=2)
        client.subscribe(TOPIC_LWT, qos=1)
        client.subscribe(TOPIC_SHARED_LOG, qos=1)
>>>>>>> 8296d15 (update)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
<<<<<<< HEAD
        topic = msg.topic
        qos = msg.qos
        retain = msg.retain

        with data_lock:
            dashboard_data["stats"]["total"] += 1
            dashboard_data["stats"][f"qos{qos}"] += 1
            if retain:
                dashboard_data["stats"]["retained"] += 1

        entry = {"topic": topic, "qos": qos, "retain": retain, "payload": payload, "timestamp": ts()}

        if "/suhu" in topic or "/kelembapan" in topic or "/cahaya" in topic:
            room_id = payload.get("room_id", "?")
            sensor = payload.get("sensor", "?")
            with data_lock:
                if room_id not in dashboard_data["sensors"]:
                    dashboard_data["sensors"][room_id] = {}
                dashboard_data["sensors"][room_id][sensor] = {
                    "value": payload.get("value", 0),
                    "unit": payload.get("unit", ""),
                    "qos": qos, "timestamp": payload.get("timestamp", "")
                }
            socketio.emit('sensor_update', {"room_id": room_id, "sensor": sensor,
                          "value": payload.get("value",0), "unit": payload.get("unit",""),
                          "qos": qos, "retain": retain, "timestamp": ts()})

        elif "/security/" in topic:
            with data_lock:
                dashboard_data["security_events"].appendleft(entry)
            socketio.emit('security_event', entry)

        elif topic == TOPIC_ADMIN_BROADCAST:
            with data_lock:
                dashboard_data["admin_broadcasts"].appendleft(entry)
            socketio.emit('admin_broadcast', entry)

        elif topic == TOPIC_LWT:
            cid = payload.get("client_id", "?")
            with data_lock:
                dashboard_data["online_status"][cid] = {
                    "status": payload.get("status","?"),
                    "type": payload.get("type","?"),
                    "timestamp": payload.get("timestamp","")
                }
            socketio.emit('status_update', {"client_id": cid, **dashboard_data["online_status"][cid]})

        elif topic == TOPIC_SHARED_LOG:
            socketio.emit('shared_log', entry)

        with data_lock:
            dashboard_data["activity_log"].appendleft(entry)
        socketio.emit('activity', entry)
        socketio.emit('stats_update', dict(dashboard_data["stats"]))

    except Exception as e:
        print(f"[DASHBOARD] Error: {e}")

# =============================================
# FLASK ROUTES
# =============================================
@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)
=======
        topic, qos, retain = msg.topic, msg.qos, msg.retain
        with data_lock:
            dashboard_data["stats"]["total"] += 1
            dashboard_data["stats"][f"qos{qos}"] += 1
            if retain: dashboard_data["stats"]["retained"] += 1
        entry = {"topic":topic,"qos":qos,"retain":retain,"payload":payload,"timestamp":ts()}

        if "/suhu" in topic or "/kelembapan" in topic or "/cahaya" in topic:
            room_id = payload.get("room_id","?")
            sensor = payload.get("sensor","?")
            value = payload.get("value",0)
            with data_lock:
                if room_id not in dashboard_data["sensors"]: dashboard_data["sensors"][room_id] = {}
                dashboard_data["sensors"][room_id][sensor] = {"value":value,"unit":payload.get("unit",""),"qos":qos,"timestamp":payload.get("timestamp","")}
                if room_id not in dashboard_data["sensor_history"]: dashboard_data["sensor_history"][room_id] = {}
                if sensor not in dashboard_data["sensor_history"][room_id]: dashboard_data["sensor_history"][room_id][sensor] = deque(maxlen=20)
                dashboard_data["sensor_history"][room_id][sensor].append({"value":value,"timestamp":ts()})
            socketio.emit('sensor_update',{"room_id":room_id,"sensor":sensor,"value":value,"unit":payload.get("unit",""),"qos":qos,"retain":retain,"timestamp":ts()})
        elif "/security/" in topic:
            with data_lock: dashboard_data["security_events"].appendleft(entry)
            socketio.emit('security_event', entry)
        elif topic == TOPIC_ADMIN_BROADCAST:
            with data_lock: dashboard_data["admin_broadcasts"].appendleft(entry)
            socketio.emit('admin_broadcast', entry)
        elif topic == TOPIC_LWT:
            cid = payload.get("client_id","?")
            with data_lock:
                dashboard_data["online_status"][cid] = {"status":payload.get("status","?"),"type":payload.get("type","?"),"timestamp":payload.get("timestamp","")}
            socketio.emit('status_update',{"client_id":cid,**dashboard_data["online_status"][cid]})
        elif topic == TOPIC_SHARED_LOG:
            socketio.emit('shared_log', entry)

        with data_lock: dashboard_data["activity_log"].appendleft(entry)
        socketio.emit('activity', entry)
        socketio.emit('stats_update', dict(dashboard_data["stats"]))
    except Exception as e:
        print(f"[DASHBOARD] Error: {e}")

@app.route('/')
def index(): return render_template_string(DASHBOARD_HTML)
>>>>>>> 8296d15 (update)

@app.route('/api/data')
def api_data():
    with data_lock:
        return json.dumps({
            "sensors": dashboard_data["sensors"],
<<<<<<< HEAD
=======
            "sensor_history": {room:{s:list(h) for s,h in sensors.items()} for room,sensors in dashboard_data["sensor_history"].items()},
>>>>>>> 8296d15 (update)
            "security": list(dashboard_data["security_events"])[:20],
            "broadcasts": list(dashboard_data["admin_broadcasts"])[:10],
            "online_status": dashboard_data["online_status"],
            "activity": list(dashboard_data["activity_log"])[:50],
            "stats": dashboard_data["stats"]
        }, default=str)

<<<<<<< HEAD
# =============================================
# HTML DASHBOARD
# =============================================
DASHBOARD_HTML = r'''<!DOCTYPE html>
=======

DASHBOARD_HTML = r"""<!DOCTYPE html>
>>>>>>> 8296d15 (update)
<html lang="id" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<<<<<<< HEAD
<title>MQTT Study Room - Dashboard Monitoring</title>
=======
<title>MQTT Study Room Dashboard</title>
>>>>>>> 8296d15 (update)
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.4/socket.io.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
<<<<<<< HEAD
html{font-size:15px}

/* ── LIGHT THEME (default) ── */
:root,[data-theme="light"]{
--bg-base:#f0f4f8;--bg-card:#ffffff;--bg-card2:#e8f1fc;
--border:rgba(147,197,253,0.5);--accent:#2563eb;--accent2:#0284c7;
--accent-soft:#dbeafe;
--green:#16a34a;--green-bg:#dcfce7;
--yellow:#d97706;--yellow-bg:#fef3c7;
--red:#dc2626;--red-bg:#fee2e2;
--purple:#7c3aed;--purple-bg:#ede9fe;
--text:#0f172a;--text2:#475569;--text3:#94a3b8;
--topbar:rgba(255,255,255,0.95);
--shadow:0 4px 24px rgba(59,130,246,0.08);
--font:'Inter',sans-serif;
}

/* ── DARK THEME ── */
[data-theme="dark"]{
--bg-base:#0a0f1e;--bg-card:#131c35;--bg-card2:#1a2540;
--border:rgba(96,165,250,0.15);--accent:#3b82f6;--accent2:#06b6d4;
--accent-soft:rgba(59,130,246,0.18);
--green:#10b981;--green-bg:rgba(16,185,129,0.15);
--yellow:#f59e0b;--yellow-bg:rgba(245,158,11,0.15);
--red:#ef4444;--red-bg:rgba(239,68,68,0.15);
--purple:#8b5cf6;--purple-bg:rgba(139,92,246,0.15);
--text:#f1f5f9;--text2:#94a3b8;--text3:#475569;
--topbar:rgba(10,15,30,0.95);
--shadow:0 8px 32px rgba(0,0,0,0.45);
}

body{font-family:var(--font);background:var(--bg-base);color:var(--text);min-height:100vh;transition:background .35s,color .35s}

.header{background:var(--topbar);border-bottom:1px solid var(--border);padding:.9rem 1.5rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:50;backdrop-filter:blur(20px);box-shadow:var(--shadow)}
.header-left{display:flex;align-items:center;gap:.75rem}
.header-logo{width:38px;height:38px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.3rem;flex-shrink:0;box-shadow:0 4px 12px rgba(37,99,235,0.3)}
.header h1{font-size:1.1rem;font-weight:800;background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.header .sub{font-size:.72rem;color:var(--text3);margin-top:.1rem}
.header-right{display:flex;align-items:center;gap:.6rem}
.theme-btn{background:var(--accent-soft);border:1.5px solid var(--border);border-radius:50%;width:38px;height:38px;font-size:1rem;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .22s;color:var(--text)}
.theme-btn:hover{transform:rotate(20deg) scale(1.1);border-color:var(--accent)}
.back-btn{display:inline-flex;align-items:center;gap:.4rem;padding:.32rem .85rem;background:var(--accent-soft);border:1.5px solid var(--border);border-radius:999px;font-size:.76rem;font-weight:700;color:var(--accent);text-decoration:none;transition:all .22s;white-space:nowrap}
.back-btn:hover{background:var(--accent);color:#fff;border-color:var(--accent);transform:translateX(-2px)}
.mqtt-badge{display:inline-flex;align-items:center;gap:.4rem;padding:.28rem .7rem;border-radius:999px;font-size:.72rem;font-weight:700;background:var(--green-bg);color:var(--green);border:1.5px solid rgba(22,163,74,.3)}
[data-theme="dark"] .mqtt-badge{border-color:rgba(16,185,129,.3)}
.mqtt-badge .dot{width:7px;height:7px;border-radius:50%;background:currentColor;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.container{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;padding:1.25rem 1.5rem;max-width:1600px;margin:0 auto}
.full-w{grid-column:1/-1}
.span-2{grid-column:span 2}
.card{background:var(--bg-card);border:1.5px solid var(--border);border-radius:14px;padding:1.1rem;box-shadow:var(--shadow);transition:transform .2s,box-shadow .2s}
.card:hover{transform:translateY(-2px);box-shadow:0 8px 28px rgba(37,99,235,0.12)}
.card-title{display:flex;align-items:center;gap:.5rem;font-size:.8rem;font-weight:800;color:var(--accent);margin-bottom:.85rem;text-transform:uppercase;letter-spacing:.06em}
.card-title .icon{width:28px;height:28px;background:var(--accent-soft);border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:.95rem;flex-shrink:0}

/* Stats */
.stats-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:.7rem}
.stat-box{background:var(--bg-card);border:1.5px solid var(--border);border-radius:12px;padding:.85rem;text-align:center;transition:all .25s;box-shadow:var(--shadow)}
.stat-box:hover{border-color:var(--accent);box-shadow:0 0 20px rgba(37,99,235,.15);transform:translateY(-2px)}
.stat-num{font-size:1.6rem;font-weight:800;color:var(--accent);line-height:1.2}
.stat-num.green{color:var(--green)}.stat-num.yellow{color:var(--yellow)}.stat-num.red{color:var(--red)}.stat-num.purple{color:var(--purple)}
.stat-label{font-size:.62rem;color:var(--text3);text-transform:uppercase;letter-spacing:.05em;margin-top:.2rem;font-weight:600}

/* Room Sensor Card */
.room-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:.9rem}
.room-card{background:var(--bg-card2);border:1.5px solid var(--border);border-radius:14px;padding:1.1rem;position:relative;overflow:hidden;transition:transform .2s,box-shadow .2s}
.room-card:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(37,99,235,.15)}
.room-card::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,var(--accent),var(--accent2))}
.room-card-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:.85rem}
.room-id-badge{font-size:.72rem;font-weight:800;color:#fff;background:linear-gradient(135deg,var(--accent),var(--accent2));padding:.22rem .65rem;border-radius:999px;letter-spacing:.06em}
.room-update{font-size:.62rem;color:var(--text3)}
.sensor-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem}
.sensor-item{background:var(--bg-card);border:1.5px solid var(--border);border-radius:10px;padding:.65rem .5rem;text-align:center;transition:border-color .2s}
.sensor-item:hover{border-color:var(--accent)}
.sensor-icon{font-size:1.1rem;margin-bottom:.2rem}
.sensor-val{font-size:1.4rem;font-weight:800;line-height:1.1}
.sensor-type{font-size:.62rem;color:var(--text3);margin-top:.15rem;font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.sensor-qos-row{display:flex;gap:.3rem;margin-top:.65rem;flex-wrap:wrap}
.sensor-qos-badge{font-size:.58rem;padding:.1rem .35rem;border-radius:4px;font-weight:700;background:var(--accent-soft);color:var(--accent);border:1px solid var(--border)}

/* Publisher Status */
.pub-list{display:flex;flex-direction:column;gap:.45rem}
.pub-item{display:flex;align-items:center;gap:.6rem;padding:.55rem .8rem;background:var(--bg-card2);border-radius:8px;border:1.5px solid var(--border);transition:border-color .2s}
.pub-item:hover{border-color:var(--accent)}
.pub-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.pub-dot.online{background:var(--green);box-shadow:0 0 8px rgba(22,163,74,.5)}
.pub-dot.offline{background:var(--red);box-shadow:0 0 8px rgba(220,38,38,.5)}
.pub-name{font-size:.82rem;font-weight:600;color:var(--text)}
.pub-type{font-size:.7rem;color:var(--text3);margin-left:auto}

/* Event log */
.event-list{max-height:320px;overflow-y:auto;display:flex;flex-direction:column;gap:.3rem}
.event-list::-webkit-scrollbar{width:4px}
.event-list::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
.event-item{padding:.48rem .7rem;background:var(--bg-card2);border-radius:7px;border-left:3px solid var(--accent);font-size:.77rem;animation:slideIn .3s ease;color:var(--text);transition:background .2s}
.event-item:hover{background:var(--accent-soft)}
.event-item.security{border-left-color:var(--red)}
.event-item.admin{border-left-color:var(--purple)}
.event-item.sensor{border-left-color:var(--green)}
.event-item.lwt{border-left-color:var(--yellow)}
.event-time{font-size:.63rem;color:var(--text3);float:right;font-weight:500}
.event-topic{font-size:.67rem;color:var(--text3);margin-top:.2rem;word-break:break-all}
.event-badge{display:inline-block;font-size:.6rem;padding:.1rem .35rem;border-radius:4px;font-weight:700;margin-left:.3rem}
.badge-qos0{background:var(--green-bg);color:var(--green)}
.badge-qos1{background:var(--yellow-bg);color:var(--yellow)}
.badge-qos2{background:var(--red-bg);color:var(--red)}
.badge-retain{background:var(--purple-bg);color:var(--purple)}
@keyframes slideIn{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:translateX(0)}}

/* Feature checklist */
.feature-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:.4rem}
.feature-item{display:flex;align-items:center;gap:.4rem;padding:.42rem .65rem;background:var(--bg-card2);border-radius:7px;font-size:.75rem;border:1.5px solid var(--border);color:var(--text2);transition:border-color .2s,background .2s}
.feature-item:hover{border-color:var(--accent);background:var(--accent-soft)}
.feature-check{color:var(--green);font-weight:800}

/* Responsive */
@media(max-width:1024px){.container{grid-template-columns:1fr 1fr}.span-2{grid-column:span 1}}
@media(max-width:768px){.container{grid-template-columns:1fr}.stats-grid{grid-template-columns:repeat(3,1fr)}.sensor-grid{grid-template-columns:repeat(2,1fr)}}
=======
:root,[data-theme="light"]{--bg-base:#f0f4f8;--bg-card:#fff;--bg-card2:#e8f1fc;--border:rgba(147,197,253,0.5);--accent:#2563eb;--accent2:#0284c7;--accent-soft:#dbeafe;--green:#16a34a;--green-bg:#dcfce7;--yellow:#d97706;--yellow-bg:#fef3c7;--red:#dc2626;--red-bg:#fee2e2;--purple:#7c3aed;--purple-bg:#ede9fe;--text:#0f172a;--text2:#475569;--text3:#94a3b8;--topbar:rgba(255,255,255,0.95);--shadow:0 4px 24px rgba(59,130,246,0.08);--font:'Inter',sans-serif;--modal-bg:rgba(15,23,42,0.65)}
[data-theme="dark"]{--bg-base:#0a0f1e;--bg-card:#131c35;--bg-card2:#1a2540;--border:rgba(96,165,250,0.15);--accent:#3b82f6;--accent2:#06b6d4;--accent-soft:rgba(59,130,246,0.18);--green:#10b981;--green-bg:rgba(16,185,129,0.15);--yellow:#f59e0b;--yellow-bg:rgba(245,158,11,0.15);--red:#ef4444;--red-bg:rgba(239,68,68,0.15);--purple:#8b5cf6;--purple-bg:rgba(139,92,246,0.15);--text:#f1f5f9;--text2:#94a3b8;--text3:#475569;--topbar:rgba(10,15,30,0.95);--shadow:0 8px 32px rgba(0,0,0,0.45);--modal-bg:rgba(0,0,0,0.78)}
body{font-family:var(--font);background:var(--bg-base);color:var(--text);min-height:100vh;transition:background .35s,color .35s}
.header{background:var(--topbar);border-bottom:1px solid var(--border);padding:.9rem 1.5rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:50;backdrop-filter:blur(20px);box-shadow:var(--shadow)}
.header-left{display:flex;align-items:center;gap:.75rem}
.logo{width:38px;height:38px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.3rem;flex-shrink:0}
.header h1{font-size:1.1rem;font-weight:800;background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.sub{font-size:.72rem;color:var(--text3);margin-top:.1rem}
.header-right{display:flex;align-items:center;gap:.6rem}
.theme-btn{background:var(--accent-soft);border:1.5px solid var(--border);border-radius:50%;width:38px;height:38px;font-size:1rem;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .22s;color:var(--text)}
.theme-btn:hover{transform:rotate(20deg) scale(1.1)}
.mqtt-badge{display:inline-flex;align-items:center;gap:.4rem;padding:.28rem .7rem;border-radius:999px;font-size:.72rem;font-weight:700;background:var(--green-bg);color:var(--green);border:1.5px solid rgba(22,163,74,.3)}
.dot{width:7px;height:7px;border-radius:50%;background:currentColor;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.container{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;padding:1.25rem 1.5rem;max-width:1600px;margin:0 auto}
.full-w{grid-column:1/-1}.span-2{grid-column:span 2}
.card{background:var(--bg-card);border:1.5px solid var(--border);border-radius:14px;padding:1.1rem;box-shadow:var(--shadow)}
.card-title{display:flex;align-items:center;gap:.5rem;font-size:.8rem;font-weight:800;color:var(--accent);margin-bottom:.85rem;text-transform:uppercase;letter-spacing:.06em}
.card-icon{width:28px;height:28px;background:var(--accent-soft);border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:.95rem;flex-shrink:0}
.stats-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:.7rem}
.stat-box{background:var(--bg-card);border:1.5px solid var(--border);border-radius:12px;padding:.85rem;text-align:center;transition:all .25s;box-shadow:var(--shadow)}
.stat-box:hover{border-color:var(--accent);transform:translateY(-2px)}
.stat-num{font-size:1.6rem;font-weight:800;color:var(--accent);line-height:1.2}
.stat-num.g{color:var(--green)}.stat-num.y{color:var(--yellow)}.stat-num.r{color:var(--red)}.stat-num.p{color:var(--purple)}
.stat-label{font-size:.62rem;color:var(--text3);text-transform:uppercase;letter-spacing:.05em;margin-top:.2rem;font-weight:600}
.room-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(265px,1fr));gap:.9rem}
.room-card{background:var(--bg-card2);border:1.5px solid var(--border);border-radius:14px;padding:1.1rem;position:relative;overflow:hidden;cursor:pointer;transition:transform .2s,box-shadow .2s,border-color .2s}
.room-card:hover{transform:translateY(-4px);box-shadow:0 12px 28px rgba(37,99,235,.2);border-color:var(--accent)}
.room-card::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,var(--accent),var(--accent2))}
.room-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:.85rem}
.room-badge{font-size:.72rem;font-weight:800;color:#fff;background:linear-gradient(135deg,var(--accent),var(--accent2));padding:.22rem .65rem;border-radius:999px}
.room-ts{font-size:.62rem;color:var(--text3)}
.room-hint{font-size:.6rem;color:var(--accent);margin-top:.5rem;text-align:right;opacity:.75}
.sensor-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem}
.sensor-item{background:var(--bg-card);border:1.5px solid var(--border);border-radius:10px;padding:.65rem .5rem;text-align:center}
.sensor-icon{font-size:1.1rem;margin-bottom:.2rem}
.sensor-val{font-size:1.4rem;font-weight:800;line-height:1.1}
.sensor-type{font-size:.62rem;color:var(--text3);margin-top:.15rem;font-weight:600;text-transform:uppercase}
.qos-row{display:flex;gap:.3rem;margin-top:.65rem;flex-wrap:wrap}
.qos-badge{font-size:.58rem;padding:.1rem .35rem;border-radius:4px;font-weight:700;background:var(--accent-soft);color:var(--accent);border:1px solid var(--border)}
.pub-list{display:flex;flex-direction:column;gap:.45rem}
.pub-item{display:flex;align-items:center;gap:.6rem;padding:.55rem .8rem;background:var(--bg-card2);border-radius:8px;border:1.5px solid var(--border)}
.pub-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.pub-dot.on{background:var(--green);box-shadow:0 0 8px rgba(22,163,74,.5)}
.pub-dot.off{background:var(--red)}
.pub-name{font-size:.82rem;font-weight:600}
.pub-type{font-size:.7rem;color:var(--text3);margin-left:auto}
.log-filter{display:flex;gap:.4rem;margin-bottom:.65rem;flex-wrap:wrap}
.fbtn{font-size:.68rem;font-weight:700;padding:.22rem .65rem;border-radius:999px;border:1.5px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;transition:all .2s}
.fbtn:hover,.fbtn.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.event-list{max-height:280px;overflow-y:auto;display:flex;flex-direction:column;gap:.3rem}
.event-list::-webkit-scrollbar{width:4px}
.event-list::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
.ei{padding:.48rem .7rem;background:var(--bg-card2);border-radius:7px;border-left:3px solid var(--accent);font-size:.77rem;animation:slideIn .3s ease;cursor:pointer;transition:background .15s}
.ei:hover{background:var(--accent-soft)}
.ei.sec{border-left-color:var(--red)}.ei.adm{border-left-color:var(--purple)}.ei.sen{border-left-color:var(--green)}.ei.lwt{border-left-color:var(--yellow)}
.ei .dp{display:none;margin-top:.45rem;padding:.45rem .6rem;background:var(--bg-card);border-radius:6px;font-size:.68rem;color:var(--text2);line-height:1.6;border:1px solid var(--border)}
.ei.exp .dp{display:block}
.etime{font-size:.63rem;color:var(--text3);float:right;font-weight:500}
.etopic{font-size:.67rem;color:var(--text3);margin-top:.2rem;word-break:break-all}
.eb{display:inline-block;font-size:.6rem;padding:.1rem .35rem;border-radius:4px;font-weight:700;margin-left:.3rem}
.eq0{background:var(--green-bg);color:var(--green)}.eq1{background:var(--yellow-bg);color:var(--yellow)}.eq2{background:var(--red-bg);color:var(--red)}.ert{background:var(--purple-bg);color:var(--purple)}
@keyframes slideIn{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:translateX(0)}}
.feature-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:.5rem}
.fi{padding:.55rem .8rem;background:var(--bg-card2);border-radius:10px;border:1.5px solid var(--border);cursor:pointer;transition:all .2s}
.fi:hover,.fi.active{border-color:var(--accent);background:var(--accent-soft)}
.fi-row{display:flex;align-items:center;gap:.45rem;font-size:.78rem;color:var(--text)}
.fi-check{color:var(--green);font-weight:800;font-size:.85rem}
.fi-name{font-weight:600;flex:1}
.fi-arr{font-size:.7rem;color:var(--text3);transition:transform .2s}
.fi.active .fi-arr{transform:rotate(90deg)}
.fi-desc{display:none;margin-top:.5rem;font-size:.72rem;color:var(--text2);line-height:1.65;padding-top:.45rem;border-top:1px solid var(--border)}
.fi.active .fi-desc{display:block}
.modal-ov{position:fixed;inset:0;background:var(--modal-bg);z-index:200;display:flex;align-items:center;justify-content:center;padding:1rem;backdrop-filter:blur(4px);opacity:0;pointer-events:none;transition:opacity .25s}
.modal-ov.open{opacity:1;pointer-events:all}
.modal{background:var(--bg-card);border:1.5px solid var(--border);border-radius:18px;width:100%;max-width:560px;max-height:90vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,.35);transform:scale(.95);transition:transform .25s}
.modal-ov.open .modal{transform:scale(1)}
.mh{display:flex;align-items:center;justify-content:space-between;padding:1.1rem 1.25rem;border-bottom:1px solid var(--border)}
.mt{font-size:1rem;font-weight:800;color:var(--accent)}
.mc{width:32px;height:32px;border-radius:50%;border:1.5px solid var(--border);background:transparent;cursor:pointer;font-size:1rem;display:flex;align-items:center;justify-content:center;color:var(--text3);transition:all .2s}
.mc:hover{background:var(--red-bg);color:var(--red);border-color:var(--red)}
.mb{padding:1.1rem 1.25rem}
.msc{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;margin-bottom:1.1rem}
.msc-card{background:var(--bg-card2);border:1.5px solid var(--border);border-radius:12px;padding:.85rem;text-align:center}
.msc-val{font-size:2rem;font-weight:800;line-height:1}
.msc-lbl{font-size:.68rem;color:var(--text3);text-transform:uppercase;font-weight:600;margin-top:.25rem}
.msc-qos{font-size:.6rem;margin-top:.4rem;padding:.1rem .4rem;border-radius:4px;background:var(--accent-soft);color:var(--accent);display:inline-block;font-weight:700}
.cw{margin-bottom:.85rem;background:var(--bg-card2);border-radius:10px;padding:.65rem;border:1.5px solid var(--border)}
.clbl{font-size:.72rem;font-weight:700;color:var(--text2);margin-bottom:.45rem}
.spark{width:100%;height:56px;display:block}
.mir{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.6rem}
.mib{font-size:.68rem;padding:.2rem .55rem;border-radius:6px;font-weight:600}
@media(max-width:1024px){.container{grid-template-columns:1fr 1fr}.span-2{grid-column:span 1}}
@media(max-width:768px){.container{grid-template-columns:1fr}.stats-grid{grid-template-columns:repeat(3,1fr)}}
>>>>>>> 8296d15 (update)
</style>
</head>
<body>
<div class="header">
  <div class="header-left">
<<<<<<< HEAD
    <div class="header-logo">🏫</div>
    <div>
      <h1>MQTT Study Room — Dashboard Monitoring</h1>
      <div class="sub">Real-time monitoring sistem ruang belajar kampus ITS</div>
    </div>
  </div>
  <div class="header-right">
    <div class="mqtt-badge"><span class="dot"></span><span id="conn-label">Terhubung ke MQTT Broker</span></div>
    <a href="#" onclick="window.open('http://127.0.0.1:5500/grpc-study-room/web/index.html','_blank');return false;" class="back-btn" title="Kembali ke gRPC Dashboard" id="btn-back-grpc">
      <span>←</span> gRPC Dashboard
    </a>
    <button class="theme-btn" id="theme-toggle" title="Ganti Tema" aria-label="Toggle tema">🌙</button>
  </div>
</div>

<div class="container">
  <!-- Stats -->
  <div class="card full-w">
    <div class="card-title"><span class="icon">📊</span> Statistik MQTT Real-Time</div>
    <div class="stats-grid">
      <div class="stat-box"><div class="stat-num" id="s-total">0</div><div class="stat-label">Total Pesan</div></div>
      <div class="stat-box"><div class="stat-num green" id="s-qos0">0</div><div class="stat-label">QoS 0</div></div>
      <div class="stat-box"><div class="stat-num yellow" id="s-qos1">0</div><div class="stat-label">QoS 1</div></div>
      <div class="stat-box"><div class="stat-num red" id="s-qos2">0</div><div class="stat-label">QoS 2</div></div>
      <div class="stat-box"><div class="stat-num purple" id="s-retain">0</div><div class="stat-label">Retained</div></div>
      <div class="stat-box"><div class="stat-num" id="s-publishers">0</div><div class="stat-label">Publishers</div></div>
    </div>
  </div>

  <!-- Sensors per Room -->
  <div class="card span-2">
    <div class="card-title"><span class="icon">🌡️</span> Data Sensor per Ruangan</div>
    <div class="room-grid" id="sensor-grid"><div style="color:var(--text3);font-size:.85rem;padding:.5rem">⏳ Menunggu data sensor dari publisher...</div></div>
  </div>

  <!-- Publisher Status -->
  <div class="card">
    <div class="card-title"><span class="icon">📡</span> Status Publisher (LWT)</div>
    <div class="pub-list" id="pub-list">
      <div style="color:var(--text3);font-size:.8rem">Menunggu publisher...</div>
    </div>
  </div>

  <!-- Security Events -->
  <div class="card">
    <div class="card-title"><span class="icon">🔒</span> Event Keamanan</div>
    <div class="event-list" id="security-list">
      <div style="color:var(--text3);font-size:.8rem">Menunggu event keamanan...</div>
    </div>
  </div>

  <!-- Admin Broadcast -->
  <div class="card">
    <div class="card-title"><span class="icon">📢</span> Broadcast Admin</div>
    <div class="event-list" id="admin-list">
      <div style="color:var(--text3);font-size:.8rem">Menunggu broadcast...</div>
    </div>
  </div>

  <!-- Activity Log -->
  <div class="card">
    <div class="card-title"><span class="icon">📝</span> Activity Log</div>
    <div class="event-list" id="activity-list">
      <div style="color:var(--text3);font-size:.8rem">Menunggu aktivitas...</div>
    </div>
  </div>

  <!-- Feature Checklist -->
  <div class="card full-w">
    <div class="card-title"><span class="icon">✅</span> 10 Fitur MQTT yang Diimplementasikan</div>
    <div class="feature-grid">
      <div class="feature-item"><span class="feature-check">✓</span> Fitur 1: Pub/Sub & QoS (0, 1, 2)</div>
      <div class="feature-item"><span class="feature-check">✓</span> Fitur 2: Topic Wildcards (+ & #)</div>
      <div class="feature-item"><span class="feature-check">✓</span> Fitur 3: Topic Alias (efisiensi)</div>
      <div class="feature-item"><span class="feature-check">✓</span> Fitur 4: User Properties (metadata)</div>
      <div class="feature-item"><span class="feature-check">✓</span> Fitur 5: Retain Message</div>
      <div class="feature-item"><span class="feature-check">✓</span> Fitur 6: Message Expiry Interval</div>
      <div class="feature-item"><span class="feature-check">✓</span> Fitur 7: Last Will & Testament</div>
      <div class="feature-item"><span class="feature-check">✓</span> Fitur 8: Request-Response Pattern</div>
      <div class="feature-item"><span class="feature-check">✓</span> Fitur 9: Shared Subscriptions</div>
      <div class="feature-item"><span class="feature-check">✓</span> Fitur 10: Flow Control (Backpressure)</div>
    </div>
=======
    <div class="logo">🏫</div>
    <div><h1>MQTT Study Room — Dashboard Monitoring</h1><div class="sub">Real-time monitoring sistem ruang belajar kampus ITS</div></div>
  </div>
  <div class="header-right">
    <div class="mqtt-badge"><span class="dot"></span><span>MQTT Terhubung</span></div>
    <button class="theme-btn" id="theme-toggle">🌙</button>
  </div>
</div>
<div class="container">
  <div class="card full-w">
    <div class="card-title"><span class="card-icon">📊</span>Statistik MQTT Real-Time</div>
    <div class="stats-grid">
      <div class="stat-box"><div class="stat-num" id="s-total">0</div><div class="stat-label">Total Pesan</div></div>
      <div class="stat-box"><div class="stat-num g" id="s-qos0">0</div><div class="stat-label">QoS 0</div></div>
      <div class="stat-box"><div class="stat-num y" id="s-qos1">0</div><div class="stat-label">QoS 1</div></div>
      <div class="stat-box"><div class="stat-num r" id="s-qos2">0</div><div class="stat-label">QoS 2</div></div>
      <div class="stat-box"><div class="stat-num p" id="s-retain">0</div><div class="stat-label">Retained</div></div>
      <div class="stat-box"><div class="stat-num" id="s-pub">0</div><div class="stat-label">Publishers</div></div>
    </div>
  </div>
  <div class="card span-2">
    <div class="card-title"><span class="card-icon">🌡️</span>Data Sensor per Ruangan <span style="font-size:.65rem;font-weight:400;color:var(--text3);margin-left:.3rem">(klik untuk detail & grafik)</span></div>
    <div class="room-grid" id="sensor-grid"><div style="color:var(--text3);font-size:.85rem">⏳ Menunggu data sensor...</div></div>
  </div>
  <div class="card">
    <div class="card-title"><span class="card-icon">📡</span>Status Publisher (LWT)</div>
    <div class="pub-list" id="pub-list"><div style="color:var(--text3);font-size:.8rem">Menunggu publisher...</div></div>
  </div>
  <div class="card">
    <div class="card-title"><span class="card-icon">🔒</span>Event Keamanan <span style="font-size:.65rem;font-weight:400;color:var(--text3);margin-left:.3rem">(klik untuk detail)</span></div>
    <div class="event-list" id="security-list"><div style="color:var(--text3);font-size:.8rem">Menunggu event keamanan...</div></div>
  </div>
  <div class="card">
    <div class="card-title"><span class="card-icon">📢</span>Broadcast Admin</div>
    <div class="event-list" id="admin-list"><div style="color:var(--text3);font-size:.8rem">Menunggu broadcast...</div></div>
  </div>
  <div class="card">
    <div class="card-title"><span class="card-icon">📝</span>Activity Log</div>
    <div class="log-filter">
      <button class="fbtn active" onclick="setFilter('all',this)">Semua</button>
      <button class="fbtn" onclick="setFilter('sen',this)">Sensor</button>
      <button class="fbtn" onclick="setFilter('sec',this)">Keamanan</button>
      <button class="fbtn" onclick="setFilter('adm',this)">Admin</button>
      <button class="fbtn" onclick="setFilter('lwt',this)">LWT</button>
    </div>
    <div class="event-list" id="activity-list"><div style="color:var(--text3);font-size:.8rem">Menunggu aktivitas...</div></div>
  </div>
  <div class="card full-w">
    <div class="card-title"><span class="card-icon">✅</span>10 Fitur MQTT — Klik untuk penjelasan</div>
    <div class="feature-grid" id="feature-grid"></div>
  </div>
</div>

<div class="modal-ov" id="room-modal" onclick="closeOut(event)">
  <div class="modal">
    <div class="mh"><div class="mt" id="modal-title">Detail Ruangan</div><button class="mc" onclick="closeModal()">✕</button></div>
    <div class="mb" id="modal-body"></div>
>>>>>>> 8296d15 (update)
  </div>
</div>

<script>
<<<<<<< HEAD
const socket = io();
const sensorData = {};
let firstSec = true, firstAdmin = true, firstAct = true;

// ── THEME TOGGLE ──
(function(){
  const html = document.documentElement;
  const btn = document.getElementById('theme-toggle');
  const saved = localStorage.getItem('mqtt-theme') || 'light';
  html.setAttribute('data-theme', saved);
  btn.textContent = saved === 'dark' ? '☀️' : '🌙';
  btn.addEventListener('click', () => {
    const cur = html.getAttribute('data-theme');
    const next = cur === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    btn.textContent = next === 'dark' ? '☀️' : '🌙';
    localStorage.setItem('mqtt-theme', next);
  });
})();

function qosBadge(q) {
  return `<span class="event-badge badge-qos${q}">QoS ${q}</span>`;
}
function retainBadge(r) {
  return r ? '<span class="event-badge badge-retain">RETAIN</span>' : '';
}

socket.on('stats_update', d => {
  document.getElementById('s-total').textContent = d.total || 0;
  document.getElementById('s-qos0').textContent = d.qos0 || 0;
  document.getElementById('s-qos1').textContent = d.qos1 || 0;
  document.getElementById('s-qos2').textContent = d.qos2 || 0;
  document.getElementById('s-retain').textContent = d.retained || 0;
});

socket.on('sensor_update', d => {
  if (!sensorData[d.room_id]) sensorData[d.room_id] = {};
  sensorData[d.room_id][d.sensor] = d;
  renderSensors();
});

function renderSensors() {
  const grid = document.getElementById('sensor-grid');
  const icons = {suhu:'🌡️', kelembapan:'💧', cahaya:'☀️'};
  const colors = {suhu:'#ef4444', kelembapan:'#3b82f6', cahaya:'#f59e0b'};
  const order = ['suhu','kelembapan','cahaya'];
  const rooms = Object.keys(sensorData).sort();
  if (!rooms.length) {
    grid.innerHTML = '<div style="color:var(--text3);font-size:.85rem;padding:.5rem">⏳ Menunggu data sensor dari publisher...</div>';
    return;
  }
  let html = '';
  for (const roomId of rooms) {
    const sensors = sensorData[roomId];
    const lastTs = Object.values(sensors)[0]?.timestamp || '';
    let sensorHtml = '';
    let qosBadges = new Set();
    let hasRetain = false;
    for (const sType of order) {
      const s = sensors[sType];
      if (!s) {
        sensorHtml += `<div class="sensor-item"><div class="sensor-icon">${icons[sType]||'📡'}</div><div class="sensor-val" style="color:var(--text3)">–</div><div class="sensor-type">${sType}</div></div>`;
      } else {
        qosBadges.add(s.qos);
        if (s.retain) hasRetain = true;
        sensorHtml += `<div class="sensor-item"><div class="sensor-icon">${icons[sType]||'📡'}</div><div class="sensor-val" style="color:${colors[sType]}">${s.value}<small style="font-size:.55em">${s.unit}</small></div><div class="sensor-type">${sType}</div></div>`;
      }
    }
    const qosHtml = [...qosBadges].map(q=>`<span class="sensor-qos-badge">QoS ${q}</span>`).join('');
    const retainHtml = hasRetain ? '<span class="sensor-qos-badge" style="background:var(--purple-bg);color:var(--purple)">📌 RETAIN</span>' : '';
    html += `<div class="room-card"><div class="room-card-header"><span class="room-id-badge">${roomId}</span><span class="room-update">🕐 ${lastTs.split(' ')[1]||''}</span></div><div class="sensor-row">${sensorHtml}</div><div class="sensor-qos-row">${qosHtml}${retainHtml}</div></div>`;
  }
  grid.innerHTML = html;
}

socket.on('status_update', d => {
  renderPubStatus(d);
});

const pubStatuses = {};
function renderPubStatus(d) {
  if (d.client_id) pubStatuses[d.client_id] = d;
  const el = document.getElementById('pub-list');
  document.getElementById('s-publishers').textContent = Object.keys(pubStatuses).length;
  let html = '';
  for (const [id, s] of Object.entries(pubStatuses)) {
    const on = s.status === 'ONLINE';
    html += `<div class="pub-item">
      <div class="pub-dot ${on?'online':'offline'}"></div>
      <div class="pub-name">${id}</div>
      <div class="pub-type">${s.type||'?'} · ${s.status}</div>
    </div>`;
  }
  el.innerHTML = html || '<div style="color:var(--text3);font-size:.8rem">Menunggu publisher...</div>';
}

socket.on('security_event', d => {
  if (firstSec) { document.getElementById('security-list').innerHTML = ''; firstSec = false; }
  const el = document.getElementById('security-list');
  const ev = d.payload?.event || d.payload?.system || 'STATUS';
  const room = d.payload?.room_id || '';
  const detail = d.payload?.detail || '';
  const isAlarm = String(ev).includes('ALARM');
  el.insertAdjacentHTML('afterbegin',
    `<div class="event-item security" style="${isAlarm?'border-left-color:#ef4444;background:rgba(239,68,68,.08)':''}">
      <span class="event-time">${d.timestamp}</span>
      ${isAlarm?'🚨':'🔒'} <b>${ev}</b> ${room} ${qosBadge(d.qos)} ${retainBadge(d.retain)}
      <div class="event-topic">${detail || d.topic}</div>
    </div>`);
  while (el.children.length > 30) el.removeChild(el.lastChild);
});

socket.on('admin_broadcast', d => {
  if (firstAdmin) { document.getElementById('admin-list').innerHTML = ''; firstAdmin = false; }
  const el = document.getElementById('admin-list');
  const title = d.payload?.title || '';
  const msg = d.payload?.message || '';
  const pri = d.payload?.priority || 'NORMAL';
  el.insertAdjacentHTML('afterbegin',
    `<div class="event-item admin" style="${pri==='HIGH'?'border-left-color:#ef4444;background:rgba(139,92,246,.08)':''}">
      <span class="event-time">${d.timestamp}</span>
      ${pri==='HIGH'?'🚨':'📢'} <b>${title}</b> ${qosBadge(d.qos)} ${retainBadge(d.retain)}
      <div class="event-topic">${msg}</div>
    </div>`);
  while (el.children.length > 15) el.removeChild(el.lastChild);
});

socket.on('activity', d => {
  if (firstAct) { document.getElementById('activity-list').innerHTML = ''; firstAct = false; }
  const el = document.getElementById('activity-list');
  let cls = 'sensor';
  if (d.topic?.includes('security')) cls = 'security';
  else if (d.topic?.includes('admin')) cls = 'admin';
  else if (d.topic?.includes('status')) cls = 'lwt';
  el.insertAdjacentHTML('afterbegin',
    `<div class="event-item ${cls}">
      <span class="event-time">${d.timestamp}</span>
      ${qosBadge(d.qos)} ${retainBadge(d.retain)}
      <div class="event-topic">${d.topic}</div>
    </div>`);
  while (el.children.length > 40) el.removeChild(el.lastChild);
});

// Load initial data dari /api/data
fetch('/api/data').then(r=>r.json()).then(d=>{
  // Stats
  if(d.stats){
    document.getElementById('s-total').textContent=d.stats.total||0;
    document.getElementById('s-qos0').textContent=d.stats.qos0||0;
    document.getElementById('s-qos1').textContent=d.stats.qos1||0;
    document.getElementById('s-qos2').textContent=d.stats.qos2||0;
    document.getElementById('s-retain').textContent=d.stats.retained||0;
  }
  // Publisher status
  if(d.online_status) Object.entries(d.online_status).forEach(([k,v])=>renderPubStatus({client_id:k,...v}));
  // Sensor data
  if(d.sensors) {
    Object.entries(d.sensors).forEach(([roomId, sensors])=>{
      Object.entries(sensors).forEach(([sType, info])=>{
        if(!sensorData[roomId]) sensorData[roomId]={};
        sensorData[roomId][sType] = {room_id:roomId, sensor:sType, value:info.value, unit:info.unit, qos:info.qos||0, retain:info.retain||false, timestamp:info.timestamp||''};
      });
    });
    renderSensors();
  }
  // Security events
  if(d.security && d.security.length){
    const el=document.getElementById('security-list');
    el.innerHTML='';
    firstSec=false;
    d.security.slice(0,20).reverse().forEach(ev=>{
      const evType=ev.payload?.event||ev.payload?.system||'STATUS';
      const room=ev.payload?.room_id||'';
      const detail=ev.payload?.detail||'';
      const isAlarm=String(evType).includes('ALARM');
      el.insertAdjacentHTML('afterbegin',`<div class="event-item security" style="${isAlarm?'border-left-color:#ef4444;background:rgba(239,68,68,.08)':''}"><span class="event-time">${ev.timestamp}</span> ${isAlarm?'🚨':'🔒'} <b>${evType}</b> ${room} ${qosBadge(ev.qos)} ${retainBadge(ev.retain)}<div class="event-topic">${detail||ev.topic}</div></div>`);
    });
  }
  // Admin broadcasts
  if(d.broadcasts && d.broadcasts.length){
    const el=document.getElementById('admin-list');
    el.innerHTML='';
    firstAdmin=false;
    d.broadcasts.slice(0,10).reverse().forEach(bc=>{
      const title=bc.payload?.title||'';
      const msg=bc.payload?.message||'';
      const pri=bc.payload?.priority||'NORMAL';
      el.insertAdjacentHTML('afterbegin',`<div class="event-item admin" style="${pri==='HIGH'?'border-left-color:#ef4444;background:rgba(139,92,246,.08)':''}"><span class="event-time">${bc.timestamp}</span> ${pri==='HIGH'?'🚨':'📢'} <b>${title}</b> ${qosBadge(bc.qos)} ${retainBadge(bc.retain)}<div class="event-topic">${msg}</div></div>`);
    });
  }
  // Activity log
  if(d.activity && d.activity.length){
    const el=document.getElementById('activity-list');
    el.innerHTML='';
    firstAct=false;
    d.activity.slice(0,30).reverse().forEach(act=>{
      let cls='sensor';
      if(act.topic?.includes('security')) cls='security';
      else if(act.topic?.includes('admin')) cls='admin';
      else if(act.topic?.includes('status')) cls='lwt';
      const payloadStr = act.payload ? (act.payload.event||act.payload.sensor||act.payload.type||'') : '';
      el.insertAdjacentHTML('afterbegin',`<div class="event-item ${cls}"><span class="event-time">${act.timestamp}</span> ${qosBadge(act.qos)} ${retainBadge(act.retain)}<div class="event-topic">${act.topic}</div>${payloadStr?`<div style="font-size:.7rem;color:var(--text2);margin-top:.15rem">${payloadStr}</div>`:''}</div>`);
    });
  }
}).catch(e=>console.warn('Initial load error:', e));
</script>
</body>
</html>'''

# =============================================
# MAIN
# =============================================
def main():
    print("=" * 60)
    print("  MQTT Study Room - Dashboard Monitoring")
    print(f"  Dashboard: http://localhost:{DASHBOARD_PORT}")
    print(f"  MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print("=" * 60)

=======
const socket=io();
const sensorData={},sensorHistory={};
let f1Sec=true,f1Adm=true,f1Act=true,actFilter='all';
const actItems=[];
const pubStatuses={};

const FEATURES=[
  {num:1,name:"Pub/Sub & QoS (0,1,2)",desc:"Inti dari MQTT. Publisher kirim pesan ke topic, subscriber terima lewat broker — tidak perlu saling kenal. QoS 0: kirim sekali, tidak ada garansi. QoS 1: dijamin sampai minimal sekali, bisa duplikat. QoS 2: tepat sekali, ada 4-step handshake. Di proyek: suhu→QoS0, kelembapan→QoS1, cahaya→QoS2."},
  {num:2,name:"Topic Wildcard (+ dan #)",desc:"+ cocok satu level: its/studyroom/+/R001/suhu match gedungA maupun gedungB. # cocok semua sub-level: security/# tangkap semua event keamanan. Dengan wildcard, satu subscriber bisa pantau ratusan topic sekaligus tanpa daftar satu-satu."},
  {num:3,name:"Topic Alias",desc:"Fitur MQTT v5 untuk hemat bandwidth. Nama topic panjang (34 byte) dipetakan ke angka kecil (1 byte) setelah pesan pertama. Pesan berikutnya cukup kirim angkanya. Krusial di IoT dengan koneksi terbatas atau bayar per byte."},
  {num:4,name:"User Properties",desc:"Metadata key-value di header MQTT terpisah dari payload. Contoh: app-version, device-id, unit, location. Broker bisa baca tanpa parse JSON. Berguna untuk tracing — tahu dari device mana pesan itu, versi berapa, tanpa buka isi payload."},
  {num:5,name:"Retain Message",desc:"Broker simpan pesan terakhir per topic. Subscriber baru yang connect langsung dapat data terkini tanpa tunggu publisher kirim lagi. Di proyek ini dipakai untuk status ONLINE/OFFLINE publisher — subscriber kapanpun join langsung tahu status terkini."},
  {num:6,name:"Message Expiry Interval",desc:"Pesan diberi batas waktu hidup (TTL). Kalau subscriber offline dan balik lagi setelah TTL habis, pesan lama tidak akan diterima — sudah dibuang broker. Berguna agar data sensor basi tidak terkirim ke subscriber yang baru online."},
  {num:7,name:"Last Will & Testament (LWT)",desc:"Publisher daftarkan 'surat wasiat' saat connect: pesan yang akan dikirim broker otomatis jika publisher mati mendadak (koneksi putus tanpa DISCONNECT formal). Di proyek: pesan status OFFLINE terkirim ke semua subscriber saat publisher crash."},
  {num:8,name:"Request-Response Pattern",desc:"MQTT v5 mendukung pola req-res mirip HTTP. Publisher sertakan ReplyTo topic di properties. Subscriber yang menerima request menjawab ke topic itu. Di proyek: sensor bisa request data spesifik ke dashboard, dashboard balas ke reply topic-nya."},
  {num:9,name:"Shared Subscription",desc:"Load balancing untuk subscriber. Format: $share/grup/topic. Pesan dibagi merata ke subscriber dalam grup — bukan semua dapat duplikat. Di proyek: subscriber_monitor dan subscriber_logger berbagi beban via shared subscription."},
  {num:10,name:"Flow Control (Backpressure)",desc:"MQTT v5 mendukung Receive Maximum di CONNECT properties. Publisher hanya boleh punya N pesan in-flight sekaligus. Dashboard ini set ReceiveMaximum=50 — broker tidak akan flood lebih dari 50 pesan belum-di-ack ke client ini."}
];

function renderFeatures(){
  document.getElementById('feature-grid').innerHTML=FEATURES.map(f=>`
    <div class="fi" onclick="this.classList.contains('active')?this.classList.remove('active'):document.querySelectorAll('.fi').forEach(x=>x.classList.remove('active'))||this.classList.add('active')">
      <div class="fi-row"><span class="fi-check">✓</span><span class="fi-name">Fitur ${f.num}: ${f.name}</span><span class="fi-arr">▶</span></div>
      <div class="fi-desc">${f.desc}</div>
    </div>`).join('');
}
renderFeatures();

(function(){
  const html=document.documentElement,btn=document.getElementById('theme-toggle');
  const sv=localStorage.getItem('mqtt-theme')||'light';
  html.setAttribute('data-theme',sv);btn.textContent=sv==='dark'?'☀️':'🌙';
  btn.addEventListener('click',()=>{const c=html.getAttribute('data-theme'),n=c==='dark'?'light':'dark';html.setAttribute('data-theme',n);btn.textContent=n==='dark'?'☀️':'🌙';localStorage.setItem('mqtt-theme',n);});
})();

function qb(q){return `<span class="eb eq${q}">QoS ${q}</span>`;}
function rb(r){return r?'<span class="eb ert">RETAIN</span>':'';}

socket.on('stats_update',d=>{
  document.getElementById('s-total').textContent=d.total||0;
  document.getElementById('s-qos0').textContent=d.qos0||0;
  document.getElementById('s-qos1').textContent=d.qos1||0;
  document.getElementById('s-qos2').textContent=d.qos2||0;
  document.getElementById('s-retain').textContent=d.retained||0;
});

socket.on('sensor_update',d=>{
  if(!sensorData[d.room_id])sensorData[d.room_id]={};
  sensorData[d.room_id][d.sensor]=d;
  if(!sensorHistory[d.room_id])sensorHistory[d.room_id]={};
  if(!sensorHistory[d.room_id][d.sensor])sensorHistory[d.room_id][d.sensor]=[];
  sensorHistory[d.room_id][d.sensor].push({value:d.value,timestamp:d.timestamp});
  if(sensorHistory[d.room_id][d.sensor].length>20)sensorHistory[d.room_id][d.sensor].shift();
  renderSensors();
});

function renderSensors(){
  const g=document.getElementById('sensor-grid');
  const ico={suhu:'🌡️',kelembapan:'💧',cahaya:'☀️'};
  const col={suhu:'#ef4444',kelembapan:'#3b82f6',cahaya:'#f59e0b'};
  const ord=['suhu','kelembapan','cahaya'];
  const rooms=Object.keys(sensorData).sort();
  if(!rooms.length){g.innerHTML='<div style="color:var(--text3);font-size:.85rem">⏳ Menunggu data sensor...</div>';return;}
  g.innerHTML=rooms.map(rid=>{
    const s=sensorData[rid];
    const lts=Object.values(s)[0]?.timestamp||'';
    const sh=ord.map(t=>{const si=s[t];if(!si)return`<div class="sensor-item"><div class="sensor-icon">${ico[t]}</div><div class="sensor-val" style="color:var(--text3)">–</div><div class="sensor-type">${t}</div></div>`;return`<div class="sensor-item"><div class="sensor-icon">${ico[t]}</div><div class="sensor-val" style="color:${col[t]}">${si.value}<small style="font-size:.5em">${si.unit}</small></div><div class="sensor-type">${t}</div></div>`;}).join('');
    const qb2=[...new Set(ord.map(t=>s[t]?.qos).filter(q=>q!==undefined))].map(q=>`<span class="qos-badge">QoS ${q}</span>`).join('');
    const hr=ord.some(t=>s[t]?.retain)?'<span class="qos-badge" style="background:var(--purple-bg);color:var(--purple)">📌 RETAIN</span>':'';
    return`<div class="room-card" onclick="openModal('${rid}')"><div class="room-header"><span class="room-badge">${rid}</span><span class="room-ts">🕐 ${lts.split(' ')[1]||''}</span></div><div class="sensor-row">${sh}</div><div class="qos-row">${qb2}${hr}</div><div class="room-hint">🔍 Klik untuk detail & grafik history</div></div>`;
  }).join('');
}

socket.on('status_update',d=>{
  if(d.client_id)pubStatuses[d.client_id]=d;
  const el=document.getElementById('pub-list');
  document.getElementById('s-pub').textContent=Object.keys(pubStatuses).length;
  let h='';
  for(const[id,s]of Object.entries(pubStatuses)){const on=s.status==='ONLINE';h+=`<div class="pub-item"><div class="pub-dot ${on?'on':'off'}"></div><div class="pub-name">${id}</div><div class="pub-type">${s.type||'?'} · ${s.status}</div></div>`;}
  el.innerHTML=h||'<div style="color:var(--text3);font-size:.8rem">Menunggu publisher...</div>';
});

function mkSec(d){
  const ev=d.payload?.event||d.payload?.system||'STATUS';
  const room=d.payload?.room_id||'';
  const detail=d.payload?.detail||'';
  const alarm=String(ev).includes('ALARM');
  const pay=JSON.stringify(d.payload,null,2);
  return`<div class="ei sec${alarm?' style="border-left-color:var(--red)"':''}" onclick="this.classList.toggle('exp')">${rb(d.retain)}${qb(d.qos)}<span class="etime">${d.timestamp}</span> ${alarm?'🚨':'🔒'} <b>${ev}</b> ${room}<div class="etopic">${detail||d.topic}</div><div class="dp"><b>Topic:</b> ${d.topic}<br><pre style="margin-top:.3rem;font-size:.65rem;overflow-x:auto">${pay}</pre></div></div>`;
}

socket.on('security_event',d=>{
  if(f1Sec){document.getElementById('security-list').innerHTML='';f1Sec=false;}
  const el=document.getElementById('security-list');
  el.insertAdjacentHTML('afterbegin',mkSec(d));
  while(el.children.length>30)el.removeChild(el.lastChild);
});

socket.on('admin_broadcast',d=>{
  if(f1Adm){document.getElementById('admin-list').innerHTML='';f1Adm=false;}
  const el=document.getElementById('admin-list');
  const pri=d.payload?.priority||'NORMAL';
  el.insertAdjacentHTML('afterbegin',`<div class="ei adm">${rb(d.retain)}${qb(d.qos)}<span class="etime">${d.timestamp}</span> ${pri==='HIGH'?'🚨':'📢'} <b>${d.payload?.title||''}</b><div class="etopic">${d.payload?.message||''}</div></div>`);
  while(el.children.length>15)el.removeChild(el.lastChild);
});

function setFilter(f,btn){actFilter=f;document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');renderAct();}

function renderAct(){
  const el=document.getElementById('activity-list');
  const fil=actFilter==='all'?actItems:actItems.filter(i=>i.cls===actFilter);
  if(!fil.length){el.innerHTML='<div style="color:var(--text3);font-size:.8rem">Tidak ada data untuk filter ini.</div>';return;}
  el.innerHTML=fil.slice(0,40).map(i=>`<div class="ei ${i.cls}"><span class="etime">${i.ts}</span>${qb(i.qos)}${rb(i.retain)}<div class="etopic">${i.topic}</div></div>`).join('');
}

socket.on('activity',d=>{
  f1Act=false;
  let cls='sen';
  if(d.topic?.includes('security'))cls='sec';
  else if(d.topic?.includes('admin'))cls='adm';
  else if(d.topic?.includes('status'))cls='lwt';
  actItems.unshift({cls,ts:d.timestamp,qos:d.qos,retain:d.retain,topic:d.topic});
  if(actItems.length>100)actItems.pop();
  renderAct();
});

function drawSpark(svgEl,values,color){
  if(!values||values.length<2){svgEl.innerHTML='<text x="50%" y="50%" text-anchor="middle" font-size="11" fill="#94a3b8">Belum ada data</text>';return;}
  const w=480,h=56,pad=6;
  const nums=values.map(v=>parseFloat(v));
  const mn=Math.min(...nums),mx=Math.max(...nums),rng=mx-mn||1;
  const pts=nums.map((v,i)=>{const x=pad+(i/(nums.length-1))*(w-pad*2);const y=pad+(1-(v-mn)/rng)*(h-pad*2);return`${x.toFixed(1)},${y.toFixed(1)}`;}).join(' ');
  const first=pts.split(' ')[0],last=pts.split(' ').at(-1);
  const lastX=last.split(',')[0],lastY=last.split(',')[1];
  svgEl.setAttribute('viewBox',`0 0 ${w} ${h}`);
  const gid='sg'+color.replace('#','');
  svgEl.innerHTML=`<defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${color}" stop-opacity="0.25"/><stop offset="100%" stop-color="${color}" stop-opacity="0.02"/></linearGradient></defs><polygon points="${pts} ${lastX},${h-pad} ${first.split(',')[0]},${h-pad}" fill="url(#${gid})"/><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="${lastX}" cy="${lastY}" r="3.5" fill="${color}"/><text x="${pad}" y="${h-2}" font-size="9" fill="#94a3b8">${mn.toFixed(1)}</text><text x="${w-pad}" y="${pad+8}" font-size="9" fill="#94a3b8" text-anchor="end">${mx.toFixed(1)}</text>`;
}

function openModal(rid){
  const sensors=sensorData[rid]||{};
  const history=sensorHistory[rid]||{};
  const ico={suhu:'🌡️',kelembapan:'💧',cahaya:'☀️'};
  const col={suhu:'#ef4444',kelembapan:'#3b82f6',cahaya:'#f59e0b'};
  const ord=['suhu','kelembapan','cahaya'];
  document.getElementById('modal-title').textContent=`📍 Detail — ${rid}`;
  const cards=ord.map(t=>{const s=sensors[t];if(!s)return`<div class="msc-card"><div class="msc-val" style="color:var(--text3);font-size:1.4rem">–</div><div class="msc-lbl">${ico[t]} ${t}</div></div>`;return`<div class="msc-card"><div class="msc-val" style="color:${col[t]}">${s.value}<small style="font-size:.4em">${s.unit}</small></div><div class="msc-lbl">${ico[t]} ${t}</div><div class="msc-qos">QoS ${s.qos}${s.retain?' · RETAIN':''}</div></div>`;}).join('');
  const charts=ord.map(t=>{const h=history[t]||[];return`<div class="cw"><div class="clbl">${ico[t]} History ${t} <span style="font-size:.62rem;color:var(--text3);font-weight:400">(${h.length} data point)</span></div><svg class="spark" id="sp-${rid}-${t}" viewBox="0 0 480 56" preserveAspectRatio="none"></svg></div>`;}).join('');
  const lts=Object.values(sensors)[0]?.timestamp||'-';
  const info=`<div class="mir"><span class="mib" style="background:var(--accent-soft);color:var(--accent)">📡 MQTT v5</span><span class="mib" style="background:var(--green-bg);color:var(--green)">🕐 Update: ${lts}</span><span class="mib" style="background:var(--purple-bg);color:var(--purple)">📊 ${Object.keys(sensors).length} sensor aktif</span></div>`;
  document.getElementById('modal-body').innerHTML=`<div class="msc">${cards}</div>${charts}${info}`;
  setTimeout(()=>{ord.forEach(t=>{const el=document.getElementById(`sp-${rid}-${t}`);if(el)drawSpark(el,(history[t]||[]).map(h=>h.value),col[t]);});},50);
  document.getElementById('room-modal').classList.add('open');
  document.body.style.overflow='hidden';
}

function closeModal(){document.getElementById('room-modal').classList.remove('open');document.body.style.overflow='';}
function closeOut(e){if(e.target===document.getElementById('room-modal'))closeModal();}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});

fetch('/api/data').then(r=>r.json()).then(d=>{
  if(d.stats){['total','qos0','qos1','qos2'].forEach(k=>document.getElementById('s-'+k).textContent=d.stats[k]||0);document.getElementById('s-retain').textContent=d.stats.retained||0;}
  if(d.online_status)Object.entries(d.online_status).forEach(([k,v])=>{pubStatuses[k]=v;});
  if(d.sensors)Object.entries(d.sensors).forEach(([rid,s])=>Object.entries(s).forEach(([t,i])=>{if(!sensorData[rid])sensorData[rid]={};sensorData[rid][t]={room_id:rid,sensor:t,value:i.value,unit:i.unit,qos:i.qos||0,retain:false,timestamp:i.timestamp||''};}));
  if(d.sensor_history)Object.entries(d.sensor_history).forEach(([rid,s])=>{sensorHistory[rid]={};Object.entries(s).forEach(([t,h])=>{sensorHistory[rid][t]=h;});});
  renderSensors();
  const pl=document.getElementById('pub-list');
  document.getElementById('s-pub').textContent=Object.keys(pubStatuses).length;
  let ph='';for(const[id,s]of Object.entries(pubStatuses)){const on=s.status==='ONLINE';ph+=`<div class="pub-item"><div class="pub-dot ${on?'on':'off'}"></div><div class="pub-name">${id}</div><div class="pub-type">${s.type||'?'} · ${s.status}</div></div>`;}
  pl.innerHTML=ph||'<div style="color:var(--text3);font-size:.8rem">Menunggu publisher...</div>';
  if(d.security&&d.security.length){const el=document.getElementById('security-list');el.innerHTML='';f1Sec=false;d.security.slice(0,20).reverse().forEach(e=>el.insertAdjacentHTML('afterbegin',mkSec(e)));}
  if(d.broadcasts&&d.broadcasts.length){const el=document.getElementById('admin-list');el.innerHTML='';f1Adm=false;d.broadcasts.slice(0,10).reverse().forEach(bc=>{const pri=bc.payload?.priority||'NORMAL';el.insertAdjacentHTML('afterbegin',`<div class="ei adm">${rb(bc.retain)}${qb(bc.qos)}<span class="etime">${bc.timestamp}</span> ${pri==='HIGH'?'🚨':'📢'} <b>${bc.payload?.title||''}</b><div class="etopic">${bc.payload?.message||''}</div></div>`);});}
  if(d.activity&&d.activity.length){f1Act=false;d.activity.slice(0,50).forEach(a=>{let cls='sen';if(a.topic?.includes('security'))cls='sec';else if(a.topic?.includes('admin'))cls='adm';else if(a.topic?.includes('status'))cls='lwt';actItems.push({cls,ts:a.timestamp,qos:a.qos,retain:a.retain,topic:a.topic});});renderAct();}
}).catch(e=>console.warn('Load error:',e));
</script>
</body>
</html>"""


def main():
    print("=" * 60)
    print("  MQTT Study Room - Dashboard (Interactive Enhanced)")
    print(f"  Dashboard: http://localhost:{DASHBOARD_PORT}")
    print(f"  MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print("=" * 60)
>>>>>>> 8296d15 (update)
    mqtt_client = mqtt.Client(
        client_id="dashboard-monitor-web",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        protocol=mqtt.MQTTv5
    )
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
<<<<<<< HEAD

    connect_props = mqtt.Properties(mqtt.PacketTypes.CONNECT)
    connect_props.ReceiveMaximum = 50

    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE, properties=connect_props)
    except Exception as e:
        print(f"[DASHBOARD] ❌ MQTT gagal: {e}")
        return

    mqtt_client.loop_start()
    print(f"[DASHBOARD] ✅ MQTT connected, starting web server...")
=======
    connect_props = mqtt.Properties(mqtt.PacketTypes.CONNECT)
    connect_props.ReceiveMaximum = 50
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE, properties=connect_props)
    except Exception as e:
        print(f"[DASHBOARD] MQTT gagal: {e}")
        return
    mqtt_client.loop_start()
>>>>>>> 8296d15 (update)
    socketio.run(app, host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=False, allow_unsafe_werkzeug=True)

if __name__ == "__main__":
    main()
