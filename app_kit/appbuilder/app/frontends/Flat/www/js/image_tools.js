"use strict";

var Thumbnail = {
	create : function(config){

		var config = config || {};

		var self = Object.create(this);

		self.config = {
			quality : 1.00,
			maxWidth : 100,
			maxHeight : 100,
			imageSize : "cover"
		}

		for (var key in config){
			self.config[key] = config[key];
		}

		return self;
	},
    
    error_handler : function(e, onerror){
        
        if (typeof(onerror) == "function"){
            onerror(e);
        }
        else {
            alert(e.toString());
        }
        
    },

	as_data_url : function(image_src, onsuccess, onerror){
		var self = this;

		self._load_image(image_src, function(loaded_image){

			// scale the loaded image in a canvas
			self._get_thumbnail_canvas(loaded_image, function(thumb_canvas){

				var image_data = thumb_canvas.toDataURL('image/jpeg', self.config.quality);
			
				onsuccess(image_data);

			});

		}, onerror)

	},

	as_blob : function(image_src, onsuccess, onerror){

		var self = this;

		self._load_image(image_src, function(loaded_image){

			// scale the loaded image in a canvas
			self._get_thumbnail_canvas(loaded_image, function(thumb_canvas){
                thumb_canvas.toBlob(onsuccess, 'image/jpeg', self.config.quality);
			});

		}, onerror)

	},

	// image can be a valid URI or a data: url
	// some browser use fakepath which makes filereader necessary, in this case image_src is an object
	_load_image : function(image_src, onsuccess, onerror){
		
		var self = this;

        self._get_valid_image_src(image_src, function(valid_image_src){

            // first, try to simply load the image
            var image = new Image();
            
            image.crossOrigin = "Anonymous";

            image.onload = function(){
                onsuccess(image);
            }
            
            image.onerror = function(e){
                self.error_handler(e, onerror);
            }
            
            image.src = valid_image_src;
            
        }, onerror);

	},
    
    // ios wkwebview can only display images in the tmp directory
    // therefore, use asDataURL to create the thumb
    _get_valid_image_src : function(image_src, onsuccess, onerror){
        
        var self = this;

        if (device.platform == "iOS" && typeof(image_src) == "string" && image_src.indexOf("cdvfile://") == 0){
            // might require cdvfile://
            resolveLocalFileSystemURL(image_src, function(fileEntry) {
                
                fileEntry.file(function (file) {
                    var reader = new FileReader();

                    reader.onloadend = function() {
                        onsuccess(this.result);
                    };

                    reader.readAsDataURL(file);

                }, onerror);
                
            },
            function(e){
                // resolve image_src error
                self.error_handler(e, onerror);
            });
        }
        else {
			if (typeof(image_src) == "object"){
				self._load_image_src_from_reader(image_src, onsuccess, onerror);
			}
			else {
	            onsuccess(image_src);
			}
        }
        
    },

	_load_image_src_from_reader : function(blob, onsuccess, onerror){
		var self = this;

		var reader = new FileReader();
		reader.onloadend = function(event){
			onsuccess(event.target.result);
		}

		reader.onerror = function(e){
			if (typeof(onerror) == "function"){
				onerror(e);
			}
			else {
				alert("error loading the image from a blob");
			}
		}
		reader.readAsDataURL(blob);
	},


	_get_thumbnail_canvas : function(loaded_image, callback){

		var self = this

		// rotate canvas if necessary
		FlexImage.correct_image_orientation(loaded_image, function(canvas){

			// reduce the image size in steps for better results
			while (canvas.width >= (2 * self.config.maxWidth) && canvas.height >= (2 * self.config.maxHeight)) {
				canvas = self._get_half_scale_canvas(canvas);
			}

			// the image is now larger than self.config.maxWidth and/or self.config.maxHeight
			// depending on self.config.imageSize == cover or contain, perform the next scale

			canvas = self._get_scaled_canvas(canvas);
			
			// the image is now downscaled, but still has its original aspect ratio
			// if self.config.imageSize == cover, cropping is necessary
			if (self.config.imageSize == "cover"){
				canvas = self._get_cropped_canvas(canvas);
			}

			callback(canvas);

		});

	},

	_get_cropped_canvas : function(canvas){
		var self = this;

		// determine topleft start of crop (sx,sy)
		var sx = Math.abs( (canvas.width/2) - (self.config.maxWidth/2));
		var sy = Math.abs( (canvas.height/2) - (self.config.maxHeight/2));

		var cropped_canvas = document.createElement("canvas");
		cropped_canvas.width = self.config.maxWidth;
		cropped_canvas.height = self.config.maxHeight;

		cropped_canvas.getContext("2d").drawImage(canvas, sx, sy, self.config.maxWidth, self.config.maxHeight, 0, 0, self.config.maxWidth, self.config.maxHeight);

		return cropped_canvas;
	},


	_get_scale_factor : function(canvas){

		var self = this;

		// check differences
		var wdiff = Math.abs(self.config.maxWidth - canvas.width),
			hdiff = Math.abs(self.config.maxHeight - canvas.height);

		if (self.config.imageSize == "contain"){
			// contain -> the larger difference determines the scale factor
			if (wdiff >= hdiff){
				var scale_factor = self.config.maxWidth / canvas.width;
			}
			else {
				var scale_factor = self.config.maxHeight / canvas.height;
			}
		}
		else {
			// cover -> the smaller difference determines the scale factor
			if (wdiff <= hdiff){
				var scale_factor = self.config.maxWidth / canvas.width;
			}
			else {
				var scale_factor = self.config.maxHeight / canvas.height;
			}
		}

		return scale_factor;

	},

	_get_scaled_canvas : function(canvas){

		var self = this;

		var scaled_canvas = document.createElement("canvas");
		
		var scale_factor = self._get_scale_factor(canvas);

		scaled_canvas.width = canvas.width * scale_factor;
		scaled_canvas.height = canvas.height * scale_factor;
	
		scaled_canvas.getContext('2d').drawImage(canvas, 0, 0, scaled_canvas.width, scaled_canvas.height);

		return scaled_canvas;

	},

	// reduce the image size in steps for better results
	_get_half_scale_canvas : function(canvas) {
		var halfCanvas = document.createElement("canvas");
		halfCanvas.width = canvas.width / 2;
		halfCanvas.height = canvas.height / 2;

		halfCanvas.getContext('2d').drawImage(canvas, 0, 0, halfCanvas.width, halfCanvas.height);

		return halfCanvas;
	},

	_get_thumb_filename : function(cdvfilepath){

		var self = this;

		var path_parts = cdvfilepath.split("/");
		var filename = path_parts.pop();

		var name_parts = filename.split(".");

		var extension = name_parts.pop();
		var name = name_parts.join(".");

		var thumb_filename = name + "_" + self.config.maxWidth.toString() + "x" + self.config.maxHeight.toString() + "." + extension;

		return thumb_filename;
	},
    
	// currently, on iOS the tempfolder is used (WKWEBVIEW limitation, maybe rewrite this after release of cordova ios 6.x)
	// on Android, persistent folder is used
	// imageUrl is cdvfile:// for Android and file:// for iOS
    get_thumbnail_filepath : function(cdvfilepath, onsuccess, onerror){

		var self = this;

		var thumb_filename = self._get_thumb_filename(cdvfilepath);

		// file:// (iOS), cdvfile:// (Android)
		if (device.platform == "iOS"){
			var thumb_filepath = cordova.file.tempDirectory + "thumbs/" + thumb_filename;
			onsuccess(thumb_filepath);
		}
		else {

			window.requestFileSystem(LocalFileSystem.PERSISTENT, 0, function (fs) {

            	fs.root.getDirectory("thumbs", { create: true }, function (dirEntry) {

					var thumb_filepath = dirEntry.toInternalURL() + "/" + thumb_filename;
					onsuccess(thumb_filepath);

				}, function(e){
		            self.error_handler(e, onerror);
		        });

			}, function(e){
				self.error_handler(e, onerror);
			});
		}

    },
    
    // ios does not support file:// for images
    // create thumbnails on demand
	// iOS: thumbnails are stored in cordova.file.tempDirectory/thumbs/
	// Android: thumbnails are stored in cordova.file.dataDirectory/thumbs/
    // return a valid url to display the thumbnail (OS specific)
    as_url : function(cdvfilepath, onsuccess, onerror){

        var self = this;
        
        var directory_name = "thumbs";
        
        // first, check if the file exists
        self.get_thumbnail_filepath(cdvfilepath, function(thumb_filepath){

			function gotThumbFileEntry(fileEntry){
				if (device.platform == "iOS"){
				    // file:// has length of 7
                    var new_thumb_filepath = fileEntry.toURL();
                    
				    var url = new_thumb_filepath.substring(7);
				    onsuccess(url);
				}
				else {
				    onsuccess(fileEntry.toURL());
				}
			}

		    window.resolveLocalFileSystemURL(thumb_filepath, gotThumbFileEntry,
				function(e){

		        // thumb file not found, create a new one from cdvfile://
		        self.as_blob(cdvfilepath, function(thumb_blob){

					var thumb_filename = self._get_thumb_filename(cdvfilepath);

		            thumb_blob.filename = thumb_filename;

		            // save to disk, temp folder for ios, persistent for android
		            FileUtil.save_ios_fallback(directory_name, thumb_filename, thumb_blob, gotThumbFileEntry,
					function(e){
		                self.error_handler(e, onerror);
		            });
		            
		        }, function(e){
		            self.error_handler(e, onerror);
		        });

		    });

		});

    }
};

