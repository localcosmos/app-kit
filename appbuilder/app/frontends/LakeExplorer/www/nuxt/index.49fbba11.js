import{a as l,b as _,o as a,e as n,f as m,h as s,w as u,i,F as f,r as x,j as p,k as d,t as c}from"./entry.e4685ebd.js";const k={async setup(){const e=l();return await e.loadFeatures(),{taxonProfile:e.taxonProfile,natureGuides:e.natureGuides}}},g={key:0};function y(e,h,F,t,G,N){const r=p;return a(),n("div",null,[m("ul",null,[t.taxonProfile?(a(),n("li",g,[s(r,{to:{name:"taxon-profile"}},{default:u(()=>[d(c(t.taxonProfile.name),1)]),_:1})])):i("",!0),t.natureGuides?(a(!0),n(f,{key:1},x(t.natureGuides,o=>(a(),n("li",{key:o.uuid},[s(r,{to:{name:"nature-guide-natureguideid",params:{natureguideid:o.uuid}}},{default:u(()=>[d(c(o.name),1)]),_:2},1032,["to"])]))),128)):i("",!0)])])}const V=_(k,[["render",y]]);export{V as default};