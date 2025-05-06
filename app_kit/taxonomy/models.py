from django.conf import settings

from django.db import models
from django.utils.translation import gettext_lazy as _

from localcosmos_server.slugifier import create_unique_slug

from django.apps import apps

import uuid

'''
    LocalCosmos Taxonomic Concept
    - a taxon is unique by latname & author
    - we do not expect the taxonomic sources (col etc) to maintain peristent IDs
    - synonyms do not have locales, only tree entries have locales
    - synonyms do not have ranks, they have the same rank like their primrary name
    - synonyms are not part of the tree (TaxonTree), stored in separate Table - enabling cascade delete if a tree entry is deleted
    - synonyms have to point to exactly one taxon in the tree, not multiple (strict tree, no duplicates via synonym)
    - synonyms are just other, secondary LATIN names WITH authors for a tree entry
    - for searching, the NamesView is created
    - name_uuid might change across tree updates
'''

'''
    Abstract Models for subclassing in taxonomy/sources
'''

'''
    The Taxon table is optimized for quick searches - all names are present with nuids
    in a set of taxa with the same nuid only one may have is_primary = True
'''

class TaxonTreeManager(models.Manager):

    def create(self, nuid, taxon_latname, taxon_author, source_id, **extra_fields):

        slug_base = '{0} {1}'.format(taxon_latname, taxon_author)

        slug = create_unique_slug(slug_base, 'slug', self.model)

        instance = self.model(
            taxon_nuid=nuid,
            taxon_latname=taxon_latname,
            taxon_author=taxon_author,
            slug=slug,
            source_id=source_id,
            **extra_fields
        )

        instance.save()

        return instance
        

'''
    use the same columns as in taxonomy.generic.py
    - name_uuid (=primary key in materialized view) 
    - taxon_nuid
    - taxon_latname

    the source is constant for each taxonomy database and not added to the db
'''
class TaxonTree(models.Model):

    # each name gets its own uuid - this is necessary to have a unique ID across latname, synonym and vernacular name
    name_uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    # parent is redundant, its purpose is models.PROTECT to prevent integrity errors
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True)
    
    taxon_latname = models.CharField(max_length=255) # latin name, or LAnguage independanT name, if someone adds a new taxon, this will be the latname
    taxon_author = models.CharField(max_length=255, null=True)
    
    taxon_nuid = models.CharField(max_length=255, unique=True)
    rank = models.CharField(max_length=255, null=True)

    is_root_taxon = models.BooleanField(default=False) # maybe not all trees start with '001' in the future
    
    slug = models.SlugField(unique=True, null=True, max_length=100)

    source_id = models.CharField(max_length=255, unique=True) # has to be unique, needed for set_nuid_from_db during tree travelling

    additional_data = models.JSONField(null=True)

    objects = TaxonTreeManager()


    def save(self, *args, **kwargs):
        if self.is_root_taxon == False and not self.parent:
            raise ValueError('non-root taxa require a parent')

        super().save(*args, **kwargs)
        

    def __str__(self):
        return self.taxon_latname

    class Meta:
        abstract=True


'''
    Synonyms are stored in a separate Table
    taxon = models.ForeignKey(TaxonTree)
'''
class TaxonSynonymManager(models.Manager):

    def create(self, taxon, taxon_latname, taxon_author, source_id, **extra_fields):

        slug = create_unique_slug(taxon_latname, 'slug', self.model)

        instance = self.model(
            taxon=taxon,
            taxon_latname=taxon_latname,
            taxon_author=taxon_author,
            slug=slug,
            source_id=source_id,
            **extra_fields
        )

        instance.save()

        return instance
        

class TaxonSynonym(models.Model):

    name_uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    
    taxon_latname = models.CharField(max_length=255)    
    taxon_author = models.CharField(max_length=255, null=True)
    
    slug = models.SlugField(unique=True, null=True, max_length=100)

    source_id = models.CharField(max_length=255) # needed because they can be attached to SourceTaxon instances

    additional_data = models.JSONField(null=True)

    objects = TaxonSynonymManager()

    def __str__(self):
        return self.taxon_latname

    class Meta:
        abstract=True
        

class TaxonLocaleManager(models.Manager):

    def create(self, taxon, name, language, preferred=False):

        if preferred == True:
            old_preferred = self.filter(taxon=taxon, language=language, preferred=True)

            for locale in old_preferred:
                locale.preferred = False
                locale.save()

        else:
            preferred_exists = self.filter(taxon=taxon, language=language, preferred=True).exists()
            
            if not preferred_exists:
                preferred = True


        slug = create_unique_slug(name, 'slug', self.model)

        instance = self.model(
            taxon=taxon,
            name=name,
            language=language,
            preferred=preferred,
            slug=slug,
        )

        instance.save()

        return instance
        

