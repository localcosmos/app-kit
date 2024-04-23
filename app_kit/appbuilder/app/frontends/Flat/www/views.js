"use strict";

var MainMenuButton = {
	create : function(button_name, action, uuid){

		var uuid = uuid || null;

		var button = {
			button_name : button_name,
			action : action,
			uuid : uuid
		};

		return button;
	}
};


function _get_categories(callback){

	var categories = [];

	if ("NatureGuide" in app_features){

		let nature_guides = app_features.NatureGuide.list;
		let has_submenu = nature_guides.length > 1 ? true : false;

		let buttons = [];

		for (let k=0; k<nature_guides.length; k++){
			let nature_guide = nature_guides[k];
			let button = MainMenuButton.create(nature_guide.name, "nature-guide/" + nature_guide.uuid + "/", null);
			buttons.push(button);
		} 

		let category = {
			"submenu_id" : "identification",
			"category_name" : _("Nature Guides"),
			"buttons" : buttons,
			"has_submenu" : has_submenu
		}; 


		categories.push(category);
	}
	
	if ("GenericForm" in app_features){
		
		// can have buttonmatrices and/or observation forms
		// always multiple: at least my observations and new observations
		// forms are listed only using "new observation"

		let default_observation_form_uuid = app_features.GenericForm["default"]["uuid"];

		let new_observation_button = MainMenuButton.create(_('NewObservation'), "observation/new/" + default_observation_form_uuid + "/", null);
		let my_observations_button = MainMenuButton.create(_('MyObservations'), "my-observations/", null);

		let all_observations_button = MainMenuButton.create(_('AllObservations'), "all-observations/", null);

		let buttons = [new_observation_button, my_observations_button, all_observations_button];

		// not every app has a button matrix - check this
		if (app_features.hasOwnProperty("ButtonMatrix") && app_features.ButtonMatrix.hasOwnProperty("default")){
			let default_buttonmatrix_uuid = app_features.ButtonMatrix["default"]["uuid"];
			let button_matrices_button = MainMenuButton.create(_('QuickLogging'), "quick-logging/" + default_buttonmatrix_uuid + "/", null);
			buttons.push(button_matrices_button);
		}
		
		let category = {
			"submenu_id" : "observation",
			"category_name" : _("Observations"),
			"buttons" : buttons,
			"has_submenu" : true
		};
		
		categories.push(category);
	
	}

	if ("Map" in app_features){
		let has_submenu = app_features.Map.length > 1 ? true : false;

		let buttons = [];
		let map = app_features.Map.list[0];
		let map_button = MainMenuButton.create(map.name, "map/" + map.uuid + "/", null);
		buttons.push(map_button);

		let category = {
			"submenu_id" : "maps",
			"category_name" : _("Maps"),
			"buttons" : buttons,
			"has_submenu" : has_submenu
		};
	
		categories.push(category);
	}
	
	
	if ("Glossary" in app_features){
	
		let glossary = app_features.Glossary;
	
		let glossary_button = MainMenuButton.create(glossary.name, "glossary/" + glossary.uuid + "/", null);
	
		let glossary_category = {
			"submenu_id" : "glossary",
			"category_name" : _("Glossary"),
			"buttons" : [glossary_button],
			"has_submenu" : false
		};
		
		categories.push(glossary_category)
	
	}
	
	if ("TaxonProfiles" in app_features) {
		let taxon_profiles = app_features.TaxonProfiles;
		
		let button_name = i18next.t('plainȵ' + taxon_profiles.name);
	
		let taxon_profiles_button = MainMenuButton.create(button_name, "taxon-profiles-registry/", null);
	
		let taxon_profiles_category = {
			"submenu_id" : "taxon_profiles",
			"category_name" : _("Taxon Profiles"),
			"buttons" : [taxon_profiles_button],
			"has_submenu" : false
		};
		
		categories.push(taxon_profiles_category)
	}

	/*
	* there is only one FactSheets Feature which contains the fact sheets
	* {"uuid": "aa4e46fb-474a-4126-b0c5-6a7fdcce49e1", "version": 1, "options": {}, "globalOptions": {}, "name": "Fact Sheets",
	*	"factSheets": {"1": {
	*		"taxonomic_restriction": [{"taxonSource": "taxonomy.sources.col", "taxonLatname": "Plantae", "taxonAuthor": "", "nameUuid": "151d41f5-5941-4169-b77b-175ab0876ca6", "taxonNuid": "006", "restrictionType": "exists"}],
	*		"localized": {"de": {"path": "1-baume/de.html", "slug": "baume"}}
			}
	*	},
	*	"localizedSlugs": {"baume": 1}}
	*/
	if ("FactSheets" in app_features){

		let factSheets_path = app_features.FactSheets.list[0].path;

		ajax.GET(factSheets_path, {}, function(content){

			let factSheets = JSON.parse(content); //JSON.parse(atob(content));

			let buttons = [];

			for (let fact_sheet_id in factSheets["factSheets"]){
				
				let fact_sheet = factSheets["factSheets"][fact_sheet_id];
				let localized_title = i18next.t('plainȵ' + fact_sheet.title);
				let localized_slug = fact_sheet["localized"][app.language]["slug"];

				let button = MainMenuButton.create(localized_title, "fact-sheet/" + localized_slug + "/", null);
				buttons.push(button);
			}
			
			
			let has_submenu = buttons.length > 1 ? true : false;

			let category = {
				"submenu_id" : "factsheets",
				"category_name" : _("Fact Sheets"),
				"buttons" : buttons,
				"has_submenu" : has_submenu
			}; 

			categories.push(category);	


			callback(categories);

		});

	}
	else {

		callback(categories);
	}
};


var load_footer_sponsors = function(){

	function remove_outer_container(){
		var outer_container = document.getElementById("footer-sponsors-container");
		if (outer_container != null){
			outer_container.parentElement.removeChild(outer_container);
		}
	}

	if (settings.SPONSORS_DISABLED != false){
		var sponsors = mango.storage.getItem("sponsors");

		if (sponsors != null){

			sponsors = JSON.parse(sponsors);

			if (sponsors.hasOwnProperty("main_sponsors") && sponsors.main_sponsors.length){

				var context = {
					"main_sponsors" : sponsors.main_sponsors
				};

				default_renderer.render("templates/footer_sponsors.html", context, function(template_html){
					var sponsors_container = document.getElementById("footer-sponsors");
					sponsors_container.insertAdjacentHTML("afterbegin", template_html);
				});

			}
			else {
				remove_outer_container();
			}
		}
		else {
			remove_outer_container();
		}
	}
	else {
		remove_outer_container();
	}
}


var load_sidemenu = function(){

	_get_categories(function(categories){

		var sponsors = false;
		if (settings.SPONSORS_DISABLED != false){
			sponsors = true;
		}

		var request = HttpRequest.create();
		request.user = mango_session.user;

		if (listeners.hasOwnProperty("get_sidemenu_context")){
			var context = listeners.get_sidemenu_context();
		}
		else {
			var context = {};
		}

		context["categories"] = categories
		context["request"] = request
		context["preview"] = settings.PREVIEW
		context["app_name"] = settings.NAME
		context["sponsors"] = sponsors

		default_renderer.render("themes/" + settings.THEME + "/templates/sidemenu.html", context, function(template_html){
			var container = document.getElementById("Sidemenu");
			Pagemanager._insert(container, template_html, [], {});
			OnlineContentMixin.load_online_content(container);
		});

	});
};


var Home = View(TemplateView, {
	identifier : "Home",
	save_state_on_exit : false,
	template_name : "themes/" + settings.THEME + "/templates/home.html",
	async_context : true,

	get_context_data : function(self, kwargs, callback){

		//var context = Home.super().get_context_data(self, kwargs);

		Home.super().get_context_data(self, kwargs, function(context){

			_get_categories(function(categories){
				context["categories"] = categories;				
				callback(context);
			});
		

		});
	}
});


var LegalNotice = View(TemplateView, {
	identifier : "LegalNotice",

	template_name : "themes/" + settings.THEME + "/templates/legalNotice.html",

	async_context : true,

	get_context_data : function (self, kwargs, callback){

		ajax.getJSON("legalNotice.json", {}, function(legalNotice){
			var context = {
				"legalNotice" : legalNotice
			};

			callback(context);

		});		

	}
});

var PrivacyStatement = View(RemoteView, {

	"identifier" : "PrivacyStatement",
	"template_name" : "themes/" + settings.THEME + "/templates/privacy_statement.html",

	"needs_internet" : true,

	get_api_url : function(self){
		var url = "app/" + settings.APP_UUID + "/privacy-statement/";
		return url;
	},

	get_api_url_params : function(self){
		var params = {};

		if (window.location.pathname.indexOf("review") >= 0){
			params["review"] = 1;
		}

		return params;
	}
})


var Sponsors = View(TemplateView, {
	identifier : "Sponsors",

	template_name : "templates/sponsorpage_sponsors.html",

	get_context_data : function(self, kwargs){

		var sponsors = mango.storage.getItem("sponsors");
		if (sponsors != null){
			sponsors = JSON.parse(sponsors);
		}
		var context = {
			"sponsors" : sponsors
		};

		return context;
	}
});

var MainMenuSubmenu = View(OverlayView, {

	identifier : "MainMenuSubmenu",

	open : function(self){
		
		self.menu.classList.remove("submenu-hidden");
		self.btn.classList.add("active");
		MainMenuSubmenu.super().open(self);
	},
	
	close : function(){
		var self = MainMenuSubmenu;
		self.menu.classList.add("submenu-hidden");
		self.btn.classList.remove("active");
		MainMenuSubmenu.super().close();
	},

	toggle : function(self, request, args, kwargs){

		if (typeof self == "undefined" || self == null){
			// do not use Object.create(this)
			var self = MainMenuSubmenu;
		}

		self.menu = document.getElementById(kwargs["submenu_id"]);
		self.btn = kwargs["currentTarget"];

		if (self.menu.classList.contains("submenu-hidden")){
			self.open(self);
		}
		else {
			self.close();
		}

	}

});


var TaxonProfiles = View(TemplateView, {
	identifier : "TaxonProfiles",
	template_name : "themes/" + settings.THEME + "/templates/taxon_profile.html",
	get : function(self, request, args, kwargs){

		var context = self.get_context_data(self, kwargs);
		context["options"] = app_features["TaxonProfiles"]["options"];
		context["wikipedia_url"] = BackboneTaxonomy.get_wikipedia_url(kwargs["taxonLatname"]);

		BackboneTaxonomy.get_taxon_profile(kwargs["taxonSource"], kwargs["nameUuid"], function(taxon_profile){

			if (taxon_profile == null){
				// use minimal taxonomic information
				context["taxon_profile"] = kwargs;
			}
			else {
				context["taxon_profile"] = taxon_profile;
			}

			self.render_to_response(self, context);

		});
	},

	post_render : function(self, args, kwargs){
		const show_longtext_buttons = document.getElementsByClassName('show-longtext');
		for (let b=0; b<show_longtext_buttons.length; b++){
			let button = show_longtext_buttons[b];
			button.addEventListener("click", function(event){
				let text_type = event.currentTarget.getAttribute("data-text-type");
				let hide = document.getElementById("" + text_type + ":short");
				let show = document.getElementById("" + text_type + ":long");

				hide.style.display = "none";
				show.style.display = "";
			});
		}

		const show_shorttext_buttons = document.getElementsByClassName('show-shorttext');
		for (let b=0; b<show_shorttext_buttons.length; b++){
			let button = show_shorttext_buttons[b];
			button.addEventListener("click", function(event){
				let text_type = event.currentTarget.getAttribute("data-text-type");
				let show = document.getElementById("" + text_type + ":short");
				let hide = document.getElementById("" + text_type + ":long");

				hide.style.display = "none";
				show.style.display = "";
			});
		}
	}
});


var FundingPartners = View(TemplateView, {

	identifier : "FundingPartners",

	template_name : "themes/" + settings.THEME + "/templates/funding_partners.html",

	get_context_data : function(self, kwargs){

		var context = FundingPartners.super().get_context_data(self, kwargs);

		var images = ["funding_partner_1", "funding_partner_2", "funding_partner_3"];

		var funding_partners = [];

		for (let k=0; k<images.length; k++){
			let key = images[k];
			if (typeof(theme_images) == "object" && theme_images.hasOwnProperty(key)){
				funding_partners.push(theme_images[key]);
			}
		}

		context["funding_partners"] = funding_partners;

		return context;
	}

});


var OccurrenceMap = View(TemplateView, {
	identifier : "OccurrenceMap",
	template_name : "themes/" + settings.THEME + "/templates/occurrence_map.html",

	post_finished : function(args, kwargs){
		var self = this;
		window.scrollTo(0,0);

		var gbifNubkey = kwargs["gbifNubkey"];

		var layerSources = {

			"osm": L.tileLayer("https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
				{
					attribution: "&copy; OpenStreetMap, Tiles courtesy of Humanitarian OpenStreetMap Team",
					subdomains: "ab"
				}),

			"gbif": L.tileLayer('https://api.gbif.org/v1/map/density/tile?x={x}&y={y}&z={z}&type=TAXON&key=' + gbifNubkey + '&layer=OBS_NO_YEAR&layer=SP_NO_YEAR&layer=OTH_NO_YEAR&layer=OBS_1900_1910&layer=SP_1900_1910&layer=OTH_1900_1910&layer=OBS_1910_1920&layer=SP_1910_1920&layer=OTH_1910_1920&layer=OBS_1920_1930&layer=SP_1920_1930&layer=OTH_1920_1930&layer=OBS_1930_1940&layer=SP_1930_1940&layer=OTH_1930_1940&layer=OBS_1940_1950&layer=SP_1940_1950&layer=OTH_1940_1950&layer=OBS_1950_1960&layer=SP_1950_1960&layer=OTH_1950_1960&layer=OBS_1960_1970&layer=SP_1960_1970&layer=OTH_1960_1970&layer=OBS_1970_1980&layer=SP_1970_1980&layer=OTH_1970_1980&layer=OBS_1980_1990&layer=SP_1980_1990&layer=OTH_1980_1990&layer=OBS_1990_2000&layer=SP_1990_2000&layer=OTH_1990_2000&layer=OBS_2000_2010&layer=SP_2000_2010&layer=OTH_2000_2010&layer=OBS_2010_2020&layer=SP_2010_2020&layer=OTH_2010_2020&layer=LIVING&layer=FOSSIL&palette=yellows_reds&resolution=16',
				{
					attribution: '&copy; GBIF'
				})
		};

		var occurrenceMap = L.map("occurrenceMap", {
			center: [55.83548, 8.71964],
			zoom: 5,
			scrollWheelZoom: false,
			layers: [
				  	layerSources["osm"],
					layerSources["gbif"]
			]
		});

		occurrenceMap.attributionControl.setPrefix("Leaflet");

	}
});



// helper
function cloneAsObject(obj) {
    if (obj === null || !(obj instanceof Object)) {
        return obj;
    }
    var temp = (obj instanceof Array) ? [] : {};
    // ReSharper disable once MissingHasOwnPropertyInForeach
    for (var key in obj) {
        temp[key] = cloneAsObject(obj[key]);
    }
    return temp;
}


/*
* MAPS
*/
var map_markers = {

	"taxonomy.sources.col" : {
		"001008002001" : "anycluster/images/markers/Anura.png",
		"001003007004" : "anycluster/images/markers/Coleoptera.png",
		"00100300700d" : "anycluster/images/markers/Lepidoptera.png",
		"00100300700j" : "anycluster/images/markers/Odonata.png",
		"00100800a" : "anycluster/images/markers/Mammalia.png",
		"001003007" : "anycluster/images/markers/Insecta.png",
		"001008005" : "anycluster/images/markers/Aves.png",
		"001003001" : "anycluster/images/markers/Arachnida.png",
		"001008002" : "anycluster/images/markers/Amphibia.png",
		"00100l" : "anycluster/images/markers/Mollusca.png",
		"001008" : "anycluster/images/markers/Chordata.png",
		"001003" : "anycluster/images/markers/Arthropoda.png",
		"001" : "anycluster/images/markers/Animalia.png",
		"006" : "anycluster/images/markers/Plantae.png",
		"005" : "anycluster/images/markers/Fungi.png"
	}
};


var map_control = {

	add_ownpos_button : function(self){
		self.geolocation_layer = new L.FeatureGroup();
		self.geolocation_layer.addTo(self.map);

		document.getElementById("leaflet-ownpos").addEventListener("click", function(event){
			event.preventDefault();
			event.stopPropagation();

			let geolocation_options = {
				"enableHighAccuracy": true
			};

			navigator.geolocation.getCurrentPosition(function(position){
				self.show_current_position_marker(self, position.coords.latitude, position.coords.longitude, position.coords.accuracy);
			}, function(){
				alert("geolocation not available");
			}, geolocation_options);
		});
	},

	show_current_position_marker : function(self, lat, lng, accuracy){

		self.geolocation_layer.clearLayers();
		
		var ownposIcon = L.icon({
			iconUrl: 'img/map/ownpos.svg',
			iconSize: [26, 26],
			iconAnchor: [13, 13]
		});

		var ownpos_marker = L.marker([lat, lng], {icon: ownposIcon, interactive: false});
		ownpos_marker.addTo(self.geolocation_layer);

		// show an accuracy radius
		L.circle([lat,lng], accuracy).addTo(self.geolocation_layer);

		self.map.panTo([lat, lng]);

	}

};

