"use strict";

/*
* mango apps are javascript only
* href links are hijaxed and the href link is the functionname
* a href="functionname?param1=1&param2=2"
* urls do not matter
*/
var ajax = {

	parse_json : function(responseText){
		return JSON.parse(responseText);
	},

	error : function(status, statusText, responseText){
		alert("[xhr] Error " + status + " : " + statusText + " " + responseText);
	},
	
	parse_html : function(responseText){
		return responseText;
	},

	parse_xml : function(responseText){
		var parser = new DOMParser();
		var response = parser.parseFromString(responseText, "text/xml");
		return response;
	},

	serialize : function(data){
		// converts {"a":1, "b":2} to a=1&b=2
		var urlencoded = "";

		for (var key in data){
			urlencoded += "" + encodeURIComponent(key) + "=" + encodeURIComponent(data[key]) + "&";
		}

		urlencoded = urlencoded.substring(0, urlencoded.length - 1);

		return urlencoded; 
	},

	send : function(_settings){

		var self = this;

		var settings = {
			async : true,
			method: "GET",
			headers : {
				"X-Requested-With" : "XMLHttpRequest"//,
				//"Content-Type" : 'application/x-www-form-urlencoded; charset=UTF-8'
			},
			statusCode : {
			},
			error : this.error,
		};

		for (var setting in _settings){
			var value = _settings[setting];
			if (typeof value == "object"){

				if (value == null){
					settings[setting] = value;
				}
				else {

					if (!( settings.hasOwnProperty(setting) )){
						settings[setting] = value;
					}
					else {
						for(var key in value){
							settings[setting][key] = value[key];
						}
					}
				}
			}
			else {
				settings[setting] = value;
			}
		}

		// settings
		/*
		{
			async: true or false, defaults to true
			method : GET or POST,
			data : "" Type: PlainObject or String or Array Data to be sent to the server. It is converted to a query string, if not already a string. It's appended to the url for GET-requests.
			 dataType (default: html)) Type: String The type of data that you're expecting back from the server.
			success : 
			error : function   // catches 4xx and 5xx errors, not xhr errors like CORS
			statusCode : {
				404 : function
			},
			// progress bar settings
			upload: {
				onload : function,  // success
				onloadstart : function,
				onabort: function,
				onerror : function,   // catches true xhr errors like CORS, not 4xx and 5xx errors 
				onprogress : function
			},
			download: {
				onload : function,  // success
				onloadstart : function,
				onabort: function,
				onerror : function,   // catches true xhr errors like CORS, not 4xx and 5xx errors 
				onprogress : function
			}
		}
		*/

		/*
			1xx Informational.
			2xx Success.
			3xx Redirection.
			4xx Client Error.
			5xx Server Error.
		*/

		console.log("[xhr] " + settings.url);

		// how to abort an xhr if multiple xhrs are run?
		var xhr = new XMLHttpRequest();

		xhr.onload = function(){
			console.log("[xhr] finished with status " + xhr.status);

			// the statusCode function overrides success/ error functions
			if (settings.statusCode.hasOwnProperty(xhr.status)){
				settings.statusCode[xhr.status](xhr.responseText);
			}
			else {


				var result = parseInt(xhr.status/100);

				if ((result == 2 || result == 0) && xhr.response){

					if (settings.hasOwnProperty("dataType") && settings.dataType != null && typeof settings.dataType != "undefined"){
						try {
							var parse_fn = "parse_" + settings.dataType.toLowerCase();
							var parsed_response = ajax[parse_fn](xhr.responseText);
						}
						catch(e){

							if (typeof settings.error == "function"){
								settings.error(xhr.status, "Server error: invalid response or Server not reachable." , "Could not parse " + settings.dataType + "." );
							}
							return false;
						}
					}
					else {
						var parsed_response = xhr.responseText;
					}

					if (typeof settings.success == "function"){
						settings.success(parsed_response, xhr.status);
					}

				}
				else {
					console.log("[xhr] ERROR : " + xhr.status + " " + xhr.statusText + " " + xhr.responseText);

					if (typeof settings.error == "function"){
						settings.error(xhr.status, xhr.statusText, xhr.responseText);
					}
				}

			}

			if (typeof settings.complete == "function") {
				settings.complete(xhr.responseText, xhr.status);
			}
		};

		// onerror is not for 4xx or 5xx error, but for xhr errors
		xhr.onerror = function(){

			var error_msg = "[xhr] ERROR : " + xhr.status + " " + xhr.statusText + " " + xhr.responseText;
			console.log(error_msg);

			if (_settings.hasOwnProperty("error") && typeof(_settings.error) == "function"){
				_settings.error(xhr.status, xhr.statusText, xhr.responseText);
			}
			else {
				alert("Server not reachable. " + error_msg);
				throw new Error(error_msg);
			}
		};

		// apply upload onprogress if in settings
		if (["POST", "PUT", "PATCH", "DELETE"].indexOf(settings.method) >= 0){

			if (settings.hasOwnProperty("upload")){
				for (let key in settings.upload){
					xhr.upload[key] = settings.upload[key]
				}
			}

		}
		
		/* onreadystatechange is deprecated in favor of onload/onerror
		xhr.onreadystatechange = function(){

			console.log("[xhr] readyState " + xhr.readyState);

			switch (xhr.readyState){
				case 4:

					console.log("[xhr] finished with status " + xhr.status);

					// the statusCode function overrides success/ error functions
					if (settings.statusCode.hasOwnProperty(xhr.status)){
						settings.statusCode[xhr.status](xhr.responseText);
					}
					else {
	

						var result = parseInt(xhr.status/100);

						if ((result == 2 || result == 0) && xhr.response){

							if (settings.hasOwnProperty("dataType") && settings.dataType != null && typeof settings.dataType != "undefined"){
								try {
									var parse_fn = "parse_" + settings.dataType.toLowerCase();
									var parsed_response = ajax[parse_fn](xhr.responseText);
								}
								catch(e){

									if (typeof settings.error == "function"){
										settings.error(xhr.status, "Server error: invalid response or Server not reachable." , "Could not parse " + settings.dataType + "." );
									}
									return false;
								}
							}
							else {
								var parsed_response = xhr.responseText;
							}

							if (typeof settings.success == "function"){
								settings.success(parsed_response, xhr.status);
							}

						}
						else {
							console.log("[ajax] ERROR : " + xhr.status + " " + xhr.statusText + " " + xhr.responseText);

							if (typeof settings.error == "function"){
								settings.error(xhr.status, xhr.statusText, xhr.responseText);
							}
						}

					}

					if (typeof settings.complete == "function") {
						settings.complete(xhr.responseText, xhr.status);
					}
					
					break;
				default:
					break;
			}
		};*/


		var data = null;

		// check if settings.data needs to be parsed or urlencoded
		if (settings.hasOwnProperty("data")){

			// settings.data always is a javascript object {lo:ve}
			// parse it according to the Content-Type header
			// application/json: JSON.stringify()
			// x-www-form-urlencoded : parse as url parameters
			// if FormData is sent, the headers may not contain Content-Type
			if (settings.data instanceof FormData){
				// do not alter data
				data = settings.data;
				delete settings.headers["Content-Type"];
			}
			else if (settings.headers.hasOwnProperty("Content-Type") && settings.headers["Content-Type"].indexOf("application/json") != -1){
				data = JSON.stringify(settings.data);
			}
			else if (settings.headers.hasOwnProperty("Content-Type") && settings.headers["Content-Type"].indexOf("x-www-form-urlencoded") != -1){
				var urlparams = self.serialize(settings.data);

				if (settings.url.indexOf("?") > 0){
					settings.url = settings.url + "&" + urlparams;
				}
				else {
					settings.url = settings.url + "?" + urlparams;
				}
				// POST needs data to be param=something&param2=somethingelse
				data = urlparams;
			}
			else {
				// default
				data = settings.data;
			}

		}
		
		xhr.open(settings.method, settings.url, true);

		if (device.platform != "browser"){
			xhr.withCredentials = true;
		}

		for (var key in settings.headers) {
			xhr.setRequestHeader(key, settings.headers[key]);
		}

		if (data != null){
			xhr.send(data);
		}
		else {
			xhr.send();
		}
	},

	POST : function(url, data, onsuccess, onerror){
		this.send({
			url : url,
			method: "POST",
			dataType : "HTML",
			success: onsuccess,
			error : onerror,
			data : data
		});
	},

	GET : function(url, data, onsuccess, onerror){
		this.send({
			url : url,
			method: "GET",
			dataType : "HTML",
			success: onsuccess,
			error : onerror,
			data : data
		});
	},

	getJSON : function(url, data, onsuccess, onerror){
		// do not alter content-type to json as the body will be ignored on GET
		this.send({
			url : url,
			method: "GET",
			dataType : "JSON",
			success: onsuccess,
			error : onerror,
			data : data
		});
	},

	postJSON : function(url, data, onsuccess, onerror){
		this.send({
			url : url,
			method : "POST",
			dataType : "JSON",
			success : onsuccess,
			error: onerror,
			data : data,
			headers : {
				"Content-Type" : 'application/json'
			}
		});
	},

	putJSON : function(url, data, onsuccess, onerror){
		this.send({
			url : url,
			method : "PUT",
			dataType : "JSON",
			success : onsuccess,
			error: onerror,
			data : data,
			headers : {
				"Content-Type" : 'application/json'
			}
		});
	}
};
