"use strict";

/*
* GeoJSONbuilder
* - create and validate GeoJSON
*/
var GeoJSONbuilder = derive(JSONbuilder, {

	supported_geometry_types : ["Point"],
	
	get_empty_json : function(self){
	
		var empty_json = {
			"type": "Feature",
			"geometry": {
				"type": null
			},
			"properties": {}
		};

		return empty_json;
	},

	validate_Point : function(self, json){
		var is_valid = true;

		return is_valid;
	},

	validate : function(self, json){

		var is_valid = true;
	
		if (self.json.type != "Feature" || !(self.json.hasOwnProperty("geometry"))){
			is_valid = false;
		}
		else {
			if (self.supported_geometry_types.indexOf(json.geometry.type) >= 0){
				var fn = "validate_" + json.geometry.type;
				is_valid = self[fn](self, json);
			}
			else {
				is_valid = false;
			}
		}

		return is_valid;

	},

	set_verbose : function(self){
		var is_valid = self.validate(self, self.json);
		if (is_valid === true){
			self.verbose = "" + self.json.geometry.coordinates[0].toFixed(4).toString() + "E " + self.json.geometry.coordinates[0].toFixed(4).toString() + "N";
		}
		else {
			self.verbose = "No coordinates set";
		}
	},

	load_html5_position : function(self, position_html5){
		// load navigator.geolocation.position as geojson
		var geojson = {
			"type" : "Feature",
			"geometry" : {
				"type": "Point",
				"coordinates": [position_html5.coords.longitude, position_html5.coords.latitude],
				"crs": {
					"type": "name",
					"properties": {
						"name":"EPSG:4326" // or urn:ogc:def:crs:EPSG::4326
					}
				}
			},
			"properties" : {
				"accuracy" : position_html5.coords.accuracy
			}
		};
		
		self.json = geojson;
	}

});
