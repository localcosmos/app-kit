import{a as y,B as S,b as g,G as k,w as i,o as a,e as n,f as o,t as _,u as m,F as p,r as f,j as w}from"./entry.6324360c.js";const F=o("h2",null,"Traits",-1),B=["src"],L=["innerHTML"],H=y({__name:"[id]",async setup(P){let e,t;const x=S(),{id:h}=x.params,l=g(),r=k();[e,t]=i(()=>l.loadFeatures()),await e,t(),[e,t]=i(()=>r.loadTaxonProfile(l.taxonProfile.uuid)),await e,t(),[e,t]=i(()=>r.loadTaxon(h)),await e,t();const u=r.currentTaxon;return(v,C)=>(a(),n("div",null,[o("h1",null,_(m(u).taxonLatname),1),o("section",null,[F,(a(!0),n(p,null,f(m(u).traits,(c,d)=>(a(),n("div",{key:d},[o("h3",null,_(c.matrixFilter.name),1),(a(!0),n(p,null,f(c.values,(s,T)=>(a(),n("div",{key:`${d}_${T}`},[s.imageUrl?(a(),n("img",{key:0,src:`/${s.imageUrl}`},null,8,B)):w("",!0),o("div",{innerHTML:s.encodedSpace},null,8,L)]))),128))]))),128))])]))}});export{H as default};
