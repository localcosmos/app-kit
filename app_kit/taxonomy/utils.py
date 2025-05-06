import math
from taxonomy.models import TaxonomyModelRouter
from taxonomy.lazy import LazyTaxon

class NuidManager:
    
    ALLOWED_CHARS = ['0','1','2','3','4','5','6','7','8','9',
                 'a','b','c','d','e','f','g','h','i','j','k','l','m',
                 'n','o','p','q','r','s','t','u','v','w','x','y','z']

    DIGITS_PER_FIGURE = 3

    def decimal_to_nuid(self, integer):
        nuid_aslist = []
    
        # determine the number of trailing zeros
        allowed_chars_count = len(self.ALLOWED_CHARS)

        if self.DIGITS_PER_FIGURE > 1:
            possible_max = allowed_chars_count**self.DIGITS_PER_FIGURE

            if integer > possible_max:
                raise ValueError('The maximum displayable with this nuid is %s, you entered %s' %(possible_max,
                                                                                                  integer))

        if integer != 0:

            nuid = ''

            if self.DIGITS_PER_FIGURE > 1:
                prefix = '0' * ( self.DIGITS_PER_FIGURE - 1 - int(math.floor(math.log(integer, allowed_chars_count))))
            else:
                prefix = ''

            while integer != 0:
                rest = integer % allowed_chars_count
                integer = int(math.floor(integer / allowed_chars_count))
                nuid = '%s%s' % (self.ALLOWED_CHARS[rest], nuid)

            nuid = '%s%s' % (prefix, nuid)
            
        else:
            nuid = '0' * self.DIGITS_PER_FIGURE

        return nuid


    def nuid_to_decimal(self, nuid):

        allowed_chars_count = len(self.ALLOWED_CHARS)
        
        #before reversing, strip off trailing 0
        while nuid.startswith('0'):
            nuid = nuid[1:]
            
        nuid = nuid [::-1] #reverse the string
        dec = 0
        
        for exponent, x in enumerate(nuid, start=0):
            x_dec = self.ALLOWED_CHARS.index(x)
            dec += x_dec * (allowed_chars_count**exponent)

        return int(dec)


    def next_nuid(self, nuid):

        nuid_head = nuid[:-3]
        nuid_tail = nuid[-3:]

        decimal = self.nuid_to_decimal(nuid_tail)

        new_nuid_tail = self.decimal_to_nuid(decimal + 1)

        return '%s%s' % (nuid_head, new_nuid_tail)



def get_lazy_taxon_from_name_uuid(taxon_source, name_uuid):
    
    models = TaxonomyModelRouter(taxon_source)
        
    if taxon_source == 'taxonomy.source.custom':
        taxon = models.TaxonTreeModel.objects.get(name_uuid=name_uuid)
    else:
        taxon = models.TaxonNamesModel.objects.get(name_uuid=name_uuid)
        
    lazy_taxon = LazyTaxon(instance=taxon)
        
    return lazy_taxon


def get_subclasses(cls):
    result = []
    classes_to_inspect = [cls]
    
    while classes_to_inspect:
        class_to_inspect = classes_to_inspect.pop()
        
        for subclass in class_to_inspect.__subclasses__():

            if subclass._meta.abstract == True:
                classes_to_inspect.append(subclass)
                
            elif subclass not in result:
                result.append(subclass)
                classes_to_inspect.append(subclass)
                
    return result