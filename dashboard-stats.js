(function(root){
 'use strict';
 const DAY=86400000;
 function periodIndex(date,mode){
  const [year,month,day]=date.slice(0,10).split('-').map(Number);
  const stamp=Date.UTC(year,month-1,day);
  if(mode==='month')return year*12+month-1;
  if(mode==='week')return Math.floor((stamp-((new Date(stamp).getUTCDay()+6)%7)*DAY)/DAY/7);
  return Math.floor(stamp/DAY);
 }
 function periodDate(index,mode){
  if(mode==='month')return new Date(Date.UTC(Math.floor(index/12),index%12,1)).toISOString().slice(0,10);
  // Week indices encode the Monday epoch offset (1970-01-05).
  return new Date((mode==='week'?index*7+4:index)*DAY).toISOString().slice(0,10);
 }
 function label(index,mode){const date=periodDate(index,mode);return mode==='month'?date.slice(0,7):date.slice(5);}
 function aggregate(rows,key,mode){
  const groups=new Map();
  for(const row of rows){
   if(!Number.isFinite(row[key]))continue;
   const index=periodIndex(row.Date,mode);
   if(!groups.has(index))groups.set(index,[]);
   groups.get(index).push(row[key]);
  }
  return [...groups].sort((a,b)=>a[0]-b[0]).map(([index,values])=>{
   const n=values.length,mean=values.reduce((sum,value)=>sum+value,0)/n;
   const sd=n>1?Math.sqrt(values.reduce((sum,value)=>sum+(value-mean)**2,0)/(n-1)):null;
   return {index,date:periodDate(index,mode),n,mean,sd,low:mean-(sd??0),high:mean+(sd??0)};
  });
 }
 const api={periodIndex,periodDate,label,aggregate};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 else root.BodyStats=api;
})(typeof globalThis!=='undefined'?globalThis:this);
