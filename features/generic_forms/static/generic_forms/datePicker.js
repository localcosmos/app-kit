"use strict";
// same .js file as in app, except template_name

/*
_minDate, _* are Date objects
minDate, * are atomized 
*/

window.datePicker = {
	template_name : "", // this differs from the app
	template : null,
	_minDate : new Date(0), // default
	minDate : null, // atomized
	_maxDate : new Date(), //default
	maxDate : null, // atomized
	_date : new Date(), //default date of this object
	date : null, // atomized
	selects : {},

	_load_options : function(options){
		var self = datePicker;

		self.options = options;

		if (options.minDate){
			self._minDate = options.minDate;
		}

		if (options.maxDate){
			self._maxDate = options.maxDate;
		}

		if (options.date){
			self._date = options.date;
			self.date = self._atomize(self._date);
		}

		if (options.template_name){
			self.template_name = options.template_name;
		}

	},

	show : function(options, onsuccess, onerror){

		var self = datePicker; // do not use "this"

		self.onsuccess = onsuccess;
		self.onerror = onerror;
		
	
		// there is always only one datepicker
		// the datePicker object will be used to read th time currently set
		self._reset();

		self._load_options(options);

		// on the browser open a modal page with inputs
		self._load_template(function(){

			var context = self._build_context();

			var html = self.template(context);
			var title = _("SelectDateTime");

			self._show(html, title);
			self._post_show();
			
		});

	},

	manage_only_inputs : function(options, container){
		var self = datePicker;

		self._reset();
		self._load_options(options);
		self.popup_container = container;
		self._post_show();
		self._reload_all_parts();
		self._update_inputs();
	},

	_show : function(html, title){
		ModalDialog.open(html, title);
		// make self.popup_container available, used in post_show
		self.popup_container = ModalDialog.content;
	},

	_post_show : function(){
		var self = datePicker;

		// after showing the picker, add event listeners
		var selects = self.popup_container.querySelectorAll("select");

		for (var s=0; s<selects.length; s++){
			var select = selects[s];

			self.selects[select.getAttribute("data-datepart")] = select;

			select.addEventListener("change", function(event){
				var datepart = event.target.getAttribute("data-datepart");

				self.date[datepart] = event.target.value;

				if (self.options.mode == "datetime"){
					var parts = ["year", "month", "day", "hours", "minutes"];
				}
				else if (self.options.mode == "date"){
					var parts = ["year", "month", "day"];
				}
				else if (self.options.mode == "time"){
					var parts = ["hours", "minutes"];
				}

				for (var p=parts.indexOf(datepart)+1; p<parts.length; p++){
					self._reload_part(parts[p]);
				}
			});
		}
	},

	_reload_all_parts : function(){
		var self = datePicker;
		var parts = ["month", "day", "hours", "minutes"];
		for (var p=0; p<parts.length; p++){
			self._reload_part(parts[p]);
		}
	},

	_build_context : function(){
		var self = datePicker;

		var context = {
			date : true,
			time: false
		};

		// decide which inputs to show
		if (self.options.mode == "datetime"){
			context.date = true;
			context.time = true;
		}
		else if (self.options.mode == "time"){
			context.date = false;
			context.time = true;
		}
		else if (context.mode == "date"){
			context.date = true;
			context.time = false;
		}

		if (context.date == true){
			context["years"] = self._get_year_options();
			context["months"] = self._get_month_options();
			context["days"] = self._get_day_options();
		}

		if (context.time == true){
			context["hours"] = self._get_hours_options();
			context["minutes"] = self._get_minutes_options();
		}

		return context;

	},

	_load_template : function(callback){
		var self = datePicker;

		if (self.template == null){
			ajax.GET(self.template_name, {}, function(template){
				self.template = Handlebars.compile(template);
				callback();
			});	
		}
		else {
			callback();
		}
	},

	_get_input_date : function(){
		var self = datePicker;

		// var d = new Date(year, month, day, hours, minutes, seconds, milliseconds);
		var hours = 0;
		var minutes = 0;

		if ("hours" in self.selects) {
			hours = self.selects.hours.value;
		}

		if ("minutes" in self.selects) {
			minutes = self.selects.minutes.value;
		}	

		var selectedDate = new Date(self.selects.year.value, self.selects.month.value - 1, self.selects.day.value, hours, minutes, 0,0);

		return selectedDate;

	},

	accept: function(){

		var self = datePicker; // do not use "this"

		ModalDialog._close();

		var selectedDate = self._get_input_date();

		self.onsuccess(selectedDate);
	},

	close : function(){

		var self = datePicker; // do not use "this"

		ModalDialog._close();
		if (self.onerror == "function"){
			self.onerror();
		}

	},
	_update_inputs : function(){
		// sets inputs to self.date
		var self = datePicker;
		
		for (var key in self.selects){
			console.log(self.date[key])
			self.selects[key].value = self.date[key];
		}
	},

	_reload_part : function(part_name){

		var self = datePicker; // do not use "this"

		var fn_name = "_get_" + part_name + "_options";

		var entries = datePicker[fn_name]();

		var select = self.selects[part_name];

		// first cut if options are longer than entries
		if (select.options.length > entries.length){

			// if the selected value is out of bounds, pull it into bounds
			if (select.options.selectedIndex + 1 > entries.length){
				select.options.selectedIndex = entries.length -1;
			}

			for (var i=select.options.length; i>entries.length; i--){
				select.options.remove(i-1);
			}
		}

		// iterate over all months/days/... and check with select
		for (var e=0; e<entries.length; e++){
			if (e >= select.options.length){
				var option = document.createElement("option");
				option.value = entries[e][part_name];
				option.textContent = entries[e][part_name];
				select.options.add(option);
			}
		}		

	},

	_reset : function(){

		var self = datePicker; // do not use "this"

		self._minDate = new Date(0);
		self.minDate = self._atomize(self._minDate);
		self._maxDate = new Date();
		self.maxDate = self._atomize(self._maxDate);
		self._date = new Date();
		self.date = self._atomize(self._date);
	},

	_get_year_options : function(){

		var self = datePicker; // do not use "this"

		// compare minDate and maxDate

		var years = [];

		for (var y=self.minDate.year; y<=self.maxDate.year; y++){
			var year = {
				"year": y,
				"selected" : false
			};

			if (y == self.date.year){
				year.selected = true;
			}
			years.push(year);
		}
		return years;
	},

	_get_month_options : function(){

		var self = datePicker; // do not use "this"

		// compare minDate and maxDate
		// months only are restricted if current year equals minyear or maxyear

		var minMonth = 1,
			maxMonth = 12;

		// adjust maxMonth
		if (self.date.year >= self.maxDate.year){
			maxMonth = self.maxDate.month;
		}

		if (self.date.year <= self.minDate.year){
			minMonth = self.minDate.month;
		}

		var months = [];
		for (var m=minMonth; m<=maxMonth; m++){
			var month = {
				"month" : m,
				"selected" : false
			};
			if (m == self.date.month){
				month.selected = true;
			}
			months.push(month);
		}
		return months;
	},

	_get_day_options : function(){

		var self = datePicker; // do not use "this"

		var maxDay = self._daymap[self.date.month.toString()],
			minDay = 1;

		// adjust maxDay
		if (self.date.year >= self.maxDate.year && self.date.month >= self.maxDate.month){
			maxDay = self.maxDate.day;
		}

		// adjust minDay
		if (self.date.year <= self.minDate.year && self.date.month <= self.minDate.month){
			minDay = self.minDate.day;
		}

		var days = [];

		for (var d=minDay; d<=maxDay; d++){
			var day = {
				"day" : d,
				"selected" : false
			};

			if (d == self.date.day){
				day.selected = true;
			}

			days.push(day);
		}

		return days;
	},

	_get_hours_options : function(){

		var self = datePicker; // do not use "this"

		var minHour = 0,
			maxHour = 23;

		// adjust maxHour
		if (self.date.year >= self.maxDate.year && self.date.month >= self.maxDate.month && self.date.day >= self.maxDate.day){
			maxHour = self.maxDate.hours;
		}

		// adjust minHours
		if (self.date.year <= self.minDate.year && self.date.month <= self.minDate.month && self.date.day <= self.minDate.day){
			minHour = self.minDate.hours;
		}


		var hours = [];

		for (var h = minHour; h<=maxHour; h++){
			var hour = {
				"hours" : h,
				"selected" : false
			};

			if (h == self.date.hours){
				hour.selected = true;
			}

			hours.push(hour);
		}

		return hours;

	},

	_get_minutes_options : function(){

		var self = datePicker; // do not use "this"

		var minMinute = 0,
			maxMinute = 59;

		if (self.date.year >= self.maxDate.year && self.date.month >= self.maxDate.month && self.date.day >= self.maxDate.day && self.date.hours >= self.maxDate.hours){
			maxMinute = self.maxDate.minutes;
		}

		if (self.date.year <= self.minDate.year && self.date.month <= self.minDate.month && self.date.day <= self.minDate.day && self.date.hours <= self.maxDate.hours){
			minMinute = self.minDate.minutes;
		}

		var minutes = [];

		for (var m = minMinute; m<=maxMinute; m++){
			var minute = {
				"minutes" : m,
				"selected" : false
			};

			if (m == self.date.minutes){
				minute.selected = true;
			}
			
			minutes.push(minute);
		}

		return minutes;

	},
	// map month to last day of each month
	_daymap : {
		"1" : 31,
		"2" : 29,
		"3" : 31,
		"4" : 30,
		"5" : 31,
		"6" : 30,
		"7" : 31,
		"8" : 31,
		"9" : 30,
		"10" : 31,
		"11" : 30,
		"12" : 31
	},

	_atomize : function(date){
		var atomized = {
			"year" : date.getFullYear(),
			"month": date.getMonth() + 1,
			"day" : date.getDate(),
			"hours" : date.getHours(),
			"minutes" : date.getMinutes()
		};
		return atomized;
	}
};

