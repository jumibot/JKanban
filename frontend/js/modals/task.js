// ═══════════════════════════════════
// MODAL: Task
// ═══════════════════════════════════
function mTask(taskId, groupId) {
  const t = taskId ? S.tasks.find(x=>x.id===taskId) : null;
  const grps = S.groups.filter(g => g.project_id === S.pid);
  const selG = groupId || t?.group_id || grps[0]?.id;
  const fmt = dt => dt ? dt.substring(0,16) : '';
  const selTags = new Set(t?.tags?.map(x=>x.id)||[]);
  const isEdit = !!t;
  const doneBg = t?.completed ? '#F97316' : 'transparent';
  const doneBdr = t?.completed ? '#F97316' : '#475569';
  const doneChk = t?.completed ? '1' : '0';
  const doneLbl = t?.completed ? '#F97316' : '#64748b';
  document.querySelector('.modal-box').classList.add('modal-lg');
  showModal(`
    <form onsubmit="saveTask(event,${taskId||'null'})" data-task-id="${taskId||''}">
      <input type="hidden" name="tag_ids" id="tid-inp" value="${[...selTags].join(',')}">
      <input type="hidden" name="priority_id" id="tpriority-inp" value="${t?.priority?.id||''}">
      <input type="hidden" name="group_id" value="${selG}">
      <input type="checkbox" name="completed" id="chk-done" style="position:absolute;opacity:0;pointer-events:none" ${t?.completed?'checked':''}>
      <div class="-mx-6 -mt-6 px-6 sm:px-8 pt-6 pb-4 mb-2 rounded-t-2xl flex flex-col gap-4" style="background:linear-gradient(135deg,rgba(249,115,22,.13) 0%,rgba(13,24,41,.4) 100%);border-bottom:1px solid rgba(249,115,22,.15)">
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-center gap-1.5 flex-1 min-w-0">
            <span class="ms ms-sm text-slate-500 flex-shrink-0 mt-0.5">edit</span>
            <input name="title" class="flex-1 text-xl font-bold bg-transparent border-b-2 border-transparent focus:border-orange-500 focus:outline-none px-1 text-slate-100 placeholder-slate-600 transition-colors" placeholder="Nombre de la tarea..." value="${esc(t?.title||'')}" required>
          </div>
          <button type="button" onclick="closeM()" class="flex-shrink-0 ms ms-sm text-slate-500 hover:text-slate-300 mt-1">close</button>
        </div>
        <div class="px-1 flex items-center gap-4 flex-wrap">
          <button type="button" id="btn-completed" onclick="toggleCompletedBtn()" class="flex items-center gap-2">
            <div class="done-ring w-6 h-6 rounded-full border-2 flex items-center justify-center" style="background:${doneBg};border-color:${doneBdr}">
              <span class="done-check ms ms-sm text-white" style="opacity:${doneChk};font-size:14px">check</span>
            </div>
            <span class="done-label text-xs font-bold uppercase tracking-wider" style="color:${doneLbl}">Marcar completada</span>
          </button>
          ${S.tags.length ? `<div id="ttag-section" style="display:inline-flex;align-items:center"></div>` : ''}
          ${S.priorities.length ? `<div id="tpriority-section" style="display:inline-flex;align-items:center"></div>` : ''}
        </div>
      </div>
      <div class="px-6 sm:px-8 pb-6">
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div class="${isEdit?'lg:col-span-7':'col-span-full'} space-y-4">
            <textarea name="description" rows="5" class="w-full bg-slate-900/40 border border-slate-700/30 rounded-xl text-sm text-slate-200 p-4 focus:ring-1 focus:ring-orange-500/40 focus:border-orange-500/40 resize-none placeholder-slate-600 outline-none" placeholder="Descripción detallada...">${esc(t?.description||'')}</textarea>
            <div class="space-y-2">
              <div class="meta-row">
                <span class="meta-label">Responsable</span>
                <select name="user_id" class="meta-select">
                  <option value="">Sin asignar</option>
                  ${S.users.map(u=>`<option value="${u.id}" ${t?.user?.id===u.id?'selected':''}>${esc(u.name)}</option>`).join('')}
                </select>
              </div>
              <div class="meta-row">
                <span class="meta-label">Duración (h)</span>
                <input name="estimated_duration" type="number" step="0.5" min="0" class="meta-input" placeholder="—" value="${t?.estimated_duration||''}">
              </div>
              <div class="meta-row">
                <span class="meta-label">Inicio estimado</span>
                <input name="estimated_start" type="datetime-local" class="meta-input" value="${fmt(t?.estimated_start)}">
              </div>
              <div class="meta-row">
                <span class="meta-label">Fin estimado</span>
                <input name="estimated_end" type="datetime-local" class="meta-input" value="${fmt(t?.estimated_end)}">
              </div>
            </div>
          </div>
          ${isEdit ? `<div class="lg:col-span-5 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-extrabold text-slate-500 uppercase tracking-[.2em] flex items-center gap-2"><span class="ms ms-sm">checklist</span> Subtareas</span>
              <button type="button" class="text-[10px] font-extrabold text-orange-500 uppercase tracking-widest hover:underline" onclick="document.getElementById('new-todo-inp').focus()">Añadir</button>
            </div>
            <div id="todos-list" class="space-y-2"></div>
            <div class="flex items-center gap-2 bg-slate-900/20 p-2 rounded-xl border border-dashed border-slate-700/30 hover:border-orange-500/40 transition-all mt-2">
              <input id="new-todo-inp" class="bg-transparent border-none focus:ring-0 text-sm text-slate-200 placeholder-slate-600 flex-1 py-1.5 px-3 outline-none" placeholder="Nueva subtarea..." onkeydown="if(event.key==='Enter'){event.preventDefault();addTodo(${t.id})}">
              <button type="button" onclick="addTodo(${t.id})" class="ms text-orange-500 text-xl hover:scale-110 active:scale-90 transition-transform">add_circle</button>
            </div>
          </div>` : ''}
        </div>
      </div>
      <div class="px-6 sm:px-8 py-4 flex items-center justify-between border-t border-slate-700/20 gap-4">
        <div>${isEdit ? `<button type="button" class="btn btn-danger" onclick="confirmDel('task',${taskId});closeM()">Eliminar</button>` : ''}</div>
        <div class="flex items-center gap-3">
          <button type="button" onclick="closeM()" class="px-5 py-2 rounded-xl text-sm font-semibold text-slate-400 hover:bg-slate-800 transition-colors">Cancelar</button>
          <button type="submit" class="px-8 py-2 rounded-xl text-sm font-extrabold bg-orange-500 text-white shadow-lg shadow-orange-500/30 hover:brightness-110 active:scale-95 transition-all">${isEdit?'Guardar':'Crear Tarea'}</button>
        </div>
      </div>
    </form>`);
  renderTTagSection();
  renderPrioritySection();
  if (taskId) loadTodos(taskId);
}

