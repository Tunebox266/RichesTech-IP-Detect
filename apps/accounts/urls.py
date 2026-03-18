# apps/accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password-change/', views.password_change, name='password_change'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/done/', views.password_reset_done, name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password-reset/complete/', views.password_reset_complete, name='password_reset_complete'),
    # apps/accounts/urls.py - Add these URLs

    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/reset-password/', views.reset_user_password, name='reset_user_password'),
    path('users/<int:pk>/unlock/', views.unlock_user_account, name='unlock_user_account'),
    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/photo/upload/', views.upload_profile_photo, name='upload_profile_photo'),
    
    # Dashboard redirect
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    
    # User Management (Admin)
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/bulk-upload/', views.bulk_upload_students, name='bulk_upload_students'),
    path('users/export/', views.export_users, name='export_users'),
    
    
    
    # apps/accounts/urls.py - Add these to your executive task URLs section

    path('executive/tasks/<int:pk>/comment/', views.executive_task_add_comment, name='executive_task_comment'),
    path('executive/tasks/comment/<int:pk>/delete/', views.executive_task_comment_delete, name='executive_task_comment_delete'),
    
    
    
    # Activity Logs
    path('activity-logs/', views.activity_logs, name='activity_logs'),
    path('activity-logs/export/', views.export_activity_logs, name='export_activity_logs'),
    path('login-attempts/', views.login_attempts, name='login_attempts'),
    
    # ========== EXECUTIVE MANAGEMENT ==========
    
    # Executive Dashboard
    path('executive/dashboard/', views.executive_dashboard, name='executive_dashboard'),
    
    # Meeting Management
    path('executive/meetings/', views.executive_meeting_list, name='executive_meeting_list'),
    path('executive/meetings/create/', views.executive_meeting_create, name='executive_meeting_create'),
    path('executive/meetings/<int:pk>/', views.executive_meeting_detail, name='executive_meeting_detail'),
    path('executive/meetings/<int:pk>/edit/', views.executive_meeting_edit, name='executive_meeting_edit'),
    path('executive/meetings/<int:pk>/delete/', views.executive_meeting_delete, name='executive_meeting_delete'),
    path('executive/meetings/<int:pk>/attendance/', views.executive_meeting_attendance, name='executive_meeting_attendance'),
    path('executive/meetings/<int:pk>/check-in/', views.executive_meeting_check_in, name='executive_meeting_check_in'),
    path('executive/meetings/<int:pk>/export-attendance/', views.export_meeting_attendance, name='export_meeting_attendance'),
    path('executive/meetings/<int:pk>/send-reminders/', views.send_meeting_reminders, name='send_meeting_reminders'),
    path('executive/meetings/export/', views.export_all_meetings, name='export_meetings'),
    
    # Task Management
    path('executive/tasks/', views.executive_task_list, name='executive_task_list'),
    path('executive/tasks/create/', views.executive_task_create, name='executive_task_create'),
    path('executive/tasks/<int:pk>/', views.executive_task_detail, name='executive_task_detail'),
    path('executive/tasks/<int:pk>/edit/', views.executive_task_edit, name='executive_task_edit'),
    path('executive/tasks/<int:pk>/delete/', views.executive_task_delete, name='executive_task_delete'),
    path('executive/tasks/<int:pk>/update-status/', views.executive_task_update_status, name='executive_task_update_status'),
    path('executive/tasks/<int:pk>/assign/', views.executive_task_assign, name='executive_task_assign'),
    path('executive/tasks/export/', views.export_tasks, name='export_tasks'),
    
    # Discussion Forum
    path('executive/discussions/', views.executive_discussion_list, name='executive_discussion_list'),
    path('executive/discussions/create/', views.executive_discussion_create, name='executive_discussion_create'),
    path('executive/discussions/<int:pk>/', views.executive_discussion_detail, name='executive_discussion_detail'),
    path('executive/discussions/<int:pk>/edit/', views.executive_discussion_edit, name='executive_discussion_edit'),
    path('executive/discussions/<int:pk>/delete/', views.executive_discussion_delete, name='executive_discussion_delete'),
    path('executive/discussions/<int:pk>/pin/', views.executive_discussion_pin, name='executive_discussion_pin'),
    path('executive/discussions/<int:pk>/add-comment/', views.executive_discussion_add_comment, name='executive_discussion_add_comment'),
    path('executive/discussions/comment/<int:pk>/delete/', views.executive_discussion_comment_delete, name='executive_discussion_comment_delete'),
    path('executive/discussions/comment/<int:pk>/edit/', views.executive_discussion_comment_edit, name='executive_discussion_comment_edit'),
    
    # Discussion Comments AJAX
    path('executive/discussions/<int:pk>/like/', views.executive_discussion_like, name='executive_discussion_like'),
    path('executive/discussions/comment/<int:pk>/like/', views.executive_discussion_comment_like, name='executive_discussion_comment_like'),
]