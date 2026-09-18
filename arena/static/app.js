/* arena front-end — self-contained (no external libs).
   Loads models, runs one prompt against the selected ones via the backend's
   serial orchestrator, and streams each reply live over SSE. */
const $ = id => document.getElementById(id);
let MODELS = [], ES = null, CARD = {}, BUF = {}, dirty = {}, renderPending = false;
let SELECTED = new Set(), firstLoad = true, pollTimer = null, LASTMAX = 2000;
let LAST_JOB = null;
let VOTED = false, REVEALED = false;
let CHALLENGES = [], GRADES = {}, HAS_CHECKS = false;

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
      out.push(`<pre class="code"><div class="code-head"><span>${b.lang||'code'}</span><button class="copy">copy</button></div><code>${hl(b.code.replace(/\n$/,''), b.lang)}</code></pre>`); continue; }
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

function buildCards(slots){
  const cards=$('cards'); cards.innerHTML=''; CARD={}; BUF={}; dirty={};
  const tb=$('score').querySelector('tbody'); tb.innerHTML='';
  slots.forEach(s=>{
    const card=document.createElement('div'); card.className='card';
    card.innerHTML=`<header><h3>Model ${s}</h3><span class="st">queued</span>
        <span class="tabs" hidden><a class="tab on" data-t="r">Rendered</a><a class="tab" data-t="p">Preview</a></span>
        <button class="votebtn" hidden>🥇 Vote</button></header>
      <div class="metrics"></div>
      <details class="reasoning" hidden><summary>thinking</summary><div class="rbody"></div></details>
      <div class="body"></div>`;
    cards.appendChild(card);
    const tr=document.createElement('tr');
    tr.innerHTML=`<td>Model ${s}</td><td class="c-st">queued</td><td class="c-ttft">—</td><td class="c-total">—</td><td class="c-tps">—</td><td class="c-tok">—</td>`;
    tb.appendChild(tr);
    CARD[s]={el:card,slot:s.replace(/[0-9]+$/,''),key:s,h3:card.querySelector('h3'),status:card.querySelector('.st'),
      metrics:card.querySelector('.metrics'),body:card.querySelector('.body'),
      reasoningEl:card.querySelector('.rbody'),reasoningBox:card.querySelector('.reasoning'),
      tabs:card.querySelector('.tabs'),vote:card.querySelector('.votebtn'),
      row:tr,streaming:false,frame:null,errors:0,shownTab:'r',errPill:null,okPill:null,passPill:null};
    BUF[s]={content:'',reasoning:''};
    const t=card.querySelectorAll('.tab');
    t[0].onclick=()=>showTab(s,'r');
    t[1].onclick=()=>showTab(s,'p');
    CARD[s].vote.onclick=()=>postVote(CARD[s].slot);
  });
  HAS_CHECKS=false;
  $('score').hidden=false; $('tiebtn').hidden=true; $('reveal').hidden=true;
}

function setStatus(id,text){
  const c=CARD[id]; if(!c) return;
  c.status.textContent=text;
  if(c.row) c.row.querySelector('.c-st').textContent=text;
}

