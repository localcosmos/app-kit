"use strict";
/*
{
  "items": [
    {
      "id": 7,
      "name": "Laubbäume",
      "uuid": "eb3eba32-1d46-4a6a-87bf-328672e2626c",
      "space": {
        "2ff6f540-1676-410e-8067-1b58c3a002ed": [
          [
            4,
            5
          ]
        ],
        "3e9f0c09-a118-4d2c-9cf7-ea52fb1b80ce": [
          1,
          3
        ],
        "43b549b3-911d-4df3-8c9c-9986ed02be45": [
          [
            241,
            45,
            45,
            1
          ],
          [
            [
              76,
              26,
              26,
              1
            ],
            [
              146,
              146,
              146,
              1
            ]
          ]
        ]
      },
      "taxon": null,
      "image_url": "/media/treesofbavaria/imagestore/1/thumbnails/73c0d5e7970ab4ed9b855dc0a4535dc5_2E9oVUY-e40c54f70e9a62da34083d82850ac09b-400.jpg",
      "node_type": "node",
      "is_visible": true,
      "max_points": 150,
      "meta_node_id": 7,
      "decision_rule": "mit Blättern, im Winter kahl"
    },
    {
      "id": 157,
      "name": "Nadelbaueme Kopie QV",
      "uuid": "8727707d-aebc-4366-a46d-b7e25f1ae88e",
      "space": {},
      "taxon": null,
      "image_url": "/media/treesofbavaria/imagestore/1/thumbnails/1659ca81b47f6be0b1b1ca8477c5f454_PkstfHA-e40c54f70e9a62da34083d82850ac09b-400.jpg",
      "node_type": "node",
      "is_visible": true,
      "max_points": 0,
      "meta_node_id": 157,
      "decision_rule": ""
    },
    {
      "id": 8,
      "name": "Nadelbäume",
      "uuid": "6fcd3ac4-2e64-4ba4-858b-0acae18fbcfb",
      "space": {
        "0c9f1e62-521e-4c09-b98e-156c3d72a9bc": [
          "<p>Text mit &gt;</p>"
        ],
        "2ff6f540-1676-410e-8067-1b58c3a002ed": [
          [
            1,
            5
          ]
        ],
        "3e9f0c09-a118-4d2c-9cf7-ea52fb1b80ce": [
          3
        ],
        "43b549b3-911d-4df3-8c9c-9986ed02be45": [
          [
            241,
            45,
            45,
            1
          ]
        ]
      },
      "taxon": null,
      "image_url": "/media/treesofbavaria/imagestore/1/thumbnails/1659ca81b47f6be0b1b1ca8477c5f454_PkstfHA-e40c54f70e9a62da34083d82850ac09b-400.jpg",
      "node_type": "node",
      "is_visible": true,
      "max_points": 200,
      "meta_node_id": 8,
      "decision_rule": "mit Nadeln"
    },
    {
      "id": 59,
      "name": "Unready",
      "uuid": "960d0c2c-2c30-48a0-8ddb-7e542ee1a152",
      "space": {},
      "taxon": null,
      "image_url": "/static/noimage.png",
      "node_type": "node",
      "is_visible": true,
      "max_points": 0,
      "meta_node_id": 59,
      "decision_rule": ""
    },
    {
      "id": 162,
      "name": "Eintrag mit Synonym",
      "uuid": "4342a9b7-5883-47f2-a22b-bd0ea0af2553",
      "space": {},
      "taxon": {
        "name_uuid": "8dfdae06-8626-46ac-8611-86926973ae72",
        "taxon_nuid": "00600800800b003002009001",
        "taxon_author": "(Bak.) Reed",
        "taxon_source": "taxonomy.sources.col",
        "taxon_latname": "Schizaea malaccana robustior"
      },
      "image_url": "/static/noimage.png",
      "node_type": "result",
      "is_visible": true,
      "max_points": 0,
      "meta_node_id": 162,
      "decision_rule": ""
    }
  ],
  "matrix_filters": {
    "0c9f1e62-521e-4c09-b98e-156c3d72a9bc": {
      "type": "TextOnlyFilter"
    },
    "27c566f8-802a-47fd-8938-2e469aef22b0": {
      "type": "DescriptiveTextAndImagesFilter",
      "restrictions": {
        "2ff6f540-1676-410e-8067-1b58c3a002ed": [
          [
            2,
            4
          ]
        ]
      }
    },
    "2ff6f540-1676-410e-8067-1b58c3a002ed": {
      "type": "RangeFilter",
      "restrictions": {
        "3e9f0c09-a118-4d2c-9cf7-ea52fb1b80ce": [
          2
        ]
      }
    },
    "3e9f0c09-a118-4d2c-9cf7-ea52fb1b80ce": {
      "type": "NumberFilter",
      "restrictions": {
        "43b549b3-911d-4df3-8c9c-9986ed02be45": [
          [
            241,
            45,
            45,
            1
          ]
        ]
      }
    },
    "43b549b3-911d-4df3-8c9c-9986ed02be45": {
      "type": "ColorFilter"
    }
  }
}
*/

var MATRIX_FILTERS = {};

var MATRIX_ITEMS = {};

const MODE_STRICT = "strict"; // sort items out immediately
const MODE_FLUID = "fluid"; // do not sort out, sort by points in descending order

var IDENTIFICATION_MODE = MODE_FLUID;

/*
* IMPORTANT: space_identifier is not globally unique, but unique for its matrix_filter
*/
class MatrixFilter {

	constructor (form_element, uuid, matrix_filter_type) {

		this.DEBUG = true;

		// for firing events
		this.form_element = form_element;

		this.uuid = uuid;
		this.matrix_filter_type = matrix_filter_type;
		// {"matrix_ilter_uuid" : { "space_identifier" : false } }
		// if all space_identifiers are set to true, show the filter
		this.restricted_by = {};
		// other matrix filters which are called from this matrix filters because their visibilty depends on it
		//{space_identifier:MATRIX_FILTER_UUID[]}
		this.restricts = {};
		this.is_visible = true;

		// values selected by the user (using an html form)
		// {identifier:parsed_value}
		this.active_matrix_filter_spaces = {};

		this.weight = 50;

		// map space_identifiers to matrix_items
		// {"space_identifier" : [matrix_item_uuid, matrix_item_uuid]}
		this.matrix_item_registry = {};

		// for strict mode only
		// {space_identifier: [matrix_item_uuid, matrix_item_uuid]}
		// if a space has no active items, it will be disabled in strict mode
		this.active_matrix_items = {};
		
	}

