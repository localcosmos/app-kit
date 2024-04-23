"use strict";
/* ORM */
/* ModelInterface: Prototype for QUERY BUILDERS like SQLModelInterface */
// construct strings for querying databases, return as string
// this will be attached as Modelname.objects
// every .objects() call creates a new interface
// if .objects was used without (), filters() have to reset this.filters
// and all othr params needed a reset somehow
var ModelInterface = {
	
	// private function attached to the Model object as .objects
	_create : function(modelname, db_identifier){
		var self = Object.create(this);
		// the following properties are independant from prototype
		self.db_identifier = db_identifier;
		self.modelname = modelname;
		self.filters = {};
		self.excludes = {};
		self.values = [];
		self.order_by = null;
		self.query_offset = null;
		self.query_limit = null;
		return self;
	},
	filter : function(new_filters){
		for (var key in new_filters){
			this.filters[key] = new_filters[key];
		}
		return this;
	},

	exclude : function(new_excludes){
		for (var key in new_excludes){
			this.excludes[key] = new_excludes[key];
		}
		return this;
	},

	all : function(callback){
		if (typeof callback == "function"){
			this.fetch(callback);
		}
		else {
			return this;
		}
	},

	offset : function(offset){
		this.query_offset = offset;
		return this;
	},
	
	limit : function(limit){
		this.query_limit = limit;
		return this;
	},

	order_by : function(str){
		this.order_by = str;
		return this;
	},
	_error_handler : function(error){
		try {
			alert("Error " + JSON.stringify(error));
		}
		catch (e){
			alert(error);
		}
	},

	_reset : function(){
		// reset filters, excludes etc.
		this.filters = {};
		this.excludes = {};
		this.order_by = null;
		this.query_offset = null;
		this.query_limit = null;
	},

	// currently, this only support fk fetching one level down
	// object_data is a dictionary{}
	_result_to_model_instance : function(object_data, callback){

		var self = this;

		Model = window[self.modelname];

		each(object_data, function(field_name, value, iterate){

			if (Model.fields.hasOwnProperty(field_name) && value != null){

				// perform a type check
				// model_field is the field how it has been defined in models.js
				var model_field = Model.fields[field_name];

				var fieldClass = model_field.fieldClass;
				var parse_method = "" + fieldClass + "_to_javascript";

				if (typeof self[parse_method] == "function"){
					self[parse_method](model_field, value, function(parsed_value){
						object_data[field_name] = parsed_value;
						iterate();
					});
				}
				else {
					object_data[field_name] = model_field.to_javascript(model_field, value);
					iterate();
				}	

			}
			else {
				iterate();
			}

		}, function(){

			// run to_javascript
			var model_instance = Model.create(object_data);

			model_instance.storage_location = self.storage_location;
			callback(model_instance);
			
		});
		
	},

	// helpers
	paginate: function(page, per_page){
		return this.offset((page-1)*per_page).limit(per_page);
	},

	/******************************************************************************************
	* implemented objects.* methods
	******************************************************************************************/

	exists: function(onsuccess, onerror){
		throw new Error("[" + this.storage_location + "] .exists is not implemented");
	},

	get: function(onsuccess, onerror){
		throw new Error("[" + this.storage_location + "] .get is not implemented");
	},

	fetch: function(onsuccess, onerror){
		throw new Error("[" + this.storage_location + "] .fetch is not implemented");
	},

	first: function(onsuccess, onerror){
		throw new Error("[" + this.storage_location + "] .first is not implemented");
	},

	count: function(onsuccess, onerror){
		throw new Error("[" + this.storage_location + "] .count is not implemented");
	},

	insert: function(object, onsuccess, onerror){
		throw new Error("[" + this.storage_location + "] .insert is not implemented");
	},

	// update multiple instances
	update: function(filters, values, onsuccess, onerror){
		throw new Error("[" + this.storage_location + "] .update is not implemented");
	},

	// update single instance
	update_instance: function(object_id, values, onsuccess, onerror){
		throw new Error("[" + this.storage_location + "] .update_instance is not implemented");
	},

	// remove multiple
	remove: function(filters, onsuccess, onerror){
		throw new Error("[" + this.storage_location + "] .remove is not implemented");
	},

	// remove single
	remove_instance: function(object_id, onsuccess, onerror){
		throw new Error("[" + this.storage_location + "] .remove is not implemented");
	},

	each : function(onIter, onFinished){
		throw new Error("[" + this.storage_location + "] .each is not implemented");
	}

};

