from app_kit.appbuilders.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.glossary.models import GlossaryEntry, TermSynonym

import re


class GlossaryJSONBuilder(JSONBuilder):
    

    def build(self):

        glossary_json = self._build_common_json()

        glossary_json['glossary'] = {}

        glossary = self.generic_content

        entries = GlossaryEntry.objects.filter(glossary=glossary)

        for entry in entries:            
            glossary_json['glossary'][entry.term] = entry.definition
            
            
        return glossary_json


    ##########################################################################################################
    #
    # glossarized.json language files
    # - contain links to the glossary terms
    # - glossary_json contians only the primary language 
    ##########################################################################################################
    def glossarize_language_file(self, glossary, glossary_json, language_code):

        glossarized_language_file = {}

        locale = self.app_release_builder.get_locale(self.meta_app, language_code,
                                                     app_version=self.app_release_builder.app_version)


        for key, text in locale.items():

            glossarized_text = text

            # do not glossarize the same text twice, if one glossary entry consists of 2 words and one
            # of those words is also a separate glossary entry
            found_terms = []

            # the glossary entry (term) can consist of multiple words with spaces
            # iterate over all glossary entries and find them in the text
            for term, definition in glossary_json['glossary'].items():

                localized_term = locale.get(term, term)

                terms_and_synonyms = []

                term_entry = {
                    'term' : term,
                    'localized_term' : localized_term,
                    'is_synonym' : False,
                }
                terms_and_synonyms.append(term_entry)

                # first, create a list of glossary terms, synonyms included

                # get the synonyms

                synonyms = TermSynonym.objects.filter(glossary_entry__glossary=glossary,
                                                      glossary_entry__term=term)

                for synonym in synonyms:

                    localized_term_synonym = locale.get(synonym.term, synonym.term)
                    
                    synonym_entry = {
                        'term' : synonym.term,
                        'localized_term' : localized_term_synonym,
                        'real_term' : localized_term,
                        'is_synonym' : True,
                    }

                    terms_and_synonyms.append(synonym_entry)

                # iterate over all terms and synonyms, add links
                for tas_entry in terms_and_synonyms:

                    term_lower = tas_entry['localized_term'].lower()

                    term_whole_word = r'\b{0}\b'.format(tas_entry['localized_term'])

                    matches = [m for m in re.finditer(term_whole_word, glossarized_text, re.IGNORECASE)]

                    if matches:

                        found_terms.append(term_lower)

                        # the glossarized_text will be split into a list
                        # eg if the glossary term is 'distribution':
                        # ['The beginning of the text ', 'distribution', ' the end of the text']
                        split_indices = [0]

                        for match in matches:

                            # if the match is a subterm of a term that already has been found, ignore it
                            # avoid multiple glossary links
                            skip_term = False

                            # UNTESTED:
                            #for found_term in found_terms:
                            # 
                            #    if term_lower in found_term or found_term in term_lower:
                            #        skip_term = True
                            #        break

                            if skip_term == True:
                                continue

                            split_indices.append(match.start())
                            split_indices.append(match.end())

                        # split the text and isolate the matches
                        text_parts = [glossarized_text[i:j] for i,j in zip(split_indices, split_indices[1:]+[None])]

                        for match in matches:

                            # replace by index
                            match_text = match.group(0)

                            # the glossarized term might be a synonym
                            if tas_entry['is_synonym'] == True:
                                data_term = tas_entry['real_term']
                            else:
                                data_term = tas_entry['term']
                                
                            glossarized_term = '<span class="glossary_link tap" action="glossary" data-term="{1}">{0} <img src="img/glossary_link.svg" class="glossary_icon" /></span>'.format(match_text, data_term)

                            # the match is replaced in the list, so the first occurrence of the match is the correct one
                            match_index = text_parts.index(match_text)

                            text_parts[match_index] = glossarized_term


                        glossarized_text = ''.join(text_parts)
                        

            glossarized_language_file[key] = glossarized_text
                
        return glossarized_language_file
        

        
