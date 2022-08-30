"use strict";
/*** FORMS ***/

/* "derive" function adding fields to modelform, if it is a modelform */
function Form(prototype, extension, override) {

	var object = derive(prototype, extension, override);

	// if it is a modelform, add fields
	if (prototype.form_type == "ModelForm"){
		object.fields = fields_for_model(object.Meta.model, object.Meta);
	}

	return object;
};

var forms = {};

function ValidationError(error_list) {
    var temp = Error.apply(this, arguments);
    temp.name = this.name = 'ValidationError';
    this.message = temp.message;

    if (Object.defineProperty) {
        // getter for more optimizy goodness
        /*this.stack = */Object.defineProperty(this, 'stack', { 
            get: function() {
                return temp.stack
            },
            configurable: true // so you can change it if you want
        })
    } 
	else {
        this.stack = temp.stack
    }

	if ( typeof error_list === 'string' ) {
		error_list = [ error_list ];
	}
	
	this.error_list = error_list || [];
}
//inherit prototype using ECMAScript 5 (IE 9+)
ValidationError.prototype = Object.create(Error.prototype, {
    constructor: {
        value: ValidationError,
        writable: true,
        configurable: true
    }
});


forms.ValidationError = ValidationError;


var ErrorList = {
	create : function(initlist){
		var self = Object.create(this);
		self.list = initlist || [];
		return self;
	}
};

