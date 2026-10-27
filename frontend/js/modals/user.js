// ═══════════════════════════════════
// MODAL: User
// ═══════════════════════════════════

// Admin: create new user
function mUser() {
  showModal(`
    ${mhdr('Nuevo Usuario','Crear una cuenta de usuario')}
    <form onsubmit="saveNewUser(event)">
      <div class="mb-3">
        <label class="lbl">Nombre</label>
        <input name="name" class="inp" placeholder="ej. Alice Martín" required>
      </div>
      <div class="mb-3">
        <label class="lbl">Email</label>
        <input name="email" type="email" class="inp" placeholder="alice@empresa.com" required>
      </div>
      <div class="mb-3">
        <label class="lbl">Contraseña</label>
        <input name="password" type="password" class="inp" placeholder="mín. 6 caracteres" required minlength="6">
      </div>
      <div class="mb-1">
        <label class="lbl">URL de Avatar</label>
        <input name="avatar_url" class="inp" placeholder="https://...">
      </div>
      ${mfoot('Crear Usuario', false)}
    </form>`);
}

async function saveNewUser(e) {
  e.preventDefault();
  const f = e.target;
  const b = { name: f.name.value, email: f.email.value, password: f.password.value, avatar_url: f.avatar_url.value||null };
  try {
    await POST('/users/', b);
    closeM(); await loadAll(); render(); toast('Usuario creado');
  } catch(err) { toast(err.message,'err'); }
}

// Current user: edit own profile
function mEditProfile() {
  const u = S.currentUser;
  if (!u) return;
  showModal(`
    ${mhdr('Mi Perfil','Actualiza tu información')}
    <form onsubmit="saveProfile(event,${u.id})">
      <div class="mb-3">
        <label class="lbl">Nombre</label>
        <input name="name" class="inp" value="${esc(u.name)}" required>
      </div>
      <div class="mb-3">
        <label class="lbl">Email</label>
        <input name="email" type="email" class="inp" value="${esc(u.email)}" required>
      </div>
      <div class="mb-3">
        <label class="lbl">Nueva contraseña</label>
        <input name="password" type="password" class="inp" placeholder="Dejar vacío para no cambiar" minlength="6">
      </div>
      <div class="mb-1">
        <label class="lbl">URL de Avatar</label>
        <input name="avatar_url" class="inp" placeholder="https://..." value="${esc(u.avatar_url||'')}">
      </div>
      ${mfoot('Guardar', false)}
    </form>`);
}

async function saveProfile(e, userId) {
  e.preventDefault();
  const f = e.target;
  const b = {};
  if (f.name.value)     b.name = f.name.value;
  if (f.email.value)    b.email = f.email.value;
  if (f.password.value) b.password = f.password.value;
  b.avatar_url = f.avatar_url.value || null;
  try {
    const updated = await PATCH(`/users/${userId}`, b);
    saveAuth(getToken(), updated);
    closeM(); await loadAll(); render(); toast('Perfil actualizado');
  } catch(err) { toast(err.message,'err'); }
}

// Admin: edit any user
function mAdminEditUser(userId) {
  const u = S.users.find(x=>x.id===userId);
  if (!u) return;
  const isMe = S.currentUser?.id === userId;
  showModal(`
    ${mhdr(isMe ? 'Mi Perfil' : `Editar Usuario`, isMe ? 'Tu cuenta de administrador' : esc(u.email))}
    <form onsubmit="saveAdminUser(event,${userId})">
      <div class="mb-3">
        <label class="lbl">Nombre</label>
        <input name="name" class="inp" value="${esc(u.name)}" required>
      </div>
      <div class="mb-3">
        <label class="lbl">Email</label>
        <input name="email" type="email" class="inp" value="${esc(u.email)}" required>
      </div>
      <div class="mb-3">
        <label class="lbl">Nueva contraseña</label>
        <input name="password" type="password" class="inp" placeholder="Dejar vacío para no cambiar" minlength="6">
      </div>
      <div class="mb-3">
        <label class="lbl">URL de Avatar</label>
        <input name="avatar_url" class="inp" placeholder="https://..." value="${esc(u.avatar_url||'')}">
      </div>
      <div class="mb-4 px-1">
        <div class="flex items-center gap-3">
          <input type="checkbox" name="is_admin" id="chk-adm-${userId}" class="w-4 h-4 accent-primary ${isMe?'cursor-not-allowed opacity-50':'cursor-pointer'}" ${u.is_admin?'checked':''} ${isMe?'disabled':''}>
          <label for="chk-adm-${userId}" class="text-sm ${isMe?'text-slate-500 cursor-not-allowed':'text-slate-300 cursor-pointer'} flex items-center gap-1.5">
            <span class="ms ms-sm" style="color:${isMe?'#6b7280':'#A78BFA'}">shield</span>Administrador de plataforma
          </label>
        </div>
        ${isMe ? `<p class="text-xs text-slate-600 mt-1.5 pl-7">No puedes retirar tus propios privilegios de administrador.</p>` : ''}
      </div>
      ${mfoot('Guardar', false)}
    </form>`);
}

