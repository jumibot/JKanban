// ═══════════════════════════════════
// API
// ═══════════════════════════════════
async function req(method, path, body) {
  const o = {method, headers:{}};
  const token = getToken();
  if (token) o.headers['Authorization'] = `Bearer ${token}`;
  if (body !== undefined) { o.headers['Content-Type']='application/json'; o.body=JSON.stringify(body); }
  const r = await fetch(path, o);
  if (r.status === 401) {
    clearAuth(); showAuthWall();
    throw new Error('Sesión expirada. Por favor inicia sesión de nuevo.');
  }
  if (r.status === 204) return null;
  const d = await r.json();
  if (!r.ok) throw new Error(d.detail || 'Error en el servidor');
  return d;
}
const GET  = p      => req('GET',    p);
const POST = (p,b)  => req('POST',   p, b);
const PATCH= (p,b)  => req('PATCH',  p, b);
const DEL  = p      => req('DELETE', p);

async function loadAll() {
  [S.projects, S.groups, S.tasks, S.users] = await Promise.all([
    GET('/projects/'), GET('/groups/'), GET('/tasks/'), GET('/users/'),
  ]);
  // Tags, flows and priorities of the open project (tags and flows include the global ones)
  if (S.pid) {
    await loadProjectMeta();
  } else {
    S.tags = []; S.priorities = []; S.flows = [];
  }
  if (S.view === 'globals') await loadGlobals();
}

async function loadProjectMeta() {
  const [tags, priorities, flows] = await Promise.all([
    GET(`/projects/${S.pid}/tags/`).catch(() => []),
    GET(`/projects/${S.pid}/priorities/`).catch(() => []),
    GET(`/projects/${S.pid}/flows/`).catch(() => []),
  ]);
  S.tags = tags; S.priorities = priorities; S.flows = flows;
}

// Global flows and tags (admin panel).
async function loadGlobals() {
  [S.gflows, S.gtags] = await Promise.all([GET('/flows/'), GET('/tags/')]);
}

async function loadMembers() {
  S.members = S.pid ? await GET(`/projects/${S.pid}/members`).catch(() => []) : [];
}