var MapView = View(TemplateView, {

	identifier : "MapView",

	template_name : "themes/" + settings.THEME + "/templates/observations_map.html",
	marker_popup_template_name : "themes/" + settings.THEME + "/templates/marker_popup.html",

	"needs_internet" : true,

	marker_popup_template : null, // loaded only once

	fallback_initial_position : {
		"latitude" : 30,
		"longitude" : 30,
		"zoom" : 4
	},

	get_context_data: function(self, kwargs){
		var context = MapView.super().get_context_data(self, kwargs);
		return context;
	},

	post_finished : function(args, kwargs){
		var self = this;

		var uuid = kwargs["map_uuid"];

		self._load_marker_popup_template(function(){

			self._get_map(uuid, function(map){
				self._load_map(map);
			});
		});

	},

	_get_map : function(uuid, callback){
		var self = this;
		var url = app_features.Map.lookup[uuid];

		ajax.GET(url, {}, function(content){

			var map = JSON.parse(content); //JSON.parse(atob(content));
			callback(map);				

		});
				
	},

	_load_marker_popup_template : function(callback){

		var self = MapView;

		if (self.marker_popup_template == null){
			ajax.GET(self.marker_popup_template_name, {}, function(template_str){
				self.marker_popup_template = Handlebars.compile(template_str);
				callback();
			});
		}
		else {
			callback();
		}
	},

	_get_marker : function(cluster){

		var pinimg = cluster["pinimg"];
		var taxonSource = cluster["taxonSource"]

		var pin_url = "anycluster/images/markers/marker_unknown.png";

		for (var nuid in map_markers[taxonSource]){
			if (pinimg.indexOf(nuid) == 0){
				pin_url = map_markers[taxonSource][nuid];
				break;
			}
		}
		return pin_url;

	},

	_load_map : function(map){
		
		if (MapView.hasOwnProperty("anycluster")){
			try {
				MapView.anycluster.map.remove();
			}
			catch (e){};
		}

		var mapdiv = document.getElementById("observations_map");

		// remove old map elements if any
		for (let c=0; c<mapdiv.children.length; c++){
			let node = mapdiv.children[c];
			if (node.classList.contains("ownpos-container")){
				continue;
			}

			mapdiv.removeChild(node);
		}

		var initial_zoom = map.options.initial_zoom || MapView.fallback_initial_position.zoom;
		var initial_latitude = map.options.initial_latitude || null;
		var initial_longitude = map.options.initial_longitude || null;

		if (initial_latitude == null || initial_longitude == null){

			if (AppGeolocation.last_position != null && AppGeolocation.last_position.hasOwnProperty("coords")){
				initial_latitude = AppGeolocation.last_position.coords.latitude;
				initial_longitude = AppGeolocation.last_position.coords.longitude;
				initial_zoom = 15;
			}
			else {
				initial_latitude = MapView.fallback_initial_position.latitude;
				initial_longitude = MapView.fallback_initial_position.longitude;
			}

		}


		var anycluster_settings = {
			"mobile" : true,
			"mapType" : "leaflet",
			"gridSize" : 256,
			"clusterMethod" : "kmeans",
			"zoom" : initial_zoom,
			"minZoom" : 4,
			"center" : [initial_latitude, initial_longitude],
			"baseURL" : settings.API_URL + 'anycluster/',
			"markerFolder": "anycluster/images/",
			"returnFormat" : "json",
			"singlePinImages": MapView._get_marker,
			"onFinalClick" : function(mapmarker, data){
			
				var timestamp = new Date().getTime();

				var popup_id = "marker-popup" + timestamp.toString();

				var context = {
					"datasets":data,
					"popup_id" : popup_id
				};

				var html = MapView.marker_popup_template(context);
	
				mapmarker.bindPopup(html).openPopup();

				// attach tap listener to popup
				var hammertime = new Hammer(document.getElementById(popup_id), {});
				hammertime.on("tap", function(event) {
					InteractionManager._input_worker(event, "tap");			
				});

				each(data, function(dataset, iterate){

					MapView._get_dataset_details(dataset.pk, function(details){

						if (details.thumbnail){
							var image_container = document.getElementById("mapmarker-popup-images-" + dataset.pk);
							if (image_container != null && typeof(image_container) != "undefined"){
								var image = document.createElement("img");
								image.setAttribute("width", "50");
								image.setAttribute("height", "auto");
								image.src = details.thumbnail;
								image_container.appendChild(image);
							}
						}
						iterate();
					});
				});
					
			}
		};

		MapView.anycluster = new Anycluster("observations_map", anycluster_settings);
		MapView.map = MapView.anycluster.map;
		MapView.add_ownpos_button(MapView);

		MapView.map.attributionControl.setPrefix("Leaflet");

	},

	_get_dataset_details : function(dataset_id, callback){
		var url = "" + settings.REMOTEDB_API_URL + "Dataset/get.json";
		var data = {
			"id" : dataset_id
		};

		mango_remotedb_api.perform_request(url, "POST", "JSON", data, callback, function(err){
		});
	},

	add_ownpos_button : map_control.add_ownpos_button,

	show_current_position_marker : map_control.show_current_position_marker
});


var ObservationDetailView = View(TemplateView, {
	identifier : "ObservationDetailView",

	template_name : "themes/" + settings.THEME + "/templates/observation_detail.html",

	image_template_name : "themes/" + settings.THEME + "/templates/observation_detail_image.html",

	async_context : true,
	image_template: null,

	_load_image_template : function(callback){

		var self = ObservationDetailView;

		if (self.image_template == null){
			ajax.GET(self.image_template_name, {}, function(template_str){
				self.image_template = Handlebars.compile(template_str);
				callback();
			});
		}
		else {
			callback();
		}
	},

	get_context_data : function(self, kwargs, callback){

		Dataset.remote_objects.get({"id":self.kwargs["pk"]}, function(dataset){

			var observation_form = dataset.data.dataset.observation_form;
			var reported_values = dataset.data.dataset.reported_values;

			var recorded_data = [];

			for (let f=0; f<observation_form.fields.length; f++){
				var field = observation_form.fields[f];

				var value = null;

				if (reported_values.hasOwnProperty(field.uuid)){
					value = reported_values[field.uuid];					
				}
				
				var data = {
					"field" : field,
					"value" : value
				};

				recorded_data.push(data);
			}

			var context = {
				"dataset" : dataset,
				"observation_form" : observation_form,
				"recorded_data" : recorded_data
			};
			callback(context);

		}, function(err){
		});
	},

	_load_maps : function(){
		var maps = document.getElementsByClassName("observation-detail-map");

		for (let m=0; m<maps.length; m++){
			var map = maps[m];

			var latitude = map.getAttribute("data-latitude");
			var longitude = map.getAttribute("data-longitude");

			var layerSources = {
				"osm" : L.tileLayer('https://{s}.tile.openstreetmap.de/{z}/{x}/{y}.png',
					{
						attribution: 'Map data &copy; OpenStreetMap contributors',
						subdomains: 'ab',
						maxZoom: 20,
						maxNativeZoom: 18
					}),
		
				"satellite_tiles" : L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
					{
						attribution: 'Tiles &copy; Esri',
						maxZoom: 20,
						maxNativeZoom: 18
					}),
				"satellite_names": L.tileLayer('https://stamen-tiles.a.ssl.fastly.net/toner-labels/{z}/{x}/{y}.{ext}', {
					attribution: '&mdash; Map data &copy; OpenStreetMap',
					subdomains: 'abcd',
					minZoom: 0,
					maxNativeZoom: 18,
					maxZoom: 20,
					ext: 'png'
				})
			};

			var center = [latitude, longitude];
			var zoom = 15;

			var map = L.map(map.id, {
				center: center,
				zoom : zoom,
				maxZoom: 24,
				scrollWheelZoom: false
			});

			map.attributionControl.setPrefix("Leaflet");

			// add tile layers
			var satellite = L.layerGroup([layerSources.satellite_tiles, layerSources.satellite_names]);
		
			satellite.addTo(map);

			var baseLayers = {
				"Satellite" : satellite,
				"Streets" : layerSources["osm"]
			};

			L.control.layers(baseLayers, {}, {"position":"topright"}).addTo(map);

			L.control.scale({"position":"bottomright"}).addTo(map);

			L.marker([latitude, longitude]).addTo(map);

		}
	},

	_load_images : function(){
		var image_fields = document.getElementsByClassName("observation-detail-images");

		each(image_fields, function(image_field, iterate){

			var dataset_id = image_field.getAttribute("data-dataset-pk");
			var field_uuid = image_field.getAttribute("data-field-uuid");

			DatasetImages.remote_objects.filter({"dataset_id":dataset_id, "field_uuid" : field_uuid}).fetch(function(dataset_images){

				if (dataset_images.length == 0){
					image_field.textContent = i18next.t('plainȵ' + "no images found");
				}
				else {
					// remove spinner
					image_field.textContent = "";

					// load images
					for (let i=0; i<dataset_images.length; i++){
						let dataset_image = dataset_images[i];

						ObservationDetailView._add_dataset_image(image_field, dataset_image);
					}
				}

				iterate();

			});

		});
	},

	_add_dataset_image(image_field, dataset_image){

		var context = {
			"dataset_image" : dataset_image
		};

		var html = this.image_template(context);

		image_field.insertAdjacentHTML('beforeend', html);
	},

	post_finished : function(args, kwargs){

		var self = ObservationDetailView;

		self._load_image_template(function(){
			self._load_maps();
			self._load_images();
		});
	}

});


