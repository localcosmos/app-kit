"use strict";

context_processors.history = function(request){
	var extra_context = {
		"history" : History
	};

	return extra_context;
};
