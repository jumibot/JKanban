// ═══════════════════════════════════
// RENDER
// ═══════════════════════════════════
function render() { renderSidebar(); renderHeader(); renderContent(); }

// ── Sidebar ──────────────────────
function renderSidebar() {
  const nav  = document.getElementById('sb-nav');
  const acts = document.getElementById('sb-actions');
  const ubox = document.getElementById('sb-user');
  const v = S.view;
  const isAdmin = !!(S.currentUser && S.currentUser.is_admin);
  const adminLink = isAdmin
    ? '<div class="nav-item' + (v==='team' ? ' active' : '') + '" onclick="go(\'#/team\')"><span class="ms ms-sm">manage_accounts</span>Usuarios</div>'
      + '<div class="nav-item' + (v==='globals' ? ' active' : '') + '" onclick="go(\'#/admin/flows\')"><span class="ms ms-sm">account_tree</span>Flujos y etiquetas globales</div>'
    : '';

  if (v === 'board' && S.pid) {
    const p = S.projects.find(x => x.id === S.pid);
    const sub = S.subview;
    nav.innerHTML = `
      <div class="px-2 mb-4">
        <div class="flex items-center gap-2">
          <div class="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0" style="background:${p?.color||'#3B82F6'}1a;border:1px solid ${p?.color||'#3B82F6'}2a">
            <span class="ms" style="font-size:17px;color:${p?.color||'#3B82F6'}">${p?.icon||'folder'}</span>
          </div>
          <div class="min-w-0">
            <div class="text-sm font-semibold text-white truncate">${esc(p?.name||'')}</div>
            ${p?.priority ? `<div class="text-xs font-medium" style="color:${p.priority.color}">${esc(p.priority.name)}</div>` : ''}
          </div>
        </div>
      </div>
      <div class="text-xs font-semibold text-slate-700 uppercase px-2 mb-1 tracking-wider">Proyecto</div>
      <div class="nav-item ${sub==='kanban'?'active':''}" onclick="go('#/board/${S.pid}')"><span class="ms ms-sm">view_kanban</span>Grupos de tareas</div>
      <div class="nav-item ${sub==='tags'?'active':''}" onclick="go('#/board/${S.pid}/tags')"><span class="ms ms-sm">label</span>Etiquetas y flujos</div>
      <div class="nav-item ${sub==='priorities'?'active':''}" onclick="go('#/board/${S.pid}/priorities')"><span class="ms ms-sm">flag</span>Prioridades</div>
      <div class="nav-item ${sub==='team'?'active':''}" onclick="go('#/board/${S.pid}/team')"><span class="ms ms-sm">group</span>Equipo</div>
      ${adminLink}
      <div class="mt-4 text-xs font-semibold text-slate-700 uppercase px-2 mb-1 tracking-wider">Navegación</div>
      <div class="nav-item" onclick="go('#/')"><span class="ms ms-sm">arrow_back</span>Proyectos</div>`;
  } else {
    nav.innerHTML =
      '<div class="nav-item' + (v==='dashboard' ? ' active' : '') + '" onclick="go(\'#/\')">'
      + '<span class="ms ms-sm">grid_view</span>Proyectos</div>'
      + adminLink;
  }

  // Sidebar action buttons
  if (v === 'board' && S.subview === 'kanban') {
    acts.innerHTML = `
      <button class="btn btn-primary py-2.5 w-full" onclick="mGroup()"><span class="ms ms-sm">add</span>Grupo de tareas</button>
      <button class="btn btn-primary py-2.5 w-full" onclick="mTask(null,null)"><span class="ms ms-sm">add</span>Nueva Tarea</button>`;
  } else if (v === 'dashboard') {
    acts.innerHTML = `<button class="btn btn-primary py-2.5 w-full" onclick="mProject()"><span class="ms ms-sm">add</span>Crear Proyecto</button>`;
  } else if (v === 'team' && isAdmin) {
    acts.innerHTML = `<button class="btn btn-primary py-2.5 w-full" onclick="mUser()"><span class="ms ms-sm">add</span>Nuevo Usuario</button>`;
  } else {
    acts.innerHTML = '';
  }

  // Current user display
  const cu = S.currentUser;
  if (cu) {
    ubox.innerHTML = `
      <div class="mt-4 mb-2 px-2 py-2 rounded-xl flex items-center gap-2.5 cursor-pointer transition-all hover:bg-white/5" onclick="mEditProfile()">
        ${cu.avatar_url
          ? `<img src="${esc(cu.avatar_url)}" class="w-8 h-8 rounded-full object-cover flex-shrink-0" style="border:1.5px solid rgba(249,115,22,.3)">`
          : `<div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0" style="background:${hashCol(cu.name)};border:1.5px solid rgba(249,115,22,.25)">${inits(cu.name)}</div>`}
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-1">
            <div class="text-xs font-semibold text-white truncate">${esc(cu.name)}</div>
            ${cu.is_admin?'<span class="ms ms-xs flex-shrink-0" style="font-size:11px;color:#A78BFA">shield</span>':''}
          </div>
          <div class="text-xs text-slate-600 truncate">${esc(cu.email)}</div>
        </div>
        <span class="ms ms-xs text-slate-700 flex-shrink-0">settings</span>
      </div>`;
  } else {
    ubox.innerHTML = '';
  }
}

// ── Header ───────────────────────
function renderHeader() {
  const bc  = document.getElementById('hdr-bc');
  const act = document.getElementById('hdr-act');
  const v = S.view;
  if (v==='board') {
    const p = S.projects.find(x => x.id === S.pid);
    const subLabels = { tags:'Etiquetas y flujos', priorities:'Prioridades', team:'Equipo' };
    const subLabel = subLabels[S.subview];
    bc.innerHTML = `<span class="cursor-pointer hover:text-primary transition-colors" onclick="go('#/')">Proyectos</span>
      <span class="ms ms-xs text-slate-700">chevron_right</span>
      ${subLabel
        ? `<span class="cursor-pointer hover:text-primary transition-colors" onclick="go('#/board/${S.pid}')">${esc(p?.name||'')}</span>
           <span class="ms ms-xs text-slate-700">chevron_right</span>
           <span class="text-white font-medium">${subLabel}</span>`
        : `<span class="text-white font-medium">${esc(p?.name||'')}</span>`}`;
    act.innerHTML = '';
  } else if (v==='dashboard') {
    bc.innerHTML = `<span class="text-white font-semibold">Proyectos</span>`;
    act.innerHTML = '';
  } else if (v==='team') {
    bc.innerHTML = `<span class="text-white font-semibold">Usuarios</span>`;
    act.innerHTML = '';
  } else if (v==='globals') {
    bc.innerHTML = `<span class="text-white font-semibold">Flujos y etiquetas globales</span>`;
    act.innerHTML = '';
  }
}

// ── Content ───────────────────────
function renderContent() {
  const c = document.getElementById('content');
  if (S.view==='dashboard') c.innerHTML = vDashboard();
  else if (S.view==='board') {
    if      (S.subview==='tags')       c.innerHTML = vProjectTags();
    else if (S.subview==='priorities') c.innerHTML = vProjectPriorities();
    else if (S.subview==='team')       c.innerHTML = vProjectTeam();
    else                               c.innerHTML = vBoard();
  }
  else if (S.view==='team') c.innerHTML = vTeam();
  else if (S.view==='globals') c.innerHTML = vGlobals();
}
