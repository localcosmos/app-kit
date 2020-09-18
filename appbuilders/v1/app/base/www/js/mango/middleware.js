var MangoUserMiddleware = {
	process_request : function(request){
		// check if there is a user attached to the mango_session object
		if (mango_session.user != null){
			request.user = mango_session.user;
		}
		else {
			request.user = AnonymousUser.create();
		}
		return request;
	}
};
