from django import forms

MAX_SUBJECT_LEN = 120
MAX_BODY_LEN = 5000


class NewMessageForm(forms.Form):
    """The `recipient` choices are built per-request in the view, since they
    depend on which students this teacher is actually assigned to."""

    recipient = forms.ChoiceField(choices=())
    subject = forms.CharField(max_length=MAX_SUBJECT_LEN)
    body = forms.CharField(max_length=MAX_BODY_LEN, widget=forms.Textarea)

    def __init__(self, *args, recipient_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["recipient"].choices = recipient_choices


class ReplyForm(forms.Form):
    body = forms.CharField(max_length=MAX_BODY_LEN, widget=forms.Textarea)
