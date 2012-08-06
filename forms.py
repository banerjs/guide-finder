from django import forms

# These are generic forms for The Site

class ContactUsForm(forms.Form):
    name = forms.CharField(max_length=100, min_length=1)
    email = forms.EmailField()
    message = forms.CharField(min_length=10, widget=forms.Textarea)

# These are trial forms that will be used to test the functionality of the site

#from customer.models import CustomerMain#
#
#class CustomerAddressForm(forms.ModelForm):
#    class Meta:
#        model = CustomeMain
