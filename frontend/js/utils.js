// ═══════════════════════════════════
// UTILS
// ═══════════════════════════════════
function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
// Encode a value as a JS string literal safe to embed in a double-quoted HTML attribute.
// JSON.stringify produces a double-quoted string so single quotes never need escaping here;
// escaping them would corrupt the value seen by the JS engine.
// Usage: onclick="fn(${jsq(name)})"  →  onclick="fn(&quot;safe value&quot;)"
function jsq(s) {
  return JSON.stringify(String(s||'')).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function inits(n) { return n.split(' ').map(w=>w[0]).slice(0,2).join('').toUpperCase(); }
function hashCol(n) {
  const cs=['#F97316','#EF4444','#8B5CF6','#3B82F6','#10B981','#F59E0B','#EC4899','#14B8A6'];
  let h=0; for (const c of n) h=((h<<5)-h)+c.charCodeAt(0);
  return cs[Math.abs(h)%cs.length];
}
function avatar(r, size) {
  const sz = size==='sm' ? 'width:22px;height:22px;font-size:9px' : 'width:30px;height:30px;font-size:11px';
  const bd = 'border:1.5px solid rgba(249,115,22,.25);border-radius:50%;object-fit:cover;flex-shrink:0';
  if (r.avatar_url) return `<img src="${esc(r.avatar_url)}" style="${sz};${bd}" title="${esc(r.name)}">`;
  return `<div style="${sz};${bd};background:${hashCol(r.name)};display:flex;align-items:center;justify-content:center;font-weight:700;color:#fff" title="${esc(r.name)}">${inits(r.name)}</div>`;
}
function toast(msg, type='ok') {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = `<span class="ms ms-sm">${type==='ok'?'check_circle':'error'}</span>${esc(msg)}`;
  document.getElementById('toasts').appendChild(el);
  setTimeout(()=>el.remove(), 3500);
}
function emptyState(icon, title, desc) {
  return `<div class="flex flex-col items-center justify-center h-full text-center px-4">
    <span class="ms mb-3" style="font-size:42px;color:#1e2d44">${icon}</span>
    <div class="text-white font-semibold mb-1">${title}</div>
    <div class="text-sm text-slate-500">${desc}</div>
  </div>`;
}
