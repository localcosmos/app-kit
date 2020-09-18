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
		"taxonomic_restriction" : field_definition.taxonomic_restriction
	};

	var widget_attrs = field_definition["widget_attrs"];

	//enable bootstrap
	if (field_definition["definition"]["widget"] == "CheckboxInput"){
		widget_attrs["class"] = "form-check-input";
	}
	else {
		widget_attrs["class"] = "form-control";
	}

	for (var key in field_definition["definition"]){
		if (key == "widget"){
			field_kwargs["widget"] = forms[field_definition["definition"]["widget"]].create([], {"attrs":widget_attrs});
		}
		else {
			field_kwargs[key] = field_definition["definition"][key];
		}
	};

	var field = forms[field_definition["field_class"]](field_kwargs);

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
		"taxonomic_reference": form_definition.taxonomic_reference,
		"geographic_reference": form_definition.geographic_reference,
		"temporal_reference": form_definition.temporal_reference
	};

	return Form(forms.Form, observation_form_definition);
};