	get_value_from_input_element (input_element) {
		return input_element.value;
	}

	apply_restrictions (restrictions) {

		for (let restrictive_matrix_filter_uuid in restrictions){

			let restrictive_matrix_filter = MATRIX_FILTERS[restrictive_matrix_filter_uuid]

			let restriction_spaces = restrictions[restrictive_matrix_filter_uuid];
			
			this.restricted_by[restrictive_matrix_filter_uuid] = {};
			
			for (let v=0; v<restriction_spaces.length; v++){
				let parsed_restriction_space = restriction_spaces[v];

				let space_identifier = restrictive_matrix_filter.get_matrix_filter_space_identifier_from_parsed(parsed_restriction_space);

				this.restricted_by[restrictive_matrix_filter_uuid][space_identifier] = false;
				restrictive_matrix_filter.restrict(this, space_identifier);
			}
		}

		if (Object.keys(this.restricted_by).length > 0){
			this.hide();
		}
	}

	restrict (restricted_matrix_filter, space_identifier) {
		if (!this.restricts.hasOwnProperty(space_identifier)){
			this.restricts[space_identifier] = [];
		}
		this.restricts[space_identifier].push(restricted_matrix_filter.uuid);
	}

	// register a matrix_item, so it can be signalled later when a space gets (de-)activated
	register_matrix_item (matrix_item, space_identifier) {
		if (!this.matrix_item_registry.hasOwnProperty(space_identifier)){
			this.matrix_item_registry[space_identifier] = [];
		}

		this.matrix_item_registry[space_identifier].push(matrix_item.uuid);
	}

	is_active () {
		return Object.keys(this.active_matrix_filter_spaces).length != 0;
	}

	// return b64 encoded space_identifier
	get_matrix_filter_space_identifier_from_parsed (parsed_space) {
		throw new Error("[MatrixFilter] subclasses require a get_matrix_filter_space_identifier_from_parsed method");
	}

	// return b64 encoded space_identifier
	get_matrix_filter_space_identifier_from_str (space_str){
		throw new Error("[MatrixFilter] subclasses require a get_matrix_filter_space_identifier_from_str method");
	}

	parse_matrix_filter_space_str (space_str) {
		throw new Error("[MatrixFilter] subclasses require a parse_matrix_filter_space_str method");
	}

	get_matrix_filter_space_from_space_identifier (b64_space_identifier){
		throw new Error("[MatrixFilter] subclasses require a get_matrix_filter_space_from_space_identifier method");
	}

	get_space_str_from_space_identifier (b64_space_identifier){
		throw new Error("[MatrixFilter] subclasses require a get_space_str_from_space_identifier method");
	}

	reset () {

		if (this.DEBUG == true){
			console.log("[MatrixFilter] " + this.matrix_filter_type + " is resetting");
		}

		var inputs = document.body.querySelectorAll("input[name='" + this.uuid + "']");

		for (let i=0; i<inputs.length;i++){
			let input = inputs[i];
			input.checked = false;
			input.removeAttribute("checked");
		}
		this.active_matrix_filter_spaces = {};

		this.update();

		if (IDENTIFICATION_MODE == MODE_STRICT){
			this.remove_all_mismatches_from_matrix_items();
		}
	}



	// validate a given space against the current selection
	validate_selected_space_against_item (selected_space_identifier, matrix_item) {

		if (this.DEBUG == true){
			console.log("[MatrixFilter] validating " + matrix_item.name);
		}

		// this.matrix_filter_spaces[matrix_filter.uuid][space_identifier] = space;
		let selected_space_is_valid_for_this_item = false;

		if (matrix_item.matrix_filter_spaces.hasOwnProperty(this.uuid)){

			let item_spaces = matrix_item.matrix_filter_spaces[this.uuid];
			let selected_space = this.active_matrix_filter_spaces[selected_space_identifier];

			if (this.DEBUG == true){
				console.log("selected space (user selection):");
				console.log(selected_space);
				console.log("superset (item space):");
				console.log(item_spaces);
			}
			
			for (let item_space_identifier in item_spaces){

				if (this.DEBUG == true){
					console.log("[MatrixFilter] comparing: " + selected_space_identifier + " with: " + item_space_identifier);
				}

				if (selected_space_identifier == item_space_identifier) {
					selected_space_is_valid_for_this_item = true;
					break;
				}
			}
		
		}

		return selected_space_is_valid_for_this_item;
	}


	// send events if an input has been turned on or off
	// signal matrix_filters which are restricted by this filter
	// if user changes his selection using a radio button, this effects other radio buttons because they automatically become unselected
	// this should hide matrix_filters dependant on the automatically unselected value
	// update iterates over all inputElements and therefore over all spaces 
	update () {

		console.log(this)

		var inputs = document.body.querySelectorAll("input[name='" + this.uuid + "']");

		for (let r=0; r<inputs.length; r++){
			let input = inputs[r];

			let space_str = this.get_value_from_input_element(input);

			let space_identifier = this.get_matrix_filter_space_identifier_from_str(space_str);

			// use the attribute, not .checked

			if (input.checked == true) {

				this.activate_space(input, space_identifier);

			}
			else {

				this.deactivate_space(input, space_identifier);
			}
			
		}

	}

	// activate a space of this filter
	activate_space (input, space_identifier){
		let space = this.get_matrix_filter_space_from_space_identifier(space_identifier); //this.parse_matrix_filter_space_str(space_str);

		this.active_matrix_filter_spaces[space_identifier] = space;

		const turned_on_event = new Event("turnedOn");
		input.dispatchEvent(turned_on_event)

		this.signal_restricted_matrix_filters(space_identifier, true);

		this.signal_matrix_items(space_identifier, true);

		if (this.DEBUG == true){
			console.log("[MatrixFilter] " + this.matrix_filter_type + " " + this.uuid + " space_identifier: " + space_identifier + " is now ON");
		}
	}

