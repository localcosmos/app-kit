// form fields
Handlebars.registerPartial('TextInput',
'<input type="text" id="{{id}}" name="{{name}}" placeholder="{{ label }}"  {{#if value}}value="{{value}}"{{/if}} {{#if error}}class="error"{{/if}} />');

Handlebars.registerPartial('PasswordInput',
'<input type="password" id="{{id}}" name="{{name}}" placeholder="{{ label }}"  {{#if value}}value="{{value}}"{{/if}} {{#if error}}class="error"{{/if}} />');

Handlebars.registerPartial('NumberInput',
'<input id="{{id}}" name="{{name}}" type="number" {{#if value}}value="{{value}}"{{/if}} {{#if error}}class="error"{{/if}} />');

Handlebars.registerPartial('NumberInputWithButtons',
'<table class="NumberInputWithButtons"><tr><td class="w30"><div class="cellbutton ontouchend" action="changeCount" params=\'{"counter_id":"{{id}}","action":"-"}\'>-</div></td><td class="w40"><input id="{{id}}" name="{{name}}" type="number" class="large center {{#if error}}error{{/if}}" {{#if max_value}}max="{{max_value}}"{{/if}} {{#if min_value}}min="{{min_value}}"{{/if}} {{#if value}}value="{{value}}"{{/if}} /></td><td class="w30"><div class="cellbutton ontouchend" action="changeCount" params=\'{"counter_id":"{{id}}","action":"+"}\'>+</div></td></tr></table>');

Handlebars.registerPartial('HiddenInput',
'<input id="{{id}}" name="{{name}}" type="hidden" {{#if value}}value="{{value}}"{{/if}} {{#if error}}class="error"{{/if}} />');

Handlebars.registerPartial('CheckboxInput',
'<input id="{{id}}" name="{{name}}" type="checkbox" {{#if selected}}selected{{/if}} {{#if error}}class="error"{{/if}} />');

Handlebars.registerPartial('Select',
'<select id="{{id}}" name="{{name}}" {{#if error}}class="error"{{/if}}>{{#each choices}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}</select>');

Handlebars.registerPartial('CheckboxSelectMultiple',
'{{#each choices}}<label>{{label}}</label><input type="checkbox" name="{{name}}" {{#if selected}}checked{{/if}} {{#if error}}class="error"{{/if}} />{{/each}}');
