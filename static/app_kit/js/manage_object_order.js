var positionmanager = {

	onMoveForward : function(){
		var $current = $("#" + $(this).attr("data-targetid"));
		var tagname = $current.prop('tagName');
		var $previous = $current.prev(tagname);
		if($previous.length !== 0){
			$current.insertBefore($previous);
		}
		positionmanager.store_positions($current);
		return false;
	},

	onMoveBack : function(){
		var $current = $("#" + $(this).attr("data-targetid"));
		var tagname = $current.prop('tagName');
		var $next = $current.next(tagname);
		if($next.length !== 0){
			$current.insertAfter($next);
		}
		positionmanager.store_positions($current);
		return false;
	},

	store_positions : function($current){
		
		var $parent = $current.parent(); 

		var order = [];

		$parent.children().each(function(){
			order.push(parseInt($(this).attr("data-object-id")));
		});

		$.post($parent.attr("data-store-positions-url"), {"order":JSON.stringify(order)}, function(){
		});
	},
	
	// get_content_fn is a function that returns the text content which is the parameter for sorting
	// alphabetical sorting does not work across languages
	sort_alphabetically : function(container_id, get_text_content_fn){
		// get all elements of container
		var container = document.getElementById(container_id);
		// get all element children, not descendants
		var elements = container.children;
		
		var sorted_elements = [];
		
		// iterate over each child, and insert it into a new list which is alphabetically sorted
		for (let e=0; e<elements.length; e++){
			
			let element = elements[e];
			
			let text_content = get_text_content_fn(element);
			
			if (sorted_elements.length == 0){
				sorted_elements.push(element);
			}
			else {
				
				let found_position = false;
				
				// iterate over all sorted_elements[]
				for (let s=0; s<sorted_elements.length; s++){
					let sorted_element = sorted_elements[s];
					let sorted_element_text_content = get_text_content_fn(sorted_element);
					
					let is_positioned_before = text_content < sorted_element_text_content;
					
					if (is_positioned_before == true){
						
						let insert_index = sorted_elements.indexOf(sorted_element);
						sorted_elements.splice(insert_index, 0, element);
						found_position = true;
						
						break;
					}					
				}
				
				if (found_position == false){
					sorted_elements.push(element);
				}
			}
		}
		
		// sort in UI
		for (let e=0; e<sorted_elements.length; e++){
			let element = sorted_elements[e];
			
			if (e == 0){
				$(element).prependTo($(container));
			}
			else if (e == sorted_elements.length -1){
				$(element).appendTo($(container));
			}
			else {
				let previous_element = sorted_elements[e-1]
				$(element).insertAfter($(previous_element));
				
			}
		}
		
		// store positions
		var element = sorted_elements[0];
		positionmanager.store_positions($(element));
	}

};
