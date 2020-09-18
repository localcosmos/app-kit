"use strict";

/*
* TemporalJSONbuilder
* - create and validate TemporalJSON
*/
var TemporalJSONbuilder = derive(JSONbuilder, {
	
	supported_types : ["timestamp"],

	get_empty_json : function(self){
	
		var empty_json = {
			"type": "Temporal",
			"cron": {
				"type": null
			}
		};

		return empty_json;
	},

	validate_timestamp : function(self, json){	
		var is_valid = true;
		if (json.cron.format == "unixtime"){
			if (!(parseInt(json.cron.timestamp) === json.cron.timestamp)){
				is_valid = false;
			}
		}
		else {
			is_valid = false;
		}

		return is_valid;
	},

	validate : function(self, json){
		// validation based on cron.type

		var is_valid = true;

		if (!(json.hasOwnProperty("type")) || json.type != "Temporal" || !(json.hasOwnProperty("cron"))){
			is_valid = false;
		}
		else {
			if (self.supported_types.indexOf(json.cron.type) >= 0){
				var fn = self["validate_" + json.cron.type];
				is_valid = fn(self, json);
			}
			else {
				is_valid = false;
			}
		}

		return is_valid;

	},

	set_verbose : function(self){
		var is_valid = self.validate(self, self.json);
		if (is_valid == true){
			var date = new Date(self.json.cron.timestamp);
			self.verbose = date.toLocaleString();
		}
		else {
			self.verbose = _("No time set");
		}
	},

	load_Date : function(self, dateobj, kwargs){
		// maybe accept format in kwargs

		var json = self.get_empty_json(self);
		json.cron["type"] = "timestamp";
		json.cron["format"] = "unixtime";

		// timestamp is always UTC
		json.cron["timestamp"] = dateobj.getTime();

		// timezone offset is necessary
		json.cron["timezone_offset"] = dateobj.getTimezoneOffset();

		self.json = json;

		self.set_verbose(self);

	},

	load_unixtime : function(self, unixtime, kwargs){
		// maybe accept format in kwargs

		var json = self.get_empty_json(self);
		json.cron["type"] = "timestamp";
		json.cron["format"] = "unixtime";
		json.cron["timestamp"] = unixtime;

		json.cron["timezone_offset"] = new Date().getTimezoneOffset();

		self.json = json;

		self.set_verbose(self);

	},

	as_unixtime : function(self){
		return self.json.cron.timestamp;
	},

	as_Date : function(self){
		return new Date(self.json.cron.timestamp);
	}

});
