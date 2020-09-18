"use strict";
/*
* authenticate against backends declared in settings.AUTHENTICATION_BACKENDS
* the first successful authentication will stop the loop
*/
function authenticate(request, kwargs, onsuccess, onerror){
    /*
    * If the given credentials are valid, return a User object.
    */

	if (!(settings.hasOwnProperty("AUTHENTICATION_BACKENDS")) || settings.AUTHENTICATION_BACKENDS.length == 0){
		throw new Error("[authenticate] AUTHENTICATION_BACKENDS missing in settings or empty");
	}

	each(settings.AUTHENTICATION_BACKENDS, function(backend_name, iterate){

		if (typeof window[backend_name] != "object"){
			throw new Error("AuthenticationBackend '" + backend_name + "' not found");
		}

		var backend = window[backend_name];

		backend.authenticate(request, kwargs, function(user, auth_data){
			onsuccess(user, auth_data);
		}, function(error_type){
			// 
			// The credentials supplied are invalid to all backends, fire signal
			// user_login_failed.send(sender=__name__, credentials=_clean_credentials(credentials), request=request)
			if (error_type == AUTH_ERRORS.permission_denied){
				onerror();
			}
			else if (error_type == AUTH_ERRORS.unusable_credentials) {
				iterate();
			}
			else {
				console.log("[authenticate] unknown error_type: " + error_type);
				onerror();
			}
		});

	}, function(){
		// no backend authenticated successfully
		onerror();
	});
    
}

// currently mango is limited to token authentication
function login(request, user, auth_data){
	/*
    Persist a user id and a backend (user.backend) in the request and mango_session. This way a user doesn't
    have to reauthenticate on every request. Note that data set during
    the anonymous session is retained when the user logs in.
    */

	request.user = user;

	// set session
	mango_session.set(user, auth_data["auth_token"]);
	
	// signals are unsupported by mango
	// user_logged_in.send(sender=user.__class__, request=request, user=user)
}


function logout(request, user){

	mango_session.clear();
	request.user = mango_session.user;

}

var AUTH_ERRORS = {
	permission_denied : "PermissionDenied",
	unusable_credentials : "UnusableCredentials",
	user_does_not_exist : "UserDoesNotExist"
};