	// always remove mismatches if a space gets deactivated
	deactivate_space(input, space_identifier){
		delete this.active_matrix_filter_spaces[space_identifier];

		const turned_off_event = new Event("turnedOff");
		input.dispatchEvent(turned_off_event);

		this.signal_restricted_matrix_filters(space_identifier, false);

		this.signal_matrix_items(space_identifier, false);

		if (this.DEBUG == true){
			console.log("[MatrixFilter] " + this.matrix_filter_type + " " + this.uuid + " space_identifier: " + space_identifier + " is now OFF");
		}

		if (IDENTIFICATION_MODE == MODE_STRICT){
			this.remove_space_mismatch_from_all_items(space_identifier);
		}
	}

	// signal all matrix_filters which are restricted by this space_identifier of this matrix_filter
	signal_restricted_matrix_filters(space_identifier, is_turned_on){

		if (this.DEBUG == true){
			console.log("[MatrixFilter] " + this.matrix_filter_type + " signaling filters restricted by this filter");
		}

		if (this.restricts.hasOwnProperty(space_identifier)){

			let restricted_matrix_filters = this.restricts[space_identifier];

			for (let m=0; m<restricted_matrix_filters.length; m++){

				let restricted_matrix_filter_uuid = restricted_matrix_filters[m];

				let restricted_matrix_filter = MATRIX_FILTERS[restricted_matrix_filter_uuid];

				if (this.DEBUG == true){
					console.log("[MatrixFilter] " + this.matrix_filter_type + " " + this.uuid + " is signaling " + restricted_matrix_filter.uuid);
				}

				restricted_matrix_filter.receive_restriction(this.uuid, space_identifier, is_turned_on);
			}
		}
	}

	receive_restriction (matrix_filter_uuid, space_identifier, is_turned_on) {

		if (this.DEBUG == true){
			console.log("[MatrixFilter] " + this.matrix_filter_type + " " + this.uuid + " received restriction update, " + space_identifier + " , is_turned_on : " + is_turned_on);
		}

		if (this.restricted_by.hasOwnProperty(matrix_filter_uuid)){
			let restriction = this.restricted_by[matrix_filter_uuid];

			if (restriction.hasOwnProperty(space_identifier)){
				this.restricted_by[matrix_filter_uuid][space_identifier] = is_turned_on;
			}
		}

		this.check_restrictions();
	}

	// if the visibilty is false, turn off all selected spaces, then call .update()
	check_restrictions () {

		let is_visible = true;

		if (this.DEBUG == true){
			console.log(this.restricted_by);
		}

		for (let matrix_filter_uuid in this.restricted_by){

			let restriction = this.restricted_by[matrix_filter_uuid];

			for (let space_identifier in restriction){
				is_visible = restriction[space_identifier];
				if (is_visible == false){
					break;
				}
			}

			if (is_visible == false){
				break;
			}
		}

		if (this.DEBUG == true){
			console.log("[MatrixFilter] " + this.matrix_filter_type + " " + this.uuid + " worked restrictions, visibilty:" + is_visible);
		}

		if (is_visible == true){
			this.show();
		}
		else {
			this.reset();
			this.hide();
		}
	}

	get_event_data () {
		
		const event_data = {
			detail: {
				"matrix_filter" : {
					"uuid" : this.uuid,
					"matrix_filter_type" : this.matrix_filter_type,
					"is_visible" : this.is_visible
				} 
			}
		};

		return event_data;
	}

	// hide or show the matrix_filter as a whole if its visibilty depends on a filter selection
	// use EVENTS, no dom manipulation here
	show () {

		const event_data = this.get_event_data();

		const show_event = new CustomEvent("show-matrix-filter", event_data);

		this.form_element.dispatchEvent(show_event);

	}

	hide () {

		const event_data = this.get_event_data();

		const hide_event = new CustomEvent("hide-matrix-filter", event_data);

		this.form_element.dispatchEvent(hide_event);
		
	}

	// notify items
	// MODE_FLUID: signal all registered matrix items that a match has been selected
	signal_matrix_items (space_identifier, is_turned_on) {
		if (this.DEBUG == true){
			console.log("[MatrixFilter] " + this.matrix_filter_type + " signaling matrix_items");
		}

		// iterate over MATCHING matrix_items
		if (this.matrix_item_registry.hasOwnProperty(space_identifier)){

			let matrix_item_uuids = this.matrix_item_registry[space_identifier];

			for (let m=0; m<matrix_item_uuids.length; m++){

				let matrix_item_uuid = matrix_item_uuids[m];
				let matrix_item = MATRIX_ITEMS[matrix_item_uuid];

				if (is_turned_on == true){
					matrix_item.activate_space(this, space_identifier);
				}
				else {
					matrix_item.deactivate_space(this, space_identifier);
				}
			}
		}
	}

	// STRICT MODE
	// events have to be fired on 2 occasions:
	// 1: the list this.active_matrix_items[space_identifier] = [] becomes empty
	// 2: the list was empty and one element has been added
	// in contrast to .update(), this only effects on inputElement/space
	update_matrix_item_mismatches (event) {

		if (this.DEBUG == true) {
			console.log("[MatrixFilter] updating matrix item mismatches");
		}

		let input = event.currentTarget;
		let space_str = this.get_value_from_input_element(input);
		let space_identifier = this.get_matrix_filter_space_identifier_from_str(space_str);

		let is_selected = input.checked;

		// activate or deactivate a matrix item based on the selected value
		let mismatching_matrix_item_uuids = Object.keys(MATRIX_ITEMS);

		// removed matched matrix_items from mismatching_matrix_item_uuids, which currently contains all matrix_items
		// if the space has been deselected, remove the mismatch from all
		if (is_selected == true && this.matrix_item_registry.hasOwnProperty(space_identifier)){

			let matrix_item_uuids = this.matrix_item_registry[space_identifier];
			for (let m=0; m<matrix_item_uuids.length; m++){

				let matched_matrix_item_uuid = matrix_item_uuids[m];
				let mismatch_index = mismatching_matrix_item_uuids.indexOf(matched_matrix_item_uuid);

				if (mismatch_index >=0){
					mismatching_matrix_item_uuids.splice(mismatch_index, 1);
				}
			}
		}

		if (this.DEBUG == true) {
			console.log("[MatrixFilter] mismatching matrix items:");
			console.log(mismatching_matrix_item_uuids);
		}
		
		// iterate over mismatches and signel them
		// add or remove from item.mismatching_spaces
		// matrix_item then checks if it became visible or invisible
		// if it became visible, it calls matrix_filter.add_to_active_matrix_items on all filters which it has spaces for
		// e.g. matrix_filter.active_matrix_items[space_red][matrix_item_uuid_1] becomes matrix_filter.active_matrix_items[space_red][matrix_item_uuid_1, matrix_item_uuid_2]
		//
		// if it became invisible, it calls matrix_filter.remove_from_active_matrix_items
		// e.g. matrix_filter.active_matrix_items[space_red][matrix_item_uuid_1, matrix_item_uuid_2] becomes matrix_filter.active_matrix_items[space_red][matrix_item_uuid_1]
		for (let u=0; u<mismatching_matrix_item_uuids.length; u++){
			let matrix_item_uuid = mismatching_matrix_item_uuids[u];
			let matrix_item = MATRIX_ITEMS[matrix_item_uuid];

			if (is_selected == true){
				matrix_item.add_mismatch(this, space_identifier);
			}
			else {
				matrix_item.remove_mismatch(this, space_identifier);
			}
		}
	}

