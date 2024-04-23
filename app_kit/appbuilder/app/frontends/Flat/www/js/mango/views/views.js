"use strict";

/*
* mango apps are javascript only
* like in django, a Request object is passed to the view
*/

var default_renderer = {

	render : function(template_name, context, callback){

		ajax.GET(template_name + "?_=" + new Date().getTime(), {}, function(template){
			var template_html = Handlebars.compile( template )(context);
			callback(template_html);
		});

	}
};

// a store for context_processors
var context_processors = {
	request : function(request){
		var extra_context = {
			"request" : request
		};
		return extra_context;
	}
};

function _get_return_function(fn){
	if (fn.indexOf(".") > 0){
		var fn_parts = fn.split(".");

		var return_fn = window[fn_parts[0]];

		for (var p=1; p<fn_parts.length; p++){
			return_fn = return_fn[fn_parts[p]];
		}
	}
	else {
		var return_fn = window[fn];
	}

	if (typeof return_fn != "function"){
		throw new Error("No function found by that name: " + fn);
	}

	return return_fn;

}

function HttpResponseRedirect(url, args, kwargs){

	var kwargs = kwargs || {};
	var args = args || [];

	var request = HttpRequest.create("GET");
	
	Pagemanager.dispatch_response(url, request, args, kwargs);

}

// url_kwargs can be a list[] with values or a dict {}
// "args" like in django urls are not supported in mango
function reverse(pattern_name, url_kwargs){

	var url = null;

	var url_kwargs = url_kwargs || {};

	var tried = [];

	var url_kwargs_values = []; // assumed to be unordered

	if (url_kwargs instanceof Array){
		var url_kwargs_values_count = url_kwargs.length;
	}
	else {
		var url_kwargs_values_count = Object.keys(url_kwargs).length;
	}

	for (var p=0; p<urlpatterns.length; p++){
		var pattern = urlpatterns[p];

		if (pattern.kwargs.name == pattern_name && pattern.variable_count == url_kwargs_values_count){

			tried.push(pattern.url);

			if (pattern.variable_count == 0){
				url = pattern.url;
			}
			else {

				var url = "";

				for (var q=0; q<pattern.url_parts.length; q++){
					var pattern_part = pattern.url_parts[q];

					if (pattern.typelist[q] == "static"){
						url = url + pattern_part + "/";
					}
					else {
						if (url_kwargs instanceof Array){
							// take the first one
							url = url + url_kwargs.shift() + "/";
						}
						else {
							// select by name
							url = url + url_kwargs[pattern.url_kwargs_by_index[q]];
						}
					}

				}
			}

			break;

		}

	}	

	if (url === null){
		var msg = "no matching urlpattern found for " + pattern_name;
		if (url_kwargs.length > 0){
			msg = msg + " with arguments " + url_kwargs.join(",");
		}

		msg = msg + ". Tried: " + tried.join(",");

		throw new Error(msg);
	}
	
    return url;

}

// receives GET_parameters as ?param1=1&param2=2 and POST_paramters as {}
// due to a name conflict with iOS WKWebview, Request has been renamed to HttpRequest
var HttpRequest = {
	create : function(method, GET_parameters, POST_parameters){
		self = Object.create(this);

		var GET_parameters_dict = {};

		var POST_parameters = POST_parameters || {};

		if (GET_parameters != null && typeof GET_parameters != "undefined"){
			GET_parameters_dict = http.deserialize(GET_parameters);
		}

		self.method = method;
		self["GET"] = GET_parameters_dict;
		self["POST"] = POST_parameters;

		return self;
	},

	// only pass GET params to history
	for_history : function(self){
		var request_obj = {
			"GET" : self.GET
		};
		return request_obj;
	}
}

// deserialize converts ?param1=1&param2=2 to {"param1" : 1,...}
// or form element to {} for use with mango form validation
// this collects the values of fields with the same name as a list

