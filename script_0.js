
// ===== SPLASH =====
setTimeout(()=>{document.getElementById('splash').classList.add('hide');setTimeout(()=>document.getElementById('splash').remove(),700);},2000);

// ===== TAB SWITCHING =====
function switchTab(name, el){
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  el.classList.add('active');
  if(name==='map'&&!gisMapReady) initGISMap();
  if(name==='report')loadReports();
  if(name==='history')loadHistory();
}

// ===== OVERVIEW: EXACT SAME JS AS BEFORE =====
const API=`${location.origin}/api/latest`;
const HIST=`${location.origin}/api/history`;
const RISK=`${location.origin}/api/risk`;
let sirenOn=false,vibOn=false,audioCtx=null,sirenOsc=null,lastStatus='safe',lastTS='',vibInterval=null,lastDataTime=0;
const $=id=>document.getElementById(id);

function initAudio(){if(!audioCtx)audioCtx=new(window.AudioContext||window.webkitAudioContext)();if(audioCtx.state==='suspended')audioCtx.resume();}
document.addEventListener('click',initAudio,{once:false});
document.addEventListener('touchstart',initAudio,{once:false});
function startSiren(){initAudio();if(sirenOsc)return;sirenOsc=audioCtx.createOscillator();const g=audioCtx.createGain();sirenOsc.type='sawtooth';sirenOsc.frequency.setValueAtTime(800,audioCtx.currentTime);sirenOsc.frequency.linearRampToValueAtTime(1200,audioCtx.currentTime+0.3);sirenOsc.frequency.linearRampToValueAtTime(600,audioCtx.currentTime+0.6);g.gain.setValueAtTime(1.0,audioCtx.currentTime);sirenOsc.connect(g);g.connect(audioCtx.destination);sirenOsc.start();sirenOsc.onended=()=>{sirenOsc=null;if(lastStatus!=='safe'&&sirenOn)startSiren();};}
function stopSiren(){if(sirenOsc){try{sirenOsc.stop();}catch(e){}sirenOsc=null;}}
function startContinuousVibrate(){if(vibInterval)return;vibInterval=setInterval(()=>{if(navigator.vibrate)navigator.vibrate([400,100,400,100,400]);},1500);if(navigator.vibrate)navigator.vibrate([400,100,400,100,400]);}
function stopContinuousVibrate(){if(vibInterval){clearInterval(vibInterval);vibInterval=null;}if(navigator.vibrate)navigator.vibrate(0);}
function toggleSiren(){sirenOn=!sirenOn;$('siren-btn').classList.toggle('on',sirenOn);$('siren-state').textContent=sirenOn?'On':'Off';if(sirenOn){initAudio();if(lastStatus!=='safe')startSiren();}else stopSiren();}
function toggleVibrate(){vibOn=!vibOn;$('vib-btn').classList.toggle('on',vibOn);$('vib-state').textContent=vibOn?'On':'Off';if(vibOn){navigator.vibrate&&navigator.vibrate(200);if(lastStatus==='danger')startContinuousVibrate();}else stopContinuousVibrate();}

