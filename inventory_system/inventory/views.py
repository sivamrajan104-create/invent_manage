from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User,Group
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models.functions import TruncMonth
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import csv

from .models import (
    Product, Supplier, Category, Customer,
    Sale, StockRequest,UserProfile,Purchase

)
from .forms import ProductForm, SupplierForm, SaleForm,PurchaseForm,UserProfileForm


# ---------------- AUTH ----------------
def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.is_superuser:
                return redirect('dashboard')
            return redirect('staff_product_list')

        messages.error(request, "Invalid username or password.")
        return redirect('/?login_error=1')

    return redirect('/')



def logout_view(request):
    logout(request)
    return redirect('landing')


def register_user(request):
    if request.method == "POST":
        u_name = request.POST.get('username')
        e_mail = request.POST.get('email')
        p_word = request.POST.get('password')

        if User.objects.filter(username=u_name).exists():
            messages.error(request, "Username already taken.")
            return redirect('/?register=1&error=username')

        user = User.objects.create_user(
            username=u_name,
            email=e_mail,
            password=p_word
        )

       
        UserProfile.objects.get_or_create(user=user)

        messages.success(request, "Account created! Please login.")

        # 🔥 Redirect BACK to landing page
        return redirect('/?registered=1')

    return redirect('/')




# ---------------- ADMIN DASHBOARD ----------------
@login_required
def dashboard(request):
    # --- 1. Access Control ---
    # Assuming is_admin is a helper function you've defined
    if not request.user.is_superuser:
        return redirect('staff_product_list')

    # --- 2. Basic Stats ---
    pending_requests = StockRequest.objects.filter(status='PENDING')
    # Filter products where quantity is less than or equal to their specific threshold
    low_stock_products = Product.objects.filter(
    threshold__isnull=False,
    threshold__gt=0,
    quantity__lte=F('threshold')
)
    
    # --- 3. Revenue Calculations ---
    # Lifetime Revenue
    total_sales_data = Sale.objects.annotate(
        revenue=ExpressionWrapper(F('quantity_sold') * F('product__price'), output_field=DecimalField())
    ).aggregate(total=Sum('revenue'))
    total_sales = total_sales_data['total'] or 0

    # Monthly Revenue
    now = timezone.now()
    monthly_revenue_data = Sale.objects.filter(
        sold_at__month=now.month,
        sold_at__year=now.year
    ).annotate(
        revenue=ExpressionWrapper(F('quantity_sold') * F('product__price'), output_field=DecimalField())
    ).aggregate(total=Sum('revenue'))
    monthly_revenue = monthly_revenue_data['total'] or 0

    # --- 4. Chart Data: Inventory (Category Distribution) ---
    category_data = Category.objects.annotate(
        stock_count=Sum('product__quantity')
    ).values('name', 'stock_count')
    
    # --- 5. Chart Data: Sales Trends (Last 6 Months) ---
    six_months_ago = now - timezone.timedelta(days=180)
    sales_trend_qs = Sale.objects.filter(sold_at__gte=six_months_ago) \
        .annotate(month=TruncMonth('sold_at')) \
        .values('month') \
        .annotate(total=Sum(F('quantity_sold') * F('product__price'))) \
        .order_by('month')

    # Formatting trend data for JS
    trend_labels = [item['month'].strftime("%b") for item in sales_trend_qs]
    trend_values = [float(item['total']) for item in sales_trend_qs]

    context = {
        'total_products': Product.objects.count(),
        'total_sales': round(float(total_sales), 2),
        'monthly_revenue': round(float(monthly_revenue), 2),
        'low_stock_count': low_stock_products.count(),
        'pending_count': pending_requests.count(),
        'recent_sales': Sale.objects.select_related('product').order_by('-sold_at')[:5],
        'products': Product.objects.all().order_by('quantity'), # For Inventory Health table
        
        # Chart Data
        'category_labels': [item['name'] for item in category_data],
        'category_values': [item['stock_count'] or 0 for item in category_data],
        'trend_labels': trend_labels,
        'trend_values': trend_values,
    }
    return render(request, 'admin_dashboard.html', context)


