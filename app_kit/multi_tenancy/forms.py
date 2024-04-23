from django import forms
from django.utils.translation import gettext_lazy as _

from django.contrib.auth import get_user_model
User = get_user_model()

class DeleteAccountForm(forms.Form):
    delete_account = forms.BooleanField(label=_('I want to delete my account. I am aware that this cannot be undone.'))


class EditAccountForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email',)


TOPIC_CHOICES = (
    ('sponsoring', _('Sponsoring')),
    ('apps', _('Apps')),
    ('custom_feature', _('Custom app feature')),
)
class ContactForm(forms.Form):

    name = forms.CharField(label=_('First name and surname'))
    email = forms.EmailField()
    
    topic = forms.ChoiceField(choices=TOPIC_CHOICES)

    message = forms.CharField(widget=forms.Textarea)
