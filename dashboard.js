'use strict';
const METRICS={
 Weight_kg:['体重','kg',1],BodyFat_percent:['体脂率','%',1],BMI:['BMI','',1],MuscleMass_kg:['肌肉量','kg',1],
 MuscleRate_percent:['肌肉率','%',1],SkeletalMuscleMass_kg:['骨骼肌量','kg',1],SkeletalMuscleRate_percent:['骨骼肌率','%',1],
 BodyWater_percent:['体水分率','%',1],BodyWaterMass_kg:['体水分量','kg',1],BoneMass_kg:['骨量','kg',1],ProteinMass_kg:['蛋白质量','kg',1],
 ProteinRate_percent:['蛋白率','%',1],VisceralFat:['内脏脂肪指标','',1],BasalMetabolism_kcal_per_day:['基础代谢','kcal/天',0],
 MetabolicAge_years:['代谢年龄','岁',0],FatMass_kg:['脂肪量','kg',1],FatFreeMass_kg:['去脂体重','kg',1],StandardWeight_kg:['标准体重','kg',1],
 WeightControl_kg:['体重控制量','kg',1],MuscleControl_kg:['肌肉控制量','kg',1],FatControl_kg:['脂肪控制量','kg',1],BodyScore:['身体评分','',0]
};
const $=id=>document.getElementById(id);
let rows=[],metric='Weight_kg',days=0,grouping='day',busy=false;
let syncing=false,syncToken='',lastSyncState='idle';
try{const saved=JSON.parse(localStorage.getItem('body-journal-view')||'{}');if(['day','week','month'].includes(saved.grouping))grouping=saved.grouping;if(METRICS[saved.metric])metric=saved.metric;if([0,7,30,90].includes(saved.days))days=saved.days;}catch{}
const format=(value,key)=>Number.isFinite(value)?value.toFixed(METRICS[key][2]):'—';
const shortDate=stamp=>new Date(stamp*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false});
function save(){try{localStorage.setItem('body-journal-view',JSON.stringify({metric,days,grouping}));}catch{}}
function filtered(){if(!days)return rows;const today=new Date(Date.now()+8*3600000).toISOString().slice(0,10);const cutoff=BodyStats.periodIndex(today,'day')-days+1;return rows.filter(row=>BodyStats.periodIndex(row.Date,'day')>=cutoff);}
function svg(tag,attributes={},text){const element=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[key,value]of Object.entries(attributes))element.setAttribute(key,String(value));if(text!==undefined)element.textContent=text;return element;}
function choose(key){metric=key;save();render();}
function render(){
 $('metric-select').value=metric; $('group-select').value=grouping;
 document.querySelectorAll('[data-metric]').forEach(button=>{const selected=button.dataset.metric===metric;button.classList.toggle('selected',selected);button.setAttribute('aria-pressed',String(selected));});
 document.querySelectorAll('[data-days]').forEach(button=>{const selected=Number(button.dataset.days)===days;button.classList.toggle('active',selected);button.setAttribute('aria-pressed',String(selected));});
 const latest=rows.at(-1),first=rows[0];
 for(const[id,key]of [['weight','Weight_kg'],['fat','BodyFat_percent'],['bmi','BMI'],['muscle','MuscleMass_kg']]){
  $('card-'+id).textContent=latest?format(latest[key],key):'—';
  const difference=latest&&first&&Number.isFinite(latest[key])&&Number.isFinite(first[key])?latest[key]-first[key]:null;
  $('delta-'+id).textContent=difference===null?'暂无可用数值':`较首次 ${difference>0?'+':''}${difference.toFixed(METRICS[key][2])} ${METRICS[key][1]}`;
 }
 const shown=filtered();$('record-count').textContent=shown.length+' 条';
 const body=$('record-body');body.replaceChildren();
 for(const row of [...shown].reverse()){
  const tr=document.createElement('tr');for(const key of ['Date','Weight_kg','BodyFat_percent','BMI','MuscleMass_kg']){const td=document.createElement('td');td.textContent=key==='Date'?row.Date:format(row[key],key);tr.append(td);}body.append(tr);
 }
 if(!shown.length){const tr=document.createElement('tr'),td=document.createElement('td');td.colSpan=5;td.textContent='当前时间范围内暂无记录';tr.append(td);body.append(tr);}
 $('latest-date').textContent=latest?latest.Date+' · 北京时间':'暂无记录';
 const extras=$('extra-metrics');extras.replaceChildren();
 for(const key of ['MuscleRate_percent','SkeletalMuscleMass_kg','BodyWater_percent','ProteinRate_percent','BoneMass_kg','VisceralFat']){
  const box=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd'),unit=document.createElement('small');dt.textContent=METRICS[key][0];dd.textContent=latest?format(latest[key],key):'—';unit.textContent=METRICS[key][1];dd.append(unit);box.append(dt,dd);extras.append(box);
 }
 draw();
}
function draw(){
 const chart=$('chart'),wrap=$('plot-wrap'),width=wrap.clientWidth,height=wrap.clientHeight;
 chart.replaceChildren();chart.setAttribute('viewBox',`0 0 ${width} ${height}`);
 const periodName={day:'日',week:'周',month:'月'}[grouping];
 chart.setAttribute('aria-label',`${METRICS[metric][0]}按${periodName}均值与标准差，横轴为等间距日历周期`);
 $('tooltip').hidden=true;
 const data=BodyStats.aggregate(filtered(),metric,grouping),count=data.reduce((sum,row)=>sum+row.n,0);
 $('chart-name').textContent=METRICS[metric][0]+' · '+periodName+'均值';$('chart-unit').textContent=METRICS[metric][1]?' / '+METRICS[metric][1]:'';
 $('range-caption').textContent=data.length?`${data.length} 个${{day:'日期',week:'周',month:'月份'}[grouping]} · ${count} 次测量`:'暂无可用数值';
 $('empty').hidden=data.length>0;
 $('chart-detail').textContent='圆点为均值 · 误差棒为 ±1 样本标准差';
 if(!data.length)return;
 const left=58,right=23,top=25,bottom=50,plotWidth=width-left-right,plotHeight=height-top-bottom;
 const minimum=Math.min(...data.map(row=>row.low)),maximum=Math.max(...data.map(row=>row.high));
 const padding=Math.max((maximum-minimum)*.3,Math.abs(maximum)*.012,.2);
 const yMin=minimum-padding,yMax=maximum+padding;
 const first=data[0].index,last=data.at(-1).index,xMin=first-.35,xMax=last+.35;
 const x=index=>left+(index-xMin)/(xMax-xMin)*plotWidth;
 const y=value=>top+(yMax-value)/(yMax-yMin)*plotHeight;
 const decimals=Math.max(METRICS[metric][2],yMax-yMin<1?2:1);
 for(let index=0;index<5;index++){
  const value=yMin+(yMax-yMin)*index/4,position=y(value);
  chart.append(svg('line',{x1:left,y1:position,x2:width-right,y2:position,stroke:'var(--plot-grid)','stroke-width':1,'stroke-dasharray':'3 5'}));
  chart.append(svg('text',{x:left-11,y:position+4,fill:'var(--plot-text)','font-size':10,'text-anchor':'end'},value.toFixed(decimals)));
 }
 const maxTicks=width<500?4:Math.max(5,Math.floor(plotWidth/85));
 const step=Math.max(1,Math.ceil((last-first+1)/maxTicks));
 const ticks=[];for(let index=first;index<=last;index+=step)ticks.push(index);
 // All ticks sit on whole calendar periods; periods without data stay empty.
 for(const index of ticks){
  const px=x(index);
  chart.append(svg('line',{x1:px,y1:top,x2:px,y2:height-bottom,stroke:'var(--plot-grid)','stroke-width':1}));
  chart.append(svg('text',{x:px,y:height-27,fill:'var(--plot-text)','font-size':10,'text-anchor':'middle'},BodyStats.label(index,grouping)));
 }
 chart.append(svg('text',{x:left,y:12,fill:'var(--plot-text)','font-size':10},METRICS[metric][1]||'数值'));
 chart.append(svg('text',{x:width-right,y:height-5,fill:'var(--plot-text)','font-size':9,'text-anchor':'end'},grouping==='week'?'周起始日（周一） · 北京时间':grouping==='month'?'日历月 · 北京时间':'日期 · 北京时间'));
 const coordinates=data.map(row=>[x(row.index),y(row.mean)]);
 // Break the line at missing periods instead of implying an unobserved value.
 let segment=[];
 function drawSegment(){if(segment.length>1)chart.append(svg('path',{d:segment.map((p,i)=>(i?'L':'M')+p.join(',')).join(' '),fill:'none',stroke:'var(--plot-line)','stroke-width':2,'stroke-linejoin':'round','stroke-linecap':'round'}));segment=[];}
 data.forEach((row,index)=>{if(index&&row.index!==data[index-1].index+1)drawSegment();segment.push(coordinates[index]);});drawSegment();
 for(const row of data){
  if(row.sd===null)continue;
  const px=x(row.index),hi=y(row.high),lo=y(row.low);
  chart.append(svg('path',{d:`M${px},${hi} V${lo} M${px-5},${hi} H${px+5} M${px-5},${lo} H${px+5}`,fill:'none',stroke:'var(--plot-error)','stroke-width':1.6,'data-error-bar':'true'}));
 }
 const guide=svg('line',{x1:0,y1:top,x2:0,y2:height-bottom,stroke:'var(--plot-guide)','stroke-width':1,'stroke-dasharray':'3 4',visibility:'hidden'});chart.append(guide);
 const tip=$('tooltip');
 function describe(row){
  let title=row.date;
  if(grouping==='week'){const end=new Date(row.date+'T00:00:00Z');end.setUTCDate(end.getUTCDate()+6);title+=' — '+end.toISOString().slice(0,10);}
  if(grouping==='month')title=row.date.slice(0,7);
  return {title,mean:row.mean.toFixed(Math.max(METRICS[metric][2],2)),sd:row.sd===null?'仅 1 次测量，标准差不可估计':`标准差 ${row.sd.toFixed(Math.max(METRICS[metric][2],2))} ${METRICS[metric][1]}`};
 }
 function reveal(row,index){
  const px=coordinates[index][0],py=coordinates[index][1],detail=describe(row);
  guide.setAttribute('x1',px);guide.setAttribute('x2',px);guide.setAttribute('visibility','visible');tip.replaceChildren();
  const date=document.createElement('span'),value=document.createElement('strong'),extra=document.createElement('span');
  date.textContent=detail.title+' · '+row.n+' 次测量';value.textContent='均值 '+detail.mean+' '+METRICS[metric][1];extra.textContent=detail.sd;
  tip.append(date,value,extra);tip.hidden=false;tip.style.left=Math.min(Math.max(px+15,4),width-tip.offsetWidth-4)+'px';tip.style.top=Math.max(py-tip.offsetHeight-13,4)+'px';
  $('chart-detail').textContent=detail.title+' · n='+row.n+' · '+detail.sd;
 }
 data.forEach((row,index)=>{
  const detail=describe(row),circle=svg('circle',{cx:coordinates[index][0],cy:coordinates[index][1],r:5,fill:'var(--plot-line)',stroke:'var(--plot-point-edge)','stroke-width':2,tabindex:0,'data-period':row.date,'data-count':row.n,'aria-label':detail.title+'，'+row.n+'次测量，均值'+detail.mean+'，'+detail.sd});
  circle.addEventListener('focus',()=>reveal(row,index));circle.addEventListener('pointerenter',()=>reveal(row,index));circle.addEventListener('click',()=>reveal(row,index));chart.append(circle);
 });
 chart.onpointermove=event=>{const position=event.clientX-chart.getBoundingClientRect().left;let nearest=0;for(let index=1;index<data.length;index++)if(Math.abs(coordinates[index][0]-position)<Math.abs(coordinates[nearest][0]-position))nearest=index;reveal(data[nearest],nearest);};
 chart.onpointerleave=()=>{tip.hidden=true;guide.setAttribute('visibility','hidden');};
}

