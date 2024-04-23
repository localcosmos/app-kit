import rules

from app_kit.multi_tenancy.models import TenantUserRole


@rules.predicate
def is_tenant_admin(user, tenant):
    
    if user.is_staff or user.is_superuser:
        return True
    
    if user.is_authenticated == True:
        return TenantUserRole.objects.filter(user=user, tenant=tenant, role='admin').exists()
        
    return False


###################################################################################################################
#
#   TENANT ADMINS ONLY
#
###################################################################################################################

rules.add_rule('app_kit.has_access', is_tenant_admin)
