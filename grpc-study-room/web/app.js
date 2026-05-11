/**
 * Smart Study Room – WebSocket Client (app.js)
 *
 * Mengelola seluruh komunikasi WebSocket antara browser dan bridge server,
 * serta mengupdate semua komponen UI secara event-driven.
 *
 * Komponen Event-Driven:
 *  1. Connection Status Indicator  – berubah saat WS connect/disconnect
 *  2. Stats Bar                    – update setiap ada perubahan status ruangan
 *  3. Notification Panel           – update setiap notif masuk dari gRPC stream
 *  4. Room Status Grid             – update kartu ruangan secara real-time
 *  5. gRPC Activity Log            – log semua event gRPC & WebSocket
 *
 * Command & Control Bridge:
 *  Browser → WebSocket → Bridge → gRPC Server
 */

// ========================================================
//  KONFIGURASI
// ========================================================
const WS_URL           = 'ws://localhost:8765';
const RECONNECT_DELAY_MS = 3000;
const MAX_LOG_ITEMS    = 150;
const MAX_NOTIF_ITEMS  = 50;

// ========================================================
//  STATE
// ========================================================
let ws             = null;
let wsReady        = false;
let reconnectTimer = null;
let currentUser    = { id: '', name: '' };
let notifCount     = 0;
let wsConnectedAt  = null;

// Penyimpanan lokal data ruangan
const roomsMap = {};   // room_id → room data

// ========================================================
//  DOM HELPERS
// ========================================================
const $ = id => document.getElementById(id);

const loginScreen     = $('login-screen');
const dashScreen      = $('dashboard-screen');
const loginForm       = $('login-form');
const inputUid        = $('input-uid');
const inputUname      = $('input-uname');
const loginError      = $('login-error');
const btnLogin        = $('btn-login');

// Status badges
const wsStatusLogin   = $('ws-status-login');
const wsLabelLogin    = $('ws-label-login');
const wsStatusDash    = $('ws-status-dash');
const wsLabelDash     = $('ws-label-dash');

// Stats bar
const countAvailable  = $('count-available');
const countOccupied   = $('count-occupied');
const countFull       = $('count-full');
const countMaint      = $('count-maint');

// Room grid
const roomGrid        = $('room-grid');

// Panels
const notifList       = $('notif-list');
const activityLog     = $('activity-log');
const notifBadge      = $('notif-badge');
const userDisplayName = $('user-display-name');

// My Bookings
const myBookingsList  = $('my-bookings-list');

// Drawer
const notifDrawer     = $('notif-drawer');
const drawerOverlay   = $('drawer-overlay');
const drawerNotifList = $('drawer-notif-list');

// ========================================================
//  DARK / LIGHT THEME TOGGLE
// ========================================================
function getTheme() {
  return localStorage.getItem('ssr-theme') || 'light';
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('ssr-theme', theme);
  // Update all theme icons
  document.querySelectorAll('.theme-icon').forEach(el => {
    el.textContent = theme === 'dark' ? '🌙' : '☀️';
  });
}

function toggleTheme() {
  const current = getTheme();
  applyTheme(current === 'dark' ? 'light' : 'dark');
}

// Init theme on load
applyTheme(getTheme());

// ========================================================
//  WEBSOCKET MANAGEMENT
// ========================================================

function connectWS() {
  setWsStatus('connecting');
  addLog('WebSocket', 'Membuka koneksi ke bridge server ws://localhost:8765…', 'ws');

  try {
    ws = new WebSocket(WS_URL);
  } catch (e) {
    setWsStatus('disconnected');
    addLog('WebSocket', `Gagal membuat koneksi: ${e.message}`, 'error');
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    wsReady = true;
    wsConnectedAt = new Date();
    clearTimeout(reconnectTimer);
    setWsStatus('connected');
    addLog('WebSocket', `✅ Koneksi WebSocket berhasil – Bridge aktif di ws://localhost:8765`, 'ws');
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleServerMessage(msg);
    } catch (e) {
      console.warn('[WS] Pesan tidak valid:', event.data);
    }
  };

  ws.onclose = (e) => {
    wsReady = false;
    setWsStatus('disconnected');
    const dur = wsConnectedAt
      ? `(durasi: ${Math.round((Date.now() - wsConnectedAt) / 1000)}s)`
      : '';
    addLog('WebSocket', `Koneksi terputus ${dur} – Mencoba reconnect dalam ${RECONNECT_DELAY_MS / 1000}s…`, 'ws');
    scheduleReconnect();
  };

  ws.onerror = () => {
    wsReady = false;
    setWsStatus('disconnected');
    addLog('WebSocket', 'Terjadi kesalahan koneksi WebSocket', 'error');
  };
}

