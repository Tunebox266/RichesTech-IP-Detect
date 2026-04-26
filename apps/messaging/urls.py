# messaging/urls.py
from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    # Core messaging
    path('', views.inbox, name='inbox'),
    path('sent/', views.sent_messages, name='sent'),
    path('drafts/', views.drafts, name='drafts'),
    path('archived/', views.archived, name='archived'),
    path('compose/', views.compose, name='compose'),
    path('compose/<int:recipient_id>/', views.compose_to_user, name='compose_to_user'),
    
    # Message actions
    path('<int:pk>/', views.message_detail, name='message_detail'),
    path('<int:pk>/reply/', views.reply_message, name='reply_message'),
    path('<int:pk>/star/', views.toggle_star, name='toggle_star'),
    path('<int:pk>/delete/', views.delete_message, name='delete_message'),
    
    # Bulk actions
    path('bulk/mark-read/', views.bulk_mark_read, name='bulk_mark_read'),
    path('bulk/star/', views.bulk_star, name='bulk_star'),
    path('bulk/delete/', views.bulk_delete, name='bulk_delete'),
    
    # Broadcast (staff/executive only)
    path('broadcast/', views.broadcast_message, name='broadcast'),
    
    # AJAX/API endpoints
    path('api/save-draft/', views.save_draft, name='api_save_draft'),
    path('api/unread-count/', views.get_unread_count, name='api_unread_count'),
    path('api/search-users/', views.search_users, name='api_search_users'),
    path('api/mark-read/<int:pk>/', views.mark_read, name='mark_read'),
    
    # Notifications
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:pk>/', views.notification_detail, name='notification_detail'),
    path('notifications/unread-count/', views.notification_unread_count, name='notification_unread_count'),
    path('notifications/<int:pk>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/<int:pk>/unread/', views.notification_mark_unread, name='notification_mark_unread'),
    path('notifications/<int:pk>/delete/', views.notification_delete, name='notification_delete'),
    path('notifications/mark-all-read/', views.notification_mark_all_read, name='notification_mark_all_read'),
    path('notifications/delete-all-read/', views.notification_delete_all_read, name='notification_delete_all_read'),
    
    # Notification Preferences
    path('notification-preferences/', views.notification_preferences, name='notification_preferences'),
    path('notification-preferences/update/', views.notification_preferences_update, name='notification_preferences_update'),
]