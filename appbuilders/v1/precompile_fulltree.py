from django.conf import settings
from taxonomy.models import TaxonTree, Taxon

import os, json

from app_kit.server_side_cursors import server_side_cursors


FULLTREE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources/fulltree/alphabet")


def _dump_taxa_by_start_letters(letters, path):
    for letter, taxon_list in letters.items():
        letter_file = os.path.join(path, "%s.json" % letter)
        with open(letter_file, "w") as f:
            json.dump(taxon_list, f, indent=4) 

def precompile_fulltree():

    # for all names, Taxon needs to be used
    #taxa = Taxon.objects.all().order_by("latname")
    taxa = TaxonTree.objects.all().order_by("latname")
    letters = {}
    current_start_letters = u"AA"

    if not os.path.isdir(FULLTREE_FOLDER):
        os.makedirs(FULLTREE_FOLDER)

    with server_side_cursors(taxa, itersize=5000):
        for taxon in taxa.iterator():

            if len(taxon.latname) == 0:
                continue
            start_letters = taxon.latname[:2].upper()

            # new start_letter -> dump and reset dict
            # avoid constructing a huge dict for huge taxon lists
            if start_letters != current_start_letters:
                
                _dump_taxa_by_start_letters(letters, FULLTREE_FOLDER)
                letters = {}
                current_start_letters = start_letters
                
            '''
            obj = {
                "nuid" : taxon.nuid(),
                "taxon_id" : taxon.id,
                "latname" : taxon.latname,
            }'''
            obj = {
                "nuid" : taxon.nuid,
                "taxon_id" : taxon.taxon_id,
                "latname" : taxon.latname,
            }
            if start_letters not in letters:
                letters[start_letters] = [obj]
            else:
                letters[start_letters].append(obj)

        # dump the last letters
        _dump_taxa_by_start_letters(letters, FULLTREE_FOLDER)
        
    
    