/*
* Observation Form
* 
*/
var ObservationView = View(FormView, {
	identifier : "ObservationView",
	template_name : "themes/" + settings.THEME + "/templates/observation.html",

	login_required : true,

	position_interval_id : null,
	position_interval_options : {
		"enableHighAccuracy" : true,
		"timeout" : 1 * 60 * 1000,
		"maximumAge" : 1 * 20 * 1000
	},

	get_form_class : function(self){

		// cache the form class to improve performance
		if (self.form_class === null){

			if (self.dataset == null){
				// use observation form delivered with the app
				self.form_class = window[self.form_uuid];
			}
			else {
				// create Observation form from dataset json, form might not be delivered with app
				self.form_class = createObservationFormFromJSON(self.dataset.data.dataset.observation_form);
			}
		}

		return self.form_class;
	},

	get_initial : function(self){

		var form = self.get_form_class(self);

		var timestamp_field_uuid = null;

		var initial = ObservationView.super().get_initial(self);

		var taxon_reference_uuid = null;

		// some fields might provide a default initial, eg datetimefield (with autofill)
		for (var name in form.fields){

			var field = form.fields[name];

			// add taxonomic restrictions if any
			// do it here to not iterate over fields twice
			if (field.taxonomic_restriction.length){
				self.fields_taxonomic_restrictions[field.uuid] = field.taxonomic_restriction;
			}

			if (field.role == "taxonomicReference"){
				taxon_reference_uuid = name;
			}

			if (!(initial.hasOwnProperty(name))){

				if (field.hasOwnProperty("default_initial")){
					initial[name] = field.default_initial();
				}
			}

		}

		// kwargs might supply a taxon
		if (self.kwargs.hasOwnProperty("taxonSource") && self.kwargs.hasOwnProperty("nameUuid") && self.kwargs.hasOwnProperty("taxonLatname") && self.kwargs.hasOwnProperty("taxonAuthor")){
			if (taxon_reference_uuid != null){

				var taxon = Taxon.create(self.kwargs.taxonSource, self.kwargs.nameUuid, self.kwargs.taxonLatname, self.kwargs.taxonAuthor, self.kwargs.taxonNuid);
				initial[taxon_reference_uuid] = taxon;
			}
		}

		// use dataset values
		if (self.dataset != null){

			var data = self.dataset.data.dataset.reported_values;

			for (var name in form.fields){
				
				if (data.hasOwnProperty(name)){
					initial[name] = data[name];
				}
				else if (self.dataset_images.hasOwnProperty(name)){
					// a fleximage instance
					initial[name] = self.dataset_images[name];
				}
			}
		}

		return initial;
	},

	get_context_data : function(self, kwargs){

		var context = ObservationView.super().get_context_data(self, kwargs);

		var available_forms = [];

		var form_list = app_features["GenericForm"]["list"];
		for (var f=0; f<form_list.length; f++){
			var generic_form = form_list[f];

			var entry = {
				"uuid" : generic_form["uuid"],
				"name" : generic_form["name"],
				"selected" : false
			};

			if (generic_form["uuid"] == self.form_uuid){
				entry["selected"] = true;
			}

			available_forms.push(entry);			

		}
		
		context["available_forms"] = available_forms;
		context["dataset"] = self.dataset;

		context["observation_form_uuid"] = self.form_uuid;

		return context;
	},

	_add_dataset_image(self, dataset_image){
		
		// make ImageViewer and thumbnails work
		var fleximage = dataset_image["image"];

		// add id for being able to delete
		fleximage.id = dataset_image.id;
		fleximage.model_route = self.model_route

		thumbnail_cache.add(fleximage.filename, "full_hd", fleximage["full_hd"]);


		if (self.dataset_images.hasOwnProperty(dataset_image.field_uuid) == false){
			self.dataset_images[dataset_image.field_uuid] = [];
		}
		self.dataset_images[dataset_image.field_uuid].push(fleximage);
	},

	_on_data_change : function(event){
		BackButtonManager.before_back = function(){
			HttpResponseRedirect(reverse("observation_view_save_warning"));
		}
	},

	_add_data_change_listener : function(self){
		var form = document.getElementById(self.form_uuid);

		var fields = form.querySelectorAll("input,select,textarea");

		for (let f=0; f<fields.length; f++){
			let field = fields[f];
			field.addEventListener("change", self._on_data_change);
		}

	},

	dispatch : function(self, request, args, kwargs){

		BackButtonManager.before_back = null;

		// important!
		var self = Object.create(this);

		var this_view = this;

		// on each dispatch, reset unsaved edits
		this_view.has_unsaved_edits = false;

		self.dataset = null;
		self.dataset_images = {};
		self.form_class = null; // caching the form class

		self.fields_taxonomic_restrictions = {};

		// which model route to go: objects or remote_objects
		// this only makes a difference on mobile. objects stores in the local database, remote_objects communicates with the server
		self.model_route = "objects";

		if (kwargs.hasOwnProperty("dataset_id")){

			self.storage_location = kwargs["storage_location"];
			if (self.storage_location == "RemoteDB") {
				self.model_route = "remote_objects";
			}
			
			Dataset[self.model_route].get({"id":kwargs["dataset_id"]}, function(dataset){
				self.dataset = dataset;

				// use the form from the dataset
				self.form_uuid = self.dataset.data.dataset.observation_form.uuid;

				// get dataset images
				DatasetImages[self.model_route].filter({"dataset_id":self.dataset.id}).fetch(function(dataset_images){

					for (let i=0; i<dataset_images.length; i++){
						let dataset_image = dataset_images[i];

						self._add_dataset_image(self, dataset_image);
						
					}

					// do not call this.super()
					this_view.super().dispatch(self, request, args, kwargs);
				});
				
			});
		}
		else {
			// create dataset -> self.model_route = "objects"
			self.form_uuid = kwargs["observation_form_uuid"] || app_features["GenericForm"]["default"]["uuid"];
			ObservationView.super().dispatch(self, request, args, kwargs);
		}

	},

	// form_valid contains async function
	// only show connecting to server modal if self.model_route == "remote_objects"
	form_valid_response : function(self, reported_files, context){

		// only save datasets which are not locked
		// there should occur an error message that the dataset is locked and was NOT saved
		if (self.dataset.is_locked === true){
			context["dataset"] = self.dataset;
			self.render_to_response(self, context);
		}
		else {

			// count the number of reported files
			var reported_file_count = 0;
			for (let field_name in reported_files){
				let filelist = reported_files[field_name];
				if (filelist != null && filelist.length > 0){
					reported_file_count = reported_file_count + filelist.length;
				}
			}

			var progress_parts = 1 + reported_file_count;

			if (self.model_route == "remote_objects"){
				var initial_message = _("connecting to server");
			}
			else {
				var initial_message = _("saving dataset to device");
			}

			modalProgress.start(_("Saving dataset"), initial_message, progress_parts);			

			self.dataset.save(self.dataset, function(dataset){

				if (progress_parts > 1){

					if (self.model_route == "objects" && device.platform != "browser"){
						modalProgress.manual_progress();
					}

					modalProgress.next_part(_("saving images"));

				}

				// update context #1
				context["dataset"] = dataset;
				self.dataset = dataset;

				// save form files, currently only images are supported
		
				each(reported_files, function(field_name, reported_filelist, iterate_formfield){

					each(reported_filelist, function(reported_file, iterate_file){

						// every reported file is a new file
						// existing files have their own delete button and are not inserted into form fields
						var image = DatasetImages.create({
							"dataset" : dataset,
							"field_uuid" : field_name,
							"image" : reported_file  // a fleximage
						});

						// set the correct storage_location for the newly attached image
						image.storage_location = self.storage_location;

						image.save(image, function(saved_image){
							self._add_dataset_image(self, saved_image);

							// progress has finished the part
							if (self.model_route == "objects" && device.platform != "browser"){
								modalProgress.manual_progress();
							}

							modalProgress.next_part(_("saving image"));

							iterate_file();
						});

					}, function(){
						// image will be in initial, remove from POST data
						delete self.request.POST[field_name];
						iterate_formfield();
					});
					
				}, function(){

					// update initial_kwargs
					if (self.initial_kwargs.hasOwnProperty("dataset_id") == false){
						self.initial_kwargs["dataset_id"] = dataset.id;
					}
				
					// re-init form

					context["form"] = self.get_form(self);

					modalProgress.finish();
					modalProgress._close();

					self.render_to_response(self, context);
				});
			});
		}
	},

	form_valid : function (self, form){
		var context = self.get_context_data(self, self.kwargs);
		context["form"] = form;
		context["success"] = true;

		// separate files from non-file data
		// files are being stored in a separate model
		var reported_data = {};
		var reported_files = {};

		var file_fieldClasses = ["FileField", "ImageField", "PictureField"];

		for (let field_uuid in form.cleaned_data){
			let data = form.cleaned_data[field_uuid];

			let field = form.fields[field_uuid];
			if (file_fieldClasses.indexOf(field.fieldClass) >= 0){
				reported_files[field_uuid] = data;
			}
			else {
				reported_data[field_uuid] = data;
			}
		}

		// save the observation
		if (self.dataset == null){

			var jsonbuilder = DatasetJSONbuilder.create();

			var dataset_data = {
				"client_id" : device.uuid
			};

			if (self.request.user.is_authenticated){
				dataset_data["user_id"] = self.request.user.uuid;
			}

			// set reported values
			jsonbuilder.set_reported_values(jsonbuilder, reported_data);

			// set the observationform
			jsonbuilder.set_observation_form(jsonbuilder, self.form_uuid, function(jsonbuilder){

				dataset_data["data"] = jsonbuilder.json;

				// store the dataset
				self.dataset = Dataset.create(dataset_data);

				// proceed
				self.form_valid_response(self, reported_files, context);

			});

		}
		else {
			// instantiate jsonbuilder with data from stored dataset
			var jsonbuilder = DatasetJSONbuilder.create(self.dataset.data);

			// use old client_id and client_platform for existing datasets
			form.cleaned_data["client_id"] = self.dataset.data.dataset.reported_values["client_id"];
			form.cleaned_data["client_platform"] = self.dataset.data.dataset.reported_values["client_platform"];
	
			jsonbuilder.set_reported_values(jsonbuilder, reported_data);
			
			// observation form currently cannot be changed for existing datasets

			// proceed
			self.form_valid_response(self, reported_files, context);

		}

	},

	post_finished : function(args, kwargs){
		var self = this;
		
		if (!kwargs.hasOwnProperty("dataset_id") || kwargs["dataset_id"] === null || typeof kwargs["dataset_id"] === "undefined"){

			var form_select = document.getElementById("observation-form-select");

			if (form_select != null && typeof form_select == "object" && form_select.tagName == "SELECT"){
				form_select.addEventListener("change", function(event){
					// reload the view and replace the state
					var kwargs = {
						"observation_form_uuid" : event.currentTarget.value
					};
					HttpResponseRedirect(reverse("new_observation", kwargs));
				});
			}

			// attach position listener only if the dataset has not been saved yet
			self.activate_position_fetching();
			
		}


		self._hide_success_indicator(5000);
	},

	activate_position_fetching : function(){
		var self = ObservationView;

		var position_inputs = Pagemanager.container.getElementsByClassName("mobilePositionInput");

		for (var i=0; i<position_inputs.length; i++){
			var verbose_input = position_inputs[i];
			var spinner = verbose_input.nextElementSibling;

			spinner.classList.remove("inactive");

			var json_input = document.getElementById(verbose_input.getAttribute("data-input-id"));

			json_input.addEventListener("manuallySelectedPosition", function(event){

				self._hide_success_indicator();

				if (ObservationView.position_interval_id != 0){
					navigator.geolocation.clearWatch(ObservationView.position_interval_id);
					ObservationView.position_interval_id = null;
					var spinner = document.getElementById("spinner_" + event.currentTarget.getAttribute("data-verbose-input-id"));
					spinner.classList.add("inactive");
				}
			});
		}

		// use only one watcher to fill all fields
		self.position_interval_id = navigator.geolocation.watchPosition(self.update_position, self.on_position_error, self.position_interval_options);
		window.addEventListener("pagechanged", ObservationView.on_page_leave);
	},

	_hide_success_indicator : function(timeout){
		var timeout = timeout || null;

		if (timeout != null){

			setTimeout(function(){

				var success_indicator = document.getElementById("observation-save-success");
				if (success_indicator != null){
			
					success_indicator.style.display = "none";
				}


			}, timeout);
		
		}
		else {
			var success_indicator = document.getElementById("observation-save-success");
			if (success_indicator != null){
		
				success_indicator.style.display = "none";
			}
		}

	},

	update_position : function(position){

		try {

			var position = cloneAsObject(position);

			// you cannot check position.hasOwnProperty(coords), which will always return false on android, even if there are coords
			var latitude = position.coords.latitude;
			var longitude = position.coords.longitude;

			PositionValidator.validate(latitude, longitude, function(errors){

				var position_inputs = Pagemanager.container.getElementsByClassName("mobilePositionInput");

				if (errors.length == 0){
					// valid position
					// receive a html5 position object

					var builder = GeoJSONbuilder.create();
					builder.load_html5_position(builder, position);
					var geojson = builder.as_json(builder);

					var value = JSON.stringify(geojson);

					var verbose_position = verbosify_position(geojson);

					for (let i=0; i<position_inputs.length; i++){

						var field = position_inputs[i];
						var input_id = field.getAttribute("data-input-id");
						var input = document.getElementById(input_id);
				
						// only update the position if it is more accurate
						field.value = verbose_position;
						input.value = value;

						// hide error container
						var error_container_id = "" + field.id + "_error";
						var error_container = document.getElementById(error_container_id);
						if (error_container != null){
							error_container.style.display = "none";
						}
					}
				}
				else {
					// invalid position
					for (let i=0; i<position_inputs.length; i++){
						var field = position_inputs[i];
						var input_id = field.getAttribute("data-input-id");
						var error_container_id = "" + field.id + "_error";
						var error_container = document.getElementById(error_container_id);
						if (error_container != null){
							error_container.textContent = errors[0];
							error_container.style.display = "";
						}
					}
				}
			});

			
		}
		catch(e){
			console.log("[Observation View] update_position: position error " + JSON.stringify(e));
		}
	},

	on_position_error : function(e){
		console.log("[Observation View] position error " + JSON.stringify(e) + ", code: " + e.code + ", message: " + e.message);
	},


	form_invalid : function(self, form, form_html){
		// make self.form available for post_render
        self.form = form;
        self.render_to_response(self, self.get_context_data(self, {"html":form_html}));
	},

	// manage taxonomically restricted fields
	post_render : function(self, args, kwargs){

		self._add_data_change_listener(self);

		// initially show/hide enable/disable fields depending on restrictions
		// default for taxonomically restriced fields is: hidden and disabled

		// taxonfield is a composed field with multiple inputs
		var taxonomicReference_field = document.getElementById("id_" + self.form_class.taxonomicReference + "_1");

		if (taxonomicReference_field.value){
			var taxon = JSON.parse(taxonomicReference_field.value);
			self._work_taxonomic_restrictions(self, taxon);
		}
		else {
			self._work_taxonomic_restrictions(self, null);
		}

		taxonomicReference_field.addEventListener("change", function(event){
			var value = event.target.value;
			if (value){
				var new_taxon = JSON.parse(value);
			}
			else {
				var new_taxon = null;
			}
			self._work_taxonomic_restrictions(self, new_taxon);
		});

		var form = document.getElementById(self.form_uuid);
		var picture_inputs = form.getElementsByClassName("multi-pictures-input");

		for (var p=0; p<picture_inputs.length; p++){
			var picture_input = picture_inputs[p];

			if (device.platform == "Android"){
				picture_input.addEventListener("click", function(event){
					ManagePictureInput.select_image(event);
				});
			}
			else {
				picture_input.addEventListener("change", function(event){
					ManagePictureInput.add_image(event)
				});
			}

			// if dataset edit and pictures are present: remove the required attribute from picture field
			if (self.dataset != null){
				if (self.dataset_images.hasOwnProperty(picture_input.name) && self.dataset_images[picture_input.name].length > 0){
					picture_input.required = false;
				}
			}

			// add data to _files if any, keep data if pictures have been added and form was invalid
			if (self.hasOwnProperty("form") && self.form.bound_fields.hasOwnProperty(picture_input.name)){
				var form_field = self.form.bound_fields[picture_input.name];
				var data = form_field.data(form_field);

				if (data instanceof Array == true){
					picture_input._files = data;
				}
			}
		}

	},

	_work_taxonomic_restrictions(self, taxon){
		var form = document.getElementById(self.form_uuid);
		
		var restricted_fields = form.getElementsByClassName("taxonomic_restriction");

		// iterate over restricted fields
		for (var f=0; f<restricted_fields.length; f++){
			var field_container = restricted_fields[f];
			var field_uuid = field_container.getAttribute("data-uuid");
			var restrictions = self.fields_taxonomic_restrictions[field_uuid];

			var enable_field = false;
			var require_field = parseInt(field_container.getAttribute("data-required"));

			// if there is no "exists" in restriction type, the field is visible for all taxa
			var restrictionTypes = [];
			
			for (var r=0; r<restrictions.length; r++){
				var restriction = restrictions[r];
				restrictionTypes.push(restriction.restrictionType);

				if (taxon){
					if (restriction.taxonSource == taxon.taxonSource && taxon.taxonNuid.indexOf(restriction.taxonNuid) == 0){

						enable_field = true;

						if (restriction.restrictionType == "required"){
							require_field = true;
						}
						else if (restriction.restrictionType == "optional"){
							require_field = false;
						}
						break;
					}
				}
			}

			if (restrictionTypes.indexOf("exists") == -1){
				enable_field = true;
			}


			var field_elements = field_container.querySelectorAll('input, select, textarea');

			if (enable_field == true){
				field_container.style.display = "";
			}
			else {
				field_container.style.display = "none";
			}

			for (var e=0; e<field_elements.length; e++){
				var field_element = field_elements[e];

				if (enable_field == true){
					field_element.disabled = false;
				}
				else {
					field_element.disabled = true;
				}

				if (require_field == true){
					field_element.required = true;
				}
				else {
					field_element.required = false;
				}
				
			}

		}
	},

	on_page_leave : function(event){
		var self = ObservationView;
		event.target.removeEventListener(event.type, ObservationView.on_page_leave);
		navigator.geolocation.clearWatch(self.position_interval_id);
		//window.removeEventListener("new_app_position", ObservationView.update_position);

		BackButtonManager.before_back = null;	
	}

});


var ObservationViewSaveWarning = View(TemplateView, {

	"identifier" : "ObservationViewSaveWarning",
	
	template_name : "themes/" + settings.THEME + "/templates/observation_view_save_warning.html",


	modal_title : function(self){
		return _("Unsaved changes");
	},

	close : function(self, args, kwargs){
		OverlayView.close_current_overlay();
	}

}, ModalView)

// PictureInput values are FlexImages
var ManagePictureInput = {
	
	template : null,

	_get_template : function(){
		if (this.template === null){
			var template_str = '<div id="{{ id }}" class="col-auto mb-3 tap" action="ImageViewer.toggle" data-hd-url="{{ hd_url }}" data-container-id="{{ container_id }}" data-thumb-container-id="{{ thumb_container_id }}" data-filename="{{ filename }}"><img src="{{ small }}" /></div>'

			this.template = Handlebars.compile(template_str);
		}

		return this.template;
	},

	get_timestamp_filename : function(image_file){

		let extension = image_file.name.split('.').pop();
		let timestamp = new Date().getTime();
		let filename = "" + timestamp + "." + extension;

		return filename;

	},

	// fix for cordova android not supporting <input type="file" /> on android
	// https://github.com/apache/cordova-android/issues/816
	select_image : function(event){

		var self = this;

		event.preventDefault();

		var message = _("Select source");
		var title = _("Add picture");

		var cameraOptions = {
			"quality" : 95,
			"destinationType" : Camera.DestinationType.FILE_URI,
			"allowEdit" : false, // allowing edit on android 5 is buggy: if you add edited image 1, then add edited image 2, then press save, image 1 and image 2 both become image 2. all edited images are saved using the same name, so the 2nd saved edited image overwrites the first
			"correctOrientation" : true,
            "targetWidth" : 3000,
            "targetHeight" : 3000
		};

		navigator.notification.confirm(message, function(buttonIndex){
			// buttonIndex starts with 1
			if (buttonIndex === 1){
				// camera
				var source = Camera.PictureSourceType.CAMERA;
			}
			else {
				// album
				var source = Camera.PictureSourceType.PHOTOLIBRARY;
			}

			cameraOptions["sourceType"] = source;

			navigator.camera.getPicture(function(imageUri){
				// convert the image to a file object and add it to the file field
				
				window.resolveLocalFileSystemURL(imageUri, function(fileEntry){

					// fileInput.files is a FileList object which is immutable, no .push() support
					// use an alternative for android
					event.target.android_files = [];

					fileEntry.file(function(file){

						event.target.android_files.push(file);

						self.add_image(event);
					});
					
					
				}, function(e){
					alert(e)
				});

			}, function(e){
				// do nothing
			}, cameraOptions);


		}, title, [_("Camera"), _("Album")])
	},

	add_image : function(event){

		var self = ManagePictureInput;

		// id of the field container, not the input element itself
		var container_id = event.target.getAttribute("data-container-id");

		if (!event.target.hasOwnProperty("_files")){
			event.target._files = [];
		}

		var thumb_container = document.getElementById("" + container_id + "_images");

		var thumbnail = Thumbnail.create();

		var hd_thumb = Thumbnail.create({
			quality : 0.9,
			maxWidth : 1000,
			maxHeight : 1000,
			imageSize : "contain"
		});


		if (device.platform == "Android"){
			var filelist = event.target.android_files;
		}
		else {
			var filelist = event.target.files;
		    // bug on iOS wkwebview: viewport gets resized after camera and is too large
		    // on could scroll on the starting page
			if (device.platform == 'iOS'){
		    	StatusBar.hide();
		    	StatusBar.show();
			}
		}

		for (let i=0; i<filelist.length; i++){

			let image_file = filelist[i];

			// pictures from camera all have the same name
			// convert the filename to timestamp.extension

			let timestamp_filename = self.get_timestamp_filename(image_file);

			let fleximage = FlexImage.create(image_file, timestamp_filename);
			image_file.filename = timestamp_filename;
			
			// hasto be fleximage, the same type as if retrieved from db
			event.target._files.push(fleximage);

			thumbnail.as_data_url(image_file, function(thumb_url){

				// add to cache
				thumbnail_cache.add(timestamp_filename, "small", thumb_url);

				hd_thumb.as_data_url(image_file, function(hd_url){

					thumbnail_cache.add(timestamp_filename, "full_hd", hd_url);

					// display thumb in canvas
					let template = self._get_template();
					
					let context = {
						"id" : thumb_url.slice(-30),
						"container_id" : container_id,
						"small" : thumb_url,
						"thumb_container_id" : thumb_container.id,
						"filename" : timestamp_filename
					};
					let html = template(context);
					
					thumb_container.insertAdjacentHTML('beforeend', html);
				});
			});
		}

	},

	// image_item is the thumb
	remove_image_from_upload : function(image_item){

		var filename = image_item.getAttribute("data-filename");

		var field_container = document.getElementById(image_item.getAttribute("data-container-id"));

		var input = field_container.getElementsByTagName("input")[0];

		var index = null;
		for (let f=0; f<input._files.length; f++){
			let fleximage = input._files[f];
			
			// use the timestamped filename, not file.name, to be compatible with cameras
			if (fleximage.filename == filename){
				index = f;
			}
		}
		
		// remove file from upload
		if (index != null){
			let removed = input._files.splice(index,1);
		}
		// remove thumb
		image_item.parentElement.removeChild(image_item);

	},

	delete_image_from_db : function(image_item){

		// yesno prompt for db images only

		// data-model and data-object-id are present
		var model_name = image_item.getAttribute("data-model");
		var object_id = image_item.getAttribute("data-object-id");
		var model_route = image_item.getAttribute("data-model-route")

		var Model = window[model_name];

		// can be objects or remote_objects
		Model[model_route].get({"id":object_id}, function(instance){

			instance.remove(instance, function(){
				// remove images on disk if any
			});

		});

		// remove thumb
		image_item.parentElement.removeChild(image_item);
		
	}
}

/*
*	ImageViewer
*	- show image fullscreen in an overlay, close on back button
*	- on tap show delete and close functionality
*	- be able to swipt left and right
*	- show how many images are there
*/

var ImageViewer = View(OverlayView, {

	identifier : "ImageViewer",

	container_id : "ImageViewerContainer",
	
	template_name : "themes/" + settings.THEME + "/templates/ImageViewer.html",

	_get_element : function(){
		var image_viewer = document.getElementById("ImageViewer");
		return image_viewer;
	},


	open : function(self, request, args, kwargs){

		var image_viewer = this._get_element();
		image_viewer.classList.remove("inback");
		image_viewer.classList.remove("closed");

		var selected_image = kwargs.currentTarget;

		var mode = "edit";

		if (selected_image.hasAttribute("data-imageviewer-mode")){
			mode = selected_image.getAttribute("data-imageviewer-mode");
		}

		if (mode == "edit"){
			document.getElementById("ImageViewerDeleteBtn").style.display = "";
		}
		else {
			document.getElementById("ImageViewerDeleteBtn").style.display = "none";
		}

		// the container holds elements with attributes data-hd-url
		var image_source = document.getElementById(selected_image.getAttribute("data-thumb-container-id"));
	
		var images = [];

		for (let i=0; i<image_source.children.length; i++){
			let image_div = image_source.children[i];

			// support form fields and cache
			let hd_url = thumbnail_cache.get(image_div.getAttribute("data-filename"), "full_hd");

			if (hd_url == null){
				hd_url = image_div.getAttribute("data-hd-url");
			}
			
			var image = {
				"thumb-id" : image_div.id,
				"image-url" : image_div.getAttribute("data-image-url"),
				"hd-url" : hd_url,
				"model" : image_div.getAttribute("data-model", null),
				"object-id" : image_div.getAttribute("data-object-id", null),
				"active" : false
			};

			if (image_div == selected_image){
				image["active"] = true;
			}

			images.push(image);
		}
		
		var context = {
			"images" : images
		}

		self.render_content(self, context, function(){
			$("#ImageViewerContainer").carousel({"interval":false});
		});		

		ImageViewer.super().open(self);
	},
	
	close : function(self){
		var image_viewer = this._get_element();		
		image_viewer.classList.add("closed");
		image_viewer.classList.add("inback");
		document.getElementById("ImageViewerYesNo").style.opacity = 0;
		ImageViewer.super().close();
	},

	toggle : function(self, request, args, kwargs){

		if (typeof self == "undefined" || self == null){
			var self = Object.create(this);
		}

		var image_viewer = this._get_element();

		if (!(image_viewer.classList.contains("closed")) || request.GET.action == "selected" || request.GET.action == "hide") {
			self.close(self);
		}
		else {
			self.open(self, request, args, kwargs);
		}

	},

	// delete the currently active item
	// currently, there are 2 deletion options: delete from db or delete from form
	"delete" : function(self, request, args, kwargs){

		// display a yesno question
		ImageViewer.close_confirm();

		$("#ImageViewerContainer").carousel("dispose")

		var container = document.getElementById("ImageViewerImages");
		var active_item = container.getElementsByClassName("active")[0];

		var thumb = document.getElementById(active_item.getAttribute("data-thumb-id"));

		if (active_item.nextElementSibling){
			active_item.nextElementSibling.classList.add("active")
		}
		else if (container.children.length > 1){
			container.children[0].classList.add("active");
		}
		else {
			ImageViewer.close(self);
		}

		// perform the appropriate delete action
		if (active_item.hasAttribute("data-object-id")){
			ManagePictureInput.delete_image_from_db(thumb);
		}
		else {
			ManagePictureInput.remove_image_from_upload(thumb);
		}

		container.removeChild(active_item);

		if (container.children.length > 0){
			$("#ImageViewerContainer").carousel({"interval":false});
		}

	},

	confirm_delete : function(){
		var confirm = document.getElementById("ImageViewerYesNo");
		if (confirm.style.opacity != 0){
			confirm.style.opacity = 0;
		}
		else {
			confirm.style.opacity = 1;
		}
	},

	close_confirm : function(){
		document.getElementById("ImageViewerYesNo").style.opacity = 0;
	}

});


