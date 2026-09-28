from django import forms

from .models import User


class RegistrationForm(forms.ModelForm):
    """Used by the HTML register view. Password complexity is enforced by
    Django's AUTH_PASSWORD_VALIDATORS (accounts.validators.ComplexityValidator),
    which `full_clean()` on the User model does not run automatically for
    passwords -- so this form calls `validate_password()` explicitly.
    """

    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "role"]

    def clean_password(self):
        from django.contrib.auth.password_validation import validate_password

        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
