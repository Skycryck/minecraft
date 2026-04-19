// ═══════════════════════════════════════
// DATA — injected via <script> in index.html (generate.py)
// ═══════════════════════════════════════
const PLAYERS_DATA = window.PLAYERS_DATA;

// ═══════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════
// PALETTE, playerColor, CHART_PALETTE and the BLOCK_COLORS family live in
// stats/assets/colors.js (loaded before this script). PLAYER_COLORS_MAP is
// derived here because it depends on PLAYERS_DATA, which is injected above.
const PLAYER_COLORS_MAP = {};
const playerNames = Object.keys(PLAYERS_DATA).sort((a,b)=>PLAYERS_DATA[b].play_hours-PLAYERS_DATA[a].play_hours);
playerNames.forEach((n,i)=>PLAYER_COLORS_MAP[n]=playerColor(i));

// ═══════════════════════════════════════
// I18N + ICON HELPER — see stats/assets/i18n.js (loaded before this file)
// Shared bindings (classic-script top-level scope): lang, T, t, label, mcIcon.
// ═══════════════════════════════════════
const SYNC_FR=window.SYNC.fr,SYNC_EN=window.SYNC.en;
let currentSection='overview';
function fmt(n){if(n>=1e6)return(n/1e6).toFixed(1)+'M';if(n>=1e3)return(n/1e3).toFixed(1)+'k';return n.toLocaleString(lang==='fr'?'fr-FR':'en-US')}
function pct(v,m){return m?Math.round(v/m*100):0}

// ═══════════════════════════════════════
// MOBILE TOP-N + EXPAND TOGGLE
// ═══════════════════════════════════════
const MOBILE_TOP_N=15;
const isMobile=()=>window.matchMedia('(max-width:600px)').matches;
const expandedCharts={}; // id -> bool (true = show all, false = top-N). undefined => default (collapsed on mobile, expanded on desktop)
function isExpanded(id){return expandedCharts[id]??!isMobile()}
function expandToggleText(chartId,fullCount){
  const expanded=isExpanded(chartId);
  return expanded
    ?'<span class="expand-arrow">▴</span> '+t('expand_show_less')
    :'<span class="expand-arrow">▾</span> '+t('expand_show_all',fullCount-MOBILE_TOP_N);
}
function attachExpandToggle(cardEl,chartId,fullCount,onToggle){
  if(!cardEl)return;
  let btn=cardEl.querySelector('.expand-toggle');
  if(fullCount<=MOBILE_TOP_N){if(btn)btn.remove();return}
  if(!btn){
    btn=document.createElement('button');
    btn.className='expand-toggle';
    btn.type='button';
    cardEl.appendChild(btn);
    btn.addEventListener('click',()=>{
      expandedCharts[chartId]=!isExpanded(chartId);
      onToggle();
      btn.innerHTML=expandToggleText(chartId,fullCount);
    });
  }
  btn.innerHTML=expandToggleText(chartId,fullCount);
}

// ═══════════════════════════════════════
// ARCHETYPE DETECTION
// ═══════════════════════════════════════
function getArchetype(p){
  if(p.play_hours<1)return{name:t('arch_new'),icon:mcIcon('oak_sapling'),color:'var(--text-muted)'};
  const h=p.play_hours;
  const scores={
    miner:p.total_mined/h,
    fighter:p.mob_kills/h,
    explorer:p.total_distance_km/h,
    builder:p.total_crafted/h,
    farmer:(p.animals_bred+p.traded_with_villager+p.fish_caught)/h
  };
  const types={
    miner:{name:t('arch_miner'),icon:mcIcon('diamond_pickaxe'),color:'var(--c-mining)'},
    fighter:{name:t('arch_fighter'),icon:mcIcon('diamond_sword'),color:'var(--c-combat)'},
    explorer:{name:t('arch_explorer'),icon:mcIcon('compass'),color:'var(--c-travel)'},
    builder:{name:t('arch_builder'),icon:mcIcon('oak_planks'),color:'var(--c-craft)'},
    farmer:{name:t('arch_farmer'),icon:mcIcon('wheat'),color:'var(--c-survival)'}
  };
  const top=Object.entries(scores).sort((a,b)=>b[1]-a[1])[0][0];
  return types[top];
}

// ═══════════════════════════════════════
// FUN FACTS GENERATOR
// Scored by impressiveness vs server max
// ═══════════════════════════════════════
const _funFactMaxCache={};
function _maxOf(fn){
  const key=fn.toString();
  if(!_funFactMaxCache[key])_funFactMaxCache[key]=Math.max(...playerNames.map(n=>fn(PLAYERS_DATA[n])||0));
  return _funFactMaxCache[key]||1;
}

function getFunFacts(name,p){
  const facts=[];const h=p.play_hours;if(h<0.5)return facts;

  const ek=p.killed_top10?.enderman||0;
  if(ek>50)facts.push({score:ek/_maxOf(p=>p.killed_top10?.enderman||0),icon:mcIcon('ender_pearl'),text:t('ff_endermen',fmt(ek),Math.floor(ek/128))});

  if(p.deaths>3&&h>1){const mpd=Math.round(h*60/p.deaths);const deathRate=p.deaths/h;
    facts.push({score:deathRate/_maxOf(p=>p.play_hours>1?p.deaths/p.play_hours:0),icon:mcIcon('skeleton_skull'),text:t('ff_death_rate',mpd)})}

  const wk=p.distances?.walk||0;
  if(wk>20)facts.push({score:wk/_maxOf(p=>p.distances?.walk||0),icon:mcIcon('diamond_boots'),text:t('ff_walk',wk.toFixed(0),(wk/42.195).toFixed(1))});

  if(p.jumps>500&&h>1)facts.push({score:p.jumps/_maxOf(p=>p.jumps||0),icon:mcIcon('rabbit_foot'),text:t('ff_jumps',Math.round(p.jumps/h))});

  if(p.total_mined>500&&h>1)facts.push({score:p.total_mined/_maxOf(p=>p.total_mined||0),icon:mcIcon('diamond_pickaxe'),text:t('ff_mining',(p.total_mined/(h*60)).toFixed(1))});

  if(p.sleep_in_bed>5)facts.push({score:p.sleep_in_bed/_maxOf(p=>p.sleep_in_bed||0),icon:mcIcon('white_bed'),text:t('ff_sleep',p.sleep_in_bed,(p.sleep_in_bed/h).toFixed(1))});

  if(p.open_chest>100)facts.push({score:p.open_chest/_maxOf(p=>p.open_chest||0),icon:mcIcon('chest'),text:t('ff_chests',fmt(p.open_chest))});

  const pvpD=(p.killed_by?.player)||0;
  if(pvpD>3)facts.push({score:pvpD/_maxOf(p=>(p.killed_by?.player)||0),icon:mcIcon('bow'),text:t('ff_pvp_target',pvpD)});

  const ely=p.distances?.aviate||0;
  if(ely>50)facts.push({score:ely/_maxOf(p=>p.distances?.aviate||0),icon:mcIcon('elytra'),text:t('ff_elytra',ely.toFixed(0),Math.round(ely/10))});

  if(p.damage_dealt>10000)facts.push({score:p.damage_dealt/_maxOf(p=>p.damage_dealt||0),icon:mcIcon('netherite_sword'),text:t('ff_damage',fmt(Math.round(p.damage_dealt/20)))});

  if(p.traded_with_villager>50)facts.push({score:p.traded_with_villager/_maxOf(p=>p.traded_with_villager||0),icon:mcIcon('emerald'),text:t('ff_trades',fmt(p.traded_with_villager))});

  const brk=Object.values(p.broken||{}).reduce((s,v)=>s+v,0);
  if(brk>5)facts.push({score:brk/_maxOf(p=>Object.values(p.broken||{}).reduce((s,v)=>s+v,0)),icon:mcIcon('anvil'),text:t('ff_tools',brk)});

  if(p.mob_kills>100)facts.push({score:p.mob_kills/_maxOf(p=>p.mob_kills||0),icon:mcIcon('diamond_sword'),text:t('ff_mob_kills',fmt(p.mob_kills),Math.round(p.mob_kills/h))});

  if(p.animals_bred>20)facts.push({score:p.animals_bred/_maxOf(p=>p.animals_bred||0),icon:mcIcon('egg'),text:t('ff_breeding',p.animals_bred)});

  if(p.fish_caught>10)facts.push({score:p.fish_caught/_maxOf(p=>p.fish_caught||0),icon:mcIcon('fishing_rod'),text:t('ff_fishing',p.fish_caught)});

  const totalDist=p.total_distance_km;
  if(totalDist>100){
    const isLong=totalDist>1000;const refKm=isLong?1040:345;
    facts.push({score:totalDist/_maxOf(p=>p.total_distance_km||0),icon:mcIcon('compass'),text:t('ff_total_dist',totalDist.toFixed(0),(totalDist/refKm).toFixed(1),isLong?t('ff_equiv_long'):t('ff_equiv_short'))});
  }

  facts.sort((a,b)=>b.score-a.score);
  return facts.slice(0,5);
}