function scheduleReconnect() {
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    addLog('WebSocket', 'Mencoba reconnect ke bridge server…', 'ws');
    connectWS();
  }, RECONNECT_DELAY_MS);
}

/**
 * Kirim command ke bridge server (Command & Control Bridge)
 * Browser → WebSocket → Bridge → gRPC
 */
function sendCommand(action, data = {}) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    showToast('Error', 'Tidak terhubung ke server', 'error');
    return false;
  }
  addLog('WebSocket → gRPC', `Browser mengirim command: "${action}"`, 'ws');
  ws.send(JSON.stringify({ action, data }));
  return true;
}

// ========================================================
//  MESSAGE ROUTER (Server → Browser)
// ========================================================

function handleServerMessage(msg) {
  switch (msg.type) {

    case 'server_alert':
      // SERVER-INITIATED EVENT: push proaktif dari server tanpa request
      handleServerAlert(msg.data);
      break;

    case 'server_push':
      handleServerPush(msg.data);
      break;

    case 'room_update':
      // gRPC WatchRoomAvailability stream → UI
      handleRoomUpdate(msg.data);
      break;

    case 'notification':
      // gRPC SubscribeNotifications stream → UI
      handleNotification(msg.data);
      break;

    case 'activity':
      // Log aktivitas dari bridge
      handleBridgeActivity(msg.data);
      break;

    case 'response':
      // Respon dari command yang dikirim browser
      handleCommandResponse(msg);
      break;

    case 'heartbeat':
      // Keepalive – tidak tampil di UI log
      break;

    case 'error':
      showToast('Error', msg.error, 'error');
      addLog('Error', msg.error, 'error');
      break;

    default:
      console.log('[WS] Unknown message type:', msg.type);
  }
}

// ========================================================
//  KOMPONEN 1: CONNECTION STATUS INDICATOR (event-driven)
// ========================================================

function setWsStatus(state) {
  const labels = {
    connected:    '🟢 Online',
    connecting:   '🟡 Menghubungkan…',
    disconnected: '🔴 Offline',
  };

  [wsStatusLogin, wsStatusDash].forEach(el => {
    el.className = `ws-badge ${state}`;
  });
  wsLabelLogin.textContent = labels[state];
  wsLabelDash.textContent  = labels[state];
}

// ========================================================
//  KOMPONEN 2: STATS BAR (event-driven)
// ========================================================

function updateStats() {
  const rooms  = Object.values(roomsMap);
  const counts = { AVAILABLE: 0, OCCUPIED: 0, FULL: 0, MAINTENANCE: 0 };
  rooms.forEach(r => { counts[r.status] = (counts[r.status] || 0) + 1; });

  bumpNumber(countAvailable, counts.AVAILABLE);
  bumpNumber(countOccupied,  counts.OCCUPIED);
  bumpNumber(countFull,      counts.FULL);
  bumpNumber(countMaint,     counts.MAINTENANCE);
}

function bumpNumber(el, newVal) {
  if (el.textContent !== String(newVal)) {
    el.textContent = newVal;
    el.classList.remove('bump');
    void el.offsetWidth;
    el.classList.add('bump');
  }
}

// ========================================================
//  KOMPONEN 3: NOTIFICATION PANEL (event-driven via gRPC Stream)
// ========================================================