	get_space_event_data (space_identifier){
		let space = this.get_matrix_filter_space_from_space_identifier(space_identifier);
		let space_str = this.get_space_str_from_space_identifier(space_identifier);

		const event_data = {
			detail : {
				"matrix_filter" : {
					"uuid" : this.uuid,
					"matrix_filter_type" : this.matrix_filter_type,
					"space_identifier" : space_identifier,
					"space" : space,
					"space_str" : space_str
				}
			}
		};

		return event_data;
	}

	add_to_active_matrix_items (matrix_item, space_identifier, setup){

		// on inital setup of IdentificationMatrix, do not send events
		setup = setup || false;

		let initially_active = true;

		if (!this.active_matrix_items.hasOwnProperty(space_identifier)){
			this.active_matrix_items[space_identifier] = [];
		}

		if (this.active_matrix_items[space_identifier].length == 0){
			initially_active = false;
		}

		if (this.active_matrix_items[space_identifier].indexOf(matrix_item.uuid) == -1){

			this.active_matrix_items[space_identifier].push(matrix_item.uuid);

			if (initially_active == false && setup == false){
				this.send_space_is_possible_event(space_identifier);
			}
		}
	}

	send_space_is_possible_event (space_identifier) {
		// send activation event
				
		const event_data = this.get_space_event_data(space_identifier);

		const activation_event = new CustomEvent("matrix-filter-space-is-possible", event_data);

		this.form_element.dispatchEvent(activation_event);
	}

	remove_from_active_matrix_items (matrix_item, space_identifier){
		let initially_inactive = true;
		let is_now_inactive = false;

		if (this.active_matrix_items.hasOwnProperty(space_identifier)){

			if (this.active_matrix_items[space_identifier].length > 0){
				initially_inactive = false;
			}

			let matrix_item_index = this.active_matrix_items[space_identifier].indexOf(matrix_item.uuid);

			if (matrix_item_index >=0) {

				this.active_matrix_items[space_identifier].splice(matrix_item_index, 1);

				if (this.active_matrix_items[space_identifier].length == 0){
					is_now_inactive = true;
				}
			}
		}

		if (this.DEBUG == true){
			console.log("[MatrixFilter] " + this.matrix_filter_type + ".active_matrix_items[" + space_identifier + "] is now:");
			console.log(this.active_matrix_items[space_identifier]);
		}

		if (initially_inactive == false && is_now_inactive == true){
			// send deactivation event
			this.send_space_is_impossible_event(space_identifier);
		}
		
	}

	send_space_is_impossible_event (space_identifier) {
		const event_data = this.get_space_event_data(space_identifier);

		const deactivation_event = new CustomEvent("matrix-filter-space-is-impossible", event_data);

		this.form_element.dispatchEvent(deactivation_event);
	}

	// remove all mismatches for a specific space from all items
	remove_space_mismatch_from_all_items (space_identifier){
		for (let matrix_item_uuid in MATRIX_ITEMS){
			let matrix_item = MATRIX_ITEMS[matrix_item_uuid];
			if (matrix_item.mismatching_spaces.hasOwnProperty(this.uuid)){
				let mismatching_spaces = matrix_item.mismatching_spaces[this.uuid];
				if (mismatching_spaces.hasOwnProperty(space_identifier)){
					matrix_item.remove_mismatch(this, space_identifier);
				}
			}
		}
	}
	// remove all mismatches on MatrixFilter.reset()
	// mismatches are stored in MatrixItem.mismatching_spaces[matrix_filter.uuid][space_identifier] = matrix_filter.weight;
	remove_all_mismatches_from_matrix_items () {

		if (this.DEBUG == true){
			console.log("[MatrixFilter] " + this.matrix_filter_type + " remove all mismatches");
		}

		for (let matrix_item_uuid in MATRIX_ITEMS){
			let matrix_item = MATRIX_ITEMS[matrix_item_uuid];
			if (matrix_item.mismatching_spaces.hasOwnProperty(this.uuid)){
				let mismatching_spaces = matrix_item.mismatching_spaces[this.uuid];

				for (let space_identifier in mismatching_spaces){
					matrix_item.remove_mismatch(this, space_identifier);
				}
			}
		}
	}

}

// sometimes uses JSON.parse / JSON.stringify
class ObjectBasedMatrixFilter extends MatrixFilter {

	get_matrix_filter_space_identifier_from_parsed (parsed_space) {
		if (this.DEBUG == true){
			console.log("[MatrixFilter] " + this.matrix_filter_type + "] stringifying parsed space: " + parsed_space);
		}
		
		let b64 = btoa(JSON.stringify(parsed_space));

		if (this.DEBUG == true){
			console.log(b64);
		}

		return b64;
	}

	// str, not b64encoded
	get_matrix_filter_space_identifier_from_str (space_str){
		// first parse to ensure the identifier is equal to from_parsed
		if (this.DEBUG ==true){
			console.log("[ObjectBasedMatrixFilter] trying to parse: " + space_str);
		}
		return btoa(JSON.stringify(JSON.parse(space_str)));
	}