// iOS WKWEBVIEW
var CachedImage = {

	error_handler : function(e, onerror){
        
        if (typeof(onerror) == "function"){
            onerror(e);
        }
        else {
            alert(e.toString());
        }
        
    },

	_get_filename : function(cdvfilepath){
		var path_parts = cdvfilepath.split("/");
		var filename = path_parts.pop();
		return filename;
	},

	// iOS only
	_get_cached_filepath: function(cdvfilepath){
        var self = this;
		
		var filename = self._get_filename(cdvfilepath);
		var cached_filepath = cordova.file.tempDirectory + "cache/" + filename;
		return cached_filepath;

	},

	_url_from_fileEntry : function(fileEntry){
		var self = this;

		if (device.platform == "iOS"){
			var filename = self._get_filename(fileEntry.toInternalURL());
			var url = cordova.file.tempDirectory + "cache/" + filename;
            url = url.substring(7);
			return url;
		}
		else {
			return fileEntry.toInternalURL();
		}
	},
	

	as_url : function(cdvfilepath, onsuccess, onerror){
		var self = this;

		if (device.platform == "iOS"){

			var cached_filepath = self._get_cached_filepath(cdvfilepath);
					
			window.resolveLocalFileSystemURL(cached_filepath, function(fileEntry){

				var url = self._url_from_fileEntry(fileEntry);
				onsuccess(url);

			}, function(e){
				// create new temp file
				window.resolveLocalFileSystemURL(cdvfilepath, function(source_fileEntry){
					window.requestFileSystem(LocalFileSystem.TEMPORARY, 0, function (fs) {

						fs.root.getDirectory("cache", { create: true }, function (dirEntry) {

							var filename = self._get_filename(cdvfilepath);

							source_fileEntry.copyTo(dirEntry, filename, function(new_fileEntry){

								var url = self._url_from_fileEntry(new_fileEntry);
								onsuccess(url);

							}, function(e){
								self.error_handler(e, onerror);
							});

						}, function(e){
							self.error_handler(e, onerror);
						});

					});
				});
			});

		}
		else {
			onsuccess(cdvfilepath);
		}
	}
};
