context_processors.auth = function(request){
	var extra_context = {
		"user" : request.user
	};

	return extra_context;
};