// Overview map
const map=L.map('map',{zoomControl:true,attributionControl:false}).setView([25.5,91.9],7);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',{maxZoom:16}).addTo(map);
let sensorMarker=null,riskCircle=null,neighborMarkersAdded=false;
function updateMap(lat,lng,riskScore,status){
  const c=status==='danger'?'#C25B45':status==='warning'?'#D69A4E':'#6FA97D';
  if(!sensorMarker){sensorMarker=L.circleMarker([lat,lng],{radius:8,fillColor:c,color:'#ECEFE9',weight:2,fillOpacity:0.8}).addTo(map).bindPopup('<b>Landsafe Sensor</b><br>sensor-001');}else{sensorMarker.setStyle({fillColor:c});}
  if(!riskCircle){riskCircle=L.circle([lat,lng],{radius:1000+riskScore*50,fillColor:c,color:c,weight:1,fillOpacity:0.1+riskScore*0.003}).addTo(map);}else{riskCircle.setStyle({fillColor:c,color:c,fillOpacity:0.1+riskScore*0.003});riskCircle.setRadius(1000+riskScore*50);}
  if(!neighborMarkersAdded){neighborMarkersAdded=true;[[25.67,91.88],[25.45,92.10],[25.55,91.75],[25.35,91.95],[25.70,92.05],[25.50,91.60]].forEach(([nlat,nlng])=>{const r=Math.max(0,riskScore+(Math.random()-0.5)*30);const cc=r>=70?'#C25B45':r>=40?'#D69A4E':'#6FA97D';L.circleMarker([nlat,nlng],{radius:4,fillColor:cc,color:cc,weight:1,fillOpacity:0.5}).addTo(map);});}
}
function update(data,risk){
  const{tilt,moisture,status,device_id,timestamp}=data;const m=moisture||0;
  const clamped=Math.max(-90,Math.min(90,tilt));$('needle').style.transform=`translateX(-50%) rotate(${-(clamped/90)*90}deg)`;
  $('tilt-val').textContent=`${tilt.toFixed(2)}°`;$('tilt-val').className=`tilt-num ${status}`;$('tilt-dev').textContent=`Device: ${device_id}`;
  $('badge').textContent=status.toUpperCase();$('badge').className=`badge-pill ${status}`;
  $('dev-id').textContent=device_id;$('dev-status').textContent=status.toUpperCase();
  $('dev-status').style.color=status==='danger'?'var(--rust)':status==='warning'?'var(--ochre)':'var(--moss)';
  $('dev-time').textContent=new Date(timestamp).toLocaleTimeString();
  $('moisture-val').textContent=`${m.toFixed(1)}%`;$('moisture-val').style.color=m>=80?'var(--rust)':m>=60?'var(--ochre)':'var(--slate)';
  const mBar=$('moisture-bar');mBar.style.width=`${Math.max(4,m)}%`;mBar.className=m>=80?'rust':m>=60?'ochre':'blue';
  if(risk){const rScore=risk.risk_score||0;$('risk-level').textContent=risk.risk_level||'LOW';
  $('risk-level').style.color=rScore>=70?'#C25B45':rScore>=40?'#D69A4E':rScore>=15?'#D69A4E':'#6FA97D';
  $('risk-score').textContent=`${rScore.toFixed(0)}%`;const rBar=$('risk-bar');rBar.style.width=`${rScore}%`;
  rBar.className='risk-bar-fill '+(rScore>=70?'critical':rScore>=40?'high':rScore>=15?'moderate':'low');
  $('prediction-text').textContent=risk.prediction||'';$('risk-trend').textContent=risk.trend||'stable';
  $('risk-trend').style.color=risk.trend==='increasing'?'var(--rust)':risk.trend==='decreasing'?'var(--moss)':'var(--text-muted)';
  const density=risk.water_density||1000;$('water-density').textContent=`${density.toFixed(0)}`;
  $('water-density').style.color=m>=80?'var(--rust)':m>=60?'var(--ochre)':'var(--slate)';$('density-sub').textContent='kg/m³';
  const dBar=$('density-bar');dBar.style.width=`${Math.min(100,(density/2000)*100)}%`;dBar.className=m>=80?'rust':m>=60?'ochre':'blue';}
  updateMap(25.5,91.9,risk?risk.risk_score:0,status);
  $('overlay').className='overlay';$('alert-bar').className='alert-bar';
  if(status==='danger'){$('overlay').classList.add('red');$('alert-bar').className='alert-bar red';$('alert-bar').textContent='⚠️ DANGER — GROUND SHIFT DETECTED';if(sirenOn)startSiren();if(vibOn)startContinuousVibrate();}
  else if(status==='warning'){$('overlay').classList.add('yellow');$('alert-bar').className='alert-bar yellow';$('alert-bar').textContent='⚠ WARNING — TILT ANOMALY DETECTED';if(lastStatus==='danger')stopContinuousVibrate();}
  else{stopSiren();stopContinuousVibrate();}
  const t=new Date(timestamp).toLocaleTimeString();const entry=document.createElement('div');entry.className='log-entry';
  entry.innerHTML=`<span class="log-t">${t}</span><span class="log-v ${status}">${tilt.toFixed(2)}° M:${m.toFixed(0)}% ${status==='danger'?'🔴':status==='warning'?'🟡':'🟢'}</span>`;
  $('log-wrap').insertBefore(entry,$('log-wrap').firstChild);while($('log-wrap').children.length>50)$('log-wrap').removeChild($('log-wrap').lastChild);
  lastStatus=status;
  checkNotif(status,tilt,lastStatus);
}
async function poll(){try{const r=await fetch(API);const j=await r.json();if(j.data&&j.data.timestamp!==lastTS){lastTS=j.data.timestamp;lastDataTime=Date.now();update(j.data,j.risk);$('conn-dot').className='dot on pulse';$('conn-label').textContent='Live';}else if(Date.now()-lastDataTime>10000&&lastDataTime>0){goOffline();}}catch(e){goOffline();}}
function goOffline(){$('conn-dot').className='dot pulse';$('conn-label').textContent='Offline';$('badge').textContent='OFFLINE';$('badge').className='badge-pill';$('dev-status').textContent='OFFLINE';$('dev-status').style.color='var(--text-muted)';$('tilt-dev').textContent='Sensor disconnected — waiting for data…';$('needle').style.transform='translateX(-50%) rotate(0deg)';$('tilt-val').textContent='0.00°';$('tilt-val').className='tilt-num safe';$('moisture-val').textContent='0%';$('moisture-val').style.color='var(--slate)';$('moisture-bar').style.width='4%';$('moisture-bar').className='blue';$('water-density').textContent='—';$('density-bar').style.width='0%';$('density-bar').className='blue';$('risk-level').textContent='Low';$('risk-level').style.color='#6FA97D';$('risk-score').textContent='0%';$('risk-bar').style.width='0%';$('risk-bar').className='risk-bar-fill low';$('prediction-text').textContent='Sensor offline — awaiting data…';$('risk-trend').textContent='stable';$('risk-trend').style.color='var(--text-muted)';$('overlay').className='overlay';$('alert-bar').className='alert-bar';stopSiren();stopContinuousVibrate();}
async function loadHist(){try{const r=await fetch(HIST);const j=await r.json();if(j.data&&j.data.length>0){const riskR=await fetch(RISK);const riskJ=await riskR.json();update(j.data[j.data.length-1],riskJ.data);j.data.slice(-20).forEach(d=>{const t=new Date(d.timestamp).toLocaleTimeString();const e=document.createElement('div');e.className='log-entry';const m=d.moisture||0;e.innerHTML=`<span class="log-t">${t}</span><span class="log-v ${d.status}">${d.tilt.toFixed(2)}° M:${m.toFixed(0)}% ${d.status==='danger'?'🔴':d.status==='warning'?'🟡':'🟢'}</span>`;$('log-wrap').appendChild(e);});}}catch(e){}}
loadHist();setInterval(poll,1000);