// ═══════════════════════════════════════
// TREEMAP BUILDER — squarified layout (Bruls, Huijing, van Wijk 2000)
// ═══════════════════════════════════════
// BLOCK_COLORS / blockColor() and the dye/wood/leaf helpers live in colors.js.
// Layout happens in abstract coords W×H (aspect 2:1, matched by CSS).
// Each rect is emitted as an absolutely-positioned % box so the card scales.
function squarifyLayout(items, x, y, w, h){
  const out=[];
  const worst=(row,side)=>{
    if(!row.length) return Infinity;
    let s=0,mx=0,mn=Infinity;
    for(const r of row){ s+=r.area; if(r.area>mx) mx=r.area; if(r.area<mn) mn=r.area; }
    const s2=s*s, side2=side*side;
    return Math.max(side2*mx/s2, s2/(side2*mn));
  };
  const layoutRow=(row,x,y,w,h)=>{
    const horizontal=w>=h;
    const side=horizontal?h:w;
    const s=row.reduce((a,r)=>a+r.area,0);
    const thickness=s/side;
    let cursor=0;
    for(const r of row){
      const len=r.area/thickness;
      if(horizontal) out.push({...r,x:x,y:y+cursor,w:thickness,h:len});
      else out.push({...r,x:x+cursor,y:y,w:len,h:thickness});
      cursor+=len;
    }
    return horizontal ? {x:x+thickness,y:y,w:w-thickness,h:h} : {x:x,y:y+thickness,w:w,h:h-thickness};
  };
  const queue=items.slice().sort((a,b)=>b.area-a.area);
  let row=[];
  while(queue.length){
    const side=Math.min(w,h);
    const next=queue[0];
    if(!row.length || worst(row.concat([next]),side) <= worst(row,side)){
      row.push(next); queue.shift();
    } else {
      ({x,y,w,h}=layoutRow(row,x,y,w,h));
      row=[];
    }
  }
  if(row.length) layoutRow(row,x,y,w,h);
  return out;
}

function buildTreemapHtml(entries){
  if(!entries.length)return '<div style="color:var(--text-muted);padding:1rem;font-family:var(--font-mono);font-size:.8rem">'+t('no_blocks')+'</div>';
  const data=entries.slice(0,15);
  const total=data.reduce((s,[_,v])=>s+v,0);
  const fallback=CHART_PALETTE;
  const W=200,H=100;
  const items=data.map(([k,v],i)=>({k,v,color:blockColor(k,fallback[i%fallback.length]),area:v/total*W*H}));
  const rects=squarifyLayout(items,0,0,W,H);
  const pct=(n,tot)=>(n/tot*100).toFixed(3);
  return `<div class="treemap">${rects.map(r=>{
    const p=r.v/total*100;
    // Label threshold uses min dimension rather than area: a rect with enough
    // width AND height can fit the 2-line label regardless of its total area.
    // An area-based check mis-hides tall+narrow rects that have room for text.
    const showLabel=r.w>=10 && r.h>=9;
    const tip=`${label(r.k)} · ${fmt(r.v)} (${p.toFixed(1)}%)`;
    return `<div class="treemap-item" style="left:${pct(r.x,W)}%;top:${pct(r.y,H)}%;width:${pct(r.w,W)}%;height:${pct(r.h,H)}%;background:${r.color}" data-tm-label="${tip}" title="${tip}">${showLabel?`<span>${label(r.k)}<br><span class=tm-count>${fmt(r.v)}</span></span>`:''}</div>`;
  }).join('')}</div>`;
}

// Floating tooltip shared across all treemap items — lives on <body>
// so it escapes the .treemap overflow:hidden clip. Native `title=` is
// kept as a11y fallback but shows with a ~1.5s OS delay and is clipped
// out of view on small rects.
function initTreemapTooltip(){
  let tip=null;
  const ensure=()=>{
    if(tip) return tip;
    tip=document.createElement('div');
    tip.className='tm-tooltip';
    document.body.appendChild(tip);
    return tip;
  };
  document.addEventListener('mouseover',e=>{
    const el=e.target.closest?.('.treemap-item');
    const node=ensure();
    if(el){ node.textContent=el.dataset.tmLabel||''; node.classList.add('visible'); }
    else { node.classList.remove('visible'); }
  });
  document.addEventListener('mousemove',e=>{
    if(!tip||!tip.classList.contains('visible')) return;
    const x=Math.min(e.clientX+14, window.innerWidth-tip.offsetWidth-8);
    const y=Math.min(e.clientY+14, window.innerHeight-tip.offsetHeight-8);
    tip.style.left=x+'px'; tip.style.top=y+'px';
  });
}

// ═══════════════════════════════════════
// BROKEN TOOLS
// ═══════════════════════════════════════
function buildBrokenHtml(broken){
  const entries=Object.entries(broken||{}).sort((a,b)=>b[1]-a[1]);
  if(!entries.length)return '<div style="color:var(--text-muted);font-family:var(--font-mono);font-size:.8rem">'+t('no_tools')+'</div>';
  return `<div class="broken-grid">${entries.map(([k,v])=>
    `<span class="broken-tag">${label(k)} <span class="bt-count">×${v}</span></span>`
  ).join('')}</div>`;
}

