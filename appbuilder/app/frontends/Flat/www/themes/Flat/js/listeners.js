/* add your listeners here */

var listeners = {
	"NatureGuideView" : {},

	get_skeleton_context : function(){
		var context = {};

		var images = ["funding_partner_1", "funding_partner_2", "funding_partner_3"];

		var funding_partners = [];

		for (let k=0; k<images.length; k++){
			let key = images[k];
			if (typeof(theme_images) == "object" && theme_images.hasOwnProperty(key)){
				funding_partners.push(theme_images[key]);
			}
		}

		context["funding_partners"] = funding_partners;

		return context;
	},

	get_sidemenu_context : function(){
		return this.get_skeleton_context();
	}
};


document.addEventListener('identification_complete', function(event){
	// hide filters is hideable
	if (typeof(OverlayView.close_current_overlay) == "function"){
		OverlayView.close_current_overlay();
	}
});
