/* load the app and create an essential navigator */

window.Connection = {
	"UNKNOWN": "UNKNOWN",
	"ETHERNET" :  "ETHERNET",
	"WIFI" : "WIFI",
	"CELL_2G" : "CELL_2G",
	"CELL_3G" : "CELL_3G",
	"CELL_4G" : "CELL_4G",
	"CELL" : "CELL",
	"NONE" : "NONE"
};


(function () {
  if ( typeof window.CustomEvent === "function" ) return false;

  function CustomEvent ( event, params ) {
    params = params || { bubbles: false, cancelable: false, detail: undefined };
    var evt = document.createEvent( 'CustomEvent' );
    evt.initCustomEvent( event, params.bubbles, params.cancelable, params.detail );
    return evt;
   }

  CustomEvent.prototype = window.Event.prototype;

  window.CustomEvent = CustomEvent;

})();

(function(){
	var deviceready = new CustomEvent('deviceready');

	window.navigator.notification = {
		// navigator.notification.alert(message, alertCallback, [title], [buttonName])
		alert : function(msg, alertCallback, title, buttonName){
			alert(msg);
		}
	};

	if (window.navigator.connection === null || typeof window.navigator.connection == "undefined"){
		window.navigator.connection = {
			type : "ETHERNET"
		};
	}

	// load lc specific cordova plugins for the browser

	var uuid_js = document.createElement('script');
	uuid_js.onload = function(){

		window.device = {
			platform : "browser",
			uuid : uuid.v4() //this has to be changed to the web_uuid as soon as the user authenticated AND is on webapp
		};

		var date_picker_js = document.createElement('script');

		date_picker_js.onload = function(){
			document.dispatchEvent(deviceready);
		};
		date_picker_js.src = 'webapp/datePicker.js';
		document.head.appendChild(date_picker_js);
	}

	uuid_js.src='webapp/uuid.js'
	document.head.appendChild(uuid_js);

})();
