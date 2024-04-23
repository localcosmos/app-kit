"use strict";

// prototypal inheritance
function derive(prototype, extension, override) {

	var override = override || {};

	var object = Object.create(prototype);

	object.super = function(){
		return Object.getPrototypeOf(this);
	};

	for (let property in extension){
		if (object.hasOwnProperty.call(extension, property) || typeof object[property] === "undefined") {
			object[property] = extension[property];
		}
	}

	// override overrides extension
	for (let property in override){
		if (object.hasOwnProperty.call(override, property) || typeof object[property] === "undefined") {
			object[property] = override[property];
		}
	}

	return object;
}


// extend
// differs from derive
function extend(prototype, extensionlist) {
	
	var object = Object.create(prototype);
	var index = extensionlist.length;

	while (index) {
		index--;
		var extension = extensionlist[index];

		for (var property in extension){
			if (object.hasOwnProperty.call(extension, property) ||	typeof object[property] === "undefined") {
				object[property] = extension[property];
			}
		}
	}

	object._super = prototype;
	object.super = function(obj){
		var obj = obj || this;
		return obj._super;
	}

	return object;
};


/* GENERAL */
// Object.create is prototype inheritance and not real cloning
function clone(obj){

	var cleaned_event = {};

	if (obj.hasOwnProperty("event")){

		var accepted_keys = ["target", "currentTarget", "pointerType", "isFirst", "isFinal", "eventType"];

		for (let k=0; k<accepted_keys.length; k++){

			let key = accepted_keys[k];

			if (obj.event.hasOwnProperty(key)){
				cleaned_event[key] = obj.event[key];
			}
		}

		obj.event = cleaned_event;
	}

	return JSON.parse(JSON.stringify(obj));
}

// type checks
function isInt(n){
	var n = parseInt(n);
    return Number(n) === n && n % 1 === 0;
}

function isFloat(n){
    return n === Number(n) && n % 1 !== 0;
}

function isBool(b){
	if (b === 0 || b === "0"){
		b = false;
	}
	else if (b === 1 || b === "1"){
		b = true;
	}
	return typeof b === "boolean";
}

function isChar(c){
	return typeof c === "string";
}

function parseBool(b){
	if (b == 1 || b == "1"){
		b = true;
	}
	else if (b == 0 || b == "0"){
		b = false;
	}
	else {
		throw new Error("parseBool error: " + b);
	}
	return b;
}


