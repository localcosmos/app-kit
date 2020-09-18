"use strict";

var BackboneTaxonomy = {

	get_taxon_by_uuid : function(name_uuid, callback){
		var start_letters = taxon_latname.substring(0,2);

		var alphabet_folder = app_features["BackboneTaxonomy"]["alphabet"];

		var filepath = alphabet_folder + start_letters.toUpperCase() + ".json";

		ajax.getJSON(filepath, {}, function(taxa){

			var taxon = null;

			for (var t=0; t<taxa.length; t++){
				var taxon_ = taxa[t];
				if (taxon_.name_uuid = name_uuid){
					taxon = taxon_;
					break;
				}
			}

			callback(taxon);

		}, function(){
			callback(null);
		});

	},
	get_taxon_profile : function(taxon_source, name_uuid, callback){

		// first try to get taxon_profile
		var profiles_folder = app_features["TaxonProfiles"]["files"];
		
		var profile_file = profiles_folder + "/" + taxon_source + "/" + name_uuid + ".json";

		ajax.getJSON(profile_file, {}, function(taxon_profile){
			callback(taxon_profile);
		}, function(e){
			callback(null);
		});

	},
	get_wikipedia_url : function(taxon_latname){
		var url = "https://" + app.language + ".m.wikipedia.org/wiki/" + taxon_latname;
		return url;
	}
};
