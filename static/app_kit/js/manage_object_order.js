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
	}

};
