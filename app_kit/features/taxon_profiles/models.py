from django.db import models

from django.utils.translation import gettext_lazy as _, gettext as __

from django.contrib.contenttypes.fields import GenericRelation
from django.db.models.signals import post_delete
from django.dispatch import receiver

from app_kit.models import ContentImageMixin, AppKitSeoParameters
from app_kit.generic import GenericContent, PUBLICATION_STATUS

from localcosmos_server.taxonomy.generic import ModelWithRequiredTaxon
from taxonomy.lazy import LazyTaxonList, LazyTaxon

from taxonomy.models import TaxonomyModelRouter
from django.db.models import Q

'''
    The content of the feature
    - there should be an multiiple choice options choosing text types
    - default is all text types
'''
from django.contrib.contenttypes.models import ContentType
from app_kit.models import MetaAppGenericContent

from taggit.managers import TaggableManager

from django.utils import timezone

class TaxonProfiles(GenericContent):

    zip_import_supported = True

    @property
    def zip_import_class(self):
        from .zip_import import TaxonProfilesZipImporter
        return TaxonProfilesZipImporter

    # moved to options
    # enable_wikipedia = models.BooleanField(default=True)
    # default_observation_form = models.IntegerField(null=True)

    def taxa(self):
        queryset = TaxonProfile.objects.filter(taxon_profiles=self)
        return LazyTaxonList(queryset)

    def higher_taxa(self):
        return LazyTaxonList()

    def collected_taxa(self, published_only=True):

        # taxa that have explicit taxon profiles
        taxa_with_profile = TaxonProfile.objects.filter(taxon_profiles=self)
        existing_name_uuids = taxa_with_profile.values_list('name_uuid', flat=True)

        taxon_profiles_ctype = ContentType.objects.get_for_model(self)
        applink = MetaAppGenericContent.objects.get(content_type=taxon_profiles_ctype, object_id=self.pk)

        # avoid circular import the ugly way
        from app_kit.features.nature_guides.models import NatureGuide

        nature_guide_ctype = ContentType.objects.get_for_model(NatureGuide)

        nature_guide_links = MetaAppGenericContent.objects.filter(meta_app=applink.meta_app,
                                                                  content_type=nature_guide_ctype)

        taxonlist = LazyTaxonList()
        taxonlist.add(taxa_with_profile)

        for link in nature_guide_links:

            if published_only == True and link.publication_status != 'publish':
                continue
            nature_guide = link.generic_content
            nature_guide_taxa = nature_guide.taxa()
            nature_guide_taxa.exclude(name_uuid__in=existing_name_uuids)

            taxonlist.add_lazy_taxon_list(nature_guide_taxa)

        return taxonlist


    '''
    - we have to collect taxa first and then add their specific profiles
    '''
    def get_primary_localization(self, meta_app=None):
        locale = super().get_primary_localization(meta_app)

        taxon_query = TaxonProfile.objects.filter(taxon_profiles=self)
        taxa = LazyTaxonList(queryset=taxon_query)
        for lazy_taxon in taxa:

            taxon_query = {
                'taxon_source' : lazy_taxon.taxon_source,
                'taxon_latname' : lazy_taxon.taxon_latname,
                'taxon_author' : lazy_taxon.taxon_author,
            }

            taxon_profile = TaxonProfile.objects.filter(taxon_profiles=self, **taxon_query).first()

            if taxon_profile:

                for text in taxon_profile.texts():

                    # text_type_key = 'taxon_text_{0}'.format(text.taxon_text_type.id)
                    # short: use name as key (-> no duplicates in translation matrix)
                    text_type_key = text.taxon_text_type.text_type
                    locale[text_type_key] = text.taxon_text_type.text_type
                    
                    # text.text is a bad key, because if text.text changes, the translation is gone
                    # text.text are long texts, so use a different key which survives text changes
                    # locale[text.text] = text.text

                    short_text_key = self.get_short_text_key(text)

                    if text.text:
                        locale[short_text_key] = text.text

                    long_text_key = self.get_long_text_key(text)

                    if text.long_text:
                        locale[long_text_key] = text.long_text

                content_images_primary_localization = taxon_profile.get_content_images_primary_localization()
                locale.update(content_images_primary_localization)
        
        navigation = TaxonProfilesNavigation.objects.filter(taxon_profiles=self).first()
        
        if navigation:
            navigation_entries = TaxonProfilesNavigationEntry.objects.filter(navigation=navigation)
            
            for navigation_entry in navigation_entries:
                if navigation_entry.name and navigation_entry.name not in locale:
                    locale[navigation_entry.name] = navigation_entry.name
                    
                if navigation_entry.description and navigation_entry.description not in locale:
                    locale[navigation_entry.description] = navigation_entry.description
                    
        categories = TaxonTextTypeCategory.objects.filter(taxon_profiles=self)
        for category in categories:
            if category.name not in locale:
                locale[category.name] = category.name
        return locale


    def get_short_text_key(self, text):
        text_key = 'taxon_text_{0}_{1}'.format(text.taxon_text_type.id, text.id)
        return text_key

        
    def get_long_text_key(self, text):
        text_key = 'taxon_text_{0}_{1}_long'.format(text.taxon_text_type.id, text.id)
        return text_key


    class Meta:
        verbose_name = _('Taxon profiles')
        verbose_name_plural = _('Taxon profiles')