var BaseForm = {

	prefix : null,
	label_suffix : ':',
	default_renderer : null,
	is_bound : false,
	_errors : null, //# Stores the errors after clean() has been called.

	empty_permitted : false,

	fields : {}, // field_name : field
	Meta : {},

	// called from subclasses, the subclass has to be passed as the first argument
	// _create receives self, create() does not
	_create : function(self, kwargs){

		// if only one dict is passed
		var kwargs = kwargs || {};

		self.initial = kwargs.initial || {};
		self.data = kwargs.data || {};

		self.bound_fields = {};


		if (Object.keys(self.data).length > 0){
			self.is_bound = true;
		}

		// a list for boundfields
		self.fieldlist = [];

		// create boundfields and add to self.fieldlist
		for (var field_name in self.fields){
			var field = self.fields[field_name];
			var bound_field = field.get_bound_field(field, self, field_name);
			self.fieldlist.push(bound_field);
			self.bound_fields[field_name] = bound_field;
		}

	},

	errors : function(self){
		//"""Return an ErrorDict for the data provided for the form."""
		if (self._errors == null){
			self.full_clean(self);
		}
		return self._errors;
	},

	is_valid : function(self){
        //"""Return True if the form has no errors, or False otherwise."""
		var errors = self.errors(self);
		
		if (self.is_bound == true && Object.keys(self._errors).length == 0){
			return true;
		}
		return false;
	},

	add_prefix : function(self, field_name){
        /*"""
        Return the field name with a prefix appended, if this Form has a
        prefix set.
        Subclasses may wish to override.
        """*/
		if (self.prefix == null){
			return field_name;
		}
		else {
			return self.prefix + '-' + field_name;
		}
	},

	add_initial_prefix : function(self, field_name){
		//"""Add a 'initial' prefix for checking dynamic initial values."""
		return 'initial-' + self.add_prefix(field_name);
	},

	auto_id : function(self){
		return 'id_%s';
	},


	add_error : function(self, field, error){
        /*"""
        Update the content of `self._errors`.
        The `field` argument is the name of the field to which the errors
        should be added. If it's None, treat the errors as NON_FIELD_ERRORS.
        The `error` argument can be a single error, a list of errors, or a
        dictionary that maps field names to lists of errors. An "error" can be
        either a simple string or an instance of ValidationError with its
        message attribute set and a "list or dictionary" can be an actual
        `list` or `dict` or an instance of ValidationError with its
        `error_list` or `error_dict` attribute set.
        If `error` is a dictionary, the `field` argument *must* be None and
        errors will be added to the fields that correspond to the keys of the
        dictionary.
        """*/
        if (!(error instanceof ValidationError)){
            //# Normalize to ValidationError and let its constructor
            //# do the hard work of making sense of the input.
            error = new ValidationError(error);
		}

		if (self._errors == null){
			self._errors = {};
		}
		
		if (field === null){
			// it is a NON_FIELD_ERROR 
		}
		else {

			if (!(self._errors.hasOwnProperty(field))){
				self._errors[field] = [];
			}
			
			for (var e=0; e<error.error_list.length; e++){
				var _error = error.error_list[e];
				self._errors[field].push(_error);
			}
			
			if (self.cleaned_data.hasOwnProperty(field)){
				delete self.cleaned_data[field];
			}
		}	
		/*
        if hasattr(error, 'error_dict'):
            if field is not None:
                raise TypeError(
                    "The argument `field` must be `None` when the `error` "
                    "argument contains errors for multiple fields."
                )
            else:
                error = error.error_dict
        else:
            error = {field or NON_FIELD_ERRORS: error.error_list}
		*/

		/*
        for field, error_list in error.items():
            if field not in self.errors:
                if field != NON_FIELD_ERRORS and field not in self.fields:
                    raise ValueError(
                        "'%s' has no field named '%s'." % (self.__class__.__name__, field))
                if field == NON_FIELD_ERRORS:
                    self._errors[field] = self.error_class(error_class='nonfield')
                else:
                    self._errors[field] = self.error_class()
            self._errors[field].extend(error_list)
            if field in self.cleaned_data:
				del self.cleaned_data[field]*/
	},

	full_clean : function(self){
        /*"""
        Clean all of self.data and populate self._errors and self.cleaned_data.
        """*/

        self._errors = {};

        if (self.is_bound == false){  //# Stop further processing.
            return;
		}

        self.cleaned_data = {};
        //# If the form is permitted to be empty, and none of the form data has
        //# changed from the initial data, short circuit any validation.
        if (self.empty_permitted == true && self.has_changed(self).length == 0){
            return;
		}

        self._clean_fields(self);
        self._clean_form(self);
		self._post_clean(self);
	},

	_clean_fields : function(self){

		for (var name in self.fields){
			var field = self.fields[name];
	
			//# value_from_datadict() gets the data from the data dictionaries.
			//# Each widget type knows how to retrieve its own data, because some
			//# widgets split data over several HTML fields.
			if (field.disabled == true){
				var value = self.get_initial_for_field(self, field, name);
			}
			else {
				var value = field.widget.value_from_datadict(field.widget, self.data, self.files, self.add_prefix(self, name));
			}

			try {
				if (field.fieldClass == 'FileField'){
					var initial = self.get_initial_for_field(self, field, name);
					value = field.clean(field, value, initial);
				}
				else {
					value = field.clean(field, value);
				}

				self.cleaned_data[name] = value;

				if (self.hasOwnProperty('clean_' + name) == true){
					value = self['clean_' + name](self);
					self.cleaned_data[name] = value;
				}
			}
			catch (e) {
				if (e instanceof ValidationError) {
					// name is the field name
					self.add_error(self, name, e);
				}
				else {
					throw e;
				}
			}
		}
	},

    _clean_form : function(self){
		var cleaned_data = null;

        try {
			cleaned_data = self.clean(self);
		}
		catch (e) {
			if (e instanceof ValidationError) {
				self.add_error(self, null, e);
			}
			else {
				throw e;
			}
		}

		if (cleaned_data != null){
			self.cleaned_data = cleaned_data;
		}
            
	},

    _post_clean : function(self){
        /*"""
        An internal hook for performing additional cleaning after form cleaning
        is complete. Used for model validation in model forms.
        """*/
	},

	clean : function(self){
		/*"""
        Hook for doing any extra form-wide cleaning after Field.clean() has been
        called on every field. Any ValidationError raised by this method will
        not be associated with a particular field; it will have a special-case
        association with the field named '__all__'.
        """*/
		return self.cleaned_data;
	},

	changed_data : function(self){
        var data = [];

		for (var name in self.fields){
			var field = self.fields[name];
			var prefixed_name = self.add_prefix(self, name);
			var data_value = field.widget.value_from_datadict(field.widget, self.data, self.files, prefixed_name);
			if (field.show_hidden_initial == false){
                //# Use the BoundField's initial as this is the value passed to
                //# the widget.
                var initial_value = self[name].initial;
			}
			else {
				var initial_prefixed_name = self.add_initial_prefix(self, name);
                var hidden_widget = field.hidden_widget.create();
                try {
					var hidden_value = hidden_widget.value_from_datadict(hidden_widget, self.data, self.files, initial_prefixed_name);
                    var initial_value = field.to_javascript(field, hidden_value);
				}

				catch(e){
					if (e instanceof ValidationError) {
						//# Always assume data has changed if validation fails.
                		data.push(name);
					} 
					else {
						throw e;
					}
				}
                continue;
			}

			if (field.has_changed(field, initial_value, data_value) == true){
                data.push(name);
			}
		}

        return data;
	},

	get_initial_for_field : function(self, field, field_name){
        /*"""
        Return initial data for field on form. Use initial data from the form
        or the field, in that order. Evaluate callable values.
        """*/

		if (self.initial.hasOwnProperty(field_name)){
			var value = self.initial[field_name];
		}
		else {
			var value = field.initial;
		}

		if (typeof value === 'function'){
			value = value();
		}

		return value;
	}

};

/* form from model, definition in appforms, has an additional save() method */
forms.ModelForm = derive(BaseForm, {

	form_type : "ModelForm",

	create : function(kwargs){
		var self = Object.create(this);

		self.instance = null
		var object_data = {};
		if (kwargs.hasOwnProperty("instance")){
			self.instance = kwargs.instance;
			object_data = model_to_dict(self.instance, self.Meta);
		}

		if (kwargs.hasOwnProperty("initial") == false){
			kwargs["initial"] = {};
		}

		for (var field_name in object_data){
			kwargs["initial"][field_name] = object_data[field_name];
		}

		this._create(self, kwargs);

		return self;
		
	},

	// the save method creates a new instance if no instance has been passed
	// if an instance has been passed, it will update this instance
	// uses cleaned_data
	save : function(self, callback){

		var perform_save = function(){

			// update the instance
			for (var field_name in self.cleaned_data){
				self.instance[field_name] = self.cleaned_data[field_name];
			}

			self.instance.save(self.instance, function(){
				// update all form fields to make form coherent with model instance
				// now the instance has all database values assigned
				// adjust all field values

				for (var f=0; f<self.fields.length; f++){
					var field = self.fields[f];
							
					// null values should be possible
					if (self.instance.hasOwnProperty(field["name"])){ // && self.instance[field["name"]] != null){
						field.value = self.instance[field["name"]];
						field.has_value = true;
					}
				}
			
				if (typeof callback == "function"){
					callback(self.instance);
				}
			});
		};
		
		if (self.instance != null){
			// avoid prototyping - be able to find changed values after .save() has been called
			// e.g. var instance1 = modelinstance; form.save(function(instance2){
			//	be able to compare instance1 with instance2
			// }) 
			var new_instance = self.Meta.model.create();
			for (var field_name in self.instance.fields){
				new_instance[field_name] = self.instance[field_name];
			}
			self.instance = new_instance;
			perform_save();
		}
		else {
			
			if (self.data.hasOwnProperty("pk")){
				self.Meta.model.objects.get({"pk":self.data["pk"]}, function(instance){
					self.instance = instance;
					perform_save();
				});
			}
			else {
				// create
				self.instance = self.Meta.model.create();
				perform_save();
			}
		}
	}
});

var ALL_FIELDS = '__all__';

