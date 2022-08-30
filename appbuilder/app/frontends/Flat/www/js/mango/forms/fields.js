"use strict";
/*** FormField ***/
// initializes a form field: complete the definition in appmodels, except id and name
// does not create a new object, but manipulates the definition in appforms, or the definition passed from modelform
// returns 
var FormField = {

	widget : forms.TextInput,  // Default widget to use when rendering this type of Field.
    hidden_widget : forms.HiddenInput,  // Default widget to use when rendering this as "hidden".
    validators : [],  // Default set of validators
	empty_values : [null, ''],
	error_messages : {
		"required": "This field is required.",
	},
	//
	required : true,
	label : null,
	initial : null,
	helpText : '',
	show_hidden_initial : false,
	localize : false,
	disabled : false,
	label_suffix : null,

	//
	value : '',

	validate : function(self, value){
        if (self.empty_values.indexOf(value) >=0 && self.required){
            throw new ValidationError(_(self.error_messages["required"]));
		}
	},

    run_validators : function(self, value){
        if (self.empty_values.indexOf(value) >=0){
            return;
		}
		
        var errors = [];

        for (var v=0; v<self.validators.length; v++){

			var validator = self.validators[v];

            try {
                validator(value);
			}
            catch(e) {
				if (e.hasOwnProperty("code") && self.error_messages.hasOwnProperty(e.code)){
					e.message = self.error_messages[e.code];
					errors.push(e.error_list);
				}
			}
		}
        if (errors.length){
            throw new ValidationError(errors);
		}		
	},

    clean : function(self, value){
        /*
        Validate the given value and return its "cleaned" value as an
        appropriate Python object. Raise ValidationError for any errors.
        */
        var value = self.to_javascript(self, value);
        self.validate(self, value);
        self.run_validators(self, value);
		return value;
	},

	prepare_value : function(self, value){
		/* prepare the value for html */
		return value;
	},

	to_javascript : function(self, value){
		if (typeof value == "string"){
			value = value.trim();
		}
		return value;
	},

	bound_data : function(self, data, initial){
        /*"""
        Return the value that should be shown for this field on render of a
        bound form, given the submitted POST data for the field and the initial
        data, if any.
        For most fields, this will simply be data; FileFields need to handle it
        a bit differently.
        """*/
        if (self.disabled == true){
            return initial;
		}
		return data;
	},

	get_bound_field : function(self, form, field_name){
        /*"""
        Return a BoundField instance that will be used when accessing the form
        field in a template.
        """*/
		return BoundField.create(form, self, field_name);
	},

	has_changed : function(self, initial, data){
        /*"""Return True if data differs from initial."""*/
        //# Always return False if the field is disabled since self.bound_data
        //# always uses the initial value in this case.
        if (self.disabled == true){
            return false;
		}
        try {
            var data = self.to_javascript(data);
            if (self.hasOwnProperty('_coerce') == true){
                return self._coerce(data) != self._coerce(initial);
			}
		}
        catch(e){
			if (e instanceof ValidationError) {
				return true;
			} 
			else {
				throw e;
			}
		}
        //# For purposes of seeing whether something has changed, None is
        //# the same as an empty string, if the data or initial value we get
        //# is None, replace it with ''.
		if (initial == null){
			var initial_value = '';
		}
		else {
			var initial_value = initial_value;
		}
        
		if (data == null){
			var data_value = '';
		}
		else {
			var data_value = data;
		}
        
		return initial_value != data_value;
	}
	
};

forms.CharField = function(kwargs){
	var field = derive(FormField, {
		"fieldClass" : "CharField"
	}, kwargs);

	return field;
};

forms.BooleanField = function(kwargs){
	var field = derive(FormField, {
		"fieldClass" : "BooleanField",
		"widget" : forms.CheckboxInput
	}, kwargs);

	return field;
};

forms.ChoiceField = function(kwargs){
	var field = derive(FormField, {
		"fieldClass" : "ChoiceField",
		"widget" : forms.Select,
		"choices" : []
	}, kwargs);

	return field;
};

forms.MultipleChoiceField = function(kwargs){
	var field = derive(FormField, {
		"fieldClass" : "MultipleChoiceField",
		"widget" : forms.SelectMultiple,
		"prepare_value" : function(self, value){
			/* prepare the value for html */
			if (value instanceof Array == false && value != null && value.length){
				value = [value];
			}
			return value;
		}
	}, kwargs);

	return field;
};


forms.DecimalField = function(kwargs){
	var field = derive(FormField, {
		"fieldClass" : "DecimalField",
		"widget" : forms.NumberInput,
		to_javascript : function(self, value){
			if (typeof value == "string" && value.length >0){
				value = parseFloat(value);
			}
			if (typeof value == "string" && value.length === 0){
				value = null;
			}
			return value;
		}
	}, kwargs);

	//field.validators.push("DecimalValidator");
	return field;
};

forms.FloatField = function(kwargs){
	var field = derive(FormField, {
		"fieldClass" : "FloatField",
		"widget" : forms.NumberInput,
		to_javascript : function(self, value){
			if (typeof value == "string" && value.length >0){
				value = parseFloat(value);
			}
			if (typeof value == "string" && value.length === 0){
				value = null;
			}
			return value;
		}
	}, kwargs);

	return field;
};

forms.IntegerField = function(kwargs){
	var field = derive(FormField, {
		"fieldClass" : "IntegerField",
		"widget" : forms.NumberInput,
		to_javascript : function(self, value){
			if (typeof value == "string" && value.length >0){
				value = parseInt(value);
			}
			if (typeof value == "string" && value.length === 0){
				value = null;
			}
			return value;
		}
	}, kwargs);

	return field;

};