var http = {

	deserialize_form : function(form_element){

		var data = {};

		var inputs = form_element.querySelectorAll("input, select, textarea");

		for (let i=0; i<inputs.length; i++){
			var input = inputs[i];

			if (input.getAttribute("type") == "checkbox" && input.checked == false){
				continue;
			}

			var input_name = input.getAttribute("name");

			if (input.getAttribute("type") == "file"){
				// the fileInput.file FileList is immutable, so first look if fileInput._files was used
				if (input.hasOwnProperty("_files")){
					data[input_name] = input._files;
				}
				else if (input.files.length > 0){
					data[input_name] = input.files;
				}
				input.files = null;
			}
			else {
				if (input.value.length > 0){
					if (data.hasOwnProperty(input_name)){
						if (data[input_name] instanceof Array == false){
							data[input_name] = [data[input_name]];
						}
						data[input_name].push(input.value);
					}
					else {
						data[input_name] = input.value;
					}
				}			
			}
		}

		return data;

	},

	deserialize : function(urlparameters){

		var parameters = {};

		var pairs = urlparameters.split("&");
		var result = {};

		for (var p=0; p<pairs.length;p++) {
		
			var pair = pairs[p].split("=");
			var name = pair[0];
			var value = pair[1];
			if ( name.length ) {
			    if (parameters[name] !== undefined) {
			        if (!parameters[name].push) {
			            parameters[name] = [parameters[name]];
			        }
			        parameters[name].push(value || '');
			    }
				else {
			        parameters[name] = value || '';
				}
			}
		};

		return parameters;
	}
}


/*
* InteractionManager
* - manages touch/gesture/mouse inputs
* - uses hammer.js
*/