# ---------------- STAFF DASHBOARD ----------------
def staff_product_list(request):
    products = Product.objects.select_related('supplier').only(
    'id', 'name', 'quantity', 'price', 'threshold'
)

    
    # NEW: Fetch the actual requests for this user
    requests = StockRequest.objects.filter(staff=request.user).order_by('-id')[:10] # Top 10 recent
    
    # 1. Count Total Units across all products
    total_stock_count = Product.objects.aggregate(Sum('quantity'))['quantity__sum'] or 0
    
    # 2. Count requests waiting for admin (matching the 'Pending' string used in your logic)
    pending_count = StockRequest.objects.filter(
        staff=request.user, 
        status__iexact='Pending'
    ).count()
    
    # 3. Total units this specific staff member has requested
    total_requested = StockRequest.objects.filter(
        staff=request.user
    ).aggregate(Sum('quantity'))['quantity__sum'] or 0

    return render(request, 'user_dashboard.html', {
        'products': products,
        'requests': requests,  # <--- MUST ADD THIS LINE
        'total_stock': total_stock_count, 
        'pending_count': pending_count,
        'total_requested': total_requested,
    })


# ---------------- STAFF → BUY FROM ADMIN ----------------
@login_required
def request_stock(request, product_id):
    if request.user.is_superuser:
     return redirect('dashboard')


    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        quantity = int(request.POST.get('quantity'))

        StockRequest.objects.create(
            staff=request.user,
            product=product,
            quantity=quantity
        )

        send_mail(
            "📦 New Stock Purchase Request",
            f"{request.user.username} requested {quantity} units of {product.name}.",
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL]
        )

        return redirect('staff_product_list')

    return render(request, 'request_stock.html', {'product': product})


# ---------------- ADMIN APPROVE REQUEST ----------------
# Corrected ADMIN APPROVE
# ---------------- ADMIN APPROVE REQUEST ----------------
@login_required
def approve_stock_request(request, request_id):
    if not request.user.is_superuser:

        messages.error(request, "Unauthorized access.")
        return redirect('admin_stock_requests')

    stock_request = get_object_or_404(StockRequest, id=request_id)
    product = stock_request.product

    # ❌ Prevent double approval
    if stock_request.status == 'APPROVED':
        messages.warning(request, "This request is already approved.")
        return redirect('admin_stock_requests')

    # ❌ Insufficient stock
    if stock_request.quantity > product.quantity:
        messages.error(
            request,
            f"Insufficient stock! Only {product.quantity} units available."
        )
        return redirect('admin_stock_requests')

    with transaction.atomic():

        # 1️⃣ Reduce admin stock
        product.quantity -= stock_request.quantity
        product.save()

        # 2️⃣ Approve request
        stock_request.status = 'APPROVED'
        stock_request.approved_at = timezone.now()
        stock_request.save()

        # 3️⃣ Create Sale record (internal transfer)
        Sale.objects.create(
            product=product,
            quantity_sold=stock_request.quantity,
            sold_by=stock_request.staff,
            customer=None
        )

        # 4️⃣ 🔔 LOW STOCK EMAIL (ADMIN)
        if product.quantity <= product.threshold:
            send_mail(
                subject=f"⚠️ Low Stock Alert: {product.name}",
                message=f"""
Product: {product.name}
Remaining Stock: {product.quantity}
Threshold: {product.threshold}

Please restock soon.
""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=True
            )

    # 5️⃣ Notify staff
    send_mail(
        subject="✅ Stock Request Approved",
        message=f"""
Hi {stock_request.staff.username},

Your request for {stock_request.quantity} units of {product.name} has been approved.

You can now see it in your stock.
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[stock_request.staff.email],
        fail_silently=True
    )

    messages.success(
        request,
        f"{product.name} request approved successfully!"
    )

    return redirect('admin_stock_requests')


@login_required
def reject_stock_request(request, request_id):
    stock_request = get_object_or_404(StockRequest, id=request_id)

    stock_request.status = 'REJECTED'
    stock_request.approved_at = timezone.now()
    stock_request.save()

    if stock_request.staff.email:
        send_mail(
            "❌ Stock Request Rejected",
            f"""
Hello {stock_request.staff.username},

Your request for {stock_request.product.name}
has been REJECTED.
""",
            settings.DEFAULT_FROM_EMAIL,
            [stock_request.staff.email],
            fail_silently=False,
        )

    messages.warning(request, "Request rejected.")
    return redirect('admin_stock_requests')





