from django import forms


class FormPositionForm(forms.Form):
    position = forms.CharField(widget=forms.HiddenInput, required=True)