function toggleCompletedBtn() {
  const chk = document.getElementById('chk-done');
  chk.checked = !chk.checked;
  const btn = document.getElementById('btn-completed');
  const ring = btn.querySelector('.done-ring');
  const checkIcon = btn.querySelector('.done-check');
  const label = btn.querySelector('.done-label');
  ring.style.background = chk.checked ? '#F97316' : 'transparent';
  ring.style.borderColor = chk.checked ? '#F97316' : '#475569';
  checkIcon.style.opacity = chk.checked ? '1' : '0';
  label.style.color = chk.checked ? '#F97316' : '#64748b';
}

function renderTTagSection() {
  const container = document.getElementById('ttag-section');
  const inp = document.getElementById('tid-inp');
  if (!container || !inp) return;
  const pickerOpen = document.getElementById('ttag-picker')?.style.display !== 'none';
  const ids = inp.value ? inp.value.split(',').map(Number).filter(Boolean) : [];
  const selSet = new Set(ids);
  const selected = S.tags.filter(t => selSet.has(t.id));
  // Estado actual de las etiquetas con flujo de la tarea abierta
  const taskId = +(document.querySelector('#modal-inner form')?.dataset.taskId || 0);
  const stateOf = tgId => S.tasks.find(x => x.id === taskId)?.tags.find(x => x.id === tgId)?.state?.name;
  container.innerHTML = `
    <div style="display:inline-flex;flex-wrap:wrap;gap:.375rem;align-items:center">
      ${selected.map(tg=>`<div class="tag-chip" style="background:${tg.color}40;color:${tg.color};outline:2px solid ${tg.color}55;outline-offset:-1px">${esc(tg.name)}${stateOf(tg.id) ? `: ${esc(stateOf(tg.id))}` : ''}<span class="ms ms-xs" onclick="toggleTTag(${tg.id})" style="cursor:pointer;margin-left:3px;opacity:.6;vertical-align:middle">close</span></div>`).join('')}
      ${S.tags.some(tg=>!selSet.has(tg.id)) ? `<div style="position:relative">
        <button type="button" onclick="toggleTTagPicker()" class="tag-chip" style="background:rgba(249,115,22,.08);color:#F97316;border:1px dashed rgba(249,115,22,.3)"><span class="ms ms-xs">add</span>Añadir etiqueta</button>
        <div id="ttag-picker" style="display:${pickerOpen?'block':'none'};position:absolute;left:0;top:calc(100% + 6px);background:#0d1829;border:1px solid rgba(249,115,22,.2);border-radius:.75rem;padding:.375rem;z-index:100;min-width:180px;box-shadow:0 8px 28px rgba(0,0,0,.55)">
          ${S.tags.filter(tg=>!selSet.has(tg.id)).map(tg=>`<div onclick="toggleTTag(${tg.id})" style="display:flex;align-items:center;gap:.6rem;padding:.45rem .625rem;border-radius:.5rem;cursor:pointer;background:${tg.color}0d" onmouseover="this.style.background='${tg.color}22'" onmouseout="this.style.background='${tg.color}0d'">
            <div style="width:8px;height:8px;border-radius:50%;background:${tg.color};flex-shrink:0"></div>
            <span style="font-size:.8rem;font-weight:600;color:${tg.color}">${esc(tg.name)}</span>
          </div>`).join('')}
        </div>
      </div>` : ''}
    </div>`;
}