forms.DateTimeField = function(kwargs){
	var field = derive(FormField, {
		"fieldClass" : "DateTimeField",
		"widget" : forms.NumberInput
	}, kwargs);

	return field;
};


/* accuracy can be stored in properties
* {
           "type": "Feature",
           "geometry": {
               "type": "Point",
               "coordinates": [102.0, 0.5],
			   "crs":{"type":"name","properties":{"name":"EPSG:3857"}}
           },
           "properties": {
               "prop0": "value0"
           }
       }
*
*/


forms.PasswordField = function(kwargs){

	var field = derive(FormField, {
		"fieldClass" : "PasswordField"
	}, kwargs);

	return field;
};


forms.FileField = function(kwargs){
	var field = derive(FormField, {
		"fieldClass" : "FileField",
		"widget" : forms.FileInput
	}, kwargs);

	return field
};

forms.ImageField = function(kwargs){
	var field = derive(FormField, {
		"fieldClass" : "ImageField",
		"widget" : forms.FileInput
	}, kwargs);

	return field
};


/*"""
Aggregate the logic of multiple Fields.
Its clean() method takes a "decompressed" list of values, which are then
cleaned into a single value according to self.fields. Each value in
this list is cleaned by the corresponding field -- the first value is
cleaned by the first field, the second value is cleaned by the second
field, etc. Once all fields are cleaned, the list of clean values is
"compressed" into a single value.
Subclasses should not have to implement clean(). Instead, they must
implement compress(), which takes a list of valid values and returns a
"compressed" version of those values -- a single value.
You'll probably want to use this with MultiWidget.
"""*/
var MultiValueField = function(kwargs){

	var field = derive(FormField, {

	error_messages : {
        "invalid" : "Enter a list of values.",
        "incomplete" : "Enter a complete value.",
		"required": "This field is required.",
    },

	fields : [],

	require_all_fields : true,

    validate : function(self, value){
        
	},

    clean : function(self, value){
		/*"""
		Validate every value in the given list. A value is validated against
		the corresponding Field in self.fields.
		For example, if this MultiValueField was instantiated with
		fields=(DateField(), TimeField()), clean() would call
		DateField.clean(value[0]) and TimeField.clean(value[1]).
		"""*/
		var clean_data = [];
		var errors = [];

		if (self.empty_values.indexOf(value) >= 0 || value instanceof Array){

			var value_ = [];

			if (value instanceof Array){
				
				for (var v=0; v<value.length; v++){
					var subvalue = value[v];
					if (self.empty_values.indexOf( subvalue ) == -1 ){
						value_.push(subvalue);
					}
				}
			}
			
			if (self.empty_values.indexOf(value) >= 0 || value_.length == 0){
				if (self.required == true){
					throw new ValidationError(_(self.error_messages["required"]));
				}
				else {
					return self.compress(self, []);
				}
			}
			
		}
		else {
			throw new ValidationError(_(self.error_messages["invalid"]));
		}

		for (var i=0; i<self.fields.length; i++){
			var field = self.fields[i];

			try {
				var field_value = value[i];
			}
			catch(e){
				var field_value = null;
			}

			if (self.empty_values.indexOf(field_value) >=0){

				if (self.require_all_fields == true){
					//# Raise a 'required' error if the MultiValueField is
                    //# required and any field is empty.
					if (self.required == true){
						throw new ValidationError(_(self.error_messages["required"]));
					}
				}				
				else if (field.required == true){
					//# Otherwise, add an 'incomplete' error to the list of
                    //# collected errors and skip field cleaning, if a required
                    //# field is empty.
					errors.push(_(self.error_messages["incomplete"]));
					continue;
				}
			}

			try {
				clean_data.push(field.clean(field, field_value));
			}
			catch(e){
				if (e instanceof ValidationError) {
					//# Collect all validation errors in a single list, which we'll
                	//# raise at the end of clean(), rather than raising a single
                	//# exception for the first error we encounter. Skip duplicates.
					for (var m=0; m<e.error_list.length; m++){
						errors.push(e.error_list[m]);
					}

				}
				else {
					throw e;
				}
			}

		}

		if (errors.length > 0){
			throw new ValidationError(errors);
		}
		
		var out = self.compress(self, clean_data);
		self.validate(self, out);
		self.run_validators(self, out);
		return out;
	},

    compress : function(self, data_list){
        /*"""
        Return a single value for the given list of values. The values can be
        assumed to be valid.
        For example, if this MultiValueField was instantiated with
        fields=(DateField(), TimeField()), this might return a datetime
        object created by combining the date and time in data_list.
        """*/
        throw new Error("Subclasses of MultiValueField must implement a compress method.");
	},

    has_changed : function(self, initial, data){
        if (self.disabled == true){
            return false;
		}
        if (initial == null || (initial instanceof Array && initial.length == 0)){
			initial = [];
			for (var x=0; x<data.length; x++){
				initial_.push('');
			}
		}
        else {
            if (initial instanceof Array == false){
                initial = self.widget.decompress(self.widget, initial);
			}
		}
		
		for (var f=0; f<self.fields.length; f++){
			var field = self.fields[f];
			var initial_ = initial[f] || null;
			var data_ = data[f] || null;

			try {
				initial_ = field.to_javascript(initial_);
			}
			catch(e){
				if (e instanceof ValidationError) {
					return true;
				}
				else {
					throw e;
				}
			}

			if (field.has_changed(initial_, data_) == true){
				return true
			}
		}

		return false;

	}

	}, kwargs);

	for (var f=0; f<field.fields.length; f++){
		var subfield = field.fields[f];

		if (subfield.require_all_fields){
			//# Set 'required' to False on the individual fields, because the
			//# required validation will be handled by MultiValueField, not
			//# by those individual fields.
			subfield.required = false;
		}
	}

	return field;

};