async function saveAdminUser(e, userId) {
  e.preventDefault();
  const f = e.target;
  const b = {};
  if (f.name.value)     b.name = f.name.value;
  if (f.email.value)    b.email = f.email.value;
  if (f.password.value) b.password = f.password.value;
  b.avatar_url = f.avatar_url.value || null;
  if (userId !== S.currentUser?.id) b.is_admin = f.is_admin.checked;
  try {
    const updated = await PATCH(`/users/${userId}`, b);
    if (userId === S.currentUser?.id) saveAuth(getToken(), updated);
    closeM(); await loadAll(); render(); toast('Usuario actualizado');
  } catch(err) { toast(err.message,'err'); }
}

// Admin: cascade delete user (with preview)
async function confirmDelUser(userId) {
  showModal(`<div class="flex items-center justify-center py-6"><div class="spin"></div></div>`);
  try {
    const preview = await GET(`/admin/users/${userId}/deletion-preview`);
    const u = preview.user;
    const t = preview.totals;
    const hasProjects = t.projects > 0;

    const projectRows = preview.projects.map(p => `
      <div class="rounded-xl px-3 py-2.5 mb-1.5" style="background:rgba(239,68,68,.06);border:1px solid rgba(239,68,68,.15)">
        <div class="text-sm font-medium text-white mb-1">${esc(p.name)}</div>
        <div class="flex flex-wrap gap-2 text-xs text-slate-400">
          <span><span class="ms ms-xs" style="vertical-align:middle">view_column</span> ${p.groups_count} grupos</span>
          <span><span class="ms ms-xs" style="vertical-align:middle">task_alt</span> ${p.tasks_count} tareas</span>
          <span><span class="ms ms-xs" style="vertical-align:middle">label</span> ${p.tags_count} etiquetas</span>
          <span><span class="ms ms-xs" style="vertical-align:middle">flag</span> ${p.priorities_count} prioridades</span>
          <span><span class="ms ms-xs" style="vertical-align:middle">group</span> ${p.members_count} miembros</span>
        </div>
      </div>`).join('');

    showModal(`
      <div class="text-center mb-4">
        <div class="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-3" style="background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.2)">
          <span class="ms" style="font-size:28px;color:#EF4444">delete_forever</span>
        </div>
        <h2 class="text-base font-bold text-white">Eliminar usuario</h2>
        <p class="text-sm text-slate-400 mt-1">
          <strong class="text-white">${esc(u.name)}</strong>
          <span class="text-slate-600 mx-1">·</span>${esc(u.email)}
        </p>
      </div>
      ${hasProjects ? `
        <div class="mb-4">
          <div class="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">
            Se eliminarán ${t.projects} proyecto${t.projects>1?'s':''} y todo su contenido
          </div>
          ${projectRows}
          <div class="mt-2 text-xs text-slate-500 text-center">
            Total: ${t.groups} grupos de tareas · ${t.tasks} tareas · ${t.tags} etiquetas · ${t.priorities} prioridades
          </div>
        </div>` : `
        <p class="text-sm text-slate-400 text-center mb-4">Este usuario no tiene proyectos propios.</p>`}
      <form onsubmit="execCascadeDelete(event,${userId})">
        <div class="mb-4">
          <label class="lbl">Confirma con tu contraseña de administrador</label>
          <input name="admin_password" type="password" class="inp" placeholder="Tu contraseña" required autofocus>
        </div>
        <div class="flex gap-3">
          <button type="button" class="btn btn-ghost flex-1 justify-center" onclick="closeM()">Cancelar</button>
          <button type="submit" class="btn btn-danger flex-1 justify-center">
            <span class="ms ms-sm">delete_forever</span>Eliminar todo
          </button>
        </div>
      </form>`);
  } catch(err) { closeM(); toast(err.message, 'err'); }
}

async function execCascadeDelete(e, userId) {
  e.preventDefault();
  const password = e.target.admin_password.value;
  try {
    await req('DELETE', `/admin/users/${userId}/cascade`, {admin_password: password});
    closeM(); await loadAll(); render(); toast('Usuario eliminado');
  } catch(err) { toast(err.message, 'err'); }
}
