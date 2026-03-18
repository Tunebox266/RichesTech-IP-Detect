# complaints/urls.py (continued)
from django.urls import path
from . import views

app_name = 'complaints'

urlpatterns = [
    # Complaint listing
    path('', views.complaint_list, name='complaint_list'),
    path('my/', views.my_complaints, name='my_complaints'),
    path('<int:pk>/', views.complaint_detail, name='complaint_detail'),
    
    # Creating complaints
    path('submit/', views.submit_complaint, name='submit_complaint'),
    
    # Responding to complaints (staff/executive)
    path('<int:pk>/respond/', views.respond_to_complaint, name='respond_to_complaint'),
    path('<int:pk>/update-status/', views.update_complaint_status, name='update_complaint_status'),
    
    # Management (staff/admin)
    path('manage/', views.manage_complaints, name='manage_complaints'),
    path('export/', views.export_complaints, name='export_complaints'),
    
    # AJAX endpoints
    path('api/stats/', views.complaint_stats, name='complaint_stats'),
]