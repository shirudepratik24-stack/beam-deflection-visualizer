async function api(path, options={}) { const r=await fetch(path,{headers:{'Content-Type':'application/json'},...options}); if(!r.ok) throw new Error(await r.text()); return r.json(); }
const money=n=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(n);
async function loadAll(){
  try{
    const [p,h,health]=await Promise.all([api('/api/payments'),api('/api/history'),api('/api/health')]);
    document.getElementById('aiStatus').textContent=health.ai_configured?'AI connected':'Fallback mode';
    document.getElementById('aiStatus').className='status '+(health.ai_configured?'ok':'warn');
    document.getElementById('risk').textContent=money(p.reduce((s,x)=>s+x.amount,0));
    document.getElementById('count').textContent=p.length;
    document.getElementById('actions').textContent=h.length;
    document.getElementById('rate').textContent=p.length?Math.round((h.length/p.length)*100)+'%':'0%';
    document.getElementById('payments').innerHTML=p.map(x=>`<div class="payment"><div><strong>${x.customer}</strong><span>${x.id} · ${x.reason.replaceAll('_',' ')}</span></div><strong>${money(x.amount)}</strong><button onclick="recover('${x.id}')">Recover</button></div>`).join('');
    document.getElementById('history').innerHTML=h.length?h.map(x=>`<div class="history"><div><strong>${x.action.replaceAll('_',' ')}</strong><span>${x.payment_id} · ${new Date(x.created_at).toLocaleString()}</span></div><span class="confidence">${Math.round(x.confidence*100)}%</span><p>${x.rationale}</p><small>${x.outcome}</small></div>`).join(''):'<p class="muted">No recovery actions yet.</p>';
  }catch(e){toast('Could not load dashboard: '+e.message)}
}
async function recover(id){
  try{toast('Agent is analyzing payment…');const r=await api('/api/recover',{method:'POST',body:JSON.stringify({payment_id:id})});toast(`Decision: ${r.decision.action.replaceAll('_',' ')} · ${r.outcome}`);loadAll();}
  catch(e){toast('Recovery failed safely: '+e.message)}
}
function toast(s){const t=document.getElementById('toast');t.textContent=s;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),3500)}
document.addEventListener('DOMContentLoaded',loadAll);
