"use strict";

var DatasetJSONbuilder = derive(JSONbuilder, {

	get_empty_json : function(self){
	
		var empty_json = {
			"type": "Dataset", // type "Dataset", type "Feature" is GEOJSON
			"dataset": {
				"type": "Observation", /* type "Observation" needs reported_values (empty = {}) and observation_form (may not be empty) */
				"specification_version" : 1, /* version of type "Observation" */
				"reported_values": {
					"client_id" : device.uuid,
					"client_platform" : device.platform
					//"field_uuid" : {}  /* the uuid of the field and the data assigned to this field. the data can be text, json or numbers, or null */
				},
				"observation_form" : null, /* the observation form as json - see specification for ObservationFormJSON */
				"properties" : {}
			},
			"properties": {
				"thumbnail" : { // provide a thumbnail, eg for rendering a preview of the observation
					"url" : null
				}
			}
		};

		return empty_json;
	},

	validate : function(self, dataset){
		return true;
	},

	set_verbose : function(self){
		self.verbose = _("Dataset");
	},

	set_reported_values : function(self, new_reported_values){

		// some data from fields are instances, e.g. TaxonField delivers a Taxon instance
		// instances cannot be saved in a database
		// a json representation for that instance is needed
		// the instance has to provide a .json property

		// reset values to eliminate values not transmitted by the form
		// by default include client_id and client_platform
		self.json.dataset.reported_values = {
			"client_id" : device.uuid,
			"client_platform" : device.platform
		};

		var data_keys = Object.keys(new_reported_values);

		// skip files and filefields
		for (let d=0; d<data_keys.length; d++){
			var key = data_keys[d];
			var value = new_reported_values[key];

			// use json type for complex data like a taxon
			if (typeof value == "object" && value != null){

				if (value.hasOwnProperty("json")){
					self.json.dataset.reported_values[key] = value.json;
				}
				else {
					self.json.dataset.reported_values[key] = value;
				}
			}
			else {
				self.json.dataset.reported_values[key] = value;
			}
		}


	},

	set_observation_form : function(self, observation_form_uuid, onsuccess, onerror){

		var path = "" + app_features.GenericForm.lookup[observation_form_uuid];

		ajax.send({
			url : path,
			method: "GET",			
			success: function(content){
				
				var observation_form_json = content; //JSON.parse(atob(content));

				self.json.dataset.observation_form = observation_form_json;
				onsuccess(self);
			},
			error : onerror,
			data : {}
		});

	},

	set_thumbnail : function(self, url){
		if (self.json.properties.hasOwnProperty("thumbnail") == false){
			self.json.properties["thumbnail"] = {};
		}
		self.json.properties.thumbnail["url"] = url;
	}
});
