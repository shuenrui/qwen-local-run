/* arena front-end — self-contained (no external libs).
   Loads models, runs one prompt against the selected ones via the backend's
   serial orchestrator, and streams each reply live over SSE. */
const $ = id => document.getElementById(id);
let MODELS = [], ES = null, CARD = {}, BUF = {}, dirty = {}, renderPending = false;
let SELECTED = new Set(), firstLoad = true, pollTimer = null;
let LAST_JOB = null;

function escapeHtml(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

/* Compact markdown renderer: fenced code, inline code, bold, italic, links,
   headings, lists, blockquote, hr, paragraphs. Good enough for LLM output. */
function renderMarkdown(src){
  if(!src) return '';
  const blocks = [];
  src = src.replace(/```(\w*)\n?([\s\S]*?)```/g, (m,lang,code)=>{ blocks.push({lang,code}); return `\u0000C${blocks.length-1}\u0000`; });
  let html = escapeHtml(src);
  html = html.replace(/`([^`]+)`/g, (m,c)=>`<code>${c}</code>`);
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
  html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  const out=[]; let list=null, para=[];
  const flushP=()=>{ if(para.length){ out.push('<p>'+para.join(' ')+'</p>'); para=[]; } };
  const flushL=()=>{ if(list){ out.push(`</${list}>`); list=null; } };
  for(const line of html.split('\n')){
    const cm = line.match(/^\u0000C(\d+)\u0000$/);
    if(cm){ flushP(); flushL(); const b=blocks[+cm[1]];
      out.push(`<pre class="code"><div class="code-head"><span>${b.lang||'code'}</span><button class="copy">copy</button></div><code>${escapeHtml(b.code.replace(/\n$/,''))}</code></pre>`); continue; }
    let m;
    if((m=line.match(/^(#{1,6})\s+(.*)$/))){ flushP(); flushL(); const l=m[1].length; out.push(`<h${l}>${m[2]}</h${l}>`); continue; }
    if(/^\s*([-*_]){3,}\s*$/.test(line)){ flushP(); flushL(); out.push('<hr>'); continue; }
    if((m=line.match(/^\s*&gt;\s?(.*)$/))){ flushP(); flushL(); out.push(`<blockquote>${m[1]}</blockquote>`); continue; }
    if((m=line.match(/^\s*[-*+]\s+(.*)$/))){ flushP(); if(list!=='ul'){flushL();out.push('<ul>');list='ul';} out.push(`<li>${m[1]}</li>`); continue; }
    if((m=line.match(/^\s*\d+\.\s+(.*)$/))){ flushP(); if(list!=='ol'){flushL();out.push('<ol>');list='ol';} out.push(`<li>${m[1]}</li>`); continue; }
    if(line.trim()===''){ flushP(); flushL(); continue; }
    flushL(); para.push(line.trim());
  }
  flushP(); flushL();
  return out.join('\n');
}

/* Throttled re-render of a card body while tokens stream in. */
function scheduleRender(mid){
  dirty[mid]=true;
  if(renderPending) return;
  renderPending=true;
  setTimeout(()=>{ renderPending=false;
    for(const k in dirty){ if(dirty[k] && CARD[k]){ renderBody(k); dirty[k]=false; } }
  }, 80);
}
function renderBody(mid){
  const b=BUF[mid], c=CARD[mid]; if(!b||!c) return;
  let html=renderMarkdown(b.content);
  if(c.streaming) html+='<span class="cursor"></span>';
  c.body.innerHTML=html;
  if(b.reasoning) c.reasoningEl.innerHTML=renderMarkdown(b.reasoning);
}

async function fetchModels(){
  const r=await fetch('/api/models'); const j=await r.json(); MODELS=j.models;
}

function modelCard(m){
  const wrap=document.createElement('div');
  const dis=(m.engine!=='sglang');
  wrap.className='model'+(dis?' disabled':'');
  if(dis) wrap.title='manual-only lane (ENGINE='+m.engine+'): boot it yourself, then untick auto';
  const eng=m.engine==='sglang'?'SGLang':m.engine;
  let left='<span class="ckspacer"></span>', badges=`<span class="badge">${eng}</span>`, control='';
  if(dis){
    badges+='<span class="badge">manual-only</span>';
    control='<div class="mid">boot from its own repo</div>';
  } else if(m.cached){
    left=`<input type="checkbox" class="msel" data-id="${m.id}" ${SELECTED.has(m.id)?'checked':''}>`;
    badges+=`<span class="badge ok">● ${m.cached_gib}GB</span>`;
  } else if(m.dl_status==='downloading'){
    const pct=m.dl_total_gib?Math.min(100,Math.round(100*m.dl_got_gib/m.dl_total_gib)):0;
    badges+=`<span class="badge">downloading ${pct}%</span>`;
    control=`<div class="dl"><div class="bar"><i style="width:${pct}%"></i></div>`+
      `<div class="mid">${m.dl_got_gib} / ${m.dl_total_gib||'?'} GB${m.dl_speed_mbs?' · '+m.dl_speed_mbs+' MB/s':''}`+
      ` <a href="#" class="cancel" data-mid="${escapeHtml(m.model_id)}">cancel</a></div></div>`;
  } else if(m.dl_status==='error'){
    badges+='<span class="badge no">● failed</span>';
    control=`<div class="mid err">${escapeHtml((m.dl_error||'').slice(0,140))}</div>`+
      `<button class="dl-btn" data-mid="${escapeHtml(m.model_id)}">↻ Retry download</button>`;
  } else {
    badges+='<span class="badge no">● needs download</span>';
    const sz=m.dl_total_gib?` ${m.dl_total_gib} GB`:'';
    control=`<button class="dl-btn" data-mid="${escapeHtml(m.model_id)}">⬇ Download${sz}</button>`;
  }
  wrap.innerHTML=`${left}<span class="mtext"><span class="nm">${escapeHtml(m.label)}</span>${badges}`+
    `<br><span class="mid">${escapeHtml(m.model_id)}</span>${control}</span>`;
  const ck=wrap.querySelector('input.msel');
  if(ck) ck.onchange=e=>{ if(e.target.checked) SELECTED.add(m.id); else SELECTED.delete(m.id); };
  const btn=wrap.querySelector('.dl-btn');
  if(btn) btn.onclick=()=>startDl(btn.dataset.mid, btn);
  const cx=wrap.querySelector('.cancel');
  if(cx) cx.onclick=e=>{ e.preventDefault(); cancelDl(cx.dataset.mid); };
  return wrap;
}

function renderModels(){
  const box=$('models'); box.innerHTML='';
  if(!MODELS.length){ box.innerHTML='<span class="no">no profiles found in profiles/*.env</span>'; return; }
  if(firstLoad){ MODELS.forEach(m=>{ if(m.cached && m.engine==='sglang') SELECTED.add(m.id); }); firstLoad=false; }
  MODELS.forEach(m=>box.appendChild(modelCard(m)));
  const anyDl=MODELS.some(m=>m.dl_status==='downloading');
  if(anyDl && !pollTimer) pollTimer=setInterval(pollModels, 2000);
  if(!anyDl && pollTimer){ clearInterval(pollTimer); pollTimer=null; }
}

async function pollModels(){ try{ await fetchModels(); renderModels(); }catch(e){} }

async function loadModels(){
  try{ await fetchModels(); }
  catch(e){ $('models').innerHTML='<span class="no">failed to load models: '+escapeHtml(String(e))+'</span>'; return; }
  renderModels();
}

async function startDl(mid, btn){
  if(btn){ btn.disabled=true; btn.textContent='starting…'; }
  try{
    const r=await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:mid})});
    const j=await r.json().catch(()=>({}));
    if(!r.ok){ alert('Download error: '+(j.error||('HTTP '+r.status))); if(btn){btn.disabled=false;btn.textContent='⬇ Download';} return; }
  }catch(e){ alert('Download request failed: '+e); if(btn){btn.disabled=false;btn.textContent='⬇ Download';} return; }
  if(!pollTimer) pollTimer=setInterval(pollModels, 2000);
  pollModels();
}

async function cancelDl(mid){
  try{ await fetch('/api/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:mid})}); }catch(e){}
  pollModels();
}

function buildCards(ids){
  const cards=$('cards'); cards.innerHTML=''; CARD={}; BUF={}; dirty={};
  const tb=$('score').querySelector('tbody'); tb.innerHTML='';
  ids.forEach(id=>{
    const m=MODELS.find(x=>x.id===id)||{label:id};
    const card=document.createElement('div'); card.className='card';
    card.innerHTML=`<header><h3>${escapeHtml(m.label)}</h3><span class="st">queued</span></header>
      <div class="metrics"></div>
      <details class="reasoning" hidden><summary>thinking</summary><div class="rbody"></div></details>
      <div class="body"></div>`;
    cards.appendChild(card);
    const tr=document.createElement('tr');
    tr.innerHTML=`<td>${escapeHtml(m.label)}</td><td class="c-st">queued</td><td class="c-ttft">—</td><td class="c-total">—</td><td class="c-tps">—</td><td class="c-tok">—</td>`;
    tb.appendChild(tr);
    CARD[id]={el:card,status:card.querySelector('.st'),metrics:card.querySelector('.metrics'),
      body:card.querySelector('.body'),reasoningEl:card.querySelector('.rbody'),
      reasoningBox:card.querySelector('.reasoning'),row:tr,streaming:false};
    BUF[id]={content:'',reasoning:''};
  });
  $('score').hidden=false;
}

function setStatus(id,text){
  const c=CARD[id]; if(!c) return;
  c.status.textContent=text;
  if(c.row) c.row.querySelector('.c-st').textContent=text;
}

function openStream(jid){
  LAST_JOB=jid;
  if(ES) ES.close();
  ES=new EventSource('/api/jobs/'+jid+'/stream');
  ES.onmessage=e=>{
    let ev; try{ ev=JSON.parse(e.data); }catch(_){ return; }
    const id=ev.model;
    switch(ev.type){
      case 'status':
        setStatus(id,ev.status);
        if(CARD[id]) CARD[id].streaming=(ev.status==='running');
        break;
      case 'delta':
        if(!BUF[id]) break;
        if(ev.kind==='reasoning'){ BUF[id].reasoning+=ev.text; if(CARD[id]) CARD[id].reasoningBox.hidden=false; }
        else BUF[id].content+=ev.text;
        scheduleRender(id);
        break;
      case 'done':
        if(CARD[id]) CARD[id].streaming=false;
        setStatus(id,'done');
        if(CARD[id]) CARD[id].metrics.innerHTML=
          `<span class="pill">TTFT <b>${ev.ttft_s}s</b></span><span class="pill">total <b>${ev.total_s}s</b></span>`+
          `<span class="pill"><b>${ev.toks_per_s}</b> tok/s</span><span class="pill">tokens <b>${ev.tokens}</b>${ev.estimated?' (est)':''}</span>`;
        if(CARD[id]&&CARD[id].row){ const r=CARD[id].row;
          r.querySelector('.c-ttft').textContent=ev.ttft_s+'s'; r.querySelector('.c-total').textContent=ev.total_s+'s';
          r.querySelector('.c-tps').textContent=ev.toks_per_s; r.querySelector('.c-tok').textContent=ev.tokens; }
        renderBody(id);
        break;
      case 'error':
        if(CARD[id]) CARD[id].streaming=false;
        setStatus(id,'error');
        if(CARD[id]) CARD[id].body.innerHTML='<div class="err">⚠ '+escapeHtml(ev.error)+'</div>';
        break;
      case 'job-done':
        $('saved').textContent='saved → '+ev.saved_dir;
        document.querySelectorAll('#export .exp').forEach(a=>{ a.href='/api/jobs/'+LAST_JOB+'/export?fmt='+a.dataset.fmt; });
        $('export').hidden=false;
        break;
      case 'end':
        $('status').textContent='done'; $('run').disabled=false;
        if(ES) ES.close(); ES=null;
        break;
    }
  };
  ES.onerror=()=>{ $('status').textContent=$('status').textContent||'stream ended'; $('run').disabled=false; if(ES) ES.close(); ES=null; };
}

$('run').onclick=async()=>{
  const ids=[...document.querySelectorAll('.msel:checked')].map(e=>e.dataset.id);
  if(!ids.length){ $('status').textContent='select ≥1 model'; return; }
  const prompt=$('prompt').value.trim();
  if(!prompt){ $('status').textContent='type a prompt'; return; }
  const temp=$('temp').value===''?null:parseFloat($('temp').value);
  const body={prompt,models:ids,thinking:$('thinking').checked,
    max_tokens:parseInt($('maxtok').value,10)||2000,temperature:temp,
    engine:$('engine').value,auto:$('auto').checked};
  $('run').disabled=true; $('status').textContent='queued…';
  $('results').hidden=false; $('saved').textContent='';
  buildCards(ids);
  let r;
  try{ r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); }
  catch(e){ $('status').textContent='request failed'; $('run').disabled=false; return; }
  const j=await r.json().catch(()=>({}));
  if(!r.ok){ $('status').textContent='error: '+(j.error||('HTTP '+r.status)); $('run').disabled=false; return; }
  $('status').textContent='running… (serial)';
  openStream(j.job_id);
};

/* copy buttons on rendered code blocks */
document.addEventListener('click',e=>{
  if(e.target.classList&&e.target.classList.contains('copy')){
    const pre=e.target.closest('pre'); const code=pre&&pre.querySelector('code');
    if(code&&navigator.clipboard) navigator.clipboard.writeText(code.innerText)
      .then(()=>{ e.target.textContent='copied'; setTimeout(()=>e.target.textContent='copy',1200); });
  }
});

loadModels();
