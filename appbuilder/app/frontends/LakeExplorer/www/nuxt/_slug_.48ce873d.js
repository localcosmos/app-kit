import{a as i,o as r,e as l,f as c,t as S,m as g,p as T,q as N,u as m,F as f,r as _,c as d,s as C,h as w,v as y,x as $,y as F,z as k,j as h,A as I,B as D,C as G,D as V,w as B}from"./entry.6324360c.js";const M=["src","alt"],R={class:"py-2"},U=i({__name:"IdentificationKeyReference",props:{reference:null},setup(e){return(t,n)=>(r(),l("div",{class:g(["flex flex-col cursor-pointer border-2",{"border-transparent":e.reference.isVisible,"border-red-500":!e.reference.isVisible}]),onClick:n[0]||(n[0]=s=>t.$emit("select",e.reference))},[c("img",{class:"w-64 h-64",src:`/${e.reference.imageUrl}`,alt:e.reference.name},null,8,M),c("h3",R,S(e.reference.name),1)],2))}}),A=i({__name:"ColorFilterSpace",props:{space:null},setup(e){const t=e,n=T(()=>{const a=t.space.encodedSpace;return`rgba(${a[0]}, ${a[1]}, ${a[2]}, ${a[3]})`}),s=()=>{t.space.isSelected?t.space.deselect():t.space.select()};return(a,o)=>(r(),l("div",{class:g([e.space.isSelected?"border-2 border-purple-500":"border-2 border-black","flex flex-col"]),onClick:s},[c("div",{class:"w-32 h-32",style:N({"background-color":m(n)})},null,4)],2))}}),O={class:"flex gap-2 cursor-pointer"},j=i({__name:"ColorFilter",props:{filter:null},setup(e){return(t,n)=>(r(),l("div",null,[c("div",O,[(r(!0),l(f,null,_(e.filter.space,s=>(r(),d(A,{key:s.spaceIdentifier,space:s},null,8,["space"]))),128))])]))}}),z=["alt","src"],K=i({__name:"DescriptiveTextAndImagesFilterSpace",props:{space:null},setup(e){const t=e,n=T(()=>({"border-purple-500":t.space.isSelected,"border-red-500":!t.space.isPossible,"border-transparent":t.space.isPossible&&!t.space.isSelected})),s=()=>{t.space.isSelected?t.space.deselect():t.space.select()};return(a,o)=>{const p=C("GlossaryTranslatable");return r(),l("div",{class:"p-4",onClick:s},[c("div",{class:g(["flex flex-col border-2",m(n)])},[c("img",{class:"w-64 h-64",alt:e.space.matrixFilter.name,src:`/${e.space.imageUrl}`},null,8,z),w(p,{value:e.space.encodedSpace},null,8,["value"])],2)])}}}),P={class:"flex"},q=i({__name:"DescriptiveTextAndImagesFilter",props:{filter:null},setup(e){return(t,n)=>(r(),l("div",P,[(r(!0),l(f,null,_(e.filter.space,s=>(r(),d(K,{key:s.spaceIdentifier,space:s},null,8,["space"]))),128))]))}}),E={key:0},L=["min"],H=["max"],J=i({__name:"RangeFilter",props:{filter:null},setup(e){const t=e,n=y(t.filter.encodedSpace[0]),s=y(t.filter.encodedSpace[0]),a=()=>Math.max(n.value,t.filter.encodedSpace[0]),o=()=>Math.min(s.value,t.filter.encodedSpace[1]),p=()=>{t.filter.selectSpace({min:n.value,max:s.value})};return $(()=>n,p),$(()=>s,p),(b,u)=>(r(),l("div",null,[e.filter.encodedSpace?(r(),l("div",E,[F(c("input",{"onUpdate:modelValue":u[0]||(u[0]=x=>n.value=x),type:"range",min:e.filter.encodedSpace[0],max:o,class:"range"},null,8,L),[[k,n.value,void 0,{number:!0}]]),F(c("input",{"onUpdate:modelValue":u[1]||(u[1]=x=>s.value=x),type:"range",min:a,max:e.filter.encodedSpace[1],class:"range"},null,8,H),[[k,s.value,void 0,{number:!0}]])])):h("",!0)]))}}),Q=i({__name:"NumberFilterSpace",props:{space:null},setup(e){const t=e,n=()=>{t.space.isSelected?t.space.deselect():t.space.select()};return(s,a)=>(r(),l("div",{class:g([e.space.isSelected?"border-2 border-purple-500":"border-2 border-black","w-32 h-32 flex items-center justify-center"]),onClick:n},[c("span",null,S(e.space.encodedSpace),1)],2))}}),W={class:"flex gap-2 cursor-pointer"},X=i({__name:"NumberFilter",props:{filter:null},setup(e){return(t,n)=>(r(),l("div",null,[c("div",W,[(r(!0),l(f,null,_(e.filter.space,s=>(r(),d(Q,{key:s.spaceIdentifier,space:s},null,8,["space"]))),128))])]))}}),Y=i({__name:"TextOnlyFilterSpace",props:{space:null},setup(e){const t=e,n=()=>{t.space.isSelected?t.space.deselect():t.space.select()};return(s,a)=>{const o=C("GlossaryTranslatable");return r(),l("div",{class:g([e.space.isSelected?"border-2 border-purple-500":"border-2 border-black","p-4"]),onClick:n},[w(o,{value:e.space.encodedSpace},null,8,["value"])],2)}}}),Z={class:"flex gap-2 cursor-pointer"},ee=i({__name:"TextOnlyFilter",props:{filter:null},setup(e){return(t,n)=>(r(),l("div",null,[c("div",Z,[(r(!0),l(f,null,_(e.filter.space,s=>(r(),d(Y,{key:s.spaceIdentifier,space:s},null,8,["space"]))),128))])]))}}),te=i({__name:"TaxonFilter",props:{filter:null},setup(e){return(t,n)=>(r(),l("div",null," TaxonFilter Filter! "))}}),se={class:"py-4"},ne=i({__name:"MatrixFilter",props:{filter:null},setup(e){const t=n=>{switch(n){case"ColorFilter":return j;case"DescriptiveTextAndImagesFilter":return q;case"RangeFilter":return J;case"NumberFilter":return X;case"TextOnlyFilter":return ee;case"TaxonFilter":return te}};return(n,s)=>(r(),l("div",se,[c("h2",null,S(e.filter.name),1),(r(),d(I(t(e.filter.type)),{filter:e.filter},null,8,["filter"]))]))}}),re={class:"columns-3 lg:columns-4"},le=i({__name:"IdentificationKey",props:{node:null},setup(e){const n=Object.values(e.node.matrixFilters).sort((s,a)=>s.position>a.position?1:-1);return(s,a)=>(r(),l("div",null,[c("h2",null,S(e.node.name),1),c("div",re,[(r(!0),l(f,null,_(e.node.children,o=>(r(),d(U,{key:o.uuid,reference:o,onSelect:p=>s.$emit("select",o)},null,8,["reference","onSelect"]))),128))]),c("div",null,[(r(!0),l(f,null,_(m(n),o=>(r(),d(ne,{key:o.uuid,filter:o},null,8,["filter"]))),128))])]))}}),ae={key:0,class:"container mx-auto px-4"},ie=i({__name:"[slug]",async setup(e){let t,n;const s=D(),a=G(),{natureguideid:o,slug:p}=s.params,b=V();[t,n]=B(()=>b.loadNatureGuide(o)),await t,n(),b.loadNodeBySlug(`${p}`);const u=b.currentNode,x=async v=>{switch(v.nodeType){case"node":return await a.push({name:"nature-guide-natureguideid-slug",params:{natureguideid:s.params.natureguideid,slug:v.slug}});case"result":return await a.push({name:"taxon-profile-taxon-id",params:{taxonid:v.taxon.taxonSource,id:v.taxon.nameUuid}})}};return(v,ce)=>m(u)?(r(),l("div",ae,[m(u)?(r(),d(le,{key:0,node:m(u),class:"mt-4",onSelect:x},null,8,["node"])):h("",!0)])):h("",!0)}});export{ie as default};
