// ═══════════════════════════════════
// VIEW: Board (kanban)
// ═══════════════════════════════════
function vBoard() {
  const cols = S.groups.filter(g => g.project_id === S.pid).sort((a,b) => (a.sort_order??0)-(b.sort_order??0)||a.id-b.id);
  if (!cols.length) return `
    <div class="flex flex-col items-center justify-center h-full text-center px-4">
      <div class="w-14 h-14 rounded-2xl flex items-center justify-center mb-4" style="background:rgba(249,115,22,.1);border:1px solid rgba(249,115,22,.14)">
        <span class="ms" style="font-size:30px;color:#F97316">view_kanban</span>
      </div>
      <h2 class="text-xl font-bold text-white mb-2">Sin grupos de tareas</h2>
      <p class="text-slate-500 text-sm mb-5">Crea el primer grupo de tareas para organizar tu flujo.</p>
      <button class="btn btn-primary" onclick="mGroup()"><span class="ms ms-sm">add</span>Añadir grupo de tareas</button>
    </div>`;

  return `<div class="flex gap-4 p-5 overflow-x-auto h-full items-start pb-10">
    ${cols.map(kanbanCol).join('')}
    <div class="k-col flex-shrink-0">
      <button class="w-full glass-card rounded-2xl p-4 flex items-center gap-2 text-slate-600 hover:text-primary hover:border-primary/25 transition-all text-sm font-medium" onclick="mGroup()">
        <span class="ms ms-sm">add</span>Añadir grupo de tareas
      </button>
    </div>
  </div>`;
}

function kanbanCol(g) {
  const tasks = S.tasks.filter(t => t.group_id === g.id).sort((a,b) => (a.sort_order??0)-(b.sort_order??0)||a.id-b.id);
  return `<div class="k-col"
               ondragover="onColReorderDragOver(event,${g.id})"
               ondragleave="onColReorderDragLeave(event,${g.id})"
               ondrop="onColReorderDrop(event,${g.id})">
    <div class="glass-card k-col-body rounded-2xl overflow-hidden">
      <div class="k-col-header px-4 py-3 flex items-center justify-between select-none" style="background:${g.color}14"
           draggable="true"
           ondragstart="onColHeaderDragStart(event,${g.id})"
           ondragend="onColHeaderDragEnd(event)">
        <div class="flex items-center gap-2 min-w-0">
          <span class="ms ms-xs text-slate-600" style="font-size:14px">drag_indicator</span>
          <div class="w-2 h-2 rounded-full flex-shrink-0" style="background:${g.color}"></div>
          <span class="text-sm font-semibold text-white truncate">${esc(g.name)}</span>
          <span class="text-xs px-1.5 py-0.5 rounded-full font-semibold flex-shrink-0" style="background:${g.color}22;color:${g.color}">${tasks.length}</span>
          <button class="btn-icon p-0.5 flex-shrink-0" draggable="false" onclick="event.stopPropagation();mGroup(${g.id})" title="Editar grupo"><span class="ms ms-xs">edit</span></button>
        </div>
        <div class="flex items-center gap-0.5 flex-shrink-0">
          <button class="btn-icon" draggable="false" onclick="event.stopPropagation();mTask(null,${g.id})" title="Añadir tarea"><span class="ms ms-sm">add</span></button>
          <button class="btn-icon" draggable="false" onclick="event.stopPropagation();mColMenu(${g.id})"><span class="ms ms-sm">more_horiz</span></button>
        </div>
      </div>
      ${g.tags?.length ? `<div class="px-3 pt-2 flex flex-wrap gap-1">${g.tags.map(tg=>tagChip(tg,'group',g.id)).join('')}</div>` : ''}
      <div class="p-2.5 flex flex-col gap-2.5" id="col-${g.id}"
           ondragover="onColDragOver(event,${g.id})"
           ondragleave="onColDragLeave(event,${g.id})"
           ondrop="onColDrop(event,${g.id})">
        ${tasks.map(taskCard).join('')}
      </div>
      <div class="px-3 pb-3">
        <button class="w-full text-left text-xs text-slate-700 hover:text-slate-400 py-2 px-2.5 rounded-xl hover:bg-white/5 transition-all flex items-center gap-1.5" onclick="mTask(null,${g.id})">
          <span class="ms ms-xs">add</span>Añadir tarea
        </button>
      </div>
    </div>
  </div>`;
}

function taskCard(t) {
  const todoPct = t.todos_total ? (t.todos_completed/t.todos_total*100) : 0;
  return `
    <div class="task-card rounded-xl p-3 ${t.completed?'done':''}" style="background:rgba(26,37,63,.9);border:1px solid rgba(249,115,22,.1)"
         draggable="true"
         ondragstart="onTaskDragStart(event,${t.id},${t.group_id})"
         ondragend="onTaskDragEnd(event)"
         ondragover="onCardDragOver(event,${t.id})"
         ondragleave="onCardDragLeave(event,${t.id})"
         onclick="mTask(${t.id},${t.group_id})">
      ${t.tags.length ? `<div class="flex flex-wrap gap-1 mb-2">${t.tags.map(tg=>tagChip(tg,'task',t.id)).join('')}</div>` : ''}
      <div class="flex items-start gap-1">
        <div class="task-title text-sm font-medium text-white leading-snug flex-1">${esc(t.title)}</div>
        <span class="ms ms-xs text-slate-500 flex-shrink-0 mt-0.5">edit</span>
      </div>
      ${t.description ? `<div class="text-xs text-slate-500 mt-1 line-clamp-2">${esc(t.description)}</div>` : ''}
      ${t.priority ? `<div class="flex items-center gap-1 mt-1.5">
        <span class="ms ms-xs" style="color:${t.priority.color}">${t.priority.icon}</span>
        <span class="text-xs" style="color:${t.priority.color}">${esc(t.priority.name)}</span>
      </div>` : ''}
      ${t.todos_total ? `<div class="mt-2">
        <div class="flex justify-between text-xs text-slate-700 mb-1"><span>Subtareas</span><span>${t.todos_completed}/${t.todos_total}</span></div>
        <div class="prog-track"><div class="prog-fill" style="width:${todoPct}%"></div></div>
      </div>` : ''}
      <div class="flex items-center justify-between mt-2.5">
        <div class="flex items-center gap-1.5">
          ${t.user ? avatar(t.user,'sm') : ''}
          ${t.estimated_duration ? `<span class="text-xs text-slate-700">${t.estimated_duration}h</span>` : ''}
        </div>
        ${t.completed ? `<span class="ms ms-sm" style="color:#10B981">check_circle</span>` : ''}
      </div>
    </div>`;
}
