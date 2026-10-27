// ═══════════════════════════════════
// FLOWS — estados de las etiquetas, editor de flujos, panel global
// ═══════════════════════════════════
// S.flows  → flujos visibles en el proyecto abierto (globales + del proyecto)
// S.gflows → flujos globales (panel de administración)
// S.gtags  → etiquetas globales (panel de administración)

function isAdmin() { return !!S.currentUser?.is_admin; }

function canManageProject(pid) {
  const p = S.projects.find(x => x.id === pid);
  const cu = S.currentUser;
  return !!(cu && p && (cu.id === p.owner?.id || cu.id === p.leader?.id));
}

// Global → admin; de proyecto → propietario o líder.
function canManageScope(projectId) {
  return projectId == null ? isAdmin() : canManageProject(projectId);
}

function flowById(id) {
  return S.flows.find(f => f.id === id) || S.gflows.find(f => f.id === id) || null;
}

function stateById(flow, id) { return flow?.states.find(s => s.id === id) || null; }

// ── Chip de etiqueta (tarjetas, columnas) ───────
// Con flujo: «Etiqueta: Estado» y abre el cambio de estado.
function tagChip(tg, kind, itemId) {
  if (!tg.flow) {
    return `<span class="tag-chip" style="background:${tg.color}20;color:${tg.color}">${esc(tg.name)}</span>`;
  }
  return `<span class="tag-chip" draggable="false" title="Cambiar estado"
      style="background:${tg.color}20;color:${tg.color};border:1px solid ${tg.color}55;cursor:pointer;text-transform:none"
      onmousedown="event.stopPropagation()"
      onclick="event.stopPropagation();mFlowState('${kind}',${itemId},${tg.id})">${esc(tg.name)}:
      <strong>${esc(tg.state?.name || '—')}</strong><span class="ms ms-xs" style="font-size:12px">expand_more</span></span>`;
}

// ── Cambiar estado + historial ──────────────────
async function mFlowState(kind, itemId, tagId) {
  const item = kind === 'task' ? S.tasks.find(t => t.id === itemId) : S.groups.find(g => g.id === itemId);
  const tag = item?.tags.find(t => t.id === tagId);
  if (!tag?.flow) return;
  showModal('<div class="flex items-center justify-center py-6"><div class="spin"></div></div>');
  try {
    const [flow, hist] = await Promise.all([
      GET(`/flows/${tag.flow.id}`),
      GET(`/${kind}s/${itemId}/tags/${tagId}/history`),
    ]);
    const cur = tag.state?.id ?? null;
    const targets = flow.states.filter(s =>
      cur == null || flow.transitions.some(tr => tr.from_state_id === cur && tr.to_state_id === s.id));
    showModal(`
      ${mhdr(`${esc(tag.name)}: ${esc(tag.state?.name || '—')}`, `${kind === 'task' ? 'Tarea' : 'Grupo'} · ${esc(item.title || item.name)} · flujo ${esc(flow.name)}`)}
      <label class="lbl">Pasar a</label>
      ${targets.length
        ? `<div class="flex flex-wrap gap-2 mb-3">${targets.map(s => `
            <button type="button" class="btn btn-ghost" onclick="setFlowState('${kind}',${itemId},${tagId},${s.id})">
              <span style="width:8px;height:8px;border-radius:50%;background:${s.color};display:inline-block"></span>${esc(s.name)}
            </button>`).join('')}</div>`
        : `<p class="text-sm text-slate-500 mb-3">No hay transiciones desde este estado.</p>`}
      ${targets.length ? `<input id="fs-note" class="inp mb-1" maxlength="1000" placeholder="Nota (opcional): motivo del cambio">` : ''}
      <label class="lbl mt-5">Historial</label>
      ${historyList(hist)}`);
  } catch (err) { closeM(); toast(err.message, 'err'); }
}

