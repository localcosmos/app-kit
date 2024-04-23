"use strict";
var MATRIX_FILTERS = {};

var MATRIX_ITEMS = {};

const MODE_STRICT = "strict"; // sort items out immediately
const MODE_FLUID = "fluid"; // do not sort out, sort by points in descending order

var IDENTIFICATION_MODE = MODE_FLUID;

const STATUS_ACTIVE = "active";
const STATUS_INACTIVE = "inactive";


class MatrixFilterSpace {

  constructor(matrix_filter, space_json) {

    this.DEBUG = true;

    this.matrix_filter = matrix_filter;

    this.space_identifier = space_json["spaceIdentifier"];
    this.encoded_space = space_json["encodedSpace"];

    // if a MatrixFilter is restricted by this MatrixfilterSpace, the MatrixFilter is listed in restricts{}
    //{matrix_filter_uuid:matrix_filter}
    this.restricts = {};

    this.input_element = null;

    this.matching_matrix_items = {};
    this.mismatching_matrix_items = {};


    // (STRICT MODE) store currently active MatrixItems for this MatrixFilterSpace
    // if this is empty, this MatrixfilterSpace becomes impossible
    this.active_matching_matrix_items = {};

    // selected by the user or unselected
    this.status = STATUS_INACTIVE;

    // Strict mode: this filter is within the current of all remaining  MatrixItems
    this.is_possible = true;

  }

  // register a MatrixFilter restricted by this space
  register_restricted_matrix_filter(restricted_matrix_filter) {
    this.restricts[restricted_matrix_filter.uuid] = restricted_matrix_filter;
  }

  register_matching_matrix_item(matrix_item) {
    this.matching_matrix_items[matrix_item.uuid] = matrix_item;
    // initially all MatrixItems are active
    this.active_matching_matrix_items[matrix_item.uuid] = matrix_item;
  }

  register_mismatching_matrix_item(matrix_item) {
    this.mismatching_matrix_items[matrix_item.uuid] = matrix_item;
  }

  // DOM BINDINGS
  bind_input_element(input_element) {

    if (this.input_element != null) {
      throw new Error("[MatrixFilterSpace] " + this.space_identifier + " of " + this.matrix_filter.matrixFilterType + " is already bound to an input element");
    }

    var self = this;
    this.input_element = input_element;

    input_element.addEventListener("change", function (event) {
      if (self.DEBUG == true) {
        console.log("[MatrixFilterSpace] new state of input # " + event.currentTarget.id + " : " + event.currentTarget.checked);
      }
      self.on_change(event);
    });

  }

  get_input_element () {
    return this.input_element;
  }

  on_change(event) {

    let input = event.currentTarget;
    let checked = input.checked;
    if (checked == true) {
      this.activate();
    }
    else {
      this.deactivate();
    }
  }

  get_event_data () {
    
    const event_data = {
      detail : {
        matrix_filter : {
          uuid : this.matrix_filter.uuid
        },
        space_identifier: this.space_identifier
      }
    };

    return event_data;
  }

  // if the user clicked on a input element to select the filter,  MatrixFilterSpace becomes active
  // depending on IDENTIFICATION_MODE, this has different consequences
  // MODE_STRICT:
  //  - this space is added to MatrixItem.mismatching_spaces[matrix_filter_uuid][space_identifier]
  //  - all matrix items in this.mismatching_matrix_items have to be informed
  // MODE_FLUID:
  //  - all matrix items in this.matching_matrix_items have to be informed
  // BOTH:
  //  - all MatrixFilters listed in this.restricts are informed
  activate() {

    console.log("[MatrixFilterSpace] " + this.matrix_filter.matrixFilterType + " is being activated.");

    this.status = STATUS_ACTIVE; 

    if (this.input_element.checked == false){
      this.input_element.checked = true;
    }

    this.input_element.setAttribute("checked", true);

    // work restrictions
    this.signal_restricted_matrix_filters(true);

    // notify matrix items
    this.signal_matrix_items();

    // fire event
    const turned_on_event = new Event("turnedOn");
		this.input_element.dispatchEvent(turned_on_event);

    // deactivate all other spaces if only one is allowed
    if (this.matrix_filter.allowMultipleValues == false){

      if (this.DEBUG == true){
        console.log("[MatrixFilterSpace] no multiple values allowed, deactivating all other spaces for " + this.matrix_filter.matrixFilterType);
      }

      for (let space_identifier in this.matrix_filter.matrix_filter_spaces){
        if (space_identifier != this.space_identifier){
          let matrix_filter_space = this.matrix_filter.matrix_filter_spaces[space_identifier];

          if (matrix_filter_space.status == STATUS_ACTIVE){
            matrix_filter_space.deactivate();
          }
        }
      }
    }

    this.post_activation();
  }

  // hook
  post_activation () {}

  // if the user clicked on a input element to UNselect the filter,  MatrixFilterSpace becomes INactive 
  deactivate() {

    if (this.status == STATUS_ACTIVE){
      console.log("[MatrixFilterSpace] " + this.matrix_filter.matrixFilterType + " is being deactivated.");

      this.status = STATUS_INACTIVE;

      if (this.input_element.checked == true){
        this.input_element.checked = false;
      }

      this.input_element.removeAttribute("checked");

      // work restrictions
      this.signal_restricted_matrix_filters(false);

      // notify matrix items
      this.signal_matrix_items();

      const turned_off_event = new Event("turnedOff");
      this.input_element.dispatchEvent(turned_off_event);
    }

  }

  // signal all matrix_filters which are restricted by this space_identifier of this matrix_filter
  signal_restricted_matrix_filters(is_turned_on) {

    if (this.DEBUG == true){
      console.log("[MatrixFilterSpace] " + this.matrix_filter.matrixFilterType + " " + this.space_identifier + " restricts: ");
      console.log(this.restricts);
    }

    for (let matrix_filter_uuid in this.restricts) {

      let restricted_matrix_filter = this.restricts[matrix_filter_uuid];

      if (this.DEBUG == true) {
        console.log("[MatrixFilterSpace] " + this.space_identifier + " of " + this.matrix_filter.matrixFilterType + " is signaling MatrixFilter " + restricted_matrix_filter.matrixFilterType + " " + restricted_matrix_filter.uuid);
      }

      restricted_matrix_filter.receive_restriction_update(this, is_turned_on);
    }

  }

