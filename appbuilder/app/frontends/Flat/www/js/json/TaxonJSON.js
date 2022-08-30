"use strict";

/*
* TaxonJSONbuilder
* - create and validate TaxonJSON
*/
var TaxonJSONbuilder = derive(JSONbuilder, {

	get_empty_json : function(self){
	
		var empty_json = {};

		return empty_json;
	},

	validate : function(self, json){
		var required_data = ["taxonSource", "nameUuid", "taxonLatname", "taxonAuthor", "taxonNuid"];

		var is_valid = true;

		// check not null and maybe type
		for (var k=0; k<required_data.length; k++){
			var attr = required_data[k];
			
			if (json.hasOwnProperty(attr) == false){
				is_valid = false;
				break;
			}
			// author can be null
			else if (attr != "taxonAuthor" && json[attr].length == 0){
				is_valid = false;
				break;
			}
		}

		return is_valid;

	},

	set_verbose : function(self){
		var is_valid = self.validate(self, self.json);
		if (is_valid === true){
			self.verbose = self.json.taxonLatname;
		}
		else {
			self.verbose = _("No Taxon set.");
		}
	},

	load_taxon : function(self, taxon, kwargs){
		// receive taxon, return TaxonJSON
		var json = self.get_empty_json(self);

		for (var k=0; k<taxon.attrs.length; k++){
			var attr = taxon.attrs[k];
			json[attr] = taxon[attr];
		}

		self.json = json;

		self.set_verbose(self);

	}

});
