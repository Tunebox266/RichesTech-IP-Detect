# payments/urls.py
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Dues
    path('dues/', views.due_list, name='due_list'),
    path('dues/<int:pk>/', views.due_detail, name='due_detail'),
    path('student/<int:student_id>/', views.student_payment, name='student_payment'),
    # Payments
    path('make-payment/<int:due_id>/', views.make_payment, name='make_payment'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('history/', views.payment_history, name='payment_history'),
    path('receipt/<int:pk>/', views.payment_receipt, name='payment_receipt'),
    path('cancel/<str:reference>/', views.cancel_payment, name='cancel_payment'),  # ADD THIS LINE
    
    # Admin/Staff only
    path('dues/create/', views.due_create, name='due_create'),
    path('dues/<int:pk>/edit/', views.due_edit, name='due_edit'),
    path('dues/<int:pk>/delete/', views.due_delete, name='due_delete'),
    path('reports/', views.payment_reports, name='payment_reports'),
    path('export/', views.export_payments, name='export_payments'),
    path('export-unpaid/', views.export_unpaid, name='export_unpaid'),
    # Webhook
    path('webhook/paystack/', views.paystack_webhook, name='paystack_webhook'),
]