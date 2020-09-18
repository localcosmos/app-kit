"use strict";

/* 
* MatrixFilterValue
* - an input like radio, checkbox or slider represents one MatrixFilterValue
* - multiple inputs/radios with the same name(uuid) together form the MatrixFilter
*/
var MatrixFilterValue = {
	create : function(input){
		var self = Object.create(this);

		self.uuid = input.name;
		self.value = input.value;

		self.id = '' + self.uuid + '_' + self.value;

		self.container = document.getElementById('' + self.uuid + '_' + self.value + '_container');

		self.input = input;
		

		return self;
	},
	hide : function(){
		var self = this;
		self.input.parentElement.style.display = "none";
		return self;
	},
	show : function(){
		var self = this;
		self.input.parentElement.style.display = "";
		return self;
	}
};

/*
	Identification Matrix
	- reads filters from the filter form
	- multiple selections of values of properties are ANDed together
*/
var IdentificationMatrix = {
	create : function(filter_form_id, get_items, options){

		var self = Object.create(this);
		
		self.filterform = document.getElementById(filter_form_id);

		// fetch items
		self.update = function(){

			get_items(function(json){
				self.data = json;
			});
			
		};

		self.update();

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

		self._attach_filterupdate_listeners();

		self.visible_count = 0;

		return self;

	},

	/* this only collects radios, checkboxes and ranges */
	_read_form : function(){
		var self = this;

		var elements = self.filterform.elements;

		var selected_filters = {};

		for (var e=0; e<elements.length; e++) {
			var element = elements[e];

			if (element.type == "radio" || element.type == "checkbox"){

				if (element.checked){
					selected_filters[element.name] = [element.dataset.value];
				}
			}
			else if (element.type == "range"){
				var input = document.getElementById(element.id + "_value");

				if (input.value.length){
					selected_filters[input.name] = [element.value];
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

		for (var i=0; i<inputs.length; i++){
			var input = inputs[i];

			var matrix_filter_value = MatrixFilterValue.create(input);
			self.matrix_filter_values.push(matrix_filter_value);

			input.addEventListener('change', function(event){
				self.apply_filters();

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
				self.apply_filters();
			});

			range.addEventListener('clear', function(event){
				self.apply_filters();
			});


		}
	},

	compare_colors : function(color_a, color_b){

		for (var c=0; c<color_a.length; c++){
			if (color_b[c] != color_a[c]){
				return false;
			}
		}
		return true;
	},

	/* check if a lower taxon is a descendant of a higher taxon
	* {"taxa": [{"taxon_nuid": "001", "name_uuid": "f61b30e9-90d3-4e87-9641-eee71506aada", "taxon_source": "taxonomy.sources.col", "taxon_latname": "Animalia"}], "latname": "Animalia", "is_custom": false}
	*/
	compare_taxa : function(taxonfilter, taxon){

		var taxonfilter = JSON.parse(atob(taxonfilter));

		var taxa = taxonfilter["taxa"];
		for (var t=0; t<taxa.length; t++){
			var taxonfilter_taxon = taxonfilter["taxa"][t];

			if (taxonfilter_taxon["taxon_source"] == taxon["taxon_source"]){

				var is_descendant = taxon["taxon_nuid"].startsWith(taxonfilter_taxon["taxon_nuid"]);

				if (is_descendant == true){
					return true;
				}

			}
			else {
				continue;
			}

		}

		return false;		

	},

	/* create a space from the filterform and apply it to all current items */
	apply_filters : function(){
		var self = this;

		self.visible_count = 0;

		/* compare new_filters with old filters
		 * a: if new_filters is an extension of old_filters, work currently visible items
		 * b: if new_filters is a subset of old_filters, work currently invisible items
		 * c: else, work all items
		 */

		self.possible_values = [];

		// formdata is unsupported by IE
		var new_filters = self._read_form() //new FormData(self.filterform);

		var workspace = 'all'; // all, visible, invisible


		if (self.current_filters == null){
			self.current_filters = new_filters;
		}
		else {
			// compare filters and set workspace
		}

		var new_filters_uuids = Object.keys(new_filters);

		// iterate over all items
		for (var i=0; i<self.data.items.length; i++){
			var item = self.data.items[i];

			var item_is_visible = true;

			if ((item.is_visible == true && workspace == "invisible") || (item.is_visible == false && workspace == "visible")){
				continue;
			}

			// iterate over all filters and check if the items space is a subspace of new_filters
			for (var k=0; k<new_filters_uuids.length; k++){

				var matrix_filter_uuid = new_filters_uuids[k];
				var matrix_filter_type = self.data.matrix_filter_types[matrix_filter_uuid];


				// apply the taxon filter
				if (matrix_filter_type == "TaxonFilter"){

					item_is_visible = false;

					var taxonfilter = new_filters[matrix_filter_uuid];
					if (item.hasOwnProperty("taxon") && item["taxon"] != null){
						item_is_visible = self.compare_taxa(taxonfilter, item["taxon"]);
					}
				}

				else if (item.space.hasOwnProperty(matrix_filter_uuid)){
					
					var selected = new_filters[matrix_filter_uuid];
					
					if (matrix_filter_type == "RangeFilter"){
						var value = parseFloat(selected[0]);
						
						if (value){
							if (value < item.space[matrix_filter_uuid][0] || value > item.space[matrix_filter_uuid][1]){
								item_is_visible = false;
								break;
							}
						}
					}
					else {

						var item_space = item.space[matrix_filter_uuid];
						
						for (var v=0; v<selected.length; v++){
							
							var value = selected[v];


							if (matrix_filter_type == "ColorFilter"){
								value = value.split(',');

								if (item_is_visible == false){
									break;
								}

								var selected_rgb = [0, 0, 0, 0];
								for (var v=0; v<value.length; v++){
									var color_part = parseInt(value[v]);
									selected_rgb[v] = color_part;
								}

								// compare the 2 rgb values. the selected value is compare with all values of the item
								// as soon as one color matches, the item is visible

								item_is_visible = false;

								for (var r=0; r<item_space.length; r++){
									var item_rgb = item_space[r];

									var equals = self.compare_colors(item_rgb, selected_rgb);
									if (equals == true){
										item_is_visible = true;
										break;
									}
								}
								
							}

							else {

								if (matrix_filter_type == "NumberFilter"){
									value = parseFloat(value);
								}
							
								if (item_space.indexOf(value) == -1){
									item_is_visible = false;
									break;
								}
							}
						}
					}

					// quit checking if item has already been sorted out
					if (item_is_visible == false){
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
				for (var key in item.space){

					var matrix_filter_type = self.data.matrix_filter_types[key];

					if (matrix_filter_type != "RangeFilter"){

						var space = item.space[key];

						for (var s=0; s<space.length; s++){
							var value = space[s];
							// {{ name }}_{{ choice.0 }}
							var property_value_id = '' + key + '_' + value;
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

		if (new_filters_uuids.length === 0){
			self.reset();
		}
		else {
			/* currently, matrix filters are not hidden
			for (var v=0; v<self.matrix_filter_values.length; v++){

				var matrix_filter_value = self.matrix_filter_values[v];

				var selected = [];
				
				if (new_filters.hasOwnProperty(matrix_filter_value.uuid)){
					selected = new_filters[matrix_filter_value.uuid];
				}
	
				if (self.possible_values.indexOf(matrix_filter_value.id) != -1 || selected.indexOf(matrix_filter_value.value) >= 0){
					matrix_filter_value.show();
				}
				else {
					matrix_filter_value.hide();
				}
		
			}
			*/
			self.update_visible_count();

		}

	},

	_update_item_visibility : function(item){
		// only manipulate the DOM of visibility has changed
		var dom_element = document.getElementById(item.uuid);

		var dom_element_is_visible = dom_element.style.display == 'none' ? false : true;

		if (dom_element_is_visible != item.is_visible){

			var style = item.is_visible == true ? '' : 'none';
			dom_element.style.display = style;
		}
	},

	reset : function(){
		var self = this;

		self.current_filters = [];

		for (var i=0; i<self.data.items.length; i++){

			var item = self.data.items[i];
			item.is_visible = true;
		
			self._update_item_visibility(item);
		}

		for (var v=0; v<self.matrix_filter_values.length; v++){
			var matrix_filter_value = self.matrix_filter_values[v];
			matrix_filter_value.show();
			matrix_filter_value.input.checked = false;
		}

		var ranges = self.filterform.querySelectorAll('input[type=range]');
		for (var r=0; r<ranges.length; r++){
			var range = ranges[r];

			range.value = '';
			range.clear()

		}

		self.visible_count = self.data.items.length;
		self.update_visible_count();

	},

	update_visible_count : function(){
		var self = this;
		document.getElementById("children-count").textContent = self.visible_count;
	}
};
