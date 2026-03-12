from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [

path('', views.landing_page, name='landing'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_user, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Redirect empty path to login
    path('', auth_views.LoginView.as_view(template_name='login.html')),
    # ---------- DASHBOARDS ----------
    path('dashboard/', views.dashboard, name='dashboard'),
    path('staff/', views.staff_product_list, name='staff_product_list'),

    # ---------- PRODUCTS ----------
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/delete/<int:pk>/', views.delete_product, name='delete_product'),

    # ---------- SALES ----------
    path('sell/', views.sell_product, name='sell_product'),
    path('sales/', views.sales_list, name='sales_list'),

    # ---------- SUPPLIERS ----------
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.add_supplier, name='add_supplier'),
    path('suppliers/delete/<int:pk>/', views.delete_supplier, name='delete_supplier'),

    # ---------- PURCHASE ----------
    path('purchase/add/', views.add_purchase, name='add_purchase'),

    # ==============================
    # 🔥 STOCK REQUEST SYSTEM 🔥
    # ==============================

    # Staff
    path('stock/request/<int:product_id>/', views.request_stock, name='request_stock'),
    path('my-stock-requests/', views.staff_stock_requests, name='staff_stock_requests'),

    # Admin
path('stock-requests/', views.admin_stock_requests, name='admin_stock_requests'),
path('stock/approve/<int:request_id>/', views.approve_stock_request, name='approve_stock_request'),
path('stock/reject/<int:request_id>/', views.reject_stock_request, name='reject_stock_request'),



    # ---------- SETTINGS ----------
    path('settings/', views.settings_view, name='settings_view'),

    # ---------- CATEGORIES ----------
    path('categories/', views.category_list, name='category_list'),

    # ---------- BULK THRESHOLD ----------
    path('bulk-threshold/', views.bulk_threshold_update, name='bulk_threshold_update'),



    path('users/', views.user_list, name='user_list'),
    path('reports/', views.report_view, name='report_view'),
    path('settings/', views.settings_view, name='settings_view'),

path('buy-products/', views.buy_products, name='buy_products'),

path('sales/register/', views.register_sale, name='register_sale'),
    path('purchase/pdf/<int:purchase_id>/', views.generate_purchase_pdf, name='generate_purchase_pdf'),
path('sales/export/', views.export_sales_csv, name='export_sales_csv'),

]
