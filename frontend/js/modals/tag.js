// ═══════════════════════════════════
// MODAL: Tag
// ═══════════════════════════════════
// scope 'project' → /projects/{pid}/tags/ ; 'global' → /tags/ (solo admin).
// Una etiqueta global solo puede usar flujos globales; una de proyecto, globales o del proyecto.
function mTag(id, scope = 'project') {
  const list = scope === 'global' ? S.gtags : S.tags;
  const t = id ? list.find(x => x.id === id) : null;
  const col = t?.color || '#3B82F6';
  const flows = scope === 'global' ? S.gflows : S.flows;
  const curFlow = t?.flow?.id ?? null;
  showModal(`
    ${mhdr(t ? 'Editar etiqueta' : 'Nueva etiqueta', scope === 'global' ? 'Global: disponible en todos los proyectos' : '')}
    <form onsubmit="saveTag(event,${id || 'null'},'${scope}')">
      <input type="hidden" name="color" value="${col}">
      <div class="mb-3">
        <label class="lbl">Nombre</label>
        <input name="name" class="inp" placeholder="ej. Backend" maxlength="50" value="${esc(t?.name || '')}" required>
      </div>
      <div class="mb-3">
        <label class="lbl">Flujo</label>
        <select name="flow_id" class="inp">
          <option value="">Sin flujo</option>
          ${flows.map(f => `<option value="${f.id}" ${f.id === curFlow ? 'selected' : ''}>${esc(f.name)}${f.project_id == null && scope !== 'global' ? ' (global)' : ''}</option>`).join('')}
        </select>
        <p class="text-xs text-slate-600 mt-1">Con flujo, cada tarea o grupo con esta etiqueta tiene un estado. No se puede cambiar mientras la etiqueta esté puesta en alguno.</p>
      </div>
      <div class="mb-1">
        <label class="lbl">Color</label>
        ${swatches(col, 'color')}
      </div>
      ${mfoot(t ? 'Guardar' : 'Crear etiqueta', false)}
    </form>`);
}

async function saveTag(e, id, scope = 'project') {
  e.preventDefault();
  const f = e.target;
  const b = { name: f.name.value, color: f.color.value, flow_id: f.flow_id.value ? +f.flow_id.value : null };
  const base = scope === 'global' ? '/tags/' : `/projects/${S.pid}/tags/`;
  try {
    id ? await PATCH(`${base}${id}`, b) : await POST(base, b);
    closeM(); await loadAll(); render(); toast(id ? 'Etiqueta actualizada' : 'Etiqueta creada');
  } catch (err) { toast(err.message, 'err'); }
}