var InteractionManager = {

	swipe_active : false,

	// attach one hammer to rule them all
	attach : function(container){

		var self = this;
		
		self._add_tap_listener(container);
		self._activate_gesture_listeners(container);
	},

	_add_tap_listener : function(element){

		var self = this;

		/*var options = {
			supportedGestures : [Tap],
			DEBUG_GESTURES: true
		};
		var pointerListener = new PointerListener(element, options);

		pointerListener.on("tap", function(event){
			self._input_worker(event, "tap");
		});*/
		
		var hammertime = new Hammer(element, {});
		hammertime.on("tap", function(event) {
			self._input_worker(event, "tap");			
		});

		element.addEventListener("auxclick", function(event){
			
			if (event.button == 1) {
				var link = event.target.getAttribute("link");
				window.open("#" + link, '_blank').focus();
			}
		});

	},

	// currently each element with gesture gets its own hammer instance, this might not be ideal
	_activate_gesture_listeners : function(container){
		var self = this;

		// attach known listeners
		var known_gestures = ["swipeleft", "swiperight", "onchange", "onkeyup", "onblur", "onfocus", "preventDefault"];


		for (var li=0; li<known_gestures.length; li++){

			var gesture = known_gestures[li];
			var elements = container.getElementsByClassName(gesture);
			//console.log(gesture)
			for (var e=0; e<elements.length; e++){
				self["_add_" + gesture + "_listener"](elements[e]);
			}
		}
	},

	_input_worker : function(event, input_type){

		var self = this;

		var element = event.target;
		var counter = 4;

		while (counter > 0){

			if (element.id == "app"){
				counter = 0;
				break;
			}

			if (element.classList.contains(input_type)){
				counter = 0;
				self._launch_request("GET", event, element);
				break;
			}
			else {
				counter--;
				element = element.parentElement;
			}
		}
	},

	_add_tap_highlightings : function(container){
		var self = this;

		var elements = container.getElementsByClassName("tap");
		
		for (var e=0; e<elements.length;e++){
			var element = elements[e];
			// ms edge fix for specific elements
			if (!element.classList.contains("nohighlight")){
				self._add_tap_highlighting(elements[e]);
			}
		}
		
	},

	_add_tap_highlighting : function(element){
		var self = this;

		element.addEventListener("touchstart", function(event){
			self.swipe_active = false;

			setTimeout(function(){
				if (self.swipe_active == false){
					event.target.style.opacity = 0.5;
				}
			}, 10);
		});

		element.addEventListener("touchend", function(event){
			setTimeout(function(){
				event.target.style.opacity = 1;
			}, 10);
			self.swipe_active = false;
		});

		element.addEventListener("touchmove", function(event){
			if (self.swipe_active == false){
				self.swipe_active = true;
				event.target.style.opacity = 1;
			}
		});

	},

	_add_swipeleft_listener : function(element){
		var self = this;

		/*var options = {
			supportedGestures : [Pan],
			supportedDirections: Directions.Horizontal,
			handleTouchEvents : false,
			DEBUG:true
		};
		var panListener = new PointerListener(element, options);

		panListener.on("swipeleft", function(event){
			self._launch_request("GET", event, element); 
		});*/

		
		var hammertime = new Hammer(element, {});
		hammertime.on("swipeleft", function(event){
			self._launch_request("GET", event, element); 
		});

	},

	_add_preventDefault_listener : function(element){
		var self = this;

		element.addEventListener("touchend", function(event){
			event.preventDefault();
			event.stopPropagation();
		});

		element.addEventListener("touchmove", function(event){
			event.preventDefault();
			event.stopPropagation();
		});

	},


	_add_swiperight_listener : function(element){
		var self = this;

		var hammertime = new Hammer(element, {});
		hammertime.on("swiperight", function(event){
			self._launch_request("GET", event, element); 
		});

	},

	_add_form_submit_listener : function(form){
		var self = this;

		// reads form field values into request.POST
		form.addEventListener("submit", function(event){
			event.preventDefault();
			
			self._launch_request("POST", event, event.currentTarget);
			
		}, false);
	},

	_add_onchange_listener : function(element){
		var self = this;
		
		element.addEventListener("change", function(event){
			self._launch_request("GET", event, element); 
		});
	},

	_add_onkeyup_listener : function(element){
		var self = this;

		element.addEventListener("keyup", function(event){
			self._launch_request("GET", event, element);
		});
	},

	_add_onblur_listener : function(element){
		var self = this;

		element.addEventListener("blur", function(event){
			self._launch_request("GET", event, element);
		});
	},

	_add_onfocus_listener : function(element){
		var self = this;

		element.addEventListener("focus", function(event){
			self._launch_request("GET", event, element);
		});
	},

	_activate_forms : function(container){
		var self = this;
		
		var forms = container.getElementsByTagName("form");
		
		for (var f=0; f<forms.length; f++){
			var form = forms[f];
			self._add_form_submit_listener(form);
		}

		// enable form scrolling
		var inputs = container.querySelectorAll("input:not([type='checkbox']), textarea");
		for (var z=0; z<inputs.length; z++){
			var input = inputs[z];
			input.addEventListener("click", function(){
				//console.log('scrolling to input');
				var rect = this.getBoundingClientRect();
				var topOffset = rect.top - ( app.containerHeight * 0.2);
				if (topOffset > window.pageYOffset){
					window.scrollTo(0, Math.floor(topOffset));
					// the following two lines prevent setting the cursor inside input[type=text] and textarea elements
					// only prevent this if scrolling to input
					this.focus();
					this.select();
				}

			});
		}
	},

	_get_element_args : function(element){
		var args = [];
		if (element.hasAttribute("args")){
			var args = element.getAttribute("args");
			args = JSON.parse(args);
		}
		return args;
	},
	_get_element_kwargs : function(element){
		var kwargs = {};
		if (element.hasAttribute("kwargs")){
			var kwargs = element.getAttribute("kwargs");
			kwargs = JSON.parse(kwargs);
		}
		return kwargs;
	},

	_get_GET_parameters : function(url){
		var parts = url.split("?");
		var fn = parts[0];

		var GET_parameters = null;

		if (parts.length > 1){
			GET_parameters = parts[1];
		}

		return GET_parameters;
	},

	_launch_request : function(request_method, event, current_target){
		var self = this;

		var args = self._get_element_args(current_target);
		var kwargs = self._get_element_kwargs(current_target);

		kwargs["event"] = event;
		// fix hammer.js missing currentTarget
		kwargs["currentTarget"] = current_target;

		// determine if it is an js action or a link
		// if the event is onblur
		if (event.type == "blur"){
			var url = current_target.getAttribute("data-onblur");
		}
		else if (event.type == "focus"){
			var url = current_target.getAttribute("data-onfocus");
		}
		else if (current_target.hasAttribute("action") || current_target.tagName.toLowerCase() == "form"){
			var url = current_target.getAttribute("action");
			if (current_target.tagName.toLowerCase() == "form"){
				var type = "link";
			}
			else {
				var type = "action";
			}
		}
		else if (current_target.hasAttribute("link")){
			var url = current_target.getAttribute("link");
			var type = "link";
		}
		else {
			throw Error("mango links need either the 'action' attribute or the 'link' attribute.")
		}
		
		var GET_parameters = self._get_GET_parameters(url);

		var POST_parameters = null;

		if (request_method == "POST"){
			POST_parameters = http.deserialize_form(current_target);
		}

		var request = HttpRequest.create(request_method, GET_parameters, POST_parameters);

		if (type === "link"){
			Pagemanager.dispatch_response(url, request, args, kwargs);
		}
		else {
			// simple ajax function call, no view processing for type "action"
			url = url.split("?")[0];

			if (url.indexOf(".") > 0){
				var url_parts = url.split(".");

				if (url_parts.length > 2){
					var return_fn = _get_return_function(url);
					return_fn(null, request, args, kwargs);
				}
				else {
					window[url_parts[0]][url_parts[1]](null, request, args, kwargs);
				}
			}
			else {
				var return_fn = _get_return_function(url);
				return_fn(return_fn, request, args, kwargs);
			}
		}
	}

};