/*
* mango
* mange depends on device so t has to be initialized after deviceready
*/
var mango = {

	models: [],

	widgets: [],

	init : function(kwargs, on_init_success){

		var kwargs = kwargs || {};

		// currently the following kwargs are supported:
		/*
			{
				"ajaxify_container" : [DocumentElement], // passed to Pagemanager
				"container" : [DocumentElement], // passed to Pagemanager,
				"on_new_page" : [function], //passed to Pagemanager
			}
		*/

		// client side storage
		if (device.platform == "browser"){
			// only use the History replacement in true apps
			// we cant hijack the back button in browser like we can in true apps
			// therefore, the webapp has not an ideal history management
			window.History = window.history;
			// the storage is used to store the authtoken
			// on the webapp this may not be permanent
			mango.storage = window.sessionStorage;
		}
		else {
			// attach backbutton
			document.addEventListener("backbutton", function(event){
				BackButtonManager.back();
			}, false);

			mango.storage = window.localStorage;
		}

		// check if required modules are ready
		var required_modules = ["i18next", "Handlebars"];
		for (var m=0; m<required_modules.length; m++){
			if (!(required_modules[m] in window)){
				throw new Error("ERROR: required object " + required_modules[m] + " not found in window");
			}	
		}
		
		// init database, has to be done before initiating models
		this.dbType = this.get_db_type();

		console.log("[mango] initiating database of type " + this.dbType);
		mango.db = window[this.dbType];
		mango.db.init();

		// init models
		this.init_models();

		// migrate database
		this.db.migrate(function(){
		});

		// init i18n
		if (this.initialized.indexOf("i18n") == -1){
			this.init_i18n();
		}

		// load the session
		mango_session.load_from_storage(function(){

			// init Pagemanager
			var pagemanager_config = {};
			var pagemanager_config_params = ["ajaxify_container", "container", "_on_new_page"];
			for (var k=0; k<pagemanager_config_params.length; k++ ){
				var key = pagemanager_config_params[k];
				if (kwargs.hasOwnProperty(key)){
					pagemanager_config[key] = kwargs[key];
				}
			}

			Pagemanager.init(pagemanager_config);

			// init widgets. this loads the widgets templates which is async
			mango.init_widgets(function(){

				mango._load_initial_page();

				delete mango["init"];
				on_init_success();

			});
		});

	},

	_load_initial_page : function(){

		if (device.platform == "browser"){
			// parse the current url and load the page with the correct params
			var url = window.location.href;
			var GET_parameters = InteractionManager._get_GET_parameters(url);
			var request = HttpRequest.create("GET", GET_parameters);
		}
		else {
			var url = "/";
			var request = HttpRequest.create("GET");
		}
		Pagemanager.dispatch_response(url, request, [], {});

	},

	get_database_settings : function(){
		if (device.platform in settings.DATABASES){
			return settings["DATABASES"][device.platform];
		}
		else {
			return settings["DATABASES"]["default"];
		}
	},

	get_db_type : function(){
		var database_settings = this.get_database_settings();
		return database_settings["ENGINE"].split(".")[0];
	},

	initialized : [],
	
	init_i18n : function(){

		i18next
			.use(i18nextXHRBackend)
			.init({
				lng: app.language,
				fallbackLng: settings.PRIMARY_LANGUAGE,
				nsSeparator: "ȵ", // use weird characters for separation
  				keySeparator: "ɕ",
				debug: true,
				ns: ['plain', 'glossarized'],
				defaultNS: 'glossarized',
				fallbackNS: 'plain', // if app has no glossary, glossarized is not present
				backend: {
					// load from i18next-gitbook repo
					loadPath: 'locales/{{lng}}/{{ns}}.json',
					crossDomain: true
				}
			});

		// make the _ translator work
		window["_"] = function(key){ 
			return i18next.t(key);
		};

		window["_p"] = function(key){
			var lookup_key = "plainȵ" + key;
			return i18next.t(lookup_key);
		};

		this.initialized.push("i18n");
	},

	init_models : function(){
		// add Managers to models
		for (var m=0; m<this.models.length; m++){
			var model = window[this.models[m]];
			if (model.hasOwnProperty("objects")){
				// a custom manager is used
				if (typeof model.objects != "string"){
					throw new Error("Model.objects has to be of type string when you define a model");
				}
				model.objects = window[model.objects].create(model.model_name, model.db_identifier);
			}
			else {
				// check if a custom ModelInterface is present for this dbType
				model.objects = window["" + this.dbType + "ModelInterface"].create(model.model_name, model.db_identifier);
			}

			// add remote_objects if applicable
			if (model.remote_supported === true){
				model.remote_objects = window["RemoteDBModelInterface"].create(model.model_name, model.db_identifier);
			}
		}
	},

	init_widgets : function(callback){
		each(this.widgets, function(widget_name, iterate){

			if (widget_name in window){
				var widget = window[widget_name];
			}
			else if (widget_name in forms){
				var widget = forms[widget_name];
			}
			else {
				throw new Error("Widget '" + widget_name + "' was neither found in forms or window.");
			}
			
			widget.__init__(widget, iterate);

		}, callback);
	}

};

