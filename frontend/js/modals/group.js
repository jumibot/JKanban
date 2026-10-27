// ═══════════════════════════════════
// MODAL: Group (columna kanban)
// ═══════════════════════════════════
function mGroup(id) {
  const g = id ? S.groups.find(x=>x.id===id) : null;
  const col = g?.color||'#3B82F6';
  showModal(`
    ${mhdr(g?'Editar grupo de tareas':'Nuevo grupo de tareas','Define un segmento para tu flujo')}
    <form onsubmit="saveGroup(event,${id||'null'})">
      <input type="hidden" name="color" value="${col}">
      <div class="mb-3">
        <label class="lbl">Nombre</label>
        <input name="name" class="inp" placeholder="ej. En Progreso" value="${esc(g?.name||'')}" required>
      </div>
      <div class="mb-3">
        <label class="lbl">Descripción</label>
        <input name="description" class="inp" placeholder="Opcional..." value="${esc(g?.description||'')}">
      </div>
      ${S.tags.length ? `<div class="mb-3">
        <label class="lbl">Etiquetas</label>
        <div class="flex flex-wrap gap-1.5">${S.tags.map(tg => {
          const on = g?.tags?.some(x => x.id === tg.id);
          return `<label class="tag-chip" style="cursor:pointer;text-transform:none;background:${tg.color}${on ? '40' : '12'};color:${tg.color};border:1px solid ${tg.color}44">
            <input type="checkbox" name="gtag" value="${tg.id}" ${on ? 'checked' : ''} style="accent-color:${tg.color}"
              onchange="this.parentElement.style.background='${tg.color}'+(this.checked?'40':'12')">${esc(tg.name)}${tg.flow ? ' <span class="ms ms-xs" title="Con flujo">account_tree</span>' : ''}</label>`;
        }).join('')}</div>
        <p class="text-xs text-slate-600 mt-1">Una etiqueta con flujo pone el grupo en su estado inicial; el estado se cambia desde la columna.</p>
      </div>` : ''}
      <div class="mb-1">
        <label class="lbl">Color</label>
        ${swatches(col,'color')}
      </div>
      ${mfoot(g?'Guardar':'Crear grupo de tareas', !!g, `confirmDel('group',${id});closeM()`)}
    </form>`);
}

async function saveGroup(e, id) {
  e.preventDefault();
  const f = e.target;
  const b = { name: f.name.value, description: f.description.value||null, color: f.color.value, project_id: S.pid };
  const wanted = [...f.querySelectorAll('input[name="gtag"]:checked')].map(x => +x.value);
  try {
    const saved = id ? await PATCH(`/groups/${id}`,b) : await POST('/groups/',b);
    const had = id ? (S.groups.find(g => g.id === id)?.tags || []).map(t => t.id) : [];
    await Promise.all([
      ...wanted.filter(x => !had.includes(x)).map(tid => POST(`/groups/${saved.id}/tags/${tid}`)),
      ...had.filter(x => !wanted.includes(x)).map(tid => DEL(`/groups/${saved.id}/tags/${tid}`)),
    ]);
    closeM(); await loadAll(); render(); toast(id?'Grupo de tareas actualizado':'Grupo de tareas creado');
  } catch(err) { toast(err.message,'err'); }
}

// ── Column context menu ───────────
function mColMenu(id) {
  const g = S.groups.find(x=>x.id===id);
  showModal(`
    <div class="flex items-center justify-between mb-4">
      <h3 class="font-semibold text-white">${esc(g?.name||'')}</h3>
      <button class="btn-icon" onclick="closeM()"><span class="ms ms-sm">close</span></button>
    </div>
    <div class="flex flex-col gap-1">
      <button class="flex items-center gap-3 p-3 rounded-xl text-slate-300 hover:text-white hover:bg-white/5 transition-all text-sm" onclick="closeM();mGroup(${id})">
        <span class="ms ms-sm" style="color:#F97316">edit</span>Editar grupo de tareas
      </button>
      <div class="border-t my-1" style="border-color:rgba(255,255,255,.06)"></div>
      <button class="flex items-center gap-3 p-3 rounded-xl text-red-400 hover:bg-red-500/10 transition-all text-sm" onclick="confirmDel('group',${id})">
        <span class="ms ms-sm">delete</span>Eliminar grupo de tareas
      </button>
    </div>`);
}
