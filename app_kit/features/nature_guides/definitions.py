from django.conf import settings

TEXT_LENGTH_RESTRICTIONS = {
    'MetaNode' : {
        'name' : 40,
        'morphotype' : 40,
    },
    'NatureGuidesTaxonTree' : {
        'decision_rule' : 40,
    },
    'MatrixFilter' : {
        'name' : 150,
    },
    'DescriptiveTextAndImages' : {
        'description' : 100,
    },
    'TextOnlyFilter' : {
        'text' : 200,
    },
    'ColorFilter' : {
        'description' : 40,
    }
}

settings_text_lengths = getattr(settings, 'APP_KIT_TEXT_LENGTH_RESTRICTIONS', {})
descriptive_text = settings_text_lengths.get('DescriptiveTextAndImages', {})
if 'description' in descriptive_text:
    TEXT_LENGTH_RESTRICTIONS['DescriptiveTextAndImages']['description'] = descriptive_text['description']