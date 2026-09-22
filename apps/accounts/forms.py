from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User

INPUT_CLASSES = (
    "block w-full rounded-lg border border-slate-300 dark:border-slate-700 "
    "bg-white dark:bg-slate-900 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 "
    "placeholder:text-slate-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30 "
    "focus:outline-none transition"
)


class SignupForm(UserCreationForm):
    email = forms.EmailField(
        label="Adresse email",
        widget=forms.EmailInput(attrs={"class": INPUT_CLASSES, "placeholder": "vous@exemple.com"}),
    )
    first_name = forms.CharField(
        label="Prénom",
        max_length=150,
        widget=forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "Prénom"}),
    )

    class Meta:
        model = User
        fields = ("email", "first_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Mot de passe"
        self.fields["password1"].widget.attrs["class"] = INPUT_CLASSES
        self.fields["password1"].widget.attrs["placeholder"] = "••••••••"
        self.fields["password2"].label = "Confirmer le mot de passe"
        self.fields["password2"].widget.attrs["class"] = INPUT_CLASSES
        self.fields["password2"].widget.attrs["placeholder"] = "••••••••"


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Adresse email",
        widget=forms.EmailInput(
            attrs={"class": INPUT_CLASSES, "placeholder": "vous@exemple.com", "autofocus": True}
        ),
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASSES, "placeholder": "••••••••"}),
    )

    error_messages = {
        "invalid_login": "Adresse email ou mot de passe incorrect.",
        "inactive": "Ce compte est désactivé.",
    }
