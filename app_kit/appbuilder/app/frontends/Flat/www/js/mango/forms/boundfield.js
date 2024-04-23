"use strict";

//"A Field plus data, bound to a form"
var BoundField = {
    
    create : function(form, field, name){

		var self = Object.create(this);

        self.form = form;
        self.form_field = field; // self.field is called from template as function
        self.name = name;
        self.html_name = form.add_prefix(form, name);
        self.html_initial_name = form.add_initial_prefix(form, name);
        self.html_initial_id = form.add_initial_prefix(form, self.auto_id(self));


		// caching errors
		self._errors = null;
		
        if (self.form_field.label == null){
			self.label = name.charAt(0).toUpperCase() + name.slice(1);
		}
        else {
            self.label = self.form_field.label;
		}

        self.helpText = field.helpText || '';

		if (self.form.is_bound == true){
			self.errors = self.get_errors(self);
		}
		else {
			self.errors = [];
		}
		return self;

	},

    field : function(){
		var self = this;
        //"""Render this field as an HTML widget."""
        if (self.form_field.show_hidden_initial){
            return self.as_widget(self, {"only_initial":true}) + self.as_hidden(self, { "only_initial":true});
		}
        return self.as_widget(self);
	},

    
    subwidgets : function(self){
        /*"""
        Most widgets yield a single subwidget, but others like RadioSelect and
        CheckboxSelectMultiple produce one subwidget for each choice.
        This property is cached so that only one database query occurs when
        rendering ModelChoiceFields.
        """*/
        /*var id_ = self.form_field.widget.attrs.get('id') || self.auto_id;
        attrs = {'id': id_} if id_ else {}
        attrs = self.build_widgetAttrs(attrs)
        return [
            BoundWidget(self.form_field.widget, widget, self.form.renderer)
            for widget in self.form_field.widget.subwidgets(self.html_name, self.value(), attrs=attrs)
        ]*/
	},


    // in django this method is called  errors
    get_errors : function(self){
        /*"""
        Return an ErrorList (empty if there are no errors) for this field.
        """*/

		if (self._errors === null){ 

			self._errors = [];

			var errors = self.form.errors(self.form);

			if (errors && errors.hasOwnProperty(self.name)){
				self._errors = errors[self.name];
			}
		}

		return self._errors;
        // return self.form.errors.get(self.name, self.form.error_class());
	},


    as_widget : function(self, kwargs){
        /*"""
        Render the field by rendering the passed widget, adding any HTML
        attributes passed as attrs. If a widget isn't specified, use the
        field's default widget.
        """*/

		var kwargs = kwargs || {};
		
		var widget = kwargs["widget"] || self.form_field.widget;
		var attrs = kwargs["attrs"] || {};
		var only_initial = kwargs["only_initial"] || false;

		// instantiate the widget
		if (widget.is_created == false){
			var widget = widget.create();
		}

        if (self.form_field.localize){
            widget.is_localized = true;
		}

        attrs = self.build_widgetAttrs(self, attrs, widget);

        var auto_id = self.auto_id(self);

        if (auto_id && !attrs.hasOwnProperty('id') && !widget.attrs.hasOwnProperty('id')){
            if (only_initial == false){
                attrs['id'] = auto_id;
			}
            else {
                attrs['id'] = self.html_initial_id;
			}
		}

        if (only_initial == false){
            var name = self.html_name;
		}
        else {
            var name = self.html_initial_name;
		}

		var value = self.value(self);

        return widget.render(widget, name, value, attrs, self.form.default_renderer, self.form_field);
      
	},

    
    data : function(self){
        /*"""
        Return the data for this BoundField, or None if it wasn't given.
        """*/
        return self.form_field.widget.value_from_datadict(self.form_field.widget, self.form.data, self.form.files, self.html_name);
	},

    value : function(self){

        /*"""
        Return the value for this BoundField, using the initial value if
        the form is not bound or the data otherwise.
        """*/
        var data = self.initial(self);
        if (self.form.is_bound == true){
			var bound_data = self.data(self);
            data = self.form_field.bound_data(self.form_field, bound_data, data);
		}

        return self.form_field.prepare_value(self.form_field, data);
	},

    label_tag : function(self, contents, attrs, label_suffix){
        /*"""
        Wrap the given contents in a <label>, if the field has an ID attribute.
        contents should be mark_safe'd to avoid HTML escaping. If contents
        aren't given, use the field's HTML-escaped label.
        If attrs are given, use them as HTML attributes on the <label> tag.
        label_suffix overrides the form's label_suffix.
        """*/
        var contents = contents || self.label;

		var attrs = attrs || {};
		var label_suffix = label_suffix || null;

        if (label_suffix == null){
			if (self.form_field.label_suffix != null){
				label_suffix = self.form_field.label_suffix;
			}
			else {
				label_suffix = self.form.label_suffix;
			}
		}
        //# Only add the suffix if the label does not end in punctuation.
        //# Translators: If found as last label character, these punctuation
        //# characters will prevent the default label_suffix to be appended to the label
        if (label_suffix != null && typeof contents == 'string' && ':?.!'.indexOf(contents[-1]) == -1){
            contents = contents + label_suffix;
		}

        var widget = self.form_field.widget;

        var id_ = widget.attrs.get('id') || self.auto_id(self);

        if (id_){
            var id_for_label = widget.id_for_label(id_);
            if (id_for_label){
                attrs['for'] = id_for_label;
			}
            if (self.form_field.required == true && self.form.hasOwnProperty('required_css_class')){
                
                if (attrs.hasOwnProperty('class')){
                    attrs['class'] += ' ' + self.form.required_css_class;
				}
                else {
                    attrs['class'] = self.form.required_css_class;
				}
			}

            flattrs = flatatt(attrs);
            var html = '<label' + flattrs + '>' + contents + '</label>';

		}
        else {
            var html = contents;
		}
        return html
	},
	// ECMAScript2015 supports defaults
    css_classes : function(self, extra_classes=null){
        /*"""
        Return a string of space-separated CSS classes for this field.
        """*/
        /*if hasattr(extra_classes, 'split'):
            extra_classes = extra_classes.split()
        extra_classes = set(extra_classes or [])
        if self.errors and hasattr(self.form, 'error_css_class'):
            extra_classes.add(self.form.error_css_class)
        if self.form_field.required and hasattr(self.form, 'required_css_class'):
            extra_classes.add(self.form.required_css_class)
        return ' '.join(extra_classes)*/
	},

    
	is_hidden : function(){
		// called from template
		var self = this;
        //"""Return True if this BoundField's widget is hidden."""
        return self.form_field.widget.is_hidden;
	},

    
    auto_id : function(self) {
        /*"""
        Calculate and return the ID attribute for this BoundField, if the
        associated Form has specified auto_id. Return an empty string otherwise.
        """*/
        var auto_id = self.form.auto_id(self.form);  //# Boolean or string

        if (typeof auto_id == 'string' && auto_id.indexOf('%s') >= 0){
            return auto_id.replace('%s', self.html_name);
		}
        return '';
	},

    
    id_for_label : function(self){
        /*"""
        Wrapper around the field widget's `id_for_label` method.
        Useful, for example, for focusing on this field regardless of whether
        it has a single widget or a MultiWidget.
        """*/
        var widget = self.form_field.widget;
		if (widget.attrs.hasOwnProperty('id')){
			var id_ = widget.attrs['id'];
		}
		else {
			var id_ = self.auto_id(self);
		}

		return widget.id_for_label(widget, id_)
	},

    
    initial : function(self){
        var data = self.form.get_initial_for_field(self.form, self.form_field, self.name)
        //# If this is an auto-generated default date, nix the microseconds for
        //# standardized handling. See #22502.
        //if (isinstance(data, (datetime.datetime, datetime.time)) and not self.form_field.widget.supports_microseconds):
        //    data = data.replace(microsecond=0)
        return data;
	},

    build_widgetAttrs : function(self, attrs, widget){

		var widget = widget || null;
        if (widget == null){
            widget = self.form_field.widget;
		}
        var attrs = JSON.parse(JSON.stringify(attrs)); //# Copy attrs to avoid modifying the argument.

        if (self.form_field.required == true){
            attrs['required'] = true;
		}
        if (self.form_field.disabled == true){
            attrs['disabled'] = true;
		}

		if (widget.hasOwnProperty("attrs")){

			for (var key in widget.attrs){
				attrs[key] = widget.attrs[key];
			}
		}

        return attrs;
	}
}
