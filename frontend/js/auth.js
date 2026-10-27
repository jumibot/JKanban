// ═══════════════════════════════════
// AUTH
// ═══════════════════════════════════
const _TK = 'jk_token', _UK = 'jk_user';

function getToken() { return localStorage.getItem(_TK); }

function saveAuth(token, user) {
  localStorage.setItem(_TK, token);
  localStorage.setItem(_UK, JSON.stringify(user));
  S.currentUser = user;
}

function clearAuth() {
  localStorage.removeItem(_TK);
  localStorage.removeItem(_UK);
  S.currentUser = null;
}

function loadStoredUser() {
  try {
    const u = localStorage.getItem(_UK);
    if (u) S.currentUser = JSON.parse(u);
  } catch(_) {}
}

function showApp() {
  document.getElementById('auth-wall').style.display = 'none';
  document.getElementById('app').style.removeProperty('display');
}

function showAuthWall() {
  document.getElementById('app').style.setProperty('display','none','important');
  document.getElementById('auth-wall').style.display = 'flex';
}

function awToggle(showRegister) {
  document.getElementById('aw-login').style.display    = showRegister ? 'none' : '';
  document.getElementById('aw-register').style.display = showRegister ? '' : 'none';
  awErr('');
}

function awErr(msg) {
  const el = document.getElementById('aw-err');
  if (!msg) { el.style.display='none'; return; }
  el.style.display = '';
  el.style.background = 'rgba(239,68,68,.13)';
  el.style.border = '1px solid rgba(239,68,68,.28)';
  el.style.color = '#fca5a5';
  el.style.padding = '.6rem .85rem';
  el.style.borderRadius = '.75rem';
  el.style.fontSize = '.82rem';
  el.textContent = msg;
}

async function doLogin(e) {
  e.preventDefault();
  awErr('');
  const email    = document.getElementById('aw-email').value;
  const password = document.getElementById('aw-pass').value;
  try {
    const d = await fetch('/auth/login', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({email, password}),
    });
    const body = await d.json();
    if (!d.ok) throw new Error(body.detail || 'Credenciales incorrectas');
    saveAuth(body.access_token, body.user);
    showApp();
    await loadAll();
    await route();
  } catch(err) { awErr(err.message); }
}

async function doRegister(e) {
  e.preventDefault();
  awErr('');
  const name     = document.getElementById('aw-rname').value;
  const email    = document.getElementById('aw-remail').value;
  const password = document.getElementById('aw-rpass').value;
  try {
    const d = await fetch('/users/', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({name, email, password}),
    });
    const body = await d.json();
    if (!d.ok) throw new Error(Array.isArray(body.detail) ? body.detail[0]?.msg : (body.detail || 'Error al registrarse'));
    // Auto-login after register
    const d2 = await fetch('/auth/login', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({email, password}),
    });
    const body2 = await d2.json();
    if (!d2.ok) throw new Error(body2.detail || 'Error al iniciar sesión');
    saveAuth(body2.access_token, body2.user);
    showApp();
    await loadAll();
    await route();
  } catch(err) { awErr(err.message); }
}

function doLogout() {
  clearAuth();
  showAuthWall();
  // Reset state — clear all in-memory data including project-scoped collections
  S.projects=[]; S.groups=[]; S.tasks=[]; S.users=[];
  S.tags=[]; S.priorities=[]; S.members=[];
  S.view='dashboard'; S.pid=null; S.subview='kanban'; S.currentUser=null;
  location.hash='#/';
}
