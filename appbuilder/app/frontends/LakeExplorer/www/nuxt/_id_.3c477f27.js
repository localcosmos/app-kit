import{a as y,y as k,b as S,w as d,e,f as n,M as l,u as m,Q as _,R as p,o as t,N as g}from"./entry.c86999db.js";import{u as w}from"./taxon-profile.c666cd97.js";const v=n("h2",null,"Traits",-1),F=["src"],L=["innerHTML"],$=y({__name:"[id]",async setup(P){let a,o;const f=k(),{id:h}=f.params,x=S(),u=w();[a,o]=d(()=>x.loadFeatures()),await a,o(),[a,o]=d(()=>u.loadTaxonProfile(x.taxonProfile.uuid)),await a,o(),[a,o]=d(()=>u.loadTaxon(h)),await a,o();const i=u.currentTaxon;return(B,C)=>(t(),e("div",null,[n("h1",null,l(m(i).taxonLatname),1),n("section",null,[v,(t(!0),e(_,null,p(m(i).traits,(r,s)=>(t(),e("div",{key:s},[n("h3",null,l(r.matrixFilter.name),1),(t(!0),e(_,null,p(r.values,(c,T)=>(t(),e("div",{key:`${s}_${T}`},[c.imageUrl?(t(),e("img",{key:0,src:`/${c.imageUrl}`},null,8,F)):g("",!0),n("div",{innerHTML:c.encodedSpace},null,8,L)]))),128))]))),128)),(t(!0),e(_,null,p(m(i).texts,(r,s)=>(t(),e("div",{key:s},[n("h3",null,l(r.taxonTextType),1),n("p",null,l(r.shortText),1)]))),128))])]))}});export{$ as default};
