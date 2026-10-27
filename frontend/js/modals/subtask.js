// ═══════════════════════════════════
// MODAL: Subtask (todos)
// ═══════════════════════════════════
async function loadTodos(taskId) {
  try {
    const todos = await GET(`/tasks/${taskId}/todos`);
    renderTodos(taskId, todos);
  } catch(e) {}
}

function renderTodos(taskId, todos) {
  const el = document.getElementById('todos-list');
  if (!el) return;
  if (!todos.length) { el.innerHTML = ''; return; }
  el.innerHTML = todos.map(td => `
    <div class="flex items-center gap-3 bg-slate-900/40 px-4 py-3 rounded-xl border group cursor-pointer transition-all ${td.completed ? 'border-slate-700/10' : 'border-slate-700/20 hover:border-orange-500/30'}" id="todo-row-${td.id}" onclick="toggleTodo(${taskId},${td.id},${!td.completed})">
      <div class="w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center transition-all ${td.completed ? 'bg-orange-500' : 'border-2 border-slate-600 group-hover:border-orange-500'}">
        ${td.completed ? '<span class="ms ms-xs text-white" style="font-size:12px">check</span>' : ''}
      </div>
      <span class="text-sm flex-1 leading-snug ${td.completed ? 'line-through text-slate-600' : 'text-slate-300'}">${esc(td.title)}</span>
      <button type="button" class="opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 ms ms-xs text-slate-500 hover:text-red-400"
        onclick="event.stopPropagation();deleteTodo(${taskId},${td.id})">close</button>
    </div>`).join('');
}

async function addTodo(taskId) {
  const inp = document.getElementById('new-todo-inp');
  if (!inp || !inp.value.trim()) return;
  const title = inp.value.trim();
  try {
    await POST(`/tasks/${taskId}/todos`, {title});
    inp.value = '';
    const todos = await GET(`/tasks/${taskId}/todos`);
    renderTodos(taskId, todos);
    const task = S.tasks.find(t => t.id === taskId);
    if (task) { task.todos_total = todos.length; task.todos_completed = todos.filter(t=>t.completed).length; render(); }
  } catch(e) { toast(e.message, 'err'); }
}

async function toggleTodo(taskId, todoId, completed) {
  try {
    await PATCH(`/tasks/${taskId}/todos/${todoId}`, {completed});
    const todos = await GET(`/tasks/${taskId}/todos`);
    renderTodos(taskId, todos);
    const task = S.tasks.find(t => t.id === taskId);
    if (task) { task.todos_total = todos.length; task.todos_completed = todos.filter(t=>t.completed).length; render(); }
  } catch(e) { toast(e.message, 'err'); }
}

async function deleteTodo(taskId, todoId) {
  try {
    await req('DELETE', `/tasks/${taskId}/todos/${todoId}`);
    const todos = await GET(`/tasks/${taskId}/todos`);
    renderTodos(taskId, todos);
    const task = S.tasks.find(t => t.id === taskId);
    if (task) { task.todos_total = todos.length; task.todos_completed = todos.filter(t=>t.completed).length; render(); }
  } catch(e) { toast(e.message, 'err'); }
}
