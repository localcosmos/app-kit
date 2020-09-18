"use strict";
/*
* LocalcosmosRemoteAuthentication
* - authentication needs to query the server
* - offline devices with offline db: a user instances is saved in the db if not present yet
*/

var LocalCosmosRemoteAuthentication = {
	authenticate : function(request, kwargs, onsuccess, onerror){
		// username and password need to be in kwargs
		if (kwargs.hasOwnProperty("username") && kwargs.hasOwnProperty("password")){
			// try to authenticate the user with the server

			var username = kwargs["username"];
			var password = kwargs["password"];

			lcapi.get_token(username, password, function(data){
	
				var auth_data = {
					"auth_token" : data.token
				};

				// set the token for being able to query the server (mango_remotedb_api.perform_request)
				mango_session.auth_token = data.token;

				// return a user instance if successful
				// get the user object - this works only with the token
				LocalcosmosUser.objects.filter({"uuid":data.uuid}).first(function(user){
					
					if (user == null){
						// this can only happen if the device is not the browser
						// user not yet in device db, create the user entry and return the user
						// remotedb will not allow user creation

						// fetch the user from the remote DB, even if we are on the device
						var url = settings["REMOTEDB_API_URL"] + "LocalcosmosUser/get.json";

						mango_remotedb_api.perform_request(url, "POST", "JSON", {"uuid":data.uuid}, function(user_data){

							delete user_data["id"];
							user = LocalcosmosUser.create(user_data);
							user.save(user, function(user){

								onsuccess(user, auth_data);
							});	

						}, onerror)
										
					}
					else {

						onsuccess(user, auth_data);
					}

				});


			}, function(status, statusText, responseText){
				if (status == 400){
					onerror(AUTH_ERRORS.permission_denied, responseText);
				}
				else {
					alert("[Server Error] " + status + " " + responseText);
					// calling onerror would fire "PermissionDenied/Wrong credentials" - dont do this if the server is unreachable
					// onerror(status, responseText);
				}
			});
	
		}
		else {
			onerror(AUTH_ERRORS.unusable_credentials);
		}
	}
};
