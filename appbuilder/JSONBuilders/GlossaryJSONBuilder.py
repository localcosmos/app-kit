from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.glossary.models import GlossaryEntry, TermSynonym

import re, base64

from collections import OrderedDict


##############################################################################################################
#
#   The displayed glossary in the app should be sorted alphabetically
#   -> additionally build localized, sorted glossary json files
#
##############################################################################################################

class GlossaryJSONBuilder(JSONBuilder):
    

    def build(self):

        glossary_json = self._build_common_json()

        glossary_json['glossary'] = {}

        glossary = self.generic_content

        glossary_entries = GlossaryEntry.objects.filter(glossary=glossary)

        for glossary_entry in glossary_entries:

            glossary_json_entry = self.get_glossary_json_entry(glossary_entry)
            
            glossary_json['glossary'][glossary_entry.term] = glossary_json_entry
            
        return glossary_json

    
    def get_glossary_json_entry(self, glossary_entry):

        synonyms = list(glossary_entry.synonyms.values_list('term', flat=True))

        entry_json = {
            'definition' : glossary_entry.definition,
            'synonyms' : synonyms,
            'imageUrl' : self._get_image_urls(glossary_entry),
        }

        return entry_json

    # an occurring glossary term can be a synonym
    def get_occurring_glossary_terms(self):

        glossary = self.generic_content

        # first, check which glossary terms DO NOT occur in the texts
        occurring_glossary_terms = set([])
        terms_and_synonyms = glossary.get_primary_localization_terms_and_synonyms()

        primary_locale_without_glossary = {}

        # get all primary locale entries, exclude glossary
        for link in self.meta_app.features():

            generic_content = link.generic_content

            if generic_content.__class__.__name__ == 'Glossary':
                continue

            generic_content_texts = generic_content.get_primary_localization(meta_app=self.meta_app)
   
            for text_key, locale in generic_content_texts.items():

                if text_key == '_meta':
                    continue

                # simple string locale, html or plain text
                elif len(locale) > 0:
                    primary_locale_without_glossary[text_key] = locale


        for term in terms_and_synonyms:

            # new_primary_locale_translation_items do not contain glossary terms
            for text_key, localized_text in primary_locale_without_glossary.items():

                if type(localized_text) == str:
                
                    term_lower = term.lower()
                    localized_text_lower = localized_text.lower()
                    # some features produce keys liek taxon_text_1
                    if term_lower in localized_text_lower:
                        occurring_glossary_terms.add(term)
                        break

        return occurring_glossary_terms

    ##########################################################################################################
    #
    # glossarized.json language files
    # - contain links to the glossary terms
    # - glossary_json contains only the primary language
    # - b64encode glossary terms in data-term
    # - also create localized_used_terms_glossary
    ##########################################################################################################
    def glossarize_language_file(self, glossary_json, language_code):

        glossary = self.generic_content

        occurring_glossary_terms = self.get_occurring_glossary_terms()

        # provide the possibility to only browse used glossary items
        localized_used_terms_glossary = {}

        glossarized_locale = {}

        locale = self.meta_app.localizations[language_code]

        # create a list of dictionaries containing the glossary entries
        terms_and_synonyms = []
        
        # the glossary entry (term) can consist of multiple words with spaces
        # iterate over all glossary entries and find them in the text
        for term, glossary_entry in glossary_json['glossary'].items():

            localized_term = locale.get(term, term)

            term_word_count = len(localized_term.split(' '))

            term_entry = {
                'term' : term,
                'localizedTerm' : localized_term,
                'isSynonym' : False,
                'wordCount' : term_word_count,
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
                    'localizedTerm' : localized_term_synonym,
                    'realTerm' : localized_term, # localized term which this word is synonym of
                    'unlocalizedRealTerm' : term,
                    'isSynonym' : True,
                    'wordCount' : synonym_word_count,
                }

                terms_and_synonyms.append(synonym_entry)
                

        terms_and_synonyms = sorted(terms_and_synonyms, key = lambda k: k['wordCount'])
        terms_and_synonyms.reverse()
        
        # key is language independant
        for key, text in locale.items():

            # localized_content_images have a dict
            if key == '_meta' or type(text) == dict:
                continue

            # original_text ist for referencing already glossarized text parts by start index and end index
            original_text = text
            # [[0,3]]
            blocked_text_parts = []                    

            glossarized_text = text

            # iterate over all terms and synonyms, add links
            for tas_entry in terms_and_synonyms:

                term_lower = tas_entry['localizedTerm'].lower()

                term_whole_word = r'\b{0}\b'.format(term_lower)

                # first, check if the text part is blocked
                # original matches reference the plain text. These references are used to avoid multiple
                # glossarizifications. example: terms "bark" and "black bark". only black bark should be
                # glossarized in the text "a black bark is common for ..."
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


                # matches are used to iteratively add html links to text parts
                # glossarized_text is edited during this loop. therefore, original_matches are required
                # to avoid the "link in link" scenario
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
                            if tas_entry['isSynonym'] == True:
                                data_term = tas_entry['realTerm']
                            else:
                                data_term = tas_entry['term']

                            data_term_b64 = base64.b64encode(data_term.encode('utf-8')).decode('utf-8')
                                
                            glossarized_term = '<span class="glossary_link tap" action="glossary" data-term="{1}">{0}</span>'.format(match_text, data_term_b64)

                            # the match is replaced in the list, so the first occurrence of the match is the correct one
                            match_index = text_parts.index(match_text)

                            text_parts[match_index] = glossarized_term

                            # add to used_terms_glossary
                            # only add terms that occur outside of the glossary
                            # only primary language is supported in occurring_glossary_terms, so use
                            # tas_entry['term']
                            if tas_entry['term'] in occurring_glossary_terms:

                                localized_term = tas_entry['localizedTerm']
                                glossary_lookup_term = tas_entry['term']

                                if tas_entry['isSynonym'] == True:
                                    localized_term = tas_entry['realTerm']
                                    glossary_lookup_term = tas_entry['unlocalizedRealTerm']


                                start_letter = localized_term[0].upper()

                                if start_letter not in localized_used_terms_glossary:
                                    localized_used_terms_glossary[start_letter] = {}


                                if localized_term not in localized_used_terms_glossary[start_letter]:

                                    glossary_entry = glossary_json['glossary'][glossary_lookup_term]

                                    localized_glossary_entry = self.get_localized_glossary_entry(glossary_entry,
                                                                                                language_code)

                                    localized_used_terms_glossary[start_letter][localized_term] = localized_glossary_entry                            


                    glossarized_text = ''.join(text_parts)
                        

            glossarized_locale[key] = glossarized_text


        sorted_used_terms_glossary = self.sort_glossary(localized_used_terms_glossary)
                
        return glossarized_locale, sorted_used_terms_glossary


    def get_localized_glossary_entry(self, glossary_entry, language_code):

        locale = self.meta_app.localizations[language_code]

        definition = glossary_entry['definition']

        localized_definition = locale.get(definition, definition)

        localized_glossary_entry = {
            'definition' : localized_definition,
            'synonyms' : [],
            'imageUrl' : glossary_entry['imageUrl'],
        }

        for synonym in glossary_entry['synonyms']:
            localized_synonym = locale.get(synonym, synonym)
            localized_glossary_entry['synonyms'].append(localized_synonym)

        return localized_glossary_entry

    # sort by begining letters { 'A' : {}}
    def build_localized_glossary(self, glossary_json, language_code):

        localized_glossary = {}

        locale = self.meta_app.localizations[language_code]

        for term, glossary_entry in glossary_json['glossary'].items():

            localized_term = locale.get(term, term)

            localized_glossary_entry = self.get_localized_glossary_entry(glossary_entry, language_code)

            start_letter = localized_term[0].upper()

            if start_letter not in localized_glossary:
                localized_glossary[start_letter] = {}

            localized_glossary[start_letter][localized_term] = localized_glossary_entry

        localized_glossary_sorted = self.sort_glossary(localized_glossary)
        
        return localized_glossary_sorted
            

    # convert glossary to sorted OrderedDict instance
    def sort_glossary(self, glossary):

        # first, sort by start letter
        glossary_sorted_startletters = OrderedDict(sorted(glossary.items(), key=lambda x: x[0].lower()))

        glossary_sorted = OrderedDict()
        
        # second, fill glossary_sorted
        for start_letter, lettered_dict in glossary_sorted_startletters.items():

            ordered_glossary_entries = OrderedDict(sorted(lettered_dict.items(), key=lambda y: y[0].lower()))
            glossary_sorted[start_letter] = ordered_glossary_entries

        return glossary_sorted
        
    '''
    def update_used_terms_glossary(self, used_terms_glossary, tas_entry, glossary_json, language_code):

        localized_term = tas_entry['localized_term']
        glossary_lookup_term = tas_entry['term']

        if tas_entry['is_synonym'] == True:
            localized_term = tas_entry['real_term']
            glossary_lookup_term = tas_entry['unlocalized_real_term']


        start_letter = localized_term[0].upper()

        
        if start_letter not in used_terms_glossary or localized_term not in used_terms_glossary[start_letter]:

            glossary_entry = glossary_json['glossary'][glossary_lookup_term]

            localized_glossary_entry = self.get_localized_glossary_entry(glossary_entry, language_code)

            if start_letter not in used_terms_glossary:
                used_terms_glossary[start_letter] = {}
            
            used_terms_glossary[start_letter][localized_term] = localized_glossary_entry

        return used_terms_glossary
    '''


    # transform the glossary into a list of lists for creating a .csv file
    def create_glossary_for_csv(self, glossary):

        csv_rows = [['Term', 'Synonyms', 'Definition']]

        # synonyms delimiter: "|"
        for start_letter, glossary_entries in glossary.items():

            for term, glossary_entry in glossary_entries.items():

                synonyms_str = ' | '.join(glossary_entry['synonyms'])

                row = [term, synonyms_str, glossary_entry['definition']]

                csv_rows.append(row)

        return csv_rows
        
        

        
