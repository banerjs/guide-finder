from django import forms

from myprojecct.location.models import BaseLocation, State

# The following forms are for users to modify and add locations to the Database

class StateForm(forms.ModelForm):
    class Meta:
        model = State

class BaseLocationForm(forms.ModelForm):
    class Meta:
        model = BaseLocation
