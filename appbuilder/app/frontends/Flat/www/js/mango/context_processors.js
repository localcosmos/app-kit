context_processors.device = function(request){
	var extra_context = {
		"device" : device
	};

	return extra_context;
};