FeatureModel = TaxonProfiles


'''
    TaxonProfile
'''
class TaxonProfile(ContentImageMixin, ModelWithRequiredTaxon):

    LazyTaxonClass = LazyTaxon

    taxon_profiles = models.ForeignKey(TaxonProfiles, on_delete=models.CASCADE)
    
    short_profile = models.TextField(null=True)

    publication_status = models.CharField(max_length=100, null=True, choices=PUBLICATION_STATUS)
    
    is_featured = models.BooleanField(default=False)

    tags = TaggableManager()
    
    seo_parameters = GenericRelation(AppKitSeoParameters)
    
    updated_at = models.DateTimeField(auto_now=True)

    def texts(self):
        return TaxonText.objects.filter(taxon_profile=self).order_by('taxon_text_type__position')
    
    def categorized_texts(self):
        
        categorized_texts = {
            'uncategorized' : TaxonText.objects.filter(taxon_profile=self,
                        taxon_text_type__category=None).order_by('taxon_text_type__position'),
        }
        
        categories = TaxonTextTypeCategory.objects.filter(taxon_profiles=self.taxon_profiles)
        
        for category in categories:
            query = TaxonText.objects.filter(taxon_profile=self,
                        taxon_text_type__category=category).order_by('taxon_text_type__position')
            

            categorized_texts[category.name] = query
        
        return categorized_texts

    '''
    this checks taxon texts and vernacularnames[latter missing]
    '''
    def profile_complete(self):

        text_types = TaxonTextType.objects.filter(taxon_profiles=self.taxon_profiles)

        for text_type in text_types:

            taxon_text = TaxonText.objects.filter(taxon_profile=self, taxon_text_type=text_type).first()

            if not taxon_text or len(taxon_text.text) == 0:
                return False
            
        return True


    def __str__(self):
        return 'Taxon Profile of {0}'.format(self.taxon)
    

    class Meta:
        # unique_together=('taxon_source', 'taxon_latname', 'taxon_author')
        unique_together=('taxon_profiles', 'taxon_source', 'name_uuid')
        verbose_name = _('Taxon Profile')
        verbose_name_plural = _('Taxon Profiles')
        
        
# Signal to clean up SeoParameters
@receiver(post_delete, sender=TaxonProfile)
def delete_seo_parameters(sender, instance, **kwargs):
    content_type = ContentType.objects.get_for_model(instance)
    AppKitSeoParameters.objects.filter(
        content_type=content_type,
        object_id=instance.id
    ).delete()


class TaxonTextTypeCategory(models.Model):
    
    taxon_profiles = models.ForeignKey(TaxonProfiles, on_delete=models.CASCADE)
    name = models.CharField(max_length=355)
    position = models.IntegerField(default=0)
    
    def __str__(self):
        return '{0}'.format(self.name)

    class Meta:
        unique_together = ('taxon_profiles', 'name')
        ordering = ['position']


class TaxonTextType(models.Model):

    taxon_profiles = models.ForeignKey(TaxonProfiles, on_delete=models.CASCADE)
    text_type = models.CharField(max_length=255) # the name of the text_type
    category = models.ForeignKey(TaxonTextTypeCategory, null=True, blank=True, on_delete=models.SET_NULL)
    position = models.IntegerField(default=0)
    
    def __str__(self):
        return '{0}'.format(self.text_type)

    class Meta:
        unique_together = ('taxon_profiles', 'text_type')
        ordering = ['category', 'position']


class TaxonText(ContentImageMixin, models.Model):
    taxon_profile = models.ForeignKey(TaxonProfile, on_delete=models.CASCADE)
    taxon_text_type = models.ForeignKey(TaxonTextType, on_delete=models.CASCADE)

    text = models.TextField(null=True)

    long_text = models.TextField(null=True)

    position = models.IntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('taxon_profile', 'taxon_text_type',)