  signal_matrix_items (){
    // always signal matching matrix items
    this.signal_matching_matrix_items();

    if (IDENTIFICATION_MODE == MODE_STRICT){
      this.signal_mismaching_matrix_items();
    }
  }

  signal_matching_matrix_items (){
    if (this.DEBUG == true){
			console.log("[MatrixFilterSpace] " + this.matrix_filter.matrixFilterType + " " + this.space_identifier + " is signaling matching_matrix_items");
		}

    for (let matrix_item_uuid in this.matching_matrix_items){
      let matrix_item = this.matching_matrix_items[matrix_item_uuid];

      if(this.status == STATUS_ACTIVE){
        matrix_item.add_matching_matrix_filter_space(this);
      }
      else {
        matrix_item.remove_matching_matrix_filter_space(this);
      }
    }
  }

  signal_mismaching_matrix_items (){
    if (this.DEBUG == true){
			console.log("[MatrixFilterSpace] " + this.matrix_filter.matrixFilterType + " " + this.space_identifier + " is signaling mismatching_matrix_items");
		}

    for (let matrix_item_uuid in this.mismatching_matrix_items){
      let matrix_item = this.mismatching_matrix_items[matrix_item_uuid];
      if(this.status == STATUS_ACTIVE){
        matrix_item.add_mismatching_matrix_filter_space(this);
      }
      else {
        matrix_item.remove_mismatching_matrix_filter_space(this);
      }
    }
  }

  // manage visibility of this space
  get_is_possible() {
    let is_possible = Object.keys(this.active_matching_matrix_items).length == 0 ? false : true;
    return is_possible;
  }

  activate_matching_matrix_item(matrix_item) {
    
    if (this.DEBUG == true){
			console.log("[MatrixFilterSpace] " + this.matrix_filter.matrixFilterType + " " + this.space_identifier + " now adds MatrixItem " + matrix_item.name + " to active_matching_matrix_items");
		}

    let is_initially_possible = this.get_is_possible();

    if (!this.active_matching_matrix_items.hasOwnProperty(matrix_item.uuid)){
      this.active_matching_matrix_items[matrix_item.uuid] = matrix_item;
    }

    this.is_possible = true;

    if (is_initially_possible == false){
      this.send_possible_event();
    }

  }

  deactivate_matching_matrix_item(matrix_item) {
    if (this.DEBUG == true){
			console.log("[MatrixFilterSpace] " + this.matrix_filter.matrixFilterType + " " + this.space_identifier + " now removes MatrixItem " + matrix_item.name + " from active_matching_matrix_items");
		}

    let is_initially_possible = this.get_is_possible();

    if (this.active_matching_matrix_items.hasOwnProperty(matrix_item.uuid)){
      delete this.active_matching_matrix_items[matrix_item.uuid];
    }

    let is_possible = this.get_is_possible();

    if (is_possible == false){
      this.is_possible = false;
      if (is_initially_possible == true){
        this.send_impossible_event();
      }
    }
  }

  // send an event if this.is_possible changes from false to true
  send_possible_event() {
    if (this.DEBUG == true){
			console.log("[MatrixFilterSpace] " + this.matrix_filter.matrixFilterType + " " + this.space_identifier + " became possible");
		}

    const event_data = this.get_event_data();
    const possible_event = new CustomEvent("possible", event_data);

    let input_element = this.get_input_element();
    input_element.dispatchEvent(possible_event);
  }

  // send an event if this.is_possible changes from true to false
  send_impossible_event() {
    if (this.DEBUG == true){
			console.log("[MatrixFilterSpace] " + this.matrix_filter.matrixFilterType + " " + this.space_identifier + " became impossible");
		}

    const event_data = this.get_event_data();
    const impossible_event = new CustomEvent("impossible", event_data);

    let input_element = this.get_input_element();
    input_element.dispatchEvent(impossible_event);
  }

}

class DescriptiveTextAndImagesSpace extends MatrixFilterSpace {
}

class TextOnlySpace extends MatrixFilterSpace {

}

class ColorSpace extends MatrixFilterSpace {

}

class NumberSpace extends MatrixFilterSpace {

}

class RangeSpace extends MatrixFilterSpace {

  // event listener is bound to Rangefilter
  bind_input_element(input_element) {
    this.input_element = input_element;
  }

  on_change(event) {

    throw new Error("[RangeFilterSpace] method on_change can only be called from RangeFilter");
  }

  get_input_element () {
    return this.matrix_filter.input_element;
  }

  activate() {    

    if (this.status == STATUS_INACTIVE){

      if (this.DEBUG == true){
        let space_str = JSON.stringify(this.encoded_space);//this.matrix_filter.get_space_str_from_space_identifier(this.space_identifier);
        console.log("[RangeSpace] " + space_str + " is now active");
      }

      this.status = STATUS_ACTIVE;
      // work restrictions
      this.signal_restricted_matrix_filters(true);

      // notify matrix items
      this.signal_matrix_items();

      this.post_activation();

    }
  }

  deactivate() {

    if (this.status == STATUS_ACTIVE){

      if (this.DEBUG == true){
        let space_str = JSON.stringify(this.encoded_space); //this.matrix_filter.get_space_str_from_space_identifier(this.space_identifier);
        console.log("[RangeSpace] " + space_str + " is now inactive");
      }

      this.status = STATUS_INACTIVE;

      // work restrictions
      this.signal_restricted_matrix_filters(false);

      // notify matrix items
      this.signal_matrix_items();

    }
  }

}

