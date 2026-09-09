const ACHIEVEMENTS = [
  ["beginner","🍀 Beginner's Luck","Ask Fukukitaru for your first fortune.",s=>s.fortunes>=1],
  ["seeker","🔮 The Seeker","Receive 10 fortunes.",s=>s.fortunes>=10],
  ["chatty","💬 Fortune Teller's Friend","Have 10 conversations with Fukukitaru.",s=>s.chats>=10],
  ["summoner","🧸 Shiraoki-sama's Disciple","Summon Shiraoki-sama.",s=>s.summons>=1],
  ["plush","✨ Plush Witness","Make the plush appear 5 times.",s=>s.plush>=5],
  ["paranoia","👁️ Paranoia","Click every suspicious button.",s=>s.suspicious],
  ["destiny","🌌 The Stars Have Spoken","Receive the ultra-rare forbidden fortune.",s=>s.rare],
  ["dedicated","🐎 Fukukitaru's Disciple","Receive 50 fortunes.",s=>s.fortunes>=50],
  ["visitor","🏠 Regular Visitor","Visit the shrine on 5 separate sessions.",s=>s.sessions>=5],
  ["forbidden","🚨 I Saw the Forbidden Fukukitaru","Trigger the 1-in-1000 forbidden event.",s=>s.forbidden],
];

let state = JSON.parse(localStorage.getItem("fukukitaru_state") || "{}");
Object.assign(state,{fortunes:0,chats:0,summons:0,plush:0,suspicious:false,rare:false,forbidden:false,sessions:0},state);
state.history = state.history || [];

if(!sessionStorage.getItem("counted_session")){
  state.sessions++;
  sessionStorage.setItem("counted_session","1");
  save();
}

