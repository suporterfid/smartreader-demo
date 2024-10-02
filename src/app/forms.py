import json
from django import forms
from .models import Reader, Alert, ScheduledCommand, Firmware
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

class AlertForm(forms.ModelForm):
    class Meta:
        model = Alert
        fields = ['name', 'condition_type', 'condition_params', 'notification_method']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'condition_type': forms.Select(attrs={'class': 'form-control'}),
            'notification_method': forms.Select(attrs={'class': 'form-control'}),
        }

    condition_params = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('''Example for tag_frequency:
            {
            "tag_epc": "123456",
            "threshold": 5,
            "time_interval": 10
            }

            Example for reader_status:
            {
            "reader_serial": "READER001",
            "offline_threshold": 5
            }''')
                    }),
                    help_text=_("Enter JSON format condition parameters. Click the help icon for more information.")
                )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['condition_params'].initial = json.dumps(self.instance.condition_params, indent=2)

    def clean_condition_params(self):
        condition_type = self.cleaned_data.get('condition_type')
        condition_params = self.cleaned_data.get('condition_params')

        try:
            condition_params = json.loads(condition_params)
        except json.JSONDecodeError:
            raise forms.ValidationError(_('Invalid JSON format for condition parameters.'))

        if condition_type == 'tag_frequency':
            if 'tag_epc' not in condition_params or 'threshold' not in condition_params or 'time_interval' not in condition_params:
                raise forms.ValidationError(_('Tag frequency alert requires tag_epc, threshold, and time_interval parameters.'))
        elif condition_type == 'reader_status':
            if 'reader_serial' not in condition_params or 'offline_threshold' not in condition_params:
                raise forms.ValidationError(_('Reader status alert requires reader_serial and offline_threshold parameters.'))
        # Add validation for other alert types as needed

        return condition_params

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.condition_params = self.cleaned_data['condition_params']
        if commit:
            instance.save()
        return instance

class ScheduledCommandForm(forms.ModelForm):
    class Meta:
        model = ScheduledCommand
        fields = ['reader', 'command_type', 'scheduled_time', 'recurrence']
        widgets = {
            'scheduled_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class FirmwareUploadForm(forms.ModelForm):
    class Meta:
        model = Firmware
        fields = ['version', 'file', 'description']