class TaxonFilterSpace extends MatrixFilterSpace {

}


class MatrixFilter {

  constructor(form_element, uuid, matrixFilterType, name, weight, allowMultipleValues) {
    this.DEBUG = true;

    // for firing events
    this.form_element = form_element;

    this.uuid = uuid;
    this.matrixFilterType = matrixFilterType;

    this.name = name;

    this.allowMultipleValues = allowMultipleValues;

    // {space_identifier : MatrixFilterSpace}
    // contains the spaces of this filter
    this.matrix_filter_spaces = {};

    // if this filter is restricted by another filter, the "other" filter is listed in restricted_by{}
    // {matrix_filter_uuid : { space_identifier : false } }
    // if all space_identifiers are set to true, show the filter
    this.restricted_by = {};

    // active: unrestricted filter, or all restrictions are met
    this.status = STATUS_ACTIVE;

    this.weight = weight;

    // map space_identifiers to matrix_items
    // {spaceIdentifier : [matrixItemUuid, matrixItemUuid]}
    this.matrix_item_registry = {};

    // for strict mode only
    // {spaceIdentifier: [matrixItemUuid, matrixItemUuid]}
    // if a space has no active items, it will be disabled in strict mode
    this.active_matrix_items = {}
  }

  //
  // MATRIX FILTER SPACE MANAGEMENT
  //

  // return b64 encoded space_identifier
  // space is the parsed space from JSON.parse
  get_space_identifier_from_parsed(space) {
    throw new Error("[MatrixFilter] subclasses require a get_space_identifier_from_parsed method");
  }

  // return b64 encoded space_identifier
  get_space_identifier_from_str(space_str) {
    throw new Error("[MatrixFilter] subclasses require a get_space_identifier_from_str method");
  }

  parse_space_str(space_str) {
    throw new Error("[MatrixFilter] subclasses require a parse_matrix_filter_space_str method");
  }

  // space_identifier is the b64 encoded space_str
  get_space_from_space_identifier(space_identifier) {
    throw new Error("[MatrixFilter] subclasses require a get_space_from_space_identifier method");
  }

  get_space_str_from_space_identifier(space_identifier) {
    throw new Error("[MatrixFilter] subclasses require a get_space_str_from_space_identifier method");
  }

  // space is the parsed space from JSON.parse()
  add_matrix_filter_space(space) {

    if (this.DEBUG == true){
      console.log("[MatrixFilter] " + this.matrixFilterType + " adding space: ");
      console.log(space);
    }

    var space_identifier = this.get_space_identifier_from_parsed(space);
    var matrix_filter_space = null

    // only register every space_identifier once
    if (!this.matrix_filter_spaces.hasOwnProperty(space_identifier)) {
      matrix_filter_space = new this.MatrixFilterSpaceClass(this, space);
      this.matrix_filter_spaces[space_identifier] = matrix_filter_space;
    }
    else {
      matrix_filter_space = this.matrix_filter_spaces[space_identifier];
    }

    return matrix_filter_space;
  }

  //
  // RESTRICTION MANAGEMENT
  //
  // if this MatrixFilter is restricted by the space of another filter, register with the restrictive space,
  // AND register with this.restricted_by[matrix_filter_uuid][space_identifier] = BOOLEAN
  apply_restrictions(restrictions) {

    for (let restrictive_matrix_filter_uuid in restrictions) {

      let restrictive_matrix_filter = MATRIX_FILTERS[restrictive_matrix_filter_uuid];

      if (this.DEBUG == true){
        console.log("[MatrixFilter] applying restrictions. " + this.matrixFilterType + " is restricted by " + restrictive_matrix_filter.matrixFilterType);
      }

      let restriction_spaces = restrictions[restrictive_matrix_filter_uuid];

      this.restricted_by[restrictive_matrix_filter_uuid] = {};

      for (let v = 0; v < restriction_spaces.length; v++) {

        let parsed_restriction_space = restriction_spaces[v];

        let space_identifier = parsed_restriction_space['spaceIdentifier']; //restrictive_matrix_filter.get_space_identifier_from_parsed(parsed_restriction_space);

        console.log("[MatrixFilter] applying restriction to " + this.matrixFilterType + ": " + restrictive_matrix_filter.matrixFilterType + " " + parsed_restriction_space + " " + space_identifier);

        this.restricted_by[restrictive_matrix_filter_uuid][space_identifier] = false;

        // e.g. RangeFilter might not have that space added yet. The RangeSpace can be part of the restriction,
        // but nor part of any MatrixItem
        if (!restrictive_matrix_filter.matrix_filter_spaces.hasOwnProperty(space_identifier)){
          if (this.DEBUG == true){
            console.log("[MatrixFilter] trying to restrict with yet unknown space_identifier: " + space_identifier);
          }
          let matrix_filter_space = restrictive_matrix_filter.add_matrix_filter_space(parsed_restriction_space);
        }

        let restrictive_matrix_filter_space = restrictive_matrix_filter.matrix_filter_spaces[space_identifier];
        restrictive_matrix_filter_space.register_restricted_matrix_filter(this);
      }
    }

    if (Object.keys(this.restricted_by).length > 0) {
      this.deactivate();
    }
  }

  receive_restriction_update(matrix_filter_space, is_turned_on) {

    let restricting_matrix_filter = matrix_filter_space.matrix_filter;
    let space_identifier = matrix_filter_space.space_identifier;

    if (this.restricted_by.hasOwnProperty(restricting_matrix_filter.uuid)) {
      let restriction = this.restricted_by[restricting_matrix_filter.uuid];

      if (restriction.hasOwnProperty(space_identifier)) {

        if (this.DEBUG == true) {
          console.log("[MatrixFilter] " + this.matrixFilterType + " " + this.uuid + " received restriction update from " + restricting_matrix_filter.matrixFilterType + " " + space_identifier + " , is_turned_on : " + is_turned_on);
        }

        this.restricted_by[restricting_matrix_filter.uuid][space_identifier] = is_turned_on;
      }

      else {
        throw new Error("[MatrixFilter] " + this.matrixFilterType + " error in receive_restriction_update. Restrictive filter not found.");
      }
    }

    this.check_restrictions();
  }

