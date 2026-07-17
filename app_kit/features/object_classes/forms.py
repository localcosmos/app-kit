from django import forms
from django.utils.translation import gettext_lazy as _

from localcosmos_server.forms import LocalizeableModelForm

from .models import ObjectClass


class ObjectClassForm(LocalizeableModelForm):
    
	localizeable_fields = ['name', 'description']

	def __init__(self, *args, **kwargs):
		self.object_classes = kwargs.pop('object_classes')
		super().__init__(*args, **kwargs)

	def clean_scientific_name(self):
		scientific_name = self.cleaned_data['scientific_name']

		existing_entries = ObjectClass.objects.filter(
			object_classes=self.object_classes,
			scientific_name=scientific_name,
		)

		if self.instance.pk:
			existing_entries = existing_entries.exclude(pk=self.instance.pk)

		if existing_entries.exists():
			raise forms.ValidationError(
				_('An object class with this scientific name already exists.')
			)

		return scientific_name

	def save(self, commit=True):
		instance = super().save(commit=False)
		instance.object_classes = self.object_classes

		if commit:
			instance.save()

		return instance

	class Meta:
		model = ObjectClass
		fields = ('name', 'scientific_name', 'description')

