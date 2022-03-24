function horizontal_slider(element_id){

	var el = document.getElementById(element_id);
	var mc = new Hammer.Manager(el);

	mc.add(new Hammer.Pan({ threshold: 0, pointers: 0 }));

	// elements have to stay within the parent container
	var left_boundary = 0,
		right_boundary = 0;

	var left_start = left_boundary;

	function onPan(event){

		if (event.type == 'panstart'){
			left_start = el.getBoundingClientRect().left - el.parentElement.getBoundingClientRect().left;
			right_boundary = el.parentElement.clientWidth;
		}

		var new_left_edge = left_start + event.deltaX,
			new_right_edge = new_left_edge + el.clientWidth;

		var new_pos = left_start + event.deltaX;

		el.style.transform = 'translate3d(' + new_pos + 'px, 0px, 0px)';

		if(event.isFinal) {

			if (new_left_edge >= left_boundary){
				new_pos = left_boundary;
			}
			else if (new_right_edge <= right_boundary){
				new_pos = right_boundary - el.clientWidth;
			}

			el.classList.add( 'is-animating' );
			
			el.style.transform = 'translateX( ' + new_pos + 'px )';
			clearTimeout( el.timer );
			el.timer = setTimeout( function() {
				el.classList.remove( 'is-animating' );
			}, 400 );
		}
	}


	mc.on("panstart panmove panend", onPan);

}
