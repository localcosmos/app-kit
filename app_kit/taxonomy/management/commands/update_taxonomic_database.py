from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

'''
    this command should drop and recreate the indices and constriants of the taxonomic database
'''
class Command(BaseCommand):
    help = 'Update a taxonomic database'

    def add_arguments(self, parser):
        parser.add_argument('database', type=str)

    def handle(self, *args, **options):

        database = options['database']

        if database not in settings.TAXONOMY_DATABASES:
            raise CommandError('Database "%s" is not supported, have you set it in your settings.py ?' % database)

        

        
