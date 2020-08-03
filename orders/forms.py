from django import forms
from orders.models import Order
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from django.contrib.auth.mixins import LoginRequiredMixin

PAYMENT_CHOICES = (
    ('S', 'Stripe'),
    ('P', 'Paypal'),
)

class CheckoutForm(forms.Form):
    shipping_address = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': '1234 Main St',
        'class': 'textinput textInput form-control',
    }))
    shipping_address2 = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Apartment or suite',
        'class': 'textinput textInput form-control',
    }))
    shipping_country = CountryField(blank_label='Select Country').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100',
        }))
    shipping_state = forms.CharField(required=False,widget=forms.TextInput(attrs={
        'placeholder': 'State',
        'class': 'textinput textInput form-control'
    }))
    shipping_zip_code = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Zip Code',
        'class': 'textinput textInput form-control',
    }))
    billing_address = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': '1234 Main St',
        'class': 'textinput textInput form-control',
    }))
    billing_address2 = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Apartment or suite',
        'class': 'textinput textInput form-control',
    }))
    billing_country = CountryField(blank_label='Select Country').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100',
        }))
    billing_state = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'State',
        'class': 'textinput textInput form-control'
    }))
    billing_zip_code = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Zip Code',
        'class': 'textinput textInput form-control',
    }))


    same_as_shipping_address = forms.BooleanField(widget=forms.CheckboxInput(), required=False) 
    set_default_shipping = forms.BooleanField(required=False)
    use_default_shipping = forms.BooleanField(required=False)
    set_default_billing = forms.BooleanField(required=False)
    use_default_billing = forms.BooleanField(required=False)
 
    payment_option = forms.ChoiceField(widget=forms.RadioSelect(), choices=PAYMENT_CHOICES)


class CouponForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Promo code',
        'aria-label': "Recipient's username", 
        'aria-describedby':"basic-addon2",
    }))



class RefundForm(forms.Form):
    ref_code = forms.CharField()
    message = forms.CharField(widget=forms.Textarea(
        attrs={
            'rows': '4'
        }
    ))
    email = forms.EmailField()

class PaymentForm(forms.Form):
    stripeToken = forms.CharField(required=False)
    save = forms.BooleanField(required=False)
    use_default = forms.BooleanField(required=False)