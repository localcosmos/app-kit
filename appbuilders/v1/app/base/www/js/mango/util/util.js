"use strict";

function validate_uuid(str){
	var pattern = new RegExp('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', 'i');
	return pattern.test(str);
}


function validate_slug(str){
	var pattern = new RegExp('^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$');
	return pattern.test(str);
}


/*
* ios only uses CELL without _2G etc
*/
function getNetworkState(){

	if (navigator.connection.hasOwnProperty("type")){
		var network_state = navigator.connection.type;
	}
	else {
		// chromium: navigator.connection == {}
		var network_state = "ETHERNET";
	}

	// Connection.CELL_2G.toLowerCase(), is offline
	var internet = [Connection.ETHERNET.toLowerCase(), Connection.WIFI.toLowerCase(), Connection.CELL_3G.toLowerCase(), Connection.CELL_4G.toLowerCase(), Connection.CELL.toLowerCase()];
	var nointernet = [Connection.UNKNOWN.toLowerCase(), Connection.NONE.toLowerCase(), Connection.CELL_2G.toLowerCase()];

	if (internet.indexOf(network_state.toLowerCase()) >= 0){
		return "online";
	}
	else {
		return "offline";
	}
}


// FILE UTIL
var FileUtil = {

	_onerror : function(e){
		if (typeof e === "string" || e instanceof String){
			var message = e;
		}
		else {
			var message = JSON.stringify(e);
		}
		alert("[FILE UTIL ERROR] " + message);
	},
    
    
    _save : function(data_location, directory_name, filename, fileObj, onsuccess, onerror){
        
        var onerror = onerror || this._onerror;

        window.requestFileSystem(data_location, 0, function (fs) {

            fs.root.getDirectory(directory_name, { create: true }, function (dirEntry) {

                console.log("storing file " + filename + " in directory " + directory_name);

                dirEntry.getFile(filename, { create: true, exclusive: false }, function (fileEntry) {

                    fileEntry.createWriter(function(fileWriter) {

                        fileWriter.onwriteend = function() {
                            console.log("[FileUtil] stored file: " + fileEntry.name);
                            console.log("[FileUtil] stored file path: " + fileEntry.fullPath);
                            onsuccess(fileEntry);
                        };

                        fileWriter.onerror = onerror;

                        fileWriter.write(fileObj);

                    }, onerror);

                }, onerror);

            }, onerror);

        }, onerror);
    },

	// currently on one cirectory is supported
	// future: allow paths like /path/to/
	save : function(directory_name, filename, fileObj, onsuccess, onerror){
		
        FileUtil._save(LocalFileSystem.PERSISTENT, directory_name, filename, fileObj, onsuccess, onerror);

	},
    // iOS WKWEBVIEW can only display images from the temp folder
    save_in_temp_folder : function(directory_name, filename, fileObj, onsuccess, onerror){
        
        FileUtil._save(LocalFileSystem.TEMPORARY, directory_name, filename, fileObj, onsuccess, onerror);
        
    },

	// iOS fallback
	save_ios_fallback : function(directory_name, filename, fileObj, onsuccess, onerror){
		if (device.platform == 'iOS'){
			var filesystem = LocalFileSystem.TEMPORARY;
		}
		else {
			var filesystem = LocalFileSystem.PERSISTENT;
		}

		FileUtil._save(filesystem, directory_name, filename, fileObj, onsuccess, onerror);

	},

    // cdvfile:// or file://
	remove : function(cdvfilepath, onsuccess, onerror){

		var onerror = onerror || this._onerror;

		var path_parts = cdvfilepath.split("/");

		var filename = path_parts.pop();
		var directory = path_parts.join("/");

		window.resolveLocalFileSystemURL(directory, function (dirEntry) {

			dirEntry.getFile(filename, {create: false}, function (fileEntry) {

		        fileEntry.remove(function(){

					console.log("[FileUtil] removed file: " + cdvfilepath);
					onsuccess();

				}, onerror);

		    }, function(error){
				if (error.code == 1){

					console.log("[FileUtil] did not remove file because it was not found: " + cdvfilepath);

					// file not found
					onsuccess();
				}
				else {
					onerror(error);
				}
				
			});

		}, onerror);

	},

	get : function(path, onsuccess, onerror){

		var onerror = onerror || this._onerror;

		window.resolveLocalFileSystemURL(path, function(fileEntry){

			fileEntry.file(function(file){
				onsuccess(file);
			}, onerror);

		}, onerror);
	},

	// stores in persistent folder
	download : function(url, to_directory, filename, onsuccess, onerror){

		var onerror = onerror || FileUtil._onerror;

		var xhr = new XMLHttpRequest();	

		// Make sure you add the domain name to the Content-Security-Policy <meta> element.
		xhr.open("GET", url, true);

		// Define how you want the XHR data to come back
		xhr.responseType = "blob";

		xhr.onload = function (event) {
		
			var blob = xhr.response; // Note: not xhr.responseText

			if (blob) {
				
				FileUtil.save(to_directory, filename, blob, onsuccess, onerror);
			}
			else {
				onerror('we didnt get an XHR response!');
			}

		};

		xhr.send(null);

	},

	// only absolute paths are supported
	// root is the eg filesystem.PERSISTENT root (sanbox in-app)
	_dir_and_filename : function(path){

		if (path.indexOf("/") != 0){
			throw new Error("path has to begin with /");
		}
		
		var path_parts = path.split("/");
		path_parts.shift();

		var filename = path_parts.pop();

		if (path_parts.length > 1){
			throw new Error("path to store file can only have one directory")
		}

		if (path_parts.length == 1){
			var directory = path_parts[0];
		}
		else {
			var directory = null;
		}
		
		var dir_and_filename = {
			"directory" : directory,
			"filename" : filename
		};
		return dir_and_filename;
	}

};
