"use strict";

/* 
* MatrixFilterValue
* - an input like radio, checkbox or slider represents one MatrixFilterValue
* - multiple inputs/radios with the same name(uuid) together form the MatrixFilter
*/
var event_identification_complete = document.createEvent('Event');
event_identification_complete.initEvent('identification_complete', true, true);


var MatrixFilterValue = {

	create : function(input, matrix_filter_type){
		var self = Object.create(this);

		self.uuid = input.name;

		self.matrix_filter_type = matrix_filter_type;
		
		if (matrix_filter_type == "TaxonFilter"){
			self.value = input.dataset.value;
		}
		else {
			self.value = input.value;
		}

		// value as string
		self.id = '' + self.uuid + '_' + self.value;
		
		if (matrix_filter_type == "ColorFilter"){
			// json stringify does not produce "1.0" for floats
			self.value = JSON.stringify(JSON.parse(self.value));
			self.id = '' + self.uuid + '_' + self.value;
			self.id = self.id.replace(/\s/g, '');
			self.value = JSON.parse(self.value);
		}
	
		self.input = input;
		
		self.allow_multiple_values = false;
		
		if (self.input.type == "checkbox"){
			self.allow_multiple_values = true;
		}
		

		return self;
	},
	
	hide : function(){
		var self = this;
		
		self.input.parentElement.classList.add("matrix-filter-inactive");
		
		return self;
	},
	
	show : function(){
		var self = this;
		
		self.input.parentElement.classList.remove("matrix-filter-inactive");
		
		return self;
	}
};


