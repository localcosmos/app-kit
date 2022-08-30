"use strict";

/* SQLITE implementation */
var SQLite = derive(Database, {

	init : function(){

		var database_settings = mango.get_database_settings();

		var dbImplementation = database_settings["ENGINE"].split(".")[1];


		if (dbImplementation == "sqliteplugin"){
			// this is the SQLite plugin of cordova
			this.db = window.sqlitePlugin.openDatabase({name: database_settings["NAME"], location: 'default'});
		}
		else if (dbImplementation == "websql"){
			// websql is deprecated and currently only should be used as a fallback for Ubuntu where SQLiteplugin is unsupported
			this.db = window.openDatabase(database_settings["NAME"], '' + database_settings["VERSION"], database_settings["NAME"], 5*1024*1024);
		}

	},

	migrate : function(migratedCB){

		console.log("[SQLite.js] starting sync");

		var self = this;
			
		function createTable(model, tablename, modelname, createdTableCB){
		
			console.log('[SQLite.js] creating table ' + tablename);

			// map
			var fieldmapping = {
				"IntegerField" : "INTEGER",
				"FloatField" : "REAL",
				"BooleanField" : "BOOLEAN",
				"DateField" : "DATE",
				"DateTimeField" : "DATETIME",
				"TextField" : "TEXT",
				"CharField" : "TEXT",
				"UUIDField" : "TEXT",
				"JSONField" : "TEXT",
				"ImageField" : "TEXT" // local filsystem
			};

			var sql_values = [];

			var primary_key = model.fields[model.Meta.primary_key];
	
			var sql_head = "CREATE TABLE IF NOT EXISTS " + tablename + " ( " + primary_key.db_column + " " + fieldmapping[primary_key.fieldClass] + " PRIMARY KEY",
				sql_inner = "",
				sql_tail = ");";
			
			// SQLITE uses ROWID by default, usually AUTOINCREMENT is not necessary, see https://www.sqlite.org/autoinc.html
			if (primary_key.hasOwnProperty("autoIncrement") ) {
				sql_head = sql_head + " AUTOINCREMENT ";
			}
		  
			if (typeof model.Meta.primaryKeyExtraSQL == "string"){
				sql_head = sql_head + " " + model.Meta.primaryKeyExtraSQL;
			}
		
			sql_head = sql_head + ",";

			// model.fields is a dictionary {}
			for (var column_name in model.fields){

				var model_field = model.fields[column_name];

				if (column_name == model.Meta.primary_key){
					continue;
				}
				else if (model_field.fieldClass == "ForeignKey"){
					if (!(model_field.hasOwnProperty("to_field"))){
						model_field.to_field = window[model_field.to_object].Meta.primary_key;
					}

					if (model_field["null"] != true) {
						var nullable = "NOT NULL";
					}
					else {
						var nullable = "";
					}
					
					// get the datatype from the model
					var fk_datatype = fieldmapping[window[model_field.to_object].fields[model_field.to_field].fieldClass];

					var constraint_name = column_name + "_" + column_name + "_fk";
					sql_inner = "" + model_field.db_column + " " + fk_datatype + " " +  nullable + " CONSTRAINT " + constraint_name + " REFERENCES " + window[model_field.to_object].db_identifier +  "(" + model_field.to_field + "),";
				}
				else {
					sql_inner = sql_inner + " " + model_field.db_column + " " + fieldmapping[model_field.fieldClass];

					if (model_field["null"] != true) {
						sql_inner = sql_inner + " NOT NULL";
					}
				
					if (model_field["default"] !== null && typeof model_field["default"] !== "undefined"){
						if (model_field.fieldClass == "BooleanField"){
							if (model_field["default"] == false){
								model_field["default"] = 0;
							}
							else {
								model_field["default"] = 1;
							}
						}
						
						if (model_field.fieldClass == "CharField" || model_field.fieldClass == "TextField"){
							sql_inner = sql_inner + " DEFAULT " + "'" + model_field["default"] + "' ";
						}
						else {
							sql_inner = sql_inner + " DEFAULT " + model_field["default"];
						}
					}

					if ("unique" in model_field  && model_field["unique"] == true){
						sql_inner = sql_inner + " UNIQUE ";
					}
				
					if (typeof model_field.extraSQL == "string") {
						sql_inner = sql_inner + " " + model_field.extraSQL;
					}
				
					sql_inner = sql_inner + ",";

				}
			}

			//add unique_togethers to sql_inner
			if (model.Meta.unique_together.length > 0){
				// it can be a list or a list of lists
				var unique_together = model.Meta.unique_together;

				function append_unique_together(list){

					var uniqueCols = [];
					
					for (var f=0; f<list.length; f++){
						var field_name = list[f];
						// get the db_column
						uniqueCols.push(model.fields[field_name].db_column);
					}

					var unique_string = " UNIQUE(" + uniqueCols.join() + "),";
					sql_inner = sql_inner + unique_string;
					
				}

				if (typeof unique_together[0] == "list"){
					for (var l=0; l<unique_together.length; l++){
						append_unique_together(unique_together[l]);
					}
				}
				else {
					append_unique_together(unique_together);
				}
				
			}
		
			if (sql_inner[sql_inner.length-1] == ",") {
				sql_inner = sql_inner.substring(0, sql_inner.length - 1);
			}
		
			var sql_query = sql_head + sql_inner + sql_tail;
		
			/* run the query */

			SQLite.db.transaction(function(tx){
			
				console.log(sql_query);
			
				tx.executeSql(sql_query, [], function (tx, result) {
					//console.log(JSON.stringify(result));
					createIndexes(model, tablename, modelname, createdTableCB);
				},
				SQLite.error_handler);

			}, SQLite.error_handler, function() {
				console.log('Successfully created table ' + tablename);
			});
		
		}
	
		function createIndexes(model, tablename, modelname, createdIndexesCB){
		
			console.log('creating indexes');

			var indexKeys = [];
			var indexCount = 0;

			for (var key in model.Meta.indexes) {
			    indexKeys.push(key);
			    indexCount++;
			}
	
			function createIndexesLoop(){
			
				indexCount--;
			
				if (indexCount >=0) {
				
					var indexKey = indexKeys[indexCount];
					var index = model.Meta.indexes[indexKey];

					var indexCols = index.keyPath;
				
					if (typeof indexCols !== "string") {
						indexCols = indexCols.join();
					}
				
					var indexName = modelname + "_" + index.name; //sql only prepend
				
					var sql_query = "CREATE INDEX IF NOT EXISTS " + indexName + " ON " + modelname + "(" + indexCols + ")";
				
					console.log(sql_query);
					/* run the query */
					SQLite.db.transaction(function(tx){
					
						console.log(sql_query);
					
						tx.executeSql(sql_query, [], function (tx, result) {
							//console.log(JSON.stringify(result));
							createIndexesLoop();
						},
						SQLite.error_handler);
					});
				
				}
				else {
					console.log('finished creating indexes');
					createdIndexesCB();
				}
			
			}
		
			createIndexesLoop();
	
		}

		// iterate over all models and creat the tables if necessary
		each(mango.models, function(modelname, iterate){

			console.log("[SQLiteDB] syncing " + modelname);						

			var model = window[modelname];

			var tablename = model.db_identifier;

			var table_exists = true;

			// iterate after the transactoin has been closed
			SQLite.db.transaction(function(tx){
				
				tx.executeSql("SELECT * FROM sqlite_master WHERE type='table' AND name=?;", [tablename], function (tx, result) {

			    	if (result.rows.length == 0) {
		            	table_exists = false;
		            }
			            
				}, SQLite.error_handler);
			          
			}, SQLite.error_handler, function(){
				if (table_exists == false){
					// create the table
					createTable(model, tablename, modelname, iterate);
				}
				else {
					iterate();
				}
			});

		}, function(){
			console.log("[SQLiteDB] finished migrations");
			if (typeof (migratedCB) == "function"){
				migratedCB();
			}
		});
		
	}

});


