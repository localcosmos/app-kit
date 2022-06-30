"use strict";

var View = derive;

/* OverlayView 
* - overlays are not pages, but overlay pages, like a modal oder a sidemenu
* - manages overlays
* - .open(overlay_view) receives the overlay_view
* - .close() receives nothing
*/
var OverlayView = {

	close_current_overlay : null,

	template_name : null,
	container_id : null,

	open : function(overlay_view){

		// allow only one open overlay
		if (typeof(OverlayView.close_current_overlay) == "function"){
			OverlayView.close_current_overlay();
		}

		document.body.classList.add("noscroll");

		OverlayView.close_current_overlay = function(){
			overlay_view.close();
			document.body.classList.remove("noscroll");
		}
	},
	
	close : function(){
		OverlayView.close_current_overlay = null;
	},


	render_content : function(self, context, callback){

		var context = context || {};

		default_renderer.render(self.template_name, context, function(template_html){
			var container = document.getElementById(self.container_id);
			Pagemanager._insert(container, template_html);
			callback();
		});
	}

};

/* args is a list[], kwargs is a dic{} */
var TemplateView = {

	is_view : true,
	identifier: null,

	login_required : false,

	needs_internet : false,

	template_name : null, // this has to be defined in the View "subclass" using derive

	save_state_on_exit : true,

	async_context : false, // flag if the view implements async get_context_data

	as_view : function(){
		return this;
	},

	// the async version should be function(self, kwargs, callback)
	get_context_data : function(self, kwargs, callback){
		var kwargs = kwargs || {};

		if (self.async_context == true){
			callback(kwargs);
		}
		else {
			return kwargs;
		}

	},

	render_to_response : function(self, context){

		// run context processors
		var context = Pagemanager._process_context(self.request, context);

		default_renderer.render(self.template_name, context, function(template_html){
			// insert the html using the pagemanager
			// pass initial_kwargs and not self.kwargs
			// event and several other objects are appended to kwargs
			Pagemanager.go(self.request, template_html, self.args, self.initial_kwargs, self.save_state_on_exit);
			self.post_render(self, self.args, self.initial_kwargs);
		});
	},

	// dispatch is the place where Object.create(this) is called
	// if a "subclass" overrides dispatch it has to use Object.create(this)
	dispatch : function(self, request, args, kwargs){

		if (typeof self == "undefined" || self == null){
			var self = Object.create(this);
		}

		var internet_status = getNetworkState();

		if (self.needs_internet === true && internet_status != "online"){
			alert(_("No Internet Connection"));
		}
		else {
			self.request = request;
			self.args = args;
			self.kwargs = kwargs;

			// prevent modification of kwargs passed from and to history
			self.initial_kwargs = clone(kwargs);

			if (request.method == "GET"){
				self.get(self, request, args, kwargs);
			}
			else if (request.method == "POST"){
				self.post(self, request, args, kwargs);
			}
			else {
				console.log("[View] method not allowed: " + request.method);
			}

		}

	},

	get : function(self, request, args, kwargs){

		if (self.async_context == true){
			self.get_context_data(self, kwargs, function(context){
				self.render_to_response(self, context);
			});
		}
		else {
			var context = self.get_context_data(self, kwargs);

			self.render_to_response(self, context);
		}
	},

	post : function(self, request, args, kwargs){
		alert('post not implemented yet')
	},
	// only called after render_to_response is called, not called if loaded from history
	post_render : function(self, args, kwargs){
	},
	// always called after a page has been rendered, also after loaded from history
	// called in Pagemanager._post_insert
	post_finished : function(args, kwargs){
	}

};