function renderPrioritySection() {
  const container = document.getElementById('tpriority-section');
  const inp = document.getElementById('tpriority-inp');
  if (!container || !inp) return;
  const pid = inp.value ? +inp.value : null;
  const sel = S.priorities.find(p => p.id === pid);
  container.innerHTML = `
    <div style="position:relative;display:inline-flex">
      ${sel
        ? `<div class="tag-chip" style="background:${sel.color}40;color:${sel.color};outline:2px solid ${sel.color}55;outline-offset:-1px"><span class="ms ms-xs" style="vertical-align:middle">${sel.icon}</span>${esc(sel.name)}<span class="ms ms-xs" onclick="selectPriority(null)" style="cursor:pointer;margin-left:3px;opacity:.6;vertical-align:middle">close</span></div>`
        : `<button type="button" onclick="togglePriorityPicker()" class="tag-chip" style="background:rgba(249,115,22,.08);color:#F97316;border:1px dashed rgba(249,115,22,.3)"><span class="ms ms-xs">add</span>Prioridad</button>`
      }
      <div id="tpriority-picker" style="display:none;position:absolute;left:0;top:calc(100% + 6px);background:#0d1829;border:1px solid rgba(249,115,22,.2);border-radius:.75rem;padding:.375rem;z-index:100;min-width:180px;box-shadow:0 8px 28px rgba(0,0,0,.55)">
        ${S.priorities.map(p=>`<div onclick="selectPriority(${p.id})" style="display:flex;align-items:center;gap:.6rem;padding:.45rem .625rem;border-radius:.5rem;cursor:pointer;background:${p.color}0d" onmouseover="this.style.background='${p.color}22'" onmouseout="this.style.background='${p.color}0d'">
          <span class="ms ms-xs" style="color:${p.color}">${p.icon}</span>
          <span style="flex:1;font-size:.8rem;font-weight:600;color:${p.color}">${esc(p.name)}</span>
        </div>`).join('')}
      </div>
    </div>`;
}

function togglePriorityPicker() {
  const p = document.getElementById('tpriority-picker');
  if (p) p.style.display = p.style.display === 'none' ? 'block' : 'none';
}

function selectPriority(pid) {
  const inp = document.getElementById('tpriority-inp');
  if (inp) inp.value = pid || '';
  renderPrioritySection();
}

function toggleTTagPicker() {
  const p = document.getElementById('ttag-picker');
  if (p) p.style.display = p.style.display === 'none' ? 'block' : 'none';
}

function toggleTTag(tagId) {
  const pickerOpen = document.getElementById('ttag-picker')?.style.display !== 'none';
  const inp = document.getElementById('tid-inp');
  let ids = inp.value ? inp.value.split(',').map(Number).filter(Boolean) : [];
  if (ids.includes(tagId)) ids = ids.filter(x => x !== tagId); else ids.push(tagId);
  inp.value = ids.join(',');
  renderTTagSection();
  if (pickerOpen) {
    const p = document.getElementById('ttag-picker');
    if (p) p.style.display = 'block';
  }
}

async function saveTask(e, id) {
  e.preventDefault();
  const f = e.target;
  const newTagIds = f.tag_ids.value ? f.tag_ids.value.split(',').map(Number).filter(Boolean) : [];
  const b = {
    title: f.title.value, description: f.description.value||null,
    group_id: +f.group_id.value,
    priority_id: f.priority_id.value ? +f.priority_id.value : null,
    user_id: f.user_id.value ? +f.user_id.value : null,
    estimated_duration: f.estimated_duration.value ? parseFloat(f.estimated_duration.value) : null,
    estimated_start: f.estimated_start.value||null,
    estimated_end: f.estimated_end.value||null,
    completed: f.completed.checked,
  };
  try {
    const saved = id ? await PATCH(`/tasks/${id}`,b) : await POST('/tasks/',b);
    const existIds = id ? (S.tasks.find(t=>t.id===id)?.tags?.map(t=>t.id)||[]) : [];
    const toAdd = newTagIds.filter(x=>!existIds.includes(x));
    const toDel = existIds.filter(x=>!newTagIds.includes(x));
    await Promise.all([
      ...toAdd.map(tid=>req('POST',`/tasks/${saved.id}/tags/${tid}`)),
      ...toDel.map(tid=>req('DELETE',`/tasks/${saved.id}/tags/${tid}`)),
    ]);
    closeM(); await loadAll(); render(); toast(id?'Tarea actualizada':'Tarea creada');
  } catch(err) { toast(err.message,'err'); }
}
