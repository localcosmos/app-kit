import{a7 as n,i as s,a8 as u,a9 as i}from"./entry.c86999db.js";const c=n(async(o,r)=>{let e,t;const a=s();if([e,t]=u(()=>a.loadLocalLogin()),await e,t(),!a.isAuthenticated)return i({name:"login",query:{next:o.fullPath}})});export{c as default};