  // if the visibilty is false, turn off all selected spaces, then call .update()
  check_restrictions() {

    let is_active = true;

    if (this.DEBUG == true) {
      console.log(this.restricted_by);
    }

    for (let matrix_filter_uuid in this.restricted_by) {

      let restriction = this.restricted_by[matrix_filter_uuid];

      for (let space_identifier in restriction) {
        is_active = restriction[space_identifier];
        if (is_active == false) {
          break;
        }
      }

      if (is_active == false) {
        break;
      }
    }

    if (this.DEBUG == true) {
      console.log("[MatrixFilter] " + this.matrixFilterType + " " + this.uuid + " worked restrictions, is_active:" + is_active);
    }

    if (is_active == true) {
      this.activate();
    }
    else {
      this.reset();
      this.deactivate();
    }
  }

  // hide or show the matrix_filter as a whole if its visibilty depends on a filter selection
  // use EVENTS, no dom manipulation here
  get_event_data() {

    const event_data = {
      detail: {
        "matrix_filter": {
          "uuid": this.uuid,
          "matrixFilterType": this.matrixFilterType,
          "status": this.status
        }
      }
    };

    return event_data;
  }

  // if all restrictions are met, this filter becomes usable by the user (STATUS_ACTIVE)
  activate() {

    this.status = STATUS_ACTIVE;

    const event_data = this.get_event_data();

    const activation_event = new CustomEvent("activate-matrix-filter", event_data);

    this.form_element.dispatchEvent(activation_event);

  }

  // if there is an active restriction, this filter becomes unusable by the user (STATUS_INACTIVE)
  deactivate() {

    if (this.status == STATUS_ACTIVE){

      this.status = STATUS_INACTIVE;

      // deactivate all MatrixFilterSpaces on MatrixFilter deactivation
      this.reset();

      const event_data = this.get_event_data();

      const deactivation_event = new CustomEvent("deactivate-matrix-filter", event_data);

      this.form_element.dispatchEvent(deactivation_event);
    }

  }

  // reset deactivates all MatrixFilterSpaces of this filter
  reset () {
    for (let space_identifier in this.matrix_filter_spaces){
      let matrix_filter_space = this.matrix_filter_spaces[space_identifier];
      matrix_filter_space.deactivate();
    }
  }

  // MATRIX ITEM MANAGEMENT


  // DOM BINDINGS
  // get the space_identifier from the input

  bind_input_element(input_element) {
    let space_identifier = this.get_space_identifier_from_input_element(input_element);

    // it is possible, that a space_identifier does not exist on any matrix item. In this case, the input_element stays unbound
    if (this.matrix_filter_spaces.hasOwnProperty(space_identifier)){
      let matrix_filter_space = this.matrix_filter_spaces[space_identifier];
      matrix_filter_space.bind_input_element(input_element);
    }
    else {
      console.warn("[MatrixFilter] " + this.matrixFilterType + " space_identifier " + space_identifier + " not found in matrix_filter_spaces.");
      console.warn(this.matrix_filter_spaces);

      // send impossible event
      const event_data = {
        detail : {
          matrix_filter : {
            uuid : this.uuid
          },
          space_identifier: space_identifier
        }
      };
      const impossible_event = new CustomEvent("impossible", event_data);
      input_element.dispatchEvent(impossible_event);
    }
  }

  get_space_identifier_from_input_element(input_element) {
    //let space_str = input_element.value;
    //let space_identifier = this.get_space_identifier_from_str(space_str);
    let space_identifier = input_element.getAttribute("data-spaceIdentifier");
    return space_identifier;
  }

}

class StringBasedMatrixFilter extends MatrixFilter {

  // space is the parsed space from JSON.parse
  get_space_identifier_from_parsed(space) {
    if (this.DEBUG == true) {
      console.log("[StringBasedMatrixFilter] " + this.matrixFilterType + "] stringifying parsed space: " + space);
    }

    // base64 encoded space
    //let space_identifier = btoa(space);
    let space_identifier = space["spaceIdentifier"];

    if (this.DEBUG == true) {
      console.log(space_identifier);
    }

    return space_identifier;
  }

  get_space_identifier_from_str(space_str) {
    return btoa(space_str);
  }

  parse_space_str(space_str) {
    return space_str;
  }

  get_space_from_space_identifier(space_identifier) {
    return atob(space_identifier);
  }

  get_space_str_from_space_identifier(space_identifier) {
    return atob(space_identifier);
  }

}

class ObjectBasedMatrixFilter extends MatrixFilter {

  get_space_identifier_from_parsed(space) {
    if (this.DEBUG == true) {
      console.log("[ObjectBasedMatrixFilter] " + this.matrixFilterType + " stringifying parsed space: " + space);
    }

    // b64 encoded space identifier
    //let space_identifier = btoa(JSON.stringify(space));
    let space_identifier = space["spaceIdentifier"];

    if (this.DEBUG == true) {
      console.log(space_identifier);
    }

    return space_identifier;
  }

  // str, not b64encoded
  get_space_identifier_from_str(space_str) {

    if (this.DEBUG == true) {
      console.log("[ObjectBasedMatrixFilter] trying to parse: " + space_str);
    }

    // first parse to ensure the identifier is equal to from_parsed
    return btoa(JSON.stringify(JSON.parse(space_str)));
  }

  parse_space_str(space_str) {
    return JSON.parse(space_str);
  }

  // return thr parsed space
  get_space_from_space_identifier(space_identifier) {
    return JSON.parse(atob(space_identifier));
  }

  get_space_str_from_space_identifier(space_identifier) {
    return atob(space_identifier);
  }
}


class DescriptiveTextAndImagesFilter extends StringBasedMatrixFilter {

