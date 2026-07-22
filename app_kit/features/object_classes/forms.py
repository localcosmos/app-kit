from django import forms
from django.utils.translation import gettext_lazy as _

from localcosmos_server.forms import LocalizeableModelForm
from localcosmos_server.taxonomy.forms import AddSingleTaxonForm

from taxonomy.lazy import LazyTaxon

from .models import ObjectClass, ObjectClassTaxon


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
		help_texts = {
			'name': _('Use a concise, user-facing name for this object class.'),
			'scientific_name': _('For example a Latin name. It has to be unique within this object class set.'),
			'description': _('Optional: add a short description to provide context.'),
		}


class AddObjectClassTaxonForm(AddSingleTaxonForm):
    
    lazy_taxon_class = LazyTaxon

    def __init__(self, *args, **kwargs):
        self.object_class = kwargs.pop('object_class')
        super().__init__(*args, **kwargs)
        
        self.fields['taxon'].label = _('Add taxon')
    
    def clean(self):
        cleaned_data = super().clean()
        taxon = cleaned_data.get('taxon', None)
        
        if taxon:
            
            already_exists_message = _('This taxon already exists for this object class.')
            
            exists = self.object_class.taxa.filter(
				taxon_source=taxon.taxon_source,
				name_uuid=taxon.name_uuid,).exists()
            
            if exists:
                self.add_error('taxon', already_exists_message)                

        return cleaned_data


class AddObjectClassLinkForm(forms.Form):

	object_class = forms.ModelChoiceField(
		queryset=ObjectClass.objects.none(),
		label=_('Object class'),
		empty_label=None,
	)

	def __init__(self, *args, **kwargs):
		self.object_classes = kwargs.pop('object_classes')
		self.taxon = kwargs.pop('taxon')
		super().__init__(*args, **kwargs)
  
		valid_nuids = self.taxon.ancestor_nuids + [self.taxon.taxon_nuid]

  
		matching_pks = ObjectClassTaxon.objects.filter(
			object_class__object_classes=self.object_classes,
			taxon_source=self.taxon.taxon_source,
			taxon_nuid__in=valid_nuids,
		).values_list('object_class', flat=True)
  
		self.fields['object_class'].queryset = ObjectClass.objects.filter(pk__in=matching_pks)