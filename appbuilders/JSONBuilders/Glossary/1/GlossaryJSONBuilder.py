from app_kit.appbuilders.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.glossary.models import GlossaryEntry, TermSynonym

import re, base64


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
    # - b64encode glossary terms in data-term
    ##########################################################################################################
    def glossarize_language_file(self, glossary, glossary_json, language_code):

        glossarized_language_file = {}

        locale = self.app_release_builder.get_locale(self.meta_app, language_code,
                                                     app_version=self.app_release_builder.app_version)


        # create a list of dictionaries containing the glossary entries
        terms_and_synonyms = []
        
        # the glossary entry (term) can consist of multiple words with spaces
        # iterate over all glossary entries and find them in the text
        for term, definition in glossary_json['glossary'].items():

            localized_term = locale.get(term, term)

            term_word_count = len(localized_term.split(' '))

            term_entry = {
                'term' : term,
                'localized_term' : localized_term,
                'is_synonym' : False,
                'word_count' : term_word_count,
            }
            terms_and_synonyms.append(term_entry)

            # first, create a list of glossary terms, synonyms included

            # get the synonyms
            # the following case is possible:
            # term a - definition a, synonym:b, but b exists as term b definition b
            # in this case, do not use the synonym, because a separate definition exists

            synonyms = TermSynonym.objects.filter(glossary_entry__glossary=glossary,
                                                  glossary_entry__term=term)

            for synonym in synonyms:
                
                # check if the syonym term has its own entry. if so, skip it
                exists_as_glossary_entry = GlossaryEntry.objects.filter(glossary=glossary,
                                                                        term=synonym.term).exists()

                if exists_as_glossary_entry == True:
                    continue

                localized_term_synonym = locale.get(synonym.term, synonym.term)

                synonym_word_count = len(localized_term_synonym.split(' '))
                
                synonym_entry = {
                    'term' : synonym.term,
                    'localized_term' : localized_term_synonym,
                    'real_term' : localized_term,
                    'is_synonym' : True,
                    'word_count' : synonym_word_count,
                }

                terms_and_synonyms.append(synonym_entry)
                

        terms_and_synonyms = sorted(terms_and_synonyms, key = lambda k: k['word_count'])
        terms_and_synonyms.reverse()
        

        for key, text in locale.items():

            if key == '_meta':
                continue

            # original_text ist for referencing already glossarized text parts by start index and end index
            original_text = text
            # [[0,3]]
            blocked_text_parts = []                    

            glossarized_text = text

            # iterate over all terms and synonyms, add links
            for tas_entry in terms_and_synonyms:

                term_lower = tas_entry['localized_term'].lower()

                term_whole_word = r'\b{0}\b'.format(tas_entry['localized_term'])

                # first, check if the text part is blocked
                # original matches reference the plain text. These references are used to avoid multiple
                # glossarizifications. example: terms "bark" and "black bark". only black bark should be
                # glossarized
                original_matches = [m for m in re.finditer(term_whole_word, original_text, re.IGNORECASE)]

                allowed_match_indices = []

                if original_matches:

                    for original_match_index, original_match in enumerate(original_matches, 0):
                        original_match_start = original_match.start()
                        original_match_end = original_match.end()

                        match_is_allowed = True
                        
                        for blocked_text_part in blocked_text_parts:

                            if original_match_start > blocked_text_part[0] and original_match_start < blocked_text_part[1]:
                                match_is_allowed = False
                                break

                            if original_match_end > blocked_text_part[0] and original_match_end < blocked_text_part[1]:
                                match_is_allowed = False
                                break

                        if match_is_allowed:
                            allowed_match_indices.append(original_match_index)
                            blocked_text_parts.append([original_match_start, original_match_end])

                            
                matches = [m for m in re.finditer(term_whole_word, glossarized_text, re.IGNORECASE)]


                if matches:

                    # the glossarized_text will be split into a list
                    # eg if the glossary term is 'distribution':
                    # ['The beginning of the text ', 'distribution', ' the end of the text']
                    split_indices = [0]

                    for match in matches:

                        split_indices.append(match.start())
                        split_indices.append(match.end())

                    # split the text and isolate the matches
                    text_parts = [glossarized_text[i:j] for i,j in zip(split_indices, split_indices[1:]+[None])]

                    for match_index, match in enumerate(matches, 0):

                        if match_index in allowed_match_indices:
                            # replace by index
                            match_text = match.group(0)

                            # the glossarized term might be a synonym
                            if tas_entry['is_synonym'] == True:
                                data_term = tas_entry['real_term']
                            else:
                                data_term = tas_entry['term']

                            data_term_b64 = base64.b64encode(data_term.encode('utf-8')).decode('utf-8')
                                
                            glossarized_term = '<span class="glossary_link tap" action="glossary" data-term="{1}">{0} </span>'.format(match_text, data_term_b64)

                            # the match is replaced in the list, so the first occurrence of the match is the correct one
                            match_index = text_parts.index(match_text)

                            text_parts[match_index] = glossarized_term


                    glossarized_text = ''.join(text_parts)
                        

            glossarized_language_file[key] = glossarized_text
                
        return glossarized_language_file
        

        