var DeleteObservation = View(TemplateView, {

	"identifier" : "DeleteObservation",

	yesno : function(self, request, args, kwargs){
		var confirm = document.getElementById("DeleteObservationYesNo");
		if (confirm.style.opacity != 0){
			confirm.style.opacity = 0;
		}
		else {
			confirm.style.opacity = 1;
		}
	},

	close_confirm : function(self, request, args, kwargs){
		document.getElementById("DeleteObservationYesNo").style.opacity = 0;
	},

	get : function(self, request, args, kwargs){

		self.model_route = "objects";
		self.storage_location = kwargs["storage_location"];
		if (self.storage_location == "RemoteDB") {
			self.model_route = "remote_objects";
		}

		DeleteObservation.close_confirm();

		var dataset_id = kwargs["dataset_id"];

		Dataset[self.model_route].get({"pk":dataset_id}, function(dataset){
			dataset.remove(dataset, function(){
				// redirect 
				History.back();
			});
		});
	}

});


var MobileNumberInputAction = function(self, request, args, kwargs){
	var button = kwargs["currentTarget"];
	var input = document.getElementById(button.getAttribute("data-input-id"));

	var min_value = input.getAttribute("min") || null;
	if (min_value != null){
		min_value = parseFloat(min_value);
	}
	var max_value = input.getAttribute("max") || null;
	if (max_value != null){
		max_value = parseFloat(max_value);
	}
	var step = input.getAttribute("step") || 1;
	step = parseFloat(step);
	var decimal_places = 0;

	var step_str = step.toString();
	var step_parts = step_str.split('.');
	if (step_parts.length > 1){
		var decimal_places = step_parts[1].length;
	}
	
	var current_value = input.value || null;

	if	(current_value === null){
		if (min_value != null && max_value != null){
			
			var mid = (min_value + max_value) / 2;
			var stepfactor = parseInt(Math.round( (mid - min_value) / step ));
			current_value = min_value + (stepfactor * step);
			
		}
		else if (min_value != null) {
			if (min_value < 0){
				current_value = 0;
			}
			else {
				current_value = min_value;
			}
		}
		else if (max_value != null){
			if (max_value > 0){
				current_value = 0;
			}
			else {
				current_value = max_value;
			}
		}
		else {
			// neither min nor max given
			current_value = 0;
		}
	}
	else {
		current_value = parseFloat(current_value);
	}

	if (button.textContent == "-"){

		current_value = current_value - step;

		if (min_value != null && current_value < min_value){	
			current_value = min_value;
		}				

	}
	else {

		current_value = current_value + step;

		if (max_value != null && current_value > max_value){
			current_value = max_value;
		}
	}

	input.value = current_value.toFixed(decimal_places);

	var event = new Event("change", {"bubbles":false, "cancelable":true});
	input.dispatchEvent(event);

};

// widget specific functions
// works with TemporalJSON
var selectDateTime = function(self, request, args, kwargs){
		
	var verbose_field = kwargs.currentTarget;
	var input = document.getElementById(verbose_field.getAttribute("data-input-id"));

	// open a datetimepicker
	// mode, min_value, max_value and value are supported

	var options = {
		mode : "datetime",
		date : new Date(),
		maxDate : new Date(), // do not allow future dates
		androidTheme : 4
	};

	if (device.platform == "iOS"){
		options.allowFutureDates = false;
	}

	if (verbose_field.hasAttribute("data-mode") && verbose_field.getAttribute("data-mode").length){
		options.mode = verbose_field.getAttribute("data-mode");
	}

	if (input.hasAttribute("max_value") && input.getAttribute("max_value").length) {
		options.maxDate = new Date(parseInt(input.getAttribute("max_value")));
	}

	if (input.hasAttribute("min_value") && input.getAttribute("min_value").length) {
		options.minDate = new Date(parseInt(input.getAttribute("min_value")));
	}

	if (input.value && input.value.length > 0){
		// TemporalJSON
		var temporal = TemporalJSONbuilder.create(JSON.parse(input.value));
		options.date = temporal.as_Date(temporal);
	}

	// minDate and maxDate should be integers on Android
	if (device.platform == "Android"){
		if (options.maxDate && options.maxDate instanceof Date){
			options.maxDate = options.maxDate.valueOf();
		}
		if (options.minDate && options.minDate instanceof Date){
			options.minDate = options.minDate.valueOf();
		}
	}

	datePicker.show(options, function(dateObj){
		verbose_field.value = dateObj.toLocaleString();
		var temporal = TemporalJSONbuilder.create();
		temporal.load_Date(temporal, dateObj);
		input.value = temporal.as_text(temporal);

		var event = new Event("change", {"bubbles":false, "cancelable":true});
		input.dispatchEvent(event);

	}, function(){
	});
};


var GeolocationReport = View(TemplateView, {
	"identifier" : "GeolocationReport",
	"template_name" : "themes/" + settings.THEME + "/templates/geolocation_report.html",
	"details_template": "themes/" + settings.THEME + "/templates/geolocation_report_details.html",

	get_context_data(self, kwargs){
		var context = GeolocationReport.super().get_context_data(self, kwargs);
		context["app_geolocation"] = AppGeolocation;
		context["app_requires_geolocation"] = app.requires_geolocation;
		return context;
	},

	update_display : function(event){
		var latlng = L.latLng(event.detail.position.coords.latitude, event.detail.position.coords.longitude);
		GeolocationReport.Map.panTo(latlng);
		var context = {
			"app_geolocation" : {
				"last_position" : event.detail.position
			}
		};

		var html = GeolocationReport.compiled_details_template(context);
	
		document.getElementById("geolocationDetails").innerHTML = html;

	},

	on_page_leave : function(event){
		event.target.removeEventListener(event.type, GeolocationReport.on_page_leave);
		window.removeEventListener("new_app_position", GeolocationReport.update_display);
	},

	post_finished : function(args, kwargs){
		
		var self = GeolocationReport;

		ajax.GET(self.details_template, {}, function(template){
			self.compiled_details_template = Handlebars.compile(template);
		});
		
		var layerSources = {

			"osm": L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
				{
					attribution: '&copy; OpenStreetMap, Tiles courtesy of Humanitarian OpenStreetMap Team',
					subdomains: 'ab'
				})

		};

		var coords = [0,0];

		if (AppGeolocation.last_position != null && AppGeolocation.last_position.hasOwnProperty("coords")){
			coords[0] = AppGeolocation.last_position.coords.latitude;
			coords[1] = AppGeolocation.last_position.coords.longitude;
		}

		GeolocationReport.Map = L.map("geolocationMap", {
			center: coords,
			zoom: 10,
			scrollWheelZoom: false,
			layers: [
				  	layerSources["osm"]
			]
		});

		GeolocationReport.Map.attributionControl.setPrefix("Leaflet");

		// add a temporary success listener to the AppGeolocation Event that is cancelled on pagechange
		window.addEventListener("new_app_position", GeolocationReport.update_display);
		window.addEventListener("pagechanged", GeolocationReport.on_page_leave);

	}

});


// receives geojson
function verbosify_position(geojson){
	return forms.MobilePositionInput.verbose_value(null, geojson);
}

function geojson_to_position_html5(geojson){

	var accuracy = 1;

	if (geojson.hasOwnProperty("properties") && geojson.properties.hasOwnProperty("accuracy")){
		accuracy = geojson.properties.accuracy;
	}

	var position = {
		"coords" : {
			"latitude" : geojson.geometry.coordinates[1],
			"longitude" : geojson.geometry.coordinates[0],
			"accuracy" : accuracy
		}
	};

	return position;

};

var selectPosition = function(self, request, args, kwargs){	

	var field = kwargs.currentTarget;

	var input_id = field.getAttribute("data-input-id");
	var input = document.getElementById(input_id);

	var error_container_id = "" + field.id + "_error";

	var error_container = document.getElementById(error_container_id);

	// open positionPicker
	var options = {};

	if (input.value && input.value.length > 0){
		var geojson = JSON.parse(input.value);
		var position = geojson_to_position_html5(geojson);
		options["position"] = position;
	}

	positionPicker.show(options, function(geojson){
		// the position json object is the value - as geojson
		if (geojson != null){
			var verbose_position = verbosify_position(geojson);
			field.value = verbose_position;
			var value = JSON.stringify(geojson);
			input.value = value;

			if (error_container != null){
				error_container.style.display = "none";
			}

			var manually_selected_event = new CustomEvent("manuallySelectedPosition", {
				detail: {
					"position" : position
				}
			});
			input.dispatchEvent(manually_selected_event);

			var change_event = new Event("change", {"bubbles":false, "cancelable":true});
			input.dispatchEvent(change_event);
		}
	});


};


var PositionValidator = {

	_project_area_geojson : null,

	_perform_project_area_validation : function(lat, lng, callback){

		var self = PositionValidator;

		var is_within = false;

		// geojson is lnglat
		var position = {
			"type": "Feature",
			"geometry": {
				"type": "Point",
				"coordinates": [lng, lat]
			}
		};

		// iterate over all polygons and check if the point is within the polygon
		for (let f=0; f<self._project_area_geojson["features"].length; f++){
			let feature = self._project_area_geojson["features"][f];
			is_within = turf.booleanWithin(position, feature);
			if (is_within == true) {
				break;
			}
		}

		if (is_within == true){
			callback([]);
		}
		else {
			callback([_("Position is not within the project area of this app.")]);
		}
	},

	_validate_against_project_area : function(lat, lng, callback){

		var self = PositionValidator;

		if (app_features.hasOwnProperty("Map")){

			if (self._project_area_geojson == null){
				var map_path = app_features["Map"]["list"][0]["path"];
				ajax.GET(map_path, {}, function(content){
					var map = JSON.parse(content);//JSON.parse(atob(content));

					if (map.hasOwnProperty("geometries") && map["geometries"].hasOwnProperty("projectArea")){
						self._project_area_geojson = map["geometries"]["projectArea"];
						var is_within = self._perform_project_area_validation(lat, lng, callback);
					}
					else {
						// no restriction
						callback([]);
					}
				});
			}
			else {
				self._perform_project_area_validation(lat, lng, callback);
			}
		}
		else {
			callback([]);
		}
	},

	validate : function(lat, lng, callback){

		var self = PositionValidator;

		self._validate_against_project_area(lat, lng, function(errors){
			callback(errors);
		});
	}
};


/*
* positionPicker
* - internally uses positions in html5 format {"coords":{"latitude":0, "longitude":0, "accuracy":0}}
*/
var positionPicker = {
	template_name : "themes/" + settings.THEME + "/templates/positionpicker.html",
	template : null,

	picked_position : null,
	initial_position : null,
	fallback_position : {
		coords : {
			latitude : 55.83548,
			longitude : 8.71964
		}
	},

	return_format : "geojson",

	marker : null,

	show : function (options, onsuccess, onerror){
		var self = positionPicker;

		self.onsuccess = onsuccess;
		self.onerror = onerror;

		self.picked_position = null;
		self.marker = null;

		var options = options || {};

		self.initial_position = options.position || null;

		self._load_template(function(){
			var context = self._build_context();

			var html = self.template(context);
			var title = _("SelectPosition");

			modalDialog.open(html, title);
			
			self._load_map(self.initial_position);
		});
	},
	accept : function(){
		var self = positionPicker;

		modalDialog._close();

		self.initial_position = null;

		var position_html5 = null;
		var return_position = null;
		
		if (self.picked_position != null){
			position_html5 = cloneAsObject(self.picked_position);
		}
		else if (self.marker != null){
			var latlng = self.marker.getLatLng();
			position_html5 = self.latlng_to_html5(latlng);
		}

		// format the position
		if (position_html5 != null){
			return_position = self["as_" + self.return_format](position_html5);
		}

		self.onsuccess(return_position);

	},
	latlng_to_html5 : function(latlng){
		var html5_position = {
			coords : {
				latitude : latlng.lat,
				longitude : latlng.lng,
				accuracy : 1
			}
		};

		return html5_position;
	},
	as_geojson : function(position_html5){
		var builder = GeoJSONbuilder.create();
		builder.load_html5_position(builder, position_html5);
		return builder.as_json(builder);
	},
	as_html5 : function(position_html5){
		return position_html5;
	},
	close : function(){
		modalDialog._close();

		if (typeof self.on_error == "function"){
			self.on_error();
		}

	},

	_get_map_feature_position : function(callback){

		if (app_features.hasOwnProperty("Map")){
			var map_path = app_features["Map"]["list"][0]["path"];

			ajax.GET(map_path, {}, function(content){
				var map = JSON.parse(content); //JSON.parse(atob(content));

				var map_initial_latitude = map.options.initial_latitude || null;
				var map_initial_longitude = map.options.initial_longitude || null;
				var map_initial_zoom = map.options.initial_zoom || 12;

				if (map_initial_latitude != null && map_initial_longitude != null){
					var position = {
						coords : {
							longitude : map_initial_longitude,
							latitude : map_initial_latitude
						},
						initial_zoom : map_initial_zoom // zoom needed by _load_map
					};

					callback(position);

				}
				else {
					callback(null);
				}
			});

		}
		else {
			callback(null);
		}

	},

	_load_map : function(position){

		var self = positionPicker;

		// map feature is optional
		self._get_map_feature_position(function(map_feature_position){		

			var map_position = position || null;

			var zoom = self.initial_position == null ? 12 : 18;

			// if no marker is given, first try to get current position
			// then try to get map initial view
			// finally use fallback position
			if (self.initial_position == null && map_position == null){
				if (AppGeolocation.last_position != null && AppGeolocation.last_position.hasOwnProperty("coords")){
					map_position = AppGeolocation.last_position;
				}
				else if (map_feature_position != null){
					map_position = map_feature_position;

					zoom = map_position.initial_zoom;
				}
				else {
					map_position = self.fallback_position;

					zoom = 7;
				}
			}

			var layerSources = {
				"osm" : L.tileLayer('https://{s}.tile.openstreetmap.de/{z}/{x}/{y}.png',
					{
						attribution: 'Map data &copy; OpenStreetMap contributors',
						subdomains: 'ab',
						maxZoom: 20,
						maxNativeZoom: 18
					}),
		
				"satellite_tiles" : L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
					{
						attribution: 'Tiles &copy; Esri',
						maxZoom: 20,
						maxNativeZoom: 18
					}),
				"satellite_names": L.tileLayer('https://stamen-tiles.a.ssl.fastly.net/toner-labels/{z}/{x}/{y}.{ext}', {
					attribution: '&mdash; Map data &copy; OpenStreetMap',
					subdomains: 'abcd',
					minZoom: 0,
					maxNativeZoom: 18,
					maxZoom: 20,
					ext: 'png'
				})
			};

			var center = [map_position.coords.latitude, map_position.coords.longitude];

			var map = L.map("positionPickerMap", {
				center: center,
				zoom : zoom,
				maxZoom: 24,
				scrollWheelZoom: false
			});

			map.attributionControl.setPrefix("Leaflet");

			self.map = map;

			// add geolocation layers - display a marker of the users current position
			self.add_ownpos_button(self);

			// add tile layers
			var satellite = L.layerGroup([layerSources.satellite_tiles, layerSources.satellite_names]);
		
			satellite.addTo(map);

			var baseLayers = {
				"Satellite" : satellite,
				"Streets" : layerSources["osm"]
			};

			L.control.layers(baseLayers, {}, {"position":"topright"}).addTo(map);

			L.control.scale({"position":"bottomright"}).addTo(map);

			// add markerlayer to map
			self.markers = new L.FeatureGroup();
		
			self.markers.addTo(map);

			if (self.initial_position != null){
				self._place_marker(self.initial_position.coords.latitude, self.initial_position.coords.longitude);
			}

			map.on("click", function (event) {

				var error_container = document.getElementById("position-picker-error");

				PositionValidator.validate(event.latlng.lat, event.latlng.lng, function(errors){

					if (errors.length == 0){

						error_container.classList.add("d-none");

						self._place_marker(event.latlng.lat, event.latlng.lng);
						positionPicker.picked_position = {
							coords : {
								latitude : event.latlng.lat,
								longitude : event.latlng.lng,
								accuracy : 1
							}
						};
					}
					else {
						self._clear_position();
						// show error
						error_container.textContent = errors.join();
						error_container.classList.remove("d-none");					
					}

				});
			});

		});

	},

	_clear_position : function(){
		var self = positionPicker;

		self.markers.clearLayers();
		self.marker = null;
		self.picked_position = null;
	},

	_place_marker : function(lat, lng){
		var self = positionPicker;
		self.markers.clearLayers();
		self.marker = L.marker([lat, lng]);
		self.marker.addTo(self.markers);
	},
	_load_template : function(callback){
		var self = positionPicker;

		if (self.template == null){
			ajax.GET(self.template_name, {}, function(template){
				self.template = Handlebars.compile(template);
				callback();
			});	
		}
		else {
			callback();
		}
	},
	_build_context : function(){
		return {};
	},

	add_ownpos_button : map_control.add_ownpos_button,

	show_current_position_marker : map_control.show_current_position_marker
};