	parse_matrix_filter_space_str (space_str) {
		return JSON.parse(space_str);
	}

	get_matrix_filter_space_from_space_identifier (b64_space_identifier){
		return JSON.parse(atob(b64_space_identifier));
	}

	get_space_str_from_space_identifier (b64_space_identifier) {
		return atob(b64_space_identifier);
	}

}

// does not use JSON.parse or JSON.stringify
class StringBasedMatrixFilter extends MatrixFilter {

	get_matrix_filter_space_identifier_from_parsed (parsed_space) {
		if (this.DEBUG == true){
			console.log("[MatrixFilter - " + this.constructor.name + "] stringifying parsed space: " + parsed_space);
		}
		
		let b64 = btoa(parsed_space);

		if (this.DEBUG == true){
			console.log(b64);
		}

		return b64;
	}

	get_matrix_filter_space_identifier_from_str (space_str){
		return btoa(space_str);
	}

	parse_matrix_filter_space_str (space_str) {
		return space_str;
	}

	get_matrix_filter_space_from_space_identifier (b64_space_identifier){
		return atob(b64_space_identifier);
	}

	get_space_str_from_space_identifier (b64_space_identifier) {
		return atob(b64_space_identifier);
	}

}

class ColorFilter extends ObjectBasedMatrixFilter {

}


class NumberFilter extends ObjectBasedMatrixFilter {

}

/*
*	the space_identifier is unique only together with the matrix_filter_uuid
* RangeFilter differs from other filters, because validity checks need to check if a numbert is within a range. We cannot just compare space_identifiers
* another difference is, that there is always only one value present in the DOM
*/
class RangeFilter extends ObjectBasedMatrixFilter {

	get_value_from_input_element (input_element) {

		let is_null = input_element.getAttribute("is-null", "true");

		if (is_null == "true" || is_null == true){
			return "";
		}
		else {
			return input_element.value;
		}
	}

	get_range_input () {
		let range_inputs= document.body.querySelectorAll("input[type='range'][name='" + this.uuid + "']");
		
		if (range_inputs.length == 1){
			let range_input = range_inputs[0];
			return range_input;
		}
		else {
			throw new Error("[RangeFilter] no range input found for " + this.uuid);
		}
	}

	reset () {

		let range_input = this.get_range_input();
		range_input.value = "";
		range_input.setAttribute("is-null", "true");

		this.update();
	}

	// update currently has no effect on mismatches
	update () {

		console.log(this)

		let range_input = this.get_range_input();
		let space_identifier = null;
		let previous_space_identifier = null;

		if (Object.keys(this.active_matrix_filter_spaces).length > 0){
			previous_space_identifier = Object.keys(this.active_matrix_filter_spaces)[0];
			//previous_space = this.active_matrix_filter_spaces[previous_space_identifier];
		}

		// hold only one value - we have to be able to access the previous value
		this.active_matrix_filter_spaces = {};

		let value = this.get_value_from_input_element(range_input);

		if (value.length > 0) {
			let space_str = value;
			space_identifier = this.get_matrix_filter_space_identifier_from_str(space_str);
		}

		if (this.DEBUG == true){
			console.log("[RangeInput] value: " + value);
		}

		// the previous value always has to be eradicated
		if (previous_space_identifier != null) {
			this.signal_restricted_matrix_filters(previous_space_identifier, false);

			this.signal_matrix_items(previous_space_identifier, false);

			if (this.DEBUG == true){
				console.log("[MatrixFilter] " + this.uuid + " space_identifier: " + previous_space_identifier + " is now OFF");
			}

			if (IDENTIFICATION_MODE == MODE_STRICT && value.length > 0){
				this.remove_space_mismatch_from_all_items(space_identifier);
			}
		}

		// add a new value if possible
		if (value.length > 0) {
			this.activate_space(range_input, space_identifier);
		}
		else {
			this.deactivate_space(range_input, space_identifier);
		}
	}

	activate_space (input, space_identifier){

		let space = this.get_matrix_filter_space_from_space_identifier(space_identifier);
		this.active_matrix_filter_spaces[space_identifier] = space;

		const turned_on_event = new Event("turnedOn");
		input.dispatchEvent(turned_on_event)

		this.signal_restricted_matrix_filters(space_identifier, true);
		this.signal_matrix_items(space_identifier, true);

		if (this.DEBUG == true){
			console.log("[MatrixFilter] " + this.uuid + " space_identifier: " + space_identifier + " is now ON");
		}
	}

	deactivate_space (input, space_identifier) {
		const turned_off_event = new Event("turnedOff");
		input.dispatchEvent(turned_off_event);

		//this.signal_restricted_matrix_filters(space_identifier, false);
		//this.signal_matrix_items(space_identifier, false);

	}

	// the space_identifier which is registered in matrix_item_registry is a range
	// the space_identifier passed to this function is a number
	// a check has t obe made if the passed space_identifier (number) is within the space_identifier(range) of matrix_item_registry
	signal_matrix_items (space_identifier, is_turned_on) {

		if (this.DEBUG == true){
			console.log("[RangeFilter] signaling matrix_items with identifier: " + space_identifier);
		}

		let selected_number = this.get_matrix_filter_space_from_space_identifier(space_identifier);

		for (let item_space_identifier in this.matrix_item_registry){

			let item_space = this.get_matrix_filter_space_from_space_identifier(item_space_identifier);

			if (this.DEBUG == true){
				console.log("[RangeFilter] matrix items, comparing number to range");
				console.log(selected_number);
				console.log(item_space);
			}

			if (selected_number >= item_space[0] && selected_number <= item_space[1]){			

				let matrix_item_uuids = this.matrix_item_registry[item_space_identifier];
				for (let m=0; m<matrix_item_uuids.length; m++){

					let matrix_item_uuid = matrix_item_uuids[m];
					let matrix_item = MATRIX_ITEMS[matrix_item_uuid];

					if (is_turned_on == true){
						matrix_item.activate_space(this, item_space_identifier);
					}
					else {
						matrix_item.deactivate_space(this, item_space_identifier);
					}
				}
			}

		}

	}

