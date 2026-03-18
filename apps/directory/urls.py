# directory/urls.py
from django.urls import path
from . import views

app_name = 'directory'

urlpatterns = [
    # Directory listing
    path('', views.directory_home, name='directory_home'),
    path('students/', views.student_list, name='student_list'),
    path('students/<int:pk>/', views.student_detail, name='student_detail'),
    
 # My ID Card (for logged-in student/executive)
    path('my-id-card/', views.my_id_card, name='my_id_card'),
    path('my-id-card/edit/', views.edit_id_card, name='edit_id_card'),
    path('my-id-card/printable/', views.view_id_card_printable, name='printable_id_card'),
    path('my-id-card/download/', views.download_id_card_pdf, name='download_id_card_pdf'),
    path('my-id-card/upload-signature/', views.upload_signature, name='upload_signature'),
    path('my-id-card/clear-signature/', views.clear_signature, name='clear_signature'),
     
    # Admin view for other students' ID cards
    path('id-card/<int:student_id>/', views.admin_view_id_card, name='admin_view_id_card'),
    path('id-card/<int:student_id>/download/', views.download_id_card_pdf, name='admin_download_id_card'),
    
    # Legacy URLs (keeping for compatibility, but redirect internally)
    path('id-card/', views.my_id_card, name='legacy_my_id_card'),
    path('upload-signature/', views.upload_signature, name='legacy_upload_signature'),
    path('clear-signature/', views.clear_signature, name='legacy_clear_signature'),
    
    # ===== PAST QUESTIONS =====
    path('past-questions/', views.past_question_list, name='past_question_list'),
    path('past-questions/<int:pk>/', views.past_question_detail, name='past_question_detail'),
    path('past-questions/<int:pk>/download/', views.download_past_question, name='download_past_question'),
    path('past-questions/upload/', views.past_question_upload, name='past_question_upload'),
    path('past-questions/<int:pk>/approve/', views.past_question_approve, name='past_question_approve'),
    path('past-questions/<int:pk>/delete/', views.past_question_delete, name='past_question_delete'),
    
    # ===== STUDENT HANDBOOK =====
    path('handbooks/', views.student_handbook_list, name='student_handbook_list'),
    path('handbooks/<int:pk>/', views.student_handbook_detail, name='student_handbook_detail'),
    path('handbooks/<int:pk>/download/', views.download_student_handbook, name='download_student_handbook'),
    path('handbooks/upload/', views.student_handbook_upload, name='student_handbook_upload'),
    path('handbooks/<int:pk>/delete/', views.student_handbook_delete, name='student_handbook_delete'),
    
    # ===== ACADEMIC CALENDAR =====
    path('calendar/', views.academic_calendar_list, name='academic_calendar_list'),
    path('calendar/<int:pk>/', views.academic_calendar_detail, name='academic_calendar_detail'),
    path('calendar/create/', views.academic_calendar_create, name='academic_calendar_create'),
    path('calendar/<int:pk>/edit/', views.academic_calendar_edit, name='academic_calendar_edit'),
    path('calendar/<int:pk>/delete/', views.academic_calendar_delete, name='academic_calendar_delete'),
    path('calendar/export/csv/', views.academic_calendar_export, name='academic_calendar_export'),
    path('calendar/export/ical/', views.academic_calendar_ical, name='academic_calendar_ical'),
    
    
    # Search and filters
    path('search/', views.directory_search, name='directory_search'),
    path('filter/', views.directory_filter, name='directory_filter'),
    
    # Export
    path('export/', views.export_directory, name='export_directory'),
]