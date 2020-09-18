"use strict";

var Taxon = {
	create : function(taxon_source, name_uuid, taxon_latname, taxon_author, taxon_nuid, kwargs){

		var taxon_source = taxon_source || null;
		var name_uuid = name_uuid || null;
		var taxon_latname = taxon_latname || null;
		var taxon_author = taxon_author || null;
		var taxon_nuid = taxon_nuid || null;

		var kwargs = kwargs || {};

		if (taxon_source == null || name_uuid == null || taxon_latname == null || taxon_nuid == null){
			throw new Error("Failed to instantiate taxon. You have to provide at least taxon_source, name_uuid, taxon_latname and taxon_nuid");
		}

		var self = Object.create(this);

		self.attrs = ["taxon_source", "name_uuid", "taxon_latname", "taxon_author", "taxon_nuid"];

		self.taxon_source = taxon_source;
		self.name_uuid = name_uuid;
		self.taxon_latname = taxon_latname;
		self.taxon_author = taxon_author;
		self.taxon_nuid = taxon_nuid;
		
		var kwargs_ = clone(kwargs);

		for (var key in kwargs_){
			self[key] = kwargs_[key];
			if (self.attrs.indexOf(key) == -1){
				self.attrs.push(key);
			}
		}

		self.json = self.as_json(self);
		self.json_string = JSON.stringify(self.json);

		return self;
	},

	as_json : function(self){

		var builder = TaxonJSONbuilder.create();

		builder.load_taxon(builder, self);

		var json = builder.as_json(builder);
		return json;
	}
};