// ═══════════════════════════════════════
// TRAVEL TIME
// ═══════════════════════════════════════
// Vanilla Minecraft movement speeds (m/s). Accurate to ~±10% for most
// modes; elytra cruise speed varies strongly with pitch (~±30%).
const TRAVEL_SPEEDS={walk:4.317,sprint:5.612,swim:2.2,fly:10.89,aviate:33,boat:8,horse:9.9,minecart:8,climb:2.35,crouch:1.295,fall:20,walk_on_water:4.317,walk_under_water:2.2};
function travelSeconds(mode,km){return (km*1000)/(TRAVEL_SPEEDS[mode]||4.317)}
function totalTravelHours(distances){
  let s=0;
  Object.entries(distances||{}).forEach(([m,km])=>{s+=travelSeconds(m,km)});
  return s/3600;
}
function fmtDuration(sec){
  if(sec<60)return Math.round(sec)+' s';
  if(sec<3600)return Math.round(sec/60)+' min';
  const h=Math.floor(sec/3600),m=Math.round((sec%3600)/60);
  return m===0?h+' h':h+'h'+String(m).padStart(2,'0');
}

// ═══════════════════════════════════════
// ANIMATED COUNTERS
// ═══════════════════════════════════════
function animateCounters(){
  const obs=new IntersectionObserver((entries)=>{
    entries.forEach(entry=>{
      if(entry.isIntersecting&&!entry.target.dataset.done){
        entry.target.dataset.done='1';
        const target=parseFloat(entry.target.dataset.target);
        const suffix=entry.target.dataset.suffix||'';
        const isFloat=String(target).includes('.');
        const duration=1000;const start=performance.now();
        const step=(now)=>{
          const elapsed=now-start;const progress=Math.min(elapsed/duration,1);
          const ease=1-Math.pow(1-progress,3);
          const current=target*ease;
          entry.target.textContent=(isFloat?current.toFixed(1):fmt(Math.round(current)))+suffix;
          if(progress<1)requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      }
    });
  },{threshold:0.2});
  document.querySelectorAll('[data-target]').forEach(c=>obs.observe(c));
}

Chart.defaults.color='#8b8b96';
Chart.defaults.borderColor='rgba(42,42,53,0.5)';
Chart.defaults.font.family="'JetBrains Mono',monospace";
Chart.defaults.font.size=11;
Chart.defaults.plugins.legend.labels.boxWidth=12;
Chart.defaults.plugins.legend.labels.padding=12;

const charts={};
function destroyChart(id){if(charts[id]){charts[id].destroy();delete charts[id]}}

// ═══════════════════════════════════════
// GLOBAL AGGREGATION
// ═══════════════════════════════════════
const totalHours=playerNames.reduce((s,n)=>s+PLAYERS_DATA[n].play_hours,0);
const totalMined=playerNames.reduce((s,n)=>s+PLAYERS_DATA[n].total_mined,0);
const totalKills=playerNames.reduce((s,n)=>s+PLAYERS_DATA[n].mob_kills,0);
const totalDeaths=playerNames.reduce((s,n)=>s+PLAYERS_DATA[n].deaths,0);
const totalDist=playerNames.reduce((s,n)=>s+PLAYERS_DATA[n].total_distance_km,0);
const totalCrafted=playerNames.reduce((s,n)=>s+PLAYERS_DATA[n].total_crafted,0);

// "7-day" deltas: sum across players for the overview tiles, per-player
// elsewhere. The actual baseline window may differ from 7 days when the
// closest qualifying snapshot is older (e.g. after a multi-day pause); we
// display the real number of days in the label so the figure stays honest.
// `null` = no baseline in the [6, 30] days window → hide the sub line.
const _hasBaseline=playerNames.some(n=>PLAYERS_DATA[n].delta_7d);
const _baselineISO=window.BASELINE_DATE;
// Use whole-date arithmetic (zeroed midnight) so the window matches Python's
// (today - snapshot_date).days — avoids "6.6 days → rounds to 7" off-by-one.
const _baselineDays=(()=>{
  if(!_baselineISO)return null;
  const today=new Date();today.setHours(0,0,0,0);
  return Math.round((today-new Date(_baselineISO+'T00:00:00'))/86400000);
})();
function _sumDelta(key){return _hasBaseline?playerNames.reduce((s,n)=>s+(PLAYERS_DATA[n].delta_7d?.[key]??0),0):null}
const deltaTotals=_hasBaseline?{
  play_hours:_sumDelta('play_hours'),total_mined:_sumDelta('total_mined'),
  mob_kills:_sumDelta('mob_kills'),total_crafted:_sumDelta('total_crafted'),
}:null;
// Render a delta sub-line ("↑ +12h (6j)" / "= 0h (6j)" / "↓ -3h (6j)").
// Returns '' only when no baseline exists — otherwise shows the real state
// (inactive = neutral grey, regression = red) so players without progress
// can't be confused with players that have no baseline.
function deltaSub(value,suffix=''){
  if(value==null||!_baselineDays)return'';
  const abs=Math.abs(value);
  const v=Number.isInteger(abs)?fmt(abs):fmt(Math.round(abs*10)/10);
  let mod,arrow,sign;
  if(value>0){mod='pos';arrow='↑';sign='+'}
  else if(value<0){mod='neg';arrow='↓';sign='-'}
  else{mod='zero';arrow='=';sign=''}
  return `<div class="sub delta-sub delta-sub--${mod}">${arrow} ${sign}${v}${suffix} (${_baselineDays}${t('delta_unit')})</div>`;
}

function updateGlobalMeta(){
  document.getElementById('globalMeta').innerHTML=`
  <span><b>${playerNames.length}</b> ${t('players')}</span>
  <span><b>${totalHours.toFixed(0)}</b> ${t('hours_played')}</span>
  <span><b>${fmt(totalMined)}</b> ${t('blocks_mined_meta')}</span>
  <span><b>${fmt(totalKills)}</b> ${t('mobs_killed_meta')}</span>`;
}
updateGlobalMeta();

// ═══════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════
const navEl=document.getElementById('nav');
const contentEl=document.getElementById('content');

function buildNav(){
  let h='';
  h+=`<button class="nav-tab" data-section="overview">${t('nav_overview')}</button>`;
  h+=`<button class="nav-tab" data-section="leaderboards">${t('nav_leaderboards')}</button>`;
  h+=`<select class="nav-player-select" id="playerSelect" aria-label="${t('nav_player_label')}">`;
  h+=`<option value="">${t('nav_player_placeholder')}</option>`;
  playerNames.forEach(name=>{
    const hrs=PLAYERS_DATA[name].play_hours;
    h+=`<option value="${name}">${name} — ${hrs}h</option>`;
  });
  h+=`</select>`;
  navEl.innerHTML=h;
  navEl.querySelectorAll('.nav-tab').forEach(btn=>{
    btn.addEventListener('click',()=>navigateTo(btn.dataset.section));
  });
  document.getElementById('playerSelect').addEventListener('change',e=>{
    if(e.target.value)navigateTo('player-'+e.target.value);
  });
}

function updateNavActive(section){
  navEl.querySelectorAll('.nav-tab').forEach(b=>b.classList.toggle('active',b.dataset.section===section));
  const sel=document.getElementById('playerSelect');
  if(!sel)return;
  if(section.startsWith('player-')){
    const name=section.replace('player-','');
    sel.value=name;
    sel.classList.add('active');
    sel.style.setProperty('--player-accent',PLAYER_COLORS_MAP[name]||'var(--accent)');
  }else{
    sel.value='';
    sel.classList.remove('active');
    sel.style.removeProperty('--player-accent');
  }
}

function sectionToHash(id){
  if(id==='leaderboards')return '#leaderboards';
  if(id.startsWith('player-'))return '#player/'+encodeURIComponent(id.replace('player-',''));
  return '';
}
function hashToSection(hash){
  const h=(hash||'').replace(/^#/,'');
  if(!h)return 'overview';
  if(h==='leaderboards')return 'leaderboards';
  if(h.startsWith('player/')){
    const name=decodeURIComponent(h.slice(7));
    if(playerNames.includes(name))return 'player-'+name;
  }
  return 'overview';
}

function navigateTo(section){
  showSection(section);
  updateNavActive(section);
  const hash=sectionToHash(section);
  if(hash!==location.hash){
    if(hash)history.pushState(null,'',hash);
    else history.pushState(null,'',location.pathname+location.search);
  }
}

function showSection(id){
  // Destroy all charts from the section we are leaving — cheapest correct
  // path: each render function re-creates its own charts on entry, and
  // destroyChart() is idempotent, so double-destroy is harmless.
  if(id!==currentSection){
    for(const cid in charts){charts[cid].destroy();delete charts[cid]}
  }
  currentSection=id;
  if(id.startsWith('player-'))ensurePlayerSection(id.replace('player-',''));
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  const el=document.getElementById(id);
  if(el)el.classList.add('active');
  if(id==='overview')renderOverviewCharts();
  if(id==='leaderboards')renderLeaderboardCharts();
  if(id.startsWith('player-'))renderPlayerCharts(id.replace('player-',''));
  setTimeout(animateCounters,50);
}

window.addEventListener('hashchange',()=>{
  const s=hashToSection(location.hash);
  showSection(s);updateNavActive(s);
});
window.addEventListener('popstate',()=>{
  const s=hashToSection(location.hash);
  showSection(s);updateNavActive(s);
});

window.matchMedia('(max-width:600px)').addEventListener('change',()=>{
  for(const k in expandedCharts)delete expandedCharts[k];
  if(currentSection==='overview')renderOverviewCharts();
  if(currentSection==='leaderboards')renderDistStackedChart();
  initLeaderboardCollapse();
});

// Lazy section rendering: only overview + leaderboards (shared across all
// players) land in the initial DOM. Per-player sections are appended on
// first visit via ensurePlayerSection() and memoized for re-entry. Keeps
// the initial innerHTML small even with 20+ players.
const renderedPlayers=new Set();
function buildAllSections(){
  contentEl.innerHTML=buildOverview()+buildLeaderboards();
  renderedPlayers.clear();
}
function ensurePlayerSection(name){
  if(renderedPlayers.has(name))return;
  if(!playerNames.includes(name))return;
  contentEl.insertAdjacentHTML('beforeend',buildPlayerSection(name));
  renderedPlayers.add(name);
}

// ═══════════════════════════════════════
// OVERVIEW
// ═══════════════════════════════════════
function buildOverview(){
  return `
  <div class="section active" id="overview">
    <div class="grid grid-4" style="margin-bottom:1rem">
      <div class="stat-tile"><div class="value" style="color:var(--c-survival)" data-target="${totalHours.toFixed(0)}" data-suffix="h">0</div><div class="label">${t('total_playtime')}</div>${deltaSub(deltaTotals?.play_hours,'h')}</div>
      <div class="stat-tile"><div class="value" style="color:var(--c-mining)" data-target="${totalMined}">0</div><div class="label">${t('blocks_mined')}</div>${deltaSub(deltaTotals?.total_mined)}</div>
      <div class="stat-tile"><div class="value" style="color:var(--c-combat)" data-target="${totalKills}">0</div><div class="label">${t('mobs_killed')}</div>${deltaSub(deltaTotals?.mob_kills)}</div>
      <div class="stat-tile"><div class="value" style="color:var(--c-craft)" data-target="${totalCrafted}">0</div><div class="label">${t('items_crafted')}</div>${deltaSub(deltaTotals?.total_crafted)}</div>
    </div>
    <div class="grid grid-2-fixed">
      <div class="card" data-chart-card="chart-playtime"><h3><span class="icon">${mcIcon('recovery_compass')}</span> ${t('chart_playtime')}</h3><div class="chart-wrap"><canvas id="chart-playtime"></canvas></div></div>
      <div class="card" data-chart-card="chart-distance"><h3><span class="icon">${mcIcon('filled_map')}</span> ${t('chart_distance')}</h3><div class="chart-wrap"><canvas id="chart-distance"></canvas></div></div>
      <div class="card" data-chart-card="chart-mined"><h3><span class="icon">${mcIcon('diamond_pickaxe')}</span> ${t('chart_mined')}</h3><div class="chart-wrap"><canvas id="chart-mined"></canvas></div></div>
      <div class="card" data-chart-card="chart-kills"><h3><span class="icon">${mcIcon('diamond_sword')}</span> ${t('chart_kills')}</h3><div class="chart-wrap"><canvas id="chart-kills"></canvas></div></div>
    </div>
    <div class="card"><h3><span class="icon">${mcIcon('knowledge_book')}</span> ${t('chart_multi')}</h3>
      <div class="chart-wrap" style="max-height:420px"><canvas id="chart-radar"></canvas></div>
    </div>
  </div>`;
}

function renderOverviewCharts(){
  const padAxis=(scale)=>{scale.width+=8};
  const mkBar=(id,metric,tooltipSuffix,yLabel)=>{
    destroyChart(id);
    const sorted=[...playerNames].sort((a,b)=>(PLAYERS_DATA[b][metric]||0)-(PLAYERS_DATA[a][metric]||0));
    const expanded=isExpanded(id);
    const labels=expanded?sorted:sorted.slice(0,MOBILE_TOP_N);
    const data=labels.map(n=>PLAYERS_DATA[n][metric]||0);
    const useHorizontal=labels.length>8;
    const canvas=document.getElementById(id);
    if(useHorizontal){
      canvas.parentNode.style.height=Math.max(350,labels.length*28)+'px';
      canvas.parentNode.style.maxHeight='none';
    }else{
      canvas.parentNode.style.height='';
      canvas.parentNode.style.maxHeight='';
    }
    const opts=useHorizontal?{
      responsive:true,maintainAspectRatio:false,indexAxis:'y',plugins:{legend:{display:false}},
      scales:{x:{title:{display:true,text:yLabel},grid:{color:'rgba(42,42,53,0.3)'}},
        y:{grid:{display:false},ticks:{autoSkip:false,font:{size:11}},afterFit:padAxis}}
    }:{
      responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},
      scales:{y:{title:{display:true,text:yLabel},grid:{color:'rgba(42,42,53,0.3)'}},
        x:{grid:{display:false},ticks:{autoSkip:false,maxRotation:60,minRotation:45,font:{size:10}}}}
    };
    charts[id]=new Chart(canvas,{type:'bar',data:{
      labels,datasets:[{data,backgroundColor:labels.map(n=>PLAYER_COLORS_MAP[n]+'cc'),
        borderColor:labels.map(n=>PLAYER_COLORS_MAP[n]),borderWidth:1,borderRadius:4}]
    },options:{...opts,plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>ctx.parsed[useHorizontal?'x':'y']+(tooltipSuffix||'')}}}}});
    const card=document.querySelector(`[data-chart-card="${id}"]`);
    attachExpandToggle(card,id,sorted.length,()=>mkBar(id,metric,tooltipSuffix,yLabel));
  };
  mkBar('chart-playtime','play_hours','h',t('axis_hours'));
  mkBar('chart-distance','total_distance_km',' km',t('axis_km'));
  mkBar('chart-mined','total_mined',' blocs',t('axis_blocks'));
  mkBar('chart-kills','mob_kills',' kills',t('axis_kills'));

  destroyChart('chart-radar');
  const top5=playerNames.slice(0,5);
  const rm=['play_hours','total_mined','mob_kills','total_distance_km','total_crafted','deaths'];
  const rl=[t('radar_playtime'),t('radar_mined'),t('radar_kills'),t('radar_distance'),t('radar_crafted'),t('radar_deaths')];
  const mx=rm.map(m=>Math.max(...playerNames.map(n=>PLAYERS_DATA[n][m]||0)));
  const avg=rm.map(m=>playerNames.reduce((s,n)=>s+(PLAYERS_DATA[n][m]||0),0)/playerNames.length);
  const avgLabel=t('radar_avg');
  const avgDataset={label:avgLabel,
    data:rm.map((m,i)=>mx[i]?(avg[i]/mx[i]*100):0),
    borderColor:'#8b8b96',backgroundColor:'transparent',borderDash:[6,4],
    borderWidth:2,pointRadius:2,pointBackgroundColor:'#8b8b96'};
  charts['chart-radar']=new Chart(document.getElementById('chart-radar'),{type:'radar',data:{
    labels:rl,datasets:top5.map(name=>({label:name,
      data:rm.map((m,i)=>mx[i]?((PLAYERS_DATA[name][m]||0)/mx[i]*100):0),
      borderColor:PLAYER_COLORS_MAP[name],backgroundColor:PLAYER_COLORS_MAP[name]+'22',
      borderWidth:2,pointRadius:3,pointBackgroundColor:PLAYER_COLORS_MAP[name]})).concat([avgDataset])
  },options:{responsive:true,maintainAspectRatio:false,
    scales:{r:{grid:{color:'rgba(42,42,53,0.4)'},angleLines:{color:'rgba(42,42,53,0.3)'},ticks:{display:false},pointLabels:{font:{size:12}}}},
    plugins:{tooltip:{callbacks:{label:ctx=>{
      const idx=ctx.dataIndex;const name=ctx.dataset.label;
      const raw=name===avgLabel?avg[idx]:(PLAYERS_DATA[name]?.[rm[idx]]||0);
      return `${name}: ${typeof raw==='number'&&raw%1?raw.toFixed(1):fmt(Math.round(raw))}`;
    }}}}}});
}

