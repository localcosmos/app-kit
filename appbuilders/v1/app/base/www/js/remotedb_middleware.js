/*
* RemoteDB middleware offers hooks for RemoteDBModelInterface
*/

var LocalCosmosRemoteDBMiddleware = {
	process_data : function(data){
		// app uuid is needed eg for determining if anonmyous uploads are allowed server-side
		// the app itself does check this, a server-side check should be implemented in case the user changes this permission
		// otherwise old app installs could still upload
		data["app_uuid"] = settings["APP_UUID"];
		data["platform"] = device.platform;
		if (window.location.pathname.indexOf("review") >= 0){
			data["review"] = 1;
		}
		return data;
	},
	process_headers : function(headers){
		// only do this if the user is registered
		/*if (mango_session.user != null && mango_session.user.is_authenticated){
			headers["Authorization"] = "Token " + mango_session.user.auth_token;
		}
		else */if (mango_session.auth_token != null){
			headers["Authorization"] = "Token " + mango_session.auth_token;
		}

		return headers;
	}
};
