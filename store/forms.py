from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Order

User = get_user_model()


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="We use this for order contact details.")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["customer_name", "email", "phone", "address", "city", "state", "postal_code"]
        labels = {
            "customer_name": "Full name",
            "address": "Shipping address",
            "postal_code": "PIN code",
        }
        widgets = {
            "customer_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
            "address": forms.TextInput(attrs={"autocomplete": "street-address"}),
            "city": forms.TextInput(attrs={"autocomplete": "address-level2"}),
            "state": forms.TextInput(attrs={"autocomplete": "address-level1"}),
            "postal_code": forms.TextInput(
                attrs={"autocomplete": "postal-code", "inputmode": "numeric", "maxlength": "6"}
            ),
        }

    def clean_customer_name(self):
        return self.cleaned_data["customer_name"].strip()