// ═══════════════════════════════════════
// LEADERBOARDS
// ═══════════════════════════════════════
function buildLeaderboards(){
  const boards=[
    {key:'play_hours',tkey:'lb_playtime',suffix:'h',color:'var(--c-survival)',cat:'production',top:true},
    {key:'total_mined',tkey:'lb_mined',suffix:'',color:'var(--c-mining)',cat:'production',top:true},
    {key:'mob_kills',tkey:'lb_kills',suffix:'',color:'var(--c-combat)',cat:'combat',top:true},
    {key:'deaths',tkey:'lb_deaths',suffix:'',color:'var(--c-survival)',cat:'combat'},
    {key:'total_distance_km',tkey:'lb_distance',suffix:' km',color:'var(--c-travel)',cat:'exploration'},
    {key:'total_crafted',tkey:'lb_crafted',suffix:'',color:'var(--c-craft)',cat:'production'},
    {key:'player_kills',tkey:'lb_pvp',suffix:'',color:'var(--c-combat)',cat:'combat'},
    {key:'enchant_item',tkey:'lb_enchant',suffix:'',color:'var(--c-craft)',cat:'economy'},
    {key:'fish_caught',tkey:'lb_fish',suffix:'',color:'var(--c-craft)',cat:'economy'},
    {key:'traded_with_villager',tkey:'lb_trades',suffix:'',color:'var(--c-craft)',cat:'economy'},
    {key:'animals_bred',tkey:'lb_breed',suffix:'',color:'var(--c-survival)',cat:'economy'},
    {key:'jumps',tkey:'lb_jumps',suffix:'',color:'var(--c-travel)',cat:'exploration'},
  ];
  const cats=['top','combat','exploration','economy','production'];
  let h=`<div class="section" id="leaderboards"><div class="lb-wrap" data-active-cat="top">`;
  h+=`<div class="lb-subnav" role="tablist">`;
  cats.forEach(c=>{
    h+=`<button class="lb-tab${c==='top'?' active':''}" data-lbcat="${c}" role="tab">${t('lb_cat_'+c)}</button>`;
  });
  h+=`</div>
    <div class="grid grid-2 lb-charts">
      <div class="card lb-card" data-lbcats="combat"><h3><span class="icon">${mcIcon('skeleton_skull')}</span> ${t('chart_deathcauses')}</h3><div class="chart-wrap"><canvas id="chart-deathcauses"></canvas></div></div>
      <div class="card lb-card" data-chart-card="chart-dist-stacked" data-lbcats="exploration"><h3><span class="icon">${mcIcon('compass')}</span> ${t('chart_dist_type')}</h3><div class="chart-wrap"><canvas id="chart-dist-stacked"></canvas></div></div>
    </div>
    <div class="grid grid-3 lb-grid">`;
  boards.forEach(b=>{
    const lbcats=b.top?`top ${b.cat}`:b.cat;
    const sorted=[...playerNames].sort((a,c)=>(PLAYERS_DATA[c][b.key]||0)-(PLAYERS_DATA[a][b.key]||0));
    h+=`<div class="card lb-card" data-lbcats="${lbcats}"><h3>${t(b.tkey)}</h3><ol class="leaderboard">`;
    sorted.forEach((name,i)=>{
      const val=PLAYERS_DATA[name][b.key]||0;const isRec=i===0&&val>0;
      h+=`<li><span class="rank">${i+1}</span>
        <span class="name"><span class="player-dot" style="background:${PLAYER_COLORS_MAP[name]}"></span>${name}</span>
        ${isRec?'<span class="record-badge">RECORD</span>':''}
        <span class="val">${typeof val==='number'&&val%1?val.toFixed(1):fmt(val)}${b.suffix}</span></li>`;
    });
    h+=`</ol></div>`;
  });
  h+=`</div></div></div>`;
  return h;
}