/*
* function to create a Model, "derive" function
* automatically adds primary key "id" column if not set in fields
* automatically creates db_identifier
*/
function Model(prototype, extension, override){

	var object = derive(prototype, extension, override);

	// prevent filling prototype Meta
	object.Meta = clone(object.Meta);

	// auto-add primary key if missing
	var clean_app_label = "" + object.Meta.app_label.split(" ").join("")
	object.db_identifier = clean_app_label + "_" + object.model_name.toLowerCase();

	if (!object.fields.hasOwnProperty(object.Meta.primary_key)){
		object.fields[object.Meta.primary_key] = models.IntegerField({"unique":true, "primary_key":true, "db_column":"id"});
	}

	// autocomplete Fields
	for (var field_name in object.fields) {
		var field = object.fields[field_name];

		// autofill db_column if not defined
		if (!(field.hasOwnProperty("db_column"))) {
			switch (field.fieldClass)
			{
				case "ForeignKey":
					field.db_column = field_name + "_id";
					break;
				default:
					field.db_column = field_name;
			}
		}

		// if a field is foreign key, add the Object_name to Meta.referenced_by of
		// the referenced object
		if (field.fieldClass == "ForeignKey"){
			object.Meta.references.push(field_name);

			// if to_field is not set, it references the primary key
			if (!(field.to_object in window)){
				throw new Error("Model " + field_to_object + " is not defined. Referenced Models have to be defined before the referencing Model");
			}

			if (!field.hasOwnProperty("to_field")){
				field.to_field = window[field.to_object].Meta.primary_key;
			}

			window[field.to_object].Meta.referenced_by.push({"modelname" : object.model_name, "field_db_column": field.db_column, "field_to_field" : field.to_field});

		}

	}

	// currently the "objects" property, which links to models.Manager is added on mango.init_models()

	// add to mango.models - needed for syncdb
	mango.models.push(object.model_name);

	return object;
}

var BaseModel = {

	model_name : null,
	db_identifier : null, // table name or objectstore name

	remote_supported : false, // defines if model.remote_objects is supported. Applies if the same model is defined on both client and server

	Meta : {
		primary_key : "id",
		referenced_by : [],
		references :  [],
		unique_together : [],
		indexes : [],
		app_label : settings.FRONTEND_NAME
	},

	fields : {},
	
	// creates a NEW instance, like app = App(thing=thong) in django would be var app = App.create({"thing":thong});
	create: function(fields){
		// reverse foreign keys need the fkname_set().filter().fetch() functionality
		// reverse relations are stored in model.Meta.referenced_by[]
		// forward foreign keys need instance of object or fk_id param
		// and other checks are still missing...
		var self = Object.create(this);

		var fields = fields || {};

		// disable querying on Model instances
		self.objects = null;

		// iterate over fields in field definition
		for(var field_name in fields){

			// perform a type check
			var value = fields[field_name];

			if (value != null) {

				if (field_name in self.fields) {

					// _field is the field how it has been defined in models.js
					var _field = self.fields[field_name];

					self[field_name] = _field.validate(_field, value);

				}
				else {
					self[field_name] = value;
				}
			}		
			
		}

		// should references be moved to define?
		var references = self.Meta.referenced_by;

		for (var m=0; m<references.length; m++){
			var reference = references[m];
			self[reference.modelname.toLowerCase() + "_set"] = function(filters){
				var filters = filters || {};
				if (self.hasOwnProperty(self.primary_key)){

					filters[reference.field_db_column] = self[reference.field_to_field];
					var model_interface = SQLModelInterface.create(mango.db, reference.modelname);
					
					model_interface.filter(filters);

					return model_interface;
				}
				else {
					throw new Error("ERROR: cannot lookup reverse relations on a non-saved object");
				}
			}
		}

		self._post_create(self);

		return self;
	},

	_post_create : function(self){	
		// hook
	},

	_get_model_route: function(self){
		if (self.storage_location == "RemoteDB"){
			return "remote_objects";
		}
		return "objects";
	},

	// async
	save : function(self, callback) {

		var model_route = self._get_model_route(self);

		// update OR inserts a single instance

		//.objects is the interface
		
		// values to store in the db
		// some values need to be parsed, stringified etc
		// self.to_db is called to transform the value
		var values = {};

		for (var key in self.fields){
			if (self.hasOwnProperty(key)){
				// if it is a foreign key, _id is appended to the key, alongside the model instance reference
				var field = self.fields[key];

				// do not use to_db to store image files on the device. Image files might just be uploaded
				values[key] = field.to_db(field, self[key]);
			}
		}

		var primary_key = self.Meta.primary_key;

		if(values.hasOwnProperty( primary_key )){

			var object_id = values[primary_key];

			// do not pass the id as an update param, id is set by db and never changed/updated
			delete values[primary_key];
			
			window[self.model_name][model_route].update_instance(object_id, values, callback);
		}
		else {
			window[self.model_name][model_route].insert(values, function(created_obj){
				// sync model field values with database values
				for (var key in created_obj){
					// parse the values from db to fit javascript
					// e.g. JSONField
					if (self.fields.hasOwnProperty(key)){
						var field = self.fields[key];
						self[key] = field.to_javascript(field, created_obj[key]);
					}
					else {
						self[key] = created_obj[key];
					}
				}

				if (typeof callback == "function"){
					callback(self);
				}
			});
		}
	},
		
	remove : function (self, callback) {

		var model_route = self._get_model_route(self);

		var primary_key = window[self.model_name].Meta.primary_key;

		if (self.hasOwnProperty(primary_key)){
			var object_id = self[primary_key];

			window[self.model_name][model_route].remove_instance(object_id, callback);
		}
		else {
			if (typeof callback == "function"){
				callback();
			}
		}
	}
};


