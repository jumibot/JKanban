// ═══════════════════════════════════
// VIEW: Priorities (project-scoped)
// ═══════════════════════════════════
function vProjectPriorities() {
  const p = S.projects.find(x => x.id === S.pid);
  const cu = S.currentUser;
  const canManage = cu && p && (cu.id === p.owner?.id || cu.id === p.leader?.id);
  if (!S.priorities.length) return `<div class="flex flex-col items-center justify-center h-full gap-4 text-center px-4">
    <span class="ms mb-1" style="font-size:42px;color:#1e2d44">flag</span>
    <div class="text-white font-semibold">Sin prioridades</div>
    <div class="text-sm text-slate-500">${canManage ? 'Crea la primera prioridad para tus tareas.' : 'Este proyecto no tiene prioridades aún.'}</div>
    ${canManage ? `<button class="btn btn-primary" onclick="mPriority()"><span class="ms ms-sm">add</span>Nueva Prioridad</button>` : ''}
  </div>`;
  return `<div class="p-6"><div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
    ${S.priorities.map(pr=>`<div class="glass-card rounded-2xl p-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-xl flex items-center justify-center" style="background:${pr.color}1a;border:1px solid ${pr.color}28">
          <span class="ms" style="font-size:18px;color:${pr.color}">${pr.icon}</span>
        </div>
        <div>
          <div class="text-sm font-medium text-white">${esc(pr.name)}</div>
          <div class="text-xs text-slate-600">${pr.color}</div>
        </div>
      </div>
      ${canManage ? `<div class="flex gap-0.5">
        <button class="btn-icon" onclick="mPriority(${pr.id})"><span class="ms ms-sm">edit</span></button>
        <button class="btn-icon" style="color:#6b7280" onmouseenter="this.style.color='#f87171'" onmouseleave="this.style.color='#6b7280'" onclick="confirmDel('priority',${pr.id})"><span class="ms ms-sm">delete</span></button>
      </div>` : ''}
    </div>`).join('')}
    ${canManage ? `<button class="glass-card rounded-2xl p-4 flex items-center justify-center gap-2 text-slate-600 hover:text-primary hover:border-primary/25 transition-all text-sm font-medium" style="border:2px dashed rgba(100,116,139,.18)" onclick="mPriority()">
      <span class="ms ms-sm">add</span>Nueva Prioridad
    </button>` : ''}
  </div></div>`;
}

// Standalone priorities view (legacy/unused — kept for completeness)
function vPriorities() {
  if (!S.priorities.length) return emptyState('flag','Sin prioridades','Crea prioridades personalizadas para tus tareas.');
  return `<div class="p-6"><div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
    ${S.priorities.map(p=>`<div class="glass-card rounded-2xl p-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-xl flex items-center justify-center" style="background:${p.color}1a;border:1px solid ${p.color}28">
          <span class="ms" style="font-size:18px;color:${p.color}">${p.icon}</span>
        </div>
        <div>
          <div class="text-sm font-medium text-white">${esc(p.name)}</div>
          <div class="text-xs text-slate-600">${p.color}</div>
        </div>
      </div>
      <div class="flex gap-0.5">
        <button class="btn-icon" onclick="mPriority(${p.id})"><span class="ms ms-sm">edit</span></button>
        <button class="btn-icon" style="color:#6b7280" onmouseenter="this.style.color='#f87171'" onmouseleave="this.style.color='#6b7280'" onclick="confirmDel('priority',${p.id})"><span class="ms ms-sm">delete</span></button>
      </div>
    </div>`).join('')}
  </div></div>`;
}