'''
    A taxonomic navigation using a simplified, manually created taxonomic tree
'''
class TaxonProfilesNavigation(models.Model):
    taxon_profiles = models.OneToOneField(TaxonProfiles, on_delete=models.CASCADE)
    last_modified_at = models.DateTimeField(null=True)
    
    prerendered = models.JSONField(null=True)
    last_prerendered_at = models.DateTimeField(null=True)
    
    
    def prerender(self):
        prerendered = {
            'tree': [],
        }
        
        root_elements = TaxonProfilesNavigationEntry.objects.filter(navigation=self, parent=None)
        
        for root_element in root_elements:
            root_dict = root_element.as_dict()
            prerendered['tree'].append(root_dict)
            
        self.prerendered = prerendered
        self.last_prerendered_at = timezone.now()
        self.save(prerendered=True)
        
    @property
    def taxa(self):
        taxa = []
        entries = TaxonProfilesNavigationEntry.objects.filter(navigation=self)
        for entry in entries:
            taxa = taxa + list(entry.taxa)
        return taxa
    
    def get_terminal_nodes(self):
        terminal_nodes = []
        
        all_nodes = TaxonProfilesNavigationEntry.objects.filter(navigation=self)
        for node in all_nodes :
            
            if not node.children:
                terminal_nodes.append(node)
                
        return terminal_nodes
        
        
    def save(self, *args, **kwargs):
        
        prerendered = kwargs.pop('prerendered', False)
        
        if prerendered == False:
            self.last_modified_at = timezone.now()
            
        super().save(*args, **kwargs)
        
    def __str__(self):
        return __('Taxonomic Navigation')
            


