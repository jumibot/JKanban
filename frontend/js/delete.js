// ═══════════════════════════════════
// DELETE — confirm & execute
// ═══════════════════════════════════

// ── Cascade delete project ────────
async function confirmCascadeDelProject(projectId) {
  showModal('<div class="flex items-center justify-center py-6"><div class="spin"></div></div>');
  try {
    const preview = await GET('/projects/' + projectId + '/deletion-preview');
    const p = preview.project;
    showModal(
      '<div class="text-center mb-4">' +
      '<div class="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-3" style="background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.2)">' +
      '<span class="ms" style="font-size:28px;color:#EF4444">delete_forever</span></div>' +
      '<h2 class="text-base font-bold text-white">Eliminar proyecto</h2>' +
      '<p class="text-sm text-slate-400 mt-1"><strong class="text-white">' + esc(p.name) + '</strong></p>' +
      '</div>' +
      '<div class="rounded-xl px-3 py-2.5 mb-4" style="background:rgba(239,68,68,.06);border:1px solid rgba(239,68,68,.15)">' +
      '<div class="flex flex-wrap gap-3 text-xs text-slate-400">' +
      '<span><span class="ms ms-xs" style="vertical-align:middle">view_column</span> ' + preview.groups_count + ' grupos de tareas</span>' +
      '<span><span class="ms ms-xs" style="vertical-align:middle">task_alt</span> ' + preview.tasks_count + ' tareas</span>' +
      '<span><span class="ms ms-xs" style="vertical-align:middle">label</span> ' + preview.tags_count + ' etiquetas</span>' +
      '<span><span class="ms ms-xs" style="vertical-align:middle">flag</span> ' + preview.priorities_count + ' prioridades</span>' +
      '<span><span class="ms ms-xs" style="vertical-align:middle">group</span> ' + preview.members_count + ' miembros</span>' +
      '</div></div>' +
      '<form onsubmit="execCascadeDelProject(event,' + projectId + ')">' +
      '<div class="mb-4"><label class="lbl">Confirma con tu contraseña</label>' +
      '<input name="owner_password" type="password" class="inp" placeholder="Tu contraseña" required autofocus></div>' +
      '<div class="flex gap-3">' +
      '<button type="button" class="btn btn-ghost flex-1 justify-center" onclick="closeM()">Cancelar</button>' +
      '<button type="submit" class="btn btn-danger flex-1 justify-center"><span class="ms ms-sm">delete_forever</span>Eliminar todo</button>' +
      '</div></form>'
    );
  } catch(err) { closeM(); toast(err.message, 'err'); }
}

async function execCascadeDelProject(e, projectId) {
  e.preventDefault();
  const password = e.target.owner_password.value;
  try {
    await req('DELETE', '/projects/' + projectId + '/cascade', {owner_password: password});
    closeM();
    if (projectId === S.pid) go('#/');
    await loadAll(); render(); toast('Proyecto eliminado');
  } catch(err) { toast(err.message, 'err'); }
}

// ── Generic confirm delete ────────
const DEL_LABELS = {project:'proyecto',group:'grupo de tareas',task:'tarea',tag:'etiqueta',gtag:'etiqueta global',flow:'flujo',priority:'prioridad',user:'usuario'};

function confirmDel(type, id) {
  const NAME_SOURCES = {
    tag:      () => S.tags.find(x => x.id === id)?.name,
    gtag:     () => S.gtags.find(x => x.id === id)?.name,
    flow:     () => flowById(id)?.name,
    priority: () => S.priorities.find(x => x.id === id)?.name,
    group:    () => S.groups.find(x => x.id === id)?.name,
    task:     () => S.tasks.find(x => x.id === id)?.title,
    project:  () => S.projects.find(x => x.id === id)?.name,
    user:     () => S.users.find(x => x.id === id)?.name,
  };
  const name = NAME_SOURCES[type]?.() ?? '';
  let extra = '';
  if (type === 'group') {
    const taskCount = S.tasks.filter(t => t.group_id === id).length;
    if (taskCount > 0)
      extra = '<p class="text-xs text-red-400 mb-4">Se eliminarán también las <strong>' + taskCount + ' tarea' + (taskCount > 1 ? 's' : '') + '</strong> que contiene.</p>';
  }
  showModal(`
    <div class="text-center py-3">
      <div class="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4" style="background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.2)">
        <span class="ms" style="font-size:28px;color:#EF4444">delete_forever</span>
      </div>
      <h2 class="text-base font-bold text-white mb-2">Eliminar ${DEL_LABELS[type]||type}</h2>
      <p class="text-slate-400 text-sm mb-3">¿Seguro que quieres eliminar <strong class="text-white">"${esc(name)}"</strong>?<br>Esta acción no se puede deshacer.</p>
      ${extra}
      <div class="flex gap-3 justify-center">
        <button class="btn btn-ghost" onclick="closeM()">Cancelar</button>
        <button class="btn btn-danger" onclick="execDel('${type}',${id})">Eliminar</button>
      </div>
    </div>`);
}

async function execDel(type, id) {
  const eps = {
    project:`/projects/${id}`, group:`/groups/${id}`,
    task:`/tasks/${id}`, tag:`/projects/${S.pid}/tags/${id}`,
    gtag:`/tags/${id}`, flow:`/flows/${id}`,
    priority:`/projects/${S.pid}/priorities/${id}`,
    user:`/users/${id}`,
  };
  try {
    await DEL(eps[type]);
    closeM();
    if (type==='project' && id===S.pid) go('#/');
    await loadAll(); render(); toast('Eliminado correctamente');
  } catch(err) { toast(err.message,'err'); }
}