function historyList(hist) {
  if (!hist.length) return `<p class="text-sm text-slate-500">Sin cambios registrados.</p>`;
  const who = id => S.users.find(u => u.id === id)?.name || (id ? `#${id}` : '—');
  const when = d => d ? d.replace('T', ' ').substring(0, 16) : '';
  return `<div class="max-h-56 overflow-y-auto flex flex-col gap-1.5">${[...hist].reverse().map(h => `
    <div class="rounded-lg px-3 py-2 text-xs" style="background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.05)">
      <div class="flex justify-between gap-2">
        <span class="text-slate-300">${h.from_state == null ? 'Entra en' : esc(h.from_state) + ' →'}
          <strong class="text-white">${h.to_state == null ? 'sale del flujo' : esc(h.to_state)}</strong></span>
        <span class="text-slate-600 flex-shrink-0">${esc(when(h.changed_at))}</span>
      </div>
      <div class="text-slate-600 mt-0.5">${esc(who(h.changed_by))}${h.note ? ` · <span class="text-slate-400">${esc(h.note)}</span>` : ''}</div>
    </div>`).join('')}</div>`;
}

async function setFlowState(kind, itemId, tagId, stateId) {
  const note = document.getElementById('fs-note')?.value.trim() || null;
  try {
    await PATCH(`/${kind}s/${itemId}/tags/${tagId}/state`, {state_id: stateId, note});
    closeM(); await loadAll(); render(); toast('Estado actualizado');
  } catch (err) { toast(err.message, 'err'); }
}

// ── Tarjetas de flujos (vistas) ─────────────────
function flowCards(flows, emptyMsg) {
  if (!flows.length) return `<p class="text-sm text-slate-500">${emptyMsg}</p>`;
  return `<div class="grid grid-cols-1 lg:grid-cols-2 gap-3">${flows.map(f => {
    const editable = canManageScope(f.project_id);
    return `<div class="glass-card rounded-2xl p-4 cursor-pointer hover:border-primary/25 transition-all" onclick="mFlowEdit(${f.id})">
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center gap-2">
          <span class="ms ms-sm" style="color:#F97316">account_tree</span>
          <span class="text-sm font-semibold text-white">${esc(f.name)}</span>
          ${f.project_id == null ? scopeBadge() : ''}
        </div>
        <span class="ms ms-sm text-slate-600">${editable ? 'edit' : 'visibility'}</span>
      </div>
      <div class="flex flex-wrap gap-1">${f.states.map(s => `
        <span class="tag-chip" style="background:${s.color}20;color:${s.color};text-transform:none">${s.is_initial ? '▶ ' : ''}${esc(s.name)}</span>`).join('')}
      </div>
      <div class="text-xs text-slate-600 mt-2">${f.transitions.length} transiciones</div>
    </div>`;
  }).join('')}</div>`;
}

function scopeBadge() {
  return `<span class="text-xs px-1.5 py-0.5 rounded-full font-semibold" style="background:rgba(167,139,250,.12);color:#A78BFA">Global</span>`;
}

// ── Nuevo flujo ─────────────────────────────────
// projectId null = global.
function mFlowNew(projectId) {
  showModal(`
    ${mhdr('Nuevo flujo', projectId == null ? 'Global: disponible en todos los proyectos' : 'Del proyecto')}
    <form onsubmit="saveFlowNew(event,${projectId ?? 'null'})">
      <div class="mb-3">
        <label class="lbl">Nombre</label>
        <input name="name" class="inp" placeholder="ej. Devslice" maxlength="50" required>
      </div>
      <div class="mb-1">
        <label class="lbl">Estados (uno por línea, en orden; el primero es el inicial)</label>
        <textarea name="states" rows="6" class="inp" placeholder="Planificada&#10;En desarrollo&#10;Terminada" required></textarea>
      </div>
      <p class="text-xs text-slate-500">Las transiciones se definen después, en el editor del flujo.</p>
      ${mfoot('Crear flujo', false)}
    </form>`);
}

async function saveFlowNew(e, projectId) {
  e.preventDefault();
  const f = e.target;
  const names = f.states.value.split('\n').map(s => s.trim()).filter(Boolean);
  if (!names.length) { toast('Indica al menos un estado', 'err'); return; }
  const body = {name: f.name.value.trim(), states: names.map(name => ({name})), initial: names[0], transitions: []};
  try {
    const flow = await POST(projectId == null ? '/flows/' : `/projects/${projectId}/flows/`, body);
    await loadAll(); render(); toast('Flujo creado');
    mFlowEdit(flow.id);
  } catch (err) { toast(err.message, 'err'); }
}

