from django.conf import settings
from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.forms import LocalizeableForm

from localcosmos_server.taxonomy.fields import TaxonField

from .models import (MatrixFilter, NodeFilterSpace, NatureGuidesTaxonTree, MatrixFilterRestriction,
    NatureGuideCrosslinks)

from app_kit.utils import get_appkit_taxon_search_url

from app_kit.validators import json_compatible

from .definitions import TEXT_LENGTH_RESTRICTIONS

class IdentificationMatrixForm(forms.Form):

    # meta_app is required to make ContentImage cache possible during the creatoin of those images
    def __init__(self, meta_app, meta_node, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # get all matrix filters for this node
        matrix_filters = MatrixFilter.objects.filter(meta_node=meta_node)

        for matrix_filter in matrix_filters:
            form_field = matrix_filter.matrix_filter_type.get_matrix_form_field(meta_app)
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

    version = forms.CharField(help_text=_('You can manually set you own version here. This will not affect the automated versioning.'), required=False)
    

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

class MatrixFilterValueChoicesMixin:

    show_add_button = True

    def get_matrix_filter_field_initial(self, field):
        raise NotImplementedError('MatrixFilterValueChoicesMixin subclasses require the method get_matrix_filter_field_initial')

    def get_matrix_filters(self):
        matrix_filters = MatrixFilter.objects.filter(meta_node=self.meta_node)
        return matrix_filters


    def add_matrix_filter_value_choices(self):

        # get all available matrix filters for the parent node
        matrix_filters = self.get_matrix_filters()

        for matrix_filter in matrix_filters:

            field = matrix_filter.matrix_filter_type.get_node_space_definition_form_field(self.meta_app, self.from_url,
                                                                    show_add_button=self.show_add_button)

            # not all filters return fields. eg TaxonFilter works automatically
            if field:

                field.required = False
                             
                field.label = matrix_filter.name
                field.is_matrix_filter = True
                field.matrix_filter = matrix_filter
                self.fields[str(matrix_filter.uuid)] = field

                field.initial = self.get_matrix_filter_field_initial(field)
        

    
# node_id and parent_node_id are transmitted via url
# locale is always primary language
# node type is filled from the view
NODE_TYPE_CHOICES = (
    ('node', _('Node')),
    ('result', _('Identification result')),
)

META_NODE_DESCRIPTION_WIDGET = forms.HiddenInput
if settings.APP_KIT_ENABLE_META_NODE_DESCRIPTION == True:
    META_NODE_DESCRIPTION_WIDGET = forms.Textarea

is_active_field = forms.BooleanField(required=False, label=_('included in app'),
                    help_text=_('Marks if this node is included in your app.'))

 # parent_node is fetched using view kwargs
class ManageNodelinkForm(MatrixFilterValueChoicesMixin, LocalizeableForm):
    
    node_type = forms.ChoiceField(widget=forms.HiddenInput, choices=NODE_TYPE_CHOICES, label=_('Type of node'))

    name = forms.CharField(help_text=_('Name of the taxon or group.'),
                           max_length=TEXT_LENGTH_RESTRICTIONS['MetaNode']['name'])

    morphotype = forms.CharField(help_text=_('Morphotype, like sex or development stage'), required=False,
                           max_length=TEXT_LENGTH_RESTRICTIONS['MetaNode']['morphotype'])

    taxon = TaxonField(label=_('Taxon (makes taxonomic filters work)'),
                       taxon_search_url=get_appkit_taxon_search_url, required=False)

    is_active = is_active_field

    # decision rule is currently hidden, might be deprecated in the future
    decision_rule = forms.CharField(required=False, label=_('Decision rule'),
        widget=forms.HiddenInput,
        max_length=TEXT_LENGTH_RESTRICTIONS['NatureGuidesTaxonTree']['decision_rule'],
        help_text=_("Will be shown below the image. Text that describes how to identify this entry or group, e.g. 'red feet, white body'."))

    description = forms.CharField(widget=META_NODE_DESCRIPTION_WIDGET, required=False, validators=[json_compatible])
    
    node_id = forms.IntegerField(widget=forms.HiddenInput, required=False) # create the node if empty


    localizeable_fields = ['name', 'decision_rule', 'description']
    field_order = ['node_type', 'name', 'taxon', 'image', 'decision_rule', 'node_id']

    layoutable_simple_fields = ['description']


    def __init__(self, meta_app, tree_parent_node, submitted_parent_node, *args, **kwargs):

        if settings.APP_KIT_ENABLE_META_NODE_DESCRIPTION != True:
            self.layoutable_simple_fields = []

        self.meta_app = meta_app

        # the node this node is attached to in the tree, no crosslinks
        self.tree_parent_node = tree_parent_node

        self.nature_guide = self.tree_parent_node.nature_guide

        # the parent_node the editor is currently editing, it might be the crosslink parent
        # the submitted parent node defines the matrix filters and the meta node
        self.submitted_parent_node = submitted_parent_node
        self.meta_node = self.submitted_parent_node.meta_node
        
        self.node = kwargs.pop('node', None)
        self.from_url = kwargs.pop('from_url')

        super().__init__(*args, **kwargs)

        self.add_matrix_filter_value_choices()
        
    # only called if field has a matrix filter assigned to field.matrix_filter
    def get_matrix_filter_field_initial(self, field):
        
        if self.node:

            space = NodeFilterSpace.objects.filter(node=self.node, matrix_filter=field.matrix_filter).first()
            
            if space:
                
                if field.matrix_filter.filter_type in ['DescriptiveTextAndImagesFilter', 'ColorFilter',
                                                       'TextOnlyFilter']:
                    return space.values.all()
                elif field.matrix_filter.filter_type in ['NumberFilter']:
                    return ['%g' %(float(i)) for i in space.encoded_space]
                else:
                    return space.encoded_space

        return None

    # the database does not allow 2 nodes with the same name for a NatureGuidesTaxonTree
    def clean(self):

        cleaned_data = super().clean()

        name = cleaned_data.get('name', None)

        node_type = cleaned_data.get('node_type', None)

        if name and node_type == 'result':
            exists_qry = NatureGuidesTaxonTree.objects.filter(nature_guide=self.nature_guide,
                                                        meta_node__name__iexact=name,
                                                        meta_node__node_type='result')

            node_id = cleaned_data.get('node_id', None)

            if node_id:
                exists_qry = exists_qry.exclude(pk=node_id)

            exists = exists_qry.first()

            # crosslink has its own view without form, only check Tree here
            if not exists:
                sibling_exists_qry = NatureGuidesTaxonTree.objects.filter(
                    nature_guide=self.nature_guide, meta_node__name__iexact=name,
                    parent=self.submitted_parent_node)

                exists = sibling_exists_qry.first()

            ''' currently, duplicates are allowed
            if exists:
                self.add_error('name',_('A node with the name {0} already exists'.format(
                    exists.meta_node.name)))
            '''
        ''' currently, 'name' is required
        decision_rule = cleaned_data.get('decision_rule', None)

        if not name and not decision_rule:
            if 'name' in cleaned_data:
                del cleaned_data['name']
                
            self.add_error('name', _('You have to enter at least a name or a decision rule.'))
        '''
        
        return cleaned_data



class ManageMatrixFilterRestrictionsForm(MatrixFilterValueChoicesMixin, forms.Form):

    show_add_button = False

    def __init__(self, meta_app, matrix_filter, meta_node, *args, **kwargs):

        self.meta_app = meta_app
        self.meta_node = meta_node
        self.matrix_filter = matrix_filter

        self.from_url = kwargs.pop('from_url')

        super().__init__(*args, **kwargs)

        self.add_matrix_filter_value_choices()


    def get_matrix_filters(self):
        matrix_filters = MatrixFilter.objects.filter(meta_node=self.meta_node).exclude(pk=self.matrix_filter.pk)
        return matrix_filters


    # only called if field has a matrix filter assigned to field.matrix_filter
    def get_matrix_filter_field_initial(self, field):

        restriction = MatrixFilterRestriction.objects.filter(restricted_matrix_filter=self.matrix_filter,
                                                        restrictive_matrix_filter=field.matrix_filter).first()
        
        if restriction:
            
            if field.matrix_filter.filter_type in ['DescriptiveTextAndImagesFilter', 'ColorFilter',
                                                   'TextOnlyFilter']:

                space = restriction.values.filter(matrix_filter=field.matrix_filter)

                if space:
                    return space
                
            elif field.matrix_filter.filter_type in ['NumberFilter']:
                return ['%g' %(float(i)) for i in restriction.encoded_space]
            else:
                return restriction.encoded_space

        return None
        


class MoveNodeForm(LocalizeableForm):

    localizeable_fields = ['search_group_name']
    search_group_name = forms.CharField(label=_('Name of new group'), required=False,
                                       help_text=_('Search whole tree for a group.'))

    new_parent_node_id = forms.IntegerField(widget=forms.HiddenInput, label=_('New group'))


    def __init__(self, child_node, old_parent_node, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.child_node = child_node
        self.old_parent_node = old_parent_node

    def downstream_crosslink_exists(self):

        downstream_crosslinks_exist = False
        
        # check if downstream crosslinks exist
        crosslinks = NatureGuideCrosslinks.objects.filter(parent__nature_guide=self.old_parent_node.nature_guide)

        child_taxon_nuid = self.child_node.taxon_nuid

        for crosslink in crosslinks:
            if crosslink.parent.taxon_nuid.startswith(child_taxon_nuid) or crosslink.child.taxon_nuid.startswith(child_taxon_nuid):
                downstream_crosslinks_exist = True
                break

        return downstream_crosslinks_exist
        

    # check circularity
    def clean(self):

        cleaned_data = super().clean()

        new_parent_node_id = cleaned_data.get('new_parent_node_id', None)

        if new_parent_node_id:

            new_parent_node = NatureGuidesTaxonTree.objects.get(pk=new_parent_node_id)

            
            if self.downstream_crosslink_exists():

                if self.child_node.nature_guide != new_parent_node.nature_guide:
                    del cleaned_data['new_parent_node_id']
                    self.add_error('new_parent_node_id',
                                _('Moving {0} to {1} ({2}) is forbidden because the branch contains crosslinks.'.format(
                                    self.child_node, new_parent_node, new_parent_node.nature_guide)))

            
            is_valid = self.child_node.move_to_is_valid(new_parent_node)

            if not is_valid:
                if 'new_parent_node_id' in cleaned_data:
                    del cleaned_data['new_parent_node_id']
                self.add_error('new_parent_node_id',
                            _('Moving {0} to {1} would result in an invalid tree.'.format(
                                self.child_node, new_parent_node)))

        return cleaned_data
        


class CopyTreeBranchForm(forms.Form):

    branch_name = forms.CharField(label=_('Name of copy'), help_text=_('Name of the copy.'),
                                  max_length=TEXT_LENGTH_RESTRICTIONS['MetaNode']['name'])

    prevent_crosslinks = forms.BooleanField(required=False,
        help_text=_('Creates a copy of each identification result instead of a crosslink. This results in 2 separate entities for each result. Only use this function if you know what you are doing.'))