	// signal all matrix_filters which are restricted by this space_identifier of this matrix_filter
	signal_restricted_matrix_filters(space_identifier, is_turned_on){

		if (this.DEBUG == true){
			console.log("[MatrixFilter] signaling filters restricted by this RANGE filter");
		}

		let selected_number = this.get_matrix_filter_space_from_space_identifier(space_identifier);

		for (let restricted_filter_space_identifier in this.restricts){

			let restriction_space = this.get_matrix_filter_space_from_space_identifier(restricted_filter_space_identifier);

			if (this.DEBUG == true){
				console.log("[RangeFilter] restrictions, comparing number to range");
				console.log(selected_number);
				console.log(restriction_space);
			}

			if (selected_number >= restriction_space[0] && selected_number <= restriction_space[1]){

				let matrix_filter_uuids = this.restricts[restricted_filter_space_identifier];

				for (let f=0; f<matrix_filter_uuids.length; f++){

					let matrix_filter_uuid = matrix_filter_uuids[f];

					let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];

					matrix_filter.receive_restriction(this.uuid, restricted_filter_space_identifier, is_turned_on);

				}
			}
		}
	}

	// STRICT MODE
	// events have to be fired on 2 occasions:
	// 1: the list this.active_matrix_items[space_identifier] = [] becomes empty
	// 2: the list was empty and one element has been added
	// Range: check if selected number is within the range if an item
	update_matrix_item_mismatches (event) {

		if (this.DEBUG == true) {
			console.log("[MatrixFilter] updating matrix item mismatches");
		}

		let input = event.currentTarget;

		let selected_number_str = this.get_value_from_input_element(input);
		let selected_number = null;
		if (selected_number_str.length > 0){
			selected_number = this.parse_matrix_filter_space_str(selected_number_str);
		}

		// activate or deactivate a matrix item based on the selected value
		let mismatching_matrix_item_uuids = Object.keys(MATRIX_ITEMS);
		let mismatching_matrix_item_space_identifiers = {};

		// removed matched matrix_items from mismatching_matrix_item_uuids, which currently contains all matrix_items
		if (selected_number != null){

			// space_identifier is the range of the matrix item
			for (let item_space_identifier in this.matrix_item_registry){

				let matrix_item_uuids = this.matrix_item_registry[item_space_identifier];
				let range = this.get_matrix_filter_space_from_space_identifier(item_space_identifier);

				for (let m=0; m<matrix_item_uuids.length; m++){
					let matrix_item_uuid = matrix_item_uuids[m];

					if (selected_number >= range[0] && selected_number <= range[1]){
						let mismatch_index = mismatching_matrix_item_uuids.indexOf(matrix_item_uuid);

						if (mismatch_index >=0){
							mismatching_matrix_item_uuids.splice(mismatch_index, 1);
						}
					}
					else {
						mismatching_matrix_item_space_identifiers[matrix_item_uuid] = item_space_identifier;
					}
				}
				
			}
	
		}

		if (this.DEBUG == true) {
			console.log("[MatrixFilter] " + this.matrix_filter_type + " mismatching matrix items:");
			console.log(mismatching_matrix_item_uuids);
		}
		
		// iterate over mismatches and signel them
		// add or remove from item.mismatching_spaces
		// matrix_item then checks if it became visible or invisible
		// if it became visible, it calls matrix_filter.add_to_active_matrix_items on all filters which it has spaces for
		// e.g. matrix_filter.active_matrix_items[space_red][matrix_item_uuid_1] becomes matrix_filter.active_matrix_items[space_red][matrix_item_uuid_1, matrix_item_uuid_2]
		//
		// if it became invisible, it calls matrix_filter.remove_from_active_matrix_items
		// e.g. matrix_filter.active_matrix_items[space_red][matrix_item_uuid_1, matrix_item_uuid_2] becomes matrix_filter.active_matrix_items[space_red][matrix_item_uuid_1]
		for (let u=0; u<mismatching_matrix_item_uuids.length; u++){
			let matrix_item_uuid = mismatching_matrix_item_uuids[u];
			let matrix_item = MATRIX_ITEMS[matrix_item_uuid];

			// get item_space for this matrix filter
			// if a matrix_item has no space defined for this filter, use a fallback
			let item_space_identifier = this.get_matrix_filter_space_identifier_from_parsed([-999999,999999]); // fallback
			if (mismatching_matrix_item_space_identifiers.hasOwnProperty(matrix_item_uuid)){
				item_space_identifier = mismatching_matrix_item_space_identifiers[matrix_item_uuid];
			}

			if (selected_number != null){
				if (this.DEBUG == true){
					console.log("[RangeFilter] adding mismatch to matrix_item " + matrix_item.name + " for space: " + item_space_identifier);
				}
				matrix_item.add_mismatch(this, item_space_identifier);
			}
			else {
				if (this.DEBUG == true){
					console.log("[RangeFilter] removing mismatch from matrix_item " + matrix_item.name + " for space: " + item_space_identifier);
				}
				matrix_item.remove_mismatch(this, item_space_identifier);
			}
		}
	}

}

class TaxonFilter extends ObjectBasedMatrixFilter {

}

class DescriptiveTextAndImagesFilter extends StringBasedMatrixFilter {
	
}

class TextOnlyFilter extends StringBasedMatrixFilter {
	
}

const MATRIX_FILTER_CLASSES = {
	"DescriptiveTextAndImagesFilter" : DescriptiveTextAndImagesFilter,
	"TextOnlyFilter" : TextOnlyFilter,
	"NumberFilter" : NumberFilter,
	"RangeFilter" : RangeFilter,
	"TaxonomicFilter" : TaxonFilter,
	"ColorFilter" : ColorFilter
};

/*
*	MatrixItem
*	- MODE_FLUID: the item gets points when a matching space is selected
*	- MODE_STRICT: the item gets undisplayed if a mismatching space is selected
*/
class MatrixItem {

