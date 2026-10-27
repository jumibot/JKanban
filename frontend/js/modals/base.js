// ═══════════════════════════════════
// MODAL SYSTEM — Base
// ═══════════════════════════════════
const COLS = ['#F97316','#EF4444','#F59E0B','#10B981','#3B82F6','#8B5CF6','#EC4899','#14B8A6','#6366F1','#6B7280'];
const ICNS = ['rocket_launch','code','folder','settings','hub','layers','memory','terminal','cloud','storage',
              'lock','security','bug_report','build','star','science','psychology','bolt','diamond','flag',
              'emergency','arrow_upward','arrow_downward','remove','priority_high'];

function swatches(sel, nm) {
  return `<div class="flex flex-wrap gap-2">${COLS.map(c=>`<div class="cswatch ${c===sel?'on':''}" style="background:${c}" data-c="${c}" onclick="pickColor(this,'${nm}')"></div>`).join('')}</div>`;
}
function iconGrid(sel, nm) {
  return `<div class="flex flex-wrap gap-1">${ICNS.map(ic=>`<div class="iopt ${ic===sel?'on':''}" data-ic="${ic}" onclick="pickIcon(this,'${nm}')"><span class="ms" style="font-size:17px">${ic}</span></div>`).join('')}</div>`;
}
function pickColor(el, nm) {
  el.closest('.flex').querySelectorAll('.cswatch').forEach(s=>s.classList.remove('on'));
  el.classList.add('on');
  fld(nm).value = el.dataset.c;
}
function pickIcon(el, nm) {
  el.closest('.flex').querySelectorAll('.iopt').forEach(s=>s.classList.remove('on'));
  el.classList.add('on');
  fld(nm).value = el.dataset.ic;
}
function fld(nm) {
  return document.getElementById('modal-inner').querySelector(`[name="${nm}"]`);
}

function showModal(html) {
  document.getElementById('modal-inner').innerHTML = html;
  document.getElementById('modal-bg').classList.add('open');
}
function closeM() {
  document.getElementById('modal-bg').classList.remove('open');
  document.querySelector('.modal-box').classList.remove('modal-lg');
}
function bgClose(e) { if (e.target===document.getElementById('modal-bg')) closeM(); }

function mhdr(title, sub) {
  return `<div class="-mx-6 -mt-6 px-6 py-4 mb-5 rounded-t-2xl flex items-start justify-between" style="background:linear-gradient(135deg,rgba(249,115,22,.13) 0%,rgba(13,24,41,.4) 100%);border-bottom:1px solid rgba(249,115,22,.15)">
    <div>
      <h2 class="text-base font-bold text-white">${title}</h2>
      ${sub?`<p class="text-xs text-slate-500 mt-0.5">${sub}</p>`:''}
    </div>
    <button class="btn-icon -mt-1 -mr-2" onclick="closeM()"><span class="ms ms-sm">close</span></button>
  </div>`;
}
function mfoot(saveLabel, showDanger, dangerFn) {
  return `<div class="flex gap-2.5 justify-end mt-5">
    ${showDanger?`<button type="button" class="btn btn-danger mr-auto" onclick="${dangerFn}">Eliminar</button>`:''}
    <button type="button" class="btn btn-ghost" onclick="closeM()">Cancelar</button>
    <button type="submit" class="btn btn-primary">${saveLabel}</button>
  </div>`;
}
