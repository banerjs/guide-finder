from django import forms

from myproject.customer.models import ContactInfo

# These are forms to deal with changing profiles, etc.

class ContactInfoForm(forms.ModelForm):
    class Meta:
        model = ContactInfo