/* simple session object
 * - user, user_uuid and auth_token
 * - store token and user uuid in mango.storage
 * - user is not stored in mango.storage, user is a model instance
 * - reload session from mango.storage if possible, so the user does not have to log in every time on native apps 
*/
var mango_session = {
	auth_token : null,
	user_uuid : null,
	user : null,

	set : function(user, auth_token){
		this.user = user;

		this.auth_token = auth_token;
		mango.storage.setItem("auth_token", auth_token);

		this.user_uuid = user.uuid;
		mango.storage.setItem("user_uuid", user.uuid);
	},

	get_auth_token : function(){
		if (this.auth_token == null){
			this.auth_token = mango.storage.getItem("auth_token");
		}
		return this.auth_token;
	},

	get_user_uuid : function(){
		if (this.user_uuid == null){
			this.user_uuid = mango.storage.getItem("user_uuid");
		}
		return this.user_uuid;
	},

	load_from_storage : function(callback){

		var self = this;

		var auth_token = this.get_auth_token();
		if (auth_token != null){
			var user_uuid = this.get_user_uuid();

			UserModel.objects.get({"uuid":user_uuid}, function(user){
				self.auth_token = auth_token;
				self.user_uuid = user_uuid;
				self.user = user;

				callback();
			});	

		}
		else {
			self.user = AnonymousUser.create();
			callback();
		}
	},

	clear : function(){
		this.auth_token = null;
		this.user_uuid = null;
		this.user = AnonymousUser.create();

		mango.storage.removeItem("user_uuid");
		mango.storage.removeItem("auth_token");
	}
};


/* BackButtonManager
* - manages both hardware and software back buttons
* - exit app if on home screen
* - else fire History.back, if no modal is open
* - of a modal is open, close the mocal
*/
var BackButtonManager = {

	// hook for overlays before back, eg "do you want to save changes?" is user presses back with unsaved changes
	before_back : null,

	"back" : function(force){
		
		var force = force || false;
		
		if (typeof(OverlayView.close_current_overlay) == "function" && force == false){
			OverlayView.close_current_overlay();
		}
		else {

			if (typeof(BackButtonManager.before_back) == "function" && force == false){
				BackButtonManager.before_back();
			}
			else {

				BackButtonManager.before_back = null;

				if (device.platform == "Android"){
					if (History.state.state.request_path == "/" || History.length == 1) {
						navigator.app.exitApp();
					} 
					else {
						History.back();
					}
				}
				else {
					History.back();
				}
			}
		}
		
	},

	force_back : function(){

		if (typeof(OverlayView.close_current_overlay) == "function"){
			OverlayView.close_current_overlay();
		}

		BackButtonManager.back(true);
	}

};

window.addEventListener("pagechanged", function(event){

	if (typeof(OverlayView.close_current_overlay) == "function"){
		OverlayView.close_current_overlay();
	}
	OverlayView.close_current_overlay = null;
	
}, false);


function each(data, onIter, onFinished){

	if (!data){
		onFinished();
	}
	else if ( Object.prototype.toString.call( data ) === '[object Array]' || data instanceof Array || Object.prototype.toString.call( data ) === '[object HTMLCollection]') {
		
		var index = -1,
			dataCount = data.length;
		
		var workLoop = function(){
			
			index++;
		
			if (index < dataCount){
			
				var obj = data[index];
			
				onIter(obj, workLoop);
			
			}
			else {
				if (typeof onFinished == 'function'){
					onFinished();
				}
			}
		
		}
	
		workLoop();

	}
	else {
		
		var keys = Object.keys(data);

		if (keys.length > 0){

			var index = -1,
				dataCount = keys.length;

			var workLoop = function(){
				index++;
			
				if (index < dataCount){

					var objname = keys[index];
				
					var obj = data[objname];
				
					onIter(objname, obj, workLoop);
				
				}
				else{
					if (typeof onFinished == 'function'){
						onFinished();
					}
				}
			}
		
			workLoop();
		}
		else {
			onFinished();
		}

	}

}

// Database Prototype
var Database = {
	init : function(callback){
		throw new Error("Database implementations do need an init() method");
	},
	migrate : function(callback){
		throw new Error("Database implementations do need a migrate() method");
	}
};