function handleNotification(data) {
  if (data.notif_type === 'HEARTBEAT') return;

  // Update badge
  notifCount++;
  notifBadge.textContent = notifCount > 99 ? '99+' : notifCount;
  notifBadge.classList.remove('hidden');

  // Buat elemen notif
  const el = makeNotifItem(data);
  prependToList(notifList, el.cloneNode(true), MAX_NOTIF_ITEMS);
  prependToList(drawerNotifList, el.cloneNode(true), MAX_NOTIF_ITEMS);

  // Toast
  if (data.notif_type !== 'SYSTEM') {
    showToast(data.title, data.message, notifTypeToToast(data.notif_type));
  }

  // Log gRPC stream event
  addLog(
    `gRPC Stream → Notification`,
    `[${data.notif_type}] ${data.title}: ${data.message}`,
    'grpc'
  );
}

function makeNotifItem(data) {
  const div = document.createElement('div');
  div.className = `notif-item type-${data.notif_type || 'SYSTEM'}`;
  div.innerHTML = `
    <div class="notif-title">${escapeHtml(data.title || '')}</div>
    <div class="notif-msg">${escapeHtml(data.message || '')}</div>
    <div class="notif-ts">${data.timestamp || data.ts || ''}</div>
  `;
  return div;
}

function notifTypeToToast(type) {
  const map = {
    BOOKING_CONFIRMED: 'success',
    BOOKING_CANCELLED: 'warn',
    ROOM_FULL:         'error',
    SYSTEM:            'info',
    BROADCAST:         'info',
  };
  return map[type] || 'info';
}

// ========================================================
//  SERVER-INITIATED EVENTS
//  Server push data proaktif ke browser tanpa request
// ========================================================

function handleServerAlert(data) {
  if (!data) return;

  const div = document.createElement('div');
  div.className = `server-alert-item type-${data.alert_type || 'INFO'}`;
  div.innerHTML = `
    <div class="notif-title">⚡ ${escapeHtml(data.title || '')}</div>
    <div class="notif-msg">${escapeHtml(data.message || '')}</div>
    <div class="notif-ts">${data.timestamp || ''}</div>
  `;
  prependToList(notifList, div, MAX_NOTIF_ITEMS);
  prependToList(drawerNotifList, div.cloneNode(true), MAX_NOTIF_ITEMS);

  if (data.alert_type === 'WELCOME' || data.alert_type === 'CONNECT') {
    showToast(data.title, data.message, 'info');
  }

  addLog(
    `Server-Initiated Event`,
    `[${data.alert_type}] ${data.title} – ${data.message}`,
    'system'
  );
}

function handleServerPush(data) {
  if (!data) return;
  showToast(data.title, data.message, 'info');
  addLog(
    `Server Push (Otomatis)`,
    data.message || data.title || '',
    'system'
  );
}

// ========================================================
//  KOMPONEN 4: ROOM STATUS GRID (event-driven via gRPC Stream)
// ========================================================

function handleRoomUpdate(data) {
  if (!data || !data.room_id || data.room_id === '*') return;

  const isNew = !roomsMap[data.room_id];

  roomsMap[data.room_id] = {
    room_id:           data.room_id,
    name:              data.room_name || roomsMap[data.room_id]?.name || data.room_id,
    status:            data.status,
    capacity:          data.capacity,
    current_occupancy: data.current_occupancy,
    location:          roomsMap[data.room_id]?.location || '',
    facilities:        roomsMap[data.room_id]?.facilities || [],
    event_type:        data.event_type,
  };

  updateStats();

  if (isNew) {
    const loading = $('room-loading');
    if (loading) loading.remove();
    roomGrid.appendChild(makeRoomCard(roomsMap[data.room_id]));
  } else {
    const card = $(`card-${data.room_id}`);
    if (card) updateRoomCard(card, roomsMap[data.room_id]);
  }

  // Log gRPC stream event (skip initial)
  if (data.event_type && data.event_type !== 'INITIAL_STATUS') {
    addLog(
      `gRPC Stream → RoomUpdate`,
      `Room ${data.room_id} (${data.room_name}): status=${data.status}, occupancy=${data.current_occupancy}/${data.capacity}, event=${data.event_type}`,
      'grpc'
    );
  } else if (data.event_type === 'INITIAL_STATUS' && isNew) {
    addLog(
      `gRPC WatchRoomAvailability`,
      `Initial status: ${data.room_id} → ${data.status} (${data.current_occupancy}/${data.capacity})`,
      'grpc'
    );
  }
}

