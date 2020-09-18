function manage_observatory_area(){

	var selectedShape,
		shapes = [];

	var shape_id = 0;

	function clearSelection() {
        if (selectedShape) {
			try {
				selectedShape.setEditable(false);
			}
          	catch(e){
			}
          	selectedShape = null;
        }
    }

    function setSelection(shape) {
        clearSelection();
        selectedShape = shape;
		try{
			shape.setEditable(true);
		}
		catch(e){
		}        
    }

	function deleteSelectedShape() {

        if (selectedShape) {
			try {
				shapes.forEach(function(shape){
					if (shape.shape_id == selectedShape.shape_id){
						var index = shapes.indexOf(shape);
						shapes.splice(index,1);
					}
				});
				selectedShape.setMap(null);
			}
			catch(e){
				try {
					map.data.remove(selectedShape);
				}
				catch(e){
				}
			}			
        }
    }

	function clearMap(){
		
		shapes.forEach(function(shape){

			shape.setMap(null);
			
			var index = shapes.indexOf(shape);
			shapes.splice(index,1);			
			
		});

		map.data.forEach(function(feature){

			map.data.remove(feature);
			
		});		

	}

	var latlng = new google.maps.LatLng(0, 0);

	var mapOptions = {
		  minZoom: 2,
		  zoom: 2,
		  scrollwheel: true,
		  center: latlng,
		  mapTypeId: google.maps.MapTypeId.HYBRID
	};

	var map = new google.maps.Map(document.getElementById("areaMap"),mapOptions);

	map.data.setStyle({
		fillColor: 'red',
		strokeColor: 'red'
	});

	var drawingManager = new google.maps.drawing.DrawingManager({
		drawingMode: google.maps.drawing.OverlayType.MARKER,
		drawingControl: true,
		drawingControlOptions: {
			position: google.maps.ControlPosition.BOTTOM_CENTER,
			drawingModes: [
				google.maps.drawing.OverlayType.POLYGON
			]
		},
		polygonOptions : {
			strokeColor : "#FF0000",
			strokeOpacity : 0.8,
			strokeWeight : 2,
			fillColor : "#FF0000",
			fillOpacity : 0.35,
			editable: true,
			draggable: true
		}
	});

	drawingManager.setMap(map);

	function addPolyListeners(newShape){
		shape_id++;

		newShape.shape_id = shape_id;

		shapes.push(newShape);

		google.maps.event.addListener(newShape, 'click', function() {
			setSelection(newShape);
		});
		newShape.addListener('rightclick', function(mev){
			if (mev.vertex != null && this.getPath().getLength() > 3) {
				this.getPath().removeAt(mev.vertex);
			}
		});
		setSelection(newShape);
	}

	google.maps.event.addListener(drawingManager, 'overlaycomplete', function(e) {
		if (e.type != google.maps.drawing.OverlayType.MARKER) {

			// Switch back to non-drawing mode after drawing a shape.
			drawingManager.setDrawingMode(null);

			// Add an event listener that selects the newly-drawn shape when the user
			// mouses down on it.
			var newShape = e.overlay;
			newShape.type = e.type;

			addPolyListeners(newShape);
		}
    });

	// Clear the current selection when the drawing mode is changed, or when the
    // map is clicked.
    google.maps.event.addListener(drawingManager, 'drawingmode_changed', clearSelection);
    google.maps.event.addListener(map, 'click', clearSelection);

	google.maps.event.addDomListener(document.getElementById('delete-shape-button'), 'click', deleteSelectedShape);
	google.maps.event.addDomListener(document.getElementById('clear-map-button'), 'click', clearMap);


	function addPoly(array){

		var polyCoords = [];
		
		for (var c=0; c<array.length;c++){
			var coords = array[c];
			polyCoords.push(new google.maps.LatLng(coords[1], coords[0]))
		}


		// Construct the polygon.
		polygon = new google.maps.Polygon({
			paths: polyCoords,
			strokeColor: '#FF0000',
			strokeOpacity: 0.8,
			strokeWeight: 2,
			fillColor: '#FF0000',
			fillOpacity: 0.35,
			editable: true,
			draggable: true
		});

		polygon.setMap(map);

		addPolyListeners(polygon);

	}

	function addPolyAsData(geojson){

		var geojson = {
			"type": "Feature",
			"geometry": geojson
		}
	
		map.data.addGeoJson(geojson);

		map.data.addListener('click', function(event){
			setSelection(event.feature);
		});
	}

	var get_url = $("#areaMap").attr("data-fetch-url");

	$.get(get_url, function(geojson){

		clearMap();

		coordinates = geojson["coordinates"];

		for (var p=0;p<coordinates.length;p++){
			var poly = coordinates[p];

			if (poly[0].length < 100){

				addPoly(poly[0]);
			}
			else {

				var geojson_poly = {

					"type": "Polygon",
					"coordinates": poly
					
				};

				addPolyAsData(geojson_poly);
			}
			
		}

		drawingManager.setDrawingMode(null);

	});

	var input = $("#id_area_name");

	function clearInput(){	
		setTimeout(function(){
			input.val('');
		},250);
	}

	input.areaautocomplete(function(ev, ui){

		clearInput();
		drawingManager.setDrawingMode(null);

		addPolyAsData(JSON.parse(ui.item.geojson))

	});

	function saveProjectArea(){
		var geojson = {
			"type": "Feature",
			"geometry": {
				"type": "MultiPolygon",
				"coordinates": []
		 	},
			"properties": {"srid": 4326}
		}

		for (var i = 0; i < shapes.length; i++) {

			var polygon_array = [];

			var polygonBounds = shapes[i].getPath();

			poly_nodes = [];

			polygonBounds.forEach(function(xy, i) {
				poly_nodes.push([ xy.lng(), xy.lat() ]);
			});

			// close the polygon
			poly_nodes.push(poly_nodes[0]);

			polygon_array.push(poly_nodes)

			geojson["geometry"]["coordinates"].push(polygon_array);

		}

		map.data.forEach(function(feature){

			feature.toGeoJson(function(feat_geojson){

				var geomType = feat_geojson["geometry"]["type"];

				if (geomType == "MultiPolygon"){

					var mpoly = feat_geojson["geometry"]["coordinates"];
					
					for (var p=0; p<mpoly.length; p++){
						geojson["geometry"]["coordinates"].push(mpoly[p]);
					}
				}
				else {

					geojson["geometry"]["coordinates"].push(feat_geojson["geometry"]["coordinates"]);
				}
			});
			
		});

		var url = $("#areaMap").attr("data-url");

		$.post(url, {"geojson":JSON.stringify(geojson)}, function(html){
			$("#areasuccess").show().html(html);
		});

	}

	$("#save-area").on('click',saveProjectArea);

}


function loadIntoModal(url){

	$.get(url, function(html){
		$("#ModalContent").html(html);
		var options = {};
		$('#Modal').modal(options);
	});

}

function toggle(content_id){
	$("#" + content_id).toggle();
}

function extend(prototype, extensionlist) {
	
	var object = Object.create(prototype);
	var index = extensionlist.length;

	while (index) {
		index--;
		var extension = extensionlist[index];

		for (var property in extension){
			if (object.hasOwnProperty.call(extension, property) ||	typeof object[property] === "undefined") {
				object[property] = extension[property];
			}
		}
	}

	object._super = prototype;
	object.super = function(obj){
		var obj = obj || this;
		return obj._super;
	}

	return object;
};