function initLeaderboardTabs(){
  const wrap=document.querySelector('#leaderboards .lb-wrap');
  if(!wrap)return;
  wrap.querySelectorAll('.lb-tab').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const cat=btn.dataset.lbcat;
      wrap.dataset.activeCat=cat;
      wrap.querySelectorAll('.lb-tab').forEach(b=>b.classList.toggle('active',b===btn));
      setTimeout(()=>{
        ['chart-deathcauses','chart-dist-stacked'].forEach(id=>{if(charts[id])charts[id].resize()});
      },0);
    });
  });
}

function initLeaderboardCollapse(){
  document.querySelectorAll('#leaderboards ol.leaderboard').forEach(ol=>{
    const items=ol.children.length;
    if(items<=MOBILE_TOP_N)return;
    const card=ol.closest('.card');
    if(!card)return;
    const h3=card.querySelector('h3');
    const stableId='lb-'+(h3?h3.textContent.trim().toLowerCase().replace(/[^a-z0-9]+/g,'-'):'unknown');
    const apply=()=>ol.classList.toggle('lb-collapsed',!isExpanded(stableId));
    apply();
    attachExpandToggle(card,stableId,items,apply);
  });
}

function renderLeaderboardCharts(){
  destroyChart('chart-deathcauses');
  const deathAggregate={};playerNames.forEach(n=>{const killedBy=PLAYERS_DATA[n].killed_by||{};Object.entries(killedBy).forEach(([m,c])=>{deathAggregate[m]=(deathAggregate[m]||0)+c})});
  const sorted=Object.entries(deathAggregate).sort((a,b)=>b[1]-a[1]);
  const daTotal=sorted.reduce((s,[,v])=>s+v,0);
  const threshold=daTotal*0.01;
  const main=[];let otherSum=0;
  sorted.forEach(([k,v])=>{if(v>=threshold)main.push([k,v]);else otherSum+=v});
  const deathSorted=otherSum>0?main.concat([['__other__',otherSum]]):main;
  const deathColors=CHART_PALETTE;
  charts['chart-deathcauses']=new Chart(document.getElementById('chart-deathcauses'),{type:'doughnut',data:{
    labels:deathSorted.map(d=>d[0]==='__other__'?t('other_slice'):label(d[0])),
    datasets:[{data:deathSorted.map(d=>d[1]),backgroundColor:deathSorted.map((d,i)=>d[0]==='__other__'?'#5c5c6888':deathColors[i%deathColors.length]+'cc'),borderColor:'#16161a',borderWidth:2}]
  },options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{font:{size:10}}}}}});

  renderDistStackedChart();
}