	constructor (form_element, data, options) {

		this.DEBUG = true;

		this.form_element = form_element;

		this.id = data.id;

		this.uuid = data.uuid;

    	this.name = data.name;
		
		this.taxon = data.taxon;
		this.image_url = data.image_url;
		this.node_type = data.node_type;

		this.is_visible = data.is_visible;

		this.meta_node_id = data.meta_node_id;

		// {matrix_filter_uuid : { space_identifier: space }}
		this.matrix_filter_spaces = {}; 

		for (let matrix_filter_uuid in data.space){

			let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];

			this.matrix_filter_spaces[matrix_filter.uuid] = {};

			let matrix_filter_spaces = data.space[matrix_filter_uuid];

			for (let s=0; s<matrix_filter_spaces.length; s++) {
				let space = matrix_filter_spaces[s];
				let space_identifier = matrix_filter.get_matrix_filter_space_identifier_from_parsed(space);
				this.matrix_filter_spaces[matrix_filter.uuid][space_identifier] = space;

				// register matrix_item with matrix_filter
				matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];
				matrix_filter.register_matrix_item(this, space_identifier);
			}
			
		}

		// the user selectes spaces (traits) during identification. If a selection matches this item, the corresponding space_identifier is added to this list
		// matrix_filter_uuid: {space_identifier : points (int)}
		this.matching_spaces = {};

		// for strict mode
		this.mismatching_spaces = {};

		this.points = 0;
		this.max_points = data.max_points;
	}

	calculate_points () {
		this.points = 0;
		for (let matrix_filter_uuid in this.matching_spaces) {

			for (let space_identifier in this.matching_spaces[matrix_filter_uuid]){
				this.points = this.points + this.matching_spaces[matrix_filter_uuid][space_identifier];
			}
		}

		if (this.DEBUG == true){
			console.log("[MatrixItem] " + this.name + " total points: "  + this.points);
		}

		this.send_points_update_event();
	}

	// try to activate the space_identifier for this matrix_item. this might fail, because this space of this item does not cover the passed space_identifier
	activate_space (matrix_filter, space_identifier) {

		if (this.DEBUG == true){
			console.log("[MatrixItem] " + this.name + ": activating space " + space_identifier + " weight: " + matrix_filter.weight);
		}

		if(!this.matching_spaces.hasOwnProperty(matrix_filter.uuid)){
			this.matching_spaces[matrix_filter.uuid] = {};
		}

		this.matching_spaces[matrix_filter.uuid][space_identifier] = matrix_filter.weight;

		this.calculate_points();
		
	}

	// deactivate the passed space, using its space_identifier
	deactivate_space (matrix_filter, space_identifier) {

		if (this.DEBUG == true){
			console.log("[MatrixItem] " + this.name + ": deactivating space (if active) " + space_identifier + " weight: " + matrix_filter.weight);
		}

		if (this.matching_spaces.hasOwnProperty(matrix_filter.uuid)){

			if (this.matching_spaces[matrix_filter.uuid].hasOwnProperty(space_identifier)){

				delete this.matching_spaces[matrix_filter.uuid][space_identifier];
			}

			if (Object.keys(this.matching_spaces[matrix_filter.uuid]).length == 0){
				delete this.matching_spaces[matrix_filter.uuid];
			}
		}

		this.calculate_points();
	}

	reset () {
		this.matching_spaces = {};
		this.mismatching_spaces = {};
		this.send_mismatch_update_event();
	}

	// events
	send_points_update_event () {

		if (this.DEBUG == true){
			console.log("[MatrixItem] " + this.name +  " sending update-matrix-item event");
		}

		const event_data = {
			detail : {
				"matrix_item" : {
					"uuid" : this.uuid,
					"points" : this.points
				}
			}
		};

		const points_update_event = new CustomEvent("update-matrix-item", event_data);

		this.form_element.dispatchEvent(points_update_event);
	}

	// STRICT MODE only
	// matrix_filter instance calls add_mismatch
	add_mismatch (matrix_filter, space_identifier) {

		if (this.DEBUG == true){
			console.log("[MatrixItem] " + this.name + ": adding space mismatch " + space_identifier);
			console.log(this.mismatching_spaces);
		}

		let initially_had_mismatches = Object.keys(this.mismatching_spaces).length == 0 ? false : true;

		if (!this.mismatching_spaces.hasOwnProperty(matrix_filter.uuid)){
			this.mismatching_spaces[matrix_filter.uuid] = {};
		}

		this.mismatching_spaces[matrix_filter.uuid][space_identifier] = matrix_filter.weight;

		this.send_mismatch_update_event();

		this.signal_matrix_filters(initially_had_mismatches);
	}

	// matrix_filter instance calls remove_mismatch
	remove_mismatch (matrix_filter, space_identifier) {
		if (this.DEBUG == true){
			console.log("[MatrixItem] " + this.name + ": removing space mismatch (if active) " + space_identifier);
		}

		let initially_had_mismatches = Object.keys(this.mismatching_spaces).length == 0 ? false : true;

		if (this.mismatching_spaces.hasOwnProperty(matrix_filter.uuid)){

			if (this.mismatching_spaces[matrix_filter.uuid].hasOwnProperty(space_identifier)){
				delete this.mismatching_spaces[matrix_filter.uuid][space_identifier];
			}

			if (Object.keys(this.mismatching_spaces[matrix_filter.uuid]).length == 0){
				delete this.mismatching_spaces[matrix_filter.uuid];
			}
		}

		this.send_mismatch_update_event();

		this.signal_matrix_filters(initially_had_mismatches);
	}

	send_mismatch_update_event () {

		let mismatch_count = Object.keys(this.mismatching_spaces).length;

		const event_data = {
			detail : {
				"matrix_item" : {
					"uuid" : this.uuid,
					"points" : this.points,
					"mismatch_count" : mismatch_count
				}
			}
		};

		if (this.DEBUG == true){
			console.log("[MatrixItem] " + this.name + " sending mismatch update event");
			console.log(event_data);
		}

		const mismatch_update_event = new CustomEvent("update-matrix-item-mismatch", event_data);

		this.form_element.dispatchEvent(mismatch_update_event);
	}

	// inform the matrix_filters that this matrix_item became visible or invisible
	signal_matrix_filters (initially_had_mismatches) {

		let has_mismatches = Object.keys(this.mismatching_spaces).length == 0 ? false : true;
		
		let signal_matrix_filters = false;
		let action;

		if (initially_had_mismatches == false && has_mismatches == true){
			signal_matrix_filters = true;
			action = "remove";
		}
		else if (initially_had_mismatches == true && has_mismatches == false){
			signal_matrix_filters = true;
			action = "add";
		}

		if (this.DEBUG == true){
			console.log("[MatrixItem] " + this.name + " initially had mismatches: " + initially_had_mismatches + " , has mismatches: " + has_mismatches);
			console.log(this.mismatching_spaces);
		}

		if (signal_matrix_filters == true){

			if (this.DEBUG == true){
				console.log("[MatrixItem]" + this.name + " signaling all MatrixFilters, action: " + action);
			}

			// this.matrix_filter_spaces[matrix_filter.uuid][space_identifier] = space;
			for (let matrix_filter_uuid in this.matrix_filter_spaces){

				let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];

				for (let space_identifier in this.matrix_filter_spaces[matrix_filter.uuid]){
					if (action == "add"){
						matrix_filter.add_to_active_matrix_items(this, space_identifier, false);
					}
					else if (action == "remove"){
						matrix_filter.remove_from_active_matrix_items(this, space_identifier);
					}
				}

			}
		}
	}

}


