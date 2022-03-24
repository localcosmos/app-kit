"use strict";

// material design appbar
var Appbar = {

	current_header_view : null,
	current_view_args : [],
	current_view_kwargs : {},

	load : function(view_identifier, args, kwargs){

		var self = this;

		if (app.theme.header_views.hasOwnProperty(view_identifier)){
			var HeaderView = app.theme.header_views[view_identifier];
		}
		else {
			var HeaderView = app.theme.header_views["default"];
		}

		if (self.current_header != HeaderView || (HeaderView.hasOwnProperty("always_load_appbar") && HeaderView.always_load_appbar == true)){
			//console.log("loading new appbar for " + page);

			Appbar.current_header_view = HeaderView;

			//
			var request = HttpRequest.create("GET");
			// run the middlewares
			request = Pagemanager._process_request(request);
			var kwargs = kwargs || {};
			var args = args || [];

			// prevent headerviews from messing with other object's kwargs
			var kwargs = clone(kwargs);

			Appbar.current_view_args = args;
			Appbar.current_view_kwargs = kwargs;

			window[HeaderView].dispatch(null, request, args, kwargs);

		}		

	},

	reload : function(){
		var request = HttpRequest.create("GET");
		// run the middlewares
		request = Pagemanager._process_request(request);
		window[Appbar.current_header_view].dispatch(null, request, Appbar.current_view_args, Appbar.current_view_kwargs);
	}
}
