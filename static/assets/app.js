// ── Navigation ────────────────────────────────────────────────────────────────
function showView(name, link) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
  document.getElementById('view-' + name).classList.add('active');
  link.classList.add('active');
  if (name === 'docs') loadDocs();
}

// ── Chat ──────────────────────────────────────────────────────────────────────
const chatMessages = document.getElementById('chat-messages');
const chatForm     = document.getElementById('chat-form');
const chatInput    = document.getElementById('chat-input');
const chatBtn      = document.getElementById('chat-btn');

chatForm.addEventListener('submit', async e => {
  e.preventDefault();
  const query = chatInput.value.trim();
  if (!query) return;

  addBubble(query, 'user');
  chatInput.value = '';
  chatBtn.disabled = true;

  const thinking = addBubble('Pensando…', 'bot thinking');

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });

    if (!res.ok) { throw new Error(res.statusText); }

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let   bubble  = null;
    let   buffer  = '';

    thinking.remove();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data:')) continue;
        let event;
        try { event = JSON.parse(line.slice(5).trim()); } catch { continue; }

        if (event.type === 'token') {
          if (!bubble) bubble = addBubble('', 'bot');
          bubble.childNodes[0]
            ? (bubble.firstChild.textContent += event.content)
            : bubble.appendChild(document.createTextNode(event.content));

        } else if (event.type === 'done' || event.type === 'reject') {
          if (!bubble) bubble = addBubble(event.answer ?? '', 'bot');

          if (event.sources?.length) {
            const src = document.createElement('div');
            src.className = 'sources';
            src.textContent = '📄 Fuentes: ' +
              event.sources.map(s => `${s.archivo} p.${s.pagina}`).join(' · ');
            bubble.appendChild(src);
          }

          if (event.metrics) {
            const m = event.metrics;
            const meta = document.createElement('div');
            meta.className = 'sources';
            meta.textContent =
              `⏱ ${m.tiempo_respuesta?.toFixed(2) ?? '—'}s` +
              ` · chunks: ${m.chunks_usados ?? '—'}/${m.chunks_encontrados ?? '—'}` +
              (m.distancia_promedio != null ? ` · dist: ${m.distancia_promedio.toFixed(3)}` : '') +
              ` · 🤖 ${m.modelo_usado ?? '—'}`;
            bubble.appendChild(meta);
          }

          chatMessages.scrollTop = chatMessages.scrollHeight;
          refreshMetrics();
        }
      }
    }
  } catch {
    thinking.remove();
    addBubble('Error al conectar con el servidor.', 'bot');
  } finally {
    chatBtn.disabled = false;
    chatInput.focus();
  }
});

function addBubble(text, cls) {
  const div = document.createElement('div');
  div.className = 'bubble ' + cls;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

// ── Upload ────────────────────────────────────────────────────────────────────
const dropZone       = document.getElementById('drop-zone');
const fileInput      = document.getElementById('file-input');
const uploadProgress = document.getElementById('upload-progress');
const uploadBar      = document.getElementById('upload-bar');
const uploadLabel    = document.getElementById('upload-label');

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  uploadFiles(e.dataTransfer.files);
});
fileInput.addEventListener('change', () => uploadFiles(fileInput.files));

async function uploadFiles(files) {
  const total = files.length;
  uploadProgress.style.display = 'block';
  uploadBar.max = total;

  for (let i = 0; i < total; i++) {
    const file = files[i];
    uploadLabel.textContent = `Subiendo ${file.name} (${i + 1}/${total})…`;
    uploadBar.value = i;

    const form = new FormData();
    form.append('file', file);
    try {
      const res  = await fetch('/documents', { method: 'POST', body: form });
      const data = await res.json();
      showToast(
        res.ok
          ? `✅ ${file.name} — ${data.chunks} chunks`
          : `⚠️ ${file.name}: ${data.detail}`,
        res.ok ? 'success' : 'warning'
      );
    } catch {
      showToast(`❌ Error subiendo ${file.name}`, 'error');
    }
  }

  uploadBar.value = total;
  uploadLabel.textContent = 'Listo.';
  setTimeout(() => { uploadProgress.style.display = 'none'; }, 2000);
  fileInput.value = '';
  loadDocs();
}

