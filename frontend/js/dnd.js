// ═══════════════════════════════════
// DRAG AND DROP
// ═══════════════════════════════════

// ── Task drag ────────────────────
let _dragTaskId = null, _dragSrcGroupId = null, _dropTarget = null;

function onTaskDragStart(e, taskId, groupId) {
  _dragTaskId = taskId;
  _dragSrcGroupId = groupId;
  _dropTarget = null;
  e.dataTransfer.effectAllowed = 'move';
  setTimeout(() => e.target.classList.add('dragging'), 0);
}

function onTaskDragEnd(e) {
  _dragTaskId = null; _dragSrcGroupId = null; _dropTarget = null;
  e.target.classList.remove('dragging');
  document.querySelectorAll('.col-drop-active').forEach(el => el.classList.remove('col-drop-active'));
  document.querySelectorAll('.drop-before,.drop-after').forEach(el => el.classList.remove('drop-before','drop-after'));
}

function onCardDragOver(e, taskId) {
  e.preventDefault();
  const rect = e.currentTarget.getBoundingClientRect();
  const before = e.clientY < rect.top + rect.height / 2;
  document.querySelectorAll('.drop-before,.drop-after').forEach(el => el.classList.remove('drop-before','drop-after'));
  e.currentTarget.classList.toggle('drop-before', before);
  e.currentTarget.classList.toggle('drop-after', !before);
  _dropTarget = {taskId, before};
  e.dataTransfer.dropEffect = 'move';
}

function onCardDragLeave(e, taskId) {
  if (!e.currentTarget.contains(e.relatedTarget)) {
    e.currentTarget.classList.remove('drop-before','drop-after');
    if (_dropTarget?.taskId === taskId) _dropTarget = null;
  }
}

function onColDragOver(e, groupId) {
  if (!_dragTaskId) return; // column reorder drag — let it bubble to outer k-col
  e.preventDefault();
  e.stopPropagation();
  e.dataTransfer.dropEffect = 'move';
  document.getElementById('col-' + groupId).classList.add('col-drop-active');
}

function onColDragLeave(e, groupId) {
  const col = document.getElementById('col-' + groupId);
  if (!col.contains(e.relatedTarget)) col.classList.remove('col-drop-active');
}

async function onColDrop(e, targetGroupId) {
  if (!_dragTaskId) return; // let column reorder drop bubble to outer k-col
  e.preventDefault();
  e.stopPropagation();
  document.getElementById('col-' + targetGroupId).classList.remove('col-drop-active');
  document.querySelectorAll('.drop-before,.drop-after').forEach(el => el.classList.remove('drop-before','drop-after'));
  const taskId = _dragTaskId;
  const srcGroupId = _dragSrcGroupId;
  const dropTarget = _dropTarget;
  _dragTaskId = null; _dragSrcGroupId = null; _dropTarget = null;

  if (srcGroupId === targetGroupId) {
    // Within-column reorder
    const tasks = S.tasks.filter(t => t.group_id === targetGroupId).sort((a,b) => (a.sort_order??0)-(b.sort_order??0)||a.id-b.id);
    const ids = tasks.map(t => t.id).filter(id => id !== taskId);
    if (!dropTarget) {
      ids.push(taskId);
    } else {
      const idx = ids.indexOf(dropTarget.taskId);
      if (idx === -1) { ids.push(taskId); }
      else if (dropTarget.before) { ids.splice(idx, 0, taskId); }
      else { ids.splice(idx + 1, 0, taskId); }
    }
    const origIds = tasks.map(t => t.id);
    if (JSON.stringify(ids) === JSON.stringify(origIds)) return;
    try {
      await PATCH('/groups/' + targetGroupId + '/tasks/reorder', {task_ids: ids});
      await loadAll(); render();
    } catch(err) { toast(err.message, 'err'); }
  } else {
    // Cross-column move
    try {
      await PATCH('/tasks/' + taskId, {group_id: targetGroupId});
      await loadAll(); render(); toast('Tarea movida');
    } catch(err) { toast(err.message, 'err'); }
  }
}

// ── Column reorder ────────────────
let _dragGroupId = null;

function onColHeaderDragStart(e, groupId) {
  _dragGroupId = groupId;
  e.dataTransfer.effectAllowed = 'move';
  setTimeout(() => e.currentTarget.classList.add('col-dragging'), 0);
}

function onColHeaderDragEnd(e) {
  _dragGroupId = null;
  e.currentTarget.classList.remove('col-dragging');
  document.querySelectorAll('.col-reorder-before,.col-reorder-after').forEach(el => el.classList.remove('col-reorder-before','col-reorder-after'));
}

function onColReorderDragOver(e, groupId) {
  if (!_dragGroupId || _dragGroupId === groupId) return;
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  const rect = e.currentTarget.getBoundingClientRect();
  const before = e.clientX < rect.left + rect.width / 2;
  document.querySelectorAll('.col-reorder-before,.col-reorder-after').forEach(el => el.classList.remove('col-reorder-before','col-reorder-after'));
  e.currentTarget.classList.toggle('col-reorder-before', before);
  e.currentTarget.classList.toggle('col-reorder-after', !before);
}

function onColReorderDragLeave(e, groupId) {
  if (!e.currentTarget.contains(e.relatedTarget)) {
    e.currentTarget.classList.remove('col-reorder-before','col-reorder-after');
  }
}

async function onColReorderDrop(e, targetGroupId) {
  if (!_dragGroupId || _dragGroupId === targetGroupId) return;
  e.preventDefault();
  const rect = e.currentTarget.getBoundingClientRect();
  const before = e.clientX < rect.left + rect.width / 2;
  document.querySelectorAll('.col-reorder-before,.col-reorder-after').forEach(el => el.classList.remove('col-reorder-before','col-reorder-after'));
  const srcGroupId = _dragGroupId;
  _dragGroupId = null;
  document.querySelectorAll('.col-dragging').forEach(el => el.classList.remove('col-dragging'));

  const cols = S.groups.filter(g => g.project_id === S.pid).sort((a,b) => (a.sort_order??0)-(b.sort_order??0)||a.id-b.id);
  const ids = cols.map(g => g.id).filter(id => id !== srcGroupId);
  const idx = ids.indexOf(targetGroupId);
  if (before) { ids.splice(idx, 0, srcGroupId); }
  else { ids.splice(idx + 1, 0, srcGroupId); }

  try {
    await PATCH('/groups/reorder', {project_id: S.pid, group_ids: ids});
    await loadAll(); render();
  } catch(err) { toast(err.message, 'err'); }
}