function renderDistStackedChart(){
  destroyChart('chart-dist-stacked');
  const distTypes=['walk','sprint','fly','aviate','swim','boat','horse','climb','crouch','fall'];
  const distColors=CHART_PALETTE;
  const sortedPlayers=[...playerNames].sort((a,b)=>(PLAYERS_DATA[b].total_distance_km||0)-(PLAYERS_DATA[a].total_distance_km||0));
  const filteredPlayers=isExpanded('chart-dist-stacked')?sortedPlayers:sortedPlayers.slice(0,MOBILE_TOP_N);
  const distHorizontal=filteredPlayers.length>8;
  const distCanvas=document.getElementById('chart-dist-stacked');
  if(distHorizontal){
    distCanvas.parentNode.style.height=Math.max(350,filteredPlayers.length*24)+'px';
    distCanvas.parentNode.style.maxHeight='none';
  }else{
    distCanvas.parentNode.style.height='';
    distCanvas.parentNode.style.maxHeight='';
  }
  charts['chart-dist-stacked']=new Chart(distCanvas,{type:'bar',data:{
    labels:filteredPlayers,datasets:distTypes.map((dtype,i)=>({label:label(dtype),data:filteredPlayers.map(n=>PLAYERS_DATA[n].distances?.[dtype]||0),backgroundColor:distColors[i]+'aa',borderWidth:0}))
  },options:{responsive:true,maintainAspectRatio:false,indexAxis:distHorizontal?'y':'x',
    scales:distHorizontal?{
      y:{stacked:true,grid:{display:false},ticks:{autoSkip:false,font:{size:10}},afterFit:(s)=>{s.width+=8}},
      x:{stacked:true,title:{display:true,text:'km'},grid:{color:'rgba(42,42,53,0.3)'}}
    }:{
      x:{stacked:true,grid:{display:false},ticks:{autoSkip:false,maxRotation:60,minRotation:45,font:{size:10}}},
      y:{stacked:true,title:{display:true,text:'km'},grid:{color:'rgba(42,42,53,0.3)'}}
    },
    plugins:{legend:{position:'bottom',labels:{font:{size:9}}}}}});
  const card=document.querySelector(`[data-chart-card="chart-dist-stacked"]`);
  attachExpandToggle(card,'chart-dist-stacked',sortedPlayers.length,renderDistStackedChart);
}

// ═══════════════════════════════════════
// BADGE / ACHIEVEMENT SYSTEM
// ═══════════════════════════════════════
const TIER_NAMES=['locked','bronze','silver','gold','diamond'];
function tierLabel(i){return [t('tier_locked'),t('tier_bronze'),t('tier_silver'),t('tier_gold'),t('tier_diamond')][i]}
const TIER_COLORS=['var(--text-muted)','#cd7f32','#c0c0c0','#ffd700','#b9f2ff'];
const TIER_EMOJIS=[mcIcon('copper_ingot'),mcIcon('iron_ingot'),mcIcon('gold_ingot'),mcIcon('diamond')];
const BADGE_CATEGORIES=[
  {id:'mining'},{id:'combat'},{id:'survival'},{id:'exploration'},
  {id:'farming'},{id:'craft'},{id:'daily'},{id:'prestige'},
];
// Badge definitions & tier computation live in scripts/minecraft/badges.py.
// The server ships pre-computed badges on each player (p.badges).

function buildBadgesHtml(name){
  const p=PLAYERS_DATA[name];
  const badges=p.badges||[];
  const unlocked=badges.filter(b=>b.tier>0).length;
  const total=badges.length;
  let h=`<div class="card"><h3><span class="icon">${mcIcon('nether_star')}</span> ${t('badges_title')}</h3>`;
  h+=`<div class="badges-counter-wrap"><span class="badges-counter"><b>${unlocked}</b> / ${total} ${t('badges_unlocked')}</span></div>`;
  BADGE_CATEGORIES.forEach(cat=>{
    const cb=badges.filter(b=>b.cat===cat.id);
    if(!cb.length)return;
    h+=`<div class="badges-cat-header">${t('cat_'+cat.id)}</div><div class="badges-grid">`;
    cb.forEach(b=>{
      const tn=TIER_NAMES[b.tier];
      const tl=b.tier>0?tierLabel(b.tier):t('tier_locked');
      const tc=b.tier>0?'tier-'+tn:'locked';
      const pc=TIER_COLORS[Math.max(b.tier,1)];
      const dv=b.value==null?'—':(b.id==='increvable'&&b.value>=999?'∞':(typeof b.value==='number'&&b.value%1!==0?b.value.toFixed(1):fmt(Math.round(b.value))));
      const nt=b.tier>=4?'MAX':fmt(b.nextTarget);
      const desc=t('bd_'+b.id);
      const ttTiers=b.tiers.map((th,i)=>{const cls=i<b.tier?'tt-done':(i===b.tier&&b.tier<4?'tt-next':'');return `<span class="tt-tier ${cls}">${TIER_EMOJIS[i]} ${fmt(th)}</span>`}).join(' · ');
      h+=`<div class="badge-card ${tc}">
        <div class="badge-tooltip"><div class="tt-desc">${desc}</div><div class="tt-tiers">${ttTiers}</div></div>
        <div class="badge-header">
          <span class="badge-icon">${b.tier>0?mcIcon(b.icon):'🔒'}</span>
          <span class="badge-name">${t('b_'+b.id)}</span>
        </div>
        <div class="badge-progress-text">
          <span class="badge-tier badge-tier-${tn}">${tl}</span>
          <span class="bpt-vals">${dv} / ${nt}</span>
        </div>
        <div class="badge-progress"><div class="badge-progress-fill" style="width:${b.progress}%;background:${pc}"></div></div>
      </div>`;
    });
    h+=`</div>`;
  });
  h+=`</div>`;
  return h;
}

