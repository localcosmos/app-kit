def import_module(module):
    module = str(module)
    d = module.rfind(".")
    module_name = module[d+1:len(module)]
    m = __import__(module[0:d], globals(), locals(), [module_name])
    return getattr(m, module_name)

def import_class(cl):
    d = cl.rfind(".")
    classname = cl[d+1:len(cl)]
    m = __import__(cl[0:d], globals(), locals(), [classname])
    return getattr(m, classname)


from django.urls import reverse
def get_appkit_taxon_search_url():
    return reverse('search_taxon')