  constructor(form_element, uuid, matrixFilterType, name, weight, allowMultipleValues) {

    super(form_element, uuid, matrixFilterType, name, weight, allowMultipleValues);

    this.MatrixFilterSpaceClass = DescriptiveTextAndImagesSpace;
  }

}

class TextOnlyFilter extends StringBasedMatrixFilter {

  constructor(form_element, uuid, matrixFilterType, name, weight, allowMultipleValues) {

    super(form_element, uuid, matrixFilterType, name, weight, allowMultipleValues);

    this.MatrixFilterSpaceClass = TextOnlySpace;
  }

}


class ColorFilter extends ObjectBasedMatrixFilter {

  constructor(form_element, uuid, matrixFilterType, name, weight, allowMultipleValues) {

    super(form_element, uuid, matrixFilterType, name, weight, allowMultipleValues);

    this.MatrixFilterSpaceClass = ColorSpace;
  }

}

class NumberFilter extends ObjectBasedMatrixFilter {

  constructor(form_element, uuid, matrixFilterType, name, weight, allowMultipleValues) {

    super(form_element, uuid, matrixFilterType, name, weight, allowMultipleValues);

    this.MatrixFilterSpaceClass = NumberSpace;
  }

}

/*
* RangeFilter differs from other filters. There is only one range slider. You can think of multiple ranges being defined on one slider input element
*/
class RangeFilter extends ObjectBasedMatrixFilter {

  constructor(form_element, uuid, matrixFilterType, name, weight, allowMultipleValues) {

    super(form_element, uuid, matrixFilterType, name, weight, allowMultipleValues);

    this.MatrixFilterSpaceClass = RangeSpace;

    // all RangeFilteSpace instances share the same input_element which is bound to RangeFilter
    this.input_element = null;
  }

  // return the value as a string
  get_value_from_input_element (input_element) {

		let is_null = input_element.getAttribute("is-null", "true");

		if (is_null == "true" || is_null == true){
			return "";
		}
		else {
			return input_element.value;
		}
	}

  // only one range slider input element
  // how to handle MatrixFilterSpaces ? there are ranges defined on MatrixItems and on MatrixFilters(restrictions)
  bind_input_element(input_element) {

    var self = this;

    this.input_element = input_element;

    input_element.addEventListener("change", function(event){
        self.on_change(event);
    });

    input_element.addEventListener("clear", function(event){
      self.on_clear(event);
    });

  }

  get_space_from_space_identifier(space_identifier){
    let space_parts = space_identifier.split(":");
    let space_b64 = space_parts[1];
    let space_str = atob(space_b64);
    let space = JSON.parse(space_str);
    return space;
  }

  on_change(event){

    let value_str = this.get_value_from_input_element(event.currentTarget);

    if (this.DEBUG == true){
      console.log("[RangeFilter] user selected " + value_str);
    }

    for (let space_identifier in this.matrix_filter_spaces){
      //"spaceIdentifier": "135a384b-eba5-468b-8ae7-b65d3e38bb43:WzMuMCw3LjBd"
      let matrix_filter_space = this.matrix_filter_spaces[space_identifier];

      //let specific_range = this.get_space_from_space_identifier(space_identifier);
      let specific_range = matrix_filter_space.encoded_space;
      
      let value_is_within_range = false;
      if (value_str.length > 0){
        let value = parseFloat(value_str);
        if (value >= specific_range[0] && value <= specific_range[1]){
          value_is_within_range = true;
        }
      }

      if (value_is_within_range == true){

        if (this.DEBUG == true){
          console.log("[RangeFilter] " + value_str + " is within " + specific_range);
        }
        matrix_filter_space.activate();
      }
      else {
        if (this.DEBUG == true){
          console.log("[RangeFilter] " + value_str + " is not within " + specific_range);
        }
        matrix_filter_space.deactivate();
      }

    }
  }

  on_clear (event) {
    this.reset();
  }

  send_turned_off_event() {
    const turned_off_event = new Event("turnedOff");
    this.input_element.dispatchEvent(turned_off_event);
  }

  reset () {
    super.reset()

    this.input_element.value = "";
    this.send_turned_off_event();
  }

}

class TaxonFilter extends ObjectBasedMatrixFilter {

  constructor(form_element, uuid, matrixFilterType, name, weight, allowMultipleValues) {

    super(form_element, uuid, matrixFilterType, name, weight, allowMultipleValues);

    this.MatrixFilterSpaceClass = TaxonFilterSpace;
  }

  // input_element.value is the b64 encoded space
  get_space_identifier_from_input_element(input_element) {
    //let space_identifier = input_element.value;
    let space_identifier = input_element.getAttribute("data-spaceIdentifier");
    return space_identifier;
  }

}

const MATRIX_FILTER_CLASSES = {
  "DescriptiveTextAndImagesFilter": DescriptiveTextAndImagesFilter,
  "TextOnlyFilter": TextOnlyFilter,
  "NumberFilter": NumberFilter,
  "RangeFilter": RangeFilter,
  "TaxonFilter": TaxonFilter,
  "ColorFilter": ColorFilter
};


class MatrixItem {

  constructor(uuid, name, taxon, maxPoints, form_element) {

    this.DEBUG = true;

    this.uuid = uuid;
    this.name = name;
    this.taxon = taxon;

    // for firing events
    this.form_element = form_element;

    this.points = 0;
    this.points_percentage =0;
    this.maxPoints = maxPoints;

    // matrix_filter_spaces associated with this MatrixItem
    // { matrix_filter_uuid : { space_identifier : MatrixfilterSpace } }
    this.matrix_filter_spaces = {}; // constant

    this.active_matching_matrix_filter_spaces = {};
    this.active_mismatching_matrix_filter_spaces = {};
    this.status = STATUS_ACTIVE;

  }

