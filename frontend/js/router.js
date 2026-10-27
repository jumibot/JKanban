// ═══════════════════════════════════
// ROUTER
// ═══════════════════════════════════
function go(hash) { location.hash = hash; }

async function route() {
  const h = location.hash || '#/';
  if (h === '#/team') {
    if (!S.currentUser?.is_admin) { go('#/'); return; }
    S.view='team'; S.pid=null; S.tags=[]; S.priorities=[]; S.flows=[]; S.members=[]; S.subview='kanban';
  } else if (h === '#/admin/flows') {
    if (!S.currentUser?.is_admin) { go('#/'); return; }
    S.view='globals'; S.pid=null; S.tags=[]; S.priorities=[]; S.flows=[]; S.members=[]; S.subview='kanban';
    await loadGlobals();
  } else if (h.startsWith('#/board/')) {
    const parts = h.split('/');
    const newPid = parseInt(parts[2], 10);
    if (!Number.isFinite(newPid)) { go('#/'); return; }
    const sub = parts[3] || 'kanban';
    if (newPid !== S.pid) {
      S.pid = newPid;
      await loadProjectMeta();
    }
    S.subview = sub;
    S.view = 'board';
    if (sub === 'team') await loadMembers();
  } else { S.view='dashboard'; S.pid=null; S.tags=[]; S.priorities=[]; S.flows=[]; S.members=[]; S.subview='kanban'; }
  render();
}

window.addEventListener('hashchange', route);