class TaxonLocale(models.Model):

    name_uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=255)
    language = models.CharField(max_length=2) # iso 6391, maxlen 2, en, de, fr,...
    iso6392 = models.CharField(max_length=3, null=True)
    language_region = models.CharField(max_length=5, null=True) # something like en_US, de_DE
    preferred = models.BooleanField(default=False)
    slug = models.SlugField(unique=True, null=True, max_length=100)

    additional_data = models.JSONField(null=True)

    objects = TaxonLocaleManager()

    def __str__(self):
        return '%s' %(self.name)

    class Meta:
        abstract = True
        # unique_together = ('taxon', 'name', 'language') # it is the responsibility of the provider to not offer duplicates, col has some duplicates


'''
    Views for faster searching
'''
NAME_TYPES = (
    ('taxontree', 'TaxonTree'),
    ('synonym', 'TaxonSynonym'),
    ('locale', 'TaxonLocale'),
)

'''
    PostgreSQL Materialized View
    - cannot have a primary key in the db, primary key on django model is a workaround
'''
class TaxonNamesView(models.Model):
    
    name_uuid = models.UUIDField(primary_key=True, unique=True, editable=False)
    taxon_latname = models.CharField(max_length=355)
    taxon_author = models.CharField(max_length=100, null=True)
    taxon_nuid = models.CharField(max_length=255)

    name = models.CharField(max_length=255) # latname or vernacular name
    
    language = models.CharField(max_length=5, null=True)

    # points to the origin of the name
    name_type = models.CharField(max_length=100, choices=NAME_TYPES)
    
    rank = models.CharField(max_length=255, null=True)

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        abstract=True



'''
    Taxonomic models can never be imported directly
    a router is needed to point at the correct model
'''
class TaxonomyModelRouter:

    def __init__(self, source):

        self.source = source

        self.TaxonTreeModel = self.get_taxontree_model(source)
        self.TaxonLocaleModel = self.get_taxonlocale_model(source)
        self.TaxonSynonymModel = self.get_taxonsynonym_model(source)
        self.TaxonNamesModel = self.get_taxonnames_model(source)

    def import_taxonomy_class(self, source, classname):
        path = '{0}.models'.format(source)
        m = __import__(path, globals(), locals(), [classname])
        return getattr(m, classname)


    def get_model_prefix(self, source):
        model_prefix = (' ').join(source.split('.')[-1].split('_')).title().replace(' ','')
        return model_prefix
    

    def get_taxontree_model(self, source):
        prefix = self.get_model_prefix(source)
        classname = '{0}TaxonTree'.format(prefix)

        return self.import_taxonomy_class(source, classname)


    def get_taxonlocale_model(self, source):
        prefix = self.get_model_prefix(source)
        classname = '{0}TaxonLocale'.format(prefix)

        return self.import_taxonomy_class(source, classname)


    def get_taxonsynonym_model(self, source):
        prefix = self.get_model_prefix(source)
        classname = '{0}TaxonSynonym'.format(prefix)

        return self.import_taxonomy_class(source, classname)


    def get_taxonnames_model(self, source):
        prefix = self.get_model_prefix(source)
        classname = '{0}TaxonNamesView'.format(prefix)

        return self.import_taxonomy_class(source, classname)
        

'''
    writeable storage for adding custom taxonomic names to sources other than CustomTaxonomy
    e.g. for supplying vernacular names for COL
'''
class MetaVernacularNames(models.Model):
    
    taxon_latname = models.CharField(max_length=255)
    taxon_author = models.CharField(max_length=255, null=True) 
    taxon_source = models.CharField(max_length=255, choices=settings.TAXONOMY_DATABASES)
    taxon_nuid = models.CharField(max_length=255)
    name_uuid = models.UUIDField()

    language = models.CharField(max_length=15)
    name = models.CharField(max_length=255)
    preferred = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        
        if self.preferred == True:
            
            old_primaries = self.__class__.objects.filter(
                taxon_source=self.taxon_source, name_uuid=self.name_uuid,
                preferred=True)
            
            if self.pk:
                old_primaries.exclude(pk=self.pk)
                
            old_primaries.update(preferred=False)
        
        super().save(*args, **kwargs)
       
        
    def __str__(self):
        return self.name


    class Meta:
        unique_together = ('taxon_source', 'taxon_latname', 'taxon_author', 'language', 'name')

        indexes = [
            models.Index(fields=['taxon_source', 'taxon_latname', 'taxon_author']),
        ]
