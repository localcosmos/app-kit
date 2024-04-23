from django.core.management.base import BaseCommand

from app_kit.features.nature_guides.models import NatureGuidesTaxonTree

import logging, os

class Command(BaseCommand):
    
    help = 'Fix broken Nature Guide Trees where node.taxon_nuid does not match node.nature_guide'


    def get_logger(self):

        logger = logging.getLogger('app_kit')
        logging_folder = '/var/log/localcosmos/app_kit/'

        if not os.path.isdir(logging_folder):
            os.makedirs(logging_folder)

        log_filename = 'fix_nature_guide_trees'

        logfile_path = os.path.join(logging_folder, log_filename)

        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

        # add FileHandler
        file_hdlr = logging.FileHandler(logfile_path)
        file_hdlr.setFormatter(formatter)
        file_hdlr.setLevel(logging.INFO)
        logger.addHandler(file_hdlr)

        logger.setLevel(logging.INFO)

        return logger


    def handle(self, *args, **options):

        logger = self.get_logger()

        root_nodes = NatureGuidesTaxonTree.objects.filter(taxon_nuid__length=6)

        changed_nodes = 0
        changed_meta_nodes = 0

        for root_node in root_nodes:

            descendants = NatureGuidesTaxonTree.objects.filter(taxon_nuid__startswith=root_node.taxon_nuid).exclude(
                taxon_nuid=root_node.taxon_nuid)

            for descendant in descendants:

                if descendant.nature_guide != root_node.nature_guide:

                    old_nature_guide = descendant.nature_guide

                    descendant.nature_guide = root_node.nature_guide
                    descendant.save(descendant.parent)

                    changed_nodes += 1
                    logger.info('Assigning new nature guide to NatureGuidesTaxonTree instance {0} (id:{1}). Old Nature Guide: {2} (id:{3}) . New Nature Guide: {4} (id:{5})'.format(
                        descendant.meta_node.name, descendant.id, old_nature_guide, old_nature_guide.id,
                        root_node.nature_guide, root_node.nature_guide.id
                    ))

                elif descendant.meta_node.nature_guide != root_node.nature_guide:

                    old_nature_guide = descendant.meta_node.nature_guide

                    descendant.meta_node.nature_guide = root_node.nature_guide
                    descendant.meta_node.save()

                    changed_meta_nodes += 1
                    logger.info('Assigning new nature guide to MetaNode instance {0} (id:{1}). Old Nature Guide: {2} (id:{3}) . New Nature Guide: {4} (id:{5})'.format(
                        descendant.meta_node.name, descendant.meta_node.id, old_nature_guide,
                        old_nature_guide.id, root_node.nature_guide, root_node.nature_guide.id
                    ))
        
        logger.info('Done. Fixed {0} NatureGuidesTaxonTree entries and {1} MetaNode entries'.format(changed_nodes,
            changed_meta_nodes))


