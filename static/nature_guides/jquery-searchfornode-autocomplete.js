(function($) {
	$.fn.searchfornodeautocomplete = function(url, options) {

		var options = options || {};

		var search_input = $( this );
		
		search_input.prop('disabled', false);

		search_input.typeahead({
			autoSelect: false,
			source: function(input_value, process){

				$.ajax({
					type: 'GET',
					url: url,
					dataType: 'json',
					cache: false,
					data: { name: input_value },
					beforeSend : function(){
						search_input.prop('disabled', true);
						search_input.parent().removeClass('has-error');
						search_input.parent().removeClass('has-success');
					},
					success: function (data) {

						search_input.prop('disabled', false);

						if (data.length == 0){
							search_input.parent().addClass('has-error');
						}
						else {
							process($.map(data, function (item) {
								return item;
							}));
						}
					},
					error: function(){
						search_input.prop('disabled', false);
					}
				});
			}, 
			afterSelect : function(item){

				if (options.hasOwnProperty('afterSelect')){
					options.afterSelect(item);
				}
				else {
					// go to the parent node
					var url = item['url'];
					window.location = url;
				}
			},
            
			minLength: 3,
			delay: 500
		}); 
	}
}(jQuery));
