from django import forms
from django.utils.translation import gettext_lazy as _

from app_kit.forms import CleanAppSubdomainMixin

'''
    Create initial app kit
    - is only used for creating an app on the commercial local cosmos
'''

class CreateInitialAppKitForm(CleanAppSubdomainMixin, forms.Form):
        
    subdomain = forms.CharField(max_length=255, required=True,
                    help_text=_('Your app kit will be available at subdomain.localcosmos.org, where "subdomain" is the name you configured here.'))


                