// ── Documents CRUD ────────────────────────────────────────────────────────────
async function loadDocs() {
  const wrap = document.getElementById('docs-table-wrap');
  wrap.innerHTML = '<p class="secondary">Cargando…</p>';

  try {
    const res  = await fetch('/documents');
    const docs = await res.json();

    if (!docs.length) {
      wrap.innerHTML = '<p class="secondary">No hay documentos ingresados.</p>';
      return;
    }

    const table = document.createElement('table');
    table.innerHTML = `
      <thead>
        <tr>
          <th>Archivo</th>
          <th>Chunks</th>
          <th>SHA-256</th>
          <th></th>
        </tr>
      </thead>
      <tbody></tbody>`;

    const tbody = table.querySelector('tbody');
    docs.forEach(doc => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${escHtml(doc.archivo)}</td>
        <td>${doc.chunks}</td>
        <td><code style="font-size:.7rem">${doc.sha256.slice(0, 12)}…</code></td>
        <td>
          <button class="outline contrast" style="padding:.25rem .6rem;font-size:.8rem"
                  onclick="deleteDoc('${doc.sha256}', '${escHtml(doc.archivo)}')">
            🗑 Eliminar
          </button>
        </td>`;
      tbody.appendChild(tr);
    });

    wrap.innerHTML = '';
    wrap.appendChild(table);
  } catch {
    wrap.innerHTML = '<p class="secondary">Error al cargar documentos.</p>';
  }
}

async function deleteDoc(sha256, name) {
  if (!confirm(`¿Eliminar "${name}"?\nSe borrarán todos sus chunks del vector store.`)) return;

  try {
    const res = await fetch(`/documents/${sha256}`, { method: 'DELETE' });
    if (res.ok) {
      const data = await res.json();
      showToast(`🗑 "${name}" eliminado (${data.chunks_deleted} chunks)`, 'success');
      loadDocs();
    } else {
      const data = await res.json();
      showToast(`Error: ${data.detail}`, 'error');
    }
  } catch {
    showToast('Error de conexión.', 'error');
  }
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg, type = 'success') {
  const t = document.createElement('div');
  t.setAttribute('role', 'alert');
  t.style.cssText =
    'position:fixed;bottom:1.5rem;right:1.5rem;z-index:999;' +
    'padding:.75rem 1.25rem;border-radius:.5rem;font-size:.85rem;' +
    'box-shadow:0 4px 12px rgba(0,0,0,.15);max-width:320px;';
  const colors = { success: '#22c55e', warning: '#f59e0b', error: '#ef4444' };
  t.style.background = colors[type] || colors.success;
  t.style.color = '#fff';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── Metrics panel ─────────────────────────────────────────────────────────────
async function refreshMetrics() {
  try {
    const res  = await fetch('/metrics');
    const data = await res.json();

    document.getElementById('m-consultas').textContent =
      `${data.consultas_registradas} consulta${data.consultas_registradas !== 1 ? 's' : ''}`;
    document.getElementById('m-tiempo').textContent =
      `⏱ ${data.promedio_tiempo_segundos ?? '—'}s promedio`;
    document.getElementById('m-chunks').textContent =
      `📦 ${data.promedio_chunks_encontrados ?? '—'} chunks promedio`;
    document.getElementById('m-rechazo').textContent =
      `🚫 ${data.tasa_rechazo != null ? (data.tasa_rechazo * 100).toFixed(0) + '%' : '—'} rechazo`;

    const tbody = document.getElementById('metrics-tbody');
    if (!data.historial.length) return;

    tbody.innerHTML = '';
    data.historial.slice().reverse().forEach((r, i) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${data.historial.length - i}</td>
        <td>${r.tiempo_respuesta?.toFixed(2) ?? '—'}s</td>
        <td>${r.chunks_encontrados ?? '—'}</td>
        <td>${r.chunks_usados ?? '—'}</td>
        <td>${r.distancia_promedio != null ? r.distancia_promedio.toFixed(3) : '—'}</td>
        <td><code style="font-size:.7rem">${escHtml(r.modelo_usado ?? '')}</code></td>
        <td>${r.rechazada ? '⚠️ Sí' : '✅ No'}</td>`;
      tbody.appendChild(tr);
    });

    document.getElementById('metrics-panel').open = true;
  } catch { /* silently ignore */ }
}

// ── Utils ─────────────────────────────────────────────────────────────────────
function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('view-docs').classList.contains('active')) loadDocs();
});