// ═══════════════════════════════════════
// PLAYER SECTION
// ═══════════════════════════════════════
// 52-week × 7-day GitHub-style activity heatmap (per player).
// Reads p.daily_hours = {YYYY-MM-DD: hours} (computed Python-side from
// consecutive snapshots; gap days are absent → render as empty cells, no
// faked zeros). Cells are colored using the player's identity color with
// 4 intensity buckets; missing days use --bg-card-alt.
function buildHeatmapHtml(name){
  const p=PLAYERS_DATA[name];
  const daily=p.daily_hours;
  if(!daily||!Object.keys(daily).length)return'';
  const color=PLAYER_COLORS_MAP[name];
  const weeks=52,cell=11,gap=2;
  const today=new Date();today.setHours(0,0,0,0);
  // Monday of the week containing today (Mon=0..Sun=6 — French week start)
  const dow=(today.getDay()+6)%7;
  const lastMon=new Date(today);lastMon.setDate(today.getDate()-dow);
  const bucket=v=>v<0.5?0:v<2?1:v<4?2:v<6?3:4;
  const op=[0,0.3,0.55,0.8,1.0];
  const w=weeks*(cell+gap)-gap,h=7*(cell+gap)-gap;
  const isoLocal=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  let cells='',totalHours=0,daysActive=0,monthLabels='';
  let lastMonthLabel=-1;
  for(let wi=0;wi<weeks;wi++){
    const colMon=new Date(lastMon);colMon.setDate(lastMon.getDate()-(weeks-1-wi)*7);
    if(colMon.getMonth()!==lastMonthLabel&&colMon.getDate()<=7){
      monthLabels+=`<text x="${wi*(cell+gap)}" y="-3" class="hm-label">${colMon.toLocaleDateString(lang==='fr'?'fr-FR':'en-US',{month:'short'})}</text>`;
      lastMonthLabel=colMon.getMonth();
    }
    for(let di=0;di<7;di++){
      const day=new Date(colMon);day.setDate(colMon.getDate()+di);
      if(day>today)continue;
      const iso=isoLocal(day);
      const v=daily[iso];
      const x=wi*(cell+gap),y=di*(cell+gap);
      if(v===undefined){
        cells+=`<rect x="${x}" y="${y}" width="${cell}" height="${cell}" rx="2" class="hm-cell hm-empty"><title>${iso} — ${t('hm_no_data')}</title></rect>`;
      }else{
        totalHours+=v;daysActive++;
        const b=bucket(v);
        cells+=`<rect x="${x}" y="${y}" width="${cell}" height="${cell}" rx="2" fill="${color}" fill-opacity="${op[b]||0.15}" class="hm-cell"><title>${iso} — ${v}${t('hm_hours_unit')}</title></rect>`;
      }
    }
  }
  // Legend swatches (5 buckets)
  const legend=op.map(o=>`<span class="hm-swatch" style="background:${color};opacity:${o||0.15}"></span>`).join('');
  const streakSuffix=p.streaks
    ?` · ${t('hm_streak_longest')} ${p.streaks.longest}${t('delta_unit')} · ${t('hm_streak_current')} ${p.streaks.current}${t('delta_unit')}`
    :'';
  return `<div class="card"><h3><span class="icon">${mcIcon('clock')}</span> ${t('card_heatmap')}</h3>
    <div class="heatmap-meta">${daysActive} ${t('hm_days_active')} · ${totalHours.toFixed(1)}${t('hm_hours_unit')}${streakSuffix}</div>
    <div class="heatmap-wrap"><svg class="heatmap" viewBox="0 -14 ${w} ${h+14}" preserveAspectRatio="xMidYMid meet">${monthLabels}${cells}</svg></div>
    <div class="heatmap-legend"><span>${t('hm_less')}</span>${legend}<span>${t('hm_more')}</span></div>
  </div>`;
}