var TaxonSearch = {

	current_alphabet_content : [],
	current_start_letters : null,

	current_vernacular_language : null,
	current_vernacularNames : [],

	search_backbone : function(searchtext, callback){
		var self = TaxonSearch;

		self._search_backbone_latnames(searchtext, function(results){
			// search vernacular names
			self._search_backbone_vernacularNames(searchtext, function(vernacular_results){
				var all_results = results.concat(vernacular_results);

				callback(all_results);
			});
		});
	},

	_search_taxon_list : function(taxon_list, searchtext, key, search_type, callback){
		var self = TaxonSearch;

		var results = [];
		var searchtext = searchtext.trim().toUpperCase();

		for (var t=0; t<taxon_list.length; t++){
			var taxon_params = taxon_list[t];

			var taxon_extra_attrs = {
				"gbifNubkey": taxon_params.gbifNubkey,
			};

			if (taxon_params.hasOwnProperty("name")){
				taxon_extra_attrs["name"] = taxon_params["name"];
			}

			var taxon = Taxon.create(taxon_params.taxonSource, taxon_params.nameUuid, taxon_params.taxonLatname, taxon_params.taxonAuthor, taxon_params.taxonNuid, taxon_extra_attrs);

			var search_value = taxon_params[key].toUpperCase();

			if (search_value == searchtext){
				results.unshift(taxon);
			}
			else {
				if (search_type == 'startswith'){
					if (search_value.indexOf(searchtext) == 0){
						results.push(taxon);
					}
				}
				else if (search_type == 'contains'){
					if (search_value.indexOf(searchtext) >= 0){
						results.push(taxon);
					}
				}
			}
		}

		callback(results);

	},

	_search_backbone_latnames : function(searchtext, callback){
		var self = TaxonSearch;

		var searchtext = searchtext.trim().toUpperCase();
		var start_letters = searchtext.substring(0,2);

		if (start_letters != self.current_start_letters){
			var filepath = app_features.BackboneTaxonomy.alphabet + "/" + start_letters + ".json";
			ajax.getJSON(filepath, {}, function(content){
				TaxonSearch.current_alphabet_content = content;
				TaxonSearch._search_taxon_list(TaxonSearch.current_alphabet_content, searchtext, 'taxonLatname', 'startswith', callback);
			}, function(e){
				console.log('No taxonfile found for ' + start_letters);
				TaxonSearch.current_alphabet_content = [];
				TaxonSearch._search_taxon_list(TaxonSearch.current_alphabet_content, searchtext, 'taxonLatname', 'startswith', callback);
			});
		}
		else {
			self._search_taxon_list(self.current_alphabet_content, searchtext, 'taxonLatname', 'startswith', callback);
		}	 

	},

	_search_backbone_vernacularNames : function(searchtext, callback){
		var self = TaxonSearch;

		if (app.language != self.current_vernacular_language){

			self.current_vernacular_language = app.language;
			
			if (app_features.BackboneTaxonomy.vernacular.hasOwnProperty(app.language)){
			
				var filepath = app_features.BackboneTaxonomy.vernacular[app.language];
				
				ajax.getJSON(filepath, {}, function(vernacular_list){
					TaxonSearch.current_vernacularNames = vernacular_list;
					TaxonSearch._search_taxon_list(TaxonSearch.current_vernacularNames, searchtext, 'name', 'contains', callback);
				});
			}
			else {
				self._search_taxon_list(self.current_vernacularNames, searchtext, 'name', 'contains', callback);
			}
		}
		else {
			self._search_taxon_list(self.current_vernacularNames, searchtext, 'name', 'contains', callback);
		}
	}
};


/*
* Logging in
* - after successfully logging in, the user instance needs to be saved
*/
var LoginView = View(FormView, {
	"identifier" : "LoginView",
	"template_name" : "themes/" + settings.THEME + "/templates/login.html",

	"needs_internet" : true,

	modal_title : function(self){
		return _("Log in");
	},

	form_class : LoginForm,

	login_redirect : null, // all LoginViews need this. this is set by mango if automatically called from another view which has the attribute login_required : true

	form_valid : function(self, form){
		// try to log the user in
		var username = form.cleaned_data["username"];
		var password = form.cleaned_data["password"];

		// try to authenticate the user
		var auth_kwargs = {
			"username" : username,
			"password" : password
		};

		// authenticate saves the user on the offline device if it is not in the db yet
		authenticate(self.request, auth_kwargs, function(user, auth_data){

			// log the user in
			login(self.request, user, auth_data);

			load_sidemenu();

			console.log("[LoginView] logged in " + user.username);

			modalDialog._close();

			console.log("redirecting")
			if (typeof self.login_redirect == "function"){
				self.login_redirect(user);
			}
			
			// reload appbar
			if (Appbar.current_header_view != null){
				Appbar.reload();
			}

		}, function(error_message){
			// display an error message, username or password are wrong
			var context = self.get_context_data(self, self.kwargs);
			context["form"] = form;

			// error_message is json in this case
			context["login_error"] = _("username or password invalid");

			self.render_to_response(self, context);

		});

	}

}, ModalView);

var LogoutView = function (self, request, args, kwargs){
	logout(request, request.user);
	HttpResponseRedirect("/");
	load_sidemenu();
	Appbar.reload();
};

/*
* always queries the server
* ONLY if the user is on a device, the user has to be saved in the db
* In theory, there are two options: use RemoteDB LocalcosmosUser.objects.create_user OR use the registratoin API
* we use the registration api because this does server-side validation
*/

var RegistrationView = View(RemoteFormView, {
	
	"identifier" : "RegistrationView",
	"template_name" : "themes/" + settings.THEME + "/templates/registration.html",

	"needs_internet" : true,


	get_api_url : function(self){
		var url = "user/register/";
		return url;
	},

	get_initial : function(self){
		var initial = {
			"client_id" : device.uuid,
			"platform" : device.platform
		};
		return initial;
	},

	form_valid : function(self, form, response_html){
		// self.success_data is available which is the data that has resulted in an code 200 response
		
		// we need to get a user object an log this user in
		// this differs between Remote and Device
		// after a LocalcosmosUser object has been retrieved/created run registration_success

		// the server assigns the uuid to the user, so we need to fetch user data from the server
		var auth_kwargs = {
			"username" : self.success_data["username"],
			"password" : self.success_data["password"]
		};

		// authenticate saves the user on the offline device if it is not in the db yet
		authenticate(self.request, auth_kwargs, function(user, auth_data){

			// log the user in
			login(self.request, user, auth_data);
			console.log("[RegistrationView] logged in " + user.username);

			load_sidemenu();

			// display a success page
			var context = self.get_context_data(self, self.kwargs);
			context["success"] = true;
			context["html"] = response_html;

			self.render_to_response(self, context);
			
		}, function(error_message){
			// this should never happen
			alert(error_message);
			// at least give the user the chance to log in
			HttpResponseRedirect(reverse("login"));
		});

	}

});


/*
* this is a special view that receives the form definition from the server
* it is only available when a network connection is present
* there is no account management on the local system
*/
var AccountView = View(RemoteFormView, {

	"identifier" : "AccountView",
	"template_name" : "themes/" + settings.THEME + "/templates/manage_account.html",

	"login_required" : true,

	"needs_internet" : true,

	get_api_url : function(self){
		var url = "user/" + mango_session.user.id + "/manage/";
		return url;
	},

	get_post_method : function(self){
		return "PUT";
	},

	form_valid : function(self, form, form_html){
		// simply display what the server rendered
		self.render_to_response(self, self.get_context_data(self, {"html":form_html, "success" : true}));
	}

});



var PasswordResetView = View(RemoteFormView, {

	"identifier" : "PasswordResetView",
	"template_name" : "themes/" + settings.THEME + "/templates/password_reset.html",
	"needs_internet" : true,

	get_api_url : function(self){
		var url = "password/reset/";
		return url;
	},

	form_valid : function(self, form, form_html){
		// simply display what the server rendered
		self.render_to_response(self, self.get_context_data(self, {"html":form_html, "success" : true}));
	}

});


/*
* DELETE ACCOUNT
*/

var DeleteAccountView = View(RemoteFormView, {

	"identifier" : "DeleteAccountView",
	"template_name" : "themes/" + settings.THEME + "/templates/delete_account.html",

	"login_required" : true,

	"needs_internet" : true,

	get_api_url : function(self){
		var url = "user/" + mango_session.user.id + '/delete/';
		return url;
	},

	get_post_method : function(self){
		return "DELETE";
	},

	form_valid : function(self, form, form_html){
		// simply display what the server rendered
		self.render_to_response(self, self.get_context_data(self, {"html":form_html, "success" : true}));

		logout(self.request, self.request.user);
		load_sidemenu();
		Appbar.reload();
	}

});


var InfiniteScrollingView = View(TemplateView, {

	"container_id" : null, // required

	"list_template_name" : null, // required

	"page_size" : 12,
	"page" : 1,
	"last_batch_count" : null,
	"fetching" : false,

	"last_scrollTop" : 0,


	get_bottom_distance_from_viewport : function(self){

		var container = document.getElementById(self.container_id);
		var viewport_height = window.innerHeight || document.documentElement.clientHeight;

		var bounding = container.getBoundingClientRect();

		var distance = bounding.bottom - viewport_height;

		return distance;
	},

	render_content : function(self, context, callback){
		default_renderer.render(self.list_template_name, context, function(template_html){
			
			var container = document.getElementById(self.container_id);
			if (container != null){
				container.insertAdjacentHTML("beforeend", template_html);
				callback();
			}
		});
	},

	_fetch_content_loop : function(self){

		if (self.fetching == false){

			self.fetching = true;
			
			var distance = self.get_bottom_distance_from_viewport(self);
			
			if (distance < 500 && (self.last_batch_count == null || self.last_batch_count >= self.page_size) ){

				self._fetch_next_content_batch(self);
				
			}
			else {
				self.fetching = false;
			}

		}
		
	},

	_post_finished : function(self){
		self.last_batch_count = null;
		self.page = 1;
		self.remote_page = 1;
		self.fetching = false;

		self.last_scrollTop = 0;

		self.initial_remote_dataset_count = 0;
		
		self._fetch_content_loop(self);
		
		self._activate_infinite_scrolling(self);
	},

	_activate_infinite_scrolling : function(self){
		self.ticking = false;
		window.addEventListener('scroll', self._onscroll_listener_wrap);
	},

	// throttle onscroll listener by 100ms
	_onscroll_listener : function(self, event){

		var scrollTop = window.pageYOffset || document.documentElement.scrollTop;

		if (scrollTop > self.last_scrollTop){

			if (!self.ticking) {

				setTimeout(function () {

					self._fetch_content_loop(self);

					self.ticking = false;

				}, 100)

			}
			self.ticking = true;

		}
		self.last_scrollTop = scrollTop <= 0 ? 0 : scrollTop; // For Mobile or negative scrolling

	}

});

/*
* MyObservations
* - support multiple users on one device
* - support anonymous observations without user_id (uuid)
* - queries Dataset.remote_objects, because the remote db GIS is much more capable (filters) than SQLite
* - the template has to be rendered in post_finished. If a user enters a dataset, changes the taxon and presses the back button, the list has to be reload from db and NOT from history to show the correct taxon
*/
var MyObservations = View(InfiniteScrollingView, {

	"identifier" : "MyObservations",

	"template_name" : "themes/" + settings.THEME + "/templates/my_observations.html",

	"list_template_name" : "themes/" + settings.THEME + "/templates/my_observations_list.html",

	"login_required" : true,

	"container_id" : "my-observations",

	"remote_page" : 1,

	"initial_remote_dataset_count" : 0,


	post_finished : function(args, kwargs){
		
		var self = MyObservations;

		var container = document.getElementById(self.container_id);
		container.textContent = "";

		self._post_finished(self);

	},

	_build_context : function(self, context, datasets){

		context["datasets"] = datasets;
		context["internet_status"] = getNetworkState();
		context["page"] = self.page;

		self.last_batch_count = datasets.length;

		self.render_content(self, context, function(){

			// next fetch should be the next page
			self.page = self.page + 1;

			// set correct self.remote_page
			self.remote_page = self.remote_page + 1;
			
			// async while loop - fetch until no more datasets are fetchable OR the distance is >= 500
			var new_distance = self.get_bottom_distance_from_viewport(self);

			self.fetching = false;

			if (new_distance < 500 && self.last_batch_count >= self.page_size){
				self._fetch_content_loop(self);
			}
			
		});

	},

	_fetch_next_content_batch : function(self){

		let context = {};

		// get local datasets first
		var local_limit = self.page_size;
		var local_offset = (self.page - 1) * self.page_size;

		self._get_local_datasets(self, local_limit, local_offset, function(local_datasets){

			var local_dataset_count = local_datasets.length;

			context["unsynced_count"] = local_dataset_count;

			// try to fetch remote datasets, do not use <=
			if (local_dataset_count < self.page_size){

				var remote_limit = self.page_size - local_dataset_count;

				// remote_page #1 might have less than page_size sightings
				var next_remote_page = self.remote_page - 2;

				if (next_remote_page < 0){
					next_remote_page = 0;
				}

				var remote_offset = self.initial_remote_dataset_count + (next_remote_page * self.page_size);

				self._get_remote_datasets(self, remote_limit, remote_offset, function(response){

					context["server_error"] = response["server_error"];

					// set self.initial_remote_dataset_count on the first mixed page
					if (local_dataset_count >= 0){
						self.initial_remote_dataset_count = response["datasets"].length;
					}

					// Dataset instances
					var datasets = local_datasets.concat(response["datasets"]);

					self._build_context(self, context, datasets);

				});
			}
			else {
				// 100% local datasets (device.platform != browser) for the current page
				// do not query remote datasets
				self._build_context(self, context, local_datasets);
			}

		});

	},

	_get_local_datasets : function(self, limit, offset, callback){

		if (device.platform == "browser"){
			callback([]);
		}
		else {
			// there might be uploaded datasets which images are not yet uploaded. In this case, show only the remote dataset
			var queryset = Dataset.objects.filter({"needs_sync":true});

			if (limit != null){
				queryset.limit(limit);
			}

			if (offset != null){
				queryset.offset(offset);
			}

			queryset.fetch(function(datasets){

				var datasets_with_thumbnail = [];

				each(datasets, function(dataset, iterate){

					dataset.prefetch_thumbnail(dataset, function(dataset){
						datasets_with_thumbnail.push(dataset);
						iterate();
					});					

				}, function(){
					callback(datasets_with_thumbnail);
				});
				
			});
			
		}

	},

	// only fetch remote datasets if internet connection is available
	_get_remote_datasets : function(self, limit, offset, callback){

		var internet_status = getNetworkState();

		if (internet_status == "online"){

			// pagination is required
			if (mango_session.user.is_authenticated){
				// support multiple users on one device ?
				var queryset = Dataset.remote_objects.filter({"user_id":mango_session.user.uuid});
			}
			else {
				// filter by client_id and user_id == null
				var queryset = Dataset.remote_objects.filter({"user_id__isnull":true, "client_id":device.uuid});
			}

			if (limit != null){
				queryset.limit(limit);
			}

			if (offset != null){
				queryset.offset(offset);
			}
		
			queryset.fetch(function(datasets){
				var response = {
					"datasets" : datasets,
					"server_error" : false
				};

				callback(response);
			}, function(status, statusText, responseText){
				// xhr error
				var response = {
					"datasets" : [],
					"server_error" : true
				};

				callback(response);

			});

		}
		else {
			var response = {
				"datasets" : [],
				"server_error" : false
			};

			callback(response);
		}

	},

	_onscroll_listener_wrap : function(event){
		var self = MyObservations;
		self._onscroll_listener(self, event);
	},

	on_page_leave : function(event){
		var self = MyObservations;
		window.removeEventListener('scroll', self._onscroll_listener_wrap);
	}

});


var AllObservations = View(InfiniteScrollingView, {

	"identifier" : "AllObservations",

	"template_name" : "themes/" + settings.THEME + "/templates/all_observations.html",

	"list_template_name" : "themes/" + settings.THEME + "/templates/all_observations_list.html",

	"container_id" : "all-observations",

	"needs_internet" : true,

	"async_context" : true,

	/*post_render : function(args, kwargs){
		var self = AllObservations;
		self._post_finished(self);
	},*/

	post_finished : function(args, kwargs){
		
		var self = AllObservations;

		var container = document.getElementById(self.container_id);
		container.textContent = "";

		self._post_finished(self);

	},

	_fetch_next_content_batch : function(self){

		var limit = self.page_size;
		var offset = (self.page - 1) * self.page_size;

		let context = {};

		// get datasets as json
		Dataset.remote_objects.all().limit(limit).offset(offset).fetch(function(datasets){

			self.last_batch_count = datasets.length;

			context["datasets"] = datasets;
			context["page"] = self.page;
			
			self.render_content(self, context, function(){

				// next fetch should be the next page
				self.page = self.page + 1;

				// async while loop - fetch until no more datasets are fetchable OR the distance is >= 500
				var new_distance = self.get_bottom_distance_from_viewport(self);

				self.fetching = false;

				if (new_distance < 500 && self.last_batch_count >= self.page_size){
					self._fetch_content_loop(self);
				}
				
			});

		});

		
	},

	_onscroll_listener_wrap : function(event){
		var self = AllObservations;
		self._onscroll_listener(self, event);
	},

	on_page_leave : function(event){
		var self = AllObservations;
		window.removeEventListener('scroll', self._onscroll_listener);
	}

});


