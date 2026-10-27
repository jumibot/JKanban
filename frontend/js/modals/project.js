// ═══════════════════════════════════
// MODAL: Project
// ═══════════════════════════════════
async function mProject(id) {
  const p = id ? S.projects.find(x=>x.id===id) : null;
  const col = p?.color||'#3B82F6', ic = p?.icon||'rocket_launch';
  // Load project-scoped priorities when editing an existing project
  const projPriorities = id
    ? await GET(`/projects/${id}/priorities/`).catch(() => [])
    : [];
  showModal(`
    ${mhdr(p?'Editar Proyecto':'Nuevo Proyecto','Define los parámetros del proyecto')}
    <form onsubmit="saveProject(event,${id||'null'})">
      <input type="hidden" name="color" value="${col}">
      <input type="hidden" name="icon"  value="${ic}">
      <div class="grid grid-cols-2 gap-3 mb-3">
        <div class="col-span-2">
          <label class="lbl">Nombre</label>
          <input name="name" class="inp" placeholder="ej. Quantum Engine V2" value="${esc(p?.name||'')}" required>
        </div>
        <div>
          <label class="lbl">Team Leader</label>
          <select name="leader_id" class="inp">
            <option value="">Sin líder</option>
            ${S.users.map(u=>`<option value="${u.id}" ${p?.leader?.id===u.id?'selected':''}>${esc(u.name)}</option>`).join('')}
          </select>
        </div>
        <div>
          <label class="lbl">Prioridad</label>
          <select name="priority_id" class="inp">
            <option value="">Sin prioridad</option>
            ${projPriorities.map(x=>`<option value="${x.id}" ${p?.priority?.id===x.id?'selected':''}>${esc(x.name)}</option>`).join('')}
          </select>
          ${!id ? `<div class="text-xs text-slate-600 mt-1">Crea prioridades desde el tablero del proyecto</div>` : ''}
        </div>
      </div>
      <div class="mb-3">
        <label class="lbl">Icono</label>
        ${iconGrid(ic,'icon')}
      </div>
      <div class="mb-3">
        <label class="lbl">Color</label>
        ${swatches(col,'color')}
      </div>
      <div class="mb-1">
        <label class="lbl">Descripción</label>
        <textarea name="description" class="inp" rows="2" placeholder="Objetivo del proyecto...">${esc(p?.description||'')}</textarea>
      </div>
      ${mfoot(p?'Guardar':'Crear Proyecto', !!p && p.owner?.id===S.currentUser?.id, `confirmCascadeDelProject(${id});closeM()`)}
    </form>`);
}

async function saveProject(e, id) {
  e.preventDefault();
  const f = e.target;
  const b = {
    name: f.name.value, description: f.description.value||null,
    icon: f.icon.value, color: f.color.value,
    leader_id: f.leader_id.value ? +f.leader_id.value : null,
    priority_id: f.priority_id.value ? +f.priority_id.value : null,
  };
  try {
    id ? await PATCH(`/projects/${id}`,b) : await POST('/projects/',b);
    closeM(); await loadAll(); render(); toast(id?'Proyecto actualizado':'Proyecto creado');
  } catch(err) { toast(err.message,'err'); }
}

