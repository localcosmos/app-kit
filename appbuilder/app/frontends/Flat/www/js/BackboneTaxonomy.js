"use strict";

var BackboneTaxonomy = {

	get_taxon_by_uuid : function(nameUuid, callback){
		var start_letters = taxonLatname.substring(0,2);

		var alphabet_folder = app_features["BackboneTaxonomy"]["alphabet"];

		var filepath = alphabet_folder + start_letters.toUpperCase() + ".json";

		ajax.getJSON(filepath, {}, function(taxa){

			var taxon = null;

			for (var t=0; t<taxa.length; t++){
				var taxon_ = taxa[t];
				if (taxon_.nameUuid = nameUuid){
					taxon = taxon_;
					break;
				}
			}

			callback(taxon);

		}, function(){
			callback(null);
		});

	},
	get_taxon_profile : function(taxonSource, nameUuid, callback){

		// first try to get taxon_profile
		var profiles_folder = app_features["TaxonProfiles"]["files"];
		
		var profile_file = profiles_folder + "/" + taxonSource + "/" + nameUuid + ".json";

		ajax.getJSON(profile_file, {}, function(taxon_profile){
			callback(taxon_profile);
		}, function(e){
			callback(null);
		});

	},
	get_wikipedia_url : function(taxonLatname){
		var url = "https://" + app.language + ".m.wikipedia.org/wiki/" + taxonLatname;
		return url;
	}
};
