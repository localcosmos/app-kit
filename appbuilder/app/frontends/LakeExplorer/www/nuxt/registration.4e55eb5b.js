import{a as w,h as g,w as y,i as b,r as v,c as x,l as d,u as e,x as N,o as U,f as S,q as _,k as o}from"./entry.c86999db.js";import{_ as B,a as s}from"./FormWrapper.vue_vue_type_script_setup_true_lang.ff311a79.js";import{a as C}from"./initializers.1e869a60.js";const E=w({__name:"registration",async setup(k){let r,i;const m=g();[r,i]=y(()=>m.loadSettings()),await r,i();const u=b(),{registration:a,validation:p}=C({app_uuid:m.appUuid,client_id:m.generateUuid(),platform:device.platform}),n=v(!1),V=async()=>{n.value||(n.value=!0,await u.register(a.value),n.value=!1,u.isAuthenticated&&await N().push({name:"index"}))};return(f,l)=>(U(),x(B,{validation:e(p),onSubmit:V},{actions:d(()=>[S("input",{type:"submit",value:"Registrieren",class:_(["btn",e(n)?"loading":""])},null,2)]),default:d(()=>[o(s,{modelValue:e(a).username,"onUpdate:modelValue":l[0]||(l[0]=t=>e(a).username=t),name:"username",label:"Benutzername",type:"text"},null,8,["modelValue"]),o(s,{modelValue:e(a).email,"onUpdate:modelValue":l[1]||(l[1]=t=>e(a).email=t),name:"email",label:"Email",type:"email"},null,8,["modelValue"]),o(s,{modelValue:e(a).email2,"onUpdate:modelValue":l[2]||(l[2]=t=>e(a).email2=t),name:"email2",label:"Email wiederholen",type:"email"},null,8,["modelValue"]),o(s,{modelValue:e(a).firstName,"onUpdate:modelValue":l[3]||(l[3]=t=>e(a).firstName=t),name:"firstName",label:"Vorname",type:"text"},null,8,["modelValue"]),o(s,{modelValue:e(a).lastName,"onUpdate:modelValue":l[4]||(l[4]=t=>e(a).lastName=t),name:"lastName",label:"Nachname",type:"text"},null,8,["modelValue"]),o(s,{modelValue:e(a).password,"onUpdate:modelValue":l[5]||(l[5]=t=>e(a).password=t),name:"password",label:"Passwort",type:"password"},null,8,["modelValue"]),o(s,{modelValue:e(a).password2,"onUpdate:modelValue":l[6]||(l[6]=t=>e(a).password2=t),name:"password2",label:"Passwort wiederholen",type:"password"},null,8,["modelValue"])]),_:1},8,["validation"]))}});export{E as default};