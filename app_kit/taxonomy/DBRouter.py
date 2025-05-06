# do not add custom to installed sources - custom taxonomy is writeable and not managed by this router
INSTALLED_SOURCES = ['col', 'algaebase']

'''
    in general, django has read and write access to the database during development
    after bulding localcosmos the taxonomy database is read only
'''
class TaxonomyRouter:
    """
    A router to control all database operations on models in the
    taxonomy application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read taxonomy models go to taxonomy_db.
        """
        if model._meta.app_label in INSTALLED_SOURCES:
            return 'taxonomy_db'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write taxonomy models go to taxonomy_db.
        """
        if model._meta.app_label in INSTALLED_SOURCES:
            return 'taxonomy_db'
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure all taxonomy sources only appear in the 'taxonomy_db'
        database.
        """
        if app_label in INSTALLED_SOURCES:
            if db == 'taxonomy_db':
                return True

            return False
        
        return None