/*
* SynchronizeObservations
* - only for android/ios clients, not for browser
* - uploaded Datasets and DatasetImages are deleted from the device after uploading
*/
var SynchronizeObservations = View(TemplateView, {
	"identifier" : "SynchronizeObservations",

	"template_name" : "themes/" + settings.THEME + "/templates/sync_observations.html",

	"async_context" : true,

	modal_title : function(){
		return _("Sync Observations");
	},

	get : function(self, request, args, kwargs){

		var action = kwargs["action"];

		if (action == "ask"){

			self.get_context_data(self, kwargs, function(context){
				self.render_to_response(self, context);
			});

		}
		else if (action == "sync"){

			self.synchronize(self, request, args, kwargs);

		}

	},

	clean_local_datasets : function(callback){

		if (device.platform != "browser"){

			DatasetImages.objects.filter({"needs_sync" : false}).fetch(function(dataset_images){

				each(dataset_images, function(dataset_image, iterate_dataset_images){

					dataset_image.remove(dataset_image, iterate_dataset_images);

				}, function(){

					Dataset.objects.filter({"needs_sync" : false}).fetch(function(datasets){
						each(datasets, function(dataset, iterate_datasets){

							dataset.remove(dataset, iterate_datasets);

						}, callback);
					});

				});

			});
		}
		else {
			callback();
		}

	},

	synchronize : function(self, request, args, kwargs){

		var progress_parts = 0;

		// get all parts
		Dataset.objects.filter({"needs_sync" : true}).count(function(dataset_count){

			progress_parts += dataset_count;

			DatasetImages.objects.filter({"needs_sync" : true}).count(function(image_count){

				progress_parts += image_count;

				// close modal, open progress
				modalDialog._close();

				var initial_message = _("collecting observations");

				modalProgress.start(_("Uploading"), initial_message, progress_parts);

				// first: upload each dataset and its images, delete images and dataset
				// second: upload all unuploaded dataset images if any 
				Dataset.objects.filter({"needs_sync" : true}).fetch(function(datasets){

					each(datasets, function(dataset, iterate_datasets){

						modalProgress.progress_text("uploading observation #" + dataset.id);

						dataset.upload(dataset, function(dataset){

							modalProgress.next_part(_("collecting images"));

							DatasetImages.objects.filter({"dataset_id":dataset.id, "needs_sync" : true}).fetch(function(dataset_images){

								each(dataset_images, function(dataset_image, iterate_dataset_images){

									var progress_text = "uploading observation image #" + dataset_image.id;
									modalProgress.progress_text(progress_text);

									dataset_image.upload(dataset_image, function(dataset_image){

										modalProgress.next_part("successfully uploaded image #" + dataset_image.id);
										iterate_dataset_images();
									});									

								}, function(){
									// finished uploading dataset images for this dataset
									modalProgress.progress_text(_("processing next dataset"));
									iterate_datasets();
								});

							});

							
						});
					
						// sync the datasets images

					}, function(){
						// all datasets have been uploaded

						// fetch all images that have not been uploaded yet
						DatasetImages.objects.filter({"needs_sync":true}).fetch(function(dataset_images){
							each(dataset_images, function(dataset_image, iterate){

								var progress_text = "uploading observation image #" + dataset_image.id;
								modalProgress.progress_text(progress_text);

								dataset_image.upload(dataset_image, function(dataset_image){

									modalProgress.next_part("successfully uploaded image #" + dataset_image.id);
									iterate();
								});
								
							}, function(){

								var progress_text = _("cleaning up");
								modalProgress.progress_text(progress_text);

								self.clean_local_datasets(function(){
									modalProgress.finish();
									modalProgress._close();

									// reload myobservations content
									kwargs.request = {
										"GET" : {
											"page" : 1
										}
									};
									MyObservations.post_finished(args, kwargs);

								});

							});
						});

					});
					
				});

			})

		});	
		
	}

}, ModalView);

var ButtonMatrixView = View(TemplateView, {

	"identifier" : "ButtonMatrixView",

	"template_name" : "themes/" + settings.THEME + "/templates/buttonmatrix.html",

	"async_context" : true,

	"login_required" : true,

	"position_interval_id" : null,
	"position_interval_options" : {
		"enableHighAccuracy" : true,
		"timeout" : 1 * 60 * 1000,
		"maximumAge" : 1 * 20 * 1000
	},

	get_exposed_field_definition : function(self, matrix_definition, callback){

		var form_uuid = matrix_definition.options.generic_form.uuid;
		var form_path = app_features.GenericForm.lookup[form_uuid];

		ajax.GET(form_path, {}, function(form_content){
			var generic_form_definition = JSON.parse(form_content); //JSON.parse(atob(form_content));
			
			var exposed_field_definition = null;

			for (var f=0; f<generic_form_definition.fields.length; f++){
				var field_definition = generic_form_definition.fields[f];
				if (field_definition.uuid == matrix_definition.options.generic_form_exposed_field.uuid){
					exposed_field_definition = field_definition;
					break;
				}
			}

			if (exposed_field_definition == null){
				throw new Error("[ButtonMatrixView.get_context_data] Exposed field not found in assigned generic form");
			}

			callback(exposed_field_definition);

		});

	},

	get_context_data : function(self, kwargs, callback){
		ButtonMatrixView.super().get_context_data(self, kwargs, function(context){

			var path = app_features.ButtonMatrix.lookup[self.kwargs["buttonmatrix_uuid"]];

			var matrices = app_features.ButtonMatrix.list;

			ajax.GET(path, {}, function(content){
				var matrix_definition  = JSON.parse(content);//JSON.parse(atob(content));
				context["matrix"] = matrix_definition;
				context["multiple_matrices"] = matrices.length > 1 ? true : false;
				context["matrixlist"] = matrices;

				if (matrix_definition.options.hasOwnProperty("generic_form_exposed_field") && matrix_definition.options.generic_form_exposed_field != null){

					self.get_exposed_field_definition(self, matrix_definition, function(exposed_field_definition){

						var field = createFieldFromJSON(exposed_field_definition);	

						var FormForExposedField = Form(forms.Form,[{
							"fields" : {
								"exposed_field" : field
							}
						}]);

						var form = FormForExposedField.create();
						var boundfield = form.fieldlist[0];
						context["exposed_field"] = boundfield.as_widget(boundfield);

						callback(context);

					});					

				}
	
				else {
					callback(context);
				}
			});	

		});
	},

	post_finished : function(args, kwargs){
		// load the exposed field as an option

		var self = ButtonMatrixView;

		// use only one watcher to fill all fields
		self.position_interval_id = navigator.geolocation.watchPosition(self.update_position, self.on_position_error, self.position_interval_options);
		window.addEventListener("pagechanged", ButtonMatrixView.on_page_leave);
		console.log("[ButtonMatrixView] fetching position");

		var path = app_features.ButtonMatrix.lookup[kwargs["buttonmatrix_uuid"]];
		ajax.GET(path, {}, function(content){
			var matrix_definition  = JSON.parse(content); //JSON.parse(atob(content));
			
			if (matrix_definition.options.hasOwnProperty("generic_form_exposed_field") && matrix_definition.options.generic_form_exposed_field != null){
				ButtonMatrixView.get_exposed_field_definition(self, matrix_definition, function(exposed_field_definition){
					var options = {
						"exposed_field" : exposed_field_definition
					};
					var button_matrix = ButtonMatrix.create(options);
					modalDialog._close();
				})
			}
			else {
				var button_matrix = ButtonMatrix.create();
				modalDialog._close();
			}

		});

		// activate slide
		var slider = document.getElementById("recent-logs");
		horizontal_slider(slider);
		
	},

	update_position: function(position){
		// receive a html5 position object
		var position_inputs = Pagemanager.container.getElementsByClassName("mobilePositionInput");
		
		var position = cloneAsObject(position);

		var builder = GeoJSONbuilder.create();
		builder.load_html5_position(builder, position);
		var geojson_string = builder.as_text(builder);

		var value = geojson_string;

		document.getElementById("matrix_current_position").value = value;

		document.getElementById("noPositionBlocker").style.display = "none";

	},

	on_position_error : function(e){
		console.log("[ButtonMatrixView] position error " + JSON.stringify(e));
	},

	on_page_leave : function(event){
		var self = ButtonMatrixView;
		event.target.removeEventListener(event.type, ButtonMatrixView.on_page_leave);

		if (self.position_interval_id != null){
			navigator.geolocation.clearWatch(self.position_interval_id);
			console.log("[ButtonMatrixView] stop fetching position");
		}
	}

});

var SwitchButtonMatrix = View(TemplateView, {

	"identifier" : "SwitchButtonMatrix",

	"template_name" : "themes/" + settings.THEME + "/templates/switch_buttonmatrix.html",

	modal_title : function(){
		return _("Switch Button Matrix");
	},

	get_context_data : function(self, request, kwargs){
		var context = SwitchButtonMatrix.super().get_context_data(self, request, kwargs);
		context["matrices"] = app_features.ButtonMatrix.list;

		return context;
	}

}, ModalView);

/*
* Log the observation and insert a small indicator on the page
*/
var LogFromMatrix = View(TemplateView, {
	"identifier" : "LogFromMatrix",

	"login_required" : true,

	"template_name" : "themes/" + settings.THEME + "/templates/buttonmatrix_observation.html",

	get : function(self, request, args, kwargs){
		var buttonmatrix_uuid = kwargs["buttonmatrix_uuid"],
			row = kwargs["row"],
			column = kwargs["column"];

		// read exposed field before it is being resetted
		var exposed_field = document.getElementById("id_exposed_field");
		var exposed_field_value = null;
		if (exposed_field != null){
			var exposed_field_value = exposed_field.value;
		}

		var path = app_features.ButtonMatrix.lookup[self.kwargs["buttonmatrix_uuid"]];
		ajax.GET(path, {}, function(content){
			var matrix_definition  = JSON.parse(content); //JSON.parse(atob(content));
			
			var button = matrix_definition.rows[row].columns[column];

			// create a log from the matrix button
			// load the form
			var form_uuid = matrix_definition.options.generic_form.uuid;
			var form_class = window[form_uuid];

			// find uuids for the 3 required reference fields
			var taxonomicReference_field_name = form_class.taxonomicReference,
				geographicReference_field_name = form_class.geographicReference,
				temporalReference_field_name = form_class.temporalReference;

			var data = {};

			// ORDINARY DATA
			// set the data from the button
			for (var uuid in button.extensions) {
				if (button.extensions.hasOwnProperty(uuid)) {
					data[uuid] = button.extensions[uuid];
				}
			}

			// read exposed field and fill data accordingly
			if (exposed_field_value != null){
				data[matrix_definition.options.generic_form_exposed_field.uuid] = exposed_field_value;
			}

			// REFERENCE FIELDS
			// currently the bmatrix builder is very restrictive and only allows jsonfields for reference fields

			// create the POST data for the form
			// taxon from button
			var taxon = Taxon.create(button.taxon.taxonSource, button.taxon.nameUuid, button.taxon.taxonLatname, button.taxon.taxonAuthor, button.taxon.taxonNuid);
			data[taxonomicReference_field_name + "_0"] = taxon.taxonLatname; // verbose representation
			data[taxonomicReference_field_name + "_1"] = JSON.stringify(taxon.as_json(taxon)); // the second widget is the json

			// time is always NOW
			var temporal = TemporalJSONbuilder.create();
			temporal.load_Date(temporal, new Date());
			data[temporalReference_field_name + "_0"] = temporal.verbose; // verbose representation
			data[temporalReference_field_name + "_1"] = temporal.as_text(temporal); // the second widget is the json

			// position is constantly fetched and stored in a hidden field
			var position_input = document.getElementById("matrix_current_position");
		
			var geojson = position_input.value; // read the field

			if (typeof geojson == "string" && geojson.length > 0){

				var geojson_builder = GeoJSONbuilder.create(JSON.parse(geojson));
				data[geographicReference_field_name + "_0"] = geojson_builder.verbose; // verbose representation
				data[geographicReference_field_name + "_1"] = geojson_builder.as_text(geojson_builder); // validates and sets pos
			}
			// data is ready
			// validate the data
			var form = form_class.create({"data":data});
			
			if (form.is_valid(form) == true){

				var datasetbuilder = DatasetJSONbuilder.create();

				// set reported values
				datasetbuilder.set_reported_values(datasetbuilder, form.cleaned_data);

				// set the observationform
				datasetbuilder.set_observation_form(datasetbuilder, form_uuid, function(datasetbuilder){

					var dataset = Dataset.create({ "data" : datasetbuilder.json});
					dataset.save(dataset, function(dataset){
						// insert an indicator below the matrix
						var context = {
							"dataset" : dataset
						};
						default_renderer.render(self.template_name, context, function(template_html){
							var container = document.getElementById("recent-logs");
							if (container.children.length >= 10){
								container.removeChild(container.children[0]);
							}
							container.insertAdjacentHTML("beforeend", template_html);
							InteractionManager._activate_gesture_listeners(container);
						});				
					});						
					
				});
			}
			else {
				// in general, this should only happen if the exposed field is required but was not filled
				var error_template_name = "themes/" + settings.THEME + "/templates/form_error_dialog.html";
				var context = {
					"form" : form
				};
				default_renderer.render(error_template_name, context, function(template_html){
					var title = _("Observation Form Error");
					modalDialog.open(template_html, title);
				});
			}

		});	
	}

});

// set anonymous observations according to settings


function calculateMatrixItemBackgroundcolor(matrix_item){

	var color = "";

	let max_color = -144;
	let min_color = -255;

	if (matrix_item.points_percentage >= 0.5){

		let color_span = max_color - min_color;
		let one_percent_in_points = color_span / (0.5*100);
		let percent_points_over_50 = Math.abs( (matrix_item.points_percentage*100) - (0.5*100) );
		let color_setter = percent_points_over_50 * one_percent_in_points;
		
		let r_value = Math.abs(min_color + color_setter);
		color = "rgb(" + r_value + ",243, 74)";
		
	}

	return color;
}


function getCurrentTranslation(element){

	var style = window.getComputedStyle(element);
	var matrix = new WebKitCSSMatrix(style.transform);
	var translation = matrix.m41;

	return translation;
}