var FormView = derive(TemplateView, {

	success_url : null,
	form_class : null,
	prefix : null,

	get_prefix : function(self){
        //"""Return the prefix to use for forms."""
		return self.prefix;
	},

	get_initial : function(self){
		return {};
	},

	get_form_class : function(self){
		return self.form_class;
	},

	get_form : function(self, form_class){

		//"""Return an instance of the form to be used in this view."""

		var form_class = form_class || self.get_form_class(self);

		var form_kwargs = self.get_form_kwargs(self);

		return form_class.create(form_kwargs);

	},

	get_form_kwargs : function(self){

		//"""Return the keyword arguments for instantiating the form."""

		var kwargs = {
            'initial': self.get_initial(self),
            'prefix': self.get_prefix(self),
        };

        if (['POST', 'PUT', 'PATCH'].indexOf(self.request.method) >= 0 ){
            kwargs['data'] = self.request.POST;
		}

		return kwargs;
	},

	get_success_url : function(self){
        //"""Return the URL to redirect to after processing a valid form."""
        if (! self.hasOwnProperty(success_url) || self.success_url === null){
            alert("No URL to redirect to. Provide a success_url.")
		}
		return self.success_url;
	},

	form_valid : function(self, form){
        //"""If the form is valid, redirect to the supplied URL."""
        return HttpResponseRedirect(self.get_success_url(self))
	},

    form_invalid : function(self, form){
        //"""If the form is invalid, render the invalid form."""
        self.render_to_response(self, self.get_context_data(self, {"form":form}));
	},

    get_context_data : function(self, kwargs){

        //"""Insert the form into the context dict."""
        if (!kwargs.hasOwnProperty("form")){
            kwargs["form"] = self.get_form(self);
		}

		return FormView.super().get_context_data(self, kwargs);
	},

	post : function(self, request, args, kwargs){
        /*"""
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """*/

        var form = self.get_form(self);

        if (form.is_valid(form) == true){
            self.form_valid(self, form);
		}
        else {
			self.form_invalid(self, form);
		}
	}

});

/*
* RemoteView queries HTML from the server and adds it as a context variable
* RemoteView should display errors (404 etc) as an html page, not as an alert
*/

var RemoteView = derive(TemplateView, {

	error_template : '',

	// send an ajax request
	perform_request : function(self, url, request_method, response_type, data, onsuccess, onerror){

		var self = this;

		// the content type of the data being sent
		var headers = {};
		
		if (request_method == "POST"){
			headers["Content-Type"] = "application/json; charset=UTF-8";
		}
		else if (request_method == "PUT"){
			headers["Content-Type"] = "application/json; charset=UTF-8";
		}
		else if (request_method == "GET"){
			headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8";
		}
	
		// hook for middlewares
		var update_data = mango_remotedb_api._process_data({});

		// hook for middlewares
		var headers = mango_remotedb_api._process_headers(headers);


		if (data instanceof FormData){
			
			for (let key in update_data){
				data.append(key, update_data[key]);
			}

			// remove Content-Type from headers for FormData
			delete headers["Content-Type"];
		}
		else {
			for (let key in update_data){
				data[key] = update_data[key];
			}
		}

		var params = {
			url : url,
			method : request_method,
			dataType : response_type,
			success : onsuccess,
			error: onerror,
			data : data,
			headers : headers
		};

		ajax.send(params);
	},

	// return the api url
	get_api_url : function(self){
	},

	// a hook for adding params to api_url_suffix
	get_api_url_params : function(self){
		return {};
	},

	get_url : function(self){
		var url = settings["API_URL"] + self.get_api_url();

		// RemoteView urls need the protocol specified, otherwise it will be interpreted as a local call by the urlresolver
		// if the user did not specify the protocol, http is used
		// the server is then responsible for forwarding http to https
		if (url.indexOf("http") !=0){
			var url = "https://" + url;
		}

		return url;
	},

	// query the api to retrieve the form html
	get_html : function(self, onsuccess, onerror){

		var url = self.get_url(self);

		var data = self.get_api_url_params(self);

		// runs middleware to add app uuid and auth
		// url, request_method, response_type, data, onsuccess, onerror
		self.perform_request(self, url, "GET", "HTML", data, onsuccess, onerror);

	},
	get : function(self, request, args, kwargs){
		self.get_html(self, function(html){

			// render page
			var context = self.get_context_data(self, kwargs);
			context["html"] = html;

			self.render_to_response(self, context);

		}, self.on_error);
	},

	on_error : function(code, error, msg){
		alert('[RemoteView] Error in communication with the Server:' + code + ' ' + error + ' ' + msg);
	}
});