function makeRoomCard(room) {
  const div = document.createElement('div');
  div.id        = `card-${room.room_id}`;
  div.className = `room-card status-${room.status}`;
  div.onclick   = () => quickBook(room.room_id);
  div.innerHTML = roomCardInner(room);
  return div;
}

function updateRoomCard(card, room) {
  card.className = `room-card status-${room.status} flash`;
  card.innerHTML = roomCardInner(room);
  setTimeout(() => card.classList.remove('flash'), 600);
}

function roomCardInner(room) {
  const occ = room.capacity ? room.current_occupancy / room.capacity : 0;
  const pct = Math.round(occ * 100);
  const fillClass = pct >= 100 ? 'full' : pct >= 70 ? 'warn' : '';

  const statusIcons = {
    AVAILABLE:    '🟢',
    OCCUPIED:     '🟡',
    FULL:         '🔴',
    MAINTENANCE:  '🔧',
  };
  const icon = statusIcons[room.status] || '⚪';

  return `
    <div class="room-id-tag">${escapeHtml(room.room_id)}</div>
    <div class="room-name">${escapeHtml(room.name)}</div>
    <div class="room-location">${escapeHtml(room.location || '')}</div>
    <div class="room-status-badge badge-${room.status}">
      ${icon} ${room.status}
    </div>
    <div class="room-occupancy">${room.current_occupancy} / ${room.capacity} orang</div>
    <div class="occ-bar">
      <div class="occ-fill ${fillClass}" style="width:${Math.min(pct, 100)}%"></div>
    </div>
    ${room.status === 'AVAILABLE' || room.status === 'OCCUPIED'
      ? `<button class="room-book-btn" onclick="event.stopPropagation();quickBook('${room.room_id}')">📅 Pesan Ruangan Ini</button>`
      : ''}
  `;
}

function quickBook(roomId) {
  $('bk-room').value = roomId;
  $('booking-section').scrollIntoView({ behavior: 'smooth' });
  $('bk-room').focus();
}

// ========================================================
//  KOMPONEN 5: gRPC & WebSocket ACTIVITY LOG (event-driven)
// ========================================================

/**
 * Kategori log:
 *  'grpc'    – peristiwa gRPC (stream, call, response)
 *  'ws'      – peristiwa WebSocket (connect, disconnect, send)
 *  'booking' – aksi booking/cancel
 *  'system'  – inisialisasi, login, server push
 *  'error'   – error
 */
function addLog(action, detail = '', category = 'system', timestamp = null) {
  const ts = timestamp || new Date().toLocaleTimeString('id-ID', { hour12: false });

  const hint = activityLog.querySelector('.empty-hint');
  if (hint) hint.remove();

  const div = document.createElement('div');
  div.className = `log-item log-${category}`;
  div.innerHTML = `
    <span class="log-type-badge badge-${category}">${category.toUpperCase()}</span>
    <div class="log-body">
      <div class="log-action">${escapeHtml(action)}</div>
      ${detail ? `<div class="log-detail">${escapeHtml(detail)}</div>` : ''}
    </div>
    <span class="log-ts">${ts}</span>
  `;
  activityLog.insertBefore(div, activityLog.firstChild);

  while (activityLog.children.length > MAX_LOG_ITEMS) {
    activityLog.removeChild(activityLog.lastChild);
  }
}

/** Bridge activity messages → log kategorisasi otomatis */
function handleBridgeActivity(data) {
  if (!data) return;
  const action  = data.action  || '';
  const detail  = data.detail  || '';

  // Kategorisasi otomatis
  let category = 'system';
  const lower  = action.toLowerCase();
  if (lower.includes('booking') || lower.includes('cancel')) category = 'booking';
  else if (lower.includes('room') || lower.includes('notif') || lower.includes('stream') || lower.includes('grpc')) category = 'grpc';
  else if (lower.includes('login') || lower.includes('logout')) category = 'system';

  addLog(action, detail, category, data.timestamp);
}

