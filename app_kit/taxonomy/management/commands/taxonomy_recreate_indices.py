'''
    This command recreates all indices, including primary key index, of a taxonomic database
    usage: python manage.py taxonomy_recreate_indices taxonomy.sources.col public
'''
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from django.db import connections

from taxonomy.DBRouter import TaxonomyRouter
from taxonomy.models import TaxonomyModelRouter

class Command(BaseCommand):
    help = 'Create taxonomic materialized views.'

    def add_arguments(self, parser):
        parser.add_argument('database', type=str)
        parser.add_argument('schema', type=str)

    def handle(self, *args, **options):

        database = options['database']

        supported_databases = [d[0] for d in settings.TAXONOMY_DATABASES]

        if database not in supported_databases:
            raise CommandError('Database "{0}" is not supported, have you set it in your settings.py ?'.format(database))

        schema = options['schema']

        # first, create the view
        models = TaxonomyModelRouter(database)
        dbrouter = TaxonomyRouter()

        db_name = dbrouter.db_for_write(models.TaxonTreeModel)

        sql = '''SELECT tablename, indices FROM (
                    SELECT tablename, array_agg(indexname) AS indices
                FROM pg_indexes
                WHERE schemaname = '{0}'
                GROUP BY tablename) as sub;
        '''.format(schema)

        with connections[db_name].cursor() as cursor:
            cursor.execute(sql)
            query = cursor.fetchall()


        for result in query:

            table_name = result[0]
            indexlist = result[1]

            print('{0} {1}'.format(table_name, indexlist))

            # delete all indices IF the table_name is not django_migrations
            for index in indexlist:
                drop_constraint_sql = 'ALTER TABLE {0}.{1} DROP CONSTRAINT IF EXISTS {2} CASCADE'.format(schema, table_name, index)
                with connections[db_name].cursor() as cursor:
                    cursor.execute(drop_constraint_sql)
                    
                drop_index_sql = 'DROP INDEX IF EXISTS {0}.{1} CASCADE'.format(schema, index)
                with connections[db_name].cursor() as cursor:
                    cursor.execute(drop_index_sql)

                print('dropped {0}'.format(index))

        # first, fix the django migrations contraints and indexes
        django_migrations_pkey_sql = 'ALTER TABLE public.django_migrations ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id)'
        with connections[db_name].cursor() as cursor:
            cursor.execute(django_migrations_pkey_sql)

        # recreate all indices - _XXtaxontree, _XXtaxonsynonyms, _XXtaxonlocale
        prefix = database.split('.')[-1]
        taxontree_table = '{0}_{1}taxontree'.format(prefix, prefix)
        taxonlocale_table = '{0}_{1}taxonlocale'.format(prefix, prefix)
        taxonsynonym_table = '{0}_{1}taxonsynonym'.format(prefix, prefix)

        tables = [taxontree_table, taxonlocale_table, taxonsynonym_table]

        # first, create all primary keys
        for table in tables:
            primary_key_sql = 'ALTER TABLE {0}.{1} ADD CONSTRAINT {1}_id_pk PRIMARY KEY(id)'.format(schema, table)

            with connections[db_name].cursor() as cursor:
                cursor.execute(primary_key_sql)

            # add slug unique
            slug_unique_sql = 'ALTER TABLE {0}.{1} ADD CONSTRAINT {1}_slug_unique UNIQUE(slug)'.format(schema, table)
            with connections[db_name].cursor() as cursor:
                cursor.execute(slug_unique_sql)

        # uuid unique
        name_uuid_unique_sql = 'ALTER TABLE {0}.{1} ADD CONSTRAINT {1}_name_uuid_unique UNIQUE(name_uuid)'.format(schema, taxontree_table)
        with connections[db_name].cursor() as cursor:
            cursor.execute(name_uuid_unique_sql)

        # nuid unique
        taxon_nuid_unique_sql = 'ALTER TABLE {0}.{1} ADD CONSTRAINT {1}_taxon_nuid_unique UNIQUE(taxon_nuid)'.format(schema, taxontree_table)
        with connections[db_name].cursor() as cursor:
            cursor.execute(taxon_nuid_unique_sql)


        # parent_id
        parent_id_fk_sql = '''ALTER TABLE {0}.{1} ADD CONSTRAINT {1}_parent_id_fk
                                FOREIGN KEY (parent_id) REFERENCES {0}.{1} (id) MATCH SIMPLE
                                ON UPDATE CASCADE
                                ON DELETE CASCADE;'''.format(schema, taxontree_table)

        with connections[db_name].cursor() as cursor:
            cursor.execute(parent_id_fk_sql)
            
        
        # third, create foreign keys
        for table in [taxonlocale_table, taxonsynonym_table]:
            fk_sql = '''ALTER TABLE {0}.{1} ADD CONSTRAINT {1}_{2}_taxon_id_fk FOREIGN KEY (taxon_id)
                        REFERENCES {0}.{2} (name_uuid) MATCH SIMPLE
                        ON UPDATE NO ACTION ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED'''.format(schema, table, taxontree_table)

            with connections[db_name].cursor() as cursor:
                cursor.execute(fk_sql)

            taxon_id_idx_sql = '''CREATE INDEX fki_{0}_coltaxontree_taxon_id_fk ON {1}.{0}
                                  USING btree (taxon_id)'''.format(table, schema)

            with connections[db_name].cursor() as cursor:
                cursor.execute(taxon_id_idx_sql)

        # fourth, create indices
        nuid_idx_sql = 'CREATE INDEX {0}_taxon_nuid_btree_idx  ON {1}.{0} USING btree (taxon_nuid COLLATE pg_catalog."default")'.format(taxontree_table, schema)
        with connections[db_name].cursor() as cursor:
            cursor.execute(nuid_idx_sql)


        uuid_idx_sql = 'CREATE INDEX {0}_name_uuid_btree_idx  ON {1}.{0} USING btree (name_uuid)'.format(taxontree_table, schema)
        with connections[db_name].cursor() as cursor:
            cursor.execute(uuid_idx_sql)


        source_id_idx_sql = 'CREATE INDEX {0}_source_id_btree_idx  ON {1}.{0} USING btree (source_id COLLATE pg_catalog."default")'.format(taxontree_table, schema)
        with connections[db_name].cursor() as cursor:
            cursor.execute(source_id_idx_sql)

        for table in [taxontree_table, taxonsynonym_table]:
            searchindex_sql = '''CREATE INDEX {0}_taxon_latname_upper_btree_idx
                            ON {1}.{0} USING btree (upper(taxon_latname::text)
                            COLLATE pg_catalog."default" varchar_pattern_ops)'''.format(table, schema)

            with connections[db_name].cursor() as cursor:
                cursor.execute(searchindex_sql)

        vernacular_idx_sql = '''CREATE INDEX {0}_language_name_upper_preferred_btree_idx
                                  ON {1}.{0} USING btree (language COLLATE pg_catalog."default", upper(name::text)
                                  COLLATE pg_catalog."default", preferred)'''.format(taxonlocale_table, schema)                

        with connections[db_name].cursor() as cursor:
            cursor.execute(vernacular_idx_sql)


        # author
        for table in [taxontree_table, taxonsynonym_table]:

            taxon_author_btree_idx_sql = '''CREATE INDEX {0}_taxon_author_btree_idx ON {1}.{0} USING btree
                                            (taxon_author COLLATE pg_catalog."default" varchar_pattern_ops ASC NULLS LAST)
                                            TABLESPACE pg_default;'''.format(table, schema)
            
            with connections[db_name].cursor() as cursor:
                cursor.execute(taxon_author_btree_idx_sql)

        print('done')
        
        