function buildPlayerSection(name){
  const p=PLAYERS_DATA[name];const color=PLAYER_COLORS_MAP[name];
  const avatarUrl=`https://mc-heads.net/avatar/${p.uuid}/64`;

  const records=[];
  ['play_hours','total_mined','mob_kills','total_distance_km','total_crafted','player_kills','enchant_item','fish_caught','traded_with_villager','animals_bred','jumps'].forEach(key=>{
    const mx=Math.max(...playerNames.map(n=>PLAYERS_DATA[n][key]||0));
    if((p[key]||0)===mx&&mx>0)records.push(key);
  });
  const recBadges=records.length?`<div style="margin-top:.5rem;display:flex;gap:.3rem;flex-wrap:wrap">${records.map(r=>`<span class="record-badge">${label(r).substring(0,20)}</span>`).join('')}</div>`:'';

  const killedBy=Object.entries(p.killed_by||{}).sort((a,b)=>b[1]-a[1]);
  const kbHtml=killedBy.length?killedBy.map(([m,c])=>`<li><span style="color:var(--text)">${label(m)}</span> <span style="color:var(--c-combat);font-weight:600">${c}×</span></li>`).join(''):'<li style="color:var(--text-muted)">'+t('no_death')+'</li>';

  const mkList=(entries,color)=>{
    if(!entries.length)return '<li style="color:var(--text-muted)">—</li>';
    const mx=Math.max(...entries.map(e=>e[1]));
    return entries.map(([k,v])=>{
      const w=mx>0?(v/mx*100):0;
      return `<li><span class="name">${label(k)}</span><span class="bar-bg"><span class="bar-fill" style="width:${w}%;background:${color}"></span></span><span class="val">${fmt(v)}</span></li>`;
    }).join('');
  };

  const kd=p.deaths>0?(p.mob_kills/p.deaths).toFixed(1):'∞';
  const mph=p.play_hours>0?Math.round(p.total_mined/p.play_hours):0;
  const kph=p.play_hours>0?Math.round(p.mob_kills/p.play_hours):0;
  const pvpDeaths=(p.killed_by&&p.killed_by.player)||0;
  const pveDeaths=p.deaths-pvpDeaths;
  const arch=getArchetype(p);
  const funFacts=getFunFacts(name,p);
  const funFactsHtml=funFacts.length?funFacts.map(f=>`<div class="fun-fact">${f.icon}<span>${f.text}</span></div>`).join(''):'<div style="color:var(--text-muted);font-family:var(--font-mono);font-size:.8rem">'+t('no_data')+'</div>';

  return `
  <div class="section" id="player-${name}">
    <div class="profile-header" style="border-left:4px solid ${color}">
      <img class="profile-avatar" src="${avatarUrl}" alt="${name}" onerror="this.style.display='none'">
      <div class="profile-info">
        <h2 style="color:${color}">${name}</h2>
        <div class="uuid">${p.uuid}</div>
        <div class="archetype" style="color:${arch.color};border-color:${arch.color}">${arch.icon} ${arch.name}</div>
        ${recBadges}
      </div>
      <div class="profile-stats">
        <div class="profile-stat"><div class="pv">${p.play_hours}h</div><div class="pl">${t('playtime')}</div>${deltaSub(p.delta_7d?.play_hours,'h')}</div>
        <div class="profile-stat"><div class="pv" style="color:var(--c-combat)">${kd}</div><div class="pl">${t('kd_ratio')}</div></div>
        <div class="profile-stat"><div class="pv" style="color:var(--c-travel)">${fmt(p.total_distance_km)} km</div><div class="pl">${t('traveled')}</div></div>
      </div>
    </div>
    <div class="grid grid-4" style="margin-bottom:1rem">
      <div class="stat-tile"><div class="value" style="color:var(--c-mining)" data-target="${p.total_mined}">0</div><div class="label">${t('blocks_mined')}</div><div class="sub">${fmt(mph)}${t('per_hour')}</div>${deltaSub(p.delta_7d?.total_mined)}</div>
      <div class="stat-tile"><div class="value" style="color:var(--c-combat)" data-target="${p.mob_kills}">0</div><div class="label">${t('mobs_killed')}</div><div class="sub">${fmt(kph)}${t('per_hour')}</div>${deltaSub(p.delta_7d?.mob_kills)}</div>
      <div class="stat-tile"><div class="value" style="color:var(--c-survival)" data-target="${p.deaths}">0</div><div class="label">${t('deaths')}</div><div class="sub">${mcIcon('iron_sword')} ${pvpDeaths} ${t('pvp')} · ${mcIcon('rotten_flesh')} ${pveDeaths} ${t('pve')}</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--c-craft)" data-target="${p.total_crafted}">0</div><div class="label">${t('items_crafted')}</div>${deltaSub(p.delta_7d?.total_crafted)}</div>
    </div>
    <div class="grid grid-4" style="margin-bottom:1rem">
      <div class="stat-tile"><div class="value" style="color:var(--c-craft)" data-target="${p.enchant_item}">0</div><div class="label">${t('enchantments')}</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--c-survival)" data-target="${p.open_chest}">0</div><div class="label">${t('chests_opened')}</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--c-craft)" data-target="${p.fish_caught}">0</div><div class="label">${t('fish_caught')}</div></div>
      <div class="stat-tile"><div class="value" style="color:var(--c-craft)" data-target="${p.traded_with_villager}">0</div><div class="label">${t('npc_trades')}</div></div>
    </div>
    <div class="grid grid-2">
      <div class="card"><h3><span class="icon">${mcIcon('diamond_boots')}</span> ${t('card_distances')}</h3><div style="font-size:.8rem;color:var(--text-muted);font-family:var(--font-mono);margin:-.25rem 0 .5rem">${t('travel_time_sub',totalTravelHours(p.distances).toFixed(1),p.play_hours>0?Math.round(totalTravelHours(p.distances)/p.play_hours*100):0)}</div><div class="chart-wrap"><canvas id="chart-dist-${name}"></canvas></div></div>
    </div>
    <div class="grid grid-2">
      <div class="card"><h3><span class="icon">${mcIcon('skeleton_skull')}</span> ${t('card_killed_by')}</h3><ul class="leaderboard" style="font-size:.8rem">${kbHtml}</ul></div>
    </div>
    <div class="card desktop-only">
      <h3><span class="icon">${mcIcon('diamond_pickaxe')}</span> ${t('card_treemap')}</h3>
      ${buildTreemapHtml(Object.entries(p.mined_top15||{}))}
    </div>
    <div class="card mobile-only">
      <h3><span class="icon">${mcIcon('diamond_pickaxe')}</span> ${t('card_top15_mined')}</h3>
      <ol class="leaderboard">${mkList(Object.entries(p.mined_top15||{}),color)}</ol>
    </div>
    <div class="grid grid-2">
      <div class="card"><h3><span class="icon">${mcIcon('diamond_sword')}</span> ${t('card_top10_killed')}</h3><ol class="leaderboard">${mkList(Object.entries(p.killed_top10||{}),'var(--c-combat)')}</ol></div>
      <div class="card"><h3><span class="icon">${mcIcon('crafting_table')}</span> ${t('card_top10_crafted')}</h3><ol class="leaderboard">${mkList(Object.entries(p.crafted_top15||{}).slice(0,10),'var(--c-craft)')}</ol></div>
    </div>
    <div class="grid grid-2">
      <div class="card"><h3><span class="icon">${mcIcon('anvil')}</span> ${t('card_tools_broken')}</h3>${buildBrokenHtml(p.broken)}</div>
      <div class="card"><h3><span class="icon">${mcIcon('torch')}</span> ${t('card_fun_facts')}</h3><div class="fun-facts">${funFactsHtml}</div></div>
    </div>
    ${buildHeatmapHtml(name)}
    ${buildBadgesHtml(name)}
  </div>`;
}

function renderPlayerCharts(name){
  const p=PLAYERS_DATA[name];

  // Distance bar
  const distId=`chart-dist-${name}`;
  destroyChart(distId);
  const dists=p.distances||{};
  const de=Object.entries(dists).filter(([_,v])=>v>0).sort((a,b)=>b[1]-a[1]);
  if(de.length&&document.getElementById(distId)){
    const dp=CHART_PALETTE;
    charts[distId]=new Chart(document.getElementById(distId),{type:'bar',data:{
      labels:de.map(d=>label(d[0])),datasets:[{data:de.map(d=>d[1]),
        backgroundColor:de.map((_,i)=>dp[i%dp.length]+'cc'),borderColor:de.map((_,i)=>dp[i%dp.length]),borderWidth:1,borderRadius:4}]
    },options:{responsive:true,maintainAspectRatio:false,indexAxis:'y',
      plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>{const mode=de[ctx.dataIndex][0];const km=ctx.parsed.x;return ` ${km.toFixed(2)} km — ~${fmtDuration(travelSeconds(mode,km))}`}}}},
      scales:{x:{title:{display:true,text:'km'},grid:{color:'rgba(42,42,53,0.3)'}},y:{grid:{display:false}}}}});
  }
}

// ═══════════════════════════════════════
// LANGUAGE SWITCH
// ═══════════════════════════════════════
function switchLang(newLang){
  lang=newLang;
  localStorage.setItem('mc-dash-lang',lang);
  document.getElementById('html-root').lang=lang;
  document.getElementById('subtitle').textContent=t('subtitle');
  document.getElementById('syncDate').textContent=t('sync_prefix')+' : '+(lang==='fr'?SYNC_FR:SYNC_EN);
  document.getElementById('langToggle').textContent=lang==='fr'?'🇬🇧 EN':'🇫🇷 FR';
  updateGlobalMeta();
  buildNav();
  buildAllSections();
  initLeaderboardTabs();
  initLeaderboardCollapse();
  showSection(currentSection);
  updateNavActive(currentSection);
}

// ═══════════════════════════════════════
// INIT
// ═══════════════════════════════════════
document.getElementById('html-root').lang=lang;
document.getElementById('subtitle').textContent=t('subtitle');
document.getElementById('syncDate').textContent=t('sync_prefix')+' : '+(lang==='fr'?SYNC_FR:SYNC_EN);
document.getElementById('langToggle').textContent=lang==='fr'?'🇬🇧 EN':'🇫🇷 FR';
document.getElementById('langToggle').addEventListener('click',function(){switchLang(lang==='fr'?'en':'fr')});
buildNav();buildAllSections();initLeaderboardTabs();initLeaderboardCollapse();initTreemapTooltip();
const _initialSection=hashToSection(location.hash);
showSection(_initialSection);updateNavActive(_initialSection);
animateCounters();
// Re-render current section once fonts finish loading. Chart.js' first pass
// may measure labels with the fallback font (shorter glyphs) and clip the
// longest y-axis label once the real font kicks in.
if(document.fonts?.ready)document.fonts.ready.then(()=>showSection(currentSection));