class IdentificationMatrix {

	constructor (filter_form_id, get_filters_and_items, options) {

		this.DEBUG = true;

		if (options.hasOwnProperty("mode")){
			IDENTIFICATION_MODE = options["mode"];
		}

		this.get_filters_and_items = get_filters_and_items;

		this.filterform = document.getElementById(filter_form_id);

		this.update();

	}

	update () {
		
		var self = this;

		this.get_filters_and_items(function(filters_and_items_json){

			if (self.DEBUG == true){
				console.log(filters_and_items_json);
			}

			// instantiate filters
			for (let matrix_filter_uuid in filters_and_items_json["matrix_filters"]){
				let data = filters_and_items_json["matrix_filters"][matrix_filter_uuid];
				let MatrixFilterClass = MATRIX_FILTER_CLASSES[data.type];
				let matrix_filter = new MatrixFilterClass(self.filterform, matrix_filter_uuid, data.type);

				MATRIX_FILTERS[matrix_filter_uuid] = matrix_filter;
			}

			// apply restrictions
			for (let matrix_filter_uuid in filters_and_items_json["matrix_filters"]){
				let data = filters_and_items_json["matrix_filters"][matrix_filter_uuid];
				let restrictions = data["restrictions"] || {};

				let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];
				matrix_filter.apply_restrictions(restrictions);
			}

			let items = filters_and_items_json["items"];

			// instantiate matrix items (tree nodes)
			for (let i=0; i<items.length; i++){
				let item = items[i];
				let matrix_item = new MatrixItem(self.filterform, item);
				MATRIX_ITEMS[matrix_item.uuid] = matrix_item;

			}

			self.add_all_matrix_items_to_matrix_filters(false);

			self.attach_filterupdate_listeners();

		});
	}

	on_matrix_filter_change (event){

		let matrix_filter_uuid = event.currentTarget.name;

		let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];

		matrix_filter.update();

		// all inputs have been worked
		if (IDENTIFICATION_MODE == MODE_STRICT){
			matrix_filter.update_matrix_item_mismatches(event);
		}

	}

	attach_filterupdate_listeners () {

		var self = this;

		// horizontal sliders
		// checkboxes are multiselect, ranges are single select
		var inputs = this.filterform.querySelectorAll("input[type=radio], input[type=checkbox]");

		for (let i=0; i<inputs.length; i++){
			let input = inputs[i];

			input.addEventListener("change", function(event){
				if (self.DEBUG == true){
					console.log("[IdentificationMatrix] new state of input # " + event.currentTarget.id + " : " + event.currentTarget.checked);
				}
				self.on_matrix_filter_change(event);
			});

		}

		// ranges currently do not work with autoupdate
		// input[type=range] has the problem of not supporting .value="". we have to add boolean "is-null" attribute
		var ranges = this.filterform.querySelectorAll("input[type=range]");
		for (var r=0; r<ranges.length; r++){
			var range = ranges[r];

			range.addEventListener("change", function(event){

				event.currentTarget.setAttribute("is-null", "false");

				if (self.DEBUG == true){
					console.log("[IdentificationMatrix] new state of range input # " + event.currentTarget.id + " : " + event.currentTarget.value);
				}
				self.on_matrix_filter_change(event);
			});

			range.addEventListener("clear", function(event){

				// this does not work. The slider-marker will be set to the center of the range, representing whatever value that is 
				// event.currentTarget.value = "";

				event.currentTarget.setAttribute("is-null", "true");

				if (self.DEBUG == true){
					console.log("[IdentificationMatrix] range cleared # " + event.currentTarget.id + " : " + event.currentTarget.value + " is-null attribute: " + event.currentTarget.getAttribute("is-null"));
				}
				self.on_matrix_filter_change(event);
			});

		}
	}

	add_all_matrix_items_to_matrix_filters (setup) {
		// add all spaces to matrix_filter.active_items
		// all spaces of this matrix_item have to be in active_spaces
		// none of the spaces of this matrix_item can be in inactive_spaces
		// MatrixItem.matrix_filter_spaces[matrix_filter.uuid][space_identifier] = space;
		for (let matrix_item_uuid in MATRIX_ITEMS){

			let matrix_item = MATRIX_ITEMS[matrix_item_uuid];

			for (let matrix_filter_uuid in matrix_item.matrix_filter_spaces){

				let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];

				for (let space_identifier in matrix_item.matrix_filter_spaces[matrix_filter_uuid]){

					matrix_filter.add_to_active_matrix_items(matrix_item, space_identifier, setup);

				}

				if (self.DEBUG == true){
					console.log("[MatrixFilter] " + matrix_filter.matrix_filter_type + " active items on spaces:");
					console.log(matrix_filter.active_matrix_items);
				}
			}
		}
	}

	reset () {
		this.reset_all_matrix_filters();
		this.reset_all_matrix_items();
		this.filterform.reset();
		this.add_all_matrix_items_to_matrix_filters(false);

	}

	reset_all_matrix_filters () {
		for (let matrix_filter_uuid in MATRIX_FILTERS){
			let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];
			matrix_filter.reset();
		}
	}

	reset_all_matrix_items () {
		for (let matrix_item_uuid in MATRIX_ITEMS){
			let matrix_item = MATRIX_ITEMS[matrix_item_uuid];
			matrix_item.reset();
		}
	}

}