var ModelField = {

	fieldClass : null,

	// if a value is stored in the db it might need to undergo a type change
	to_db : function(self, value){
		return value;
	},

	// if a value is read from the db it might need to undergo a type change
	to_javascript : function(self, value){
		return value;
	},

	// validate a value of a model field
	validate : function(self, value){
		return value;
	},

	formfield : function(self, kwargs){

		if (self.hasOwnProperty("choices")){
			kwargs["choices"] = self.choices;
			return forms.ChoiceField(kwargs);
		}
		else {
			return forms[self.fieldClass](kwargs);
		}
	},

	value_from_object : function(self, object, field_name){
		if (object.hasOwnProperty(field_name)){
			return object[field_name];
		}
		return '';
	}
};

var models = {
	Model : BaseModel
};

models.CharField = function(kwargs){
	var field = derive(ModelField, {
		"fieldClass" : "CharField",
		"validate" : function(self, value){
			if (isChar(value)){
				return value.toString();
			}
			else {
				throw new TypeError("ERROR: models.CharField expected string, not " + typeof(value) + "(" + value + ")");
			}
		}
	}, kwargs);

	return field;
};

models.IntegerField = function(kwargs){
	var field = derive(ModelField, {
		"fieldClass" : "IntegerField",
		"validate" : function(self, value){
			if (isInt(value)) {
				return parseInt(value);
			}
			else {
				throw new TypeError("ERROR: models.IntegerField expected Integer, not " + typeof(value) + "(" + value + ")");
			}
		} 
	}, kwargs);

	return field;
};

models.FloatField = function(kwargs){
	var field = derive(ModelField, {
		"fieldClass" : "FloatField",
		"validate" : function(self, value){
			if (isFloat(value)){
				return parseFloat(value);
			}
			else {
				throw new TypeError("ERROR: models.FloatField expected Float, not " + typeof(value) + "(" + value + ")");
			}
		}
	}, kwargs);

	return field;
};

models.DecimalField = function(kwargs){
	var field = derive(models.FloatField, {
		"fieldClass" : "DecimalField"
	}, kwargs);

	return field;
};

models.BooleanField = function(kwargs){
	var field = derive(ModelField, {
		"fieldClass" : "BooleanField",
		"validate" : function(self, value){
			if (isBool(value)){
				return parseBool(value);
			}
			else {
				throw new TypeError("ERROR: models.BooleanField expected Boolean, not " + typeof(value) + "(" + value + ")");
			}
		}
	}, kwargs);

	return field;
};

/* accepts Date object, which is casted to unixtime for the db */
models.DateTimeField = function(kwargs){
	var field = derive(ModelField, {
		"fieldClass" : "DateTimeField",
		"validate" : function(self, value){
			if (!(value instanceof Date)){

				try {
					value = new Date(value);
				}
				catch (e) {
					throw new TypeError("ERROR: models.DateField expected value of type Date or string(ISO formatted), not " + typeof(value) + "(" + value + ")");
				}
			}
			return value;
		},
		// if a value is stored in the db it might need to undergo a type change
		"to_db" : function(self, value){
			// expects Date object, returns ISO 8601 string
			return value.toISOString();
		},

		// if a value is read from the db it might need to undergo a type change
		"to_javascript" : function(self, value){
			// it has to be of type Date
			if (!(value instanceof Date)){
				value = new Date(value);
			}
			return value;
		}
	}, kwargs);

	return field;
};

