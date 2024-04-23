"use strict";

/*
	The DataSet model
	- the app creator can define anything as required or optional so no database constraints are possible
	- the dataset is stored as a json object
	- datasets without uuid need sync, only the server can assign uuids
	- if a dataset with a uuid has been modified, needs_sync is set to true
*/

var Dataset = Model(models.Model, {
	"model_name" : "Dataset",

	"remote_supported" : true,

	"fields" : {
		"uuid" : models.UUIDField({"null":true}), // this is always set by the server - if it is null, the dataset has not yet been transmitted
		"data" : models.JSONField(),
		"timestamp" : models.DateTimeField({"null":true}), // quick access for the temporal reference field
		"validation_step" : models.CharField({"max_length":255, "null":true}),
		"is_valid" : models.BooleanField({"default":true}),
		"created_at" : models.DateTimeField(), // timestamp when the dataset has been created on the server OR the offline device
		"last_modified" : models.DateTimeField({"null":true}), // timestamp when the dataset has been altered on the server OR the offline device. used to compare with servers last_modified column
		"client_id" : models.CharField({"max_length":255}),
		"user_id" : models.UUIDField({"null":true}), // UUID of the user
		"needs_sync" : models.BooleanField({"default":true}) // not yet uploaded Datasets
	},

	taxonLatname : function(self){
		// called from template - do not pass self
		var self = self || this;
		if (self.hasOwnProperty(taxon)){
			return taxon.taxonLatname;
		}
		else {
			return _("no taxon assigned");
		}
	},

	prefetch_thumbnail : function(self, callback){
		if (self.hasOwnProperty("thumbnail")){
			callback(self);
		}
		else {
			DatasetImages.objects.filter({"dataset_id":self.id}).first(function(dataset_image){

				if (dataset_image){
					self.thumbnail = dataset_image.image.medium;
				}
				else {
					self.thumbnail = null;
				}
				
				callback(self);
			});
		}
	},

	save : function(self, callback) {

		if (self.hasOwnProperty("id") && self.id != null && typeof self.id != "undefined"){
			self.last_modified = new Date();			
		}
		else {
			self.created_at = new Date();
		}

		// try to set self.timestamp
		if (self.data && self.data.hasOwnProperty("dataset") && self.data.dataset.hasOwnProperty("observation_form")){
			var temporal_field_uuid = self.data.dataset.observation_form.temporalReference;
			if (self.data.dataset.reported_values.hasOwnProperty(temporal_field_uuid)){
				var temporal_value = self.data.dataset.reported_values[temporal_field_uuid];
				if (temporal_value.cron.type == "timestamp"){
					self.timestamp = new Date(temporal_value.cron.timestamp);
				}
			}
		}

		Dataset.super().save(self, callback);

	},

	_post_create : function(self){
		// lock dataset if it is being validated
		self.is_locked = false;
		if (self.validation_step != null && typeof validation_step == "string"){
			self.is_locked = true;
		}

		if (self.data && self.data.hasOwnProperty("dataset") && self.data.dataset.hasOwnProperty("observation_form")){

			// set self.taxon, self.datetime and self.geography if possible
			// first, find taxon field uuid
			var taxon_field_uuid = self.data.dataset.observation_form.taxonomicReference;
			var temporal_field_uuid = self.data.dataset.observation_form.temporalReference;
			var geographic_field_uuid = self.data.dataset.observation_form.geographicReference;

			var values = self.data.dataset.reported_values;
			if (values.hasOwnProperty(taxon_field_uuid)){
				var taxon_data = values[taxon_field_uuid];

				if (taxon_data.hasOwnProperty("taxonSource") && taxon_data.hasOwnProperty("nameUuid") && taxon_data.hasOwnProperty("taxonLatname") && taxon_data.hasOwnProperty("taxonAuthor") && taxon_data.hasOwnProperty("taxonNuid")){
					self.taxon = Taxon.create(taxon_data.taxonSource, taxon_data.nameUuid, taxon_data.taxonLatname, taxon_data.taxonAuthor, taxon_data.taxonNuid, taxon_data);
				}
			}

			if (values.hasOwnProperty(temporal_field_uuid)){
				self.temporal = TemporalJSONbuilder.create(values[temporal_field_uuid]);
			}

			if (values.hasOwnProperty(geographic_field_uuid)){
				self.geography = GeoJSONbuilder.create(values[geographic_field_uuid]);
			}

		}

	},

	upload : function(self, onsuccess, onerror){
		if (self.needs_sync == true){

			// fetch a new instance of self
			Dataset.objects.get({"id":self.id}, function(dataset){

				delete dataset["id"];

				dataset.storage_location = "RemoteDB";

				dataset.save(dataset, function(remote_dataset){
					self.uuid = remote_dataset.uuid;
					self.needs_sync = false;
					self.save(self, function(self){
						onsuccess(self);
					});
				});

			});

			
		}
		else {
			onsuccess(self);
		}
	},

	remove : function(self, callback){

		var dataset = self;

		var model_route = "objects";
		
		if (self.storage_location == "RemoteDB") {
			model_route = "remote_objects";
		}

		// remove all dataset images
		DatasetImages[model_route].filter({"dataset_id":self.id}).fetch(function(dataset_images){

			each(dataset_images, function(dataset_image, iterate){

				dataset_image.remove(dataset_image, iterate);

			}, function(){
				Dataset.super().remove(self, callback);
			});
		});
	}

});