def send_low_stock_email(product):
    send_mail(
        subject=f"⚠️ Low Stock Alert: {product.name}",
        message=f"""
Product: {product.name}
Remaining Stock: {product.quantity}
Threshold: {product.threshold}
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
        fail_silently=False,
    )





# ---------------- STAFF → SELL TO CUSTOMER ----------------
@login_required
def sell_product(request):
    if request.user.is_superuser:
     return redirect('dashboard')


    form = SaleForm(request.POST or None)

    if form.is_valid():
        sale = form.save(commit=False)
        product = sale.product

        if sale.quantity_sold > product.quantity:
            return render(request, 'sell_product.html', {
                'form': form,
                'error': 'Insufficient stock'
            })

        with transaction.atomic():
            # 1️⃣ Reduce stock
            product.quantity -= sale.quantity_sold
            product.save()

            # 2️⃣ Save sale
            sale.sold_by = request.user
            sale.save()

            # 3️⃣ 🔔 LOW STOCK EMAIL
            if product.quantity <= product.threshold:
                send_mail(
                    subject=f"⚠️ Low Stock Alert: {product.name}",
                    message=f"""
Product: {product.name}
Remaining Stock: {product.quantity}
Threshold: {product.threshold}

Please restock soon.
""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.ADMIN_EMAIL],
                    fail_silently=True
                )

        messages.success(request, "Sale registered successfully.")
        return redirect('staff_product_list')

    return render(request, 'sell_product.html', {'form': form})


# ---------------- PRODUCT MANAGEMENT ----------------
def product_list(request):
    query = request.GET.get('q')
    products = Product.objects.all().select_related('category')

    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(sku__icontains=query) |
            Q(category__name__icontains=query)
        )

    context = {
        'products': products,
        'search_query': query, # Pass this back to keep it in the input box
    }
    return render(request, 'products.html', context)

@login_required
def add_product(request):
    if not request.user.is_superuser:
        return redirect('staff_product_list')

    form = ProductForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('product_list')

    return render(request, 'add_product.html', {'form': form})


@login_required
def delete_product(request, pk):
    # 🔐 Admin-only access
    if not request.user.is_superuser:
        return redirect('staff_product_list')

    Product.objects.filter(pk=pk).delete()
    return redirect('product_list')



# ---------------- SUPPLIER ----------------
@login_required
def supplier_list(request):
    if not request.user.is_superuser:
        return redirect('staff_product_list')

    return render(request, 'suppliers.html', {
        'suppliers': Supplier.objects.all()
    })

    
    # Handle Deletion
    if request.method == 'POST' and 'delete_id' in request.POST:
        supplier_id = request.POST.get('delete_id')
        supplier = get_object_or_404(Supplier, id=supplier_id)
        supplier_name = supplier.name
        supplier.delete()
        messages.success(request, f"Supplier '{supplier_name}' has been deleted.")
        return redirect('supplier_list')

    return render(request, 'suppliers.html', {
        'suppliers': Supplier.objects.all()
    })


@login_required
def add_supplier(request):
    if not request.user.is_superuser:
     return redirect('staff_product_list')

    form = SupplierForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('supplier_list')

    return render(request, 'add_supplier.html', {'form': form})


@login_required
def delete_supplier(request, pk):
    # 🔐 Admin-only access
    if not request.user.is_superuser:
        return redirect('staff_product_list')

    Supplier.objects.filter(pk=pk).delete()
    return redirect('supplier_list')



# ---------------- CATEGORY ----------------
@login_required
def category_list(request):
    if not request.user.is_superuser:
        return redirect('staff_product_list')


    categories = Category.objects.all()
    if request.method == "POST":
        Category.objects.create(name=request.POST.get('name'))
        return redirect('category_list')

    return render(request, 'categories.html', {'categories': categories})


# ---------------- LOW STOCK EMAIL ----------------
def send_low_stock_email(product):
    send_mail(
        f"⚠️ Low Stock Alert: {product.name}",
        f"Remaining stock: {product.quantity}\nThreshold: {product.threshold}",
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL]
    )



@login_required
def sales_list(request):
    if not request.user.is_superuser:

        return redirect('dashboard')

    sales = Sale.objects.select_related(
        'product', 'sold_by'
    ).order_by('-sold_at')

    return render(request, 'sales_list.html', {
        'sales': sales
    })