models.ForeignKey = function(model, kwargs){

	var kwargs = kwargs || {};
	kwargs["to_object"] = model.model_name;
	
	var field = derive(ModelField, {
		"fieldClass" : "ForeignKey",
		"validate" : function(self, value){
			if (Object.getPrototypeOf(value) === window[self.to_object] ){
				return value;				
			}
			else {
				throw new TypeError("ERROR: models.ForeignKey has to be an instance of " + self.to_object);
			}
		}/*,

		to_db : function(self, value){
			return value.id;
		}*/

	}, kwargs);

	return field;
};

models.JSONField = function(kwargs){
	var field = derive(ModelField, {
		"fieldClass" : "JSONField",
		"to_db" : function(self, value){
			if (typeof value != "string"){
				return JSON.stringify(value);
			}
			return value;
		},
		"to_javascript" : function(self, value){
			if (typeof value != "object"){
				return JSON.parse(value);
			}
			return value;
		},
		"validate" : function(self, value){
			// make sure the value is parsed
			if (typeof value != "object"){
				throw new TypeError("ERROR: models.JSONField has to be dict/object, not " + typeof(value));
			}
			return value;
		}
	}, kwargs);

	return field;
};


models.UUIDField = function(kwargs){
	var field = derive(ModelField, {
		"fieldClass" : "UUIDField",
		"validate" : function(self, value){
			// regex /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

			var pattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
			if (pattern.test(value) != true) {
				throw new TypeError("ERROR: models.UUIDField expected a valid uuid, not " + value);
			}

			return value;
		}
	}, kwargs);

	return field;
};

// value of an imagefield is a FlexFile instance
var FlexFile = {
	_create : function(file_data, filename){
		// file_data can be a blob or a URL
		var self = Object.create(this);

		self._blob = null; // a Blob instance
		self._url = null; // a string

		self.filename = filename;

		if (file_data instanceof Blob){
			self._blob = file_data;
		}
		else if (typeof file_data === "string" || file_data instanceof String){
			self.filename = file_data.split("/").pop();
			self._url = file_data;
		}
		else if (file_data instanceof File){
			// usually, File implements Blob
			// sometimes (cordova) file_data instanceof File can be true, but file_data instanceof Blob can be false at the same time
			self._blob = file_data;
		}
		else {
			throw new TypeError("FlexFile has to be instantiated with one of the following datatypes: [Image/Blob/String(url)]")
		}

		return self;

	},

	create : function(file_data, filename){
		var self = this._create(file_data, filename);
		return self;
	},
	
	// convert a Blob or a File to URL
	url : function(callback){

		var self = this;

		if (self._url === null){
			alert("blob to url not implemented")

		}
		else {
			callback(self._url);
		}
	},

	// convert url or Blob to File
	// File implements Blob
	// a File instance is a Blob instance, but a Blob instance is not a File instance
	file : function(callback){

		var self = this;

		if (self._blob === null){
			// url to blobonly works on local filesystems
			if (device.platform == "browser"){
				alert("url to file not implemented on browser");
			}
			else {
				FileUtil.get(self._url, function(file){
					self._blob = file;
					callback(file);
				});
			}
		}
		else {
			if (self._blob instanceof File == true){
				callback(self._blob);
			}
			else {
				if (self._blob instanceof Blob == true && device.platform == "iOS"){
					// using new File(self._blob, self.filename); or new File([self._blob], self.filename); does not work on ios:
					// fileinstance,name is not of type string then, and FileWriter cannot digest this fileinstance on ios
					// furthermore, you cannot set Blob.name programmatically on iOS
					// therefore, just return self._blob
					callback(self._blob);
				}
				else {
					alert("only Blob instances can be converted to File");
				}
			}
		}

	},

	// usually, File implements Blob, So File is also a Blob
	// sometimes (cordova) file_data instanceof File can be true, but file_data instanceof Blob can be false at the same time
	blob : function(callback){

		var self = this;

		if (self._blob === null){
			// url to blobonly works on local filesystems
			if (device.platform == "browser"){
				alert("url to blob not implemented on browser");
			}
			else {
				FileUtil.get(self._url, function(file){

					self._blob = file;

					if (self._blob instanceof Blob == true){
						callback(elf._blob);
					}
					else {
						self._blob_from_file(self._blob, callback);
					}
				});
			}
		}
		else {
			if (self._blob instanceof Blob == true){
				callback(self._blob);
			}
			else {
				self._blob_from_file(self._blob, callback);
			}
		}
	},

	_blob_from_file : function(file, callback){
	
		var self = this;

		var reader = new FileReader();
        reader.onloadend = function() {
            // Create a blob based on the FileReader "result", which we asked to be retrieved as an ArrayBuffer
            var blob = new Blob([new Uint8Array(this.result)], { type: file.type });
			blob.name = self._blob.name;
            callback(blob);
        };
        // Read the file as an ArrayBuffer
        reader.readAsArrayBuffer(file);
	}
};

