"use strict";

/*
* FakeInput
* a "fake" TextField that opens a popup when clicked
*/
forms["FakeInput"] = Widget(BaseWidget, {

	"identifier" : "FakeInput",
	"template_name" : "js/templates/forms/widgets/fake.html"

});

/*
* FakePositionInput
* - also supplies an indicator that the position is being fetched automatically
*/
forms["FakePositionInput"] = Widget(BaseWidget, {

	"identifier" : "FakePositionInput",
	"template_name" : "js/templates/forms/widgets/fake_position.html"

});


forms["AutocompleteTextInput"] = Widget(BaseWidget, {

	"identifier" : "AutocompleteTextInput",
	"template_name" : "js/templates/forms/widgets/autocomplete_text.html"

});

/*
* JSONWidget
* - consists of a verbose field (TextInput) and a textValue field (HiddenInput) which holds the json
* - supports autocomplete
* - currently, JSONWidget has to consist of exactly two widgets: verbose (Text or Fake) and json (Hidden)
*/
forms["JSONWidget"] = derive(MultiWidget, {
	"identifier" : "JSONWidget",

	widgets : [
		forms.TextInput,
		forms.HiddenInput
	],

	get_context : function(self, name, value, attrs, field){

		var context = forms.JSONWidget.super().get_context(self, name, value, attrs, field);

		context["widget"]["subwidgets"][0]["attrs"]["data-input-id"] = context["widget"]["subwidgets"][1]["attrs"]["id"];
		context["widget"]["subwidgets"][1]["attrs"]["data-verbose-input-id"] = context["widget"]["subwidgets"][0]["attrs"]["id"];

		return context;

	},

	verbose_value : function(self, value){
		// called from decompress
		throw new Error("JSONWidgets need to implement verbose_value");
	},

	format_value : function(self, value){

		if (value != null && value != ''){
			if (typeof value == "object"){
				if (value instanceof Array){
					value = value[1];
				}
				value = JSON.stringify(value);
			}
		}
		else {
			value = '';
		}

		return value;
	},

	decompress : function(self, value){
		// value in this case is parsed JSON
        /*"""
        Return a list of decompressed values for the given compressed value.
        The given value can be assumed to be valid, but not necessarily
        non-empty.
        """*/
		// the first is the human-readable value, the second is stringified json
		if (value != null && value != ''){
        	return [self.verbose_value(self, value), self.format_value(self, value)];
		}
		return [null, null];
	}

});


