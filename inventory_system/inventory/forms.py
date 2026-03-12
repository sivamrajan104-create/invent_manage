from django import forms
from .models import Product
from .models import Sale
from .models import Supplier, Purchase,StockRequest,UserProfile


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'category', 'supplier', 'quantity', 'price', 'threshold']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adding CSS classes so they look good with our Figma theme
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['product', 'quantity_sold']


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = '__all__'

class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['product', 'supplier', 'quantity', 'cost_price']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
        }


class StockRequestForm(forms.ModelForm):
    class Meta:
        model = StockRequest
        fields = ['product', 'quantity']



class UserProfileForm(forms.ModelForm):
    email = forms.EmailField(required=False)
    mobile_number = forms.CharField(required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = UserProfile
        fields = ['mobile_number', 'address']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['email'].initial = user.email