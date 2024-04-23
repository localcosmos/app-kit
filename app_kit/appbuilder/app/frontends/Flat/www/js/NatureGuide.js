"use strict;"
/*
* this file is different from the one in app and builder
* element_id NatureGuideTaxa contains taxa
* element_id TaxonfilterContainer contains Taxonfilters
* element_id ActiveTaxonfilter contains the image of the active Taxonfilter
* element_id ActiveAlphabetfilter contains the image of the active Taxonfilter
* element_id TaxonNameSearch is the name search input
* NatureGuide.taxa points to DOMElements or list of objects (overview page)
*/

var NatureGuide = {

	overview_search_template : '<div><div>{{ taxon.merged_name }}</div><div class="natureguide-overview-searchresult">{{#if options.enable_taxon_details_button}}<a link="{{url \'TaxonProfiles\' taxon.taxonSource taxon.nameUuid taxon.taxonNuid taxon.taxonLatname}}" class="tap"><img src="{{themeFolder}}img/taxon_detail.svg" /></a>&nbsp;{{/if}}{{#if options.enable_wikipedia_button}}<a href="https://{{language }}.m.wikipedia.org/wiki/{{taxon.taxonLatname}}" target="_blank"><img src="{{themeFolder}}img/wikipedia_button.svg" /></a>&nbsp;{{/if}}{{#if options.enable_observation_button}}<a link="{{url \'new_observation\' options.enable_observation_button.uuid }}" kwargs=\'{"taxonSource":"{{taxon.taxonSource}}","nameUuid":"{{taxon.nameUuid}}","taxonLatname":"{{taxon.taxonLatname}}","taxonNuid":"{{taxon.taxonNuid}}"}\' class="tap"><img src="{{themeFolder}}img/observation.svg" /></a>{{/if}}</div></div>',

	create : function(nature_guide){
		var self = this; //Object.create(this);

		self.nature_guide = nature_guide;

		// mode: overview or list
		// overview and list need different namesearch
		self.mode = document.getElementById("NatureGuidePage").getAttribute("data-mode");
		if (self.mode != "overview" && self.mode != "list"){
			throw new Error("[NatureGuide.js] unsupported mode: " + self.mode);
		}

		// a list of taxa
		// - DOMElements for list, objects for overview
		self.taxa = [];

		// automatically detected and filled
		self.available_filtertypes = [];

		self.taxonfilters = null;
		self.active_taxonfilter = null;

		if (self.mode == "list"){
			self.load_domtaxa();
		}
		else {
			self.load_objecttaxa(nature_guide.taxa);
		}

		// taxonfilters
		if (nature_guide.options.enable_taxonfilters == true){
			self.load_taxonfilters(nature_guide.compiled_taxonfilters);
			self.activate_filterbuttons("Taxonfilter");
		}

		// Alphabetfilter
		self.activate_filterbuttons("Alphabetfilter");

		// name search is always enabled
		self.activate_namesearch();

		self.result_template = Handlebars.compile(self.overview_search_template);

		return self;
	},

	hide_all_filters : function(){

		var self = this;

		for (var f=0; f<self.available_filtertypes.length; f++){
			var filtertype = self.available_filtertypes[f];
			self.hide_filter(document.getElementById("" + filtertype + "Container"));
		}
	},

	show_filter : function(element){
		element.classList.remove("inback");
		element.classList.remove("closed");
	},
	
	hide_filter : function(element){
		element.classList.add("closed");
			
		setTimeout(function(){
			element.classList.add("inback");
		}, 400);
	},
	toggle_filter : function(toggle_filtertype){
		var self = this;

		var filterelement = document.getElementById("" + toggle_filtertype + "Container");

		if (filterelement.classList.contains("inback")){
			self.show_filter(filterelement);
		}
		else {
			self.hide_filter(filterelement);
		}

		for (var f=0; f<self.available_filtertypes.length; f++){
			var filtertype = self.available_filtertypes[f];
			
			if (toggle_filtertype != filtertype){
				self.hide_filter(document.getElementById("" + filtertype + "Container"));
			}
		}
	},

	// initialzation
	load_domtaxa : function(){
		// mode: list
		var self = this;
		self.taxa = document.getElementById("NatureGuideTaxa").querySelectorAll(".natureguide-item");
	},
	load_objecttaxa : function(taxa){
		// mode: overview
		var self = this;
		self.taxa = taxa;
	},
	load_taxonfilters : function(taxonfilters){
		var self = NatureGuide;
		self.taxonfilters = taxonfilters;
	},

	activate_filterbuttons : function(filtertype){

		var self = this;

		var toggler = document.getElementById("Active" + filtertype);

		if (toggler != null){

			self.available_filtertypes.push(filtertype);

			var active_filter_hammer = new Hammer(toggler);
			active_filter_hammer.on("tap", function(event){
				var filtertype = event.target.getAttribute("data-filtertype");
				NatureGuide.toggle_filter(filtertype);
			});

			var filter_container = document.getElementById("" + filtertype + "Container");

			var hammertime = new Hammer(filter_container);
			hammertime.on("tap", function(event){
				var element = event.target;
				var counter = 4;

				while (counter > 0){

					if (element.classList.contains("natureguide-filter")){
						counter = 0;
						var filtertype = element.getAttribute("data-filtertype");
						NatureGuide.activate_filter(filtertype, element);
					}
					else {
						counter--;
						element = element.parentElement;
					}
				}
			});

		}
		else {
			console.log("[NatureGuide.js] failed to activate filters: " + filtertype);
		}

	},

	activate_filter : function(filtertype, element){
		var self = NatureGuide;

		// if there is a special fn use it
		// currently, there is no default filter method
		var fn_name = "activate_" + filtertype;
		if (self.hasOwnProperty(fn_name)){
			self[fn_name](element);
		}

		self.adjust_indicators(element);

	},

	set_indicator : function(element){
		// adjust one indicator based on the filterDomElement of class natureguide-filter
		var filtertype = element.getAttribute("data-filtertype");

		var indicator = document.getElementById("Active" + filtertype);

		if (element.hasAttribute("data-image")){
			var imageUrl = element.getAttribute("data-image");
			indicator.style.backgroundImage = "url('" + imageUrl + "')";
		}

		if (element.hasAttribute("data-text")){
			indicator.textContent = element.getAttribute("data-text").substring(0,3);
		}
		else {
			indicator.innerHTML = "&nbsp;";
		}

	},

	adjust_indicators : function(element){

		var self = this;

		self.set_indicator(element);

		var filtertype = element.getAttribute("data-filtertype");
		// reset all other indicators
		for (var f=0; f<self.available_filtertypes.length; f++){
			var reset_filtertype = self.available_filtertypes[f];
			
			if (reset_filtertype != filtertype){
				var no_filter = document.getElementById("" + reset_filtertype + "NoFilter");
				self.set_indicator(no_filter);
			}
		}

	},

	activate_Alphabetfilter : function(element){

		var self = this;

		var letter = element.getAttribute("data-letter");

		if (letter == "no_filter"){
			for (var t=0; t<self.taxa.length; t++){
				var taxon = self.taxa[t];
				taxon.style.display="";
			}
		}
		else {
			for (var t=0; t<self.taxa.length; t++){
				var taxon = self.taxa[t];
				var latname = taxon.getAttribute("data-taxon-latname");
				var vernacular = taxon.getAttribute("data-taxon-vernacular");
				if (latname.toUpperCase().substring(0,1) == letter.toUpperCase() || vernacular.toUpperCase().substring(0,1) == letter.toUpperCase()){
					taxon.style.display="";
				}
				else {
					taxon.style.display="none";
				}
			}
		}
	},

	activate_namesearch : function(self){
		// make the search input work
		var input = document.getElementById("TaxonNameSearch");
		input.addEventListener("keyup", function(event){
			var searchtext = event.target.value;
			NatureGuide.name_search(searchtext);
		});
	},

	insert_search_result : function(insert_at, taxon){		
		var self = NatureGuide;

		var context = {
			"taxon" : taxon,
			"options" : self.nature_guide.options
		};

		document.getElementById("NameSearchResults").insertAdjacentHTML(insert_at, self.result_template(context));

	},

	// maybe namesearch should only search within the visible taxa ?
	name_search : function(searchtext){
		var self = this;

		var searchtext = searchtext.trim().toLowerCase();

		var result_count = 0;

		if (self.mode == "overview"){
			document.getElementById("NameSearchResults").textContent = "";
		}
		
		if (searchtext.length >= 1){

			// only applies for mode overvie

			// reset other filter indicators
			if (self.available_filtertypes.length){
				var firstfilter = self.available_filtertypes[0];
				self.adjust_indicators(document.getElementById("" + firstfilter + "NoFilter"));
				self.hide_all_filters();
			}

			for (var c=0; c<self.taxa.length; c++){

				if (self.mode == "overview" && result_count >= 10){
					break;
				}

				var taxon = self.taxa[c];

				// first, check if it covered by the current taxonfilter
				// currently filters cannot be combined - all other filters are reset. this behaviour is open for debate
				/*if (self.active_taxonfilter != null){
					var isVisible = self.check_taxonfilter(taxon);
					if (isVisible == false) {
						continue;
					}
				}*/

				if (self.mode == "list"){
					var latname = taxon.getAttribute("data-taxon-latname").toLowerCase();
					var vernacular = taxon.getAttribute("data-taxon-vernacular").toLowerCase();
				}
				else {
					var latname = taxon.taxonLatname.toLowerCase();
					var vernacular = taxon.taxon_vernacular.toLowerCase();
				}

				if (searchtext.length == 1){
					
					if (latname.indexOf(searchtext) == 0 || vernacular.indexOf(searchtext) == 0){

						result_count++;

						if (self.mode == "list"){
							taxon.style.display = "";
						}
						else {
							self.insert_search_result("afterbegin", taxon);
						}
					}
					else {
						if (self.mode == "list"){
							taxon.style.display = "none";
						}
						else {
							continue;
						}
					}
					
				}
				else {
					
					if (latname.indexOf(searchtext) >=0 || vernacular.indexOf(searchtext) >= 0){

						result_count++;

						if (self.mode == "list") {
							taxon.style.display = "";
						}
						else {
							// overview search
							var insert_at = "beforeend";
							if (latname.indexOf(searchtext) == 0 || vernacular.indexOf(searchtext) == 0){
								insert_at = "afterbegin";
							}
							self.insert_search_result(insert_at, taxon);
						}
					}
					else {
						if (self.mode == "list") {
							taxon.style.display = "none";
						}
						else {
							continue;
						}
					}
				}
			}
		}
		else {
			if (self.mode == "list"){
				for (var c=0; c<self.taxa.length; c++){
					var taxon = self.taxa[c];

					/*if (self.active_taxonfilter != null){
						var isVisible = self.check_taxonfilter(taxon);
						if (isVisible == false) {
							continue;
						}
					}*/
				
					if (taxon.style.display == "none"){
						taxon.style.display = "";
					}
				}
			}
			else {
				document.getElementById("NameSearchResults").textContent = "";
			}
		}
	},

	check_taxonfilter : function(taxon){
		// checks against self.active_taxonfilter
		var self = this;

		var taxonSource = taxon.getAttribute("data-taxon-source");

		var isVisible = false;

		// self.active_taxonfilter is a dict with taxonomic sources as key

		if (taxonSource in self.active_taxonfilter){
		
			var nuids = self.active_taxonfilter[taxonSource];

			var taxonNuid = taxon.getAttribute("data-taxon-nuid");

			for (var n=0; n<nuids.length; n++){
				var nuid = nuids[n];
				if (taxonNuid.indexOf(nuid) == 0){
					isVisible = true;
					break;
				}
			}
		}

		return isVisible;

	},

	activate_Taxonfilter : function(element){

		var self = NatureGuide;

		// during build it might be null
		if (self.taxonfilters != null){

			var latname = element.getAttribute("data-latname");

			if (latname == "no_filter"){

				self.active_taxonfilter = null;

				for (var t=0; t<self.taxa.length; t++){
					var taxon = self.taxa[t];
					taxon.style.display="";
				}
			}

			else if (self.taxonfilters.hasOwnProperty(latname)){

				self.active_taxonfilter = self.taxonfilters[latname];
				
				for (var t=0; t<self.taxa.length; t++){
					var taxon = self.taxa[t];

					var isVisible = self.check_taxonfilter(taxon);
					
					if (isVisible == true){
						if (taxon.style.display != ""){
							taxon.style.display = "";
						}
					}
					else {
						if (taxon.style.display != "none"){
							taxon.style.display = "none";
						}
					}
				}
			}

		}

	}
};