  add_matrix_filter_space (matrix_filter_space) {
    let matrix_filter = matrix_filter_space.matrix_filter;

    if (!this.matrix_filter_spaces.hasOwnProperty(matrix_filter.uuid)){
      this.matrix_filter_spaces[matrix_filter.uuid] = {};
    }

    this.matrix_filter_spaces[matrix_filter.uuid][matrix_filter_space.space_identifier] = matrix_filter_space;

  }

  // ALL MODES
  calculate_points () {
    let points = 0;
		for (let matrix_filter_uuid in this.active_matching_matrix_filter_spaces) {

			for (let space_identifier in this.active_matching_matrix_filter_spaces[matrix_filter_uuid]){
        let weight = this.active_matching_matrix_filter_spaces[matrix_filter_uuid][space_identifier];
				points = points + weight;
			}
		}

		if (this.DEBUG == true){
			console.log("[MatrixItem] " + this.name + " total points: "  + points);
		}

		return points;
  }

  add_matching_matrix_filter_space(matrix_filter_space) {

    if (this.DEBUG == true){
      console.log("[MatrixItem] " + this.name + " is adding space " + matrix_filter_space.space_identifier + " of " + matrix_filter_space.matrix_filter.matrixFilterType);
    }

    let matrix_filter = matrix_filter_space.matrix_filter;

    if (!this.active_matching_matrix_filter_spaces.hasOwnProperty(matrix_filter.uuid)) {
      this.active_matching_matrix_filter_spaces[matrix_filter.uuid] = {};
    }

    this.active_matching_matrix_filter_spaces[matrix_filter.uuid][matrix_filter_space.space_identifier] = matrix_filter.weight;

    this.update();

  }

  remove_matching_matrix_filter_space(matrix_filter_space) {

    if (this.DEBUG == true){
      console.log("[MatrixItem] " + this.name + " is removing space " + matrix_filter_space.space_identifier + " of " + matrix_filter_space.matrix_filter.matrixFilterType);
    }

    let matrix_filter = matrix_filter_space.matrix_filter;

    if (this.active_matching_matrix_filter_spaces.hasOwnProperty(matrix_filter.uuid)) {
      let matrix_item_space = this.active_matching_matrix_filter_spaces[matrix_filter.uuid];

      if (matrix_item_space.hasOwnProperty(matrix_filter_space.space_identifier)){
        delete this.active_matching_matrix_filter_spaces[matrix_filter.uuid][matrix_filter_space.space_identifier];
      }

      if (Object.keys(this.active_matching_matrix_filter_spaces[matrix_filter.uuid]).length == 0){
        delete this.active_matching_matrix_filter_spaces[matrix_filter.uuid];
      }
    }

    this.update();
  }

  update() {

    if (this.DEBUG == true){
      console.log("[MatrixItem] " + this.name + " updating points");
    }

    this.points = this.calculate_points();
    this.points_percentage = this.points / this.maxPoints;
    this.send_matrix_item_update_event();

    if (this.points_percentage == 1){
      this.send_100_percent_event();
    }
  }

  // events
  get_event_data () {
    const event_data = {
			detail : {
				"matrix_item" : {
					"uuid" : this.uuid,
					"points" : this.points,
          "maxPoints" : this.maxPoints,
          "points_percentage" : this.points_percentage
				}
			}
		};

    return event_data;

  }

	send_matrix_item_update_event () {

		if (this.DEBUG == true){
			console.log("[MatrixItem] " + this.name +  " sending update-matrix-item event");
		}

		const event_data = this.get_event_data();

		const points_update_event = new CustomEvent("update-matrix-item", event_data);

		this.form_element.dispatchEvent(points_update_event);
	}

  // send an event when a matrix item reaches 100%
  send_100_percent_event () {
    if (this.DEBUG == true){
			console.log("[MatrixItem] " + this.name +  " sending matrix-item-100-percent");
		}

		const event_data = this.get_event_data();

		const matrix_item_100_percent_event = new CustomEvent("matrix-item-100-percent", event_data);

		this.form_element.dispatchEvent(matrix_item_100_percent_event);
  }

  reset() {

    this.points = 0;

    this.active_matching_matrix_filter_spaces = {};
    this.active_mismatching_matrix_filter_spaces = {};
    
    this.activate();
  }

  //
  // STRICT MODE ONLY
  //
  add_mismatching_matrix_filter_space(matrix_filter_space) {

    if (this.DEBUG == true){
      console.log("[MatrixItem] " + this.name + " received an added mismatch from " + matrix_filter_space.matrix_filter.matrixFilterType + " : " + matrix_filter_space.space_identifier);
    }

    let matrix_filter = matrix_filter_space.matrix_filter;
    let matrix_item_is_initially_visible = Object.keys(this.active_mismatching_matrix_filter_spaces).length == 0 ? false : true;

    if(!this.active_mismatching_matrix_filter_spaces.hasOwnProperty(matrix_filter.uuid)){
      this.active_mismatching_matrix_filter_spaces[matrix_filter.uuid] = {}; 
    }

    this.active_mismatching_matrix_filter_spaces[matrix_filter.uuid][matrix_filter_space.space_identifier] = matrix_filter_space;

    if (matrix_item_is_initially_visible == false){
      this.deactivate();
    }
  }

  remove_mismatching_matrix_filter_space(matrix_filter_space) {

    if (this.DEBUG == true){
      console.log("[MatrixItem] " + this.name + " received a removed mismatch from " + matrix_filter_space.matrix_filter.matrixFilterType + " : " + matrix_filter_space.space_identifier);
    }

    let matrix_filter = matrix_filter_space.matrix_filter;
    let matrix_item_is_initially_visible = Object.keys(this.active_mismatching_matrix_filter_spaces).length == 0 ? false : true;

    if (this.active_mismatching_matrix_filter_spaces.hasOwnProperty(matrix_filter.uuid)) {
      let matrix_item_space = this.active_mismatching_matrix_filter_spaces[matrix_filter.uuid];

      if (matrix_item_space.hasOwnProperty(matrix_filter_space.space_identifier)){
        delete this.active_mismatching_matrix_filter_spaces[matrix_filter.uuid][matrix_filter_space.space_identifier];
      }

      if (Object.keys(this.active_mismatching_matrix_filter_spaces[matrix_filter.uuid]).length == 0){
        delete this.active_mismatching_matrix_filter_spaces[matrix_filter.uuid];
      }
    }

    if (Object.keys(this.active_mismatching_matrix_filter_spaces).length == 0 && matrix_item_is_initially_visible == true) {
      this.activate();
    }
  }