/*
* RemoteFormView fetches the form html from the API and only the server validates the form
* - uses FormData to send data
*/
var RemoteFormView = derive(RemoteView, {

	success_url : null,
	sent_data : null,

	get_success_url : function(self){
        //"""Return the URL to redirect to after processing a valid form."""
        if (! self.hasOwnProperty(success_url) || self.success_url === null){
            alert("No URL to redirect to. Provide a success_url.")
		}
		return self.success_url
	},

	get_api_url_params : function(self){
		var data = self.get_initial(self);
		return data;
	},
	
	get_initial : function(self){
		// initial form data, appended to GET request
		return {};
	},

	get_form : function(self){
		// look for the form in the html
		var form = Pagemanager.container.getElementsByTagName("form")[0];
		return form;
	},

	get_post_method : function(self){
		return "POST";
	},

	post : function(self, request, args, kwargs){
        // Handle POST requests : submit the form to the api and get html back
		// first, get the html form element
		var form = self.get_form(self);

		var submit_button = form.querySelectorAll("button[type='submit']")[0];
		submit_button.disabled = true
	
		// read the form fields
		
		var enctype = form.getAttribute("enctype");

		if (enctype == "multipart/form-data"){
			var form_data = new FormData(form);
		}
		else {
			var form_data = http.deserialize_form(form);
		}
	
		var url = self.get_url(self);
		mango_remotedb_api.perform_request(url, self.get_post_method(self), "HTML", form_data, function(form_html){

			// success_data should be accessible
			// as of 12/2017 Safari and Edge do not support FormData.get(key)
			self.success_data = http.deserialize_form(form);

			self.form_valid(self, form, form_html);

		}, function(status, statusText, responseText){

			// if error_code is 400 the form was invalid
			if (status == 400){
				// error_msg is the html
				self.form_invalid(self, form, responseText);
			}
			else {
				self.on_error(status, statusText, responseText);
			}
		});
        
	},

	form_valid : function(self, form, form_html){
        //"""If the form is valid, redirect to the supplied URL."""
        return HttpResponseRedirect(self.get_success_url(self));
	},

    form_invalid : function(self, form, form_html){
        //"""If the form is invalid, render the invalid form."""
        self.render_to_response(self, self.get_context_data(self, {"html":form_html}));
	}

});

/*
* APIFormView implements server-side form validation in addition to client-side validation
* APIFormView requires a form being defined in the app
*/
var APIFormView = derive(FormView, {

	api_url_suffix : null,

	get_api_url : function(self){
		var url = settings["API_URL"] + self.api_url_suffix + ".json";

		return url;

	},

	post : function(self, request, args, kwargs){
        /*"""
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """*/

        var form = self.get_form(self);

        if (form.is_valid(form) == true){
			// send to api
			var url = self.get_api_url(self);

			// use mango_remotedb_api.perform_request to set correct headers and auth
			mango_remotedb_api.perform_request(url, "POST", "JSON", form.cleaned_data, function(response_data){
				// server side success
				// make response_data available
				self.response_data = response_data;
				
            	self.form_valid(self, form);

			}, function(status, statusText, responseText){
				// server side error
				// make response_data available
				if (status == 400){
					self.response_data = JSON.parse(responseText);

					// update form errors
					for (var f=0; f<form.fieldlist.length; f++){
						var boundfield = form.fieldlist[f];
						if (self.response_data.hasOwnProperty(boundfield.name)){

							var error_list = self.response_data[boundfield.name];

							form.add_error(form, boundfield.name, error_list);
							
							for (var e=0; e<error_list.length; e++){
								boundfield.errors.push(error_list[e]);
							}

						}
					}
					self.form_invalid(self, form);

				}
				else {
					alert("Server Error: " + status + " " + statusText)
				}
			});
		}
        else {
			self.form_invalid(self, form);
		}
	}
});
