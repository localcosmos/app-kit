/*
* Local Cosmos API used by both webapp and app to communicate with server (REST)
* 
* - user authentication
* - user-dataset up- and downloads (sync)
* - register new account
* - fetching online_content
*/

// PUT is idempotent (e.g. client knows url of entity/dataset), POST is not


var api_endpoints = {
	"get_token" : "auth-token",
	"get_browser_client_id" : "get-browser-client-id",
	"get_online_content" : "online-content",
	"get_online_content_by_flag" : "online-content/list",
	"get_sponsor_list" : "sponsoring/sponsors"
};

/*
* api for Local Cosmos (non-mango)
* models use mangos RemoteDBModelInterface
*/
var lcapi = {

	// get_token should not use mango_remotedb_api, because this calls middlewares an adds authorization to the headers
	// get_token is for unauthorized stuff
	get_token : function(username, password, onsuccess, onerror){

		var url_suffix = api_endpoints["get_token"];

		var url = settings["API_URL"] + url_suffix + ".json";

		var data = {
			"username" : username,
			"password" : password,
			"client_id" : device.uuid,
			"platform" : device.platform
		};

		ajax.send({
			url : url,
			method : "POST",
			dataType : "JSON",
			success : onsuccess,
			error: onerror,
			data : data,
			headers : {
				"Content-Type" : "application/json; charset=UTF-8"
			}
		});
	},

	get_online_content_by_flag : function(flag, onsuccess, onerror){

		var url = settings.API_URL + api_endpoints["get_online_content_by_flag"] + "/?language=" + app.language;

		var data = {
			"flag" : flag,
			"app_uuid" : settings.APP_UUID
		}

		if (settings.hasOwnProperty("PREVIEW") && settings.PREVIEW == true){
			data["preview"] = 1;
		}

		ajax.send({
			url : url,
			method : "GET",
			dataType : "HTML",
			success : onsuccess,
			error: onerror,
			data : data,
			headers : {
				"Content-Type" : "x-www-form-urlencoded"
			}
		});

	},

	get_sponsor_list : function(onsuccess, onerror){

		var url = settings.API_URL + api_endpoints["get_sponsor_list"] + "/?sponsor_type=main_sponsors&source=" + device.uuid;

		var headers = {
			"Content-Type" : "application/json; charset=UTF-8"
		};

		ajax.send({
			url : url,
			method : "GET",
			dataType : "JSON",
			success : onsuccess,
			error: onerror,
			headers : headers
		});
	}

};
