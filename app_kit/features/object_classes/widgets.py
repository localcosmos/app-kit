from localcosmos_server.datasets.widgets import ObjectClassWidget as BaseObjectClassWidget


class ObjectClassWidget(BaseObjectClassWidget):

    template_name = 'object_classes/widgets/object_class_widget.html'

    def __init__(self, *args, **kwargs):
        self.ajax_url = kwargs.pop('ajax_url', '')
        self.taxon_field_id = kwargs.pop('taxon_field_id', '')
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['ajax_url'] = self.ajax_url
        context['taxon_field_id'] = self.taxon_field_id
        return context

