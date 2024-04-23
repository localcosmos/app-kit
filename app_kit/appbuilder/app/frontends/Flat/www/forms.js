var LoginForm = Form(forms.Form, {
	"fields" : {
		"username" : forms.CharField({"max_length": 60, "widget":forms.TextInput.create([],{"attrs":{"autocorrect" : "off", "autocapitalize":"none", "class" : "form-control"}}) }),
		"password" : forms.CharField({"widget" : forms.PasswordInput.create([], {"attrs":{"class":"form-control"}}) })
	}
});


/*
* receive form json and return a form class
*/
function createFieldFromJSON(field_definition){
	var field_kwargs = {
		"uuid" : field_definition.uuid,
		"role" : field_definition.role,
		"taxonomic_restriction" : field_definition.taxonomicRestrictions
	};

	var widgetAttrs = field_definition["widgetAttrs"];

	//enable bootstrap
	if (field_definition["definition"]["widget"] == "CheckboxInput"){
		widgetAttrs["class"] = "form-check-input";
	}
	else {
		widgetAttrs["class"] = "form-control";
	}

	for (var key in field_definition["definition"]){
		if (key == "widget"){
			field_kwargs["widget"] = forms[field_definition["definition"]["widget"]].create([], {"attrs":widgetAttrs});
		}
		else {
			field_kwargs[key] = field_definition["definition"][key];
		}
	};

	var field = forms[field_definition["fieldClass"]](field_kwargs);

	return field;	

};

function createObservationFormFromJSON(form_definition){

	var _fields = {};

	for (var f=0; f<form_definition.fields.length; f++){
		var field_definition = form_definition.fields[f];
		
		var field = createFieldFromJSON(field_definition);

		_fields[field_definition["uuid"]] = field;
	}

	var observation_form_definition = {
		"fields" : _fields,
		"taxonomicReference": form_definition.taxonomicReference,
		"geographicReference": form_definition.geographicReference,
		"temporalReference": form_definition.temporalReference
	};

	return Form(forms.Form, observation_form_definition);
};