// ========================================================
//  COMMAND RESPONSE HANDLER
// ========================================================

function handleCommandResponse(msg) {
  const { action, success, data, error } = msg;

  switch (action) {

    case 'login':
      if (success) {
        currentUser = { id: data.user_id, name: data.user_name };
        showDashboard();
        addLog(
          `gRPC ↔ WebSocket: Login Berhasil`,
          `User "${data.user_name}" (${data.user_id}) berhasil auth. Memulai gRPC streaming…`,
          'system'
        );
        setTimeout(() => sendCommand('get_rooms'), 500);
      } else {
        showLoginError(error || 'Login gagal');
        btnLogin.disabled = false;
        btnLogin.querySelector('span').textContent = 'Masuk ke Dashboard';
        addLog('Login Gagal', error || 'Autentikasi ditolak', 'error');
      }
      break;

    case 'get_rooms':
      if (success && data.rooms) {
        data.rooms.forEach(r => {
          if (roomsMap[r.room_id]) {
            roomsMap[r.room_id].location   = r.location;
            roomsMap[r.room_id].facilities = r.facilities;
            const card = $(`card-${r.room_id}`);
            if (card) updateRoomCard(card, roomsMap[r.room_id]);
          } else {
            roomsMap[r.room_id] = r;
            const loading = $('room-loading');
            if (loading) loading.remove();
            roomGrid.appendChild(makeRoomCard(r));
          }
        });
        updateStats();
        addLog(
          `gRPC GetAllRooms → Response`,
          `${data.rooms.length} ruangan berhasil dimuat dari gRPC server`,
          'grpc'
        );
      }
      break;

    case 'book_room': {
      const bookMsg = $('booking-msg');
      if (success) {
        bookMsg.textContent = `✅ ${data.message} — Kode: ${data.confirmation_code}`;
        bookMsg.className   = 'form-msg success';
        $('booking-form').reset();
        $('bk-date').value = getTodayDate();
        showToast('Booking Berhasil!', data.message, 'success');
        addLog(
          `gRPC BookRoom → Sukses`,
          `Booking ID: ${data.booking_id} | Ruangan: ${data.room_name} | Kode: ${data.confirmation_code}`,
          'booking'
        );
      } else {
        bookMsg.textContent = `❌ ${error || data.message || 'Gagal'}`;
        bookMsg.className   = 'form-msg failure';
        showToast('Booking Gagal', error || data.message, 'error');
        addLog(`gRPC BookRoom → Gagal`, error || data.message || '', 'error');
      }
      $('btn-book').disabled = false;
      $('btn-book').querySelector('span').textContent = '✅ Booking Sekarang';
      break;
    }

    case 'cancel_booking': {
      const cancelMsg = $('cancel-msg');
      if (success) {
        cancelMsg.textContent = `✅ ${data.message}`;
        cancelMsg.className   = 'form-msg success';
        $('cancel-form').reset();
        showToast('Berhasil Dibatalkan', data.message, 'success');
        addLog(
          `gRPC CancelBooking → Sukses`,
          `Booking ID: ${data.booking_id || ''} berhasil dibatalkan`,
          'booking'
        );
        // Refresh daftar my bookings jika tampil
        if (myBookingsList.querySelector('.booking-item')) {
          sendCommand('get_my_bookings');
        }
      } else {
        cancelMsg.textContent = `❌ ${error || 'Gagal membatalkan booking'}`;
        cancelMsg.className   = 'form-msg failure';
        showToast('Gagal', error || 'Booking tidak dapat dibatalkan', 'error');
        addLog(`gRPC CancelBooking → Gagal`, error || '', 'error');
      }
      $('btn-cancel').disabled = false;
      $('btn-cancel').textContent = '❌ Batalkan Booking';
      // Re-enable inline cancel buttons
      document.querySelectorAll('.btn-cancel-booking').forEach(btn => {
        btn.disabled    = false;
        btn.textContent = '⛔ Batalkan';
      });
      break;
    }

    case 'get_my_bookings':
      renderMyBookings(data.bookings || []);
      addLog(
        `gRPC GetUserBookings → Response`,
        `${(data.bookings || []).length} booking ditemukan untuk user "${currentUser.name}"`,
        'grpc'
      );
      break;

    case 'send_notification': {
      const notifSendMsg = $('notif-send-msg');
      if (success) {
        notifSendMsg.textContent = `✅ Notifikasi terkirim ke ${data.recipients || 'semua'} pengguna`;
        notifSendMsg.className   = 'form-msg success';
        $('notif-form').reset();
        showToast('Broadcast Terkirim', 'Notifikasi berhasil dikirim ke semua user', 'success');
        addLog(
          `gRPC SendNotification → Sukses`,
          `Notifikasi broadcast dikirim ke ${data.recipients} penerima`,
          'grpc'
        );
      } else {
        notifSendMsg.textContent = `❌ ${error}`;
        notifSendMsg.className   = 'form-msg failure';
        addLog(`gRPC SendNotification → Gagal`, error || '', 'error');
      }
      $('btn-send-notif').disabled = false;
      $('btn-send-notif').textContent = '📤 Broadcast ke Semua';
      break;
    }

    default:
      if (!success) {
        showToast('Error', error || 'Terjadi kesalahan', 'error');
        addLog(`gRPC Response Error [${action}]`, error || '', 'error');
      }
  }
}

