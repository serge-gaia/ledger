import os
import json
from datetime import datetime

from django import forms
from django.contrib.postgres.forms import JSONField

from dateutil.relativedelta import relativedelta

from wildlifelicensing.apps.main.models import WildlifeLicence, CommunicationsLogEntry

DATE_FORMAT = '%d/%m/%Y'


class BetterJSONField(JSONField):
    """
    A form field for the JSONField.
    It fixes the double 'stringification', avoid the null text and indents the json (see prepare_value).
    """

    def __init__(self, **kwargs):
        kwargs.setdefault('widget', forms.Textarea(attrs={'cols': 80, 'rows': 20}))
        super(JSONField, self).__init__(**kwargs)

    def prepare_value(self, value):
        if value is None:
            return ""
        if isinstance(value, basestring):
            # already a string
            return value
        else:
            return json.dumps(value, indent=4)


class IdentificationForm(forms.Form):
    VALID_FILE_TYPES = ['png', 'jpg', 'jpeg', 'gif', 'pdf', 'PNG', 'JPG', 'JPEG', 'GIF', 'PDF']

    identification_file = forms.FileField(label='Image containing Identification',
                                          help_text='E.g. drivers licence, passport, proof-of-age')

    def clean_identification_file(self):
        id_file = self.cleaned_data.get('identification_file')

        ext = os.path.splitext(str(id_file))[1][1:]

        if ext not in self.VALID_FILE_TYPES:
            raise forms.ValidationError('Uploaded image must be of file type: %s' % ', '.join(self.VALID_FILE_TYPES))

        return id_file


class IssueLicenceForm(forms.ModelForm):
    class Meta:
        model = WildlifeLicence
        fields = ['issue_date', 'start_date', 'end_date', 'is_renewable', 'return_frequency', 'purpose', 'locations',
                  'cover_letter_message']

    def __init__(self, *args, **kwargs):
        purpose = kwargs.pop('purpose', None)

        is_renewable = kwargs.pop('is_renewable', False)

        return_frequency = kwargs.pop('return_frequency', WildlifeLicence.DEFAULT_FREQUENCY)

        super(IssueLicenceForm, self).__init__(*args, **kwargs)

        if purpose is not None:
            self.fields['purpose'].initial = purpose

        self.fields['is_renewable'].widget = forms.CheckboxInput()

        if 'instance' not in kwargs:
            today_date = datetime.now()
            self.fields['issue_date'].initial = today_date.strftime(DATE_FORMAT)
            self.fields['start_date'].initial = today_date.strftime(DATE_FORMAT)

            self.fields['issue_date'].localize = False

            one_year_today = today_date + relativedelta(years=1, days=-1)

            self.fields['end_date'].initial = one_year_today.strftime(DATE_FORMAT)

            self.fields['is_renewable'].initial = is_renewable

            self.fields['return_frequency'].initial = return_frequency


class CommunicationsLogEntryForm(forms.ModelForm):
    attachment = forms.FileField(required=False)

    class Meta:
        model = CommunicationsLogEntry
        fields = ['to', 'fromm', 'type', 'subject', 'text', 'attachment']

    def __init__(self, *args, **kwargs):
        to = kwargs.pop('to', None)
        fromm = kwargs.pop('fromm', None)

        super(CommunicationsLogEntryForm, self).__init__(*args, **kwargs)

        if to is not None:
            self.fields['to'].initial = to

        if fromm is not None:
            self.fields['fromm'].initial = fromm