/*
*	Pagemanager
*	- inserts rendered pages into html
*	- takes care of history mangement
*	- launches middleware classes
*	- flow: Pagemanager.dispatch_response -> View func -> Pagemanager.go
*/

// pagechange is fired
var Pagemanager = {

	container : document.body,
	ajaxify_container : document.body,
	current_page_id : null,
	current_request_path : null,
	current_view_identifier : null, // only class based views are supported
	current_kwargs : {},
	current_args : [],

	save_state_on_exit : true,

	pagechanged_event : new CustomEvent("pagechanged", {}), // fired on both back and new page, after the page has been loaded

	init : function(config){

		var self = Pagemanager;

		// fall back to native history if History is not present
		if (!("History" in window)){
			window.History = window.history;
		}

		//*** history ***
		window.addEventListener("popstate", self._load_from_history);

		var config = config || {};

		for (var key in config){
			self[key] = config[key];
		}

		InteractionManager.attach(self.ajaxify_container);
		
	},

	_load_from_history : function(event){
		// assign self correctly, "this" would fail because it is an event
		var self = Pagemanager;

		var page_id = event.state.page_id;
		console.log("[Pagemanager] back to " + page_id);

		//self.container.textContent = "";
		var template_html = event.state.template_html;
		var request_path = event.state.request_path;
		var view_identifier = event.state.view_identifier;
		var args = event.state.args;
		var kwargs = event.state.kwargs;

		// loading from history populates event.state.kwargs with weird stuff
		self.save_state_on_exit = window[view_identifier].save_state_on_exit;

		self._insert(self.container, template_html, args, kwargs);
		self._post_insert(view_identifier, args, kwargs);

		self._on_new_page(view_identifier, args, kwargs);
    	
    	self._update_self(page_id, request_path, view_identifier, args, kwargs);
	    
		self._animations.fadein();

    	window.scrollTo(0,0);

		window.dispatchEvent(self.pagechanged_event);

	},

	_on_new_page : function(view_identifier, args, kwargs){
		// override this to trigger a function on every new page insert, like changing the header
	},

	_animations : {
		fadein : function(){
			var page = document.getElementsByClassName("page");

			if (page.length > 0) {
				window.getComputedStyle(page[0]).opacity;
			    page[0].classList.remove("faded-out-right");
				page[0].classList.remove("faded-out-left");
				page[0].classList.remove("faded-out");
			}
		},
		fadeout : function (){
			var page = document.getElementsByClassName("page");

			if (page.length > 0) {
				window.getComputedStyle(page[0]).opacity;
			    page[0].classList.add("faded-out");
			}
		}
	},

	_update_state : function(){

		var self = this;

		// htmlize inputs so they dont get lost
		var inputs = self.container.querySelectorAll("input, select, textarea");
	
		for (var i=0; i<inputs.length; i++){
			var element = inputs[i];
		
			if (element.tagName == "TEXTAREA"){
				element.textContent = element.value;
			}
			else if (element.tagName == "INPUT"){
				var type = element.getAttribute("type").toLowerCase();
				if (type == "text"){
					element.setAttribute("value", element.value);
				}
				else if (type == "radio" || type == "checkbox"){
					if (element.checked){
						element.setAttribute("checked", "checked");
					}
					else {
						element.removeAttribute("checked");
					}
				}
			}
			else if (element.tagName == "SELECT"){
				var options = element.getElementsByTagName("option");
			
				for (var o=0;o<options.length;o++){
					var opt = options[o];
					if (opt.getAttribute("value") == element.value){
						opt.setAttribute("selected","selected");
					}
					else {
						opt.removeAttribute("selected");
					}
				}
			}
		}
		// page_id, request_path, view_identifier, template_html, args, kwargs

		var state = self._create_state(self.current_page_id, self.current_request_path, self.current_view_identifier, self.container.innerHTML, self.current_args, self.current_kwargs);
		
		History.replaceState(state, self.current_page_id, self.current_page_id);
	},

	// context processor runner
	_process_context : function(request, context){

		for (let p=0; p<settings.CONTEXT_PROCESSORS.length; p++){
			var context_processor_name = settings.CONTEXT_PROCESSORS[p];
			if (!(context_processors.hasOwnProperty(context_processor_name))){
				throw new Error('context_processor ' + context_processor_name + ' not found in context_processors');
			}
		
			var processor = context_processors[context_processor_name];
			var extra_context = processor(request);
			
			for (let key in extra_context){
				context[key] = extra_context[key];
			}
		}
		
		return context;
	},

	// middleware runner
	// currentl only process_request is supported, something better is needed
	_process_request : function(request) {

		for (var m=0; m<settings.MIDDLEWARE.length; m++){
			var middleware_name = settings.MIDDLEWARE[m];

			if (typeof window[middleware_name] != "object"){
				throw new Error("Middleware " + middleware_name + " does not exist");
			}

			request = window[middleware_name].process_request(request);	

		}
		return request;
	},

	dispatch_response : function(url, request, args, kwargs){
		var self = this;

		// request, args and kwargs are passed to the view
		var resolved = URLResolver.resolve(url);

		// add path to request
		request.path = resolved.request_path;
		request.view_identifier = resolved.pattern.view.identifier;

		// run middlewares
		request = self._process_request(request);

		var view = resolved.pattern.view;

		for (var key in resolved.url_kwargs){
			kwargs[key] = resolved.url_kwargs[key];
		}

		if (view.is_view == true){
			if (view.login_required == true){
				if (request.user.is_authenticated){
					
					view.dispatch(null, request, args, kwargs);
				}
				else {
					// redirect to login view which accepts an onsuccess paramter
					// LOGIN_VIEW settings parameter
					if ( !settings.hasOwnProperty("LOGIN_VIEW") ) {
						throw new Error("LOGIN_VIEW not defined in settings");
					}

					var login_view = window[settings["LOGIN_VIEW"]];
					login_view.login_redirect = function(user){
						request.user = user;
						view.dispatch(null, request, args, kwargs);
						// reset
						login_view.login_redirect = null;
					}
	
					var login_request = HttpRequest.create("GET");
					login_view.dispatch(null, login_request, [], {});

				}
			}
			else {
				view.dispatch(null, request, args, kwargs);
			}
		}
		else {
			// caveat: no login checking on function views
			view(null, request, args, kwargs);
		}
		
	},

	// inserting html
	_insert : function(container, template_html, args, kwargs){
		var self = this;

		try {
			modalDialog._close();
		}
		catch (e) {

		}
		
		container.innerHTML = template_html;

		InteractionManager._add_tap_highlightings(container); // on edge mobile this interferes with the tap listener
		InteractionManager._activate_forms(container);
		InteractionManager._activate_gesture_listeners(container);

	},

	_post_insert : function(view_identifier, args, kwargs){
		if (typeof(view_identifier) != "undefined" && view_identifier != null){
			
			if (view_identifier in window){
				window[view_identifier].post_finished(args, kwargs);
			}
		}
	},

	_update_self : function(page_id, request_path, view_identifier, args, kwargs){

		var self = this;

		self.current_page_id = page_id;
		self.current_request_path = request_path;
		self.current_view_identifier = view_identifier;
		self.current_args = args;
		self.current_kwargs = clone(kwargs);
	},

	// the history only covers self.container
	// a callback function
	_create_state : function(page_id, request_path, view_identifier, template_html, args, kwargs){

		if (typeof page_id === "undefined" || typeof template_html === "undefined" || typeof request_path === "undefined" || typeof view_identifier === "undefined" || typeof args === "undefined" || typeof kwargs === "undefined"){
			alert("error creating history state");
		}

		var state = {
			"page_id" : page_id,
			"request_path": request_path,
			"view_identifier" : view_identifier,
			"template_html": template_html,
			"args":args,
			"kwargs" : kwargs
		};

		return state;

	},

	_add_to_history : function(page_id, request_path, view_identifier, template_html, args, kwargs){

		var self = this;

		// prevent cloning errors
		var kwargs = JSON.parse(JSON.stringify(kwargs));

		var state = self._create_state(page_id, request_path, view_identifier, template_html, args, kwargs);
	    //console.log(JSON.stringify(state));

		// make the firstly rendered view the starting point of the history
		// and do not add to history if the page is the same - e.g. when submitting forms
		if (self.current_page_id == null || self.current_page_id == page_id){
			History.replaceState(state, page_id, page_id);
		}		
		else {
			History.pushState(state, page_id, page_id);
		}

		this._update_self(page_id, request_path, view_identifier, args, kwargs);

	},

	// called from view, manages inserting of html and the history
	go : function(request, template_html, args, kwargs, save_state_on_exit){

		var self = this;

		// dump current state of the page to history
		var pages = document.getElementsByClassName("page");
		if (pages.length){
			pages[0].classList.add("faded-out");
			//pages[0].classList.remove("faded-in");
			//pages[0].classList.add("faded-out");
		}

		try {
			OverlayView.close_current_overlay();
		}
		catch {}

		if (self.save_state_on_exit == true){
			self._update_state();
		}

		self.save_state_on_exit = save_state_on_exit;

		var args = args || [];
		var kwargs = kwargs || {};

		// store request in kwargs
		kwargs.request = request.for_history(request);

		var target_element = self.container;
	
		if ("target_id" in kwargs){
			target_element = document.getElementById(kwargs.target_id);
		}
		
		var request_path = request.path;
		var page_id = "#" + request_path;

		self._add_to_history(page_id, request_path, request.view_identifier, template_html, args, kwargs);

		self._insert(target_element, template_html, args, kwargs);

		window.scrollTo(0,0);
	
		// has to come before post_render which is called in self._post_insert
		window.dispatchEvent(self.pagechanged_event);
		
		// calls post_render
		self._post_insert(request.view_identifier, args, kwargs);

		self._animations.fadein();

		self._on_new_page(request.view_identifier, args, kwargs);

		
		//fix range slider on iOS (bug https://github.com/hammerjs/hammer.js/issues/992)
		const ranges = RangeTouch.setup('input[type="range"]', { });

	}

}