/* covers both species lists and identificatoin keys */
var NatureGuideView = View(TemplateView, {

	"identifier" : "NatureGuideView",
	"template_name" : "themes/" + settings.THEME + "/templates/nature_guide.html",

	"always_load_appbar" : true,

	get : function(self, request, args, kwargs){
		
		if ("noautomatics" in request.GET){
			app.automatics = false;
		}
		else if ("automatics" in request.GET) {
			app.automatics = true;
		}

		var keynodes = document.getElementById("keynodes-page-new");
		if (keynodes != null){
			//ToggleMatrixItems.slideleft(ToggleMatrixItems);
			//setTimeout(function(){
				//ToggleMatrixItems.close(ToggleMatrixItems);
			//},500)
		}

		// pass to appheader
		self.initial_kwargs["filter_available"] = false;

		var uuid = kwargs["nature_guide_uuid"];

		self._get_nature_guide(uuid, function(nature_guide){

			var node_uuid = kwargs["node_uuid"] || nature_guide.startNodeUuid;

			var current_node = nature_guide.tree[node_uuid];

			var context = {
				"node" : current_node,
				"uuid" : uuid,
				"filter_available" : false,
				"automatics" : app.automatics
			};
			
			if (current_node.matrixFilters.length > 0){
				self.initial_kwargs["filter_available"] = true;
				context["filter_available"] = true;
			}

			self.initial_kwargs["childrenCount"] = current_node.childrenCount;
			context["childrenCount"] = current_node.childrenCount;


			document.addEventListener("identification_complete", NatureGuideView.on_identification_complete);

			self.render_to_response(self, context);

		});

	},

	on_identification_complete : function(event){
		window.scrollTo(0,0);
	},

	on_page_leave : function(event){
		document.removeEventListener("identification_complete", NatureGuideView.on_identification_complete);
	},

	_get_nature_guide : function(uuid, callback){

		var self = this;

		// only fetch the key for the root node
		if (app.hasOwnProperty("current_nature_guide") && uuid == app.current_nature_guide.uuid){
			callback(app.current_nature_guide);
		}
		else {
			var url = app_features.NatureGuide.lookup[uuid];
	
			ajax.GET(url, {}, function(content){

				var nature_guide = JSON.parse(content); //JSON.parse(atob(content));
				app.current_nature_guide = nature_guide
				callback(nature_guide);				

			});
		}		

	},

	/* the nodes are loaded after rendering the page */
	post_render : function(self, args, kwargs){

		//ToggleMatrixItems.close(ToggleMatrixItems);

		var uuid = kwargs["nature_guide_uuid"];

		self._get_nature_guide(uuid, function(nature_guide){

			var node_uuid = kwargs["node_uuid"] || nature_guide.startNodeUuid;
			self.current_node = nature_guide.tree[node_uuid];

			var result_action = nature_guide.options["resultAction"];
			
			// render and insert node template
			var node_template = "themes/" + settings.THEME + "/templates/nature_guide_nodes.html"

			ajax.GET(node_template, {}, function(template){
			
				var many_children = false;
				if (self.current_node.childrenCount > 30){
					many_children = true;
				}


				var context = {
					"node" : self.current_node,
					"uuid" : kwargs["nature_guide_uuid"],
					"many_children" : many_children,
					"result_action" : result_action
				};

				var template_html = Handlebars.compile(template)(context);

				var container = document.getElementById("keynodes");
				
				Pagemanager._insert(container, template_html, args, kwargs);
				
			});

		});

	},

	_attach_identification_event_listeners : function (){

		var identificationForm = document.getElementById("matrix-filters-form");
		var inputs = identificationForm.querySelectorAll('input[type=radio], input[type=checkbox]');

		const keynodes_container = document.getElementById("keynodes");
		const sorted_out_keynodes_container = document.getElementById("sorted-out-keynodes");

		for (let i=0; i<inputs.length; i++){
			let input = inputs[i];

			// matrix items
			input.addEventListener("turnedOn", function(event){

			
			});
			
			// matrix items
			input.addEventListener("turnedOff", function(event){
				
			
			});
			
			// strict mode
			input.addEventListener("possible", function(event){

				
				let input = event.currentTarget;
			
				if (event.detail.matrix_filter.matrixFilterType == "RangeFilter"){
				}
				else {
					input.parentElement.classList.remove("matrix-filter-inactive");
				}

			});
			
			// strict mode
			input.addEventListener("impossible", function(event){
				
				let input = event.currentTarget;
			
				if (event.detail.matrix_filter.matrixFilterType == "RangeFilter"){
				}
				else {
					input.parentElement.classList.add("matrix-filter-inactive");
				}

			});
		}

		var range_inputs = identificationForm.querySelectorAll('input[type=range]');

		function onClear(event){
			let matrix_filter_uuid = event.currentTarget.getAttribute("data-uuid");
			let slider = document.getElementById(matrix_filter_uuid + "_range");
			let unit_and_clear_button_container = document.getElementById(matrix_filter_uuid + "-onactive");

			unit_and_clear_button_container.style.display = "none";

			let value_container = document.getElementById("output-" + matrix_filter_uuid);
			value_container.textContent = "off";

			slider.value = "";

			
		}
	
		for (let r=0; r<range_inputs.length; r++){
			let range_input = range_inputs[r];

			let matrix_filter_uuid = range_input.name;

			let clear_button = document.getElementById(matrix_filter_uuid + "-clearbtn");

			clear_button.addEventListener("click", function(event){
				onClear(event);

				let matrix_filter_uuid = event.currentTarget.getAttribute("data-uuid");
				let slider = document.getElementById(matrix_filter_uuid + "_range");
				let clear_event = new Event("clear");
				slider.dispatchEvent(clear_event);
			});

			range_input.addEventListener("input", function(event){

				let matrix_filter_uuid = event.currentTarget.name;

				let unit_and_clear_button_container = document.getElementById(matrix_filter_uuid + "-onactive");
				unit_and_clear_button_container.style.display = "";

				let value_container = document.getElementById("output-" + matrix_filter_uuid);
				value_container.textContent = event.currentTarget.value;
						
			});

			range_input.addEventListener("turnedOff", onClear);

		}

		// RESTRICTIONS
		identificationForm.addEventListener("activate-matrix-filter", function(event){

			let matrix_filter = event.detail.matrix_filter;
			let container = document.getElementById(matrix_filter.uuid);
			container.classList.remove("restriction-active");

		});
		
		identificationForm.addEventListener("deactivate-matrix-filter", function(event){

			let matrix_filter = event.detail.matrix_filter;
			let container = document.getElementById(matrix_filter.uuid);
			container.classList.add("restriction-active");
			
		});

		identificationForm.addEventListener("activate-matrix-item", function(event){

			let matrix_item = event.detail.matrix_item;
			let matrix_item_element = document.getElementById(matrix_item.uuid);
			matrix_item_element.style.opacity = 1;

			keynodes_container.appendChild(matrix_item_element);
			
		});

		identificationForm.addEventListener("deactivate-matrix-item", function(event){

			let matrix_item = event.detail.matrix_item;
			let matrix_item_element = document.getElementById(matrix_item.uuid);
			matrix_item_element.style.opacity = 0.3;

			sorted_out_keynodes_container.appendChild(matrix_item_element);
			
		});

		// FLUID MODE
		identificationForm.addEventListener("update-matrix-item", function(event){

			let matrix_item = event.detail.matrix_item;
			
			let matrix_item_element = document.getElementById(matrix_item.uuid);

			let order =  Math.ceil( matrix_item.points_percentage * 100 ) * (-1);

			matrix_item_element.style.order = order;
			
			// update point percentage
			let points_span = document.getElementById(matrix_item.uuid + "-points");
			if (matrix_item.points > 0){
				//points_span.textContent = parseInt(matrix_item.points_percentage * 100) + "% (" + matrix_item.points + "/" + matrix_item.maxPoints + ")";
				points_span.textContent = "" + matrix_item.points + "/" + matrix_item.maxPoints;
			}
			else {
				points_span.textContent = "0";
			}


			let bgcolor = calculateMatrixItemBackgroundcolor(matrix_item);
			points_span.parentElement.parentElement.style.backgroundColor = bgcolor;
			
		});

		function onFinishedIdentificationStep(event){

			if (app.automatics == true){
			
				var mqList = window.matchMedia("(min-width: 768px)");
				if (mqList.matches == true){
					HttpResponseRedirect(reverse("next_identification_step"));
				}
				else {
					ToggleMatrixItems.open(ToggleMatrixItems);
				}
			}
		}

		//identificationForm.addEventListener("matrix-item-100-percent", onFinishedIdentificationStep);

		identificationForm.addEventListener("identification-finished", onFinishedIdentificationStep);

		
	},

	_attach_pan_listeners : function(){
		var page = document.getElementById("nature-guide-container");

		var options = {
			supportedGestures : [Pan],
			supportedDirections: Directions.Horizontal,
			handleTouchEvents : false
			//DEBUG:true
		};
		
		var panListener = new PointerListener(page, options);

		panListener.on("swipeleft", function(event){
			if (screen.width < 768){
				ToggleMatrixItems.open(ToggleMatrixItems);
			}
		});

		page.addEventListener("swiperight", function(event){
			if (screen.width < 768){
				ToggleMatrixItems.close();
			}
		});

		var ticking = false;
		var animationFrameId = null;
		var start_x = 0;
		var pan_active = false;		

		function requestElementUpdate(transform, wait) {

			wait = wait || false;
		
			var transformString = "translate3d(" + transform.translate.x + "px, " + "0, 0)";
			
			//console.log(transformString);
			
			if (!ticking) {
			
				animationFrameId = requestAnimationFrame(function (timestamp) {

					//console.log("update with " + transformString)
			
					page.style.webkitTransform = transformString;
					page.style.mozTransform = transformString;
					page.style.transform = transformString;
				
					animationFrameId = null;
					ticking = false;
			
				});
			
				ticking = true;
			}
			else if (wait == true){
				//console.log("WAITING")
				setTimeout(function(){
					requestElementUpdate(transform, true);
				}, 100);
			}
		
		}

		function onPan(event){

			if (pan_active == true){

				//console.log(event.detail.global.deltaX);

				var deltaX = start_x + event.detail.global.deltaX;

				var transform = {
					translate : {
						x: deltaX
					}
				};

				requestElementUpdate(transform);
			}
		}

		function onPanEnd(event){

			//console.log("panend");

			page.classList.remove("notransition");

			var deltaX = event.detail.global.deltaX
			//console.log(deltaX);
			//console.log(screen.width)

			if (pan_active == true){

				if (event.detail.recognizer.isSwipe == false){

					let translation = getCurrentTranslation(page);

					if (event.detail.global.direction == "left"){
						if (translation < (-screen.width / 3)){
							//console.log("panend noswipe call tmi open");
							ToggleMatrixItems.open(ToggleMatrixItems);
						}
						else {
							//console.log("panend noswipe call tmi close");
							ToggleMatrixItems.close(ToggleMatrixItems);
						}
					}
					else {
						if (translation > (-screen.width * (2/ 3))){
							//console.log("panend noswipe call tmi open");
							ToggleMatrixItems.close(ToggleMatrixItems);
						}
						else {
							//console.log("panend noswipe call tmi close");
							ToggleMatrixItems.open(ToggleMatrixItems);
						}
					}
					
				}
				else {
					//console.log("swipe detected")
				}
				pan_active = false;
			}
			else {

			}
			
		}

		function onPanStart(event){
			//console.log(event.detail.live.direction)
			//console.log(Directions.Horizontal)
			
			if (Directions.Horizontal.indexOf(event.detail.live.direction) >= 0 && screen.width < 768){

				pan_active = true;

				page.classList.add("notransition");
				let style = window.getComputedStyle(page);
				let matrix = new WebKitCSSMatrix(style.transform);
				let translateX =  matrix.m41;

				start_x = translateX;
			}
		}
		
		page.addEventListener("panleft", onPan);
		page.addEventListener("panright", onPan);
		page.addEventListener("panend", onPanEnd);
		page.addEventListener("panstart", onPanStart);

	},

	post_finished : function(args, kwargs){
		var self = this;
		var uuid = kwargs["nature_guide_uuid"];

		self._get_nature_guide(uuid, function(nature_guide){

			var node_uuid = kwargs["node_uuid"] || nature_guide.startNodeUuid;
			self.current_node = nature_guide.tree[node_uuid];

			if (Object.keys(self.current_node.matrixFilters).length > 0){

				//self._attach_matrix_filter_listeners();

				var data = {
					"items" : self.current_node.children,
					"matrixFilters" : self.current_node.matrixFilters
				};

				var options = {
					"mode" : self.current_node.identificationMode
				};


				function get_items(callback){
					callback(data);
				}

				if (app.identification != null){
					app.identification.destroy();
				}

				app.identification = new IdentificationMatrix('matrix-filters-form', get_items, options);

				self._attach_identification_event_listeners();
				self._attach_pan_listeners();

				// check if overlay is open, from history
				var page = document.getElementById("nature-guide-container");
				let translation = getCurrentTranslation(page);
				
				if (translation < 0){

					// wait for pagechanged event to be finished, ugly race condition solution
					setTimeout(function(){
						page.setAttribute("data-is-open", 1);
						OverlayView.close_current_overlay = function(){
							ToggleMatrixItems.close();
							document.body.classList.remove("noscroll");
						}
					}, 500);
					
				}


			}
		});

	}

});


function switchImage(self, request, args, kwargs){

	var currentTarget = kwargs["currentTarget"];

	var primary_image_id = currentTarget.getAttribute("data-primary-image-id");
	var primary_image = document.getElementById(primary_image_id);

	// check if a popover is already present
	var primary_imageUrl = currentTarget.getAttribute("data-primary-image-url");
	var secondaryImageUrl = currentTarget.getAttribute("data-secondary-image-url");

	if (primary_image.style.backgroundImage.indexOf(primary_imageUrl) >=0){
		primary_image.style.backgroundImage = "url(" + secondaryImageUrl + ")";
		currentTarget.src = primary_imageUrl;
	}
	else {
		primary_image.style.backgroundImage = "url(" + primary_imageUrl + ")";
		currentTarget.src = secondaryImageUrl;
	}

}


var NextIdentificationStep = View(TemplateView, {

	"identifier" : "NextIdentificationStep",
	
	template_name : "themes/" + settings.THEME + "/templates/next_identification_step.html",


	modal_title : function(self){
		return _("Next step");
	},

	get_context_data : function(self, kwargs){

		var return_result_length = 3;

		// top 3 results, sorted from high to low
		var matrix_items_sorted = [];

		for (let matrix_item_uuid in MATRIX_ITEMS){
			let matrix_item = MATRIX_ITEMS[matrix_item_uuid];
			if (matrix_items_sorted.length == 0){
				matrix_items_sorted.push(matrix_item);
			}
			else {

				let is_inserted = false;

				for (let i=0; i<matrix_items_sorted.length; i++){
					let sorted_matrix_item = matrix_items_sorted[i];
					if (matrix_item.points_percentage > sorted_matrix_item.points_percentage){
						// insert BEFORE sorted_matrix_item
						matrix_items_sorted.splice(i, 0, matrix_item);
						is_inserted = true;
						break;
					}
				}

				if (is_inserted == false){
					matrix_items_sorted.push(matrix_item);
				}
			}
		}

		var top_matrix_items = [];

		for (let i=0; i < matrix_items_sorted.length; i++){

			let matrix_item = matrix_items_sorted[i];

			if (top_matrix_items.length < return_result_length){

				let nature_guide_item = app.identification.get_nature_guide_item(matrix_item.uuid);

				if (nature_guide_item == null){
					throw new Error("Could not find nature_guide_item for matrix_item " + matrix_item.name);
				}
				else {
					nature_guide_item = JSON.parse(JSON.stringify(nature_guide_item));

					let node = document.getElementById(nature_guide_item.uuid);
					nature_guide_item.link = node.firstElementChild.getAttribute("link");

					nature_guide_item.points = matrix_item.points;
					nature_guide_item.maxPoints = matrix_item.maxPoints;
					nature_guide_item.points_percentage = parseInt(matrix_item.points_percentage*100);

					let bgcolor = calculateMatrixItemBackgroundcolor(matrix_item);
					nature_guide_item.bgcolor = bgcolor;

					top_matrix_items.push(nature_guide_item);
				}
			}
			else {
				break;
			}
		}

		var context = {
			'matrix_items' : top_matrix_items
		};

		return context;

	},

	close : function(self, args, kwargs){
		modalDialog._close();
	}


}, ModalView)


var ThemeTextView = View(TemplateView, {

	"identifier" : "ThemeTextView",
	"template_name" : "themes/" + settings.THEME + "/templates/theme_text.html",

	"async_context" : true,

	"page_size" : 10,

	get_context_data : function(self, kwargs, callback){

		ThemeTextView.super().get_context_data(self, kwargs, function(context){

			var page = self.request.GET["page"] || 1;
			page = parseInt(page);
			
			context["current_page"] = page;

			var previous_page = page == 1 ? null : page - 1;

			context["previous_page"] = previous_page;

			context["key"] = self.kwargs.key;

			if (self.kwargs.key == "about_app"){
				context["app_version"] = settings.APP_VERSION;
			}

			if (self.kwargs.key == "app_sources"){
				ajax.getJSON("licence_registry.json", {}, function(licence_registry){

					var licences = [];

					var keys = Object.keys(licence_registry["licences"]);
			
					var start = self.page_size * page;
					var end = start + self.page_size + 1;

					if (keys.length > end){
						var next_page = page + 1;
					}
					else {
						var next_page = null;
					}

					context["next_page"] = next_page;

					var usable_keys = keys.slice(start, end);
					
					for (let k=0; k<usable_keys.length; k++){
						let key = usable_keys[k];
						var licence = {
							"image" : key,
							"licence" : licence_registry["licences"][key]
						};

						licences.push(licence);
					}
					context["licences"] = licences;
					callback(context);
				});
			}
			else {
				callback(context);
			}
		});
	}
});


var Sidemenu = View(OverlayView, {

	identifier : "Sidemenu",

	get_dom_element : function(){
		var sidemenu = document.getElementById(this.identifier);
		return sidemenu;
	},

	open : function(self){
		var sidemenu = this.get_dom_element();
		sidemenu.classList.add("showmenu");
		Sidemenu.super().open(self);
	},
	
	close : function(){
		var sidemenu = this.get_dom_element(); 
		sidemenu.classList.remove("showmenu");
		Sidemenu.super().close();
	},

	toggle : function(self, request, args, kwargs){

		if (typeof self == "undefined" || self == null){
			var self = Object.create(this);
		}

		var sidemenu = this.get_dom_element();

		if (sidemenu.classList.contains("showmenu") || request.GET.action == "selected" || request.GET.action == "hide") {
			self.close(self);
		}
		else {
			self.open(self);
		}

	}

});

var ToggleMatrixItems = View(OverlayView, {

	identifier : "ToggleMatrixItems",

	toggle_element_id : "nature-guide-container",

	toggle_class : "keynodes-hidden",

	respond_to_pagechaged : false,

	_animate : function(self, transformString){
		
		var page = document.getElementById(this.toggle_element_id);

		page.classList.remove("notransition");
			
		var animationFrameId = requestAnimationFrame(function (timestamp) {

			console.log("TMI update with " + transformString)
	
			page.style.webkitTransform = transformString;
			page.style.mozTransform = transformString;
			page.style.transform = transformString;
		});

	},

	open : function(self){

		console.log("TMI open");

		var page = document.getElementById(this.toggle_element_id);
		var is_open = page.getAttribute("data-is-open");

		if (typeof self == "undefined" || self == null){
			self = this;//Object.create(this);
		}

		var transformString = "translate3d(-" + screen.width + "px, " + "0, 0)";
				
		self._animate(self, transformString);

		document.getElementById("toggleMatrixItemsButton").style.display="none";

		if (is_open == "0"){
			ToggleMatrixItems.super().open(self);
		}

		page.setAttribute("data-is-open", 1);
		document.body.classList.remove("noscroll");
		/*if (typeof self == "undefined" || self == null){
			var self = Object.create(this);
		}

		var filters = document.getElementById(this.toggle_element_id);

		if (filters.classList.contains(this.toggle_class)){
			filters.classList.remove(this.toggle_class);

			filters.scrollTo(0,0);

			document.body.classList.add("modal-open");
			ToggleMatrixItems.super().open(self);
		}*/
	},
	close : function(){

		console.log("TMI close");

		var page = document.getElementById(this.toggle_element_id);
		var is_open = page.getAttribute("data-is-open");

		var transformString = "translate3d(0, 0, 0)";
				
		this._animate(this, transformString);

		document.getElementById("toggleMatrixItemsButton").style.display="";

		if (is_open == "1"){
			ToggleMatrixItems.super().close();
		}

		page.setAttribute("data-is-open", 0);
		/*var filters = document.getElementById(this.toggle_element_id);
		filters.classList.add(this.toggle_class);
		filters.classList.remove(this.slideleft_class);

		document.body.classList.remove("modal-open");
		ToggleMatrixItems.super().close();*/
	},

	toggle : function(self, request, args, kwargs){

		if (typeof self == "undefined" || self == null){
			var self = Object.create(this);
		}

		var filters = document.getElementById(this.toggle_element_id);

		if (filters.classList.contains(this.toggle_class)){
			self.open(self);
		}
		else {
			self.close(self);
		}
	}

});

var reset_matrix_filters = function(self, request, args, kwargs){
	app.identification.reset();
	kwargs['currentTarget'].blur();
};


