// ═══════════════════════════════════
// VIEW: Dashboard
// ═══════════════════════════════════
function vDashboard() {
  // Precompute in O(G + T) so each projCard renders in O(1)
  const groupPid    = new Map(S.groups.map(g => [g.id, g.project_id]));
  const groupCounts = new Map();
  for (const g of S.groups) groupCounts.set(g.project_id, (groupCounts.get(g.project_id) ?? 0) + 1);
  const taskStats = new Map(); // projectId -> {total, done}
  for (const t of S.tasks) {
    const pid = groupPid.get(t.group_id);
    if (pid == null) continue;
    const s = taskStats.get(pid) ?? {total: 0, done: 0};
    s.total++;
    if (t.completed) s.done++;
    taskStats.set(pid, s);
  }

  if (!S.projects.length) return `
    <div class="flex flex-col items-center justify-center h-full text-center px-4">
      <div class="w-20 h-20 rounded-2xl flex items-center justify-center mb-5" style="background:rgba(249,115,22,.1);border:1px solid rgba(249,115,22,.18)">
        <span class="ms" style="font-size:40px;color:#F97316">rocket_launch</span>
      </div>
      <h1 class="text-3xl font-extrabold text-white mb-2">¿Listo para tu primer<br><span style="color:#F97316">proyecto?</span></h1>
      <p class="text-slate-500 max-w-sm mb-7 text-sm leading-relaxed">Crea tu primer proyecto y empieza a organizar tareas con precisión.</p>
      <button class="btn btn-primary py-3 px-7 text-base" onclick="mProject()"><span class="ms">add</span>Crear Primer Proyecto</button>
      <div class="grid grid-cols-3 gap-3 mt-14 max-w-xl w-full">
        ${[['Escalabilidad','hub','Gestiona flujos complejos sin desorden.'],
           ['Organización','drag_pan','Grupos de tareas personalizados por proyecto.'],
           ['Precisión','memory','Fechas, duraciones, prioridades y más.']
          ].map(([t,ic,d])=>`<div class="glass-card rounded-2xl p-4 text-left">
            <span class="ms mb-2 block" style="color:#F97316;font-size:22px">${ic}</span>
            <div class="text-sm font-semibold text-white mb-1">${t}</div>
            <div class="text-xs text-slate-500">${d}</div>
          </div>`).join('')}
      </div>
    </div>`;

  return `<div class="p-6">
    <div class="mb-5">
      <h1 class="text-2xl font-bold text-white">Proyectos</h1>
      <p class="text-xs text-slate-600 mt-0.5">${S.projects.length} proyecto${S.projects.length!==1?'s':''} activos</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
      ${S.projects.map(p => projCard(p, taskStats, groupCounts)).join('')}
      <div class="glass-card rounded-2xl p-5 flex flex-col items-center justify-center text-center cursor-pointer min-h-[180px] hover:border-primary/30 transition-colors"
           style="border:2px dashed rgba(100,116,139,.18)" onclick="mProject()">
        <span class="ms mb-2" style="font-size:26px;color:#334155">add_circle</span>
        <div class="text-sm font-medium text-slate-600">Nuevo Proyecto</div>
      </div>
    </div>
  </div>`;
}

function projCard(p, taskStats, groupCounts) {
  const { total = 0, done = 0 } = taskStats?.get(p.id) ?? {};
  const grpCount = groupCounts?.get(p.id) ?? 0;
  const pct = total ? Math.round(done / total * 100) : 0;
  return `
    <div class="proj-card glass-card rounded-2xl p-5" onclick="go('#/board/${p.id}')">
      <div class="flex items-start justify-between mb-3">
        <div class="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style="background:${p.color}1a;border:1px solid ${p.color}28">
          <span class="ms" style="color:${p.color};font-size:20px">${p.icon}</span>
        </div>
        <div class="flex items-center gap-1.5">
          ${p.priority ? `<span class="tag-chip" style="background:${p.priority.color}22;color:${p.priority.color}">
            <span class="ms" style="font-size:10px">${p.priority.icon}</span>${esc(p.priority.name)}</span>` : ''}
          <button class="btn-icon" onclick="event.stopPropagation();mProjectMenu(${p.id})">
            <span class="ms ms-sm">more_horiz</span>
          </button>
        </div>
      </div>
      <div class="flex items-center gap-1.5 mb-1">
        <h3 class="text-sm font-semibold text-white">${esc(p.name)}</h3>
        <button class="btn-icon p-0.5" onclick="event.stopPropagation();mProject(${p.id})" title="Editar proyecto"><span class="ms ms-xs">edit</span></button>
      </div>
      ${p.description ? `<p class="text-xs text-slate-500 mb-3 line-clamp-2">${esc(p.description)}</p>` : '<div class="mb-3"></div>'}
      <div class="prog-track mb-1.5"><div class="prog-fill" style="width:${pct}%"></div></div>
      <div class="flex items-center justify-between">
        <div class="text-xs text-slate-600">${done}/${total} tareas</div>
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-700">${grpCount} col</span>
          ${p.members.length ? `<div class="flex -space-x-1">${p.members.slice(0,3).map(m=>avatar(m,'sm')).join('')}${p.members.length>3?`<div style="width:22px;height:22px;border-radius:50%;background:rgba(249,115,22,.2);border:1.5px solid rgba(249,115,22,.3);display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:#F97316">+${p.members.length-3}</div>`:''}</div>` : ''}
          ${p.leader ? avatar(p.leader,'sm') : ''}
        </div>
      </div>
    </div>`;
}