  // the matrix_item had mismatches and the last mismatch has been removed. the matrix item transforms from inactive to active
  activate() {

    this.status = STATUS_ACTIVE;

    // when a MatrixItem gets activated, MatrixFilterSpaces can become possible
    this.signal_matrix_filter_spaces(true);

		if (this.DEBUG == true){
			console.log("[MatrixItem] " + this.name +  " sending activate-matrix-item event");
		}

		const event_data = this.get_event_data();

		const activation_event = new CustomEvent("activate-matrix-item", event_data);

		this.form_element.dispatchEvent(activation_event);
  }

  // the matrix_item had no mismatches and the the first mismatch has been added. the matrix item transforms from active to inactive
  deactivate() {

    this.status = STATUS_INACTIVE;

    // when a MatrixItem gets deactivated, MatrixFilterSpaces can become impossible
    this.signal_matrix_filter_spaces(false);

    if (this.DEBUG == true){
			console.log("[MatrixItem] " + this.name +  " sending deactivate-matrix-item event");
		}

		const event_data = this.get_event_data();

		const deactivation_event = new CustomEvent("deactivate-matrix-item", event_data);

		this.form_element.dispatchEvent(deactivation_event);
  }

  signal_matrix_filter_spaces(matrix_item_is_active) {
    for (let matrix_filter_uuid in this.matrix_filter_spaces){
      let item_spaces = this.matrix_filter_spaces[matrix_filter_uuid];
      for (let space_identifier in item_spaces){
        let matrix_filter_space = item_spaces[space_identifier];

        if (matrix_item_is_active == true){
          matrix_filter_space.activate_matching_matrix_item(this);
        }
        else {
          matrix_filter_space.deactivate_matching_matrix_item(this);
        }
      }
    }
  }
}


class IdentificationMatrix {

  constructor(filter_form_id, get_matrix_filters_and_items, options) {

    this.DEBUG = true;

    var options = options || {};

    if (options.hasOwnProperty("mode")) {
      IDENTIFICATION_MODE = options["mode"];
    }

    this.get_matrix_filters_and_items = get_matrix_filters_and_items;

    this.data = [];

    this.form_element = document.getElementById(filter_form_id);

    this.init();

  }

  init(onFinished) {

    if (this.DEBUG == true){
      console.log("[IdentificationMatrix] is initializing.");
    }

    var self = this;

    this.get_matrix_filters_and_items(function (matrix_filters_and_items_json) {

      if (self.DEBUG == true) {
        console.log(matrix_filters_and_items_json);
      }


      self.data = matrix_filters_and_items_json;

      // instantiate filters
      for (let matrix_filter_uuid in matrix_filters_and_items_json["matrixFilters"]) {
        let matrix_filter_data = matrix_filters_and_items_json["matrixFilters"][matrix_filter_uuid];
        let MatrixFilterClass = MATRIX_FILTER_CLASSES[matrix_filter_data.type];

        let matrix_filter = new MatrixFilterClass(self.form_element, matrix_filter_uuid, matrix_filter_data.type, matrix_filter_data.name, matrix_filter_data.weight, matrix_filter_data.allowMultipleValues);

        MATRIX_FILTERS[matrix_filter_uuid] = matrix_filter;
      }

      let items = matrix_filters_and_items_json["items"];

      // instantiate matrix items (tree nodes)
      for (let i = 0; i < items.length; i++) {
        let item = items[i];
        let matrix_item = new MatrixItem(item.uuid, item.name, item.taxon, item.maxPoints, self.form_element);
        MATRIX_ITEMS[matrix_item.uuid] = matrix_item;

        // add MatrixFilterSpaces to matrix filters and to matrix items
        for (let matrix_filter_uuid in item["space"]) {

          let spaces = item["space"][matrix_filter_uuid];
          let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];

          for (let s = 0; s < spaces.length; s++) {
            let parsed_space = spaces[s];
            let matrix_filter_space = matrix_filter.add_matrix_filter_space(parsed_space);
            matrix_item.add_matrix_filter_space(matrix_filter_space);

            // bind evaluation to MatrixFilterSpace.post_change
            matrix_filter_space.post_activation = function(){
              self.evaluate_identification();
            }
          }
        }

      }

      self.bind_dom_elements_to_matrix_filters();

      // apply restrictions - AFTER instantiating MatrixItems. MatrixItems fill
      for (let matrix_filter_uuid in matrix_filters_and_items_json["matrixFilters"]) {
        let data = matrix_filters_and_items_json["matrixFilters"][matrix_filter_uuid];
        let restrictions = data["restrictions"] || {};

        let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];
        matrix_filter.apply_restrictions(restrictions);
      }

      // add matching and mismatching matrix_items to MatrixFilterSpace instances
      for (let matrix_filter_uuid in MATRIX_FILTERS){
        let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];

        for (let space_identifier in matrix_filter.matrix_filter_spaces){
          let matrix_filter_space = matrix_filter.matrix_filter_spaces[space_identifier];

          for (let matrix_item_uuid in MATRIX_ITEMS){
            let matrix_item = MATRIX_ITEMS[matrix_item_uuid];
            
            let space_contained_in_item = false;

            if (matrix_item.matrix_filter_spaces.hasOwnProperty(matrix_filter.uuid)){
              if (matrix_item.matrix_filter_spaces[matrix_filter.uuid].hasOwnProperty(space_identifier)){
                space_contained_in_item = true;
              }
            }

            if (space_contained_in_item == true){
              matrix_filter_space.register_matching_matrix_item(matrix_item);
            }
            else {
              matrix_filter_space.register_mismatching_matrix_item(matrix_item);
            }

          }

        }
      }

