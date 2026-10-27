// ═══════════════════════════════════
// VIEW: Team
// ═══════════════════════════════════

// Project team subview (inside board)
function vProjectTeam() {
  const p = S.projects.find(x => x.id === S.pid);
  const cu = S.currentUser;
  const canManage = cu && p && (cu.id === p.owner?.id || cu.id === p.leader?.id);
  const memberIds = new Set(S.members.map(m => m.id));
  const nonMembers = S.users.filter(u => !memberIds.has(u.id) && u.id !== p?.owner?.id && u.id !== p?.leader?.id);

  const roleCard = (user, role, roleColor) => `
    <div class="glass-card rounded-2xl p-4 flex items-center justify-between" style="border-color:${roleColor}28">
      <div class="flex items-center gap-3">
        ${avatar(user)}
        <div class="min-w-0">
          <div class="text-sm font-medium text-white truncate">${esc(user.name)}</div>
          <div class="text-xs text-slate-500 truncate">${esc(user.email)}</div>
        </div>
      </div>
      <span class="text-xs px-2 py-0.5 rounded-full font-semibold flex-shrink-0" style="background:${roleColor}18;color:${roleColor}">${role}</span>
    </div>`;

  return `<div class="p-6 space-y-6">
    <div>
      <div class="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-3">Propietario</div>
      ${p?.owner ? roleCard(p.owner, 'Owner', '#F97316') : ''}
    </div>
    ${p?.leader && p.leader.id !== p?.owner?.id ? `<div>
      <div class="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-3">Líder</div>
      ${roleCard(p.leader, 'Líder', '#3B82F6')}
    </div>` : ''}
    <div>
      <div class="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-3">Miembros (${S.members.length})</div>
      ${S.members.length ? `<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        ${S.members.map(m=>`<div class="glass-card rounded-2xl p-4 flex items-center justify-between">
          <div class="flex items-center gap-3">
            ${avatar(m)}
            <div class="min-w-0">
              <div class="text-sm font-medium text-white truncate">${esc(m.name)}</div>
              <div class="text-xs text-slate-500 truncate">${esc(m.email)}</div>
            </div>
          </div>
          ${canManage ? `<button class="btn-icon flex-shrink-0" style="color:#6b7280" onmouseenter="this.style.color='#f87171'" onmouseleave="this.style.color='#6b7280'" onclick="removeMember(${S.pid},${m.id})"><span class="ms ms-sm">person_remove</span></button>` : ''}
        </div>`).join('')}
      </div>` : `<p class="text-sm text-slate-600">Sin miembros asignados.</p>`}
    </div>
    ${canManage && nonMembers.length ? `<div>
      <div class="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-3">Añadir miembro</div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        ${nonMembers.map(u=>`<div class="glass-card rounded-2xl p-4 flex items-center justify-between">
          <div class="flex items-center gap-3">
            ${avatar(u)}
            <div class="min-w-0">
              <div class="text-sm font-medium text-white truncate">${esc(u.name)}</div>
              <div class="text-xs text-slate-500 truncate">${esc(u.email)}</div>
            </div>
          </div>
          <button class="btn-icon flex-shrink-0" style="color:#64748b" onmouseenter="this.style.color='#F97316'" onmouseleave="this.style.color='#64748b'" onclick="addMember(${S.pid},${u.id})"><span class="ms ms-sm">person_add</span></button>
        </div>`).join('')}
      </div>
    </div>` : ''}
  </div>`;
}

// Admin users panel (top-level team view)
function vTeam() {
  const cu = S.currentUser;
  if (!cu?.is_admin) return emptyState('lock','Acceso restringido','Solo los administradores pueden gestionar usuarios.');
  if (!S.users.length) return emptyState('group','Sin usuarios','Aún no hay usuarios registrados.');
  return `<div class="p-6">
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
    ${S.users.map(u=>`<div class="glass-card rounded-2xl p-4 flex items-center justify-between ${u.id===cu.id?'border border-primary/20':''}">
      <div class="flex items-center gap-3">
        ${u.avatar_url
          ? `<img src="${esc(u.avatar_url)}" class="w-10 h-10 rounded-full object-cover flex-shrink-0" style="border:2px solid rgba(249,115,22,.28)">`
          : `<div class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white flex-shrink-0" style="background:${hashCol(u.name)};border:2px solid rgba(249,115,22,.28)">${inits(u.name)}</div>`}
        <div class="min-w-0">
          <div class="flex items-center gap-1.5 flex-wrap">
            <div class="text-sm font-medium text-white">${esc(u.name)}</div>
            ${u.id===cu.id?'<span class="tag-chip" style="background:rgba(249,115,22,.15);color:#F97316">Tú</span>':''}
            ${u.is_admin?'<span class="tag-chip" style="background:rgba(139,92,246,.15);color:#A78BFA"><span class="ms ms-xs" style="font-size:11px">shield</span>Admin</span>':''}
          </div>
          <div class="text-xs text-slate-500 truncate">${esc(u.email)}</div>
        </div>
      </div>
      <div class="flex gap-0.5 flex-shrink-0">
        <button class="btn-icon" title="Editar" onclick="mAdminEditUser(${u.id})"><span class="ms ms-sm">edit</span></button>
        ${u.id!==cu.id?`<button class="btn-icon" style="color:#6b7280" title="Eliminar" onmouseenter="this.style.color='#f87171'" onmouseleave="this.style.color='#6b7280'" onclick="confirmDelUser(${u.id})"><span class="ms ms-sm">delete</span></button>`:''}
      </div>
    </div>`).join('')}
    </div>
  </div>`;
}
