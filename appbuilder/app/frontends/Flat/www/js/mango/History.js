/*
 * drop-in replacement for html5 history api with extra features
 * html5 history api is not supported on all android devices
 * this class fixes this specific issue
 * there is no support for forward, history stack always ends with current page
 * url and page title are also currently NOT supported
 */


var History = (function() {

	var eventObj = document.createEvent('Event');
	eventObj.initEvent('popstate', true, true);

	var initial_state = {
		state:{},
		title:"",
		url:"/"
	};

	return {
		state : initial_state, // initial state
		states : [initial_state],
		"length" : 1,
		dispatch_popstate : function(){
			eventObj.state = this.state.state;
			document.dispatchEvent(eventObj);
		},
		go : function(backto){
			if (backto < 0){
				for (var i =-1; i >= backto; i--){
					//never remove the first state
					if (this.states.length > 1){
						this.states.pop();
						this.state = this.states[this.states.length-1];
					}
					else {
						break;
					}

				}
			
				this["length"] = this.states.length;
			
				this.dispatch_popstate();
			}
		},
		back : function(){
			//never remove the first state
			if (this.states.length > 1){
			
				//popping removes the current page from stack
				this.states.pop();
			
				//last state on stack is now the page to go - this has to stay in history
				this.state = this.states[this.states.length-1];
			
				this["length"] = this.states.length;
			
				this.dispatch_popstate();

			}
		},
		pushState : function(obj, title, url){

			var newState = {
				"state": obj,
				"title": title,
				"url": url
			};
		
			this.state = newState;
			this.states.push(newState);
		
			this["length"] = this.states.length;
		
		},
	
		replaceState : function(obj, title, url){
		
			var max_index = this.states.length -1;
		
			var newState = {
				"state": obj,
				"title": title,
				"url": url
			};
		
			this.states.splice(max_index, 1, newState);
		
			this["length"] = this.states.length;
		
		},

		restart : function(){
			this.states = [this.states[0]];
			this.state = this.states[0];
			this["length"] == 1;
		}
	};

})();