forms["BackboneTaxonAutocompleteWidget"] = Widget(forms.JSONWidget, {
	"identifier" : "BackboneTaxonAutocompleteWidget",

	widgets : [
		forms.AutocompleteTextInput.create([], {"attrs" : {"action" : "forms.BackboneTaxonAutocompleteWidget.autofill", "data-onblur":"forms.BackboneTaxonAutocompleteWidget.onblur", "data-onfocus" : "forms.BackboneTaxonAutocompleteWidget.onfocus", "autocomplete":"off"} }),
		forms.HiddenInput // taxon_json
	],

	verbose_value : function(self, value){
		// receives parsed JSON
		var verbose_value = '';
		
		if (value && typeof value == "object") {
			return value.taxonLatname;
		}

		return verbose_value;
	},

	/* autofill process
	*  - display selectable search results
	*  - typing equals deselection -> mark the field as invalid
	*  - selecting equals valid field -> mark the field as valid
	*/
	autofill : function(self, request, args, kwargs){

		var search_result_template = '{{#if results}}{{#each results}}<div class="tap" action="forms.BackboneTaxonAutocompleteWidget.select_taxon" data-taxon-json="{{ json_string }}" data-verbose-input-id="{{ ../verbose_input_id }}" data-taxon-json-input-id="{{ ../taxon_json_input_id }}">{{#if name}}{{ name }} ({{ taxonLatname }}){{else}}{{ taxonLatname }}{{/if}}</div>{{/each}}{{else}}<div>{{t "NoTaxonFound"}}</div>{{/if}}';

		var input = kwargs.currentTarget;
		input.classList.remove("is-valid");
		input.classList.add("is-invalid");
		var taxon_json_input_id = input.id.substring(0, input.id.length-2) + "_1";

		// remove the current taxon json value
		var taxon_json_input = document.getElementById(taxon_json_input_id);
		taxon_json_input.value = "";
		
		// fire change event for taxon_json_input
		var change_event = new Event('change');
		taxon_json_input.dispatchEvent(change_event);

		var searchtext = input.value;

		var results_container_id = input.getAttribute("data-results");
		var results_container = document.getElementById(results_container_id)

		if (searchtext.length >= 3){
			results_container.classList.remove("hidden");
			TaxonSearch.search_backbone(searchtext, function(results){

				var context = {
					"results" : results,
					"verbose_input_id" : input.id,
					"taxon_json_input_id" : taxon_json_input_id
				};

				var template_html = Handlebars.compile( search_result_template )(context);

				results_container.innerHTML = template_html;			

			});
		}
		else {
			results_container.textContent = "";
			results_container.classList.add("hidden");
		}
	},

	onblur : function(self, request, args, kwargs){
		var verbose_input = kwargs.currentTarget;
		
		// if the field losesfocus and no value has been set for the taxon, remove the verbosetext input

		var taxon_json_input_id = verbose_input.getAttribute("data-input-id");
		var taxon_json_input = document.getElementById(taxon_json_input_id);

		if (taxon_json_input.value.length == 0){
			verbose_input.value = "";
		}
	},

	select_taxon : function(self, request, args, kwargs){
		var selected = kwargs.currentTarget;

		var selected_text = selected.textContent;
		var taxon_json = selected.getAttribute("data-taxon-json");

		var taxon_json_input_id = selected.getAttribute("data-taxon-json-input-id");

		var taxon_json_input = document.getElementById(taxon_json_input_id);
		taxon_json_input.value = taxon_json;

		// fire changeevent
		var change_event = new Event('change');
		taxon_json_input.dispatchEvent(change_event);

		var taxon = JSON.parse(taxon_json);

		var verbose_input_id = selected.getAttribute("data-verbose-input-id");
		var verbose_input = document.getElementById(verbose_input_id);
		verbose_input.value = selected_text;

		verbose_input.classList.add("is-valid");
		verbose_input.classList.remove("is-invalid");

		var results_container_id = verbose_input.getAttribute("data-results");
		document.getElementById(results_container_id).textContent="";
	},

	onfocus : function(self, request, args, kwargs){
		var verbose_input = kwargs.currentTarget;
		verbose_input.select();
	}

});

/*
	the mobileposition input uses the geojson position object as stringified json
*/
forms["MobilePositionInput"] = Widget(forms.JSONWidget, {
	"identifier" : "MobilePositionInput",

	widgets : [
		forms.FakePositionInput.create([], {"attrs": {"action":"selectPosition"} }),
		forms.HiddenInput
	],

	verbose_value : function(self, value){
		/* the value in human readable format, receives parsed JSON */
		var verbose_value = '';

		if (value && typeof value == "object") {
			
			var geojson = value;
			
			verbose_value = "" + geojson.geometry.coordinates[1].toFixed(4).toString() + "N " + geojson.geometry.coordinates[0].toFixed(4).toString() + "E [" + parseInt(geojson.properties.accuracy).toString() + "m]";

		}

		return verbose_value;
	}

});