// ── Editor de flujo ─────────────────────────────
async function mFlowEdit(flowId) {
  try {
    const flow = await GET(`/flows/${flowId}`);
    document.querySelector('.modal-box').classList.add('modal-lg');
    showModal(flowEditorHtml(flow, canManageScope(flow.project_id)));
  } catch (err) { closeM(); toast(err.message, 'err'); }
}

function flowEditorHtml(f, edit) {
  const dis = edit ? '' : 'disabled';
  const has = (a, b) => f.transitions.some(t => t.from_state_id === a && t.to_state_id === b);
  const stateRows = f.states.map(s => `
    <div class="flex items-center gap-2 mb-1.5">
      <input type="color" value="${s.color}" ${dis} title="Color" style="width:28px;height:28px;background:none;border:none;padding:0;cursor:pointer"
        onchange="flowOp(${f.id},'PATCH','/states/${s.id}',{color:this.value})">
      <input class="inp" style="padding:.4rem .7rem" value="${esc(s.name)}" maxlength="50" ${dis}
        onchange="flowOp(${f.id},'PATCH','/states/${s.id}',{name:this.value})">
      <label class="flex items-center gap-1 text-xs text-slate-400 flex-shrink-0" title="Estado inicial: el que toma un elemento al ponerle la etiqueta">
        <input type="radio" name="initial" ${s.is_initial ? 'checked' : ''} ${dis}
          onchange="flowOp(${f.id},'PATCH','/states/${s.id}',{is_initial:true})">Inicial
      </label>
      ${edit ? `<button type="button" class="btn-icon flex-shrink-0" title="Eliminar estado" style="color:#6b7280"
          onclick="armThen(this, () => flowOp(${f.id},'DELETE','/states/${s.id}'))"><span class="ms ms-sm">delete</span></button>` : ''}
    </div>`).join('');
  const matrix = `
    <div class="overflow-x-auto"><table class="text-xs">
      <thead><tr><th class="text-left text-slate-600 font-semibold pr-3 pb-2">desde ↓ / hacia →</th>
        ${f.states.map(s => `<th class="px-2 pb-2 text-slate-400 font-semibold" style="max-width:90px">${esc(s.name)}</th>`).join('')}</tr></thead>
      <tbody>${f.states.map(a => `<tr>
        <td class="pr-3 py-1 text-slate-300 font-medium whitespace-nowrap">${esc(a.name)}</td>
        ${f.states.map(b => a.id === b.id
          ? `<td class="text-center text-slate-700">—</td>`
          : `<td class="text-center py-1"><input type="checkbox" ${has(a.id, b.id) ? 'checked' : ''} ${dis}
              onchange="toggleTransition(${f.id},${a.id},${b.id},this.checked)"></td>`).join('')}
      </tr>`).join('')}</tbody>
    </table></div>`;
  return `
    ${mhdr(edit ? 'Editar flujo' : 'Flujo', f.project_id == null ? 'Global' : 'Del proyecto')}
    <div class="mb-4">
      <label class="lbl">Nombre</label>
      <input class="inp" value="${esc(f.name)}" maxlength="50" ${dis}
        onchange="flowOp(${f.id},'PATCH','',{name:this.value})">
    </div>
    <div class="flex flex-col gap-6">
      <div class="max-w-xl">
        <label class="lbl">Estados</label>
        ${stateRows}
        ${edit ? `<form class="flex gap-2 mt-2" onsubmit="event.preventDefault();flowOp(${f.id},'POST','/states',{name:this.sname.value})">
          <input name="sname" class="inp" style="padding:.4rem .7rem" placeholder="Nuevo estado" maxlength="50" required>
          <button class="btn btn-ghost flex-shrink-0"><span class="ms ms-sm">add</span>Añadir</button>
        </form>` : ''}
      </div>
      <div>
        <label class="lbl">Transiciones permitidas</label>
        ${matrix}
      </div>
    </div>
    <div class="flex gap-2.5 justify-end mt-6">
      ${edit ? `<button type="button" class="btn btn-danger mr-auto" onclick="confirmDel('flow',${f.id})">Eliminar flujo</button>` : ''}
      <button type="button" class="btn btn-primary" onclick="closeM()">Cerrar</button>
    </div>`;
}

