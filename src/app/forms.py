from django import forms
from .models import Reader

class ReaderForm(forms.ModelForm):
    class Meta:
        model = Reader
        fields = ['serial_number', 'ip_address', 'location', 'enabled']

class ModeForm(forms.Form):
    type = forms.ChoiceField(
        choices=[('INVENTORY', 'Inventory')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    antennas = forms.MultipleChoiceField(
        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4')],
        widget=forms.CheckboxSelectMultiple
    )
    antennaZone = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    antennaZoneState = forms.ChoiceField(
        choices=[('enabled', 'Enabled'), ('disabled', 'Disabled')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    transmitPower = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    groupIntervalInMs = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    rfMode = forms.ChoiceField(
        choices=[('MaxThroughput', 'Max Throughput')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    searchMode = forms.ChoiceField(
        choices=[('single-target', 'Single Target')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    session = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    tagPopulation = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )