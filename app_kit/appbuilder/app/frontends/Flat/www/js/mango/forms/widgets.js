"use strict";

var BaseWidget = {

	is_hidden : false,
	is_required : true,
	template_name : null,

	needs_multipart_form : false,
	
	// forms.CharField(widget=forms.TextInput) and forms.CharField(widget=forms.TextInput.create(something)) both have to work
	is_created : false,

	__init__ : function(self, onsuccess){
		ajax.GET(self.template_name, {}, function(template_html){
			self.template = template_html;
			onsuccess();
		});
	},

	create : function(args, kwargs){
		var self = Object.create(this);

		// attrs can be passed in kwargs
		self.attrs = {};

		var args = args || [];
		var kwargs = kwargs || {};

		for (var key in kwargs){
			if (self.hasOwnProperty.call(kwargs, key) || typeof self[key] === "undefined") {
				self[key] = kwargs[key];
			}		
		}

		self.is_created = true;

		return self;
	},

	format_value : function(self, value){
		//"""
        //Return a value as it should appear when rendered in a template.
        //"""

		if (typeof value != "string"){
			if (typeof value == "undefined" || value == null){
				value = '';
			}
			else {
				value = value.toString();
			}
		}
		return value;
	},

	get_context : function(self, name, value, attrs, field){

        var context = {
			'widget' : {
		        'name': name,
		        'is_hidden': self.is_hidden,
		        'required': self.is_required,
		        'value': self.format_value(self, value),
		        'attrs': self.build_attrs(self, self.attrs, attrs),
		        'template_name': self.template_name
			}
        };
		return context;
	},

	render : function(self, name, value, attrs, renderer, field){

		var attrs = attrs || {};
		var renderer = renderer || null;
        //"""Render the widget as an HTML string."""
        var context = self.get_context(self, name, value, attrs, field);
        return self._render(self, self.template_name, context, renderer);
	},

    _render : function(self, template_name, context, renderer){

		var renderer = renderer || null;

		// create flatatts
		context["widget"]["flatattrs"] = flatatt(context["widget"]["attrs"]);

        if (renderer === null){
            var template_html = Handlebars.compile(self.template)(context);
			return template_html;
		}
		else {
			return default_renderer.render(template_name, context);
		}
	},

	build_attrs : function(self, base_attrs, extra_attrs){
        //"""Build an attribute dictionary."""
		var attrs = {};

		for (var key in base_attrs){
			attrs[key] = base_attrs[key];
		}
		
		if (typeof extra_attrs == "object"){
        	for (var key in extra_attrs){
				attrs[key] = extra_attrs[key];
			}
		}
		return attrs;
	},


	value_from_datadict : function(self, data, files, name){
        /*"""
        Given a dictionary of data and this widget's name, return the value
        of this widget or None if it's not provided.
        """*/
		if (data.hasOwnProperty(name)){
			return data[name];
		}
		return null;
	},

	id_for_label : function(self, id_){
        /*"""
        Return the HTML ID attribute of this Widget for use by a <label>,
        given the ID of the field. Return None if no ID is available.
        This hook is necessary because some widgets have multiple HTML
        elements and, thus, multiple IDs. In that case, this method should
        return an ID value that corresponds to the first ID in the widget's
        tags.
        """*/
		return id_;
	}
};


var Widget = function(prototype, extension, override){

	var	widget = derive(prototype, extension, override);

	mango.widgets.push(widget.identifier);

	return widget;

};


var MultiWidget = derive(BaseWidget, {
    /*"""
    A widget that is composed of multiple widgets.
    In addition to the values added by Widget.get_context(), this widget
    adds a list of subwidgets to the context as widget['subwidgets'].
    These can be looped over and rendered like normal widgets.
    You'll probably want to use this class with MultiValueField.
    """*/

	widgets : [],

    create : function(args, kwargs){
		var self = Object.create(this);
		var kwargs = kwargs || null;

		self._widgets = [];

		self.attrs = {};

		self.is_hidden = true;

		for (var w=0; w<self.widgets.length; w++){
			var widget = self.widgets[w];
			if (widget.is_created == false){
				widget = widget.create();
			}
			if (widget.is_hidden == false){
				self.is_hidden = false;
			}

			if (widget.needs_multipart_form == true){
				self.needs_multipart_form = true;
			}

			self._widgets.push(widget);
		}
        
        //self.super().__init__(attrs)
		// c&p
		var kwargs = kwargs || {};
		for (var key in kwargs){
			if (self.hasOwnProperty.call(kwargs, key) || typeof self[key] === "undefined") {
				self[key] = kwargs[key];
			}		
		}

		self.is_created = true;

		return self;
	},

    get_context : function(self, name, value, attrs, field){

        var context = MultiWidget.super().get_context(self, name, value, attrs, field);

        if (self.is_localized == true){
            for (var w=0; w<self._widgets.length; w++){
				var widget = self._widgets[w];
                widget.is_localized = self.is_localized;
			}
		}

        //# value is a list of values, each corresponding to a widget
        //# in self._widgets.
		if (!(value instanceof Array)){
			value = self.decompress(self, value);
		}

        var final_attrs = context["widget"]["attrs"];

		var input_type = null;
		if (final_attrs.hasOwnProperty("type")){
			input_type = final_attrs["type"];
		}
		
		var id_ = null;
		if (final_attrs.hasOwnProperty("id")){
	        id_ = final_attrs['id'];
		}

        var subwidgets = [];

        for (var i=0; i<self._widgets.length; i++){

			var widget = self._widgets[i];

            if (input_type != null){
                widget.input_type = input_type;
			}

            var widget_name = '' + name + '_' + i;

            var widget_value = null;
			if (value.length > i){
                widget_value = value[i];
			}

            if (id_ != null){
                var widgetAttrs = clone(final_attrs);
                widgetAttrs["id"] = '' + id_ + '_' + i;
			}
            else {
                var widgetAttrs = final_attrs;
			}

			var subwidget_context = widget.get_context(widget, widget_name, widget_value, widgetAttrs)["widget"];

            subwidgets.push(subwidget_context);
		}

        context["widget"]["subwidgets"] = subwidgets;
        return context
	},

    id_for_label : function(self, id_){
        if (id_){
            id_ += '_0';
		}
        return id_;
	},

    value_from_datadict : function(self, data, files, name){
		var value = [];

		for (var i=0; i<self._widgets.length; i++){
			var widget = self._widgets[i];
			var widget_value = widget.value_from_datadict(widget, data, files, name + '_' + i);
			value.push(widget_value)
		}
        return value;
	},

    value_omitted_from_data : function(self, data, files, name){
		var omitted = true;

		for (var i=0; i<self._widgets.length; i++){
			var widget = self._widgets[i];
			if (widget.value_omitted_from_data(data, files, name + '_' + i) == false){
				omitted = false;
			}
		}
        
		return omitted;

	},


    decompress : function(self, value){
        /*"""
        Return a list of decompressed values for the given compressed value.
        The given value can be assumed to be valid, but not necessarily
        non-empty.
        """*/
        throw new Error('Subclasses of MultiWidget must implement a decompress method.');
	},

    _get_media : function(self){
        /*"""
        Media for a multiwidget is the combination of all media of the
        subwidgets.
        """*/
        var media = []; //Media()
        for (var i=0; i<self._widgets.length; i++){
            media.push(self._widgets[i].media);
		}
        return media
    //media = property(_get_media)
	},

	_render : function(self, template_name, context, renderer){

		var renderer = renderer || null;

        if (renderer === null){

			// render the "supertemplate" which supplies rendered "subtemplates" in the context
			for (var i=0; i<self._widgets.length; i++){

				var widget = self._widgets[i];

				var widget_context = {
					"widget" : context["widget"]["subwidgets"][i]
				}

				// create flatatts
				widget_context["widget"]["flatattrs"] = flatatt(widget_context["widget"]["attrs"]);

            	var widget_html = Handlebars.compile(widget.template)(widget_context);

				widget_context["html"] = widget_html;

				context["widget"]["subwidgets"][i] = widget_context;
			}
			
			var template_html = Handlebars.compile(self.template)(context);
			return template_html;

		}
		else {
			return default_renderer.render(template_name, context);
		}
	},

	"template_name" : "js/mango/forms/templates/mango/forms/widgets/multi.html"

});


forms.TextInput = Widget(BaseWidget, {
	"identifier" : "TextInput",
	"template_name" : "js/mango/forms/templates/mango/forms/widgets/text.html"
});

forms.PasswordInput = Widget(BaseWidget, {
	"identifier" : "PasswordInput",
	"template_name" : "js/mango/forms/templates/mango/forms/widgets/password.html"
});

forms.HiddenInput = Widget(BaseWidget, {
	"identifier" : "HiddenInput",
	"is_hidden" : true,
	"template_name" : "js/mango/forms/templates/mango/forms/widgets/hidden.html"
});

forms.CheckboxInput = Widget(BaseWidget, {
	"identifier" : "CheckboxInput",
	"template_name" : "js/mango/forms/templates/mango/forms/widgets/checkbox.html"
});

forms.Textarea = Widget(BaseWidget, {
	"identifier" : "Textarea",
	"template_name" : "js/mango/forms/templates/mango/forms/widgets/textarea.html"
});

forms.NumberInput = Widget(BaseWidget, {
	"identifier" : "NumberInput",
	"template_name" : "js/mango/forms/templates/mango/forms/widgets/number.html"
});


var ChoiceWidget = derive(BaseWidget, {
	"identifier" : "ChoiceWidget",
	"choices" : [],
	"allow_multiple_selected" : false,
	"checked_attribute" : {"checked" : true},

	get_context : function(self, name, value, attrs, field){
		// add choices to context
        var context = ChoiceWidget.super().get_context(self, name, value, attrs);
		context["widget"]["choices"] = field.choices;
		return context;
	},

	"template_name" : "js/mango/forms/templates/mango/forms/widgets/select.html"
});

forms.Select = Widget(ChoiceWidget, {
	"identifier" : "Select",
	"checked_attribute" : {"selected" : true}
});

forms.CheckboxSelectMultiple = Widget(ChoiceWidget, {
	"identifier" : "CheckboxSelectMultiple",
	"template_name" : "js/mango/forms/templates/mango/forms/widgets/checkbox_multiple.html"
});


forms.FileInput = Widget(BaseWidget, {
	"identifier" : "FileInput",
	"template_name" : "js/mango/forms/templates/mango/forms/widgets/file.html"
});
