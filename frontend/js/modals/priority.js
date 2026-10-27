// ═══════════════════════════════════
// MODAL: Priority
// ═══════════════════════════════════

// Project priorities list modal (used from project context menu)
function mProjectPriorities(pid) {
  const p = S.projects.find(x => x.id === pid);
  const cu = S.currentUser;
  const canManage = cu && p && (cu.id === p.owner?.id || cu.id === p.leader?.id);
  const rows = S.priorities.length
    ? S.priorities.map(pr => `
        <div class="flex items-center justify-between py-2.5 border-b" style="border-color:rgba(255,255,255,.06)">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0" style="background:${pr.color}1a;border:1px solid ${pr.color}28">
              <span class="ms" style="font-size:16px;color:${pr.color}">${pr.icon}</span>
            </div>
            <div>
              <div class="text-sm text-white font-medium">${esc(pr.name)}</div>
              <div class="text-xs text-slate-600">${pr.color}</div>
            </div>
          </div>
          ${canManage ? `<div class="flex gap-0.5">
            <button class="btn-icon" onclick="closeM();mPriority(${pr.id})"><span class="ms ms-sm">edit</span></button>
            <button class="btn-icon" style="color:#6b7280" onmouseenter="this.style.color='#f87171'" onmouseleave="this.style.color='#6b7280'" onclick="closeM();confirmDel('priority',${pr.id})"><span class="ms ms-sm">delete</span></button>
          </div>` : ''}
        </div>`).join('')
    : `<p class="text-slate-500 text-sm text-center py-6">${canManage ? 'Sin prioridades. Crea la primera.' : 'Este proyecto no tiene prioridades aún.'}</p>`;
  showModal(`
    ${mhdr('Prioridades', esc(p?.name||''))}
    <div class="max-h-64 overflow-y-auto -mx-5 px-5">${rows}</div>
    ${canManage ? `<button class="btn btn-primary w-full mt-4" onclick="closeM();mPriority()"><span class="ms ms-sm">add</span>Nueva Prioridad</button>` : ''}`);
}

// Priority create/edit modal
function mPriority(id) {
  const p = id ? S.priorities.find(x=>x.id===id) : null;
  const col = p?.color||'#F97316', ic = p?.icon||'flag';
  showModal(`
    ${mhdr(p?'Editar Prioridad':'Nueva Prioridad')}
    <form onsubmit="savePriority(event,${id||'null'})">
      <input type="hidden" name="color" value="${col}">
      <input type="hidden" name="icon"  value="${ic}">
      <div class="mb-3">
        <label class="lbl">Nombre</label>
        <input name="name" class="inp" placeholder="ej. Crítico" value="${esc(p?.name||'')}" required>
      </div>
      <div class="mb-3">
        <label class="lbl">Icono</label>
        ${iconGrid(ic,'icon')}
      </div>
      <div class="mb-1">
        <label class="lbl">Color</label>
        ${swatches(col,'color')}
      </div>
      ${mfoot(p?'Guardar':'Crear Prioridad', false)}
    </form>`);
}

async function savePriority(e, id) {
  e.preventDefault();
  const f = e.target;
  const b = { name: f.name.value, icon: f.icon.value, color: f.color.value };
  try {
    id
      ? await PATCH(`/projects/${S.pid}/priorities/${id}`, b)
      : await POST(`/projects/${S.pid}/priorities/`, b);
    closeM(); await loadAll(); render(); toast(id?'Prioridad actualizada':'Prioridad creada');
  } catch(err) { toast(err.message,'err'); }
}
