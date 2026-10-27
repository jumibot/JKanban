// ═══════════════════════════════════
// STATE
// ═══════════════════════════════════
const S = {
  projects:[], groups:[], tasks:[], users:[], tags:[], priorities:[], members:[],
  flows:[], gflows:[], gtags:[],   // flujos del proyecto (+ globales); panel global
  view:'dashboard', pid:null, subview:'kanban',
  currentUser: null,
};