/*
* SelectDateTimeWidget should be used in conjunction with JSONField
*/
forms["SelectDateTimeWidget"] = Widget(forms.JSONWidget, {
	"identifier" : "SelectDateTimeWidget",

	widgets : [
		forms.FakeInput.create([], {"attrs": {"action":"selectDateTime"} }),
		forms.HiddenInput
	],

	verbose_value : function(self, value){

		/* the value in human readable format, receives parsed JSON */
		var temporal_json = self.format_value(self, value);

		var verbose_value = '';

		if (temporal_json != ''){
			var temporal = TemporalJSONbuilder.create(JSON.parse(temporal_json));
			verbose_value = temporal.verbose;
		}

		return verbose_value;
	},

	format_value : function(self, value){
		// receives temporalJSON string or a Date object
		/* the value as TemporalJSON string  */

		if (value != null && value != ''){

			if (typeof value == "object" && value instanceof Array){
				value = value[1];
			}

			if (typeof value == "object" && value.type === "Temporal"){
				value = JSON.stringify(value);
			}
			else {

				if (typeof value == "object" && value instanceof Date){
					var unixtime = value.getTime();
					// create the correct TemporalJSON
					var temporal = TemporalJSONbuilder.create();
					temporal.load_unixtime(temporal, unixtime);
					value = temporal.as_text(temporal);
				}
				else if (typeof value != "string"){
					throw new Error("[SelectDateTimeWidget].format_value received invalid value.");
				}

			}
		}
		else {
			value = '';
		}

		return value;
		
	}

});


forms["MobileNumberInput"] = Widget(forms.NumberInput, {
	"identifier" : "MobileNumberInput",
	"template_name" : "js/templates/forms/widgets/mobile_number.html"
});


var thumbnail_cache = {
	_cache : {},
	add : function(filename, thumbnail_type, thumb_url){
		if (this._cache.hasOwnProperty(filename) == false){
			this._cache[filename] = {};
		}
		this._cache[filename][thumbnail_type] = thumb_url;
	},
	get : function(filename, thumbnail_type) {
		if (this._cache.hasOwnProperty(filename) && this._cache[filename].hasOwnProperty(thumbnail_type)){
			return this._cache[filename][thumbnail_type];
		}
		return null;
	}
};

forms["CameraAndAlbumWidget"] = Widget(forms.FileInput, {
	"identifier" : "CameraAndAlbumWidget",
	"template_name" : "js/templates/forms/widgets/camera_and_album.html",

	format_value : function(self, value){
		//"""
        //Return a value as it should appear when rendered in a template.
        //"""
		// simply return a list of images
		if (value){
			var filelist = value;
			var image_list = [];

			for (let f=0; f<filelist.length; f++){
				let file_obj = filelist[f];

				if (FlexImage.isPrototypeOf(file_obj)){

					// a flexfile
					var fleximage = file_obj;

					// fleximage from db has small attached. fleximage from form field does not
					if (fleximage.hasOwnProperty("small") == false){
						var thumbnail = thumbnail_cache.get(fleximage.filename, "small");
						fleximage.small = thumbnail;
					}

					image_list.push(fleximage);
				}
				else {
					// it might be json from remotedb - this has to be altered in a way that remotedb returns fleximages
					image_list.push(file_obj);
				}
			}

			return image_list;
		}

		return value;
		
	},

	_create_thumbnail : function(self, file_obj, thumbnail_type){

		let existing_thumb = thumbnail_cache.get(file_obj.filename, thumbnail_type);

		if (existing_thumb == null){
			if (thumbnail_type == "full_hd"){
				var thumbnail = Thumbnail.create({
					quality : 0.9,
					maxWidth : 1000,
					maxHeight : 1000,
					imageSize : "contain"
				});
			}
			else {
				var thumbnail = Thumbnail.create();
			}

			thumbnail.as_data_url(file_obj, function(thumb_url){
				thumbnail_cache.add(file_obj.filename, thumbnail_type, thumb_url)
			});
		}
	},

	value_from_datadict : function(self, data, files, name){

        /*"""
        Given a dictionary of data and this widget's name, return the value
        of this widget or None if it's not provided.
        """*/

		// data is an Array of File objects if not yet uploaded

		if (data.hasOwnProperty(name)){
			let filelist = data[name];

			// this is not a good solution because this is async and creates a race condition
			// anyhow, this is only a backup, the cache should already be filled at this time
			each(filelist, function(file_obj, iterate){
				// create thumbnails for cache
				self._create_thumbnail(self, file_obj, "small");
	  			self._create_thumbnail(self, file_obj, "full_hd");
				iterate();
			}, function(){});

			return filelist;
		}

		return null;
	}
});