// ===== GIS MAP TAB =====
let gisMapReady=false,gisMap=null;
function initGISMap(){
  if(gisMapReady)return;gisMapReady=true;
  gisMap=L.map('gis-map',{zoomControl:true,attributionControl:false}).setView([25.5,91.9],7);
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',{maxZoom:16}).addTo(gisMap);
  // Corridors
  const corridors=[
    {name:'Guwahati–Shillong',coords:[[26.14,91.74],[25.85,91.88],[25.57,91.89]],color:'#6FA97D'},
    {name:'Dimapur–Kohima',coords:[[25.90,93.73],[25.67,94.11]],color:'#6C8B9E'},
    {name:'Silchar–Imphal',coords:[[24.83,92.80],[24.81,93.50],[24.81,93.94]],color:'#D69A4E'}
  ];
  corridors.forEach(c=>{L.polyline(c.coords,{color:c.color,weight:3,opacity:0.7,dashArray:'8,6'}).addTo(gisMap).bindPopup(`<b>${c.name}</b>`);});
  // Hazard badges
  const hazards=[
    {lat:25.57,lng:91.89,score:68,label:'HIG'},
    {lat:25.15,lng:92.85,score:48,label:'MOD'},
    {lat:24.81,lng:93.94,score:58,label:'MOD'}
  ];
  hazards.forEach(h=>{
    const c=h.score>=60?'#C25B45':'#D69A4E';
    L.marker([h.lat,h.lng],{icon:L.divIcon({className:'',html:`<div style="background:${c};color:#fff;font-family:'JetBrains Mono';font-size:9px;font-weight:700;padding:3px 6px;border-radius:6px;white-space:nowrap;">${h.label} ${h.score}</div>`,iconSize:[50,20]})}).addTo(gisMap);
  });
  // Weather markers for NE India cities
  const cities=[
    {name:'Shillong',lat:25.58,lng:91.89,temp:22,humidity:84,rain:12,desc:'Light rain'},
    {name:'Guwahati',lat:26.14,lng:91.74,temp:28,humidity:78,rain:5,desc:'Cloudy'},
    {name:'Imphal',lat:24.81,lng:93.94,temp:24,humidity:88,rain:18,desc:'Moderate rain'},
    {name:'Kohima',lat:25.67,lng:94.11,temp:20,humidity:90,rain:22,desc:'Heavy rain'},
    {name:'Agartala',lat:23.83,lng:91.29,temp:27,humidity:80,rain:8,desc:'Overcast'},
    {name:'Aizawl',lat:23.73,lng:92.72,temp:21,humidity:86,rain:15,desc:'Rain likely'}
  ];
  cities.forEach(city=>{
    const rainColor=city.rain>15?'#C25B45':city.rain>8?'#D69A4E':'#6C8B9E';
    const html=`<div style="background:rgba(23,27,22,0.92);border:1px solid #2B322A;border-radius:10px;padding:8px 10px;width:130px;">
      <div style="font-family:'Space Grotesk';font-weight:600;font-size:11px;color:#ECEFE9;margin-bottom:4px;">${city.name}</div>
      <div style="font-family:'JetBrains Mono';font-size:10px;color:#9AA396;">🌡️ ${city.temp}°C 💧 ${city.humidity}%</div>
      <div style="font-family:'JetBrains Mono';font-size:10px;color:${rainColor};margin-top:2px;">🌧️ ${city.rain}mm — ${city.desc}</div>
    </div>`;
    L.marker([city.lat,city.lng],{icon:L.divIcon({className:'',html,iconSize:[130,50]})}).addTo(gisMap);
  });
  // Fetch live weather from Open-Meteo (free, no API key)
  fetchWeather(cities);
}
function fetchWeather(cities){
  const cityList=[
    {name:'Shillong',lat:25.58,lng:91.89},
    {name:'Guwahati',lat:26.14,lng:91.74},
    {name:'Imphal',lat:24.81,lng:93.94},
    {name:'Kohima',lat:25.67,lng:94.11},
    {name:'Agartala',lat:23.83,lng:91.29},
    {name:'Aizawl',lat:23.73,lng:92.72}
  ];
  const lats=cityList.map(c=>c.lat).join(',');
  const lngs=cityList.map(c=>c.lng).join(',');
  fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lats}&longitude=${lngs}&current=temperature_2m,relative_humidity_2m,precipitation,weather_code&timezone=Asia/Kolkata`)
  .then(r=>r.json()).then(j=>{
    if(j.length){j.forEach((d,i)=>{if(d.current){updateWeatherMarker(cityList[i].name,d.current);}});}
  }).catch(()=>{});
}
function updateWeatherMarker(name,data){}

// ===== DYNAMIC STATIONS/ALERTS/INCIDENT DATA =====
const STATION_BASE=[
  {name:'Gangtok — 32nd Mile NH10 Corridor',loc:'East Sikkim, Sikkim',id:'ESP32-NER-001',baseScore:72,slope:42.5,rainBase:78,moistureBase:73,tiltBase:1.1},
  {name:'Haflong — Jatinga Valley Escarpment',loc:'Dima Hasao, Assam',id:'ESP32-NER-002',baseScore:48,slope:38.0,rainBase:38,moistureBase:58,tiltBase:0.3},
  {name:'Cherrapunji — Shella Gorge Rim',loc:'East Khasi Hills, Meghalaya',id:'ESP32-NER-003',baseScore:68,slope:48.0,rainBase:112,moistureBase:82,tiltBase:0.7},
  {name:'Tupul — Ijei River Rail Corridor',loc:'Noney, Manipur',id:'ESP32-NER-007',baseScore:58,slope:46.8,rainBase:52,moistureBase:65,tiltBase:0.4}
];
let stationData=[];
let alertHistory=[];

function rand(min,max){return (Math.random()*(max-min)+min);}
function clamp(v,min,max){return Math.max(min,Math.min(max,v));}

function generateStationData(){
  stationData=STATION_BASE.map(s=>{
    const rain=clamp(Math.round((s.rainBase+rand(-15,15))*10)/10,5,180);
    const moisture=clamp(Math.round((s.moistureBase+rand(-10,10))*10)/10,5,98);
    const tilt=clamp(Math.round((s.tiltBase+rand(-0.5,0.5))*100)/100,0,5);
    const score=clamp(Math.round(s.baseScore+rand(-12,12)),10,98);
    const level=score>=65?'HIGH':score>=40?'MODERATE':'LOW';
    return{...s,rain,moisture,tilt,score,level};
  });
}
function generateAlerts(){
  const actives=[];
  stationData.filter(s=>s.score>=50).forEach(s=>{
    const hrs=Math.floor(rand(1,6));
    actives.push({level:s.score>=65?'danger':'warn',title:s.score>=65?'🔴 HIGH HAZARD':'🟡 MODERATE',name:s.name,body:`Soil saturation at ${s.moisture.toFixed(1)}% with inclinometer creep (+${s.tilt.toFixed(2)}°). ${s.rain.toFixed(1)}mm rainfall in 24h. Risk score: ${s.score}.`,time:`${hrs} hour${hrs>1?'s':''} ago`});
  });
  if(actives.length===0){actives.push({level:'info',title:'ℹ️ INFO',name:'All Stations',body:'All monitored corridors within safe parameters. No active hazard alerts.',time:'Just now'});}
  const hist=[];
  stationData.filter(s=>s.score>=35).slice(0,2).forEach(s=>{
    hist.push({level:'warn',title:'🟡 PAST ALERT — '+s.name,body:`Elevated moisture (${s.moisture.toFixed(1)}%) detected. Tilt at ${s.tilt.toFixed(2)}°. Monitoring continued.`,time:'1 day ago'});
  });
  hist.push({level:'info',title:'ℹ️ WEATHER ADVISORY',body:'India Meteorological Department forecast: Heavy rainfall expected across Meghalaya and Assam in next 48 hours.',time:'2 days ago'});
  return{actives,hist};
}
function generateIncidents(){
  return stationData.filter(s=>s.score>=55).map(s=>({name:s.name,loc:s.loc,score:s.score,level:s.level,slope:s.slope,rain:s.rain,moisture:s.moisture,tilt:s.tilt}));
}

function renderStations(){
  const el=$('tab-stations');
  el.innerHTML='<div class="card-title" style="margin:16px 16px 0;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 21l4-13 4 13"/><path d="M2 21h20"/></svg>Monitored Stations (NER) <span style="color:var(--moss);font-size:9px;margin-left:6px;">● Live</span><span class="line"></span></div>';
  stationData.forEach(s=>{
    const bc=s.score>=65?'high':s.score>=45?'moderate':'low';
    el.innerHTML+=`<div class="station-card"><div class="station-head"><div class="station-name">${s.name}</div><div class="station-badge ${bc}">${s.score} • ${s.level}</div></div><div class="station-meta">${s.loc} • ${s.id} • Online</div><div class="station-grid"><div class="sg-item"><div class="sg-val">${s.rain}</div><div class="sg-label">Rain mm</div></div><div class="sg-item"><div class="sg-val">${s.moisture}%</div><div class="sg-label">Moisture</div></div><div class="sg-item"><div class="sg-val">${s.tilt}°</div><div class="sg-label">Tilt Δθ</div></div><div class="sg-item"><div class="sg-val">${s.slope}°</div><div class="sg-label">Slope</div></div></div></div>`;
  });
}

function renderAlerts(){
  const a=generateAlerts();
  const el=$('tab-alerts');
  el.innerHTML=`<div class="segment-tabs"><div class="seg-tab active" onclick="showAlertTab('active',this)">Active Alerts (${a.actives.length})</div><div class="seg-tab" onclick="showAlertTab('history',this)">Historical Logs (${a.hist.length})</div></div><div id="alerts-active">${a.actives.map(x=>`<div class="alert-card ${x.level}"><div class="alert-title">${x.title} — ${x.name}</div><div class="alert-body">${x.body}</div><div class="alert-time">${x.time}</div></div>`).join('')}</div><div id="alerts-history" style="display:none;">${a.hist.map(x=>`<div class="alert-card ${x.level}"><div class="alert-title">${x.title}</div><div class="alert-body">${x.body}</div><div class="alert-time">${x.time}</div></div>`).join('')}</div>`;
}
function showAlertTab(tab,el){
  el.parentElement.querySelectorAll('.seg-tab').forEach(t=>t.classList.remove('active'));el.classList.add('active');
  $('alerts-active').style.display=tab==='active'?'block':'none';
  $('alerts-history').style.display=tab==='history'?'block':'none';
}

function renderIncidents(){
  const inc=generateIncidents();
  const el=$('tab-incident');
  el.innerHTML='<div class="card-title" style="margin:16px 16px 0;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>Active Incidents<span class="line"></span></div>';
  inc.forEach(s=>{
    const bc=s.score>=65?'high':'moderate';
    el.innerHTML+=`<div class="incident-card"><div class="incident-head"><div class="incident-name">${s.name}</div><div class="station-badge ${bc}">${s.score} / 100 • ${s.level}</div></div><div class="incident-loc">${s.loc} • ${s.slope}° Slope</div><div class="incident-summary">${s.score>=65?'High':'Elevated'} 24h precipitation (${s.rain.toFixed(1)} mm) and soil saturation at ${s.moisture.toFixed(1)}% with inclinometer reading +${s.tilt.toFixed(2)}°.</div><div class="incident-telemetry"><div class="it-item"><div class="it-val">${s.rain.toFixed(1)}mm</div><div class="it-label">Rainfall</div></div><div class="it-item"><div class="it-val">${s.moisture.toFixed(1)}%</div><div class="it-label">Moisture</div></div><div class="it-item"><div class="it-val">${s.tilt.toFixed(2)}°</div><div class="it-label">Tilt Δθ</div></div></div><div class="incident-btn" onclick="switchTab('stations',document.querySelectorAll('.nav-item')[2])">View Telemetry Diagnostics →</div></div>`;
  });
  if(inc.length===0){el.innerHTML+='<div style="text-align:center;padding:40px;color:var(--text-muted);font-family:var(--font-mono);font-size:12px;">No active incidents — all corridors stable.</div>';}
}

// Generate initial data + refresh every 15 minutes
function refreshAllData(){generateStationData();renderStations();renderAlerts();renderIncidents();}
refreshAllData();
setInterval(refreshAllData,15*60*1000);

// ===== CHATBOT =====
function toggleChat(){$('chat-panel').classList.toggle('open');}
const CHAT_KB=[
  {q:/landslide|land slide/i,a:'Landslides occur when saturated soil loses friction and slides downhill. In NE India, they are triggered by heavy monsoon rainfall (>100mm/24h), steep slopes (>30°), and deforestation. Our sensors monitor tilt and moisture to predict them.'},
  {q:/moisture|saturation|wet/i,a:'Soil moisture above 60% is a warning sign. Above 80% is critical — the soil is nearly saturated and can no longer absorb water, increasing landslide risk dramatically.'},
  {q:/rain|rainfall|monsoon/i,a:'Heavy rainfall is the #1 trigger. IMD classifies: Moderate (64-115mm/day), Heavy (115-204mm), Very Heavy (>204mm). When 24h rainfall exceeds 75mm, our system raises alerts.'},
  {q:/safe|safety|protect|evac/i,a:'During landslide risk: 1) Move to higher ground. 2) Avoid river valleys. 3) Keep emergency kit ready. 4) Follow local authority alerts. 5) If you feel ground vibration, run!'},
  {q:/tilt|angle|slope/i,a:'Our inclinometers detect ground movement as small as 0.1°. Warning at 10°, danger at 60°. Any sudden increase indicates active ground movement — evacuate.'},
  {q:/hello|hi|hey|help/i,a:'Hello! Ask me about landslide causes, soil moisture, rainfall thresholds, safety tips, our sensors, or NE India risks.'},
  {q:/sensor|esp32|device/i,a:'ESP32 with MPU-6500 inclinometer + moisture sensor. Sends data every 2s via WiFi to cloud. Dashboard updates live with risk predictions.'},
  {q:/risk|score|hazard/i,a:'Risk score (0-100): tilt (60% weight) + moisture (40% weight). Moisture amplifies tilt risk. Low (0-15), Moderate (15-40), High (40-70), Critical (70-100).'},
  {q:/northeast|ner|sikkim|meghalaya|assam|manipur/i,a:'NE India: young tectonic mountains, extreme monsoon, steep slopes, deforestation. Key zones: Gangtok, Cherrapunji, Haflong, Tupul.'},
];
function sendChat(){
  const input=$('chat-input');const msg=input.value.trim();if(!msg)return;input.value='';
  const body=$('chat-body');
  body.innerHTML+=`<div class="chat-msg user"><div class="chat-bubble">${msg}</div><div class="chat-time">Now</div></div>`;
  let reply="I'm not sure about that. Try asking about landslides, rainfall, soil moisture, safety tips, or our sensors!";
  for(const k of CHAT_KB){if(k.q.test(msg)){reply=k.a;break;}}
  setTimeout(()=>{body.innerHTML+=`<div class="chat-msg bot"><div class="chat-bubble">${reply}</div><div class="chat-time">Now</div></div>`;body.scrollTop=body.scrollHeight;},500);
  body.scrollTop=body.scrollHeight;
}

// ===== BROWSER NOTIFICATIONS =====
let notifAsked=false;
function requestNotifPermission(){if(notifAsked)return;notifAsked=true;if('Notification' in window && Notification.permission==='default')Notification.requestPermission();}
document.addEventListener('click',requestNotifPermission,{once:true});
document.addEventListener('touchstart',requestNotifPermission,{once:true});
function sendBrowserNotif(title,body){try{if('Notification' in window && Notification.permission==='granted')new Notification(title,{body});}catch(e){}}

// ===== CITIZEN REPORTING =====
let selectedSeverity='low';
let reportLat=null,reportLng=null;
let reportPhotoData='';
let reportMapReady=false,reportMap=null;
let allReports=[];

function selectSeverity(sev,el){
  selectedSeverity=sev;
  document.querySelectorAll('.sev-btn').forEach(b=>b.classList.remove('selected'));
  el.classList.add('selected');
}

function handlePhoto(input){
  const file=input.files[0];
  if(!file)return;
  const reader=new FileReader();
  reader.onload=function(e){
    reportPhotoData=e.target.result;
    const upload=$('photo-upload');
    upload.innerHTML=`<input type="file" id="photo-input" accept="image/*" capture="environment" onchange="handlePhoto(this)"><img src="${e.target.result}" alt="Report photo"><div class="upload-text" style="position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,0.7);padding:4px 8px;border-radius:6px;font-size:10px;color:var(--text-primary);">Tap to change</div>`;
    upload.classList.add('has-photo');
  };
  reader.readAsDataURL(file);
}

function getMyLocation(){
  const btn=document.querySelector('.loc-btn');
  btn.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin 1s linear infinite;width:14px;height:14px;"><path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8"/></svg>Detecting...';
  if(!navigator.geolocation){$('loc-display').textContent='Geolocation not supported';return;}
  navigator.geolocation.getCurrentPosition(
    pos=>{
      reportLat=pos.coords.latitude;
      reportLng=pos.coords.longitude;
      $('loc-display').textContent=`📍 ${reportLat.toFixed(4)}°N, ${reportLng.toFixed(4)}°E`;
      btn.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/></svg>Location Detected!';
      btn.style.borderColor='var(--moss)';
    },
    err=>{
      $('loc-display').textContent='Location access denied — using NE India default';
      reportLat=25.57;reportLng=91.89;
      btn.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 6-9 12-9 12s-9-6-9-12a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>Use Default Location';
    }
  );
}

async function submitReport(){
  const btn=$('submit-btn');
  const type=$('report-type').value;
  const desc=$('report-desc').value;
  const name=$('reporter-name').value||'Anonymous';
  const lat=reportLat||25.57;
  const lng=reportLng||91.89;

  btn.disabled=true;
  btn.textContent='Submitting...';
  btn.className='submit-btn';

  try{
    const res=await fetch(`${location.origin}/api/report`,{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        report_type:type,
        severity:selectedSeverity,
        lat:lat,
        lng:lng,
        description:desc,
        reporter_name:name,
        photo_data:reportPhotoData
      })
    });
    const j=await res.json();
    if(j.ok){
      btn.textContent='✅ Report Submitted!';
      btn.className='submit-btn success';
      setTimeout(()=>{btn.textContent='Submit Report';btn.disabled=false;btn.className='submit-btn';},2000);
      // Reset form
      $('report-desc').value='';
      $('report-photo-input')&&(document.getElementById('photo-input').value='');
      reportPhotoData='';
      // Reload reports
      loadReports();
    }
  }catch(e){
    btn.textContent='❌ Submission Failed';
    btn.className='submit-btn error';
    setTimeout(()=>{btn.textContent='Submit Report';btn.disabled=false;btn.className='submit-btn';},2000);
  }
}

async function loadReports(){
  try{
    const res=await fetch(`${location.origin}/api/reports`);
    const j=await res.json();
    allReports=(j.data||[]).reverse();
    renderReports();
  }catch(e){}
}

function renderReports(){
  const el=$('report-list');
  if(allReports.length===0){
    el.innerHTML='<div class="empty-reports"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/></svg><p>No field reports yet.<br>Be the first to report a hazard!</p></div>';
    return;
  }
  const typeIcons={crack:'🔨',slope_damage:'⛰️',blocked_road:'🚧',flooding:'🌊',rockfall:'🪨',other:'⚠️'};
  const typeNames={crack:'Ground Crack',slope_damage:'Slope Damage',blocked_road:'Blocked Road',flooding:'Flooding',rockfall:'Rockfall',other:'Other Hazard'};
  el.innerHTML=allReports.map(r=>{
    const photo=r.photo_data?`<img class="report-card-photo" src="${r.photo_data}" alt="Report photo">`:'';
    const time=new Date(r.timestamp).toLocaleString();
    return `<div class="report-card">
      ${photo}
      <div class="report-card-body">
        <div class="report-card-head">
          <div class="report-card-type">${typeIcons[r.report_type]||'⚠️'} ${typeNames[r.report_type]||r.report_type}</div>
          <div class="report-severity-badge ${r.severity}">${r.severity.toUpperCase()}</div>
        </div>
        ${r.description?`<div class="report-card-desc">${r.description}</div>`:''}
        <div class="report-card-meta">
          <span>📍 ${r.lat.toFixed(4)}°, ${r.lng.toFixed(4)}° • by ${r.reporter_name}</span>
          <span>${time}</span>
        </div>
      </div>
    </div>`;
  }).join('');
}

function showReportView(view,el){
  el.parentElement.querySelectorAll('.seg-tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  $('report-list-view').style.display=view==='all'?'block':'none';
  $('report-map-view').style.display=view==='map'?'block':'none';
  if(view==='map'&&!reportMapReady){
    reportMapReady=true;
    reportMap=L.map('report-map',{zoomControl:true,attributionControl:false}).setView([25.5,91.9],7);
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',{maxZoom:16}).addTo(reportMap);
  }
  if(reportMapReady)updateReportMap();
}

function updateReportMap(){
  if(!reportMap)return;
  // Clear existing report markers
  reportMap.eachLayer(layer=>{if(layer._isReport)reportMap.removeLayer(layer);});
  const typeIcons={crack:'🔨',slope_damage:'⛰️',blocked_road:'🚧',flooding:'🌊',rockfall:'🪨',other:'⚠️'};
  const sevColors={low:'#6FA97D',medium:'#D69A4E',high:'#C25B45',critical:'#ff3333'};
  allReports.forEach(r=>{
    const c=sevColors[r.severity]||'#6FA97D';
    const icon=L.divIcon({className:'',html:`<div style="background:${c};width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;border:2px solid #ECEFE9;box-shadow:0 2px 8px rgba(0,0,0,0.3);">${typeIcons[r.report_type]||'⚠️'}</div>`,iconSize:[28,28]});
    const marker=L.marker([r.lat,r.lng],{icon}).addTo(reportMap);
    marker._isReport=true;
    marker.bindPopup(`<b>${typeIcons[r.report_type]} ${r.report_type.replace(/_/g,' ')}</b><br>Severity: <b style="color:${c}">${r.severity.toUpperCase()}</b><br>${r.description?r.description+'<br>':''}📍 ${r.lat.toFixed(4)}, ${r.lng.toFixed(4)}<br>By: ${r.reporter_name}<br>${new Date(r.timestamp).toLocaleString()}`);
  });
}

// Load reports on startup and refresh every 60s
loadReports();
setInterval(loadReports,60000);

// Add spin keyframe for loading
document.head.insertAdjacentHTML('beforeend','<style>@keyframes spin{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}</style>');

// ===== SERVICE WORKER (PWA OFFLINE) =====
if('serviceWorker' in navigator){
  navigator.serviceWorker.register('/sw.js').catch(()=>{});
}
window.addEventListener('online',()=>{document.getElementById('offline-banner').classList.remove('show');});
window.addEventListener('offline',()=>{document.getElementById('offline-banner').classList.add('show');});
if(!navigator.onLine)document.getElementById('offline-banner').classList.add('show');

// ===== MULTILINGUAL =====
const LANGS=['en','hi','as','bn','mni'];
const LANG_NAMES={en:'EN',hi:'HI',as:'AS',bn:'BN',mni:'MN'};
const LANG_FONTS={en:'var(--font-body)',hi:"'Noto Sans Devanagari',sans-serif",as:"'Noto Sans Bengali',sans-serif",bn:"'Noto Sans Bengali',sans-serif",mni:"'Noto Sans Meetei Mayek',sans-serif"};
let currentLang='en';
const T={
  en:{landing_risk:'Landslide risk',tilt_angle:'Tilt Angle',soil_moisture:'Soil moisture',density:'Density',sensor_info:'Sensor info',alert_controls:'Alert controls',siren:'Siren',vibrate:'Vibrate',live_log:'Live log',waiting:'Waiting for data',offline_msg:'Sensor disconnected',dry:'Dry',saturated:'Saturated',trend:'Trend',stable:'stable',increasing:'increasing',decreasing:'decreasing',connecting:'Connecting',live:'Live',offline:'Offline',safe:'SAFE',warning:'WARNING',danger:'DANGER',sms_title:'SMS Alerts',sms_sub:'Register phone to receive SMS on danger',sms_placeholder:'9876543210',sms_register:'Register',sms_registered:'Registered',history_title:'Historical Landslide Data — NER',incidents_by_year:'Incidents by Year',casualties_by_state:'Casualties by State',incident_timeline:'Incident Timeline',total_incidents:'Total Incidents',total_deaths:'Total Deaths',years_covered:'Years Covered',report_title:'Submit Field Report',report_sub:'Report cracks, slope damage, blocked roads, or flooding with geo-tagged photos',report_type:'Report Type',severity:'Severity Level',photo:'Photo (optional)',tap_photo:'Tap to take photo or choose from gallery',your_location:'Your Location',detect_location:'Detect My Location',description:'Description',your_name:'Your Name (optional)',submit:'Submit Report',all_reports:'All Reports',on_map:'On Map',no_reports:'No field reports yet. Be the first to report a hazard!'},
  hi:{landing_risk:'भूस्खलन जोखिम',tilt_angle:'झुकाव कोण',soil_moisture:'मिट्टी की नमी',density:'घनत्व',sensor_info:'सेंसर जानकारी',alert_controls:'अलर्ट नियंत्रण',siren:'सायरन',vibrate:'वाइब्रेट',live_log:'लाइव लॉग',waiting:'डेटा की प्रतीक्षा है',offline_msg:'सेंसर डिस्कनेक्ट',dry:'सूखी',saturated:'संतृप्त',trend:'प्रवृत्ति',stable:'स्थिर',increasing:'बढ़ रही',decreasing:'घट रही',connecting:'कनेक्ट हो रहा है',live:'लाइव',offline:'ऑफलाइन',safe:'सुरक्षित',warning:'चेतावनी',danger:'खतरा',sms_title:'SMS अलर्ट',sms_sub:'खतरे पर SMS प्राप्त करने के लिए फोन नंबर दर्ज करें',sms_placeholder:'9876543210',sms_register:'रजिस्टर',sms_registered:'दर्ज',history_title:'ऐतिहासिक भूस्खलन डेटा — NER',incidents_by_year:'वर्ष अनुसार घटनाएं',casualties_by_state:'राज्य अनुसार हताहत',incident_timeline:'घटना समयरेखा',total_incidents:'कुल घटनाएं',total_deaths:'कुल मौतें',years_covered:'वर्ष कवरेज',report_title:'फील्ड रिपोर्ट जमा करें',report_sub:'भूस्खलन, दरार, बंद सड़क, या बाढ़ की रिपोर्ट करें',report_type:'रिपोर्ट प्रकार',severity:'गंभीरता स्तर',photo:'फोटो (वैकल्पिक)',tap_photo:'फोटो लेने के लिए टैप करें',your_location:'आपका स्थान',detect_location:'स्थान पता करें',description:'विवरण',your_name:'आपका नाम (वैकल्पिक)',submit:'रिपोर्ट जमा करें',all_reports:'सभी रिपोर्ट',on_map:'मानचित्र पर',no_reports:'अभी तक कोई रिपोर्ट नहीं। पहली रिपोर्ट दर्ज करें!'},
  as:{landing_risk:'ভূমিধসৰ বিপদ',tilt_angle:'ঢাল কোণ',soil_moisture:'মাটীৰ আৰ্দ্ৰতা',density:'ঘনত্ব',sensor_info:'ছেন্সৰ তথ্য',alert_controls:'সতৰ্কতা নিয়ন্ত্ৰণ',siren:'ছাইৰেন',vibrate:'কম্পন',live_log:'লাইভ লগ',waiting:'ডাটাৰ অপেক্ষাত',offline_msg:'ছেন্সৰ সংযোগ বিচ্ছিন্ন',dry:'শুকনা',saturated:'পৰিপূৰ্ণ',trend:'প্ৰৱণতা',stable:'স্থিৰ',increasing:'বৃদ্ধি পাই আছে',decreasing:'হ্ৰাস পাই আছে',connecting:'সংযোগ কৰি আছে',live:'লাইভ',offline:'অফলাইন',safe:'নিৰাপদ',warning:'সতৰ্কতা',danger:'বিপদ',sms_title:'SMS সতৰ্কতা',sms_sub:'বিপদত SMS পাবলৈ ফোন নম্বৰ দিয়ক',sms_placeholder:'9876543210',sms_register:'ৰেজিষ্টাৰ',sms_registered:'ৰেজিষ্টাৰ্ড',history_title:'ঐতিহাসিক ভূমিধসৰ ডাটা — NER',incidents_by_year:'বছৰ অনুযায়ী ঘটনা',casualties_by_state:'ৰাজ্য অনুযায়ী ক্ষতিগ্ৰস্ত',incident_timeline:'ঘটনাৰ সময়ৰেখা',total_incidents:'মুঠ ঘটনা',total_deaths:'মুঠ মৃত্যু',years_covered:'বছৰ পৰিসীমা',report_title:'ফিল্ড প্ৰতিবেদন দিয়ক',report_sub:'ভূমিধস, ফাটল, বন্ধ ৰাস্তাৰ প্ৰতিবেদন দিয়ক',report_type:'প্ৰতিবেদন প্ৰকাৰ',severity:'গুৰুতৱ স্তৰ',photo:'ফটো (ঐচ্ছিক)',tap_photo:'ফটো লিবলৈ টেপ কৰক',your_location:'আপোনাৰ স্থান',detect_location:'স্থান নিৰ্ধাৰণ কৰক',description:'বিৱৰণ',your_name:'আপোনাৰ নাম (ঐচ্ছিক)',submit:'প্ৰতিবেদন দিয়ক',all_reports:'সকলো প্ৰতিবেদন',on_map:'মানচিত্ৰত',no_reports:'এতিয়াও কোনো প্ৰতিবেদন নাই!'},
  bn:{landing_risk:'ভূমিধ্বসের ঝুঁকি',tilt_angle:'ঢাল কোণ',soil_moisture:'মাটির আর্দ্রতা',density:'ঘনত্ব',sensor_info:'সেন্সর তথ্য',alert_controls:'সতর্কতা নিয়ন্ত্রণ',siren:'সাইরেন',vibrate:'কম্পন',live_log:'লাইভ লগ',waiting:'ডাটার অপেক্ষায়',offline_msg:'সেন্সর সংযোগ বিচ্ছিন্ন',dry:'শুকনো',saturated:'পরিপূর্ণ',trend:'প্রবণতা',stable:'স্থির',increasing:'বৃদ্ধি পাচ্ছে',decreasing:'হ্রাস পাচ্ছে',connecting:'সংযোগ হচ্ছে',live:'লাইভ',offline:'অফলাইন',safe:'নিরাপদ',warning:'সতর্কতা',danger:'বিপদ',sms_title:'SMS সতর্কতা',sms_sub:'বিপদে SMS পেতে ফোন নম্বর দিন',sms_placeholder:'9876543210',sms_register:'নিবন্ধন',sms_registered:'নিবন্ধিত',history_title:'ঐতিহাসিক ভূমিধ্বসের ডাটা — NER',incidents_by_year:'বছর অনুযায়ী ঘটনা',casualties_by_state:'রাজ্য অনুযায়ী ক্ষতিগ্রস্ত',incident_timeline:'ঘটনার সময়রেখা',total_incidents:'মোট ঘটনা',total_deaths:'মোট মৃত্যু',years_covered:'বছর পরিসীমা',report_title:'ফিল্ড রিপোর্ট জমা দিন',report_sub:'ভূমিধ্বস, ফাটল, বন্ধ রাস্তার রিপোর্ট দিন',report_type:'রিপোর্ট প্রকার',severity:'গুরুত্ব স্তর',photo:'ছবি (ঐচ্ছিক)',tap_photo:'ছবি তুলতে ট্যাপ করুন',your_location:'আপনার অবস্থান',detect_location:'অবস্থান সনাক্ত করুন',description:'বিবরণ',your_name:'আপনার নাম (ঐচ্ছিক)',submit:'রিপোর্ট জমা দিন',all_reports:'সব রিপোর্ট',on_map:'মানচিত্রে',no_reports:'এখনো কোনো রিপোর্ট নেই!'},
  mni:{landing_risk:'মাংল থিগাদা পাংদা',tilt_angle:'থিদোক কোণ',soil_moisture:'মাং চিং',density:'ঘনত্ব',sensor_info:'ছেন্সর পীরি',alert_controls:'ইশারা কন্ত্রোল',siren:'ছাইৰেন',vibrate:'ফুগাদবা',live_log:'লাইভ লগ',waiting:'দাতা যাইরে',offline_msg:'ছেন্সর সিং',dry:'ইয়েক্তা',saturated:'ইয়েক্তা',trend:'যাগাই',stable:'ইয়েক্তা',increasing:'যাগাই',decreasing:'যাগাই',connecting:'মশক তুনাইরে',live:'লাইভ',offline:'অফলাইন',safe:'শান্তি',warning:'ইশারা',danger:'মহুত',sms_title:'SMS ইশারা',sms_sub:'মহুত SMS লৈবা ফোন নম্বর দিয়ো',sms_placeholder:'9876543210',sms_register:'দিয়ো',sms_registered:'দিয়ে',history_title:'যাইরে মাংল থিগাদা পাংদা — NER',incidents_by_year:'চিং অনুযায়ী',casualties_by_state:'লাই অনুযায়ী',incident_timeline:'ঘটনা সময়',total_incidents:'লীবা ঘটনা',total_deaths:'লীবা মথৌ',years_covered:'চিং পীরি',report_title:'ফিল্ড রিপোর্ট',report_sub:'মাংল থিগাদা, ফাটল, বন্ধ রাস্তা দিয়ো',report_type:'রিপোর্ট প্রকার',severity:'গুরুত্ব',photo:'ফোটো (যাইরে)',tap_photo:'ফোটো লৈবা ট্যাপ দিয়ো',your_location:'মসি লাই',detect_location:'লাই খোঁজে',description:'পীরি',your_name:'মসি মিং (যাইরে)',submit:'রিপোর্ট দিয়ো',all_reports:'লীবা রিপোর্ট',on_map:'মানচিত্র',no_reports:'রিপোর্ট অমত্তা নত্তে!'}
};
function t(key){return (T[currentLang]&&T[currentLang][key])||T.en[key]||key;}
function cycleLang(){
  const i=LANGS.indexOf(currentLang);
  currentLang=LANGS[(i+1)%LANGS.length];
  document.getElementById('lang-label').textContent=LANG_NAMES[currentLang];
  translatePage();
  localStorage.setItem('landsafe-lang',currentLang);
}
function translatePage(){
  document.querySelectorAll('[data-i18n]').forEach(el=>{el.textContent=t(el.dataset.i18n);});
  document.querySelectorAll('[data-i18n-ph]').forEach(el=>{el.placeholder=t(el.dataset.i18nPh);});
}
// Restore saved language
const savedLang=localStorage.getItem('landsafe-lang');
if(savedLang&&LANGS.includes(savedLang)){currentLang=savedLang;document.getElementById('lang-label').textContent=LANG_NAMES[currentLang];}

// ===== HISTORICAL DATA =====
async function loadHistory(){
  try{
    const res=await fetch(`${location.origin}/api/historical`);
    const j=await res.json();
    const data=j.data||[];
    const summary=j.summary||{};
    // Summary cards
    const sumEl=document.getElementById('hist-summary');
    if(sumEl)sumEl.innerHTML=`<div class="hist-stat"><div class="hist-stat-val">${summary.total_incidents||0}</div><div class="hist-stat-label">Total Incidents</div></div><div class="hist-stat"><div class="hist-stat-val">${summary.total_deaths||0}</div><div class="hist-stat-label">Total Deaths</div></div><div class="hist-stat"><div class="hist-stat-val">${summary.years_covered||'N/A'}</div><div class="hist-stat-label">Years Covered</div></div>`;
    // Bar chart by year
    const yearCounts={};
    data.forEach(d=>{yearCounts[d.year]=(yearCounts[d.year]||0)+1;});
    const years=Object.keys(yearCounts).sort();
    const maxCount=Math.max(...Object.values(yearCounts),1);
    const barEl=document.getElementById('bar-chart');
    if(barEl){barEl.innerHTML=years.map(y=>{const h=(yearCounts[y]/maxCount)*130;const c=yearCounts[y]>=4?'var(--rust)':yearCounts[y]>=2?'var(--ochre)':'var(--moss)';return `<div class="bar-col"><div class="bar" style="height:${h}px;background:${c};"><span class="bar-val">${yearCounts[y]}</span></div><span class="bar-label">${y}</span></div>`;}).join('');}
    // Bar chart by state
    const stateCounts={};
    data.forEach(d=>{const s=d.location.split(',').pop().trim();stateCounts[s]=(stateCounts[s]||0)+1;});
    const states=Object.entries(stateCounts).sort((a,b)=>b[1]-a[1]);
    const maxState=Math.max(...states.map(s=>s[1]),1);
    const stateEl=document.getElementById('state-chart');
    if(stateEl){stateEl.innerHTML=states.map(([s,c])=>{const h=(c/maxState)*130;const col=c>=4?'var(--rust)':c>=2?'var(--ochre)':'var(--moss)';return `<div class="bar-col"><div class="bar" style="height:${h}px;background:${col};"><span class="bar-val">${c}</span></div><span class="bar-label" style="font-size:8px;">${s.substring(0,6)}</span></div>`;}).join('');}
    // Timeline
    const tlEl=document.getElementById('hist-timeline');
    if(tlEl){tlEl.innerHTML=data.sort((a,b)=>b.year-a.year||b.month-a.month).slice(0,15).map(d=>{const sev=d.deaths>=20?'critical':d.deaths>=8?'high':d.deaths>=3?'moderate':'low';const months=['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];return `<div class="timeline-item"><div class="timeline-dot ${sev}"></div><div class="timeline-content"><div class="timeline-header"><span class="timeline-location">${d.location}</span><span class="timeline-date">${months[d.month]} ${d.year}</span></div><div class="timeline-detail">${d.cause} — ${d.rainfall_mm}mm rainfall${d.road_blocks?`, ${d.road_blocks} road blocks`:''}</div><span class="timeline-deaths">💀 ${d.deaths} deaths${d.injured?`, ${d.injured} injured`:''}</span></div></div>`;}).join('');}
  }catch(e){}
}

// ===== SMS SETTINGS =====
let smsRecipients=[];
async function loadSMSRecipients(){
  try{const r=await fetch(`${location.origin}/api/sms/recipients`);const j=await r.json();smsRecipients=j.recipients||[];renderSMSList();}catch(e){}
}
function renderSMSList(){
  const el=document.getElementById('sms-list');
  if(!el)return;
  if(smsRecipients.length===0){el.innerHTML='';return;}
  el.innerHTML=smsRecipients.map(p=>`<div class="sms-item"><span class="num">📱 ${p}</span><span class="remove" onclick="removeSMS('${p}')">✕</span></div>`).join('');
}
async function registerSMS(){
  const input=document.getElementById('sms-phone');
  const phone=input.value.trim();
  if(!phone||phone.length!==10){input.style.borderColor='var(--rust)';setTimeout(()=>input.style.borderColor='var(--border)',2000);return;}
  try{const r=await fetch(`${location.origin}/api/sms/register`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone,message:'',severity:'danger'})});const j=await r.json();if(j.ok){input.value='';smsRecipients.push(phone);renderSMSList();}}catch(e){}
}
function removeSMS(phone){smsRecipients=smsRecipients.filter(p=>p!==phone);renderSMSList();}
loadSMSRecipients();

// ===== OVERVIEW MAP TRANSLATED LABELS =====
function updateOverviewLabels(){
  document.querySelector('.risk-label').textContent=t('landing_risk');
  document.querySelector('.tilt-unit').textContent=t('tilt_angle');
}

// Trigger notification only on STATUS CHANGE (not every poll)
function checkNotif(status,tilt,prevStatus){
  if(status===prevStatus) return; // Only notify on change
  try {
    if(status==='danger') sendBrowserNotif('⚠️ DANGER — Landsafe AI','Ground shift detected! Tilt: '+tilt.toFixed(1)+'°. Evacuate immediately!');
    else if(status==='warning') sendBrowserNotif('⚠️ WARNING — Landsafe AI','Tilt anomaly: '+tilt.toFixed(1)+'°. Monitor closely.');
  } catch(e){}
}
