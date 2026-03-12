from django.db import models
from django.contrib.auth.models import User

# ---------------- SUPPLIER ----------------
class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)

    def __str__(self):
        return self.name


# ---------------- CATEGORY ----------------
class Category(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


# ---------------- PRODUCT ----------------
class Product(models.Model):
    name = models.CharField(max_length=100)
    sku = models.CharField(max_length=50, unique=True,default='TEMP-SKU')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    threshold = models.PositiveIntegerField(default=5)
    low_stock_alert_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    @property
    def get_status(self):
        if self.quantity <= 0:
            return "Out of Stock"
        elif self.quantity <= 10:
            return "Low Stock"
        return "In Stock"


# ---------------- CUSTOMER ----------------
class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.name


# ---------------- STAFF BUY REQUEST ----------------
class StockRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('DELIVERED', 'Delivered'),
        ('REJECTED', 'Rejected'),
    )

    staff = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    # ✅ ADD THIS FIELD (THIS IS THE FIX)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} - {self.staff.username}"


# ---------------- SALE TO CUSTOMER ----------------
class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    quantity_sold = models.PositiveIntegerField()
    sold_by = models.ForeignKey(User, on_delete=models.CASCADE)
    sold_at = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        return self.quantity_sold * self.product.price


class Purchase(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    purchased_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"
    

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.username