/*
	Identification Matrix
	- reads filters from the filter form
	- multiple selections of values of properties are ANDed together
*/
var IdentificationMatrix = {

	create : function(filter_form_id, get_filters_and_items, options){

		var self = Object.create(this);
		
		self.filterform = document.getElementById(filter_form_id);

		self.options = options || {};

		/* the current space according to the filter form, defaults to the empty space */
		self.current_filters = null;

		/* a dictionary holding the currently possible values for each uuid of a property
		 * this is used to hide/show property values
		 * this should be a list of ids of DOM elements
		 */
		self.possible_values = [];

		// a list of all VALUES of matrix filters as MatrixFilterValue Instances
		self.matrix_filter_values = [];

		

		self.visible_count = 0;
		
		// containers
		self.keynodes_container = document.getElementById("keynodes");
		self.sorted_out_keynodes_container = document.getElementById("sorted-out-keynodes");
		
		
		// fetch items
		self.update = function(){

			get_filters_and_items(function(filters_and_items_json){

				self.data = filters_and_items_json;
				self._attach_filterupdate_listeners();
			});
			
		};

		self.update();

		return self;

	},

	/* this only collects radios, checkboxes and ranges */
	_read_form : function(){
		var self = this;

		var elements = self.filterform.elements;
		
		// a dicitonary {"matrix_filter_uuid":[value,value]}
		var selected_filters = {};

		for (let e=0; e<elements.length; e++) {
		
			let element = elements[e];
			let matrix_filter_uuid = element.name;
			let matrix_filter = self.data.matrix_filters[matrix_filter_uuid];

			if (element.type == "radio" || element.type == "checkbox"){

				if (element.checked){
				
					let value = element.dataset.value;
					
					if (matrix_filter.type == "ColorFilter"){
						value = JSON.parse(value);
					}
				
					if (selected_filters.hasOwnProperty(matrix_filter_uuid)){
						selected_filters[matrix_filter_uuid].push(value);
					}
					else {
						selected_filters[matrix_filter_uuid] = [value];
					}
				}
			}
			else if (element.type == "range"){
			
				matrix_filter_uuid = element.dataset.uuid;
				
				let input = document.getElementById(element.id + "_value");

				if (input.value.length){
					//matrix_filter_uuid = input.name;
					selected_filters[matrix_filter_uuid] = [element.value];
				}
			}
		}

		return selected_filters;
	},

	_attach_filterupdate_listeners : function(){
		var self = this;

		// horizontal sliders
		// checkboxes are multiselect, ranges are single select
		var inputs = self.filterform.querySelectorAll('input[type=radio], input[type=checkbox]');

		for (let i=0; i<inputs.length; i++){
			let input = inputs[i];

			let matrix_filter_type = self.data.matrix_filters[input.name]["type"];
			let matrix_filter_value = MatrixFilterValue.create(input, matrix_filter_type);
			self.matrix_filter_values.push(matrix_filter_value);

			input.addEventListener('change', function(event){
				self.apply_filters(event);

				// slide to the beginning
				var _slider_container = event.currentTarget.parentElement.parentElement;
				_slider_container.style.transform = 'translate3d(0px, 0px, 0px)';

			});

		}

		// ranges currently do not work with autoupdate
		var ranges = self.filterform.querySelectorAll('input[type=range]');
		for (var r=0; r<ranges.length; r++){
			var range = ranges[r];

			range.addEventListener('change', function(event){
				self.apply_filters(event);
			});

			range.addEventListener('clear', function(event){
				self.apply_filters(event);
			});


		}
	},
	
	// compare two spaces
	// always check if subset_space is a subset of superset_spave  (subset_space, superset_space)
	// case item: selected space is subset of item space
	// case restriction: restriction space is subset os selected space
	
	compare_DescriptiveTextAndImagesFilter : function(subset_space, superset_space){
		
		const is_subset = subset_space.every(val => superset_space.includes(val));
		return is_subset;
		
	},
	
	compare_TextOnlyFilter : function(subset_space, superset_space){
		var self = this;
		return self.compare_DescriptiveTextAndImagesFilter(subset_space, superset_space);
	},
	
	
	compare_RangeFilter : function(subset_space, superset_space){
	
		var value = parseFloat(subset_space[0]);

		var is_subset = true
						
		if (value){
			if (value < superset_space[0] || value > superset_space[1]){
				is_subset = false;
			}
		}
		
		return is_subset;
	},
	
	compare_NumberFilter : function(subset_space, superset_space){
	
		var is_subset = true;
	
		for (let v=0; v<subset_space.length; v++){
		
			let subset_number = parseFloat(subset_space[v]);
	
			if (superset_space.indexOf(subset_number) == -1){
				is_subset = false;
				break;
			}
		}
		
		return is_subset;
	},
	
	compare_ColorFilter : function(subset_space, superset_space){
		// filter items: selected space is subset_space, item space is superset_space
		var self = this;
	
		var is_subset = true;
	
		for (let v=0; v<subset_space.length; v++){
							
			let subset_color = subset_space[v];
			
			if (subset_color[0] instanceof Array){
			
				let subset_gradient = subset_color;
				
				let subset_gradient_occurs_in_superset = false;
			
				// gradients have to be compared
				// check if all gradients of the subset occur in the superset

				for (let c=0; c<superset_space.length; c++){
				
					var superset_gradient = superset_space[c];
					
					if (superset_gradient[0] instanceof Array){
						
						var equals = self.compare_gradients(superset_color, subset_color);
						if (equals == true){
							subset_gradient_occurs_in_superset = true;
							break;
						}
					}
				}
				
				if (subset_gradient_occurs_in_superset == false){
					is_subset = false;
					break;
				}
			}
			
			else {
			
				let subset_rgb = [0, 0, 0, 0];
				
				for (let cp=0; cp<subset_color.length; cp++){
					let color_part = parseInt(subset_color[cp]);
					subset_rgb[cp] = color_part;
				}

				// compare the 2 rgb values. the selected value is compare with all values of the item
				// as soon as one color matches, the item is visible
				
				let subset_color_occurs_in_superset = false;

				for (let r=0; r<superset_space.length; r++){
					let superset_rgb = superset_space[r];

					let equals = self.compare_colors(superset_rgb, subset_rgb);
					if (equals == true){
						subset_color_occurs_in_superset = true;
						break;
					}
				}
				
				if (subset_color_occurs_in_superset == false){
					is_subset = false;
					break;
				}
			}
			
		}
		
		return is_subset;
	
	},
	
	// superset_space is a taxon as json, not a list
	// this function checks if any of the taxa in subset_space is equal to or a descendant of the superset_space taxon
	/* check if a lower taxon is a descendant of a higher taxon
	* {"taxa": [{"taxon_nuid": "001", "name_uuid": "f61b30e9-90d3-4e87-9641-eee71506aada", "taxon_source": "taxonomy.sources.col", "taxon_latname": "Animalia"}], "latname": "Animalia", "is_custom": false}
	*/
	compare_TaxonFilter : function(subset_space, superset_space){
	
		var is_subset = false;

		var subset_taxa = subset_space["taxa"];
		
		for (let t=0; t<subset_taxa.length; t++){
		
			let subset_taxon = subset_taxa[t];

			if (subset_taxon["taxon_source"] == superset_space["taxon_source"]){

				let is_descendant = superset_space["taxon_nuid"].startsWith(subset_taxon["taxon_nuid"]);

				if (is_descendant == true){
					is_subset = true;
					break;
				}

			}
			else {
				continue;
			}

		}

		return is_subset;
	
	},
	

	compare_colors : function(color_a, color_b){

		for (var c=0; c<color_a.length; c++){
			if (color_b[c] != color_a[c]){
				return false;
			}
		}
		return true;
	},
	
	compare_gradients : function(gradient_a, gradient_b){
		// gradients are arraysof arrays [[255,255,255,1],[0,0,0,1]]
		var gradient_a_color_count = gradient_a.length;
		var gradient_b_color_count = gradient_b.length;
		
		if (gradient_a_color_count != gradient_b_color_count){
			return false;
		}
		
		for (let c=0; c<gradient_a_color_count; c++){
			let color_a = gradient_a[c];
			let color_b = gradient_b[c];
			
			let equals = this.compare_colors(color_a, color_b);
			
			if (equals == false){
				return false;
			}
		}
		
		return true;
		
	},

	
	/*
		iterate over all matrix filters, check if the key "restrictions" is present
		- iterate over these restrictions and check if all of them are met
	*/
	work_matrix_filter_restrictions : function(event, selected_filters){
	
		var self = this;

		for (let matrix_filter_uuid in self.data["matrix_filters"]) {
		
			let matrix_filter = self.data["matrix_filters"][matrix_filter_uuid];
			
			// only proceed if the matrix filter is restricted
			if (matrix_filter.hasOwnProperty("restrictions") && Object.keys(matrix_filter.restrictions).length ){
				
				let all_restrictions_are_met = true;
				
				// check visibility of matrix_filter
				// iterate over all restrictions, and check if the restrictions are met by selected_filters
				for (let restriction_filter_uuid in matrix_filter["restrictions"]) {

					let restriction_filter = self.data["matrix_filters"][restriction_filter_uuid];
					let restriction_filter_space = matrix_filter["restrictions"][restriction_filter_uuid];
					
					if (restriction_filter.type == "TaxonFilter"){
						alert("taxonomically restricted visibility is currently not supported");
					}
					
					else {
				
						if (selected_filters.hasOwnProperty(restriction_filter_uuid)){

							let selected_matrix_filter = self.data["matrix_filters"][restriction_filter_uuid];
							let selected_matrix_filter_space = selected_filters[restriction_filter_uuid];
							
							let compare_fn_name = "compare_" + selected_matrix_filter.type;

							let is_subset = self[compare_fn_name](restriction_filter_space, selected_matrix_filter_space);

							if (is_subset == false){
								all_restrictions_are_met = false;
								break;
							}
						
						}
						else {
							all_restrictions_are_met = false;
							break;
						}
					}
				
				}
				
				
				
				let matrix_filter_element = document.getElementById(matrix_filter_uuid);
				matrix_filter_element.classList.add("restriction-active");
				
				if (all_restrictions_are_met == true){
					matrix_filter_element.classList.remove("restriction-active");
				}
				else {
					matrix_filter_element.classList.add("restriction-active");
				}

			}	
		
		}
	
	},

	/* create a space from the filterform and apply it to all current items */
	apply_filters : function(event){
	
		var self = this;
		
		var hide_overlay_on_completion = true;

		self.visible_count = 0;

		self.possible_values = [];

		// formdata is unsupported by IE
		var selected_filters = self._read_form();

		self.current_filters = selected_filters;

		var selected_filters_uuids = Object.keys(selected_filters);
		
		// iterate over all matrix filters - hide or unhide filter
		self.work_matrix_filter_restrictions(event, selected_filters);
		
		// iterate over all items
		for (let i=0; i<self.data.items.length; i++){
		
			let item = self.data.items[i];

			let item_is_visible = true;
			

			// iterate over all filters and check if the items space is a subspace of selected_filters
			for (let k=0; k<selected_filters_uuids.length; k++){

				let selected_matrix_filter_uuid = selected_filters_uuids[k];

				let selected_matrix_filter = self.data.matrix_filters[selected_matrix_filter_uuid];
				let selected_matrix_filter_type = selected_matrix_filter["type"];
				
				// the currently selected space of this matrix filter
				let selected_matrix_filter_space = selected_filters[selected_matrix_filter_uuid];
				
				if (selected_matrix_filter_type == "TaxonFilter"){
				
					// add TaxonFilter to possible values, use the name of the taxon filter
					let taxonfilter_property_value_id = "" + selected_matrix_filter_uuid + "_" + selected_matrix_filter_space;
					self.possible_values.push(taxonfilter_property_value_id);
				
					// decode b64 encoded json
					selected_matrix_filter_space = JSON.parse(atob(selected_matrix_filter_space));
				
					if (item.hasOwnProperty("taxon") && item["taxon"] != null){
						let is_subset = self.compare_TaxonFilter(selected_matrix_filter_space, item["taxon"]);
						
						if (is_subset == false){
							item_is_visible = false;
							break;
						}
					}
				
				}
				else if (item.space.hasOwnProperty(selected_matrix_filter_uuid)){
				
					let item_matrix_filter_space = item.space[selected_matrix_filter_uuid];
					
					let compare_fn_name = "compare_" + selected_matrix_filter.type;

					
					let is_subset = self[compare_fn_name](selected_matrix_filter_space, item_matrix_filter_space);
					
					if (is_subset == false){
						item_is_visible = false;
						break;
					}
					
				}
				else {
					item_is_visible = false;
					break;
				}

			}

			// if the item is visible, add its property values to possible values
			if (item_is_visible == true){
				for (let matrix_filter_uuid in item.space){

					var matrix_filter_type = self.data.matrix_filters[matrix_filter_uuid]["type"];

					if (matrix_filter_type != "RangeFilter"){

						var space = item.space[matrix_filter_uuid];

						for (let s=0; s<space.length; s++){
							let value = space[s];
							
							if (matrix_filter_type == "ColorFilter"){
								value = JSON.stringify(value);
							}
							// {{ name }}_{{ choice.0 }}
							let property_value_id = '' + matrix_filter_uuid + '_' + value;

							if (self.possible_values.indexOf(property_value_id) == -1){
								self.possible_values.push(property_value_id);
							}
						}
					}
				}
			}

			item.is_visible = item_is_visible;

			self._update_item_visibility(item);

			if (item_is_visible == true){
				self.visible_count++;
			}

		}

		// all items have been traveled - adjust the displayed filters now
		// undisplay the impossible values and display the possible values
		// iterate over all inputs

		if (selected_filters_uuids.length === 0){
			self.reset();
		}
		else {
			
			for (let v=0; v<self.matrix_filter_values.length; v++){

				let matrix_filter_value = self.matrix_filter_values[v];
				let matrix_filter_type = self.data.matrix_filters[matrix_filter_value.uuid]["type"];
				
				let matrix_filter_value_id = matrix_filter_value.id;
				

				let selected_values = [];
				
				// uuid is uuid of matrix_filter, values do not have uuids
				if (selected_filters.hasOwnProperty(matrix_filter_value.uuid)){
					selected_values = selected_filters[matrix_filter_value.uuid];
				}
				
				if (self.possible_values.indexOf(matrix_filter_value_id) != -1) {
					matrix_filter_value.show();
				}
				else if (selected_values.indexOf(matrix_filter_value.value) >= 0) {
					matrix_filter_value.show();
				}
				else {
					if (matrix_filter_type == "ColorFilter") {
						let is_visible = false;
						// [].indexOf(element) is not supported if element is an Array or Object
						for (let v=0; v<selected_values.length; v++){
							let selected_value = selected_values[v];
							if (JSON.stringify(matrix_filter_value.value) == JSON.stringify(selected_value)){
								is_visible = true;
								break;
							}
						}
						
						if (is_visible == false) {
							matrix_filter_value.hide();
						}
						else {
							matrix_filter_value.show();
						}
					}
					else {
						matrix_filter_value.hide();
					}
				}
		
			}
			
			self.update_visible_count();

		}


		if (self.visible_count == 1 && hide_overlay_on_completion === true){
			event_identification_complete.result = {"identification_complete" : true};
			document.dispatchEvent(event_identification_complete);
		}

	},

	_update_item_visibility : function(item){
	
		var self = this;
	
		// only manipulate the DOM of visibility has changed
		var dom_element = document.getElementById(item.uuid);
		
		if (dom_element != null){
			
			if (item.is_visible == true && dom_element.parentElement.id != "keynodes"){
				self.keynodes_container.appendChild(dom_element);
			}
			else if (item.is_visible == false && dom_element.parentElement.id != "sorted-out-keynodes") {
				self.sorted_out_keynodes_container.appendChild(dom_element);
			}

		}
		
	},

	reset : function(){
		var self = this;

		self.current_filters = [];

		for (let i=0; i<self.data.items.length; i++){

			let item = self.data.items[i];
			item.is_visible = true;
		
			self._update_item_visibility(item);

		}
		
		for (let matrix_filter_uuid in self.data.matrix_filters){

			let matrix_filter = self.data.matrix_filters[matrix_filter_uuid];
			
			if (matrix_filter.hasOwnProperty("restrictions") && Object.keys(matrix_filter.restrictions).length ){
			
				let matrix_filter_element = document.getElementById(matrix_filter_uuid);
				matrix_filter_element.classList.add("restriction-active");
			
				/*let restriction_indicator = document.getElementById("" + matrix_filter_uuid + "_restriction_indicator");
				restriction_indicator.classList.remove("badge-success");
				restriction_indicator.classList.add("badge-danger");
				*/
			}

		}

		for (let v=0; v<self.matrix_filter_values.length; v++){
			let matrix_filter_value = self.matrix_filter_values[v];
			matrix_filter_value.show();
			matrix_filter_value.input.checked = false;
		}

		var ranges = self.filterform.querySelectorAll('input[type=range]');
		for (let r=0; r<ranges.length; r++){
			let range = ranges[r];

			range.value = '';
			range.clear()

		}

		self.visible_count = self.data.items.length;
		self.update_visible_count();

	},

	update_visible_count : function(){
		var self = this;
		var children_count = document.getElementsByClassName("children-count");
		for (var e=0; e<children_count.length; e++){
			children_count[e].textContent = self.visible_count;
		}
	}
};
