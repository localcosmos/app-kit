"use strict";

/* render page in a modal, no history */
var ModalView = {

	/*modal_title : function(self){
		return '';
	},*/

	render_to_response : function(self, context){

		// show a Modal
		default_renderer.render(self.template_name, context, function(template_html){
			// insert the html into a modal
			modalDialog.open(template_html, self.modal_title(self));

			self.post_finished(self.args, self.initial_kwargs);

		});
	}
};


/*
* search the template for online_content that needs to be loaded
* loads online_content by flag
*/
var OnlineContentMixin = {

	load_online_content : function(container){

		var online_contents = container.querySelectorAll("[online-content]");

		var internet_status = getNetworkState();

		/*online_contents.forEach(function(oc){

			if (internet_status == "online") {

				var flag = oc.getAttribute("online-content");
				lcapi.get_online_content_by_flag(flag, function(html){
					oc.innerHTML = html;
				}, function(status, statusText, responseText){
					oc.innerHTML = '<div class="alert alert-danger p-0">Server Error:' + status + ' ' + statusText + '</div>';
				});

			}
			else {
				if (oc.hasAttribute("data-indicate-offline") && oc.getAttribute("data-indicate-offline") == "1"){
					oc.innerHTML = '<div class="alert alert-warning p-0">' + i18next.t('You are offline.') + '</div>';
				}
			}
		});*/
		
	},

	post_render : function(self, args, kwargs){

		var container_id = "online_content_container_id" in self ? self.online_content_container_id : "content";

		var container = document.getElementById(container_id);
		self.load_online_content(container);
	}
};
