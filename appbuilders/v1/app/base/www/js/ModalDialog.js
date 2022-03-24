"use strict";

/*
* show a modal displaying the progress of an operation
* follows the xhr event nomenclature
*/
var ModalDialog = {

	_create : function(container_id){
		var self = Object.create(this);
		self.container = document.getElementById(container_id);
		self.title = self.container.getElementsByClassName("dialogbox-title")[0];
		self.content = self.container.getElementsByClassName("dialogbox-content")[0];

		return self;
	},

	create : function(container_id){
		var self = this._create(container_id);
		return self;
	},

	open : function(html, title){
		
		if (this.container.classList.contains("closed")){
			// the ModalDialog is closed, close open overlay if present
			if (typeof(OverlayView.close_current_overlay) == "function"){
				OverlayView.close_current_overlay();
			}
		}

		this.title.textContent = title;

		if (html != null){
			this.content.innerHTML = html;
		}
		this.container.classList.remove("inback");
		this.container.classList.remove("closed");
		// activate blocktouchthrough
		InteractionManager._activate_gesture_listeners(this.content);
		InteractionManager._activate_forms(this.content);

		var self = this;
		
		OverlayView.close_current_overlay = function(){
			self._close();
		}
		
	},

	close : function(self, request, args, kwargs){//called from html
		if (kwargs.currentTarget.classList.contains("closeperm")) {
			this._close(); // do not use "this._close"
		}
	},

	_close : function(){ // called from js

		OverlayView.close();

		this.container.classList.add("closed");
		var self = this;
		setTimeout(function(){
			self.container.classList.add("inback");
		}, 400);
	},

	set_content : function(html){
		this.content.innerHTML = html;
	}
};

/*
* ModalProgress needs to support multiple parts. e.g. 1 Dataset + 2 Images = 3 parts. Each part has its own xhr request
*/
var ModalProgress = derive(ModalDialog, {

	create : function(container_id){

		var self = this._create(container_id);

		self.progressbar_percent = self.container.getElementsByClassName("progressbar-percent")[0];
		self.progressbar_progress = self.container.getElementsByClassName("progressbar-inner")[0];
		self.progressbar_text = self.container.getElementsByClassName("progressbar-text")[0];

		return self;

	},

	onabort : function(event){
	},
	
	onerror : function(event){
	},

	// called when an XMLHttpRequest transaction completes successfully.
	onload : function(event){
		var self = this;
	},

	onloadstart : function(event, text){		

	},


	start : function(title, text, parts){

		var self = this;

		// the number of jobs to upload/download. eg 1 dataset and 2 images = 3 parts
		self.parts = parts || 1;
		self.current_part = 1;

		var text = text || "";

		var title = title || "";

		// set defaults
		self.progressbar_percent.textContent = "0";
		self.progressbar_progress.style.width = "0%";
		self.progressbar_text.textContent = text;

		self.open(title, null);

	},

	next_part : function(text){
		var self = this;
		var text = text || "";

		self.current_part = self.current_part + 1;
		self.progressbar_text.textContent = text;
	},

	finish : function(){
		var self = this;
		self.progressbar_progress.style.width = "100%";
		self.progressbar_percent.textContent = "100%";
		self.progressbar_text.textContent = _("Finished");
	},

	onprogress : function(event){

		var self = this;

		// finished parts determine initial percent
		// first part starts with 0 percent, second of 3 parts starts with 33%
		var initial_percent = parseInt(((self.current_part - 1) / self.parts) * 100);
 
		// the total percentage of one part. 3 parts -> 33% percent each part
		var part_percent = parseInt( 100/self.parts );

		// update percent and progressbar
		var loaded = event.loaded;
		var total = event.total;
		console.log('part loaded:' + event.loaded);
		console.log('part total:' + event.total);

		// eg loaded / total == 0.45
		// part_percent_loaded < part_percent
		var part_percent_loaded = parseInt( (event.loaded / event.total) * part_percent );

		var total_percent = initial_percent + part_percent_loaded;
		console.log('total_percent ' + total_percent);
		self.progressbar_percent.textContent = total_percent.toString();
		self.progressbar_progress.style.width = total_percent + "%";

	},

	manual_progress : function(){

		var self = this;

		var event = {
			"loaded" : 1,
			"total" : 1
		};

		self.onprogress(event);
	},

	progress_text : function(text){
		var self = this;
		self.progressbar_text.textContent = text;
	}

});