// ========================================================
//  MY BOOKINGS RENDERER
// ========================================================

function renderMyBookings(bookings) {
  myBookingsList.innerHTML = '';
  if (!bookings.length) {
    myBookingsList.innerHTML = '<p class="empty-hint">Belum ada booking.</p>';
    return;
  }
  bookings.forEach(b => {
    const isActive    = b.status === 'ACTIVE';
    const div = document.createElement('div');
    div.className   = 'booking-item';
    div.dataset.bid = b.booking_id;
    div.innerHTML = `
      <div class="bi-header">
        <span class="bi-id">${escapeHtml(b.booking_id)}</span>
        <span class="bi-status bi-status-${b.status}">${b.status}</span>
      </div>
      <div class="bi-room">${escapeHtml(b.room_name)}</div>
      <div class="bi-time">📅 ${escapeHtml(b.date)} &nbsp;|&nbsp; ⏰ ${b.start_time} – ${b.end_time}</div>
      <div class="bi-code">Kode: <strong>${escapeHtml(b.confirmation_code)}</strong> &nbsp;|&nbsp; ${escapeHtml(b.purpose)}</div>
      ${isActive ? `
      <div class="bi-actions">
        <button class="btn-cancel-booking" data-booking-id="${escapeHtml(b.booking_id)}">⛔ Batalkan</button>
      </div>` : ''}
    `;
    myBookingsList.appendChild(div);
  });

  // Attach event listeners untuk inline cancel buttons
  myBookingsList.querySelectorAll('.btn-cancel-booking').forEach(btn => {
    btn.addEventListener('click', () => {
      const bookingId = btn.dataset.bookingId;
      if (!bookingId) return;
      if (!confirm(`Yakin ingin membatalkan booking ${bookingId}?`)) return;

      // Isi form cancel secara otomatis dan kirim
      $('cancel-id').value     = bookingId;
      $('cancel-reason').value = 'Dibatalkan dari daftar booking';

      btn.disabled    = true;
      btn.textContent = '⏳ Membatalkan…';

      $('btn-cancel').disabled    = true;
      $('btn-cancel').textContent = '⏳ Memproses…';
      $('cancel-msg').textContent = '';

      addLog(
        `WebSocket → gRPC: CancelBooking`,
        `Browser mengirim perintah pembatalan booking ID: ${bookingId}`,
        'ws'
      );
      sendCommand('cancel_booking', {
        booking_id: bookingId,
        reason:     'Dibatalkan dari daftar booking',
      });
    });
  });
}

// ========================================================
//  LOGIN / LOGOUT
// ========================================================

function showLoginError(msg) {
  loginError.textContent = msg;
  loginError.classList.remove('hidden');
}

function showDashboard() {
  loginScreen.classList.remove('active');
  dashScreen.classList.add('active');
  userDisplayName.textContent = currentUser.name;
  $('bk-date').value = getTodayDate();
}