function openStream(jid){
  LAST_JOB=jid; VOTED=false; REVEALED=false;
  if(ES) ES.close();
  ES=new EventSource('/api/jobs/'+jid+'/stream');
  ES.onmessage=e=>{
    let ev; try{ ev=JSON.parse(e.data); }catch(_){ return; }
    const sl=ev.slot;
    switch(ev.type){
      case 'status':
        setStatus(sl,ev.status);
        if(CARD[sl]) CARD[sl].streaming=(ev.status==='running');
        break;
      case 'delta':
        if(!BUF[sl]) break;
        if(ev.kind==='reasoning'){ BUF[sl].reasoning+=ev.text; if(CARD[sl]) CARD[sl].reasoningBox.hidden=false; }
        else BUF[sl].content+=ev.text;
        scheduleRender(sl);
        break;
      case 'done':
        if(CARD[sl]) CARD[sl].streaming=false;
        setStatus(sl,'done');
        if(CARD[sl]) CARD[sl].metrics.innerHTML=
          `<span class="pill">TTFT <b>${ev.ttft_s}s</b></span><span class="pill">total <b>${ev.total_s}s</b></span>`+
          `<span class="pill"><b>${ev.toks_per_s}</b> tok/s</span><span class="pill">tokens <b>${ev.tokens}</b>${ev.estimated?' (est)':''}</span>`+
          (ev.tokens>=LASTMAX?'<span class="pill no" title="generation stopped at max_tokens — raise the limit or reselect the challenge preset">⚠ truncated</span>':'');
        if(CARD[sl]&&CARD[sl].row){ const r=CARD[sl].row;
          r.querySelector('.c-ttft').textContent=ev.ttft_s+'s'; r.querySelector('.c-total').textContent=ev.total_s+'s';
          r.querySelector('.c-tps').textContent=ev.toks_per_s; r.querySelector('.c-tok').textContent=ev.tokens; }
        renderBody(sl);
        if(CARD[sl]){
          if(CARD[sl].tabs && detectHtml(BUF[sl].content)) CARD[sl].tabs.hidden=false;
          (ev.checks||[]).forEach(d=>{
            if(d.type) HAS_CHECKS=true;
            const p=document.createElement('span'); p.className='pill '+(d.pass?'ok':'no');
            p.title=d.out||''; p.textContent=(d.pass?'✓ ':'✗ ')+d.type;
            CARD[sl].metrics.appendChild(p);
          });
          (ev.dom||[]).forEach(d=>HAS_CHECKS=true);
          if(ev.passed===true) markPass(sl,'✅ pass',true);
          else if(ev.passed===false) markPass(sl,'❌ fail',false);
          else if(ev.dom && ev.dom.length){ markPass(sl,'dom: checking…',null); requestDomChecks(sl, ev.dom); }
        }
        break;
      case 'error':
        if(CARD[sl]) CARD[sl].streaming=false;
        setStatus(sl,'error');
        if(CARD[sl]) CARD[sl].body.innerHTML='<div class="err">⚠ '+escapeHtml(ev.error)+'</div>';
        break;
      case 'stopped':
        if(CARD[sl]) CARD[sl].streaming=false;
        setStatus(sl,'stopped');
        renderBody(sl);
        if(CARD[sl]&&![...CARD[sl].metrics.querySelectorAll('.pill')].some(p=>p.textContent.includes('stopped')))
          CARD[sl].metrics.insertAdjacentHTML('beforeend',
            '<span class="pill no" title="stopped by user — partial output kept">■ stopped</span>');
        break;
      case 'job-done':
        $('stop').hidden=true;
        $('saved').textContent=(ev.stopped?'stopped · partial run saved → ':'saved → ')+ev.saved_dir;
        if(!ev.stopped && HAS_CHECKS && ev.rates){
          const bits=Object.keys(ev.rates).sort().map(s=>{ const e=ev.rates[s];
            return `${s}: pass@1 ${e.pass1?'✓':'✗'} · ${e.n_pass}/${e.k} reps`; });
          if(bits.length) $('saved').textContent += '   ·   '+bits.join('  |  ');
        }
        document.querySelectorAll('#export .exp').forEach(a=>{ a.href='/api/jobs/'+LAST_JOB+'/export?fmt='+a.dataset.fmt; });
        $('export').hidden=false;
        if(!ev.stopped) showVoting();
        break;
      case 'end':
        $('status').textContent='done — read side-by-side, Preview if it is code, then vote';
        $('run').disabled=false;
        $('stop').hidden=true;
        if(ES) ES.close(); ES=null;
        break;
    }
  };
  ES.onerror=()=>{ $('status').textContent=$('status').textContent||'stream ended'; $('run').disabled=false; if(ES) ES.close(); ES=null; };
}

