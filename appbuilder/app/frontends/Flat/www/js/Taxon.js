"use strict";

var Taxon = {
	create : function(taxonSource, nameUuid, taxonLatname, taxonAuthor, taxonNuid, kwargs){

		var taxonSource = taxonSource || null;
		var nameUuid = nameUuid || null;
		var taxonLatname = taxonLatname || null;
		var taxonAuthor = taxonAuthor || null;
		var taxonNuid = taxonNuid || null;

		var kwargs = kwargs || {};

		if (taxonSource == null || nameUuid == null || taxonLatname == null || taxonNuid == null){
			throw new Error("Failed to instantiate taxon. You have to provide at least taxonSource, nameUuid, taxonLatname and taxonNuid");
		}

		var self = Object.create(this);

		self.attrs = ["taxonSource", "nameUuid", "taxonLatname", "taxonAuthor", "taxonNuid"];

		self.taxonSource = taxonSource;
		self.nameUuid = nameUuid;
		self.taxonLatname = taxonLatname;
		self.taxonAuthor = taxonAuthor;
		self.taxonNuid = taxonNuid;
		
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