function fields_for_model(model, kwargs){
		/*fields=None, exclude=None, widgets=None,
                     formfield_callback=None, localized_fields=None,
                     labels=None, helpTexts=None, error_messages=None,
                     fieldClasses=None, *, apply_limit_choices_to=True):*/
    /*"""
    Return an ``OrderedDict`` containing form fields for the given model.
    ``fields`` is an optional list of field names. If provided, return only the
    named fields.
    ``exclude`` is an optional list of field names. If provided, exclude the
    named fields from the returned fields, even if they are listed in the
    ``fields`` argument.
    ``widgets`` is a dictionary of model field names mapped to a widget.
    ``formfield_callback`` is a callable that takes a model field and returns
    a form field.
    ``localized_fields`` is a list of names of fields which should be localized.
    ``labels`` is a dictionary of model field names mapped to a label.
    ``helpTexts`` is a dictionary of model field names mapped to a help text.
    ``error_messages`` is a dictionary of model field names mapped to a
    dictionary of error messages.
    ``fieldClasses`` is a dictionary of model field names mapped to a form
    field class.
    ``apply_limit_choices_to`` is a boolean indicating if limit_choices_to
    should be applied to a field's queryset.
    """*/

    var fields = null;

	var kwargs = kwargs || {};

	if (kwargs.hasOwnProperty("fields")){
		fields = kwargs["fields"];
	}

	var exclude = null;
	if (kwargs.hasOwnProperty("exclude")){
		exclude = kwargs["exclude"];
	}

    var ignored = [];
    var opts = model.Meta;

	var field_dict = {
		"pk" : forms.IntegerField({"widget":forms.HiddenInput, "required":false})
	};

	for (var field_name in model.fields){
		var f = model.fields[field_name];

		var editable = f.hasOwnProperty("editable") ? f.editable : true;

		if (editable == false){
			throw new Error("" + field_name + " cannot be specified for " + model.model_name + " model form as it is a non-editable field" );
		}

		if (fields != null && fields.indexOf(field_name) < 0 ){
			continue;
		}

		if (exclude != null && exclude.indexOf(field_name) >=0){
			continue;
		}

		var field_kwargs = {};


		if (kwargs.hasOwnProperty("widgets") && kwargs.widgets.hasOwnProperty(field_name)){
            field_kwargs["widget"] = kwargs.widgets[field_name];
		}

		if (kwargs.hasOwnProperty("localized_fields")){
	        if (kwargs.localized_fields == ALL_FIELDS || kwargs.localized_fields.hasOwnProperty(field_name)){
    	        field_kwargs["localize"] = true;
			}
		}
        if (kwargs.hasOwnProperty("labels") && kwargs.labels.hasOwnProperty(field_name)){
            field_kwargs["label"] = kwargs.labels[field_name];
		}
        if (kwargs.hasOwnProperty("helpTexts") && kwargs.helpTexts.hasOwnProperty(field_name)){
            field_kwargs["helpText"] = kwargs.helpTexts[field_name];
		}
        if (kwargs.hasOwnProperty("error_messages") && kwargs.error_messages.hasOwnProperty(field_name)){
            field_kwargs["error_messages"] = kwargs.error_messages[field_name];
		}
        if (kwargs.hasOwnProperty("fieldClasses") && kwargs.fieldClasses.hasOwnPropert(field_name)){
			// django source uses "form_class" attribute
            field_kwargs["form_class"] = kwargs.fieldClasses[field_name];
		}
		
		var form_field = f.formfield(f, field_kwargs);
		field_dict[field_name] = form_field;
	}

	return field_dict;

}


function model_to_dict(instance, kwargs){
	//fields=None, exclude=None):
    /*"""
    Return a dict containing the data in ``instance`` suitable for passing as
    a Form's ``initial`` keyword argument.
    ``fields`` is an optional list of field names. If provided, return only the
    named.
    ``exclude`` is an optional list of field names. If provided, exclude the
    named from the returned dict, even if they are listed in the ``fields``
    argument.
    """*/
    var opts = instance.Meta;
    var data = {};
	var fields = null;
	if (kwargs.hasOwnProperty("fields")){
		fields = kwargs.fields;
	}

	var exclude = null;
	if (kwargs.hasOwnProperty("exclude")){
		exclude = kwargs.exclude;
	}

	for (var field_name in instance.fields){
		var f = instance.fields[field_name];
		if (f.hasOwnProperty("editable") && f.editable == false){
			continue;
		}
		if (fields != null && fields.indexOf(field_name) < 0){
			continue;
		}
		if (exclude != null && exclude.indexOf(field_name) > 0){
			continue;
		}

		data[field_name] = f.value_from_object(f, instance, field_name);
	}

    return data;
}


/* free form */
forms.Form = derive(BaseForm, {

	form_type : "Form",

	create : function(kwargs){
		var self = Object.create(this);
		
		this._create(self, kwargs);

		return self;
	}
});

/* utils.py */
var flatatt = function(attrs){
	/*"""
    Convert a dictionary of attributes to a single string.
    The returned string will contain a leading space followed by key="value",
    XML-style pairs. In the case of a boolean value, the key will appear
    without a value. It is assumed that the keys do not need to be
    XML-escaped. If the passed dictionary is empty, then return an empty
    string.
    The result is passed through 'mark_safe' (by way of 'format_html_join').
    """*/

    var key_value_attrs = {};
    var boolean_attrs = [];

    for (var attr in attrs){

		var value = attrs[attr];

        if (typeof value === 'boolean'){
            if (value === true){
                boolean_attrs.push(attr);
			}
		}
        else if (value != null){
            key_value_attrs[attr] = value;
		}
	}

    var flat = '';

	for (var attr in key_value_attrs){
		flat += ' ' + attr + '="' + key_value_attrs[attr] + '"';
	}

	for (var b=0; b<boolean_attrs.length; b++){
		flat += ' ' + boolean_attrs[b];
	}

	return flat;
}