// OnlineContentView
// - for both preview and view
var OnlineContentView = View(RemoteView, {

	"identifier" : "OnlineContentView",
	"template_name" : "themes/" + settings.THEME + "/templates/online_content.html",

	"needs_internet" : true,

	get_api_url : function(self){
		var url = "online-content";
		return url;
	},

	get_api_url_params : function(self){
		var params = {
			"slug" : self.kwargs["slug"]
		};

		if (self.kwargs.hasOwnProperty("preview_token")) {
			params["preview_token"] = self.kwargs["preview_token"];
		}

		return params;
	}

});


// FactSheetView
// - for both preview and view
// ATTENTION: used by appKit

var TemplateContentView = View(RemoteView, {

	"identifier" : "TemplateContentView",
	"template_name" : "template_content/pages/home/",


	get : function(self, request, args, kwargs){

	
		self.get_data(self, function(data){

			self.template_name = data['templatePath'];

			// render page
			var context = self.get_context_data(self, kwargs);
			context["data"] = data;

			self.render_to_response(self, context);

		}, self.on_error);
	},
	
	
	get_local_data : function (self, onsuccess, onerror){
		
		let slug = self.kwargs["slug"];
		let contents_path = app_features.TemplateContent.slugs[slug];
		self.perform_request(self, contents_path, 'GET', 'JSON', {}, onsuccess, onerror);
		
	},
	
	get_preview_data : function(self, onsuccess, onerror){
		// settings.API_URL points to the app kit if settings.PREVIEW == true
		var url = '' + settings.API_URL + 'template-content-preview/' + self.kwargs["slug"] + "/";
		self.perform_request(self, url, 'GET', 'JSON', {}, onsuccess, onerror);
	},
	
	get_data : function(self, onsuccess, onerror){

		if (settings.PREVIEW == true){
			self.get_preview_data(self, onsuccess, onerror);
		}
		else {
			self.get_local_data(self, onsuccess, onerror);
		}

	}
});


var TemplateContentModal = View(TemplateView, {

	"identifier" : "FactSheetModal",
	
	template_name : "themes/" + settings.THEME + "/templates/fact_sheet_modal.html",

	"async_context" : true,


	_set_fact_sheet : function(self, fact_sheet_id, callback){
		let factSheets_path = app_features.FactSheets.list[0].path;

		ajax.GET(factSheets_path, {}, function(content){

			let factSheets = JSON.parse(content); //JSON.parse(atob(content));

			self.factSheets = factSheets;
			self.fact_sheet = factSheets["factSheets"][fact_sheet_id];

			callback();

		});
	},


	dispatch : function(self, request, args, kwargs){
		var self = Object.create(this);
		self._set_fact_sheet(self, kwargs["fact_sheet_id"], function(){
			FactSheetModal.super().dispatch(self, request, args, kwargs);
		});
	},

	get_context_data : function(self, kwargs, callback){

		let context = {};

		let factSheets_folder = app_features.FactSheets.list[0].folder;

		let path = factSheets_folder + "/" + self.fact_sheet["localized"][app.language]["path"];

		ajax.GET(path, {}, function(html){
			context["fact_sheet_html"] = html;

			callback(context);
		})		
	},


	modal_title : function(self){
		return i18next.t('plainȵ' + self.fact_sheet.title);
	},

	close : function(self, args, kwargs){
		OverlayView.close_current_overlay();
	}

}, ModalView);



var OverviewImageModal = View(TemplateView, {

	"identifier" : "OverviewImageModal",
	
	template_name : "themes/" + settings.THEME + "/templates/overview_image_modal.html",


	get_context_data : function(self, kwargs){
		const element = document.getElementById("overview-img");

		let context = {
			"overviewImageURL" : element.getAttribute("data-overview-image-url")
		};
	
		return context;		
	},

	modal_title : function(self){
		return "Overview";
	},

	close : function(self, args, kwargs){
		OverlayView.close_current_overlay();
	}

}, ModalView);

// header views
var BaseHeaderView = View(TemplateView, {

	"online_content_container_id" : "main-nav",
	"async_context" : true,

	get_context_data : function(self, kwargs, callback){

		var context = {};
		context["preview"] = settings.PREVIEW;
		
		callback(context);
	},

	render_to_response : function(self, context){

		// run context processors
		var context = Pagemanager._process_context(self.request, context);

		default_renderer.render(self.template_name, context, function(template_html){
			var target_element = document.getElementById("appbar-container");

			Pagemanager._insert(target_element, template_html, self.args, self.initial_kwargs);			

			self.post_render(self, self.args, self.initial_kwargs);
		});
	}

}, OnlineContentMixin);


var DefaultAppbar = View(BaseHeaderView, {

	"identifier" : "DefaultAppbar",
	"template_name" : "themes/" + settings.THEME + "/templates/appbars/default.html",
	"async_context" : true,

	get_context_data : function(self, kwargs, callback){

		DefaultAppbar.super().get_context_data(self, kwargs, function(context){

			_get_categories(function(categories){

				context["categories"] = categories;

				context["backbutton"] = true;

				var sponsors = false;
				if (settings.SPONSORS_DISABLED != false){
					sponsors = true;
				}
				context["sponsors"] = sponsors;

				callback(context);

			});

		});

	}

});


var HomeAppbar = View(BaseHeaderView, {

	"identifier" : "HomeAppbar",
	"template_name" : "themes/" + settings.THEME + "/templates/appbars/default.html",
	"async_context" : true,

	get_context_data : function(self, kwargs, callback){

		HomeAppbar.super().get_context_data(self, kwargs, function(context){

			_get_categories(function(categories){

				context["categories"] = categories;

				context["backbutton"] = false;

				callback(context);
			});
			
		});

	}

});


// toggle an elements visibility
var Toggle = View(TemplateView, {
	"identifier" : "Toggle",

	get : function(self, request, args, kwargs){
		var element = document.getElementById(kwargs["element_id"]);

		if (element.classList.contains("closed")){
			element.classList.remove("inback");
			element.classList.remove("closed");
		}
		else {
			element.classList.add("closed");
			
			setTimeout(function(){
				element.classList.add("inback");
			}, 400);
		}
	}

});


var AlphabetMixin = {

	add_alphabet_buttons : function(self){
	
		var alphabet_links = document.getElementsByClassName("alphabet-link");	
		
		for (let g=0; g<alphabet_links.length; g++){
			let alphabet_link = alphabet_links[g];
			var hammertime = new Hammer(alphabet_link, {});
			hammertime.on("tap", function(event) {
				let element_id = event.target.getAttribute("jumpto");
				let element = document.getElementById(element_id);
				self.scrollToTargetAdjusted(self, element);
			});
		}
		
		var alphabet_select = document.getElementById("alphabet-select");
		alphabet_select.addEventListener("change", function(event){
			let element_id = alphabet_select.value;
			let element = document.getElementById(element_id);
			self.scrollToTargetAdjusted(self, element);
		});
	
	},
	
	add_search : function (self) {
	
		var search_inputs = document.getElementsByClassName("alphabet-search");
		for (let i=0; i<search_inputs.length; i++){
		
			let search_input = search_inputs[i];
			let results_container_id = search_input.getAttribute("results-container");
			let results_container = document.getElementById(results_container_id);
			
			search_input.addEventListener("keyup", function(event){
				self.search_data(self, event);
			});
			
			search_input.addEventListener("blur", function(event){
				var input = event.target;

				var results_container_id = input.getAttribute("results-container");
				var results_container = document.getElementById(results_container_id);
				
				// wait for mouseup to be able to click on a search result
				results_container.classList.add("hidden");
				input.value = "";

			});
			
			results_container.addEventListener('mousedown', function(event) {
			   event.preventDefault();
			   event.stopPropagation();
			});
			
		}
	
	},

	// called from template
	jumpTo : function(self, request, args, kwargs){

		var target = kwargs.currentTarget;
		var term = target.getAttribute("data-term");
		var element_id = "alphabet-entry-" + term;
		var element = document.getElementById(element_id);
		
		AlphabetMixin.scrollToTargetAdjusted(self, element);
		
		target.parentElement.classList.add("hidden");
		var input_id = target.parentElement.getAttribute("data-input-id");
		var input = document.getElementById(input_id);
		input.value = "";
		
	},

	scrollToTargetAdjusted : function(self, element){
	
		var subheader = document.getElementById("alphabet-bar");
		
		var headerOffset = 220;
		
		if (subheader.offsetParent == null){
			headerOffset = 50;
		}
	
		var elementPosition = element.getBoundingClientRect().top;
		var offsetPosition = elementPosition + window.pageYOffset - headerOffset;
	  
		window.scrollTo({
			 top: offsetPosition,
			 behavior: "smooth"
		});
	},
	
	search_data : function(self, event){
		// search all names, bith scientific and vernacular, always
		
		var max_results = 7;

		var input = event.target;
		var searchtext = input.value;
		var results_container_id = input.getAttribute("results-container");
		var results_container = document.getElementById(results_container_id);
		
		if (searchtext.length < 3){
			results_container.classList.add("hidden");
			results_container.textContent = "";
		}
		else {
			
			var results = self.perform_search(self, searchtext, max_results);
			
			var context = {
				"results" : results
			};

			var template_html = Handlebars.compile( self.search_results_template )(context);

			results_container.innerHTML = template_html;
		
			results_container.classList.remove("hidden");
		}
	}
};


var GlossaryView = View(TemplateView, {

	"identifier" : "GlossaryView",
	"template_name" : "themes/" + settings.THEME + "/templates/glossary.html",
	async_context : true,
	
	glossary: null,
	
	search_results_template : '{{#if results}}{{#each results}}<div class="tap" action="GlossaryView.jumpTo" data-term="{{ term }}">{{ matched_text }}</div>{{/each}}{{else}}<div>{{t "No results found"}}</div>{{/if}}',
	
	get_context_data : function(self, kwargs, callback){
	
		var glossary_uuid = kwargs["glossary_uuid"];
		var csv_path = null;
		
		if (app_features.Glossary.localized.hasOwnProperty(app.language)){
			var show_used_terms_only = self.request.GET.usedTerms == "1";
			
			if (show_used_terms_only == true){
				csv_path = app_features.Glossary.localized[app.language]["usedTermsCsv"];
			}
			else {
				csv_path = app_features.Glossary.localized[app.language]["allTermsCsv"];
			}
		}
	
		var show_used_terms_only = self.request.GET.usedTerms == "1";
		var url = self.get_glossary_url(self);

		GlossaryView.super().get_context_data(self, kwargs, function(context){
		
			// load language specific glossary
			ajax.GET(url, {}, function(content){
			
				self.glossary = JSON.parse(content);

				context["glossary"] = self.glossary;
				context["glossary_uuid"] = glossary_uuid;
				context["show_used_terms_only"] = show_used_terms_only;
				context["csv_path"] = csv_path;

				callback(context);			

			});
		
		});
	},
	
	get_glossary_url : function(self){
	
		var show_used_terms_only = self.request.GET.usedTerms == "1";
		
		if (app_features.Glossary.localized.hasOwnProperty(app.language)){
			
			if (show_used_terms_only == true){
				var url = app_features.Glossary.localized[app.language]["usedTerms"];
			}
			else {
				var url = app_features.Glossary.localized[app.language]["allTerms"];
			}
		}
		else {
			var url = app_features.Glossary.path;
		}
		return url;
	},
	
	post_render : function(self, args, kwargs){
	
		self.add_alphabet_buttons(self);
		self.add_search(self);
	
	},
	
	perform_search : function(self, searchtext, max_results) {

		var results = [];
		var result_count = 0;
	
		var start_letter = searchtext[0].toUpperCase();
		
		if (self.glossary.hasOwnProperty(start_letter)){
			var glossary_entries = self.glossary[start_letter];
			
			for (let term in glossary_entries){
			
				if (result_count > max_results){
					break;
				}
				
				let glossary_entry = glossary_entries[term];
				
				let result = {
					"matched_text" : null,
					"term" : term,
					"glossary_entry" : glossary_entry
				};
				
				if (term.toLowerCase().startsWith(searchtext.toLowerCase())){
					result["matched_text"] = term;
					results.push(result);
					result_count++;
				}
				else {
					let synonyms = glossary_entry["synonyms"];
					for (let s=0; s<synonyms.length; s++){
						let synonym = synonyms[s];
						if (synonym.toLowerCase().startsWith(searchtext.toLowerCase())){
							result["matched_text"] = synonym;
							results.push(glossary_entry);
							result_count++;
						}
					}
				}
			}
		}
		
		return results;
			
	}
	
}, AlphabetMixin);


var glossary = function(self, request, args, kwargs){

	var template_name = "themes/" + settings.THEME + "/templates/glossary_lookup.html";

	var currentTarget = kwargs["currentTarget"];

	// check if a popover is already present
	var aria_describedby = currentTarget.getAttribute("aria-describedby");

	if (typeof(aria_describedby) == "string" && aria_describedby.indexOf("popover") == 0){
		$(currentTarget).popover("hide");
	}

	else {

		var term_b64 = currentTarget.getAttribute("data-term");
		var term = atob(term_b64);

		var glossary_path = app_features["Glossary"]["path"];

		ajax.GET(glossary_path, {}, function(content){

			var glossary = JSON.parse(content); //JSON.parse(atob(content));

			var glossary_entry = glossary["glossary"][term];

			ajax.GET(template_name, {}, function(template){

				var context = {
					"term" : term,
					"glossary_entry" : glossary_entry
				};

				var template_html = Handlebars.compile(template)(context);

				var element = $(currentTarget)

				element.popover({
					"content" : template_html,
					"html" : true,
					"placement" : "top",
					"trigger" : "manual"
				});

				element.popover("toggle");

				if (kwargs.event.pointerType == "touch"){
					var event_handler = "touchstart";
				}
				else {
					var event_handler = "mousedown";
				}

				var hide_popover = function(event){
					element.popover("hide");
					event.target.removeEventListener(event_handler, hide_popover); //arguments.callee); use hide_popover instead of arguments.callee, which is forbidden in strict mode
				};

				document.addEventListener(event_handler, hide_popover);
				
			});
	
		});
	}

}


var TaxonProfilesRegistry = View(TemplateView, {

	"identifier" : "TaxonProfilesRegistry",
	"template_name" : "themes/" + settings.THEME + "/templates/taxon_profiles_registry.html",
	async_context : true,
	
	search_results_template : '{{#if results}}{{#each results}}<div class="tap" action="TaxonProfilesRegistry.on_select" data-taxon-source="{{ taxonSource }}" data-name-uuid="{{ nameUuid }}">{{ matched_text }}</div>{{/each}}{{else}}<div>{{t "No results found"}}</div>{{/if}}',
	
	get_context_data : function(self, kwargs, callback){
	
		var use_vernacularNames = self.request.GET.vernacular == "1";

		var search_index_url = app_features.TaxonProfiles.search;
		
		self.search_index = null;

		TaxonProfilesRegistry.super().get_context_data(self, kwargs, function(context){
		
			ajax.GET(search_index_url, {}, function(content){
			
				self.search_index = JSON.parse(content);
				
				let has_vernacularNames = Object.keys(self.search_index.vernacular[app.language]).length > 0 ? true : false;

				context["search_index"] = self.search_index;
				context["use_vernacularNames"] = use_vernacularNames;
				
				context["vernacularNames"] = self.search_index.vernacular[app.language];

				context["has_vernacularNames"] = has_vernacularNames
				callback(context);			

			});
		
		});
	},
	
	post_finished : function(args, kwargs){
	
		var self = this;
	
		var search_index_url = app_features.TaxonProfiles.search;
		
		ajax.GET(search_index_url, {}, function(content){
		
			self.search_index = JSON.parse(content);
		
			self.add_alphabet_buttons(self);
			self.add_search(self);
		});
	
	},
	
	perform_search : function(self, searchtext, max_results) {
	
		var results = [];
		var result_count = 0;
		
		var start_letter = searchtext[0].toUpperCase();
	
		if (self.search_index != null){
			var vernacularNames = self.search_index.vernacular[app.language];
			
			if (start_letter in vernacularNames) {
				var names_list = vernacularNames[start_letter];
				
				for (let n=0; n<names_list.length; n++){
				
					if (result_count > max_results){
						break;
					}
					
					let taxon = names_list[n];
					
					
					if (taxon.name.toLowerCase().startsWith(searchtext.toLowerCase())){
						let result = {
							"matched_text" : taxon.name,
							"taxonSource" : taxon.taxonSource,
							"taxonLatname" : taxon.taxonLatname,
							"taxonAuthor" : taxon.taxonAuthor,
							"nameUuid" : taxon.nameUuid,
						};
						results.push(result);
						result_count++;
					}
				}
			}
			
			if (start_letter in self.search_index.taxonLatname) {
				
				let taxa = self.search_index.taxonLatname[start_letter];
				for (let t=0; t<taxa.length; t++) {
				
					if (result_count > max_results){
						break;
					}

					let taxon = taxa[t];
					
					//let taxon = taxa[full_taxonLatname];
					
					if (taxon.isSynonym == true){
						continue;
					}
				
					if (taxon.taxonLatname.toLowerCase().startsWith(searchtext.toLowerCase()) ){
					
						let result = {
							"matched_text" : taxon.taxonLatname,
							"taxonSource" : taxon.taxonSource,
							"taxonLatname" : taxon.taxonLatname,
							"taxonAuthor" : taxon.taxonAuthor,
							"nameUuid" : taxon.nameUuid,
						};
						results.push(result);
						result_count++;
					}
				}
				
			}
			
		}
		
		return results;
	},
	
	on_select : function(self, request, args, kwargs){

		var target = kwargs.currentTarget;
		
		target.parentElement.classList.add("hidden");
		var input_id = target.parentElement.getAttribute("data-input-id");
		var input = document.getElementById(input_id);
		input.value = "";
	
		var taxonSource = target.getAttribute("data-taxon-source");
		var nameUuid = target.getAttribute("data-name-uuid");
		
		
		var kwargs = [taxonSource, nameUuid]
		
		var url = reverse("TaxonProfilesUUID", kwargs);

		HttpResponseRedirect(url);
	
	}

}, AlphabetMixin);
