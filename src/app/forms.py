from django import forms
from .models import Reader
from django.utils.translation import gettext as _

class ReaderForm(forms.ModelForm):
    class Meta:
        model = Reader
        fields = ['serial_number', 'ip_address', 'location', 'enabled']

class ModeForm(forms.Form):
    type = forms.ChoiceField(
        label=_("Type"),
        choices=[('INVENTORY', _('Inventory'))],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    antennas = forms.MultipleChoiceField(
        label=_("Antennas"),
        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4')],
        widget=forms.CheckboxSelectMultiple
    )
    antennaZone = forms.CharField(
        label=_("Antenna Zone"),
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    antennaZoneState = forms.ChoiceField(
        label=_("Antenna Zone State"),
        choices=[('enabled', _('Enabled')), ('disabled', _('Disabled'))],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    transmitPower = forms.FloatField(
        label=_("Transmit Power"),
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    groupIntervalInMs = forms.IntegerField(
        label=_("Group Interval (ms)"),
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    rfMode = forms.ChoiceField(
        label=_("RF Mode"),
        choices=[
            ('MaxThroughput', _('Max Throughput')),
            ('Hybrid', _('Hybrid')),
            ('DenseReaderM4', _('DenseReaderM4')),
            ('DenseReaderM8', _('DenseReaderM8')),
            ('MaxMiller', _('MaxMiller')),
            ('AutoSetDenseReaderDeepScan', _('AutoSetDenseReaderDeepScan')),
            ('AutoSetStaticFast', _('AutoSetStaticFast')),
            ('AutoSetStaticDRM', _('AutoSetStaticDRM'))
            ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    searchMode = forms.ChoiceField(
        label=_("Search Mode"),
        choices=[
            ('reader-selected', _('Reader Selected')),
            ('single-target', _('Single Target')),
            ('dual-target', _('Dual Target')),
            ('single-target-with-tagfocus', _('TagFocus')),
            ('single-target-b-to-a', _('SingleTargetReset')),
            ('dual-target-with-b-to-a-select', _('DualTargetBtoASelect'))
                 ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    session = forms.ChoiceField(
        label=_("Session"),
        choices=[
            ('0', '0'),
            ('1', '1'),
            ('2', '2'),
            ('3', '3')
                 ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    tagPopulation = forms.IntegerField(
        label=_("Tag Population"),
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )