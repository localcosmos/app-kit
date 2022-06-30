// creates a simple swipe carousel
function carousel(){
	var box = document.querySelector('.carousel');

	var items = box.querySelectorAll('.carousel-item');
	var counter = 0;
	var amount = items.length;
	var current = items[0];

	function navigate(direction) {
		current.classList.remove('current');
		counter = counter + direction;
		if (direction === -1 && counter < 0) { 
			counter = amount - 1; 
		}
		if (direction === 1 && !items[counter]) { 
			counter = 0;
		}
		current = items[counter];
		current.classList.add('current');
	}

	if (amount > 1){
		// insert next and prev buttons
		var next = document.createElement('div');
		var next_arrow_container = document.createElement('div');
		var next_arrow = document.createElement('img');
		next_arrow.setAttribute('src', 'carousel/rightarrow.svg');
		next_arrow_container.appendChild(next_arrow);
		next.appendChild(next_arrow_container);
		next.classList.add('carousel-nav');
		next.style.right = 0;
		box.appendChild(next);

		var prev = document.createElement('div');
		var prev_arrow_container = document.createElement('div');
		var prev_arrow = document.createElement('img');
		prev_arrow.setAttribute('src', 'carousel/leftarrow.svg');
		prev_arrow_container.appendChild(prev_arrow);
		prev.appendChild(prev_arrow_container);
		prev.classList.add('carousel-nav');
		prev.style.left = 0;
		box.appendChild(prev);

		next.addEventListener('click', function(ev) {
			navigate(1);
		});
		prev.addEventListener('click', function(ev) {
			navigate(-1);
		});
	}
	navigate(0);
}
