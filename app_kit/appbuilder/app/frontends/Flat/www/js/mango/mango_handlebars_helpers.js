"use strict";

// currently, only 3 url kwargs are supported
Handlebars.registerHelper ('url', function (pattern_name, arg1, arg2, arg3, arg4, options) {

	var url = null;

	var url_kwargs = [];

	var optional_args = [arg1, arg2, arg3, arg4];

	var tried = [];

	for (var a=0; a<optional_args.length; a++){
		var arg = optional_args[a];
		if (typeof arg != "undefined" && arg != null){
			url_kwargs.push(arg);
		}
	}

	if (typeof options == "undefined"){
		// options has been assigned to arg1 or arg2, remove options from url_kwargs
		url_kwargs.pop();
	}

	var url = reverse(pattern_name, url_kwargs);

	return url;
});

Handlebars.registerHelper('ifequal', function(a, b, opts) {
	if (a == b) {
		return opts.fn(this);
	}
	else {
		return opts.inverse(this);
	}
});

Handlebars.registerHelper ('truncate', function (str, len) {
	var str = str.toString();
    if (str.length > len) {
        var new_str = str.substr (0, len+1);

        while (new_str.length) {
            var ch = new_str.substr ( -1 );
            new_str = new_str.substr ( 0, -1 );

            if (ch == ' ') {
                break;
            }
        }

        if ( new_str == '' ) {
            new_str = str.substr ( 0, len );
        }

        return new Handlebars.SafeString ( new_str +'...' ); 
    }
    return str;
});


Handlebars.registerHelper ('cut', function (str, len) {
	var str = str.toString();
    if (str.length > len) {
        var new_str = str.substr (0, len+1);

        while (new_str.length) {
            var ch = new_str.substr ( -1 );
            new_str = new_str.substr ( 0, -1 );

            if (ch == ' ') {
                break;
            }
        }

        if ( new_str == '' ) {
            new_str = str.substr ( 0, len );
        }

        return new Handlebars.SafeString ( new_str ); 
    }
    return str;
});


Handlebars.registerHelper('t', function (i18n_key) {
	var result = i18next.t(i18n_key);
	return new Handlebars.SafeString(result);
});


Handlebars.registerHelper('tp', function (i18n_key) {

	// ȵ is the namespace separator
	var lookup_key = 'plainȵ' + i18n_key;

	var result = i18next.t(lookup_key);
	return new Handlebars.SafeString(result);
});


Handlebars.registerHelper('ifIn', function(element, list, options) {
	if (list.indexOf(element) > -1) {
		return options.fn(this);
	}
	return options.inverse(this);
});

Handlebars.registerHelper('unixToDate', function(unixtime) {
	var date = new Date(parseInt(unixtime));
	return date.toLocaleString();
});

Handlebars.registerHelper('static', function(path) {

	var theme_folder = "themes/" + settings.THEME + "/";

	var themed_path = theme_folder + path;	

	return themed_path;
});

Handlebars.registerHelper('language', function(path) {
	return app.language;
});