      // if the user comes from using the back button, activate all checked MatrixFilterSpaces
      // this has to be done at the end ofinitialization, so the MatrixFilterSpaces can signal/notify MatrixItems, which leads to the MatrixItems updateing their points
      for (let matrix_filter_uuid in MATRIX_FILTERS){
        let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];

        for (let space_identifier in matrix_filter.matrix_filter_spaces){
          let matrix_filter_space = matrix_filter.matrix_filter_spaces[space_identifier];

          if (matrix_filter_space.input_element != null && matrix_filter_space.input_element.checked == true){
            // the input might be checked on initialization, e.g. when the page is rendered from history using the back button
    
            matrix_filter_space.activate();
    
          }
        }
      }

      if (typeof onFinished == "function"){
        onFinished();
      }

    });
  }

  bind_dom_elements_to_matrix_filters() {

    // horizontal sliders
    // checkboxes are multiselect, ranges are single select
    var inputs = this.form_element.querySelectorAll("input[type=radio], input[type=checkbox], input[type=range]");

    for (let i = 0; i < inputs.length; i++) {
      let input = inputs[i];

      let matrix_filter_uuid = input.name;
      let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];
      matrix_filter.bind_input_element(input);
    }

  }

  deactivate_all_matrix_filters() {
    for (let matrix_filter_uuid in MATRIX_FILTERS){
      let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];
      matrix_filter.reset();
    }
  }

  set_mode (mode){
    console.log("[IdentificationMatrix] changing mode to " + mode);
    IDENTIFICATION_MODE = mode;
    this.reset();
  }

  reset() {
    this.deactivate_all_matrix_filters();
    this.reset_all_matrix_items();
    this.form_element.reset();
    this.send_reset_event();
  }

  reset_all_matrix_filters() {
    for (let matrix_filter_uuid in MATRIX_FILTERS) {
      let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];
      matrix_filter.reset();
    }
  }

  reset_all_matrix_items() {
    for (let matrix_item_uuid in MATRIX_ITEMS) {
      let matrix_item = MATRIX_ITEMS[matrix_item_uuid];
      matrix_item.reset();
    }
  }

  send_reset_event() {
    const reset_event = new Event("reset");

    this.form_element.dispatchEvent(reset_event);
  }

  // reset all items, reload from data
  reload () {

    if (this.DEBUG == true){
      console.log("[IdentificationMatrix] reloading data");
    }

    var self = this;

    MATRIX_FILTERS = {};
    MATRIX_ITEMS = {};
    this.init(function(){

      // make all MatrixFilterSpaces possible
      for (let matrix_filter_uuid in MATRIX_FILTERS){
        let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];
        for (let space_identifier in matrix_filter.matrix_filter_spaces){
          let matrix_filter_space = matrix_filter.matrix_filter_spaces[space_identifier];
          matrix_filter_space.send_possible_event();
        }
      }

      self.reset();
    });

  }

  destroy () {
    MATRIX_FILTERS = {};
    MATRIX_ITEMS = {};
  }

  // events when identification has finished
  // check if all matrix filters have a selection
  // also check if those matrix filters, which have no selection have spaces which can be activated
  evaluate_identification () {

    if (this.DEBUG == true){
      console.log("[IdentificationMatrix] evalutating identification");
    }

    let all_filters_have_selection = true;

    for (let matrix_filter_uuid in MATRIX_FILTERS){
      let matrix_filter = MATRIX_FILTERS[matrix_filter_uuid];

      let matrix_filter_has_selection = false;
      let matrix_filter_has_selectable_space = false;

      if (matrix_filter.status == STATUS_INACTIVE){
        matrix_filter_has_selection = true;
        continue;
      }
      else {

        // this does not work with ranges. the user can select a value that is not within any given range.
        // simply check if the range slider has been set
        
        if (matrix_filter.matrixFilterType == "RangeFilter"){
          if (matrix_filter.input_element.value.length != 0){
            matrix_filter_has_selection = true;
          }
        }
        else {

          // check for selection
          for (let space_identifier in matrix_filter.matrix_filter_spaces){
            let matrix_filter_space = matrix_filter.matrix_filter_spaces[space_identifier];

            if (matrix_filter_space.status == STATUS_ACTIVE){
              matrix_filter_has_selection = true;
              break;
            }

            // check if there are selectable spaces
            if (matrix_filter_space.is_possible == true){
              matrix_filter_has_selectable_space = true;
            }
          }

        }
      }

      if (matrix_filter_has_selection == false && matrix_filter_has_selectable_space == true){
        all_filters_have_selection = false;
        if (this.DEBUG == true){
          console.log("[IdentificationMatrix] " + matrix_filter.name + " has no selection yet.");
        }
        break;
      }
    }

    if (all_filters_have_selection == true){
      this.send_identification_finished_event();
    }

  }
  // notify the user to select the next identification step
  send_identification_finished_event (){
    // strict mode always ends with 100%
    // send event when every VISIBLE matrix filter has one selection
    // use MatrixFilter.active_matrix_filter_spaces{}
    if (this.DEBUG == true){
      console.log("[IdentificationMatrix] sending identification-finished event");
    }
    const event_data = {};
    const finished_event = new CustomEvent("identification-finished", event_data);
    
    this.form_element.dispatchEvent(finished_event);
  }

  get_nature_guide_item (matrix_item_uuid){
    var matched_nature_guide_item = null;

    for (let i=0; i<this.data.items.length; i++){
      let nature_guide_item = this.data.items[i];
      if (nature_guide_item.uuid == matrix_item_uuid){
        matched_nature_guide_item = nature_guide_item;
        break;
      }
    }

    return matched_nature_guide_item;
  }

}