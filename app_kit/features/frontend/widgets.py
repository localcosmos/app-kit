import os

from django import forms


class ResourceFileInput(forms.ClearableFileInput):
    template_name = 'frontend/widgets/resource_file_input.html'

    def is_initial(self, value):
        # avoid accessing .url which is unavailable for private storage
        return bool(value and hasattr(value, 'name') and value.name)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['input_type'] = self.input_type
        if self.is_initial(value):
            context['widget']['display_name'] = os.path.basename(value.name)
        return context
