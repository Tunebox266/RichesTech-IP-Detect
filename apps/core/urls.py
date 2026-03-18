# core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('announcements/', views.announcement_list, name='announcements'),
    path('announcements/<int:pk>/', views.announcement_detail, name='announcement_detail'),
    path("announcements/create/", views.announcement_create, name="announcement_create"),
    path("announcements/<int:pk>/edit/", views.announcement_edit, name="announcement_edit"),
    path("announcements/<int:pk>/delete/", views.announcement_delete, name="announcement_delete"),
    
    path('announcements/<int:pk>/unpin/', views.announcement_unpin, name='announcement_unpin'),
    
    path('announcements/<int:pk>/archive/', views.announcement_archive, name='announcement_archive'),
    path('announcements/<int:pk>/comment/', views.announcement_comment, name='announcement_comment'),
    path(
      'announcements/reply/', 
      views.announcement_reply, 
      name='announcement_reply'
    ),
    # Announcement Likes
    path('announcements/<int:pk>/like/', views.like_announcement, name='like_announcement'), 
    
    
    
    # About and Contact URLs
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('faq/', views.faq_view, name='faq'),
    
    path('api/verify-passcode/', views.verify_student_passcode, name='verify_passcode'),
    
    # ===== LEGAL PAGES =====
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('privacy-policy/edit/', views.privacy_policy_edit, name='privacy_policy_edit'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('terms-of-service/edit/', views.terms_of_service_edit, name='terms_of_service_edit'),
    # Admin URLs for contact messages
    path('contact/messages/', views.contact_messages, name='contact_messages'),
    path('contact/messages/<int:pk>/', views.contact_message_detail, name='contact_message_detail'),
    path('contact/messages/<int:pk>/reply/', views.reply_contact_message, name='reply_contact_message'),
    path('contact/messages/<int:pk>/update-status/', views.update_message_status, name='update_message_status'),
    
    # API
    path('api/contact/', views.contact_api, name='contact_api'),

    
    path('notifications/', views.notification_list, name='notifications'),
   
    path('notifications/settings/', views.notification_settings, name='notification_settings'),
   
    path('notifications/<int:pk>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:pk>/delete/', views.delete_notification, name='delete_notification'),

    
    # Email Subscription
    path('subscribe/', views.subscribe_email, name='subscribe'),
    path('subscribe/verify/<str:token>/', views.verify_subscription, name='verify_subscription'),
    path('subscribe/unsubscribe/<str:token>/', views.unsubscribe, name='unsubscribe'),
    path('subscribe/preferences/', views.subscription_preferences, name='subscription_preferences'),
    
    
    
    path('search/', views.global_search, name='global_search'),
    
    # Dashboard views
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/staff/', views.staff_dashboard, name='staff_dashboard'),
    path('dashboard/executive/', views.executive_dashboard, name='executive_dashboard'),
    
    # Blog
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<int:pk>/', views.blog_detail, name='blog_detail'),
    path('blog/<int:pk>/comment/', views.blog_add_comment, name='blog_comment_add'),  # Changed from blog_add_comment
    path('blog/comment/reply/', views.blog_reply_comment, name='blog_comment_reply'),
    path('blog/comment/<int:pk>/delete/', views.blog_comment_delete, name='blog_comment_delete'),
    # Like URLs
    path('blog/<int:pk>/like/', views.blog_post_like, name='blog_post_like'),
    path('blog/comment/<int:pk>/like/', views.blog_comment_like, name='blog_comment_like'),
    path('blog/<int:pk>/likes/status/', views.get_user_likes_status, name='blog_likes_status'),
 
    # Vlogs
    path('vlogs/', views.vlog_list, name='vlog_list'),
    path('vlogs/<int:pk>/', views.vlog_detail, name='vlog_detail'),
    path('vlogs/<int:pk>/comment/', views.videovlog_add_comment, name='vlog_add_comment'
    ),
    path("vlog/reply-comment/", views.videovlog_reply_comment, name="vlog_reply_comment"
    ),
    
    path("vlog/<int:pk>/report/", views.videovlog_report, name="vlog_report"
    ),
    
    
    
]