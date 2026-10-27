// ═══════════════════════════════════
// VIEW: Etiquetas y flujos del proyecto
// ═══════════════════════════════════
// S.tags trae primero las globales y después las del proyecto.
// Las globales y los flujos globales se ven aquí en solo lectura.
function vProjectTags() {
  const canManage = canManageProject(S.pid);
  const own = S.tags.filter(t => t.project_id === S.pid);
  const global = S.tags.filter(t => t.project_id == null);
  const ownFlows = S.flows.filter(f => f.project_id === S.pid);
  const globalFlows = S.flows.filter(f => f.project_id == null);
  return `<div class="p-6 space-y-8">
    <div>
      ${sectionHead('Etiquetas del proyecto', canManage ? 'Nueva etiqueta' : '', "mTag(null,'project')")}
      ${tagCards(own, canManage, 'project',
        canManage ? 'Crea la primera etiqueta para clasificar tareas.' : 'Este proyecto no tiene etiquetas propias.')}
    </div>
    ${global.length ? `<div>
      ${sectionHead('Etiquetas globales <span class="normal-case font-normal text-slate-700">· solo lectura</span>')}
      ${tagCards(global, false, 'project', '')}
    </div>` : ''}
    <div>
      ${sectionHead('Flujos del proyecto', canManage ? 'Nuevo flujo' : '', `mFlowNew(${S.pid})`)}
      ${flowCards(ownFlows, canManage
        ? 'Un flujo define estados y transiciones; asígnalo a una etiqueta para seguir el estado de tareas y grupos.'
        : 'Este proyecto no tiene flujos propios.')}
    </div>
    ${globalFlows.length ? `<div>
      ${sectionHead('Flujos globales <span class="normal-case font-normal text-slate-700">· solo lectura</span>')}
      ${flowCards(globalFlows, '')}
    </div>` : ''}
  </div>`;
}
