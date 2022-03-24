"use strict";

var urlpatterns = [];

function path(url, view, kwargs){

	var kwargs = kwargs || {};

	var url_parts = get_path_parts(url);

	var supported_parameter_types = ["int", "str", "uuid", "slug"];

	var result = {
		"url" : url,
		"url_parts" : url_parts,
		"view" : view,
		"url_kwargs_by_index" : [], // the name of the kwargs in the correct order
		"kwargs" : kwargs,
		"typelist" : [], // length equals url_kwargs_keys - the type of the kwargs in the correct order
		"variable_count" : 0
	};

	for (var p=0; p<url_parts.length; p++){
		var part = url_parts[p];

		if (part[0] === "<"){
			if (part[part.length-1] != ">"){
				throw new Error("[path] Invalid url parameter: " + part);

			}

			var definition = get_url_kwarg_definition(part);

			if (supported_parameter_types.indexOf(definition[0]) == -1){
				throw new Error("[path] Invalid url parameter type: " + definition[0]);
			}

			result.typelist.push("variable");
			result.variable_count++;

			// add the name of the kwarg to the list
			result.url_kwargs_by_index.push(definition[1]);

		}
		else {
			result.url_kwargs_by_index.push(null);
			result.typelist.push("static");
		}

	}

	return result;

}

function get_url_kwarg_definition(pattern_part){
	return pattern_part.substring(1, pattern_part.length - 1).split(":");
}

// remove empty strings from list
function get_path_parts(path){

	var path_parts = path.split("/");

	var sanitized_path = path_parts.filter(
		function(v){
			return v!==''
		}
	);

	if (sanitized_path.length == 0){
		sanitized_path = ["/"];
	}

	return sanitized_path;

}

// URLResolver searches urlpatterns in urls.js and parses url kwargs if a match has been found
// it returns an object which includes the matched pattern and the parsed urlkwargs
var URLResolver = {

	resolve : function(url){
		// receive an url, return result
		// the received url can be in the form of "http(s)://domain.org#pattern or simply view_name/

		if (url.indexOf("http") >= 0){
			// it is an absolute url
			var parts = url.split("#");
			
			if (parts.length > 2){
				throw new Error("[URLResolver] mango urls may only have one '#' character");
			}

			if (parts.length == 1){
				var path = "/";
			}
			else {

				var path = parts[1];
			}

		}
		else {
			// it is a relative url, relative to the root domain
			var path = url;
		}

		// for later use: store request path
		var request_path = path;

		// strip off ?param= urlparams
		path = path.split("?")[0];

		// atomize path
		var url_parts = get_path_parts(path);

		var pattern_match = null;
		var resolved_url_kwargs = {};

		// try to find a matching pattern, not yet trying to parse url kwargs
		for (var p=0; p<urlpatterns.length; p++){
			var pattern = urlpatterns[p];

			var pattern_parts = pattern.url_parts;

			// check if the pattern matches
			// url_parts is an Array, so is the patterns first entry
			if (url_parts.length === pattern_parts.length){

				// check each pattern part against the url_part
				
				for (var q=0; q<pattern_parts.length; q++){

					var is_match = true;
					
					var pattern_part = pattern_parts[q];
					var url_part = url_parts[q];

					// first check if it is a param or not
					if (pattern_part[0] === "<"){

						// try to parse the url kwarg

						var definition = get_url_kwarg_definition(pattern_part);

						try {
							var parsed_kwarg = URLResolver.parse_kwarg[definition[0]](url_part);
						}
						catch (e){
	
							if (e instanceof TypeError) {
								is_match = false;
								break;
							}
							else {
								throw e;
							}

						}

						// parsed_kwarg is available
						resolved_url_kwargs[definition[1]] = parsed_kwarg;					

					}
					else {
						if (!(pattern_part == url_part)){
							is_match = false;
							break;
						}
					}
					
				}

				if (is_match === true) {
					pattern_match = pattern;
					// do not try other patterns if a match has been found
					break;
				}
				else {
					resolved_url_kwargs = {};
					continue;
				}

			}

		}

		if (pattern_match === null){
			alert("404");
		}
		else {
			
			// the resolver just returns the resolved url stuff including parsed kwargs
			var result = {
				"request_path" : request_path,
				"pattern" : pattern_match,
				"url_kwargs" : resolved_url_kwargs
			};

			return result;
		}

	},
	// try to parse the kwarg. if it fails throw a TypeError
	parse_kwarg : {
		"int" : function(value){
			var number = parseInt(value);

			if (Number.isNaN(number) == true){
				throw new TypeError("[URLResolver.parse_kwarg] Could not parse int: " + value);
			}

			return number;

		},
		"str" : function(value){

			var str = decodeURIComponent(value.toString());

			if (typeof str != "string"){
				throw new TypeError("[URLResolver.parse_kwarg] The following value failed parsing as string: " + str + ". It is of type " + typeof str);
			}
			
			return str;
		},
		"slug" : function(value){
			// check if it is a valid slug
			var is_valid = validate_slug(value);
			if (is_valid == false){
				throw new TypeError("[URLResolver.parse_kwarg] The following value is not a valid slug: " + value);
			}
			return value;
		},
		"uuid" : function(value){
			// check if it is a valid uuid
			var is_valid = validate_uuid(value);
			if (is_valid == false){
				throw new TypeError("[URLResolver.parse_kwarg] The following value is not a valid uuid: " + value);
			}
			return value;
		}
	}

};
