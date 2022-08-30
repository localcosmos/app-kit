"use strict";
/*
* RemoteDB uses POST, PUT and DELETE, GET is not used because of ASCII restriction, urlencoded restriction, url length etc.
* this should be further examined as GET enables caching, POST does not
* the response type is currently added as eg .json (like suggested by django rest) - this should maybe be moved into the header
*/

var RemoteDB = derive(Database, {
	init : function(){
		// nothing to do
	},
	migrate : function(migratedCB){
		console.log("[djangoREST] bogus syncdb done");
		migratedCB();
	}
});


/* custom interfaces for models are located in this object
* if none is found, RemoteDBModelInterface is used
*/
var RemoteDBInterfaces = {};

/*
* mango RemoteDB API object for calling the servers API
*/
var mango_remotedb_api = {
	
	_cache : {}, // stores the last request in case of login errors

	_403_cache : {},

	// a middleware hook for manipulating the data sent to the mango_remotedb_api
	_process_data : function(data){
		for (let m=0; m<settings.REMOTEDB_MIDDLEWARE.length; m++){
			var middleware_name = settings.REMOTEDB_MIDDLEWARE[m];

			if (typeof window[middleware_name] != "object"){
				throw new Error("RemoteDBMiddleware " + middleware_name + " does not exist");
			}

			data = window[middleware_name].process_data(data);	

		}
		return data;
	},
	// a middleware hook for manipulating the headers sent to the mango_remotedb_api
	_process_headers : function(headers){
		for (var m=0; m<settings.REMOTEDB_MIDDLEWARE.length; m++){
			var middleware_name = settings.REMOTEDB_MIDDLEWARE[m];

			if (typeof window[middleware_name] != "object"){
				throw new Error("RemoteDBMiddleware " + middleware_name + " does not exist");
			}

			headers = window[middleware_name].process_headers(headers);	

		}
		return headers;
	},

	perform_request : function(url, request_method, response_type, data, onsuccess, onerror, options){

		var self = this;

		var options = options || {};
		var optional_params = {}	

		// the content type of the data being sent
		var headers = {};
		
		if (["POST", "PUT", "PATCH", "DELETE"].indexOf(request_method) >= 0){
			headers["Content-Type"] = "application/json; charset=UTF-8";

			if (options.hasOwnProperty("show_progress_modal") && options.show_progress_modal === true){

				optional_params["upload"] = {
					"onprogress" : function(event){
						modalProgress.onprogress(event);
					},
					"onload" : function(event){
						modalProgress.onload(event);
					},
					"onloadstart" : function(event){
						modalProgress.onloadstart(event);
					},
					"onabort" : function(event){
						modalProgress.onabort(event);
					},
					"onerror" : function(event){
						modalProgress.onerror(event);
					}
				};
			}

		}
		else if (request_method == "GET"){
			headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8";
		}
		
		// hook for middlewares
		var data = self._process_data(data);

		// hook for middlewares
		var headers = self._process_headers(headers);


		// check if FormData is necessary
		if (request_method != "GET"){

			// if the object contains files, use formdata
			var form_data = new FormData();
			var use_formdata = false;
			
			for (let key in data){

				let value = data[key];

				if (value instanceof File || value instanceof Blob){
					use_formdata = true;
					// ???
					delete headers["Content-Type"];

					form_data.append(key, value, value.name);
				}
				else {
					form_data.append(key, value);
				}
			}

			if (use_formdata == true){
				data = form_data;
			}
		}

		var params = {
			url : url,
			method : request_method,
			dataType : response_type,
			success : onsuccess,
			error: onerror,
			data : data,
			headers : headers,
			statusCode : self.statusCode_callbacks
		};

		for (let key in optional_params){
			params[key] = optional_params[key];
		}

		self._cache = params;

		ajax.send(params);
	},
	
	statusCode_callbacks : {
		// "403 forbidden" - invalid token - prompt the user to log in
		"403" : function(status, statusText, responseText){

			// invalid token, log out the user
			var self = mango_remotedb_api;
			self._403_cache = self._cache;

			// display a login prompt ?
			var login_view_name = settings["LOGIN_VIEW"];

			window[login_view_name].login_redirect = function(self, request, args, kwargs){
				// self is null from login_redirect arg
				var self = mango_remotedb_api;

				self.perform_request(self._403_cache.url, self._403_cache.method, self._403_cache.dataType, self._403_cache.data, self._403_cache.success, self._403_cache.error);			

			};

			HttpResponseRedirect(login_view_name);
		}
	}
};


