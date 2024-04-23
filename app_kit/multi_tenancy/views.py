from django.conf import settings
from django.views.generic import TemplateView, FormView
from django.shortcuts import redirect
from django.core.mail import EmailMessage

from .forms import DeleteAccountForm, EditAccountForm, ContactForm

from .models import Tenant


'''
    ACCOUNT
    - registration is not done by the user itself, but by an operator of the institute
'''
class MyAccount(TemplateView):
    template_name = 'localcosmos/my_account.html'


class EditAccount(FormView):
    template_name = 'localcosmos/edit_account.html'
    form_class = EditAccountForm

    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.request.user
        return kwargs

    def form_valid(self, form):

        user = form.save()

        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        return self.render_to_response(context)
    


# Deleting an account has to stop subscriptions
class DeleteAccount(FormView):
    template_name = 'localcosmos/delete_account.html'
    form_class = DeleteAccountForm

    def form_valid(self, form):

        user = self.request.user

        if user.is_authenticated:

            logout(self.request)

            user.delete()

        return redirect('/')


class ContactUs(FormView):
    template_name = 'localcosmos/contact_us.html'
    form_class = ContactForm

    def form_valid(self, form):

        name = form.cleaned_data['name']
        topic = form.cleaned_data['topic']

        email = form.cleaned_data['email']

        message = '{0} - {1}'.format(form.cleaned_data['message'], email)

        subject = '[ContactForm] {0}'.format(topic, email)

        message = EmailMessage(
            subject,
            message,
            'service@localcosmos.org', # from
            ['service@localcosmos.org'], # to
            [], # bcc
        )

        message.send()
        
        context = self.get_context_data(**self.kwargs)
        context['success'] = True

        return self.render_to_response(context)


'''
    Generic start page for app kit installations
'''

class ListAppKits(TemplateView):
    template_name = 'multi_tenancy/list_app_kits.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tenants'] = Tenant.objects.all().exclude(schema_name='public')
        return context
