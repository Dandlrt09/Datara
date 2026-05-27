/* ============================================
   DATARA — API Client
   ============================================ */

var DataraAPI = (() => {
  const BASE = '/api';

  /** Get or create session ID from sessionStorage */
  function getSessionId() {
    let sid = sessionStorage.getItem('datara_session_id');
    if (!sid) {
      // Will be initialized on first API call
      return null;
    }
    return sid;
  }

  function setSessionId(sid) {
    sessionStorage.setItem('datara_session_id', sid);
  }

  /** Core fetch wrapper */
  async function request(method, path, body, options = {}) {
    const headers = {};
    const sid = getSessionId();
    if (sid) headers['X-Session-Id'] = sid;
    
    if (body && !(body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const config = {
      method,
      headers,
    };
    if (body) config.body = body instanceof FormData ? body : JSON.stringify(body);

    try {
      const res = await fetch(`${BASE}${path}`, config);
      
      // Handle 404 (expired session) → auto-reset
      if (res.status === 404) {
        const data = await res.json().catch(() => ({}));
        if (data.code === 'SESSION_EXPIRED' || data.code === 'SESSION_NOT_FOUND') {
          showToast('Sesión expirada. Creando nueva...', 'warning');
          await resetSession();
          return request(method, path, body, options);
        }
        throw new APIError('Recurso no encontrado', 404, 'NOT_FOUND');
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: res.statusText }));
        throw new APIError(data.error || 'Error de servidor', res.status, data.code);
      }

      // Handle 204 No Content
      if (res.status === 204) return null;

      return res.json();
    } catch (err) {
      if (err instanceof APIError) throw err;
      showToast('Error de conexión con el servidor', 'error');
      throw new APIError('Error de conexión', 0, 'NETWORK_ERROR');
    }
  }

  class APIError extends Error {
    constructor(message, status, code) {
      super(message);
      this.status = status;
      this.code = code;
    }
  }

  /** Initialize session — verifies the saved ID is still valid, creates one if not */
  async function initSession() {
    var saved = getSessionId();
    if (saved) {
      /* Quick check: is this session still alive? */
      try {
        await request('GET', '/session');
        return saved;  /* still valid */
      } catch (_) {
        /* Session expired — fall through to create a new one */
        sessionStorage.removeItem('datara_session_id');
      }
    }
    try {
      const data = await request('POST', '/session/reset');
      setSessionId(data.new_session);
      return data.new_session;
    } catch (err) {
      showToast('Error al iniciar sesión', 'error');
      return null;
    }
  }

  /** Reset session */
  async function resetSession() {
    try {
      const data = await request('POST', '/session/reset');
      setSessionId(data.new_session);
      showToast('Nueva sesión creada', 'success');
      return data;
    } catch (err) {
      showToast('Error al reiniciar sesión', 'error');
      return null;
    }
  }

  /** Get session state (sidebar indicators) */
  async function getSessionState() {
    return request('GET', '/session');
  }

  // --- Files ---
  async function uploadFile(file, sheetName) {
    const formData = new FormData();
    formData.append('file', file);
    if (sheetName) formData.append('sheet_name', sheetName);
    return request('POST', '/files/upload', formData);
  }

  async function listFiles() {
    return request('GET', '/files');
  }

  async function deleteFile(filename) {
    return request('DELETE', `/files/${encodeURIComponent(filename)}`);
  }

  async function getFilePreview(filename, rows = 10) {
    return request('GET', `/files/${encodeURIComponent(filename)}/preview?rows=${rows}`);
  }

  // --- Chat ---
  async function sendMessage(message) {
    return request('POST', '/chat/message', { message });
  }

  async function getChatHistory() {
    return request('GET', '/chat/history');
  }

  async function clearChat() {
    return request('DELETE', '/chat/clear');
  }

  // --- Dashboard ---
  async function getDashboard(filters) {
    let path = '/dashboard';
    if (filters) {
      const params = new URLSearchParams();
      if (filters.filter_col) params.set('filter_col', filters.filter_col);
      if (filters.filter_vals) params.set('filter_vals', filters.filter_vals.join(','));
      path += '?' + params.toString();
    }
    return request('GET', path);
  }

  async function addDashboardItem(config) {
    return request('POST', '/dashboard', config);
  }

  async function deleteDashboardItem(itemId) {
    return request('DELETE', `/dashboard/${itemId}`);
  }

  // --- Settings ---
  async function getSettings() {
    return request('GET', '/settings');
  }

  async function updateSettings(data) {
    return request('PUT', '/settings', data);
  }

  // --- Export ---
  async function exportChart(messageId) {
    return request('GET', `/export/${messageId}/chart`);
  }

  async function exportData(messageId) {
    return request('GET', `/export/${messageId}/data`);
  }

  async function exportSession() {
    return request('GET', '/export/session');
  }

  // --- Archive ---
  async function archiveCurrentSession(archiveId) {
    // Always send a JSON body — empty object when creating, {archive_id} when updating
    return request('POST', '/session/current/archive', archiveId ? { archive_id: archiveId } : {});
  }

  async function listArchivedSessions() {
    return request('GET', '/session/archived');
  }

  async function getArchivedSession(archiveId) {
    return request('GET', `/session/archived/${encodeURIComponent(archiveId)}`);
  }

  async function restoreArchivedSession(archiveId) {
    return request('POST', `/session/archived/${encodeURIComponent(archiveId)}/restore`);
  }

  async function deleteArchivedSession(archiveId) {
    return request('DELETE', `/session/archived/${encodeURIComponent(archiveId)}`);
  }

  async function renameArchivedSession(archiveId, name) {
    return request('PATCH', `/session/archived/${encodeURIComponent(archiveId)}`, { name });
  }

  // --- Toast system ---
  let toastContainer = null;

  function ensureToastContainer() {
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.className = 'toast-container';
      document.body.appendChild(toastContainer);
    }
    return toastContainer;
  }

  function showToast(message, type = 'info', duration = 4000) {
    const container = ensureToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.animation = 'toastOut 0.2s ease forwards';
      setTimeout(() => toast.remove(), 200);
    }, duration);
  }

  // --- Sidebar ---

  /** HTML-escape a string */
  function escHtml(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  /** Load archived sessions into the sidebar */
  async function loadSidebarArchives() {
    var list = document.getElementById('sidebar-archives-list');
    var toggle = document.getElementById('sidebar-archives-toggle');
    var arrow = document.getElementById('sidebar-archives-arrow');
    if (!list) return;

    try {
      var archives = await request('GET', '/session/archived');
      list.innerHTML = '';
      if (!archives || archives.length === 0) {
        list.innerHTML = '<p class="text-xs text-on-surface-variant px-2 py-1">No hay sesiones archivadas</p>';
        if (toggle) toggle.classList.add('hidden');
        return;
      }
      if (toggle) toggle.classList.remove('hidden');

      list.classList.remove('hidden');
      if (arrow) arrow.style.transform = 'rotate(90deg)';

      archives.forEach(function(arch) {
        var dateStr = '\u2014';
        if (arch.archived_at) {
          dateStr = new Date(arch.archived_at * 1000).toLocaleString('es-ES');
        }
        var item = document.createElement('div');
        item.className = 'flex items-center gap-1 px-3 py-2 rounded-lg hover:bg-surface-container-highest transition-colors group cursor-pointer';
        item.setAttribute('data-archive-id', arch.archive_id);

        /* Click = restore */
        item.addEventListener('click', function(e) {
          if (e.target.closest('.sidebar-archive-del-btn')) return;
          var aid = this.getAttribute('data-archive-id');
          if (aid) {
            showToast('Restaurando sesión...', 'info');
            DataraAPI.restoreArchivedSession(aid).then(function(response) {
              if (response && response.new_session_id) {
                sessionStorage.setItem('datara_session_id', response.new_session_id);
                sessionStorage.setItem('datara_active_archive_id', aid);
                window.location.href = '/chat';
              }
            }).catch(function(err) {
              var msg = err.message || 'desconocido';
              if (msg.indexOf('ARCHIVE_NOT_FOUND') >= 0 || msg.indexOf('404') >= 0) {
                showToast('Esa sesión ya no existe.', 'warning');
                loadSidebarArchives();
                if (typeof fetchArchivedSessions === 'function') fetchArchivedSessions();
              } else {
                showToast('Error al restaurar: ' + msg, 'error');
              }
            });
          }
        });

        item.innerHTML =
          '<div class="flex-1 min-w-0">' +
            '<span class="text-xs text-on-surface font-medium truncate block">' + escHtml(arch.name || 'Sesión') + '</span>' +
            '<span class="text-[10px] text-on-surface-variant mt-0.5 block">' + escHtml(dateStr) + '</span>' +
          '</div>' +
          '<button class="sidebar-archive-del-btn w-7 h-7 rounded-full flex items-center justify-center text-on-surface-variant opacity-0 group-hover:opacity-100 hover:text-error hover:bg-error/10 transition-all shrink-0" title="Eliminar" data-id="' + arch.archive_id + '">' +
            '<span class="material-symbols-outlined text-sm">delete</span>' +
          '</button>';
        list.appendChild(item);

        /* Delete handler */
        var delBtn = item.querySelector('.sidebar-archive-del-btn');
        if (delBtn) {
          delBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            var id = this.getAttribute('data-id');
            if (confirm('¿Eliminar esta sesión archivada?\nNo se puede deshacer.')) {
              DataraAPI.deleteArchivedSession(id).then(function() {
                /* Si el archivo borrado es el que tenemos activo, limpiar el flag */
                var activeId = sessionStorage.getItem('datara_active_archive_id');
                if (activeId === id) {
                  sessionStorage.removeItem('datara_active_archive_id');
                  showToast('Archivo borrado. La sesión actual sigue activa pero ya no está vinculada.', 'warning', 5000);
                  /* Cambiar botón de "Actualizar" a "Archivar" si existe */
                  var archiveBtn = document.getElementById('archive-btn');
                  if (archiveBtn) archiveBtn.innerHTML = '<span class="material-symbols-outlined text-sm">archive</span> Archivar';
                } else {
                  showToast('Sesión eliminada', 'success');
                }
                loadSidebarArchives();
                /* También refrescar panel de sesiones anteriores en chat */
                if (typeof fetchArchivedSessions === 'function') fetchArchivedSessions();
              }).catch(function(err) {
                showToast('Error: ' + (err.message || 'desconocido'), 'error');
              });
            }
          });
        }
      });
    } catch(e) {
      list.innerHTML = '<p class="text-xs text-on-surface-variant px-2 py-1">Error al cargar</p>';
    }

    if (toggle && list && arrow && !toggle.getAttribute('data-init')) {
      toggle.setAttribute('data-init', '1');
      toggle.addEventListener('click', function() {
        var isHidden = list.classList.contains('hidden');
        list.classList.toggle('hidden');
        arrow.style.transform = isHidden ? 'rotate(90deg)' : 'rotate(0deg)';
      });
    }
  }

  /** Load active files into the sidebar (safe to call before session exists) */
  async function loadActiveFiles(retries) {
    if (retries === undefined) retries = 0;
    var MAX_RETRIES = 30; /* ~1.5s at 50ms intervals */
    var list = document.getElementById('sidebar-active-files');
    if (!list) {
      if (retries < MAX_RETRIES) {
        setTimeout(function() { loadActiveFiles(retries + 1); }, 50);
      }
      return;
    }

    /* No session yet — schedule retry if we haven't given up */
    if (!getSessionId()) {
      if (retries < MAX_RETRIES) {
        setTimeout(function() { loadActiveFiles(retries + 1); }, 50);
      }
      return;
    }

    try {
      var files = await request('GET', '/files');
      list.innerHTML = '';

      /* Update file count stat — always, even when 0 */
      var countEl = document.getElementById('sidebar-file-count');
      if (countEl) countEl.textContent = files ? files.length : 0;

      if (!files || files.length === 0) {
        list.innerHTML = '<p class="text-xs text-on-surface-variant px-2 py-1">Sin archivos cargados</p>';
        return;
      }

      files.forEach(function(f) {
        var item = document.createElement('div');
        item.className = 'flex items-center gap-2 p-2 rounded hover:bg-surface-container-highest transition-colors cursor-pointer group';
        item.innerHTML =
          '<span style="width:6px;height:6px;border-radius:50%;background:#22c55e;flex-shrink:0;display:inline-block;"></span>' +
          '<span class="text-xs text-on-surface font-mono truncate">' + escHtml(f.filename || f.display_name) + '</span>';
        list.appendChild(item);
      });
    } catch(e) {
      list.innerHTML = '<p class="text-xs text-on-surface-variant px-2 py-1">Error al cargar</p>';
    }
  }

  /** Load message count into the sidebar statistic */
  async function loadMessageCount() {
    var countEl = document.getElementById('sidebar-message-count');
    if (!countEl) return;

    /* No session yet — silently skip */
    if (!getSessionId()) return;

    try {
      var state = await request('GET', '/session');
      var total = state.message_count || 0;
      var user = state.user_message_count || 0;
      var assistant = state.assistant_message_count || 0;
      countEl.textContent = total;
      /* Also set a title tooltip with breakdown */
      countEl.title = 'Tú: ' + user + ' · Datara: ' + assistant;
    } catch(e) {
      // silently ignore
    }
  }

  /** Refresh the entire sidebar (fetch + nav + archives + files) */
  async function refreshSidebar() {
    var c = document.getElementById('sidebar-container');
    if (!c) return;

    try {
      var r = await fetch('/static/screens/sidebar.inc.html?t=' + Date.now());
      var h = await r.text();
      c.innerHTML = h;

      /* Highlight active nav link */
      var p = window.location.pathname;
      var a = c.querySelectorAll('nav a');
      for (var i = 0; i < a.length; i++) {
        if (a[i].getAttribute('href') === p) {
          a[i].className = 'bg-secondary-container text-on-secondary-container font-bold rounded-lg px-4 py-2.5 flex items-center gap-3 transition-all duration-200 active:scale-95 active-nav-border group';
        }
      }

      /* Load dynamic content */
      loadActiveFiles();
      loadSidebarArchives();
      loadMessageCount();
    } catch(e) {
      // sidebar invisible — not critical
    }
  }

  return {
    initSession,
    resetSession,
    getSessionState,
    uploadFile,
    listFiles,
    deleteFile,
    getFilePreview,
    sendMessage,
    getChatHistory,
    clearChat,
    getDashboard,
    addDashboardItem,
    deleteDashboardItem,
    getSettings,
    updateSettings,
    exportChart,
    exportData,
    exportSession,
    archiveCurrentSession,
    listArchivedSessions,
    getArchivedSession,
    restoreArchivedSession,
    deleteArchivedSession,
    renameArchivedSession,
    showToast,
    refreshSidebar,
    loadSidebarArchives,
    loadActiveFiles,
    loadMessageCount,
    getSessionId: () => getSessionId(),
  };
})();
