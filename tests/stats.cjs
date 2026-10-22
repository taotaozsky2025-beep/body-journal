'use strict';
// Synthetic dates and values; no real health records.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={};vm.createContext(context);
vm.runInContext(fs.readFileSync(require('path').join(__dirname,'../dashboard-stats.js'),'utf8'),context);
const stats=context.BodyStats;
const rows=[{Date:'2050-01-01 08:00:00',value:10},{Date:'2050-01-01 09:00:00',value:14},{Date:'2050-01-03 08:00:00',value:20}];
const days=stats.aggregate(rows,'value','day');
assert.equal(days.length,2);assert.equal(days[0].mean,12);assert.ok(Math.abs(days[0].sd-Math.sqrt(8))<1e-10);
assert.equal(days[1].sd,null);assert.equal(days[1].index-days[0].index,2);
assert.equal(stats.aggregate(rows,'value','month').length,1);
console.log('PASS: calendar spacing, sample SD, singleton, month aggregation');
