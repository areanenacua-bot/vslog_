import re

from django import forms
from django.db.models import Q, Value
from django.db.models.functions import Concat

from .models import Office, Visit, Visitor


class BootstrapForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'


class RegistrationForm(BootstrapForm):
    visitor = forms.ModelChoiceField(queryset=Visitor.objects.all(), required=False, widget=forms.HiddenInput)
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    contact_number = forms.CharField(max_length=20)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}))
    visitor_type = forms.ChoiceField(choices=[('', 'Select visitor type'), *Visitor.VISITOR_TYPES])
    visitor_type_other = forms.CharField(label='Specify visitor type', max_length=100, required=False,
                                         widget=forms.TextInput(attrs={'placeholder': 'For example, Researcher'}))
    purpose = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}))
    office = forms.ModelChoiceField(queryset=Office.objects.order_by('office_name'), empty_label='Select destination')
    person_to_visit = forms.CharField(max_length=150, required=False)

    def clean(self):
        data = super().clean()
        if data.get('visitor_type') == 'Other':
            if not data.get('visitor_type_other') and 'visitor_type_other' not in self.errors:
                self.add_error('visitor_type_other', 'Please specify the visitor type.')
        else:
            data['visitor_type_other'] = ''
        return data

    def clean_contact_number(self):
        value = self.cleaned_data['contact_number']
        if not re.fullmatch(r'\+?[0-9 ()-]+', value) or not 7 <= len(re.sub(r'\D', '', value)) <= 15:
            raise forms.ValidationError('Enter a contact number containing 7 to 15 digits.')
        return value


class VisitFilterForm(BootstrapForm):
    q = forms.CharField(label='Search', required=False, max_length=200,
                        widget=forms.TextInput(attrs={'placeholder': 'Name, contact, purpose or person'}))
    status = forms.ChoiceField(required=False, choices=[('', 'All statuses'), *Visit.STATUS_CHOICES])
    visitor_type = forms.ChoiceField(required=False, choices=[('', 'All visitor types'), *Visitor.VISITOR_TYPES])
    office = forms.ModelChoiceField(required=False, queryset=Office.objects.order_by('office_name'), empty_label='All destinations')
    date_from = forms.DateField(required=False, label='Arrival date from', widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, label='Arrival date to', widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        data = super().clean()
        if data.get('date_from') and data.get('date_to') and data['date_from'] > data['date_to']:
            raise forms.ValidationError('The start date must be on or before the end date.')
        return data

    def filter(self, visits):
        if not self.is_valid():
            return visits.none()
        data = self.cleaned_data
        if data['q']:
            visits = visits.annotate(full_name=Concat('visitor__first_name', Value(' '), 'visitor__last_name')).filter(
                Q(full_name__icontains=data['q']) | Q(visitor__contact_number__icontains=data['q']) |
                Q(purpose__icontains=data['q']) | Q(person_to_visit__icontains=data['q']))
        for field in ('status', 'office'):
            if data[field]:
                visits = visits.filter(**{field: data[field]})
        if data['visitor_type']:
            visits = visits.filter(visitor__visitor_type=data['visitor_type'])
        if data['date_from']:
            visits = visits.filter(time_in__date__gte=data['date_from'])
        if data['date_to']:
            visits = visits.filter(time_in__date__lte=data['date_to'])
        return visits
