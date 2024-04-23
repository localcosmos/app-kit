"use strict";

// replacement for features.js
var features = {};

var upstart = {

	run : function(){

		var self = this;

		console.log("[UPSTART] running on " + device.platform);

		self._load_settings(function(){

			self._load_features(function(){

				self._load_frontend(function(){

					// disable context menus, especially on Android
					if (device.platform != "browser"){
						window.oncontextmenu = function(event) {
							event.preventDefault();
							event.stopPropagation();
							return false;
						};
					}

					// localize from a json dict
					Handlebars.registerHelper('localize', function (obj) {
						var result = obj[app.language];
						return new Handlebars.SafeString(result);
					});

					Handlebars.registerHelper('vernacular', function (i18n_key) {

						// ȵ is the namespace separator
						var lookup_key = 'plainȵ' + i18n_key;

						var result = i18next.t(lookup_key);

						if (result == i18n_key){
							return "";
						}
						return new Handlebars.SafeString(result);
					});
					
					
					Handlebars.registerHelper('stringify', function (json) {

						let json_string = JSON.stringify(json);
						
						return new Handlebars.SafeString(json_string);
					});

					Handlebars.registerHelper('date', function (date_obj) {
						if (!date_obj){
							return '';
						}
						return new Handlebars.SafeString(date_obj.toLocaleDateString());
					});

					Handlebars.registerHelper('verbose_datetime', function (str) {

						var date = new Date(str);

						return new Handlebars.SafeString(date.toLocaleString());
					});

					// first check requirements
					if ("GenericForm" in app_features || "ButtonMatrix" in app_features){
						app.requires_geolocation = true;	
					}

					self._load_theme(function(){

						console.log("[UPSTART] theme initialized");

						document.title = settings.NAME;

						self._load_language(function(){

							self._load_handlebars_helpers();

							self._render_skeleton(function(){

								// load ModalDialog immediately after the skeleton
								window.modalDialog = ModalDialog.create("ModalDialog");

								// load ModalProgress
								window.modalProgress = ModalProgress.create("ModalProgress");

								// observation forms
								if ("GenericForm" in app_features){
									self._init_observation_forms();
								}

								// init geolocation
								if (app.requires_geolocation == true){
									AppGeolocation.start_watching();
								}

								self._load_mango(function(){

									// sponsors require mango.storage
									//self._load_sponsors();

									// sidemenu requires mango_session.user
									load_sidemenu();

									// load the template
									//load_footer_sponsors();

									console.log("[UPSTART] finished loading LC app");

								});

							});	

						});
						
					});

				});

			});

		});

	
	},


	_load_settings : function(callback){

		ajax.getJSON("settings.json", {}, function(app_settings){
			for (let key in app_settings){
				settings[key] = app_settings[key];
			}

			//alert(JSON.stringify(settings));
			if (settings.OPTIONS.hasOwnProperty("allowAnonymousObservations") && settings.OPTIONS.allowAnonymousObservations == true){
				MyObservations.login_required = false;
			}

			if (settings.OPTIONS.hasOwnProperty("allowAnonymousObservations") && settings.OPTIONS.allowAnonymousObservations == true){
				ObservationView.login_required = false;
				ButtonMatrixView.login_required = false;
				LogFromMatrix.login_required = false;
			}

			callback();
		});
		
	},

	_load_features : function(callback){
		ajax.getJSON("localcosmos/features.json", {}, function(features){
			for (let key in features){
				app_features[key] = features[key];
			}

			callback();
		});
	},

	_load_frontend : function(callback){

		if (settings.PREVIEW == true){
			callback();
		}
		else {
			var path = app_features["Frontend"]["path"];
			ajax.getJSON(path, {}, function(frontend){

				const style = document.createElement('style');
				style.innerHTML = `@media (orientation: landscape) { 
					html {	
						background-image: url('${frontend.userContent.images.appPcBackground.imageUrl['8x']}');
					}
				}
				@media (orientation: portrait) {
					html {
						background-image: url('${frontend.userContent.images.appBackground.imageUrl['8x']}');
					}
				}
				.logo-home > div {
					background-image: url('${frontend.userContent.images.logo.imageUrl['1x']}');

				}
				.navbar-logo {
					background-image: url('${frontend.userContent.images.logo.imageUrl['1x']}');

				}
				`;

				document.head.appendChild(style);

				callback();
			});
		}
	},


	_load_language : function(callback){
		
		var language = navigator.language.substring(0,2).toLowerCase();

		if (settings.LANGUAGES.indexOf(language) >=0){
			app.language = language;
		}
		else if (settings.LANGUAGES.indexOf("en") >=0){
			app.language = "en";
		}
		else {
			app.language = settings.PRIMARY_LANGUAGE;
		}
		callback();
	},

	_load_mango : function(callback){

		mango.init({
			"ajaxify_container" : document.getElementById("app"),
			"container" : document.getElementById("content"),
			"_on_new_page" : function(view_identifier, args, kwargs){
				// load the App bar
				Appbar.load(view_identifier, args, kwargs);
				// check if a custom callback function is in kwargs
			}

		}, callback);

	},

	_load_theme : function(callback){

		ajax.getJSON("themes/" + settings.THEME + "/config.json", {}, function(theme_config){

			app.theme = theme_config;

			// load theme specific css files

			each(app.theme.css, function(css_relative_filepath, iterate){

				var css_filepath = "themes/" + settings.THEME + "/" + css_relative_filepath; 

				var link = document.createElement("link");
				link.setAttribute("rel", "stylesheet");
				link.setAttribute("type","text/css");

				link.onload = function(){
					link.onload = null;
					iterate();
				}

				link.setAttribute("href", css_filepath);

				document.head.appendChild(link);

			},

			function(){

				// load theme specific js files
				// make sure script x+1 is loaded after x has finished loading -> async
				each(app.theme.js, function(script_relative_filepath, iterate){

					var script_filepath = "themes/" + settings.THEME + "/" + script_relative_filepath;

					var script = document.createElement("script");
					script.async = true;
					script.setAttribute("type","text/javascript");

					script.onload = function() {
						// Cleanup onload handler
						script.onload = null;

						iterate();
					}

					script.src = script_filepath;

					document.head.appendChild(script);

				}, callback);

			});

		});
	},

	_render_skeleton : function (callback){

		// we need the t helper in the skeleton
		mango.init_i18n();

		var sponsors = false;
		//if (settings.SPONSORS_DISABLED != false){
		//	sponsors = true;
		//}

		if (listeners.hasOwnProperty("get_skeleton_context")){
			var context = listeners.get_skeleton_context();
		}
		else {
			var context = {};
		}

		context["sponsors"] = sponsors;

		context["app_requires_geolocation"] = app.requires_geolocation;

		ajax.GET("themes/" + settings["THEME"] + "/templates/skeleton.html", {}, function(template){
			var skeleton = Handlebars.compile( template )(context);
			document.getElementById("app").innerHTML = skeleton;

			callback();
		});
		
	},

	_load_handlebars_helpers : function() {

		Handlebars.registerHelper("themeFolder", function () {
		    return "themes/" + settings.THEME + "/";
		});		

	},

	_init_observation_forms : function(callback){
		/* Create form prototypes for all forms in settings */

		var observation_forms = app_features["GenericForm"]["list"];

		each(observation_forms, function(form_link, iterate){
			ajax.GET(form_link["path"], {}, function(content){

				// create window[uuid] as a Form prototype
				var form_definition  = JSON.parse(content);//JSON.parse(atob(content));

				window[form_definition["uuid"]] = createObservationFormFromJSON(form_definition);

				iterate();
			});
		});

	},

	_load_taxonomy : function(){
		// loads the vernacular taxonomy
		var path = app_features.BackboneTaxonomy.vernacular[app.language];

		ajax.getJSON(path, {}, function(taxa){
			window.Vernacular = taxa;
		});
	},

	_load_sponsors : function(callback){
		// async load sponsors, once every hour
		
		// now in milliseconds
		var now = new Date().getTime();
		var last_update = mango.storage.getItem("last_sponsor_update");
		var needs_update = false;

		// one hour in milliseconds
        var one_hour = 1 * 60 * 60 * 1000;
		
		if (last_update == null){
			needs_update = true;
		}
		else {
			var timespan = now - last_update;
			if (timespan > one_hour){
				needs_update = true;
			}
		}

        /*{
          "main_sponsors": [
            {
              "id": 2,
              "logos": {
                "400x100": "http://tomwork.sisol:8080/media/sponsors/SiSol%20Systems/logos/200x50/sisollogo_200x50.svg.png",
                "100x100": "http://tomwork.sisol:8080/media/sponsors/SiSol%20Systems/logos/100x100/sisollogo_100x100.svg.png"
              },
              "company_name": "SiSol Systems",
              "company_link": "https://sisol-systems.com"
            }
          ]
        }*/

		if (needs_update == true){

		    lcapi.get_sponsor_list(function(sponsors){

		        if (Object.keys(sponsors).length){
		            // update the sponsoring store
		            if (device.platform == "browser"){
		                mango.storage.setItem("sponsors", JSON.stringify(sponsors));
		            }
		            else {
		                // app: download main sponsor images and store a new dict
		                if (sponsors.hasOwnProperty("main_sponsors")){

		                    var offline_sponsors = {
		                        "main_sponsors" : []
		                    };

		                    each(sponsors.main_sponsors, function(main_sponsor, iterate_sponsor){

		                        var main_sponsor = JSON.parse(JSON.stringify(main_sponsor));

		                        each(main_sponsor.logos, function(logo_name, logo_url, iterate_logo){

									var logo_parts = logo_url.split(".");
		                            var fileextension = logo_parts[logo_parts.length -1];
		                            var filename = main_sponsor.id + "_" + logo_name + "." + fileextension;

									FileUtil.download(logo_url, "sponsors", filename, function(fileEntry){

										CachedImage.as_url(fileEntry.toInternalURL(), function(cached_logo_url){

											main_sponsor["logos"][logo_name] = cached_logo_url;
											iterate_logo();

										}, iterate_logo);
									});

								}, function(){
		                                offline_sponsors["main_sponsors"].push(main_sponsor);
		                                iterate_sponsor();
								});


		                    }, function(){
		                        mango.storage.setItem("last_sponsor_update", now);
		                        mango.storage.setItem("sponsors", JSON.stringify(offline_sponsors));
		                    });
		            
		                }
		            }
		        }

		    }, function(error){
		    });

		}
		else {
			// create logo cache images on ios
			if (device.platform == "iOS"){
				var offline_sponsors_str = mango.storage.getItem("sponsors");
                if (offline_sponsors_str != null){
                    
                    var offline_sponsors = JSON.parse(offline_sponsors_str);
                    var new_offline_sponsors = {
                        "main_sponsors" : []
                    };

                    each(offline_sponsors.main_sponsors, function(main_sponsor, iterate_sponsor){

                        each(main_sponsor.logos, function(logo_name, cached_logo_url, iterate_logo){
                            var logo_path_parts = cached_logo_url.split("/");
                            var logo_filename = logo_path_parts.pop();

                            window.requestFileSystem(LocalFileSystem.PERSISTENT, 0, function (fs) {

                                fs.root.getDirectory("sponsors", { create: true }, function (dirEntry) {

                                    dirEntry.getFile(logo_filename, { create : false }, function(fileEntry){

                                        CachedImage.as_url(fileEntry.toInternalURL(), function(new_cached_logo_url){
                                            
                                            main_sponsor["logos"][logo_name] = new_cached_logo_url;
                                            
                                            iterate_logo();
                                        }, iterate_logo);

                                    }, function(e){
                                        console.log("[UPSTART ERROR] dirEntry.getFile " + JSON.stringify(e));
                                    });

                                });

                            });

                        }, function(){
                            new_offline_sponsors["main_sponsors"].push(main_sponsor);
                            iterate_sponsor();
                        });
                    }, function(){
                        mango.storage.setItem("sponsors", JSON.stringify(new_offline_sponsors));
                        console.log("finished updating sponsor logo cache");
                    });
                }
			}
		}

	}

}
