from django.contrib import admin
from .models import Product
from .models import Supplier, Purchase
from .models import Product, Sale,Category

admin.site.register(Product)
admin.site.register(Sale)
admin.site.register(Supplier)
admin.site.register(Purchase)
admin.site.register(Category) 