// DatasetImages have to be compatible with GenericForms
// - reference the field uuid
var DatasetImages = Model(models.Model, {
	"model_name" : "DatasetImages",

	"remote_supported" : true,

	"fields" : {
		"dataset" : models.ForeignKey(Dataset),
		"field_uuid" : models.UUIDField(),
		"image" : models.ImageField({"save_to" : "observation-images", "thumbnails" : {
				"small" : {"size" : [100, 100], "type" : "cover"}, // definition has to be in sync with localcosmos_server django_road, do not change this
				"medium" : {"size" : [400, 400], "type" : "cover"},// definition has to be in sync with localcosmos_server django_road, do not change this
				"full_hd" : {"size" : [1920, 1080], "type" : "contain"} // definition has to be in sync with localcosmos_server django_road, do not chagen this
			}
		}), // a local or remote url
		"needs_sync" : models.BooleanField({"default":true}) // not yet uploaded Datasets
	},

	remove : function (self, callback) {

		if (device.platform != "browser" && self.storage_location != "RemoteDB"){
	
			// remove images from disk
			self.image.url(function(imageUrl){

				var path_parts = imageUrl.split("/");
				var filename = path_parts.pop();

				each(DatasetImages.fields["image"]["thumbnails"], function(name, definition, iterate){

					var thumbnail_config = {
						quality : 0.95,
						maxWidth : definition.size[0],
						maxHeight : definition.size[1],
						imageSize : definition.type
					};
					var thumbnail = Thumbnail.create(thumbnail_config);

					thumbnail.get_thumbnail_filepath(imageUrl, function(thumbnail_path){
						FileUtil.remove(thumbnail_path, iterate);
					}, iterate);

				}, function(){

					FileUtil.remove(imageUrl, function(){

						// remove from db
						DatasetImages.super().remove(self, callback);

					});

				});

			});
		}

		else {
			DatasetImages.super().remove(self, callback);
		}

	},

	upload : function(self, onsuccess, onerror){

		if (self.needs_sync == true){

			Dataset.objects.get({"id":self.dataset_id}, function(dataset){

				if (dataset.needs_sync == true){

					var error = "You cannot sync a dataset image before the dataset has been synced";

					if (typeof onerror == "function"){
						onerror(error);
					}
					else {
						alert(error);
					}
					
				}
				else {

					DatasetImages.objects.get({"id":self.id}, function(local_image){

						Dataset.remote_objects.get({"uuid":dataset.uuid}, function(remote_dataset){

							delete local_image["id"];
							local_image.storage_location = "RemoteDB";
							local_image.dataset = remote_dataset;

							local_image.save(local_image, function(remote_image){
								self.needs_sync = false;
								
								self.save(self, function(self){
									onsuccess(self);
								});
							});

						});

					});
				}

			});

		}
		else {
			onsuccess();
		}

	}

});


// it has to be the same layout as on the server
var LocalcosmosUser = Model(models.Model, {
	"model_name" : "LocalcosmosUser",
	"fields" : {
		"uuid" : models.UUIDField(), // same as on server
		"slug" : models.CharField({"max_length":255}), // same as on server
		"username" : models.CharField({"max_length":255}),
		"first_name" : models.CharField({"max_length":255, "null" : true}),
		"last_name" : models.CharField({"max_length":255, "null" : true}), 
		"email" : models.CharField({"max_length":255, "unique":true}),
		"details" : models.JSONField({"null":true})
	}
}, BaseUser);

// make UserModel available for mango
var UserModel = LocalcosmosUser;
