from django.core.mail import send_mail
from django.conf import settings

def send_low_stock_email(product):
    send_mail(
        subject=f"⚠️ Low Stock Alert: {product.name}",
        message=f"""
Product: {product.name}
Remaining Stock: {product.quantity}
Minimum Threshold: {product.threshold}

Action Required: Restock immediately.
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
        fail_silently=False,
    )