// ── Project Team Modal ────────────
async function mProjectTeam(projId) {
  const p = S.projects.find(x=>x.id===projId);
  const members = await GET(`/projects/${projId}/members`).catch(()=>[]);
  const memberIds = new Set(members.map(m=>m.id));
  const nonMembers = S.users.filter(u=>!memberIds.has(u.id) && u.id!==p?.owner?.id && u.id!==p?.leader?.id);

  showModal(`
    ${mhdr('Equipo del Proyecto', esc(p?.name||''))}
    <div class="mb-4">
      <div class="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">Owner</div>
      ${p?.owner ? `<div class="flex items-center gap-2.5 px-3 py-2 rounded-xl" style="background:rgba(249,115,22,.07)">
        ${avatar(p.owner)}
        <div>
          <div class="text-sm font-medium text-white">${esc(p.owner.name)}</div>
          <div class="text-xs text-slate-500">${esc(p.owner.email)}</div>
        </div>
        <span class="ml-auto text-xs px-2 py-0.5 rounded-full font-semibold" style="background:rgba(249,115,22,.15);color:#F97316">Owner</span>
      </div>` : ''}
    </div>
    ${p?.leader ? `<div class="mb-4">
      <div class="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">Líder</div>
      <div class="flex items-center gap-2.5 px-3 py-2 rounded-xl" style="background:rgba(59,130,246,.07)">
        ${avatar(p.leader)}
        <div>
          <div class="text-sm font-medium text-white">${esc(p.leader.name)}</div>
          <div class="text-xs text-slate-500">${esc(p.leader.email)}</div>
        </div>
        <span class="ml-auto text-xs px-2 py-0.5 rounded-full font-semibold" style="background:rgba(59,130,246,.15);color:#3B82F6">Líder</span>
      </div>
    </div>` : ''}
    <div class="mb-4">
      <div class="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">Miembros (${members.length})</div>
      <div id="pt-members" class="flex flex-col gap-1.5">
        ${members.length ? members.map(m=>`
          <div class="flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-white/5 transition-all">
            ${avatar(m)}
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-white truncate">${esc(m.name)}</div>
              <div class="text-xs text-slate-500 truncate">${esc(m.email)}</div>
            </div>
            <button class="btn-icon" style="color:#6b7280" onmouseenter="this.style.color='#f87171'" onmouseleave="this.style.color='#6b7280'"
              onclick="removeMember(${projId},${m.id})"><span class="ms ms-sm">person_remove</span></button>
          </div>`).join('') : '<div class="text-xs text-slate-600 px-3 py-2">Sin miembros asignados</div>'}
      </div>
    </div>
    ${nonMembers.length ? `<div>
      <div class="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">Añadir miembro</div>
      <div class="flex gap-2">
        <select id="pt-sel" class="inp flex-1">
          <option value="">Seleccionar usuario...</option>
          ${nonMembers.map(u=>`<option value="${u.id}">${esc(u.name)} — ${esc(u.email)}</option>`).join('')}
        </select>
        <button class="btn btn-primary py-2 px-3" onclick="addMember(${projId}, +document.getElementById('pt-sel').value)"><span class="ms ms-sm">person_add</span></button>
      </div>
    </div>` : ''}
    <div class="flex justify-end mt-5">
      <button class="btn btn-ghost" onclick="closeM()">Cerrar</button>
    </div>`);
}

async function addMember(projId, userId) {
  if (!userId) return;
  try {
    await POST(`/projects/${projId}/members/${userId}`);
    await Promise.all([loadAll(), loadMembers()]);
    render(); toast('Miembro añadido');
  } catch(err) { toast(err.message,'err'); }
}

async function removeMember(projId, userId) {
  try {
    await DEL(`/projects/${projId}/members/${userId}`);
    await Promise.all([loadAll(), loadMembers()]);
    render(); toast('Miembro eliminado');
  } catch(err) { toast(err.message,'err'); }
}

// ── Project context menu ──────────
function mProjectMenu(id) {
  const p = S.projects.find(x=>x.id===id);
  const isOwner = p && S.currentUser && p.owner?.id === S.currentUser.id;
  showModal(`
    <div class="flex items-center justify-between mb-4">
      <h3 class="font-semibold text-white">${esc(p?.name||'')}</h3>
      <button class="btn-icon" onclick="closeM()"><span class="ms ms-sm">close</span></button>
    </div>
    <div class="flex flex-col gap-1">
      <button class="flex items-center gap-3 p-3 rounded-xl text-slate-300 hover:text-white hover:bg-white/5 transition-all text-sm" onclick="closeM();go('#/board/${id}')">
        <span class="ms ms-sm" style="color:#F97316">view_kanban</span>Abrir tablero
      </button>
      <button class="flex items-center gap-3 p-3 rounded-xl text-slate-300 hover:text-white hover:bg-white/5 transition-all text-sm" onclick="closeM();mProject(${id})">
        <span class="ms ms-sm" style="color:#F97316">edit</span>Editar proyecto
      </button>
      <button class="flex items-center gap-3 p-3 rounded-xl text-slate-300 hover:text-white hover:bg-white/5 transition-all text-sm" onclick="closeM();mProjectTeam(${id})">
        <span class="ms ms-sm" style="color:#3B82F6">group</span>Gestionar equipo
      </button>
      ${isOwner ? `
      <div class="border-t my-1" style="border-color:rgba(255,255,255,.06)"></div>
      <button class="flex items-center gap-3 p-3 rounded-xl text-red-400 hover:bg-red-500/10 transition-all text-sm" onclick="closeM();confirmCascadeDelProject(${id})">
        <span class="ms ms-sm">delete_forever</span>Eliminar proyecto
      </button>` : ''}
    </div>`);
}