/*
* If the dbType is "RemoteDB" the .objects attribute of all models will be a RemoteDBModelInterface.
*/
var RemoteDBModelInterface = derive(ModelInterface, {

	storage_location : "RemoteDB",

	create : function(modelname, db_identifier){

		var self = this._create(modelname, db_identifier);

		return self;

	},

	// the actual ajax api call
	_perform_request : function(url_suffix, request_method, response_type, data, onsuccess, onerror, options){
		
		var self = this;
		var onerror = onerror || self._error_handler;		

		var url = settings["REMOTEDB_API_URL"] + self.modelname + "/" + url_suffix + "." + response_type.toLowerCase();

		url = self._apply_limitoffset(url);
		
		mango_remotedb_api.perform_request(url, request_method, response_type, data, onsuccess, onerror, options);
		
	},

	_sanitize_filters : function(_filters){

		var self = this;

		var filters = {};

		for ( var key in _filters ) {

			if (key == "pk"){
				filters[window[self.modelname].Meta.primary_key] = _filters[key];
			}
			else {
				filters[key] = _filters[key];
			}
		}

		return filters;
	},

	_append_url_param : function(url, key, value){
		if (url.indexOf("?") < 0){ 	
				url = url + "?";
		}
		else {
			url = url + "&";
		}

		url = url + key + "=" + value;
		return url;
	},

	_apply_limitoffset : function(url){

		if (this.query_limit != null){
			url = this._append_url_param(url, "limit", this.query_limit);
		}
		if (this.query_offset != null){
			url = this._append_url_param(url, "offset", this.query_offset);
		}

		return url;

	},

	_error_handler : function(status, statusText, responseText){
		// resetting in the error callback currently does not work
		//var self = this;
		// reset all filters
		//self._reset();

		alert("Remote Database Error:" + status + " " + statusText + " " + responseText);
	},

	/******************************************************************************************
	* parsing values: from javascript to API
	******************************************************************************************/

	_parse_outgoing_data : function(key, value, callback) {

		var field_definition = window[this.modelname].fields[key];


		if (value != null){

			switch (field_definition.fieldClass){
				case "ForeignKey":

					if (field_definition.hasOwnProperty("to_field")){
						value = value[field_definition.to_field];
					}
					else {
						value = value[window[value.object_type].Meta.primary_key];
					}
					break;
			}
		}

		if (field_definition.fieldClass == "ImageField" && value != null){
			// value is a FlexImage
			value.blob(function(blob){

				// rotate image before upload if necessary
				value.correct_blob_image_orientation(blob, function(corrected_blob){

					var parsed_data = {
						"key": key,
						"value" : corrected_blob
					}

					callback(parsed_data);

				});

			});
		}
		else {

			var parsed_data = {
				"key" : key,
				"value" : value
			};

			callback(parsed_data);

		}
		
	},


	/******************************************************************************************
	* parsing values: from db to javascript
	******************************************************************************************/
	ImageField_to_javascript : function(model_field, value, callback){

		var url = value["url"];
		// ImageField valuesare FlexImages
		var path_parts = url.split("/");
		var filename = path_parts.pop();

		var thumbnails = {};

		each(model_field.thumbnails, function(thumbnail_name, definition, iterate){

			if (value.hasOwnProperty(thumbnail_name)){
				thumbnails[thumbnail_name] = value[thumbnail_name];
				iterate();
			}
			else {
				iterate();
			}

		}, function(){

			var fleximage = FlexImage.create(url, filename, thumbnails);
			callback(fleximage);

		});

	},

	// value is a dict receive from REST
	ForeignKey_to_javascript : function(model_field, value, callback){

		var Model = window[model_field.to_object];

		var model_instance = Model.create(value);

		callback(model_instance);		

	},

	/******************************************************************************************
	* implemented objects.* methods
	******************************************************************************************/
	
	// exists returns true or false
	exists : function(onsuccess, onerror){
		
		var self = this;
		var filters = self._sanitize_filters(filters);

		self._perform_request("exists", "POST", "JSON", filters, function(response){

			self._reset();
			var result = response["exists"];
			onsuccess(result);
			

		}, onerror);

	},

	get : function(filters, onsuccess, onerror){

		var self = this;
		var filters = self._sanitize_filters(filters);

		self._perform_request("get", "POST", "JSON", filters, function(response){

			// create a model instance from the response or return null
			self._result_to_model_instance(response, function(instance){
				self._reset();
				onsuccess(instance);
			});

		}, onerror);

	},

	// fetch is "filter"
	fetch : function(onsuccess, onerror){
		var self = this;
		
		var filters = self._sanitize_filters(self.filters);
		
		self._perform_request("filter", "POST", "JSON", filters, function(response){

			self._reset();

			// create model instances
			var instance_list = [];

			each(response, function(item, iterate){
				self._result_to_model_instance(item, function(instance){
					instance_list.push(instance);
					iterate();
				});
			}, function(){
				onsuccess(instance_list);
			});
			

		}, onerror);

	},

	first : function(onsuccess, onerror){
		var self = this;

		var filters = self._sanitize_filters(self.filters);

		self._perform_request("first", "POST", "JSON", filters, function(response){

			self._reset();

			// create a model instance from the response or return null
			self._result_to_model_instance(response, function(instance){
				onsuccess(instance);
			});

		}, onerror);

	},

	// apply this.filters, return number
	count : function(onsuccess, onerror){
		var self = this;

		var filters = self._sanitize_filters(self.filters);

		self._perform_request("count", "POST", "JSON", filters, function(response){

			// create a model instance from the response or return null
			var count = response["count"];
			self._reset();
			onsuccess(count);

		}, onerror);		

	},

	// {object}
	insert : function(object, onsuccess, onerror){
		var self = this;

		var options = {
			"show_progress_modal" : true
		};

		var parsed_object = {};

		each(object, function(key, value, iterate){
			
			self._parse_outgoing_data(key, value, function(parsed_data){

				parsed_object[parsed_data.key] = parsed_data.value;

				iterate();

			});
			
		}, function(){

			// parsing finished
			self._perform_request("insert", "POST", "JSON", parsed_object, function(response){
				// create a model instance
				self._result_to_model_instance(response, onsuccess);
				self._reset();

			}, onerror, options)

		});
		
	},

	// objects.filter({}).update({})
	// updates several rows by filter
	// update is a PATCH request updating many instances
	update : function(filters, values, onsuccess, onerror){
		alert("update_many not implemented");
		return false;		
		/*
		self._reset();
		each(response, function(item, iterate){

			self._result_to_model_instance(function(instance){
				response_instances.push(instance);
			}, iterate);

		}, function(){
			onsuccess(response_instances);
		});*/
	},

	// update_instance is a PUT request if only ONE object is updates (---> id)
	// modelinstance.save() triggers update_instance
	// update_instance
	update_instance : function(object_id, values, onsuccess, onerror){

		var self = this;
		
		var options = {
			"show_progress_modal" : true
		};

		var url_suffix = "update/" + object_id;


		var parsed_values = {};

		each(values, function(key, value, iterate){
			
			self._parse_outgoing_data(key, value, function(parsed_data){

				parsed_values[parsed_data.key] = parsed_data.value;

				iterate();

			});
			
		}, function(){
			// PUT
			self._perform_request(url_suffix, "PUT", "JSON", parsed_values, function(response){
				self._result_to_model_instance(response, onsuccess);
				self._reset();
			}, onerror, options);

		});


	},

	// instance.remove()
	remove_instance : function(object_id, onsuccess, onerror){

		var self = this;

		var url_suffix = "delete/" + object_id;

		self._perform_request(url_suffix, "DELETE", "JSON", {}, function(response){
			onsuccess();
		}, onerror);

	}
		
});
