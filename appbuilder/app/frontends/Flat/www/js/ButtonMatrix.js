/*
 * ButtonMatrix Class for both app and web
 * VERSION: 0.1
 */
var ButtonMatrix = {

	touch_device : false,

	create : function(options){

		var self = this; // only one matrix at a time 
		
		// defaults
		self.options = {
			"demo" : false,
			"exposed_field" : null,
			"lock_exposed_field" : false
		};
		
		var options = options || {};
		for (var key in options){
			self.options[key] = options[key];
		}

		self.lockedExposedFieldButton = null;

		if (self.options.exposed_field != null){

			self.lockExposedFieldButton = document.getElementById("lock_exposed_field");

			self.lockExposedFieldButton.addEventListener("click", function(event){
				event.preventDefault();
				self.toggleLockExposedFieldButton(event);
			});
		}
		
		// add matrix log buttons - with click explanations for maintainer
		var taxoncells = document.getElementsByClassName("hastaxon");
			
		for (var c=0; c< taxoncells.length; c++){
			var cell = taxoncells[c];

			cell.classList.remove("touched");
		
			cell.addEventListener("touchstart", function(event){
				ButtonMatrix.touch_device = true;
				event.preventDefault();
				event.currentTarget.classList.add("touched");
				ButtonMatrix.quick_log(event);
			});

			cell.addEventListener("touchend", function(event){
				event.preventDefault();
				var target = event.currentTarget;

				setTimeout(function(){
					target.classList.remove("touched");
				},250);
			
			});

			cell.addEventListener("click", function(event){
				event.preventDefault();

				ButtonMatrix.quick_log(event);

				var target = event.currentTarget;

				if (ButtonMatrix.touch_device == false){
					target.classList.add("touched");
					setTimeout(function(){
						target.classList.remove("touched");
					}, 350);
				}
			});

		}

		return self;
	},

	quick_log : function(event){
		var self = ButtonMatrix;

		event.preventDefault();

		if (self.options.demo == true) {
			self.resetExposedField();
		}
		else {

			var url = event.currentTarget.getAttribute("action");

			// add the count as kwargs	

			HttpResponseRedirect(url);

			if (self.options.lock_exposed_field == false){
				self.resetExposedField();
			}
		}

	},

	resetExposedField : function(){
		var self = ButtonMatrix;

		if (self.options.exposed_field != null && self.options.lock_exposed_field == false){

			var field = document.getElementById("id_exposed_field");

			if (self.options.exposed_field.definition.initial != null){
				field.value = self.options.exposed_field.definition.initial;
			}
			else {
				field.value = '';
			}
		}
	},

	toggleLockExposedFieldButton : function(event){

		var self = ButtonMatrix;

		if (self.lockExposedFieldButton != null){

			var lock = event.currentTarget.getAttribute("data-lock");

			if (lock == "off"){
				self.lockExposedFieldButton.setAttribute("data-lock","on");
				self.lockExposedFieldButton.classList.remove("btn-secondary");
				self.lockExposedFieldButton.classList.add("btn-success");
				self.options.lock_exposed_field = true;
			}
			else {
				self.lockExposedFieldButton.setAttribute("data-lock","off");
				self.lockExposedFieldButton.classList.remove("btn-success");
				self.lockExposedFieldButton.classList.add("btn-secondary");
				self.options.lock_exposed_field = false;
			}
		}
	}
}