'''
    The entries should cover more than one taxonomic source
    - the taxon is identified by latname, author (optional) and rank
    - ModelWihTaxon is not used to not restrict it to one taxonomic source
    - during build, the taxon is looked up in all taxonomic sources for each endpoint and the matching taxon profiles are added
'''
class TaxonProfilesNavigationEntry(ContentImageMixin, models.Model):
    navigation = models.ForeignKey(TaxonProfilesNavigation, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=355, null=True)
    description = models.TextField(null=True)
    
    publication_status = models.CharField(max_length=100, default='publish', choices=PUBLICATION_STATUS)
    
    position = models.IntegerField(default=0)
    
    @property
    def key(self):
        return 'tpne-{0}'.format(self.id)
    
    def as_dict(self):
        
        children = [child.as_dict() for child in self.children]
        
        navigation_entry_content_type = ContentType.objects.get_for_model(TaxonProfilesNavigationEntry)
        
        images = []
        
        for image in self.images():
            
            image = {
                'id': image.id,
                'url': image.image_url(),
            }
            
            images.append(image)
            
        
        taxa = []
        
        for taxon_link in self.taxa:
            taxa.append(taxon_link.taxon.as_typeahead_choice())
        
        dic = {
            'id': self.id,
            'content_type_id': navigation_entry_content_type.id,
            'key': self.key,
            'parent_id': None,
            'parent_key': None,
            'taxa': taxa,
            'verbose_name': '{0}'.format(self.__str__()),
            'name' : self.name,
            'description': self.description,
            'children': children,
            'images': images,
            'publication_status' : self.publication_status,
        }
        
        if self.parent:
            dic.update({
                'parent_id': self.parent.id,
                'parent_key': self.parent.key,
            })
        
        return dic
    
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.navigation.save()
    
    def change_publication_status(self, new_status):
        # Get all descendants
        descendants = self.get_descendants()
            
        # Update this node and all descendants in a single query
        TaxonProfilesNavigationEntry.objects.filter(
            models.Q(id=self.id) | models.Q(id__in=descendants.values_list('id', flat=True))
        ).update(publication_status=new_status)
        
        self.refresh_from_db()
    
    def publish(self):
        self.change_publication_status('publish')
    
    def unpublish(self):
        self.change_publication_status('draft')
    
    @property
    def children(self):
        return TaxonProfilesNavigationEntry.objects.filter(parent=self)
    
    @property
    def taxa(self):
        return TaxonProfilesNavigationEntryTaxa.objects.filter(navigation_entry=self)
    
    @property
    def matching_custom_taxa(self):
        matching_custom_taxa = []
        
        custom_taxonomy_name = 'taxonomy.sources.custom'
        custom_taxonomy_models = TaxonomyModelRouter(custom_taxonomy_name)
        
        existing_custom_taxa = self.taxa.filter(taxon_source=custom_taxonomy_name)
        
        for taxon_link in self.taxa.exclude(taxon_source=custom_taxonomy_name):
                
            search_kwargs = {
                'taxon_latname' : taxon_link.taxon_latname
            }

            if taxon_link.taxon_author:
                search_kwargs['taxon_author'] = taxon_link.taxon_author

            custom_taxa = custom_taxonomy_models.TaxonTreeModel.objects.filter(
                **search_kwargs)
            
            
            for custom_taxon in custom_taxa:
                if custom_taxon not in existing_custom_taxa:
                    matching_custom_taxa.append(custom_taxon)
            
        return matching_custom_taxa
    
    
    @property
    def combined_taxa(self):
        combined_taxa = []
        
        for taxon in self.taxa:
            lazy_taxon = LazyTaxon(instance=taxon)
            combined_taxa.append(lazy_taxon)
            
        for custom_taxon in self.matching_custom_taxa:
            lazy_custom_taxon = LazyTaxon(instance=custom_taxon)
            combined_taxa.append(lazy_custom_taxon)
            
        return combined_taxa
        
    
    '''
        attached taxon profiles are
        - all taxa that are descendants of this node's taxa and that are NOT covered by a subgroup (or a subgroup downards the branch)
    '''
    
    def get_descendants(self):
        
        cte_query = """
            WITH RECURSIVE descendants AS (
                SELECT id, parent_id
                FROM {table_name}
                WHERE id = %(node_id)s
                UNION ALL
                SELECT tn.id, tn.parent_id
                FROM {table_name} tn
                INNER JOIN descendants d ON tn.parent_id = d.id
            )
            SELECT id FROM descendants WHERE id != %(node_id)s
        """.format(table_name=self._meta.db_table)
        
        # Execute with params as a dictionary
        params = {'node_id': self.id}
        descendant_ids = [node.id for node in TaxonProfilesNavigationEntry.objects.raw(cte_query, params)]
        
        return TaxonProfilesNavigationEntry.objects.filter(id__in=descendant_ids)
        
    
    @property
    def attached_taxon_profiles(self):
        
        taxon_profiles = []
        
        if not self.taxa:
            return []
        
        descendants = self.get_descendants()
        
        subgroups_taxa = []
        for descendant in descendants:
            subgroups_taxa = subgroups_taxa + descendant.combined_taxa
            
        # if a taxon is a descendant of this node's taxa and NOT a descendat of subgroups_taxa
        # it is an attached taxon profile

        custom_taxonomy_name = 'taxonomy.sources.custom'
        custom_taxonomy_models = TaxonomyModelRouter(custom_taxonomy_name)
        
        q_objects = Q()
        
        for taxon_link in self.taxa:
            
            q_objects |= Q(taxon_source=taxon_link.taxon_source,
                           taxon_nuid__startswith=taxon_link.taxon_nuid)
            
            if taxon_link.taxon_source != 'taxonomy.sources.custom':
                
                search_kwargs = {
                    'taxon_latname' : taxon_link.taxon_latname
                }

                if taxon_link.taxon_author:
                    search_kwargs['taxon_author'] = taxon_link.taxon_author

                custom_parent_taxa = custom_taxonomy_models.TaxonTreeModel.objects.filter(
                    **search_kwargs)
                
                for custom_parent_taxon in custom_parent_taxa:
                    
                    q_objects |= Q(taxon_source=custom_taxonomy_name,
                                   taxon_nuid__startswith=custom_parent_taxon.taxon_nuid)
                    
        final_q = Q(taxon_profiles=self.navigation.taxon_profiles) & q_objects
        taxon_profile_candidates = TaxonProfile.objects.filter(final_q)
        
        for candidate in taxon_profile_candidates:
            candidate_exists_in_subgroup = False
            for subgroup_taxon in subgroups_taxa:
                if candidate.taxon_source == subgroup_taxon.taxon_source:
                    if candidate.taxon_nuid.startswith(subgroup_taxon.taxon_nuid):
                        candidate_exists_in_subgroup = True
                        break
            
            if candidate_exists_in_subgroup == False:
                taxon_profiles.append(candidate)
                
        return taxon_profiles

    
    @property
    def branch(self):
        branch = [self]
        
        parent = self.parent
        
        while parent:
            branch.append(parent)
            parent = parent.parent
            
        branch.reverse()
        
        return branch
    
    
    def __str__(self):
        
        if self.name:
            return '{0}'.format(self.name)
        
        taxa = self.taxa
        if taxa:
            taxon_latnames = [t.taxon_latname for t in taxa]
            return ', '.join(taxon_latnames)
        
        return __('Unconfigured navigation entry')    
    
    class Meta:
        ordering = ('position', 'name')
        

class TaxonProfilesNavigationEntryTaxa(ModelWithRequiredTaxon):
    navigation_entry = models.ForeignKey(TaxonProfilesNavigationEntry, on_delete=models.CASCADE)
    
    def __str__(self):
        return '{0} {1}'.format(self.taxon_latname, self.taxon_author)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.navigation_entry.navigation.save()
    
    class Meta:
        unique_together=('navigation_entry', 'name_uuid')
        verbose_name = _('Taxon Profiles Navigation Entry Taxon')
    