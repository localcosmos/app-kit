"use strict";

/*
* A field that expects JSON and offers a verbose value
*/
forms.JSONField = function(kwargs){

	var definition = {
		"fieldClass" : "JSONField",
		"widget" : forms.JSONWidget, // this widget is not usable - it needs to be subclassed
		"fields" : [
			forms.CharField(), // verbose input
			forms.CharField() // json (as text)
		],

		compress : function(self, data_list){
			var json = JSON.parse(data_list[1]);
			return json;
		}

	};

	for (var key in kwargs){
		definition[key] = kwargs[key];
	}

	var field = MultiValueField(definition);

	return field;
};


// this field provides an "initial" function
forms.DateTimeJSONField = function(kwargs){

	var definition = {
		"fieldClass" : "DateTimeJSONField",
		"default_initial" : function(){
			return new Date();
		}
	};

	for (var key in kwargs){
		definition[key] = kwargs[key];
	}

	var field = forms.JSONField(definition);

	return field;
};

// rename this TaxonJSONField ?
forms.TaxonField = function(kwargs){

	var definition = {
		"fieldClass" : "TaxonField",

		"error_messages" : {
			"required" : "You have to start typing and then select a Taxon from the suggestions.",
			"taxon_error" : "The taxon you selected is missing parameters. Try selecting a different taxon"
		},

		// custom validation method
		validate : function(self, value){
			// compress has been called
		    if ( self.empty_values.indexOf(value) >=0 && self.required ){
		        throw new forms.ValidationError(_(self.error_messages["required"]));
			}

			// validate the taxon
			// value is a taxon instance

			var attrs = ["taxonSource", "nameUuid", "taxonLatname", "taxonAuthor"];

			for (var a=0; a<attrs.length; a++){
				var attr = attrs[a];
			
				if (!(value.hasOwnProperty(attr))){
					throw new forms.ValidationError(_(self.error_messages["taxon_error"]));
				}
				else if (attr != "taxonAuthor" && value[attr].length == 0) {
					throw new forms.ValidationError(_(self.error_messages["taxon_error"]));
				}
			}
		
		},

		compress : function(self, data_list){

			var taxon_json = JSON.parse(data_list[1]);
			var taxon = Taxon.create(taxon_json.taxonSource, taxon_json.nameUuid, taxon_json.taxonLatname, taxon_json.taxonAuthor, taxon_json.taxonNuid);
			return taxon;
		}

	};

	if (kwargs.hasOwnProperty("widget") == false){
		kwargs["widget"] = forms.BackboneTaxonAutocompleteWidget;
	}

	for (var key in kwargs){
		definition[key] = kwargs[key];
	}

	var field = forms.JSONField(definition);

	return field;
};


forms.PointJSONField = function(kwargs){

	var definition = {
		"fieldClass" : "PointJSONField",
		"error_messages" : {
			"required": "This field is required.",
			"invalid_geojson" : "Invalid Geojson.",
			"invalid_geometry" : "Only GeoJSON Point Geometries including a SRID are allowed."
		},

		"validate" : function(self, value){

			this.super().validate(self, value);
	
			// the value is json and needs to be validated as GEOJSON Point
			var geojson = value;

			try {

				var geometry = geojson.geometry;

				if (geojson.type == "Feature" && geometry.type == "Point" && (geometry.coordinates.length == 2 || geometry.coordinates.length == 3) && geometry.hasOwnProperty("crs")){
					if (geometry.crs.type == "name" && geometry.crs.hasOwnProperty("properties") && geometry.crs.properties.hasOwnProperty("name")){
						// pass test
					}
					else {
						// fail
						throw new forms.ValidationError(_(self.error_messages["invalid_geometry"]));
					}
				}
				else {
					throw new forms.ValidationError(_(self.error_messages["invalid_geometry"]));
				}
			}
			catch (e){
				throw new forms.ValidationError(_(self.error_messages["invalid_geometry"]));
			}
		}
	};

	for (var key in kwargs){
		definition[key] = kwargs[key];
	}

	var field = forms.JSONField(definition);

	return field;
};


// the value of a PictureField is always a list
forms.PictureField = function(kwargs){

	var definition = {
		"fieldClass" : "PictureField",
		"widget" : forms.CameraAndAlbumWidget,
		"empty_values" : [null, '', []],

		bound_data : function(self, data, initial){
		    /* make the file field data available on consecutive "save" actions
			* filefields data gets cleared after user presses save, fall back to initial
			* data that is in inital
			*/

			var data = data || [];
			var initial = initial || [];

			var bound_data = data.concat(initial);
			return bound_data;
		}
	};

	for (var key in kwargs){
		definition[key] = kwargs[key];
	}

	var field = forms.ImageField(definition);

	return field;

}
