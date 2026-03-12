from .utils import send_low_stock_email

def check_and_send_low_stock_alert(product):
    if product.quantity <= product.threshold and not product.low_stock_alert_sent:
        send_low_stock_email(product)
        product.low_stock_alert_sent = True
        product.save(update_fields=['low_stock_alert_sent'])

    # Reset flag if stock is refilled
    if product.quantity > product.threshold and product.low_stock_alert_sent:
        product.low_stock_alert_sent = False
        product.save(update_fields=['low_stock_alert_sent'])
