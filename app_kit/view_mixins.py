from .models import MetaApp

class MetaAppMixin:

    def dispatch(self, request, *args, **kwargs):
        self.set_meta_app(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_meta_app(self, **kwargs):
        self.meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'meta_app' : self.meta_app,
        })
        return context


class MetaAppFormLanguageMixin(MetaAppMixin):

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['language'] = self.meta_app.primary_language
        return kwargs


class FormLanguageMixin:

    def dispatch(self, request, *args, **kwargs):
        self.set_primary_language()
        return super().dispatch(request, *args, **kwargs)

    def set_primary_language(self):
        raise NotImplementedError('FormLanguageMixin needs set_primary_language')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['language'] = self.primary_language
        return kwargs
    

class ViewClassMixin(object):
    @classmethod
    def as_view(self, **kwargs):
        view = super().as_view(**kwargs)
        view.view_class = self
        return view
