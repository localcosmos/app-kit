import{a as b,A as C,m as B,b as H,w as N,p as A,o as t,e as s,s as f,x as v,f as e,J as k,u as a,t as x,j as g,h as i,i as c,l as h,k as L}from"./entry.1f123120.js";const D={class:"drawer"},M={class:"drawer-content"},U={class:"container mx-auto"},Z={for:"main-drawer",class:"drawer-button btn btn-circle swap swap-rotate"},$=e("svg",{class:"swap-off fill-current",xmlns:"http://www.w3.org/2000/svg",width:"32",height:"32",viewBox:"0 0 512 512"},[e("path",{d:"M64,384H448V341.33H64Zm0-106.67H448V234.67H64ZM64,128v42.67H448V128Z"})],-1),E=e("svg",{class:"swap-on fill-current",xmlns:"http://www.w3.org/2000/svg",width:"32",height:"32",viewBox:"0 0 512 512"},[e("polygon",{points:"400 145.49 366.51 112 256 222.51 145.49 112 112 145.49 222.51 256 112 366.51 145.49 400 256 289.49 366.51 400 400 366.51 289.49 256 400 145.49"})],-1),F={class:"drawer-side"},P=e("label",{for:"main-drawer",class:"drawer-overlay"},null,-1),j={class:"p-4 overflow-y-auto w-80 bg-base-100 text-base-content flex flex-col"},J={key:0},R={class:"mx-4"},T={class:"menu grow"},W=h(" Startseite "),q={key:0},z={class:"menu"},G={key:0},I={key:1},K=h(" Login "),O=b({__name:"NavigationDrawer",async setup(y){let n,d;const w=C(),o=B(!1),m=H();[n,d]=N(()=>m.loadFeatures()),await n,d();const p=m.taxonProfile,l=A(),V=async()=>{await l.logout(),await w.push({name:"index"})};return w.beforeEach(()=>{o.value=!1}),(S,r)=>{const u=L;return t(),s("div",D,[f(e("input",{id:"main-drawer","onUpdate:modelValue":r[0]||(r[0]=_=>o.value=_),type:"checkbox",class:"drawer-toggle"},null,512),[[v,o.value]]),e("div",M,[e("div",U,[e("label",Z,[f(e("input",{"onUpdate:modelValue":r[1]||(r[1]=_=>o.value=_),type:"checkbox"},null,512),[[v,o.value]]),$,E]),k(S.$slots,"default")])]),e("div",F,[P,e("div",j,[a(l).isUserLoaded?(t(),s("div",J,[e("div",R," Wilkommen "+x(a(l).user.username)+"! ",1)])):g("",!0),e("ul",T,[e("li",null,[i(u,{to:{name:"index"}},{default:c(()=>[W]),_:1})]),a(p)?(t(),s("li",q,[i(u,{to:{name:"taxon-profile"}},{default:c(()=>[h(x(a(p).name),1)]),_:1})])):g("",!0)]),e("ul",z,[a(l).isAuthenticated?(t(),s("li",G,[e("a",{onClick:V}," Logout ")])):(t(),s("li",I,[i(u,{to:{name:"login"}},{default:c(()=>[K]),_:1})]))])])])])}}}),X=b({__name:"default",setup(y){return(n,d)=>(t(),s("main",null,[i(O,null,{default:c(()=>[k(n.$slots,"default")]),_:3})]))}});export{X as default};