// SQLite querying implementation - depends on ModelInterface Object prototype
// translates model functions into SQL strings
// this still needs the feature of detecting foreign keys and convert them into objects
var SQLiteModelInterface = derive(ModelInterface, {

	storage_location : "SQLite",

	create : function(modelname, db_identifier){
		var self = this._create(modelname, db_identifier);
		return self;
	},
	
	// sql_command : string, values: {}, filters: {}
	// some values might need parsing, eg BooleanField is stored as 0 and 1 in SQLite
	_construct_where_part : function(filters){

		var self = this;

		var where = {
			sql : "",
			values_list : []
		};

		if (Object.keys(filters).length > 0){
			var where_parts = [],
				values = [];
	
			for (let key in filters ) {

				var field_name = key;

				if (key == "pk"){
					var field_name = window[self.modelname].Meta.primary_key;
				}

				var where_part = field_name + " = ? ";

				var value = filters[key];

				var Model = window[self.modelname];
				if (Model.fields.hasOwnProperty(field_name)){
					var field_definition = Model.fields[field_name];

					switch (field_definition.fieldClass) {
						case "BooleanField":
							if (value === true){
								value = 1;
							}
							else if (value == false){
								value = 0;
							}
							break;
					}
				}

				where_parts.push(where_part);
				values.push( value );
			}
	
			if (values.length > 0) {
				var where_part = where_parts.join(" AND ");
				var where_sql = " WHERE " + where_part;
			}
	
			where.sql =  where_sql;
			where.values_list = values;
		}
		return where;		

	},

	_apply_limitoffset : function(sql_string){
		if (this.query_limit != null){
			sql_string = sql_string + " LIMIT " + this.query_limit;
		}

		if (this.query_offset != null){
			sql_string = sql_string +  " OFFSET " + this.query_offset;
		}
		return sql_string;
	},

	_execute : function(sql_string, values, onsuccess, onerror){
	
		var self = this;

		var sql_string = this._apply_limitoffset(sql_string);

		// reset filters, excludes etc.
		this._reset();

		console.log(sql_string + " values: " + JSON.stringify(values));

		var tx_error = null;
		var return_results = null;

		SQLite.db.transaction(function(tx) {

            tx.executeSql(sql_string, values, function(tx, results){
				// returning results here breaks DELETE FROM on Android (nested transactions)
				return_results = results;

			},
			function(tx, error){

				tx_error = error;
				console.log("[SQLITE] tx level error: " + error.message);

			});

		}, function(error){
			// transaction error
			if (tx_error != null){
				var error = tx_error;
			}

			if (typeof onerror == "function"){
				onerror(error);
			}
			else {
				self._error_handler(error);
			}

		}, function(){
			// transaction success
			if (tx_error == null){

				if (typeof onsuccess == "function"){
					onsuccess(return_results);
				}

			}
			else {
				var error = tx_error;
				if (typeof onerror == "function"){
					onerror(error);
				}
				else {
					self._error_handler(error);
				}
			}

		});

	},

	_select_sql : function(){
		var where = this._construct_where_part(this.filters);

		var values = this.values.join();
		var values_selector = values ? values : "*";

		var sql_string = "SELECT " + values_selector + " FROM " + this.db_identifier + where.sql;
	
		return {"sql_string" : sql_string, "values_list" : where.values_list};
		
	},

	// INSERT / UPDATE / DELETE
	// convert values to match the database column type, e.g. bool to 0/1 and DateTime values to integer
	// images are received as FlexImage instances. those images are stored locally and the URL to those files is the value
	_parse_column_and_value : function(column, value, callback) {

		var field_definition = window[this.modelname].fields[column];

		if (field_definition.hasOwnProperty("db_column")){
			column = field_definition.db_column;
		}
		else {
			if (field_definition.fieldClass == "ForeignKey"){
				column = column + "_id";
			}
		}

		// read the value
		switch (field_definition.fieldClass){
			case "ForeignKey":
				if (field_definition.hasOwnProperty("to_field")){
					value = value[field_definition.to_field];
				}
				else {
					value = value[window[value.object_type].Meta.primary_key];
				}
				break;
				
			case "BooleanField":
				if (value === false){
					value = 0;
				}
				else if (value === true){
					value = 1;
				}
				break;
			case "DateTimeField":
				if (value == "now"){
					value = new Date().getTime();
				}
				else if (value instanceof Date){
					value = value.getTime();
				}
				break;
			case "IntegerField":
				value = parseInt(value);
				break;
			case "FloatField":
			case "DecimalField":
				value = parseFloat(value);
				break;
		}

		// async
		if (field_definition.fieldClass == "ImageField"){

			function saveNewImageToDisk(){

				// store the image locally and set the url as the value
				// create the defined thumbnails and store them locally
				// eg filename.jpg -> filename_100x100.jpg
				// fileutil .save requires a File instance, not a Blob instance
				value.file(function(file){

					// iOS: Blob instance from form (File implementation is buggy on iOS)
					// Android: File instance from form
					// Blob instances sometimes do not have .name
					// Blob instances from forms supply .filename
					var filename = file.name;

					if (file.hasOwnProperty("filename") && typeof(file.filename) == "string"){
						var filename = file.filename;
					}

					FileUtil.save(field_definition.save_to, filename, file, function(fileEntry){

                        // in the db, a cdvfile:// is stored
						var cdvfilepath = fileEntry.toInternalURL();

						var column_and_value = {
							"db_column" : column,
							"db_value" : cdvfilepath
						};

						var image_filename = fileEntry.name;
                        
						// create all thumbnails
						each(field_definition["thumbnails"], function(thumbnail_name, definition, iterate){

							var thumbnail_config = {
								quality : 0.95,
								maxWidth : definition.size[0],
								maxHeight : definition.size[1],
								imageSize : definition.type
							};

							var thumbnail = Thumbnail.create(thumbnail_config);
                            
                            // thumbnail.as_url creates a file on disk
                            thumbnail.as_url(cdvfilepath, function(thumb_url){

									console.log("[SQLite] thumbnail available at " + thumb_url);
									iterate();

								}, function(e) {
                                alert(JSON.stringify(e));
                                iterate();
                            });

						}, function(){
							callback(column_and_value);
						});

						
					});

				});

			}

			// value is a FlexImage
			// only perform save actions if the file does not yet exist on disk
			if (value._url == null){
				// if the fleximage has been instantiated from db, it has an ._url
				saveNewImageToDisk();
			}
			else {
				// the fleximage has the attribute ._url
				FileUtil.get(value._url, function(file){
					// file does exists, the Model  has been updated, do not save to disk, do not change the db value
					var column_and_value = {
						"db_column" : column,
						"db_value" : value._url
                    };

					callback(column_and_value);

				}, function(e){
					// could not find the file on disk
					// save the file
					saveNewImageToDisk();
				});
			}
			
			
		}
		else {

			var column_and_value = {
				"db_column" : column,
				"db_value" : value
			}

			callback(column_and_value);
		}
	},

	// create a model_instance for each result and run onIter each created model_instance
	_iterateSQLResults : function(results, onIter, onFinished){
		var self = this;

		var count = results.rows.length;
    	
    	console.log("found " + count + " entries");
		
		function iterate(){
			
    		count--;
    		
    		if (count >=0) {
    			var result = results.rows.item(count);
				
				// create the model_instance and run onIter for that instance
				self._result_to_model_instance(result, function(instance){
					onIter(instance, iterate);
				});
        		
    		}
    		else {
    			if (typeof onFinished == "function") {
        			onFinished();
        		}
    		}
    	}
    	
    	iterate();

	},

	_get_last_insert : function(tablename, onsuccess, onerror){

		var self = this;

		var sql = "SELECT last_insert_rowid() AS last_insert_id FROM " + this.db_identifier;

		self._execute(sql, [], function(results){

			var sql_2 = "SELECT * FROM " + tablename + " WHERE ROWID=?";

			self._execute(sql_2, [results.rows.item(0).last_insert_id], function(results_2){
				onsuccess(results_2.rows.item(0));
			}, onerror);


		}, onerror);
		
	},

	/******************************************************************************************
	* parsing values: from db to javascript
	******************************************************************************************/

	ImageField_to_javascript : function(model_field, value, callback){

		var thumbnails = {};

        // thumbnail_name is eg "small" or "hd"
		each(model_field.thumbnails, function(thumbnail_name, definition, iterate){

            // create thumbnail only on demand using Thumbnail.as_url
            var thumbnail_config = {
                quality : 0.95,
                maxWidth : definition.size[0],
                maxHeight : definition.size[1],
                imageSize : definition.type
            };

            var thumbnail = Thumbnail.create(thumbnail_config);

            thumbnail.as_url(value, function(thumb_url){
                
                thumbnails[thumbnail_name] = thumb_url;

                iterate();
                
            }, function(e){
                alert(e.toString());
                iterate();
            });


		}, function(){

            var path_parts = value.split("/");
            var filename = path_parts.pop();
            
			var fleximage = FlexImage.create(value, filename, thumbnails);

			callback(fleximage);

		});
		
	},

	// value is the referenced column, eg "id"
	ForeignKey_to_javascript : function(model_field, value, callback){

		var Model = window[model_field.to_object];

		var model_instance = Model.create({"id" : value});

		callback(model_instance);		

	},


	/******************************************************************************************
	* implemented objects.* methods
	******************************************************************************************/

	// exists immediately executes sql command
	exists : function(onsuccess, onerror){
		//SELECT EXISTS(SELECT 1 FROM myTbl WHERE u_tag="tag" LIMIT 1);
		
		var self = this;
		self.query_limit = 1;
		
		var where = self._construct_where_part(self.filters);
		var sql_string = "SELECT COUNT(*) AS count FROM " + self.db_identifier + where.sql;

		this._execute(sql_string, where.values_list, function(results){
			onsuccess(results.rows.item(0).count);
		}, onerror);

	},

	get : function(filters, onsuccess, onerror){

		var self = this;
		
		var where = this._construct_where_part(filters);
		var sql = "SELECT * FROM " + this.db_identifier + where.sql;
		
		this._execute(sql, where.values_list, function(results){

			if (results.rows.length > 1){
				var error_message = "GET returned " + results.rows.length + " items instead of 1";

				if (typeof onerror == "function"){
					onerror(error_message);
				}
				else {
					self.error_handler(error_message);
				}
			}
			else {		
				self._result_to_model_instance(results.rows.item(0), onsuccess);
			}
		});
		
	},

	fetch : function(onsuccess, onerror){

		var self = this;

		var sql = this._select_sql();
	
		self._execute(sql.sql_string, sql.values_list, function(results){

			var instance_list = [];

			if (results.rows.length > 0){

				self._iterateSQLResults(results, function(instance, iterate_result){
					
					instance_list.push(instance);
					iterate_result();
				}, function(){
					onsuccess(instance_list);
				});

			}
			else {
				onsuccess(instance_list);
			}
		}, onerror);
	},

	first : function(onsuccess, onerror){

		var self = this;

		var sql = this._select_sql();

		var sql_string = sql.sql_string + " LIMIT 1";

		this._execute(sql_string, sql.values_list, function(results){
			if (results.rows.length > 0){
				self._result_to_model_instance(results.rows.item(0), onsuccess);
			}
			else {
				onsuccess(null);
			}
		}, onerror);
		
	},

	// apply this.filters
	count : function(onsuccess, onerror){

		var where = this._construct_where_part(this.filters);
		
		var sql = "SELECT COUNT(*) AS count FROM " + this.db_identifier;
			
		var values = where.values_list;
		sql = sql + where.sql;
		
		this._execute(sql, values, function(results){
			onsuccess(results.rows.item(0).count);
		}, onerror);
	},

	// {object}
	insert : function(object, onsuccess, onerror){

		var self = this;

		var columns = [],
			values = [],
			values_placeholder = [];


		each(object, function(column, value, iterate){

			self._parse_column_and_value(column, value, function(parameters){
				columns.push(parameters.db_column);
				values.push(parameters.db_value);
				values_placeholder.push("?");

				iterate();
				
			});

		}, function(){
			// done

			var columns_string = columns.join();
			var values_string = values.join();
			var values_placeholder_string = values_placeholder.join();

			var sql = "INSERT OR REPLACE INTO " + self.db_identifier + " (" + columns_string + ") VALUES (" + values_placeholder_string + ")";

			self._execute(sql, values, function(results){
				if (typeof onsuccess == "function"){
					self._get_last_insert(self.db_identifier, function(db_obj){
						self._result_to_model_instance(db_obj, onsuccess);
					}, onerror);
				}
			}, onerror);

		});

	},
	// .filter().update() - updates multiple objs
	update : function(values, onsuccess, onerror){

		var self = this;

		var set_columns = [],
			set_values = [];
		
		for (var key in values){
			
			var parameters = this._parse_column_and_value(key, values[key]);

			var column = " " + parameters.db_column + " = ?";
			set_columns.push(column);
			set_values.push( parameters.db_value );
		}

		var where = this._construct_where_part(self.filters);

		var set_columns_string = set_columns.join();
		
		// append values from where to set_values
		var set_values = set_values.concat(where.values_list);

		var sql = "UPDATE " + this.db_identifier + " SET " + set_columns_string + " " + where.sql;

		this._execute(sql, set_values, onsuccess, onerror);

	},

	// update single instance
	update_instance : function(object_id, values, onsuccess, onerror){

		var self = this;

		var set_columns = [],
			set_values = [];

		each(values, function(column, value, iterate){

			self._parse_column_and_value(column, value, function(parameters){

				var column = " " + parameters.db_column + " = ?";
				set_columns.push(column);
				set_values.push( parameters.db_value );

				iterate();

			});


		}, function(){
			// done

			var set_columns_string = set_columns.join();

			var sql = "UPDATE " + self.db_identifier + " SET " + set_columns_string + " WHERE id = " + object_id;

			self._execute(sql, set_values, function(results){
				// create a model instance from the results
				self.get({"id":object_id}, onsuccess, onerror);
			}, onerror);

		});

	},

	// .filter().remove()
	remove : function(onsuccess, onerror){
		
		var where = this._construct_where_part(this.filters);
		var sql = "DELETE FROM " + this.db_identifier + " " + where.sql;
		
		this._execute(sql, where.values_list, onsuccess, onerror);
		
	},

	// instance.remove()
	remove_instance : function(object_id, onsuccess, onerror){

		var self = this;

		var sql = "DELETE FROM " + this.db_identifier + " WHERE id = ?";

		self._execute(sql, [object_id], function(results){
			if (typeof(onsuccess) == "function"){
				onsuccess();
			}
		}, onerror);		

	},

	each : function(onIter, onFinished){
		var self = this;

		var where = this._construct_where_part(this.filters);
		var sql = "SELECT * FROM " + this.db_identifier;

		values = where.values_list;
		sql = sql + where.sql;

		this._execute(sql, values, function(results){
			self._iterateSQLResults(results, onIter, onFinished);
		});
	}

});

var websqlModelInterface = SQLiteModelInterface;
