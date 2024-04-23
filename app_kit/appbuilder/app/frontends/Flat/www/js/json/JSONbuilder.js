"use strict";

/*
* JSONbuilder prototype
* - subclasses need load_* methods for loading content
* .json is the current - maybe incomplete json
* .as_json completes/validates the json and returns it
*/

var JSONbuilder = {
	
	create : function(provided_json){
		var self = Object.create(this);

		if (typeof self.get_empty_json != "function"){
			throw new Error("JSONbuilder subclasses need a get_empty_json method");
		}

		if (typeof self.set_verbose != "function"){
			throw new Error("JSONbuilder subclasses need an set_verbose method");
		}

		if (typeof self.validate != "function"){
			throw new Error("JSONbuilder subclasses need a validate method");
		}

		self.json = provided_json || self.get_empty_json(self);

		self.set_verbose(self);

		return self;
	},

	json : null, // the current json representation

	load_json : function(self, json){
		self.json = json;	
	},

	validate : null, // a method which validates a given json (self, json)

	get_empty_json : null, // a method that returns an empty json. superior to property like json : "", which could be altered unintentionally

	as_json : function(self){

		var is_valid = self.validate(self, self.json);
		
		if (is_valid == true){
			return self.json;
		}
		else {
			throw new Error("[JSONBuilder] Invalid JSON: " + JSON.stringify(self.json));
		}
	},

	as_text : function(self){
		var is_valid = self.validate(self, self.json);
		if (is_valid == true){
			return JSON.stringify(self.json);
		}
		else {
			throw new Error("[JSONBuilder] You tried to stringify invalid json");
		}
	},

	set_verbose : null, // create JSONbuilder.verbose text

	verbose : null // optional human-readable representation (text) of the json

};