// FlexImage can be instantiated with an optional set of thumbnails
var FlexImage = derive(FlexFile, {

	create : function(file_data, filename, thumbnails){
		var self = this._create(file_data, filename);

		var thumbnails = thumbnails || {};

		// make self.thumbnail, self.small, self.full_hd etc available
		for (let key in thumbnails){
			self[key] = thumbnails[key];
		}

		return self;
	},

	// image is image.src -> onload callback
	correct_image_orientation : function(image, callback){

        var success = false;
        
        var width = image.width;
        var height = image.height;
        
        var canvas = document.createElement("canvas");
        
        canvas.width = width;
        canvas.height = height;

        var ctx = canvas.getContext("2d");
        
		EXIF.getData(image, function() {

			var orientation = EXIF.getTag(this, "Orientation");

            if (orientation && device.platform == "browser"){

				if (4 < orientation && orientation < 9) {
					canvas.width = height;
					canvas.height = width;
				}

				switch (orientation) {
					case 2:
						ctx.transform(-1, 0, 0, 1, width, 0);
						break;
					case 3:
						ctx.transform(-1, 0, 0, -1, width, height);
						break;
					case 4:
						ctx.transform(1, 0, 0, -1, 0, height);
						break;
					case 5:
						ctx.transform(0, 1, 1, 0, 0, 0);
						break;
					case 6:
						ctx.transform(0, 1, -1, 0, height, 0);
						break;
					case 7:
						ctx.transform(0, -1, -1, 0, height, width);
						break;
					case 8:
						ctx.transform(0, -1, 1, 0, 0, width);
						break;
					default:
						break;
				}

				success = true;

			}
            
            
			if (success == true){
				ctx.drawImage(image, 0, 0, width, height);
				callback(canvas);
			}

		});
        
        if (success == false){
            ctx.drawImage(image, 0, 0, width, height);
            callback(canvas);
        }

	},

	correct_blob_image_orientation : function(blob, callback){

		var self = FlexImage;

		var reader = new FileReader();

		reader.onloadend = function(event){
			var image = new Image();
			
			image.crossOrigin = "Anonymous";

			image.onload = function(){
				
				self.correct_image_orientation(image, function(corrected_canvas){

					// convert canvas to blob
					var new_blob = corrected_canvas.toBlob(function(new_blob){

						new_blob.filename = blob.filename;
						new_blob.name = blob.name;
						callback(new_blob);

					}, 'image/jpeg', 0.95);

				}, function(uncorrected_image){
					callback(blob);
				});

			}
			
			image.onerror = function(event){
				console.log("[FlexImage] failed to correct orientation: " + event);
				callback(blob);
			}

			image.src = reader.result;

		}

		reader.onerror = function(event){
			console.log("[FlexImage] failed to read image blob with FileReader: " + event);
			callback(blob);
		}

		reader.readAsDataURL(blob);

	}
});

// to_db passes the default value type (FlexImage) to the modelinterface
models.ImageField = function(kwargs){

	var field = derive(ModelField, {
		"fieldClass" : "ImageField",
		"validate" : function(self, value){
			if (FlexImage.isPrototypeOf(value) == false){
				throw new TypeError("ERROR: models.ImageField expected FlexImage instance, not " + value);
			}
			/*
			if (value instanceof File == false){
			
				var pattern = /\.(gif|jpg|jpeg|png)$/i;

				if (pattern.test(value) != true) {
					throw new TypeError("ERROR: models.ImageField expected jpg, png or gif, not " + value);
				}
			}*/

			return value;
		},
		"to_javascript" : function(self, value){
			// value is most likely a url
			if (FlexImage.isPrototypeOf(value) == false){
				return FlexImage.create(value);
			}
			return value;
		},

		"thumbnails" : {}

	}, kwargs);

	return field;

}
