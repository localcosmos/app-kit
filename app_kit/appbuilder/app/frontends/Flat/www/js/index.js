var app = {
	language : null,
	automatics: false,
	requires_geolocation : false, 
    initialize: function() {
        this.bindEvents();
    },
    bindEvents: function() {
        document.addEventListener('deviceready', this.onDeviceReady, false);
    },
    onDeviceReady: function() {

		console.log("device " + device.platform + " is ready");
		// give some devices time to hide the keyboard after entering the url
		if (device.platform == "browser"){
			setTimeout(function(){
				upstart.run(function(){

										
		
				});
			}, 50);
		}
		else {
			upstart.run(function(){
			
			});
		}
    },
};

app.initialize();