def add_purchase(request):
    # ================================
    # FEATURE: Monthly Supplier Report
    # ================================
    current_month = timezone.now().month

    supplier_report = (
        Purchase.objects
        .filter(purchased_at__month=current_month)
        .values(name=F('supplier__name'))
        .annotate(
            total_spent=Sum(
                ExpressionWrapper(
                    F('quantity') * F('cost_price'),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
        )
        .order_by('-total_spent')[:5]
    )

    # ================================
    # PURCHASE FORM LOGIC
    # ================================
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                purchase = form.save(commit=False)
                purchase.added_by = request.user   # if you track who added it
                purchase.save()

                product = purchase.product

                # Update Inventory Quantity
                product.quantity += purchase.quantity

                # Dynamic Stock Status Logic
                if product.quantity > product.threshold:
                    product.stock_status = "In Stock"
                elif product.quantity > 0:
                    product.stock_status = "Low Stock"
                else:
                    product.stock_status = "Out of Stock"

                product.save()

            messages.success(
                request,
                f"Purchase recorded successfully! Total Cost: ₹{purchase.quantity * purchase.cost_price}"
            )
            return redirect('generate_purchase_pdf', purchase_id=purchase.id)

    else:
        form = PurchaseForm()

    return render(request, 'add_purchase.html', {
        'form': form,
        'supplier_report': supplier_report
    })



@login_required
def settings_view(request):
    profile = request.user.userprofile

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile, user=request.user)

        if form.is_valid():
            profile = form.save(commit=False)
            profile.save()

            # Update User email
            request.user.email = request.POST.get('email')
            request.user.save()

            messages.success(request, "Your profile has been updated successfully!")
            return redirect('settings_view')
    else:
        form = UserProfileForm(
            instance=profile,
            user=request.user,
            initial={
                'email': request.user.email
            }
        )

    return render(request, 'settings.html', {'form': form})




@login_required
def bulk_threshold_update(request):
    # 🔐 Admin-only access
    if not request.user.is_superuser:
        return redirect('staff_product_list')

    if request.method == "POST":
        for key, value in request.POST.items():
            if key.startswith('threshold_'):
                product_id = key.split('_')[1]
                try:
                    Product.objects.filter(id=product_id).update(
                        threshold=int(value)
                    )
                except (ValueError, TypeError):
                    pass

        return redirect('product_list')

    products = Product.objects.all()
    return render(request, 'bulk_update.html', {'products': products})



@login_required
def staff_stock_requests(request):
    all_requests = StockRequest.objects.filter(staff=request.user).order_by('-id')
    
    pending_count = all_requests.filter(status__iexact='Pending').count()
    approved_count = all_requests.filter(status__iexact='Approved').count()
    rejected_count = all_requests.filter(status__iexact='Rejected').count()
    total = all_requests.count() or 1 # Avoid division by zero
    
    context = {
        'requests': all_requests,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'pending_pct': (pending_count / total) * 100,
        'approved_pct': (approved_count / total) * 100,
        'rejected_pct': (rejected_count / total) * 100,
    }
    return render(request, 'staff_stock_requests.html', context)


def admin_stock_requests(request):
    # __iexact makes it case-insensitive to avoid missing 'PENDING' vs 'Pending'
    pending_requests = StockRequest.objects.filter(status__iexact='PENDING').order_by('-requested_at')
    history_requests = StockRequest.objects.exclude(status__iexact='PENDING').order_by('-approved_at')
    
    return render(request, 'admin_stock_requests.html', {
        'requests': pending_requests,
        'history': history_requests
    })



def user_list(request):
    users = User.objects.select_related('userprofile')
    return render(request, 'users.html', {'users': users})



def report_view(request):
    # We multiply Sale quantity by the Price in the related Product model
    sales_data = Sale.objects.annotate(
        revenue=F('quantity_sold') * F('product__price')
    ).aggregate(total_revenue=Sum('revenue'))
    
    total_revenue = sales_data['total_revenue'] or 0
    total_stock = Product.objects.aggregate(Sum('quantity'))['quantity__sum'] or 0

    return render(request, 'reports.html', {
        'total_revenue': total_revenue,
        'total_stock': total_stock
    })








@login_required
def buy_products(request):
    # ✅ Allow ALL logged-in NON-admin users
    if request.user.is_superuser:
        return redirect('dashboard')

    category_id = request.GET.get('category')

    products = Product.objects.select_related('category').order_by('name')
    categories = Category.objects.all()

    if category_id:
        products = products.filter(category_id=category_id)

    if request.method == "POST":
        product_ids = request.POST.getlist('product_ids')
        quantities = request.POST.getlist('quantities')

        if product_ids:
            try:
                with transaction.atomic():
                    request_details = []

                    for pid, qty in zip(product_ids, quantities):
                        qty = int(qty)
                        if qty > 0:
                            product = get_object_or_404(Product, id=pid)

                            StockRequest.objects.create(
                                staff=request.user,
                                product=product,
                                quantity=qty,
                                status='PENDING'
                            )

                            request_details.append(
                                f"- {product.name} (Qty: {qty})"
                            )

                    # 📧 EMAIL ADMIN
                    if request_details:
                        send_mail(
                            subject="📦 New Stock Request",
                            message=(
                                f"New stock request received.\n\n"
                                f"Requested by: {request.user.username}\n\n"
                                f"Items:\n" + "\n".join(request_details)
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[settings.ADMIN_EMAIL],
                            fail_silently=True,
                        )

                messages.success(
                    request,
                    "Stock request submitted successfully. Awaiting admin approval."
                )
                return redirect('staff_product_list')

            except Exception as e:
                messages.error(request, f"Error processing request: {e}")

    return render(request, 'buy_products.html', {
        'products': products,
        'categories': categories,
    })



@login_required
def register_sale(request):
    # Handle "Confirm Delivery" Action
    if request.method == "POST" and "confirm_id" in request.POST:
        req_id = request.POST.get("confirm_id")
        stock_req = get_object_or_404(StockRequest, id=req_id, staff=request.user)
        stock_req.status = 'DELIVERED'
        stock_req.delivered_at = timezone.now() # Ensure you have this field in your model
        stock_req.save()
        
        # Logic to add the quantity to the product's actual stock
        product = stock_req.product
        product.quantity += stock_req.quantity
        product.save()
        
        return redirect('register_sale')

    # 1. Fetch active approved requests
    approved_requests = StockRequest.objects.filter(
        staff=request.user, 
        status__iexact='APPROVED'
    ).order_by('-approved_at')

    now = timezone.now()
    for req in approved_requests:
        req.delivery_date = req.approved_at + timedelta(days=2)
        total_time = (req.delivery_date - req.approved_at).total_seconds()
        elapsed_time = (now - req.approved_at).total_seconds()
        req.progress = min(100, max(0, int((elapsed_time / total_time) * 100)))

    # 2. Fetch last 10 completed deliveries for History
    delivery_history = StockRequest.objects.filter(
        staff=request.user,
        status__iexact='DELIVERED'
    ).order_by('-delivered_at')[:10]

    context = {
        'approved_requests': approved_requests,
        'delivery_history': delivery_history,
        'total_inventory': Product.objects.aggregate(Sum('quantity'))['quantity__sum'] or 0,
        'my_total_sales': Sale.objects.filter(sold_by=request.user).count(),
    }
    return render(request, 'register_sale.html', context)



def landing_page(request):
    """
    Entry point for the application.
    Displays project quality and provides login routes.
    """
    # Optional: If user is already logged in, you can 
    # show a 'Return to Dashboard' button in the template
    # or redirect them automatically.
    
    return render(request, 'landing.html')




def generate_purchase_pdf(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="purchase_{purchase.id}.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("<b>Purchase Receipt</b>", styles['Title']))
    elements.append(Spacer(1, 0.3 * inch))

    # Purchase Details Table
    data = [
        ["Purchase ID", purchase.id],
        ["Product", purchase.product.name],
        ["Supplier", purchase.supplier.name],
        ["Quantity", purchase.quantity],
        ["Cost Price", f"₹{purchase.cost_price}"],
        ["Total Amount", f"₹{purchase.quantity * purchase.cost_price}"],
        ["Purchased At", purchase.purchased_at.strftime("%d-%m-%Y %H:%M")],
        ["Added By", purchase.added_by.username if purchase.added_by else "Admin"],
    ]

    table = Table(data, colWidths=[150, 250])
    elements.append(table)

    doc.build(elements)
    return response



@login_required
def export_sales_csv(request):
    if not request.user.is_superuser:
     return redirect('dashboard')



    # Create HTTP response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'

    writer = csv.writer(response)

    # CSV Header
    writer.writerow([
        'Date',
        'Time',
        'Product',
        'Sold By',
        'Quantity',
        'Unit Price',
        'Total Revenue'
    ])

    # Fetch sales
    sales = Sale.objects.select_related('product', 'sold_by').order_by('-sold_at')

    for sale in sales:
        writer.writerow([
            sale.sold_at.strftime('%Y-%m-%d'),
            sale.sold_at.strftime('%H:%M'),
            sale.product.name,
            sale.sold_by.username if sale.sold_by else 'Admin',
            sale.quantity_sold,
            sale.product.price,
            sale.quantity_sold * sale.product.price
        ])

    return response