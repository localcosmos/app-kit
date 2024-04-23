from django.conf import settings
from django_tenants.utils import get_tenant_model, get_tenant_domain_model
Tenant = get_tenant_model()
Domain = get_tenant_domain_model()

def get_public_schema_url(request):

    # host, maybe with port. like sub.domain:80 or sub.localhost:8080
    host = request.META['HTTP_HOST']

    tenant = Tenant.objects.get(schema_name='public')

    # no port, no subdomain
    domain = Domain.objects.get(tenant=tenant, is_primary=True)

    # remove everything that is left of the host in the domain
    public_host = host[host.index(domain.domain):]
    
    public_schema_url = '%s://%s' %(request.scheme, public_host)

    return public_schema_url


# look up a.b.c in a dict
def dict_path_lookup(dic, path):

    path_keys = path.split('.')

    entry = dic.copy()

    for path_key in path_keys:

        if path_key in entry:
            entry = entry[path_key]

            if type(entry) != type({}):
                break

        else:
            return None

    return entry