function logout() {
  addLog('WebSocket', 'User logout – menutup koneksi WebSocket', 'ws');
  if (ws) { ws.close(); ws = null; }
  wsReady = false;

  loginScreen.classList.add('active');
  dashScreen.classList.remove('active');

  // Reset state
  Object.keys(roomsMap).forEach(k => delete roomsMap[k]);
  notifCount = 0;
  notifBadge.classList.add('hidden');
  notifList.innerHTML     = '<p class="empty-hint">Notifikasi akan muncul di sini…</p>';
  activityLog.innerHTML   = '';
  myBookingsList.innerHTML = '<p class="empty-hint">Klik tombol Muat untuk melihat booking Anda.</p>';
  roomGrid.innerHTML = `
    <div class="room-skeleton" id="room-loading">
      ${Array(5).fill('<div class="sk-card"></div>').join('')}
    </div>`;
  loginError.classList.add('hidden');
  inputUid.value   = '';
  inputUname.value = '';
  currentUser = { id: '', name: '' };

  setTimeout(() => connectWS(), 100);
}

// ========================================================
//  TOAST NOTIFICATION
// ========================================================

function showToast(title, message, type = 'info') {
  const icons     = { success: '✅', error: '❌', warn: '⚠️', info: 'ℹ️' };
  const container = $('toast-container');

  const div = document.createElement('div');
  div.className = `toast ${type}`;
  div.innerHTML = `
    <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
    <div class="toast-body">
      <div class="toast-title">${escapeHtml(title)}</div>
      ${message ? `<div class="toast-msg">${escapeHtml(message)}</div>` : ''}
    </div>
  `;
  container.appendChild(div);

  setTimeout(() => {
    div.classList.add('exit');
    setTimeout(() => div.remove(), 350);
  }, 4500);
}

// ========================================================
//  NOTIFICATION DRAWER
// ========================================================

function openDrawer() {
  notifDrawer.classList.remove('hidden');
  drawerOverlay.classList.remove('hidden');
  requestAnimationFrame(() => {
    notifDrawer.classList.add('open');
    drawerOverlay.classList.add('open');
  });
  notifCount = 0;
  notifBadge.classList.add('hidden');
}

function closeDrawer() {
  notifDrawer.classList.remove('open');
  drawerOverlay.classList.remove('open');
  setTimeout(() => {
    notifDrawer.classList.add('hidden');
    drawerOverlay.classList.add('hidden');
  }, 350);
}

// ========================================================
//  UTILITY
// ========================================================

function getTodayDate() {
  return new Date().toISOString().split('T')[0];
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;');
}

function prependToList(container, el, max = 50) {
  const hint = container.querySelector('.empty-hint');
  if (hint) hint.remove();
  container.insertBefore(el, container.firstChild);
  while (container.children.length > max) {
    container.removeChild(container.lastChild);
  }
}

// ========================================================
//  EVENT LISTENERS
// ========================================================

// -- Theme toggles --
$('btn-theme-login').addEventListener('click', toggleTheme);
$('btn-theme-dash').addEventListener('click',  toggleTheme);

// -- Login form --
loginForm.addEventListener('submit', e => {
  e.preventDefault();
  const uid   = inputUid.value.trim();
  const uname = inputUname.value.trim();

  if (!uid || !uname) {
    showLoginError('NIM dan Nama wajib diisi');
    return;
  }
  if (!wsReady) {
    showLoginError('Belum terhubung ke server. Tunggu sebentar…');
    return;
  }

  loginError.classList.add('hidden');
  btnLogin.disabled = true;
  btnLogin.querySelector('span').textContent = 'Menghubungkan…';

  addLog(
    `WebSocket → gRPC: Login`,
    `Browser mengirim command login untuk user "${uname}" (${uid})`,
    'ws'
  );
  sendCommand('login', { user_id: uid, user_name: uname });
});

// -- Logout --
$('btn-logout').addEventListener('click', logout);

// -- Refresh rooms --
$('btn-refresh-rooms').addEventListener('click', () => {
  addLog('WebSocket → gRPC', 'Browser meminta refresh data ruangan', 'ws');
  sendCommand('get_rooms');
});