// Borrado en dos clics: el primero arma el botón («¿Eliminar?»), el segundo ejecuta.
// Se desarma solo a los 3 s. Evita borrar por un clic que cae en otra fila.
function armThen(btn, action) {
  if (btn.dataset.armed) { action(); return; }
  btn.dataset.armed = '1';
  const prev = btn.innerHTML;
  btn.innerHTML = '<span class="text-xs font-semibold" style="color:#f87171">¿Eliminar?</span>';
  setTimeout(() => { if (btn.isConnected) { delete btn.dataset.armed; btn.innerHTML = prev; } }, 3000);
}

// Aplica un cambio al flujo y vuelve a pintar el editor con el resultado.
async function flowOp(flowId, method, sub, body) {
  try {
    await req(method, `/flows/${flowId}${sub}`, body);
    await refreshFlowEditor(flowId);
  } catch (err) { toast(err.message, 'err'); await refreshFlowEditor(flowId); }
}

async function toggleTransition(flowId, from, to, on) {
  await flowOp(flowId, on ? 'POST' : 'DELETE',
    on ? '/transitions' : `/transitions/${from}/${to}`,
    on ? {from_state_id: from, to_state_id: to} : undefined);
}

async function refreshFlowEditor(flowId) {
  try {
    const flow = await GET(`/flows/${flowId}`);
    await loadAll(); render();
    showModal(flowEditorHtml(flow, canManageScope(flow.project_id)));
  } catch (err) { toast(err.message, 'err'); }
}

// ── Lista de etiquetas (vistas) ─────────────────
// scope: 'project' (rutas del proyecto) o 'global' (rutas /tags/).
function tagCards(tags, editable, scope, emptyMsg) {
  if (!tags.length) return `<p class="text-sm text-slate-500">${emptyMsg}</p>`;
  return `<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">${tags.map(t => `
    <div class="glass-card rounded-2xl p-4 flex items-center justify-between">
      <div class="flex items-center gap-3 min-w-0">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style="background:${t.color}1a;border:1px solid ${t.color}28">
          <div class="w-3 h-3 rounded-full" style="background:${t.color}"></div>
        </div>
        <div class="min-w-0">
          <div class="text-sm font-medium text-white truncate flex items-center gap-1.5">${esc(t.name)} ${t.project_id == null && scope === 'project' ? scopeBadge() : ''}</div>
          <div class="text-xs text-slate-600 truncate">${t.flow ? `<span class="ms ms-xs" style="vertical-align:middle">account_tree</span> ${esc(t.flow.name)}` : 'Sin flujo'}</div>
        </div>
      </div>
      ${editable ? `<div class="flex gap-0.5 flex-shrink-0">
        <button class="btn-icon" onclick="mTag(${t.id},'${scope}')"><span class="ms ms-sm">edit</span></button>
        <button class="btn-icon" style="color:#6b7280" onmouseenter="this.style.color='#f87171'" onmouseleave="this.style.color='#6b7280'"
          onclick="confirmDel('${scope === 'global' ? 'gtag' : 'tag'}',${t.id})"><span class="ms ms-sm">delete</span></button>
      </div>` : ''}
    </div>`).join('')}</div>`;
}

function sectionHead(title, btnLabel, btnFn) {
  return `<div class="flex items-center justify-between mb-3">
    <div class="text-xs font-semibold text-slate-600 uppercase tracking-wider">${title}</div>
    ${btnLabel ? `<button class="btn btn-ghost py-1.5" onclick="${btnFn}"><span class="ms ms-sm">add</span>${btnLabel}</button>` : ''}
  </div>`;
}

// ── VIEW: panel global (admin) ──────────────────
function vGlobals() {
  return `<div class="p-6 space-y-8">
    <p class="text-sm text-slate-500 max-w-3xl">Los flujos y etiquetas globales sirven en todos los proyectos. Solo los
      gestiona un administrador; los miembros de cada proyecto pueden usarlos y cambiar los estados.</p>
    <div>
      ${sectionHead('Flujos globales', 'Nuevo flujo', 'mFlowNew(null)')}
      ${flowCards(S.gflows, 'Aún no hay flujos globales.')}
    </div>
    <div>
      ${sectionHead('Etiquetas globales', 'Nueva etiqueta', "mTag(null,'global')")}
      ${tagCards(S.gtags, true, 'global', 'Aún no hay etiquetas globales.')}
    </div>
  </div>`;
}