function save(){ localStorage.setItem("fukukitaru_state",JSON.stringify(state)); renderAchievements(); }
function toast(text){
  const t=document.getElementById("toast"); t.textContent=text; t.classList.add("show");
  clearTimeout(window.toastTimer); window.toastTimer=setTimeout(()=>t.classList.remove("show"),2800);
}
function renderAchievements(){
  const el=document.getElementById("achievements"); el.innerHTML="";
  let count=0;
  ACHIEVEMENTS.forEach(([id,name,desc,fn])=>{
    const unlocked=fn(state); if(unlocked) count++;
    const d=document.createElement("div");
    d.className="achievement "+(unlocked?"unlocked":"");
    d.innerHTML=`<strong>${unlocked?"✓":"🔒"} ${name}</strong><span>${desc}</span>`;
    el.appendChild(d);
  });
  document.getElementById("achievementCount").textContent=`${count} / 10 unlocked`;
}
function unlockCheck(before){
  const now=ACHIEVEMENTS.filter(([id,n,d,fn])=>fn(state));
  const old=before || [];
  now.forEach(([id,name])=>{ if(!old.includes(id)) toast("🏆 Achievement unlocked: "+name); });
}
async function getFortune(){
  const before=ACHIEVEMENTS.filter(([id,n,d,fn])=>fn(state)).map(x=>x[0]);
  state.fortunes++;
  const r=await fetch("/api/fortune"); const x=await r.json();
  document.getElementById("fortune").innerHTML=`<strong>${x.title}</strong><p>${x.text}</p>`;
  state.history.unshift({title:x.title,text:x.text,time:new Date().toLocaleString()});
  state.history=state.history.slice(0,12);
  if(x.rare){state.rare=true; dramatic("🌌 The stars have spoken...");}
  save(); renderHistory(); unlockCheck(before);
}
function summon(){
  const before=ACHIEVEMENTS.filter(([id,n,d,fn])=>fn(state)).map(x=>x[0]);
  state.summons++; state.plush++;
  document.getElementById("plushOverlay").classList.add("show");
  const zone=document.getElementById("plushZone");
  zone.innerHTML=`<div class="plush-mini"><img src="/static/fukukitaru_plush.png" alt="Matikanefukukitaru plush" onerror="this.style.display='none';this.parentElement.classList.add('fallback')}></div><p>SHIRAOKI-SAMA HAS ARRIVED.</p>`;
  save(); unlockCheck(before);
}
function hidePlush(){document.getElementById("plushOverlay").classList.remove("show")}
function suspiciousButton(){
  const before=ACHIEVEMENTS.filter(([id,n,d,fn])=>fn(state)).map(x=>x[0]);
  state.suspicious=true; save(); unlockCheck(before); toast("You were warned.");
}
let chatHistory = [];
async function sendChat(){
  const input=document.getElementById("chatInput"); const text=input.value.trim(); if(!text)return;
  addMessage(text,"user"); input.value="";
  const before=ACHIEVEMENTS.filter(([id,n,d,fn])=>fn(state)).map(x=>x[0]);
  state.chats++; save();
  const previous = chatHistory.slice(-12);
  chatHistory.push({role:"user",content:text});
  try{
    const r=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text,history:previous})});
    const x=await r.json();
    const reply=x.reply || "The stars have gone strangely quiet... Please try again!";
    chatHistory.push({role:"assistant",content:reply});
    chatHistory=chatHistory.slice(-12);
    addMessage(reply,"bot");
  }catch(e){
    chatHistory.pop();
    addMessage("The spirits are having connection trouble! Please try again!","bot");
  }
  unlockCheck(before);
}
function addMessage(text,who){
  const m=document.getElementById("messages"); const d=document.createElement("div");
  d.className="msg "+who; d.textContent=text; m.appendChild(d); m.scrollTop=m.scrollHeight;
}
function renderHistory(){
  const el=document.getElementById("history");
  if(!state.history.length){el.innerHTML="<p class='muted'>No fortunes recorded yet. Your destiny is blank.</p>";return}
  el.innerHTML=state.history.map(x=>`<div class="history-item"><strong>${escapeHtml(x.title)}</strong><span>${escapeHtml(x.text)}</span><small>${escapeHtml(x.time)}</small></div>`).join("");
}
function clearHistory(){state.history=[];save();renderHistory();toast("Your fortune history has been erased. The stars remember.");}
function escapeHtml(s){return s.replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
async function dailyLuck(){
  try{
    const r=await fetch("/api/daily-luck"); const x=await r.json();
    let displayed=x.value;
    document.getElementById("luckNumber").textContent=displayed+"%";
    document.getElementById("luckFill").style.width=displayed+"%";
    document.getElementById("luckMessage").textContent =
      displayed>=90?"THE STARS ARE ABSOLUTELY SCREAMING YES!":
      displayed>=70?"A highly fortunate day!":
      displayed>=45?"Moderate luck. Proceed with confidence!":
      "The stars are being mysterious today.";
  }catch(e){}
}
function dramatic(text){ document.body.classList.add("dramatic"); toast(text); setTimeout(()=>document.body.classList.remove("dramatic"),1300); }
function forbiddenEvent(){
  if(Math.random()<0.001){
    const before=ACHIEVEMENTS.filter(([id,n,d,fn])=>fn(state)).map(x=>x[0]);
    state.forbidden=true; save(); document.getElementById("forbidden").classList.add("show"); unlockCheck(before);
  }
}
function closeForbidden(){document.getElementById("forbidden").classList.remove("show")}
const sigils=["🔮","🐴","🍀","✨"]; let sigilClicks=[];
document.querySelector(".sigils").addEventListener("click",e=>{
  const s=[...e.target.textContent].find(x=>sigils.includes(x)); if(!s)return;
  sigilClicks.push(s); sigilClicks=sigilClicks.slice(-4);
  if(sigilClicks.join("")==="🔮🐴🍀✨"){
    document.getElementById("cultist").classList.add("revealed");
    document.getElementById("cultStatus").textContent="🍀 CULTIST MODE UNLOCKED. The stars approve of your devotion.";
    toast("🍀 You have discovered the secret mode.");
  }
});
renderAchievements(); renderHistory(); dailyLuck(); forbiddenEvent();
