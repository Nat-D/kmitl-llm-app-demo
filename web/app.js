// The browser side of the SSE lecture: POST the question, then read the streaming
// response body. Network chunks do NOT line up with SSE frames, so we stitch them
// with a buffer, split on the blank line, and JSON.parse each `data:` payload.
const form = document.getElementById('form');
const input = document.getElementById('q');
const log = document.getElementById('log');
const ragToggle = document.getElementById('rag');

function addUser(text) {
  const d = document.createElement('div');
  d.className = 'msg user';
  d.textContent = text;
  log.appendChild(d);
  d.scrollIntoView({ block: 'end' });
}

function addBot() {
  const wrap = document.createElement('div');
  wrap.className = 'msg bot';
  const answer = document.createElement('span');
  wrap.appendChild(answer);
  log.appendChild(wrap);
  let sources = null;
  return {
    appendToken: (t) => { answer.textContent += t; wrap.scrollIntoView({ block: 'end' }); },
    showSources: (list) => {
      if (!sources) { sources = document.createElement('div'); sources.className = 'sources'; wrap.appendChild(sources); }
      sources.innerHTML = '<b>sources</b> ' + list.map((s, i) => `[${i + 1}] ${s.title}`).join('&nbsp;&nbsp;');
    },
    error: (m) => { answer.textContent += '\n⚠ ' + m; },
  };
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q) return;
  input.value = '';
  addUser(q);
  const bot = addBot();

  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ message: q, use_rag: ragToggle.checked }),
  });

  // A rejected request (422 bad input, 429 rate-limited) has no SSE body — show it.
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try { const d = await res.json(); if (d.detail) msg = d.detail; } catch { /* non-JSON */ }
    bot.error(msg);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop();               // last piece may be a partial frame — keep it
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith('data:')) continue;
      const payload = line.slice('data:'.length).trim();
      if (payload === '[DONE]') return;
      let obj;
      try { obj = JSON.parse(payload); } catch { continue; }
      if (obj.sources) bot.showSources(obj.sources);   // arrives first (from l06-rag)
      if (obj.token) bot.appendToken(obj.token);
      if (obj.error) bot.error(obj.error);
    }
  }
});
