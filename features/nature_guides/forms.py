from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.forms import LocalizeableForm

from localcosmos_server.taxonomy.fields import TaxonField

from .models import MatrixFilter, NodeFilterSpace

from app_kit.utils import get_appkit_taxon_search_url

from .definitions import TEXT_LENGTH_RESTRICTIONS

class IdentificationMatrixForm(forms.Form):

    def __init__(self, meta_node, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # get all matrix filters for this node
        matrix_filters = MatrixFilter.objects.filter(meta_node=meta_node)

        for matrix_filter in matrix_filters:
            form_field = matrix_filter.matrix_filter_type.get_matrix_form_field()
            setattr(form_field, 'matrix_filter', matrix_filter)
            self.fields[str(matrix_filter.uuid)] = form_field
            

class SearchForNodeForm(LocalizeableForm):
    localizeable_fields = ['search_node_name']
    search_node_name = forms.CharField(label=_('Search nature guide'),
                                       help_text=_('Search whole tree for an entry.'))


'''
    Actions need a multiple choice field that contains instances of more than one model
'''
from app_kit.models import MetaAppGenericContent
from app_kit.forms import GenericContentOptionsForm
from django.db.models.fields import BLANK_CHOICE_DASH
from app_kit.features.taxon_profiles.models import TaxonProfiles
from app_kit.features.generic_forms.models import GenericForm

class NatureGuideOptionsForm(GenericContentOptionsForm):

    generic_form_choicefield = 'result_action'
    instance_fields = ['result_action']

    result_action = forms.ChoiceField(label=_('Action when tapping on an identification result'), required=False,
        help_text=_('Define what happens when the user taps on an entry (not a group) of this nature guide.'))

    #image_recognition = forms.BooleanField(label=_('Enable automatic identification using image recognition'),
    #                                       required=False)
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # get all forms of this app
        generic_form_ctype = ContentType.objects.get_for_model(GenericForm)
        taxon_profiles_ctype = ContentType.objects.get_for_model(TaxonProfiles)

        generic_contents = MetaAppGenericContent.objects.filter(meta_app=self.meta_app,
                                    content_type__in=[generic_form_ctype, taxon_profiles_ctype])

        generic_choices = []
        
        for link in generic_contents:
    
            choice = (
                str(link.generic_content.uuid), link.generic_content.name
            )
            generic_choices.append(choice)
            self.uuid_to_instance[str(link.generic_content.uuid)] = link.generic_content
            
        choices = BLANK_CHOICE_DASH + generic_choices

        self.fields[self.generic_form_choicefield].choices = choices


'''
    Manage Node links/Nodes
    - group links have a different form from result links
    - common form parts are in ManageNodeLinkForm
'''
# node_id and parent_node_id are transmitted via url
# locale is always primary language
# node type is filled from the view
NODE_TYPE_CHOICES = (
    ('node', _('Node')),
    ('result', _('Identification result')),
)

 # parent_node is fetched using view kwargs
class ManageNodelinkForm(LocalizeableForm):
    
    node_type = forms.ChoiceField(widget=forms.HiddenInput, choices=NODE_TYPE_CHOICES, label=_('Type of node'))

    name = forms.CharField(help_text=_('Name of the taxon or group.'), required=False,
                           max_length=TEXT_LENGTH_RESTRICTIONS['MetaNode']['name'])

    taxon = TaxonField(label=_('Taxon (makes taxonomic filters work)'),
                       taxon_search_url=get_appkit_taxon_search_url, required=False)
    
    decision_rule = forms.CharField(required=False, label=_('Decision rule'),
        max_length=TEXT_LENGTH_RESTRICTIONS['NatureGuidesTaxonTree']['decision_rule'],
        help_text=_("Will be shown below the image. Text that describes how to identify this entry or group, e.g. 'red feet, white body'."))

    node_id = forms.IntegerField(widget=forms.HiddenInput, required=False) # create the node if empty


    localizeable_fields = ['name', 'decision_rule']
    field_order = ['node_type', 'name', 'taxon', 'image', 'decision_rule', 'node_id']


    def __init__(self, parent_node, *args, **kwargs):

        self.node = kwargs.pop('node', None)
        self.from_url = kwargs.pop('from_url')

        super().__init__(*args, **kwargs)

        # get all available matrix filters for the parent node
        matrix_filters = MatrixFilter.objects.filter(meta_node=parent_node.meta_node)

        for matrix_filter in matrix_filters:
            field = matrix_filter.matrix_filter_type.get_node_space_definition_form_field(self.from_url)

            # not all filters return fields. eg TaxonFilter works automatically
            if field:

                field.required = False
                             
                field.label = matrix_filter.name
                field.is_matrix_filter = True
                field.matrix_filter = matrix_filter
                self.fields[str(matrix_filter.uuid)] = field

                field.initial = self.get_matrix_filter_field_initial(field)
        
    # only called if field has a matrix filter assigned to field.matrix_filter
    def get_matrix_filter_field_initial(self, field):
        
        if self.node:

            space = NodeFilterSpace.objects.filter(node=self.node, matrix_filter=field.matrix_filter).first()
            
            if space:
                
                if field.matrix_filter.filter_type in ['DescriptiveTextAndImagesFilter', 'ColorFilter']:
                    return space.values.all()
                elif field.matrix_filter.filter_type in ['NumberFilter']:
                    return ['%g' %(float(i)) for i in space.encoded_space]
                else:
                    return space.encoded_space

        return None


    def clean(self):

        cleaned_data = super().clean()

        name = cleaned_data.get('name', None)
        decision_rule = cleaned_data.get('decision_rule', None)

        if not name and not decision_rule:
            del cleaned_data['name']
            self.add_error('name', _('You have to enter at least a name or a decision rule.'))

        return cleaned_data
