/* get new pos all 5 mins and manage displays */
/* fire events when new positions are fetched */
var AppGeolocation = {

	watch_id : null,

	last_position : null,
	last_error : null,

	default_options : {
		"enableHighAccuracy" : true,
		"timeout" : 15 * 60 * 1000,
		"maximumAge" : 3 * 60 * 1000
	},

	start_watching : function(options, onSuccess, onError){
		var self = this;

		self.on_success = onSuccess;
		self.onError = onError;


		if (self.watch_id != null){
			self.stop_watching();
		}
		
		var options = options || {};

		if (!options.hasOwnProperty("enableHighAccuracy")){
			options["enableHighAccuracy"] = self.default_options["enableHighAccuracy"]; 
		}

		if (!options.hasOwnProperty("timeout")){
			options["timeout"] = self.default_options["timeout"]; 
		}

		if (!options.hasOwnProperty("maximumAge")){
			options["maximumAge"] = self.default_options["maximumAge"]; 
		}

		self.watch_id = navigator.geolocation.watchPosition(self._on_success, self._on_error, options);

	},

	stop_watching : function(){
		var self = this;
		if (self.watch_id != null){
			navigator.geolocation.clearWatch(self.watch_id);
		}
	},

	_on_success	: function(position){
		var self = AppGeolocation;

		self.last_position = position;
		self.last_error = null;


		// fire event
		var new_app_position_event = new CustomEvent("new_app_position", {
			detail : {
				position : position
			}
		});

		window.dispatchEvent(new_app_position_event);

		if (typeof self.on_success == "function"){
			self.on_success(position);
		}

	},

	_on_error : function(positionError){
		var self = AppGeolocation;
		self.last_error = positionError;
		self.last_position = null;

		if (typeof self.on_error == "function"){
			self.on_error(positionError);
		}
	}

};

/*
function(div_id, onPositionSuccess){
		
	// vars for manager
	var manager = this;
	var onPositionSuccess = onPositionSuccess;

	var marker = new google.maps.Marker({
		position: { lat: 0, lng: 0},
		map: null
	});

	this.watchId = null;
	this.position = null; // the position of the map marker if it was set by a human, not the position of the inputs or the gps sensor

	var map = new google.maps.Map(document.getElementById(div_id), {
		zoom: 14,
		center: {lat: -25.363, lng: 131.044},
		mapTypeId: google.maps.MapTypeId.TERRAIN,
		streetViewControl: false,
	});

	function placeMarker(latlng){
		marker.setMap(map);
		marker.setPosition(latlng);
	}

	// place a marker on click
	google.maps.event.addListener(map, "click", function(event){

		placeMarker(event.latLng)        

		var position = manager.latLngToPosition(event.latLng);
		manager.position = position;
		onPositionSuccess(position);
		manager.clearWatch();
    });


	this.latLngToPosition = function(latlng){
		var position = {
			coords : {
				latitude : latlng.lat(),
				longitude : latlng.lng(),
				accuracy : 0
			}
		};
		return position;
	}

	this.positionToLatLng = function(position){
		return new google.maps.LatLng(position.coords.latitude, position.coords.longitude);
	}

	this.initialPosition = function(position){
		var latlng = manager.positionToLatLng(position);
		placeMarker(latlng);
		setTimeout(function(){
			map.setCenter(latlng);
		}, 500);
	}

	// verify the position object, return a cleaned position or null
	function clean_position(position){
		try {
			if (typeof(position.coords.latitude) == "number" && typeof(position.coords.longitude) == "number" && typeof(position.coords.accuracy == "number")){
				var position_cleaned = {
					coords : {
						latitude : position.coords.latitude,
						longitude : position.coords.longitude,
						accuracy : position.coords.accuracy
					}
				};
				return position_cleaned;
			}
			else {
				return null;
			}
		}
		catch (e){
			return null;
		}
	}


	function onSuccess(position){
		var valid_position = clean_position(position);

		if (valid_position != null) {
			var latlng = manager.positionToLatLng(valid_position);
			placeMarker(latlng);
			map.setCenter(latlng);

			if (position.coords.accuracy < 100){
				manager.clearWatch();
			}
			onPositionSuccess(valid_position);
		}
	}

	function onError(e){
		alert(e);
	}

	this.watchPosition = function() {
		if (manager.watchId == null){
			manager.watchId = navigator.geolocation.watchPosition(onSuccess, onError, {enableHighAccuracy:true, timeout:60000, maximumAge:0});
			gps_indicator.classList.remove("glyphicon-refresh");
			gps_indicator.classList.add("blink");
			gps_indicator.classList.add("glyphicon-hourglass");
		}
	}

	this.clearWatch = function() {
		navigator.geolocation.clearWatch(manager.watchId);
		manager.watchId = null;
		gps_indicator.classList.remove("blink");
		gps_indicator.classList.remove("glyphicon-hourglass");
		gps_indicator.classList.add("glyphicon-refresh");
	}

	this.removeMarker = function(){
		marker.setMap(null);
		manager.position = null;
	}
	
}*/