// -- Booking form --
$('booking-form').addEventListener('submit', e => {
  e.preventDefault();
  const data = {
    room_id:    $('bk-room').value.trim().toUpperCase(),
    date:       $('bk-date').value,
    start_time: $('bk-start').value,
    end_time:   $('bk-end').value,
    num_people: parseInt($('bk-people').value, 10),
    purpose:    $('bk-purpose').value.trim(),
  };
  if (!data.room_id || !data.date || !data.start_time || !data.end_time || !data.num_people) {
    $('booking-msg').textContent = 'Semua field wajib diisi';
    $('booking-msg').className   = 'form-msg failure';
    return;
  }
  $('btn-book').disabled = true;
  $('btn-book').querySelector('span').textContent = '⏳ Memproses…';
  $('booking-msg').textContent = '';

  addLog(
    `WebSocket → gRPC: BookRoom`,
    `Memesan ruangan ${data.room_id} untuk ${data.date} pukul ${data.start_time}–${data.end_time} (${data.num_people} orang)`,
    'ws'
  );
  sendCommand('book_room', data);
});

// -- Cancel form --
$('cancel-form').addEventListener('submit', e => {
  e.preventDefault();
  const bookingId = $('cancel-id').value.trim().toUpperCase();
  const reason    = $('cancel-reason').value.trim();

  if (!bookingId) {
    $('cancel-msg').textContent = 'Booking ID wajib diisi';
    $('cancel-msg').className   = 'form-msg failure';
    return;
  }

  $('btn-cancel').disabled    = true;
  $('btn-cancel').textContent = '⏳ Memproses…';
  $('cancel-msg').textContent = '';

  addLog(
    `WebSocket → gRPC: CancelBooking`,
    `Browser mengirim perintah pembatalan booking ID: ${bookingId}${reason ? ` | Alasan: ${reason}` : ''}`,
    'ws'
  );
  sendCommand('cancel_booking', { booking_id: bookingId, reason });
});

// -- My bookings --
$('btn-load-mybooking').addEventListener('click', () => {
  addLog('WebSocket → gRPC', 'Browser meminta daftar booking milik user', 'ws');
  sendCommand('get_my_bookings');
});

// -- Send notification (admin / server-initiated trigger) --
$('notif-form').addEventListener('submit', e => {
  e.preventDefault();
  const data = {
    title:          $('notif-title').value.trim(),
    message:        $('notif-msg').value.trim(),
    notif_type:     'BROADCAST',
    target_user_id: '*',
  };
  if (!data.title || !data.message) {
    $('notif-send-msg').textContent = 'Judul dan pesan wajib diisi';
    $('notif-send-msg').className   = 'form-msg failure';
    return;
  }
  $('btn-send-notif').disabled    = true;
  $('btn-send-notif').textContent = '⏳ Mengirim…';

  addLog(
    `WebSocket → gRPC: SendNotification (Server Push)`,
    `Admin broadcast: "${data.title}" → ke semua pengguna`,
    'ws'
  );
  sendCommand('send_notification', data);
});

// -- Clear log --
$('btn-clear-log').addEventListener('click', () => {
  activityLog.innerHTML = '<p class="empty-hint">Log dihapus.</p>';
});

// -- Clear notifications --
$('btn-clear-notif').addEventListener('click', () => {
  notifList.innerHTML = '<p class="empty-hint">Notifikasi dihapus.</p>';
  notifCount = 0;
  notifBadge.classList.add('hidden');
});

// -- Notification drawer --
$('btn-notif-bell').addEventListener('click', openDrawer);
$('btn-close-drawer').addEventListener('click', closeDrawer);
$('drawer-overlay').addEventListener('click', closeDrawer);

// ========================================================
//  INIT
// ========================================================

document.addEventListener('DOMContentLoaded', () => {
  const dateInput = $('bk-date');
  if (dateInput) dateInput.value = getTodayDate();

  addLog('Sistem', 'Aplikasi Smart Study Room diinisialisasi', 'system');
  addLog('WebSocket', `Menghubungkan ke bridge server: ws://localhost:8765`, 'ws');

  connectWS();
});