/* ---------------------- blind voting + reveal ---------------------- */
function showVoting(){
  if(VOTED) return;
  Object.values(CARD).forEach(c=>{ c.vote.hidden=false; });
  if(Object.keys(CARD).length>1) $('tiebtn').hidden=false;
}
async function postVote(pick){
  if(VOTED || !LAST_JOB) return;
  let r;
  try{ r=await fetch('/api/vote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job:LAST_JOB,pick})}); }
  catch(e){ $('status').textContent='vote failed'; return; }
  if(!r.ok){ const j=await r.json().catch(()=>({})); $('status').textContent='vote: '+(j.error||('HTTP '+r.status)); return; }
  VOTED=true;
  Object.values(CARD).forEach(c=>{ c.vote.hidden=true; });
  $('tiebtn').hidden=true; $('reveal').hidden=false;
  $('status').textContent='vote locked in — click Reveal names when ready';
}
async function revealNames(){
  if(REVEALED || !LAST_JOB) return;
  let j; try{ j=await (await fetch('/api/jobs/'+LAST_JOB)).json(); }catch(e){ return; }
  REVEALED=true;
  (j.results||[]).forEach(r=>{
    const c=CARD[r.key||r.slot]; if(!c) return;
    c.h3.textContent = r.label || r.name || c.key;
    c.row.querySelector('td').textContent = (r.label || r.name || c.key)+(r.rep>1?` rep${r.rep}`:'');
  });
  const pick=(j.vote && j.vote.pick)||'';
  if(pick && pick!=='TIE'){
    const w=(j.results||[]).find(r=>r.slot===pick);
    const c=w && CARD[w.slot];
    if(c){ c.el.classList.add('won'); c.h3.textContent='🏆 '+c.h3.textContent; }
  }
  $('reveal').hidden=true;
  $('status').textContent='revealed — scoreboard updated';
  refreshScores();
}
$('tiebtn').onclick=()=>postVote('TIE');
$('reveal').onclick=revealNames;

/* ------------------------- sandboxed preview ------------------------- */
function detectHtml(text){
  if(!text) return null;
  if(/<!doctype\s+html|<html[\s>]/i.test(text)) return {doc:true, html:text};
  const m=text.match(/```(?:html|xml)?\s*\n([\s\S]*?)```/i);
  if(m && /<[a-z!]/i.test(m[1])) return {doc:false, html:m[1]};
  return null;
}
const SHIM='<script>'+
  'window.onerror=function(m){parent.postMessage({__arenaPreview:1,err:String(m)},"*")};'+
  'window.addEventListener("unhandledrejection",function(e){parent.postMessage({__arenaPreview:1,err:"promise: "+e.reason},"*")});'+
  '<\/script>';
function buildPreviewHtml(sl){
  const d=detectHtml((BUF[sl]&&BUF[sl].content)||''); if(!d) return null;
  if(d.doc){
    return /<head[^>]*>/i.test(d.html) ? d.html.replace(/<head[^>]*>/i, m=>m+SHIM) : SHIM+d.html;
  }
  return '<!doctype html><html><head><meta charset="utf-8">'+
    '<meta name="viewport" content="width=device-width,initial-scale=1">'+
    '<style>body{font-family:system-ui,sans-serif;margin:1rem;background:#fff;color:#111}</style>'+
    SHIM+'</head><body>'+d.html+'</body></html>';
}
function showTab(sl,which){
  const c=CARD[sl]; if(!c) return;
  c.el.querySelectorAll('.tab').forEach(t=>t.classList.toggle('on', t.dataset.t===which));
  if(which==='p'){
    const html=buildPreviewHtml(sl); if(!html) return;
    c.errors=0;
    if(c.errPill){ c.errPill.remove(); c.errPill=null; }
    if(c.okPill){ c.okPill.remove(); c.okPill=null; }
    if(!c.frame){
      c.frame=document.createElement('iframe');
      c.frame.className='preview';
      c.frame.setAttribute('sandbox','allow-scripts allow-modals allow-forms allow-popups');
      c.frame.setAttribute('title','model-generated page (sandboxed)');
    }
    c.frame.srcdoc=html;
    c.body.innerHTML=''; c.body.appendChild(c.frame);
    c.shownTab='p';
    setTimeout(()=>{
      if(c.shownTab!=='p' || c.errors>0 || c.okPill) return;
      c.okPill=document.createElement('span'); c.okPill.className='pill ok';
      c.okPill.textContent='0 runtime errors ✓'; c.metrics.appendChild(c.okPill);
    }, 6000);
  } else {
    c.shownTab='r';
    if(c.frame) c.frame.remove();
    renderBody(sl);
  }
}
window.addEventListener('message',e=>{
  const d=e.data; if(!d || !d.__arenaPreview || !d.err) return;
  for(const sl in CARD){
    const c=CARD[sl];
    if(c.frame && c.frame.contentWindow===e.source){
      c.errors++;
      if(c.okPill){ c.okPill.remove(); c.okPill=null; }
      if(!c.errPill){ c.errPill=document.createElement('span'); c.errPill.className='pill no'; c.metrics.appendChild(c.errPill); }
      c.errPill.textContent='⚠ '+c.errors+' runtime error'+(c.errors>1?'s':'')+': '+String(d.err).slice(0,90);
      return;
    }
  }
});

/* ---------------------------- scoreboard ---------------------------- */
async function refreshScores(){
  let j; try{ j=await (await fetch('/api/scores')).json(); }catch(e){ return; }
  const tb=$('sboard').querySelector('tbody'); tb.innerHTML='';
  const rows=j.rows||[];
  if(!rows.length){
    tb.innerHTML='<tr><td colspan="6" style="color:var(--muted)">no votes yet — run a comparison, then vote blind</td></tr>';
    return;
  }
  rows.forEach(r=>{
    const tr=document.createElement('tr');
    tr.innerHTML=`<td>${escapeHtml(r.label||r.id)}</td><td>${r.votes}</td><td>${r.wins}</td>`+
      `<td>${r.ties}</td><td>${r.losses}</td><td><b>${r.win_rate}%</b></td>`;
    tb.appendChild(tr);
  });
}
$('srefresh').onclick=e=>{ e.preventDefault(); refreshScores(); };

$('run').onclick=async()=>{
  const ids=[...document.querySelectorAll('.msel:checked')].map(e=>e.dataset.id);
  if(!ids.length){ $('status').textContent='select ≥1 model'; return; }
  const prompt=$('prompt').value.trim();
  if(!prompt){ $('status').textContent='type a prompt'; return; }
  const temp=$('temp').value===''?null:parseFloat($('temp').value);
  const body={prompt,models:ids,thinking:$('thinking').checked,
    max_tokens:Math.min(parseInt($('maxtok').value,10)||32000,32000),temperature:temp,
    engine:$('engine').value,auto:$('auto').checked,
    runs:parseInt($('runs').value,10)||1};
  LASTMAX=body.max_tokens;
  if($('challenge').value) body.challenge=$('challenge').value;
  $('run').disabled=true; $('status').textContent='queued…';
  $('results').hidden=false; $('saved').textContent=''; $('export').hidden=true;
  let r, j;
  try{
    r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    j=await r.json().catch(()=>({}));
  }catch(e){ $('status').textContent='request failed'; $('run').disabled=false; return; }
  if(!r.ok){ $('status').textContent='error: '+(j.error||('HTTP '+r.status)); $('run').disabled=false; return; }
  buildCards(j.order||[]);
  $('status').textContent='running… (serial, blind)';
  $('stop').hidden=false; $('stop').disabled=false; $('stop').textContent='■ Stop';
  openStream(j.job_id);
};

$('stop').onclick=async()=>{
  if(!LAST_JOB) return;
  $('stop').disabled=true; $('stop').textContent='stopping…';
  let r;
  try{ r=await fetch('/api/stop',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({job:LAST_JOB})}); }
  catch(e){ $('stop').disabled=false; $('stop').textContent='■ Stop'; return; }
  if(!r.ok){ const j=await r.json().catch(()=>({}));
    $('stop').disabled=false; $('stop').textContent='■ Stop';
    $('status').textContent='stop refused: '+(j.error||('HTTP '+r.status)); }
};

/* copy buttons on rendered code blocks */
document.addEventListener('click',e=>{
  if(e.target.classList&&e.target.classList.contains('copy')){
    const pre=e.target.closest('pre'); const code=pre&&pre.querySelector('code');
    if(code&&navigator.clipboard) navigator.clipboard.writeText(code.innerText)
      .then(()=>{ e.target.textContent='copied'; setTimeout(()=>e.target.textContent='copy',1200); });
  }
});

/* ------------------------ tiny offline highlighter ------------------------ */
function hl(code, lang){
  lang=(lang||'').toLowerCase();
  const py=lang==='python', jsl=/(js|ts|javascript|typescript|jsx|tsx)/.test(lang);
  if(!py && !jsl) return escapeHtml(code);
  const kw=py?/^(def|class|return|if|elif|else|for|while|in|not|and|or|import|from|as|with|try|except|finally|raise|lambda|None|True|False|yield|async|await|pass|break|continue)$/
            :/^(function|const|let|var|return|if|else|for|while|switch|case|new|class|this|typeof|try|catch|finally|throw|async|await|null|undefined|true|false|import|export|from)$/;
  const re=/("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|#[^\n]*|\/\/[^\n]*|\b[A-Za-z_]\w*\b|\b\d+(?:\.\d+)?\b)/g;
  return code.split(re).map(tok=>{
    if(tok==null || tok==='') return '';
    if(/^(?:"""|'''|"|')/.test(tok)) return '<span class="hs">'+escapeHtml(tok)+'</span>';
    if(/^#|^\/\//.test(tok)) return '<span class="hc">'+escapeHtml(tok)+'</span>';
    if(/^\d/.test(tok)) return '<span class="hn">'+escapeHtml(tok)+'</span>';
    if(kw.test(tok)) return '<span class="hk">'+escapeHtml(tok)+'</span>';
    return escapeHtml(tok);
  }).join('');
}

/* ----------------------------- challenges ----------------------------- */
async function loadChallenges(){
  let j; try{ j=await (await fetch('/api/challenges')).json(); }catch(e){ return; }
  CHALLENGES=j.challenges||[];
  const sel=$('challenge');
  sel.innerHTML='<option value="">custom…</option>';
  CHALLENGES.forEach(c=>{
    const o=document.createElement('option'); o.value=c.id;
    const nchk=(c.server_checks||0)+(c.dom_checks||0);
    o.textContent=`${c.name} [${c.category}${nchk?` · ${nchk} check${nchk>1?'s':''}`:''}${c.runs>1?` · ×${c.runs}`:''}]`;
    sel.appendChild(o);
  });
  // A browser reload can restore the select without firing onchange; resync the form.
  if(sel.value) applyChallenge();
}
function applyChallenge(){
  const c=CHALLENGES.find(x=>x.id===$('challenge').value);
  const hint=$('chint');
  if(!c){ hint.hidden=true; return; }
  $('prompt').value=c.prompt||'';
  $('thinking').checked=!!c.thinking;
  $('maxtok').value=c.max_tokens||2000;
  $('runs').value=c.runs||1;
  if(c.engine) $('engine').value=c.engine;
  if(c.temperature!=null) $('temp').value=c.temperature;
  hint.hidden=false;
  hint.textContent=`${c.name} · ${c.category} · checks: `+
    ((c.checks||[]).map(k=>k.type).join(', ')||'none (showcase — vote only)')+
    ' · pass@1 reported after the run';
}
$('challenge').onchange=applyChallenge;

/* ------------------ DOM grading via hidden sandboxed iframe ------------------ */
const CHECK_SHIM='<script>(function(){var errs=[];window.onerror=function(m){errs.push(String(m));return false;};'+
 'window.addEventListener("unhandledrejection",function(e){errs.push("promise: "+e.reason);});'+
 'var raf=0,orAF=window.requestAnimationFrame;window.requestAnimationFrame=function(c){raf++;return orAF.call(window,function(t){c(t);});};'+
 'var gCtx=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(t,a){'+
 'if(a&&(t==="webgl"||t==="webgl2"||t==="experimental-webgl")){a=Object.assign({},a);a.preserveDrawingBuffer=true;}'+
 'return gCtx.call(this,t,a);};'+
 'var specs=%%SPECS%%,out=[],sent=false,started=false;var timer=setTimeout(finish,12000);'+
 'function finish(){if(sent)return;sent=true;clearTimeout(timer);'+
 'parent.postMessage({__arenaGrade:1,checks:out.length?out:[{type:"dom_no_errors",pass:errs.length===0}]},"*");}'+
 'function tick(){if(sent)return;if(!specs.length)return finish();var sp=specs.shift();'+
 'try{run(sp);}catch(e){out.push({type:sp.type,pass:false,err:String(e)});tick();}}'+
 'function run(sp){var t=sp.type;'+
 'if(t==="dom_no_errors"){out.push({type:t,pass:errs.length===0,errors:errs.slice(0,3)});tick();}'+
 'else if(t==="dom_selectors"){var res={};(sp.selectors||[]).forEach(function(s){try{res[s]=document.querySelectorAll(s).length;}catch(e){res[s]=-1;}});'+
 'out.push({type:t,pass:Object.keys(res).every(function(k){return res[k]>=1;}),sel:res});tick();}'+
 'else if(t==="canvas_motion"){var cv=document.querySelector(sp.selector||"canvas");'+
 'if(!cv){out.push({type:t,pass:false,err:"no canvas found",raf:raf});tick();return;}'+
 'var d1;try{d1=cv.toDataURL();}catch(e){out.push({type:t,pass:false,err:"canvas blocked: "+e,raf:raf});tick();return;}'+
 'setTimeout(function(){if(sent)return;var r;'+
 'try{r={type:t,pass:cv.toDataURL()!==d1,raf:raf};}catch(e){r={type:t,pass:false,err:String(e),raf:raf};}'+
 'out.push(r);tick();},sp.delay_ms||900);}'+
 'else{out.push({type:t,pass:false,err:"unknown check type"});tick();}}'+
 'function start(){if(started||sent)return;started=true;tick();}'+
 'window.addEventListener("load",function(){setTimeout(start,700);});setTimeout(start,2500);})();<\/script>';
function markPass(key,val,ok){
  const c=CARD[key]; if(!c) return;
  if(c.passPill) c.passPill.remove();
  c.passPill=document.createElement('span');
  c.passPill.className='pill '+(ok===true?'ok':(ok===false?'no':''));
  c.passPill.textContent=val; c.metrics.appendChild(c.passPill);
}
function requestDomChecks(key,domSpecs){
  let base=buildPreviewHtml(key);
  if(!base){ gradeNow(key,[{type:'dom_no_errors',pass:false,err:'no renderable html found'}]); return; }
  const shim=CHECK_SHIM.replace('%%SPECS%%', JSON.stringify(domSpecs||[]));
  const html=/<\/head>/i.test(base)? base.replace(/<\/head>/i, m=>m+shim) : shim+base;
  const f=document.createElement('iframe');
  f.setAttribute('sandbox','allow-scripts');
  f.style.cssText='position:absolute;left:-9999px;top:0;width:420px;height:320px;border:0';
  GRADES[key]=f; document.body.appendChild(f); f.srcdoc=html;
  setTimeout(()=>{ if(GRADES[key]){ delete GRADES[key]; f.remove();
    gradeNow(key,[{type:'dom_no_errors',pass:false,err:'grade timeout'}]); } }, 30000);
}
async function gradeNow(key,checks){
  try{
    const r=await fetch('/api/grade',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({job:LAST_JOB,key,checks})});
    const j=await r.json().catch(()=>({}));
    markPass(key, j.passed===true?'✅ pass':(j.passed===false?'❌ fail':'⏳ pending'), j.passed);
    loadHistory();
  }catch(e){ markPass(key,'dom: grade failed',false); }
}
window.addEventListener('message',e=>{
  const d=e.data; if(!d||!d.__arenaGrade||!Array.isArray(d.checks)) return;
  for(const k in GRADES){
    if(GRADES[k].contentWindow===e.source){ const f=GRADES[k]; delete GRADES[k]; f.remove();
      gradeNow(k,d.checks); return; }
  }
});

/* ------------------------------ history ------------------------------ */
async function loadHistory(){
  let j; try{ j=await (await fetch('/api/runs')).json(); }catch(e){ return; }
  const tb=$('hist').querySelector('tbody'); tb.innerHTML='';
  const runs=j.runs||[];
  if(!runs.length){ tb.innerHTML='<tr><td colspan="5" style="color:var(--muted)">no saved runs yet</td></tr>'; return; }
  runs.slice(0,60).forEach(r=>{
    const tr=document.createElement('tr');
    const badges=(r.reconstructed?' <span class="badge">recon</span>':'')+
      (r.challenge?` <span class="badge">${escapeHtml(r.challenge)}</span>`:'')+
      (r.artifacts?` <span class="badge ok">${r.artifacts} html</span>`:'');
    tr.innerHTML=`<td>${escapeHtml(r.name)}${badges}</td><td>${escapeHtml((r.prompt||'').slice(0,70))}</td>`+
      `<td>${escapeHtml((r.models||[]).join(', '))}</td><td>${escapeHtml(r.vote||'—')}</td>`+
      `<td><a class="exp" href="#" data-v>view</a> `+
      `<a class="exp" href="/api/runs/${encodeURIComponent(r.name)}/export?fmt=md">md</a> `+
      `<a class="exp" href="/api/runs/${encodeURIComponent(r.name)}/export?fmt=csv">csv</a></td>`;
    tr.querySelector('[data-v]').onclick=ev=>{ ev.preventDefault(); showRun(r.name); };
    tb.appendChild(tr);
  });
}
async function showRun(name){
  let j; try{ j=await (await fetch('/api/runs/'+encodeURIComponent(name))).json(); }catch(e){ return; }
  const v=$('hviewer'); v.innerHTML='';
  const h=document.createElement('h3'); h.textContent=name; v.appendChild(h);
  const p=document.createElement('div'); p.className='hint'; p.textContent='Prompt: '+(j.prompt||''); v.appendChild(p);
  const grid=document.createElement('div'); grid.className='cards';
  (j.results||[]).forEach(r=>{
    const key=r.key||r.slot||'';
    const c=document.createElement('div'); c.className='card';
    const meta=(r.label||r.name||'')+(r.rep>1?` rep ${r.rep}`:'')+' — '+r.status+
      (r.toks_per_s?` · ${r.toks_per_s} tok/s`:'')+
      (r.passed===true?' · ✅ pass':(r.passed===false?' · ❌ fail':''));
    const art=r.artifact?('/api/runs/'+encodeURIComponent(name)+'/artifact/'+encodeURIComponent(key)):null;
    c.innerHTML=`<header><h3>${escapeHtml(meta)}</h3>`+
      (art?'<span class="tabs"><a class="tab on" data-t="r">Rendered</a><a class="tab" data-t="p">Preview</a></span>':'')+
      `</header><div class="body"></div>`;
    if(art){
      const a=document.createElement('a'); a.className='exp'; a.target='_blank';
      a.href=art; a.textContent='open ↗'; a.style.marginLeft='.6rem';
      c.querySelector('h3').appendChild(a);
    }
    const body=c.querySelector('.body');
    const rendered=document.createElement('div');
    rendered.innerHTML=renderMarkdown(r.text||('⚠ '+(r.error||'')));
    body.appendChild(rendered);
    if(art){
      let frame=null;
      const tabs=c.querySelectorAll('.tab');
      const sel=t=>tabs.forEach(x=>x.classList.toggle('on',x.dataset.t===t));
      tabs[0].onclick=()=>{ sel('r'); rendered.style.display=''; if(frame) frame.style.display='none'; };
      tabs[1].onclick=()=>{
        sel('p'); rendered.style.display='none';
        if(!frame){
          frame=document.createElement('iframe'); frame.className='preview';
          frame.setAttribute('sandbox','allow-scripts allow-modals allow-forms allow-popups');
          frame.setAttribute('title','saved model-generated page (sandboxed)');
          frame.src=art; body.appendChild(frame);
        } else frame.style.display='';
      };
    }
    grid.appendChild(c);
  });
  v.appendChild(grid);
  v.scrollIntoView({behavior:'smooth'});
}
$('hrefresh').onclick=e=>{ e.preventDefault(); loadHistory(); };

loadModels();
refreshScores();
loadChallenges();
loadHistory();

/* Reconnect to a run still in progress after a page refresh — the server
   replays the whole event log to a fresh SSE connection. */
(async()=>{
  try{
    const r=await (await fetch('/api/jobs/last')).json();
    if(r&&r.job){
      buildCards(r.order||[]);
      $('results').hidden=false;
      $('status').textContent='reconnected to running job…';
      $('stop').hidden=false; $('stop').disabled=false; $('stop').textContent='■ Stop';
      openStream(r.job);
    }
  }catch(e){}
})();