async function load(){
 if(busy)return;busy=true;$('refresh').disabled=true;
 try{const response=await fetch('/api/data',{cache:'no-store'});if(!response.ok)throw new Error();const payload=await response.json();rows=payload.rows;$('sync-time').textContent=payload.updated?'本地更新 '+new Date(payload.updated).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}):'尚未同步';$('error').hidden=true;render();}
 catch{$('error').hidden=false;$('error').textContent='暂时无法读取本地数据。请确认程序正在运行，再点击刷新。';}
 finally{busy=false;$('refresh').disabled=false;}
}
for(const[key,info]of Object.entries(METRICS)){const option=document.createElement('option');option.value=key;option.textContent=info[0]+(info[1]?' / '+info[1]:'');$('metric-select').append(option);}
$('metric-select').addEventListener('change',event=>choose(event.target.value));
document.querySelectorAll('[data-metric]').forEach(button=>button.addEventListener('click',()=>choose(button.dataset.metric)));
document.querySelectorAll('[data-days]').forEach(button=>button.addEventListener('click',()=>{days=Number(button.dataset.days);save();render();}));
$('group-select').addEventListener('change',event=>{grouping=event.target.value;save();draw();});
$('refresh').addEventListener('click',load);
$('sync').addEventListener('click',startSync);
new ResizeObserver(draw).observe($('plot-wrap'));
load();setInterval(load,60000);
function showSync(status){
 const running=status.State==='running';syncing=running;
 $('sync').disabled=running;$('sync').textContent=running?'同步中…':'↻ 一键同步';
 $('sync').setAttribute('aria-busy',String(running));
 $('sync-panel').dataset.state=status.State;
 $('stage-cloud').dataset.state=status.Cloud==='success'?'done':status.Cloud==='failed'?'failed':status.Cloud==='not_authorized'?'skipped':running&&status.Phase==='xiaomi'?'active':'';
 $('stage-github').dataset.state=status.GitHub==='success'?'done':status.GitHub==='failed'?'failed':running&&status.Phase==='github'?'active':'';
 let title='云端同步已就绪',detail='一键读取米家新测量，合并 GitHub 历史并上传新增记录。';
 if(running){title=status.Phase==='github'?'正在合并历史并同步 GitHub…':'正在读取米家云端…';detail='请稍候，已有记录保留原值，新日期与时间的记录自动追加。';}
 else if(status.State==='complete'){title='同步完成';detail=status.Cloud==='not_authorized'?'GitHub 历史已双向同步。本机未授权米家；需要采集新测量时，请运行「米家登录.cmd」。':'米家新测量与 GitHub 历史已合并，本地新增记录已上传。';}
 else if(status.State==='local_only'){title=status.Cloud==='success'?'本地归档完成':'尚未连接云端服务';detail='GitHub 数据同步尚未配置。运行 Setup-DataSync.ps1 连接自己的私人数据仓库；米家首次授权使用「米家登录.cmd」。';}
 else if(status.State==='partial'){title='GitHub 已同步，米家读取未完成';detail='已有历史已合并保存。请检查网络；若米家授权过期，运行「米家登录.cmd」后重试。';}
 else if(status.State==='error'){title='同步未完成 · 本地记录已保留';detail=status.Message||'请检查 GitHub 登录与网络连接，稍后重试。米家已读取的新记录仍保存在本地。';}
 $('sync-title').textContent=title;$('sync-detail').textContent=detail;
 if(lastSyncState==='running'&&!running)load();lastSyncState=status.State;
}
async function pollSync(){
 try{const response=await fetch('/api/sync',{cache:'no-store'});if(!response.ok)throw new Error();const status=await response.json();syncToken=status.token;showSync(status);}
 catch{if(syncing){$('sync-title').textContent='暂时无法获取同步状态';$('sync-detail').textContent='请保持程序运行，网络恢复后会继续更新状态。';}}
}
async function startSync(){
 if(syncing)return;
 $('sync').disabled=true;
 try{
  if(!syncToken){await pollSync();if(!syncToken)throw new Error();}
  const response=await fetch('/api/sync',{method:'POST',headers:{'X-Sync-Token':syncToken}});
  if(!response.ok&&response.status!==409)throw new Error();
  showSync(await response.json());
 }catch{showSync({State:'error',Message:'无法启动同步。请刷新页面后重试；已有记录保持不变。'});}
}
pollSync();setInterval(pollSync,2000);
