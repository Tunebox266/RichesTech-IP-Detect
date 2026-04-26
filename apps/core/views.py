# core/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_POST
#from django.utils import timezone
from datetime import date, timedelta
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
from .models import (
    Announcement, Notification, NotificationSetting, BlogPost, 
    VideoVlog, AcademicSetting, StudentDocument, AnnouncementComment,
    BlogPostLike, BlogCommentLike, VideoVlogLike, VideoVlogCommentLike,
    BlogComment, VideoVlogComment
)
from apps.accounts.models import User, ActivityLog
from apps.courses.models import Course, CourseRegistration, CourseMaterial
from apps.payments.models import Due, Payment
from apps.events.models import Event
from django.core.paginator import Paginator

from apps.complaints.models import Complaint
from apps.messaging.models import Message   # ✅ FIX
from apps.attendance.models import AttendanceRecord


def home(request):
    """Home page view"""
    announcements = Announcement.objects.filter(is_active=True)[:5]
    blog_posts = BlogPost.objects.filter(published=True)[:3]
    video_vlogs = VideoVlog.objects.all()[:4]
    upcoming_events = Event.objects.filter(
        start_date__gte=timezone.now(),
        is_active=True
    )[:3]
    
    context = {
        'announcements': announcements,
        'blog_posts': blog_posts,
        'video_vlogs': video_vlogs,
        'upcoming_events': upcoming_events,
    }
     # Add flag to template if passcode is required
    if request.GET.get('require_passcode') == 'true':
        context['require_passcode'] = True
    return render(request, 'core/home.html', context)

# apps/core/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, FileResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import timedelta
import json
import os

from .models import Announcement
#from .forms import AnnouncementForm
from apps.accounts.models import User


from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from .models import Announcement
from .forms import AnnouncementForm
@login_required
def announcement_list(request):
    now = timezone.now()

    # Base queryset: active and not expired
    announcements = Announcement.objects.filter(
        is_active=True
    ).filter(
        Q(expiry_date__isnull=True) | Q(expiry_date__gte=now)
    ).order_by('-created_at')

 
    # Filter by user group
    if request.user.is_authenticated:
        user_group = request.user.user_type
        announcements = announcements.filter(
            Q(target_groups=user_group) | Q(target_groups='all')
        )

    # Filter by priority
    priority = request.GET.get('priority')
    if priority:
        mapping = {'high': 3, 'medium': 2, 'low': 1}
        if priority in mapping:
            announcements = announcements.filter(priority=mapping[priority])

    # Filter by date
    date_filter = request.GET.get('date')
    if date_filter == 'today':
        announcements = announcements.filter(created_at__date=now.date())
    elif date_filter == 'week':
        announcements = announcements.filter(created_at__gte=now - timedelta(days=7))
    elif date_filter == 'month':
        announcements = announcements.filter(created_at__gte=now - timedelta(days=30))

    # Filter by status
    status = request.GET.get('status')
    if status == 'active':
        announcements = announcements.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=now))
    elif status == 'expired':
        announcements = announcements.filter(expiry_date__lt=now)

    # Search
    search_query = request.GET.get('search')
    if search_query:
        announcements = announcements.filter(
            Q(title__icontains=search_query) | Q(content__icontains=search_query)
        )

    # Separate pinned
    pinned_announcements = announcements.filter(is_pinned=True)
    regular_announcements = announcements.filter(is_pinned=False)

    # Pagination
    paginator = Paginator(regular_announcements, 10)
    page = request.GET.get('page')
    paginated_announcements = paginator.get_page(page)

    # Archive months
    archive_months = []
    for dt in Announcement.objects.dates('created_at', 'month', order='DESC'):
        month_count = Announcement.objects.filter(
            created_at__year=dt.year,
            created_at__month=dt.month
        ).count()
        archive_months.append({
            'month': dt.month,
            'year': dt.year,
            'month_name': dt.strftime('%B'),
            'count': month_count
        })

    # Priority counts
    priority_counts = {
        'high': announcements.filter(priority=3).count(),
        'medium': announcements.filter(priority=2).count(),
        'low': announcements.filter(priority=1).count(),
    }

    context = {
        'announcements': paginated_announcements,
        'pinned_announcements': pinned_announcements,
        'pinned_count': pinned_announcements.count(),
        'archive_months': archive_months,
        'total_count': announcements.count(),
        'monthly_count': announcements.filter(created_at__month=now.month, created_at__year=now.year).count(),
        'active_count': announcements.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=now)).count(),
        'expired_count': announcements.filter(expiry_date__lt=now).count(),
        'high_count': priority_counts['high'],
        'medium_count': priority_counts['medium'],
        'low_count': priority_counts['low'],
        'now': now,
    }

    return render(request, 'core/announcements.html', context)
@login_required
def announcement_edit(request, pk):
    """Edit an existing announcement"""
    announcement = get_object_or_404(Announcement, pk=pk)

    # Only admins, staff, and executive can edit
    if request.user.user_type not in ['admin', 'staff', 'executive']:
        raise PermissionDenied

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, "Announcement updated successfully!")
            return redirect('core:announcement_detail', pk=announcement.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AnnouncementForm(instance=announcement)

    context = {
        'form': form,
        'announcement': announcement,
    }
    return render(request, 'core/announcement_form.html', context)

@login_required
def announcement_delete(request, pk):
    """Delete an announcement"""
    announcement = get_object_or_404(Announcement, pk=pk)

    # Only admins, staff, and executive can delete
    if request.user.user_type not in ['admin', 'staff', 'executive']:
        raise PermissionDenied

    if request.method == 'POST':
        announcement.delete()
        messages.success(request, "Announcement deleted successfully!")
        return redirect('core:announcements')  # back to list

    context = {
        'announcement': announcement,
    }
    return render(request, 'core/announcement_confirm_delete.html', context)
@login_required
def announcement_detail(request, pk):
    """Display a single announcement with its attachment"""
    announcement = get_object_or_404(
        Announcement,
        pk=pk,
        is_active=True
    )
    
    # Increment view count
    announcement.views += 1 if hasattr(announcement, 'views') else 0
    if hasattr(announcement, 'views'):
        announcement.save(update_fields=['views'])
    
    # Related announcements: same priority or pinned
    related_announcements = Announcement.objects.filter(
        is_active=True
    ).exclude(pk=announcement.pk).filter(
        Q(priority=announcement.priority) | Q(is_pinned=True)
    ).order_by('-created_at')[:3]
    
    context = {
        'announcement': announcement,
        'related_announcements': related_announcements,
        'attachment': announcement.attachment,  # single file
    }
    
    return render(request, 'core/announcement_detail.html', context)


@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff', 'executive'])
def announcement_create(request):
    """Create a new announcement with attachments"""
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()
            
            # Handle attachments
            attachments = request.FILES.getlist('attachments')
            for attachment in attachments:
                AnnouncementAttachment.objects.create(
                    announcement=announcement,
                    file=attachment,
                    filename=attachment.name
                )
            
            # Handle target audience from checkboxes
            target_audience = []
            if request.POST.get('target_students'):
                target_audience.append('student')
            if request.POST.get('target_executives'):
                target_audience.append('executive')
            if request.POST.get('target_staff'):
                target_audience.append('staff')
            if request.POST.get('target_all'):
                target_audience = ['student', 'executive', 'staff']
            
            announcement.target_audience = target_audience
            announcement.save()
            
            messages.success(request, 'Announcement created successfully!')
            return redirect('core:announcement_detail', pk=announcement.pk)
    else:
        form = AnnouncementForm()
    
    return render(request, 'core/announcement_create.html', {
        'form': form,
        'action': 'Create'
    })


@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff', 'executive'])
def announcement_edit(request, pk):
    """Edit an existing announcement"""
    announcement = get_object_or_404(Announcement, pk=pk)
    
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)
        if form.is_valid():
            announcement = form.save(commit=False)
            
            # Handle new attachments
            attachments = request.FILES.getlist('attachments')
            for attachment in attachments:
                AnnouncementAttachment.objects.create(
                    announcement=announcement,
                    file=attachment,
                    filename=attachment.name
                )
            
            # Handle deleted attachments
            delete_attachments = request.POST.getlist('delete_attachments')
            if delete_attachments:
                AnnouncementAttachment.objects.filter(
                    id__in=delete_attachments
                ).delete()
            
            # Update target audience
            target_audience = []
            if request.POST.get('target_students'):
                target_audience.append('student')
            if request.POST.get('target_executives'):
                target_audience.append('executive')
            if request.POST.get('target_staff'):
                target_audience.append('staff')
            if request.POST.get('target_all'):
                target_audience = ['student', 'executive', 'staff']
            
            announcement.target_audience = target_audience
            announcement.save()
            
            messages.success(request, 'Announcement updated successfully!')
            return redirect('core:announcement_detail', pk=announcement.pk)
    else:
        form = AnnouncementForm(instance=announcement)
    
    return render(request, 'core/announcement_create.html', {
        'form': form,
        'action': 'Edit',
        'announcement': announcement
    })


@login_required
def announcement_delete(request, pk):
    """Delete an announcement"""
    announcement = get_object_or_404(Announcement, pk=pk)
    
    # Check permission
    if not (request.user.user_type in ['admin', 'staff'] or 
            request.user == announcement.created_by):
        messages.error(request, 'You do not have permission to delete this announcement.')
        return redirect('core:announcement_detail', pk=pk)
    
    if request.method == 'POST':
        announcement.delete()
        messages.success(request, 'Announcement deleted successfully!')
        return redirect('core:announcements')
    
    return render(request, 'core/announcement_confirm_delete.html', {
        'announcement': announcement
    })


@login_required
def download_attachment(request, pk):
    """Download an attachment file"""
    attachment = get_object_or_404(AnnouncementAttachment, pk=pk)
    
    # Check if user has access to this announcement
    if not attachment.announcement.is_active:
        messages.error(request, 'This attachment is no longer available.')
        return redirect('core:announcements')
    
    # Increment download count if you have such field
    # attachment.download_count += 1
    # attachment.save()
    
    response = FileResponse(attachment.file)
    response['Content-Disposition'] = f'attachment; filename="{attachment.filename}"'
    return response


@login_required
def announcement_unpin(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    announcement.is_pinned = False
    announcement.save()
    messages.success(request, 'Announcement unpinned successfully.')
    return redirect('core:announcements')

@login_required
@require_POST
def announcement_view(request, pk):
    """Increment view count for an announcement"""
    announcement = get_object_or_404(Announcement, pk=pk, is_active=True)
    announcement.views += 1
    announcement.save(update_fields=['views'])
    return JsonResponse({
        'success': True,
        'views': announcement.views
    })

@login_required
def announcement_archive(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    announcement.is_archived = True
    announcement.save()
    return JsonResponse({'success': True})
@login_required
def announcement_comment(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk, is_active=True)
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            AnnouncementComment.objects.create(
                announcement=announcement,
                user=request.user,
                content=content
            )
    return redirect('core:announcement_detail', pk=pk)

from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@login_required
@require_POST
def announcement_reply(request):
    comment_id = request.POST.get('comment_id')
    content = request.POST.get('content', '').strip()
    comment = get_object_or_404(AnnouncementComment, pk=comment_id)

    if content:
        AnnouncementCommentReply.objects.create(
            comment=comment,
            user=request.user,
            content=content
        )

    return redirect('core:announcement_detail', pk=comment.announcement.pk)

@login_required
@require_POST
def subscribe_email(request):
    """Subscribe to email notifications"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        digest = data.get('digest', False)
        
        # Validate email
        if not email or '@' not in email:
            return JsonResponse({'success': False, 'message': 'Invalid email'})
        
        # Here you would save to a Subscription model
        # Subscription.objects.get_or_create(email=email, digest=digest)
        
        return JsonResponse({
            'success': True,
            'message': 'Successfully subscribed!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def notification_list(request):
    """List user notifications"""
    notifications = Notification.objects.filter(
        Q(is_global=True) | Q(target_users=request.user)
    ).order_by('-created_at')
    
    # Mark as viewed
    unread = notifications.filter(read_by__isnull=True)
    if unread.exists():
        request.session['unread_notifications'] = unread.count()
    
    paginator = Paginator(notifications, 20)
    page = request.GET.get('page')
    notifications = paginator.get_page(page)
    
    return render(request, 'core/notifications.html', {'notifications': notifications})
  
@login_required
def notification_settings(request):
    """User notification settings"""
    setting, created = NotificationSetting.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        setting.email_messages = bool(request.POST.get('email_messages'))
        setting.email_events = bool(request.POST.get('email_events'))
        setting.email_payments = bool(request.POST.get('email_payments'))
        setting.app_messages = bool(request.POST.get('app_messages'))
        setting.app_events = bool(request.POST.get('app_events'))
        setting.app_payments = bool(request.POST.get('app_payments'))
        setting.quiet_start = request.POST.get('quiet_start') or None
        setting.quiet_end = request.POST.get('quiet_end') or None
        setting.digest = request.POST.get('digest', 'never')
        setting.save()
        return redirect('core:notification_settings')
    
    return render(request, 'core/notification_settings.html', {'setting': setting})


# apps/core/views.py

from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
import json
import uuid

from .models import Announcement, AnnouncementLike, EmailSubscription, SubscriptionLog


@login_required
@require_POST
def like_announcement(request, pk):
    """Toggle like on an announcement"""
    try:
        announcement = get_object_or_404(Announcement, pk=pk)
        
        # Check if user already liked
        like, created = AnnouncementLike.objects.get_or_create(
            announcement=announcement,
            user=request.user
        )
        
        if not created:
            # Unlike - delete the like
            like.delete()
            liked = False
            message = 'Announcement unliked'
        else:
            liked = True
            message = 'Announcement liked'
            
            # Create notification for announcement author (if not self)
            if announcement.created_by != request.user:
                Notification.objects.create(
                    user=announcement.created_by,
                    title='New Like on Your Announcement',
                    message=f'{request.user.get_full_name()} liked your announcement "{announcement.title}"',
                    notification_type='info',
                    created_by=request.user
                )
        
        # Get updated like count
        likes_count = announcement.likes.count()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='like',
            ip_address=get_client_ip(request),
            details={
                'announcement_id': announcement.id,
                'title': announcement.title,
                'action': 'liked' if liked else 'unliked'
            }
        )
        
        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': likes_count,
            'message': message
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@require_POST
def subscribe_email(request):
    """Subscribe to email notifications"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        digest = data.get('digest', False)
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        
        if not email:
            return JsonResponse({
                'success': False,
                'error': 'Email is required'
            }, status=400)
        
        # Validate email format
        import re
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return JsonResponse({
                'success': False,
                'error': 'Invalid email format'
            }, status=400)
        
        # Get or create subscription
        subscription, created = EmailSubscription.objects.get_or_create(
            email=email.lower(),
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'frequency': 'daily' if digest else 'instant',
                'verification_token': get_random_string(64),
            }
        )
        
        if not created:
            # Update existing subscription
            subscription.is_active = True
            subscription.frequency = 'daily' if digest else subscription.frequency
            if first_name:
                subscription.first_name = first_name
            if last_name:
                subscription.last_name = last_name
            subscription.save()
        
        # Log subscription
        SubscriptionLog.objects.create(
            subscription=subscription,
            action='subscribe',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        # Send verification email
        send_verification_email(subscription)
        
        return JsonResponse({
            'success': True,
            'message': 'Successfully subscribed! Please check your email to verify.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def send_verification_email(subscription):
    """Send verification email to subscriber"""
    subject = 'Verify Your Email Subscription - MELTSA-TaTU'
    
    context = {
        'subscription': subscription,
        'full_name': subscription.get_full_name(),
        'verify_url': f"{settings.SITE_URL}/core/subscribe/verify/{subscription.verification_token}/",
        'unsubscribe_url': f"{settings.SITE_URL}/core/subscribe/unsubscribe/{subscription.verification_token}/",
    }
    
    html_message = render_to_string('core/emails/subscription_verify.html', context)
    plain_message = render_to_string('core/emails/subscription_verify.txt', context)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [subscription.email],
        html_message=html_message,
        fail_silently=True,
    )


def verify_subscription(request, token):
    """Verify email subscription"""
    try:
        subscription = get_object_or_404(EmailSubscription, verification_token=token)
        
        if not subscription.verified:
            subscription.verified = True
            subscription.save()
            
            # Log verification
            SubscriptionLog.objects.create(
                subscription=subscription,
                action='verify',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
            messages.success(request, 'Your email has been verified successfully!')
        else:
            messages.info(request, 'Your email was already verified.')
            
    except EmailSubscription.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
    
    return redirect('core:home')


def unsubscribe(request, token):
    """Unsubscribe from email notifications"""
    try:
        subscription = get_object_or_404(EmailSubscription, verification_token=token)
        
        subscription.is_active = False
        subscription.unsubscribed_at = timezone.now()
        subscription.save()
        
        # Log unsubscription
        SubscriptionLog.objects.create(
            subscription=subscription,
            action='unsubscribe',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        messages.success(request, 'You have been unsubscribed successfully.')
        
    except EmailSubscription.DoesNotExist:
        messages.error(request, 'Invalid unsubscribe link.')
    
    return redirect('core:home')


@login_required
def subscription_preferences(request):
    """View and update subscription preferences"""
    try:
        subscription = EmailSubscription.objects.get(email=request.user.email)
    except EmailSubscription.DoesNotExist:
        subscription = EmailSubscription(
            email=request.user.email,
            first_name=request.user.first_name,
            last_name=request.user.last_name,
            verified=True  # Auto-verify for logged-in users
        )
    
    if request.method == 'POST':
        subscription.frequency = request.POST.get('frequency', 'instant')
        subscription.subscribe_announcements = bool(request.POST.get('subscribe_announcements'))
        subscription.subscribe_events = bool(request.POST.get('subscribe_events'))
        subscription.subscribe_blog = bool(request.POST.get('subscribe_blog'))
        subscription.is_active = bool(request.POST.get('is_active', True))
        subscription.save()
        
        # Log update
        SubscriptionLog.objects.create(
            subscription=subscription,
            action='updated',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        messages.success(request, 'Your subscription preferences have been updated.')
        return redirect('core:subscription_preferences')
     
    return render(request, 'core/subscription_preferences.html', {'subscription': subscription})


@login_required
def mark_notification_read(request, pk):
    """Mark notification as read"""
    notification = get_object_or_404(Notification, pk=pk)
    notification.read_by.add(request.user)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('core:notifications')

@login_required
def mark_all_notifications_read(request):
    """Mark all user notifications as read"""
    # Get all notifications for the user that are unread
    unread_notifications = Notification.objects.filter(
        Q(is_global=True) | Q(target_users=request.user)
    ).exclude(read_by=request.user)

    # Mark them all as read by adding the user
    for notification in unread_notifications:
        notification.read_by.add(request.user)
    
    # Reset unread count in session
    request.session['unread_notifications'] = 0

    # If called via AJAX, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'All notifications marked as read'})

    # Otherwise redirect to notifications page
    return redirect('core:notifications')
    


@login_required
def delete_notification(request, pk):
    """Delete a notification"""
    notification = get_object_or_404(Notification, pk=pk)
    
    # Check if user has permission to delete
    if request.user in notification.target_users.all() or request.user == notification.created_by:
        notification.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        messages.success(request, 'Notification deleted successfully')
        return redirect('core:notifications')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    messages.error(request, 'You do not have permission to delete this notification')
    return redirect('core:notifications')

@login_required
def student_dashboard(request):
    """Student dashboard view"""
    current_academic = AcademicSetting.objects.filter(is_active=True).first()
    
    # Get registered courses
    registered_courses = CourseRegistration.objects.filter(
        student=request.user,
        academic_setting=current_academic
    ).select_related('course')
    
    registrations = CourseRegistration.objects.filter(
        student=request.user,
        academic_setting=current_academic
    ).select_related('course')

    registered_courses = registrations.count()

    course_materials = CourseMaterial.objects.filter(
        course__in=registrations.values_list('course', flat=True)
    ).order_by('-uploaded_at')[:5]
    
    # Get dues
    dues = Due.objects.filter(
        is_active=True,
        academic_setting=current_academic
    )
    
    # Get payments
    
    payments = Payment.objects.filter(student=request.user)
    
    paid_dues = payments.filter(status='success').values_list('due_id', flat=True)
    
    # Total dues assigned to this user
     # Total dues assigned to this user
    # Total dues assigned to this student
    total_dues = Payment.objects.filter(student=request.user).values_list('due_id', flat=True).distinct().count()

    # Calculate percentage
    # Calculate percentage
    if total_dues > 0:
        payment_percentage = (len(paid_dues) / total_dues) * 100
    else:
        payment_percentage = 0
    
    
    
    context = {
        'registrations': registrations,
        'registered_courses': registered_courses,
        'current_academic': current_academic,
        'total_credits': sum(r.course.credit_hours for r in registrations),
        'payments': payments,
        'payment_percentage': round(payment_percentage, 2),
    }
    
    return render(request, 'core/students/dashboard.html', context)

@staff_member_required
def admin_dashboard(request):
    """Admin dashboard view"""
    # Statistics
    total_students = User.objects.filter(user_type='student').count()
    total_staff = User.objects.filter(user_type='staff').count()
    total_executives = User.objects.filter(user_type='executive').count()
    
    # Students by level
    students_by_level = User.objects.filter(
        user_type='student'
    ).values('level').annotate(
        count=Count('id')
    ).order_by('level')
    
    # Students by program
    students_by_program = User.objects.filter(
        user_type='student'
    ).values('program_type').annotate(
        count=Count('id')
    )
    
    # Payment statistics
    current_academic = AcademicSetting.objects.filter(is_active=True).first()
    total_dues = Due.objects.filter(
        academic_setting=current_academic
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_paid = Payment.objects.filter(
        due__academic_setting=current_academic,
        status='success'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Recent activities
    recent_activities = ActivityLog.objects.select_related('user')[:10]
    
    # Recent payments
    recent_payments = Payment.objects.select_related(
        'student', 'due'
    ).filter(status='success')[:10]
    
    # Recent registrations
    recent_registrations = User.objects.filter(
        user_type='student'
    ).order_by('-date_joined')[:10]
    
    context = {
        'total_students': total_students,
        'total_staff': total_staff,
        'total_executives': total_executives,
        'students_by_level': students_by_level,
        'students_by_program': students_by_program,
        'total_dues': total_dues,
        'total_paid': total_paid,
        'collection_rate': (total_paid / total_dues * 100) if total_dues > 0 else 0,
        'recent_activities': recent_activities,
        'recent_payments': recent_payments,
        'recent_registrations': recent_registrations,
    }
    return render(request, 'core/admin/dashboard.html', context)

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

# Import your models
from apps.accounts.models import User, StudentExecutive
from apps.complaints.models import Complaint
from apps.events.models import Event
from apps.courses.models import CourseMaterial

@login_required
def staff_dashboard(request):
    """Staff dashboard view"""
    if request.user.user_type not in ['staff', 'admin']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    # Statistics
    total_students = User.objects.filter(user_type='student').count()
    total_executives = User.objects.filter(user_type='executive').count()
    
    # Pending complaints
    pending_complaints = Complaint.objects.filter(status='pending').count()
    
    # Recent complaints
    recent_complaints = Complaint.objects.select_related(
        'student'
    ).order_by('-created_at')[:5]
    
    # Upcoming events
    upcoming_events = Event.objects.filter(
        start_date__gte=timezone.now(),
        is_active=True
    ).order_by('start_date')[:5]
    
    # Recent course materials uploaded
    recent_materials = CourseMaterial.objects.select_related(
        'course', 'uploaded_by'
    ).order_by('-uploaded_at')[:5]
    
    context = {
        'total_students': total_students,
        'total_executives': total_executives,
        'pending_complaints': pending_complaints,
        'recent_complaints': recent_complaints,
        'upcoming_events': upcoming_events,
        'recent_materials': recent_materials,
    }
    return render(request, 'core/staff/dashboard.html', context)

@login_required
def executive_dashboard(request):
    """Executive dashboard view"""
    if request.user.user_type != 'executive':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    # Statistics
    total_students = User.objects.filter(user_type='student').count()
    
    # Events created by this executive
    my_events = Event.objects.filter(created_by=request.user).order_by('-start_date')[:5]
    
    # Upcoming events
    upcoming_events = Event.objects.filter(
        start_date__gte=timezone.now(),
        is_active=True
    )[:5]
    
    # Recent attendance records
    recent_attendance = AttendanceRecord.objects.filter(
        session__created_by=request.user
    ).select_related('student', 'session')[:10]
    
    # Recent complaints to address
    pending_complaints = Complaint.objects.filter(status='pending')[:5]
    
    # Recent messages
    recent_messages = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).order_by('-sent_at')[:5]
    
    tenure = None
    student_exec = StudentExecutive.objects.filter(user=request.user).first()
    if student_exec:
        today = date.today()
        tenure_days = (student_exec.tenure_end_date - student_exec.tenure_start_date).days
        remaining_days = (student_exec.tenure_end_date - today).days

        tenure = {
            'position': student_exec.position,  # <-- added position
            'start_date': student_exec.tenure_start_date,
            'end_date': student_exec.tenure_end_date,
            'total_days': tenure_days,
            'remaining_days': max(remaining_days, 0)
        }
        
    
    
                
    
    context = {
        'total_students': total_students,
        'my_events': my_events,
        'upcoming_events': upcoming_events,
        'recent_attendance': recent_attendance,
        'pending_complaints': pending_complaints,
        'recent_messages': recent_messages,
        #'executive': executives,
        'tenure': tenure,
    }
    return render(request, 'core/executive/dashboard.html', context)



# apps/core/views.py

from django.core.paginator import Paginator
from django.db.models import Q
from .models import BlogPost, Category

def blog_list(request):
    """List all blog posts"""
    blogs = BlogPost.objects.filter(published=True)
    
    # Search
    search_query = request.GET.get('search')
    if search_query:
        blogs = blogs.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query)
        )
    
    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        blogs = blogs.filter(category_id=category_id)
    
    # Sorting
    sort = request.GET.get('sort', '-created_at')
    blogs = blogs.order_by(sort)
    
    # Get categories for filter
    categories = Category.objects.all()
    
    # Pagination
    paginator = Paginator(blogs, 9)
    page = request.GET.get('page')
    blogs = paginator.get_page(page)
    
    context = {
        'blogs': blogs,
        'categories': categories,
    }
    return render(request, 'core/blog_list.html', context)

def blog_detail(request, pk):
    """View single blog post"""
    post = get_object_or_404(BlogPost, pk=pk, published=True)
    post.views += 1
    post.save()
    
    # Get related posts
    related_posts = BlogPost.objects.filter(
        published=True
    ).exclude(pk=pk)[:3]
    
    return render(request, 'core/blog_detail.html', {
        'post': post,
        'related_posts': related_posts
    })

def vlog_list(request):
    """List video vlogs"""
    vlogs = VideoVlog.objects.all()
    
    paginator = Paginator(vlogs, 8)
    page = request.GET.get('page')
    vlogs = paginator.get_page(page)
    
    return render(request, 'core/vlog_list.html', {'vlogs': vlogs})

# apps/core/views.py

def vlog_detail(request, pk):
    vlog = get_object_or_404(VideoVlog, pk=pk)
    
    # Get all comments for this vlog
    comments = VideoVlogComment.objects.filter(videovlog=vlog).select_related('user')
    
    # Increment view count
    vlog.views += 1
    vlog.save()
    
    context = {
        'vlog': vlog,
        'comments': comments,  # Make sure this is included
    }
    return render(request, 'core/vlog_detail.html', context)

@login_required
def global_search(request):
    """Global search functionality"""
    query = request.GET.get('q', '').strip()
    results = {}
    
    if query and len(query) >= 2:
        # Search students (if authenticated)
        if request.user.is_authenticated:
            students = User.objects.filter(
                Q(user_type='student') | Q(user_type='executive')
            ).filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(student_id__icontains=query)
            ).distinct()[:10]
            
            results['students'] = [{
                'id': s.id,
                'name': s.get_full_name(),
                'student_id': s.student_id,
                'type': 'Executive' if s.user_type == 'executive' else 'Student',
                'url': f'/directory/student/{s.id}/'
            } for s in students]
        
        # Search courses
        courses = Course.objects.filter(
            Q(code__icontains=query) |
            Q(title__icontains=query)
        )[:10]
        
        results['courses'] = [{
            'id': c.id,
            'code': c.code,
            'title': c.title,
            'level': c.get_level_display(),
            'url': f'/courses/{c.id}/'
        } for c in courses]
        
        # Search announcements
        announcements = Announcement.objects.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query)
        )[:10]
        
        results['announcements'] = [{
            'id': a.id,
            'title': a.title,
            'date': a.created_at.strftime('%Y-%m-%d'),
            'url': f'/announcements/{a.id}/'
        } for a in announcements]
        
        # Search blog posts
        blog_posts = BlogPost.objects.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query),
            published=True
        )[:10]
        
        results['blog_posts'] = [{
            'id': b.id,
            'title': b.title,
            'author': b.author.get_full_name(),
            'url': f'/blog/{b.id}/'
        } for b in blog_posts]
        
        # Search events
        events = Event.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query),
            is_active=True
        )[:10]
        
        results['events'] = [{
            'id': e.id,
            'title': e.title,
            'date': e.start_date.strftime('%Y-%m-%d'),
            'url': f'/events/{e.id}/'
        } for e in events]
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(results)
    
    return render(request, 'core/search_results.html', {
        'results': results,
        'query': query
    })



# apps/core/views.py (add these to your existing views)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
import json

from .models import (
    About, ExecutiveTeam, ContactInfo, ContactMessage, 
    FAQ, Partner, Testimonial
)
from .forms import ContactForm, FAQSearchForm, QuickContactForm


def about_view(request):
    """About page view"""
    # Get about page content (should only be one)
    about = About.objects.first()
    
    # If no about content exists, create default
    if not about:
        about = About.objects.create(
            mission="Our mission is to promote academic excellence and professional development among medical laboratory students.",
            vision="To be the leading student association in medical laboratory science education in Ghana.",
            history="Founded in 2010, MELTSA-TaTU has grown to become a vibrant community of future medical laboratory professionals."
        )
    
    # Get executive team
    executive_team = ExecutiveTeam.objects.filter(is_active=True)
    
    # Get testimonials
    testimonials = Testimonial.objects.filter(is_active=True)[:6]
    
    # Get partners
    partners = Partner.objects.filter(is_active=True)
    
    # Get FAQ featured
    faqs = FAQ.objects.filter(is_active=True, is_featured=True)[:5]
    
    context = {
        'about': about,
        'executive_team': executive_team,
        'testimonials': testimonials,
        'partners': partners,
        'faqs': faqs,
    }
    
    return render(request, 'core/about.html', context)


def contact_view(request):
    """Contact page view"""
    # Get contact information
    contact_info = ContactInfo.objects.first()
    
    # If no contact info exists, create default
    if not contact_info:
        contact_info = ContactInfo.objects.create(
            primary_email="info@meltsa.edu",
            primary_phone="+233 (0) 59 190 7870",
            address_line1="Tamale Technical University",
            city="Tamale",
            region="Northern Region",
            country="Ghana"
        )
    
    # Get FAQs for contact page
    faqs = FAQ.objects.filter(is_active=True)[:3]
    
    # Handle contact form submission
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            
            # Get client IP and user agent
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                message.ip_address = x_forwarded_for.split(',')[0]
            else:
                message.ip_address = request.META.get('REMOTE_ADDR')
            
            message.user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # If user is logged in, associate with user
            if request.user.is_authenticated:
                # You could add a user field to ContactMessage if needed
                pass
            
            message.save()
            
            # Send email notification (implement later)
            # send_contact_notification(message)
            
            messages.success(request, 'Your message has been sent successfully! We will get back to you soon.')
            return redirect('core:contact')
    else:
        form = ContactForm()
    
    # Quick contact form for sidebar
    quick_form = QuickContactForm()
    
    context = {
        'contact_info': contact_info,
        'form': form,
        'quick_form': quick_form,
        'faqs': faqs,
    }
    
    return render(request, 'core/contact.html', context)


def faq_view(request):
    """FAQ page view"""
    # Get all FAQs
    faqs = FAQ.objects.filter(is_active=True)
    
    # Handle search
    search_form = FAQSearchForm(request.GET)
    if search_form.is_valid():
        query = search_form.cleaned_data.get('query')
        category = search_form.cleaned_data.get('category')
        
        if query:
            faqs = faqs.filter(
                Q(question__icontains=query) | 
                Q(answer__icontains=query)
            )
        
        if category:
            faqs = faqs.filter(category=category)
    
    # Group FAQs by category
    categories = {}
    for faq in faqs:
        cat = faq.get_category_display()
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(faq)
    
    context = {
        'categories': categories,
        'search_form': search_form,
        'total_faqs': faqs.count(),
    }
    
    return render(request, 'core/faq.html', context)


@login_required
def contact_messages(request):
    """View contact messages (admin/staff only)"""
    if not request.user.user_type in ['admin', 'staff']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    # Get all messages
    messages_list = ContactMessage.objects.all()
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        messages_list = messages_list.filter(status=status)
    
    # Search
    search = request.GET.get('search')
    if search:
        messages_list = messages_list.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(subject__icontains=search) |
            Q(message__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(messages_list, 20)
    page = request.GET.get('page')
    messages_list = paginator.get_page(page)
    
    # Statistics
    stats = {
        'total': ContactMessage.objects.count(),
        'new': ContactMessage.objects.filter(status='new').count(),
        'replied': ContactMessage.objects.filter(status='replied').count(),
    }
    
    context = {
        'messages': messages_list,
        'stats': stats,
        'status_choices': ContactMessage.STATUS_CHOICES,
    }
    
    return render(request, 'core/contact_messages.html', context)


@login_required
def contact_message_detail(request, pk):
    """View single contact message"""
    if not request.user.user_type in ['admin', 'staff']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    message = get_object_or_404(ContactMessage, pk=pk)
    
    # Mark as read if new
    if message.status == 'new':
        message.status = 'read'
        message.save()
    
    context = {
        'message': message,
    }
    
    return render(request, 'core/contact_message_detail.html', context)


@login_required
@require_POST
def reply_contact_message(request, pk):
    """Reply to contact message"""
    if not request.user.user_type in ['admin', 'staff']:
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    message = get_object_or_404(ContactMessage, pk=pk)
    
    try:
        data = json.loads(request.body)
        reply_text = data.get('reply')
        
        if not reply_text:
            return JsonResponse({'success': False, 'error': 'Reply text is required'})
        
        message.reply_message = reply_text
        message.status = 'replied'
        message.replied_at = timezone.now()
        message.replied_by = request.user
        message.save()
        
        # Send email with reply (implement later)
        # send_reply_email(message)
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def update_message_status(request, pk):
    """Update contact message status"""
    if not request.user.user_type in ['admin', 'staff']:
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    message = get_object_or_404(ContactMessage, pk=pk)
    
    try:
        data = json.loads(request.body)
        status = data.get('status')
        
        if status not in dict(ContactMessage.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'})
        
        message.status = status
        message.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def contact_api(request):
    """API endpoint for quick contact form"""
    if request.method == 'POST':
        form = QuickContactForm(request.POST)
        if form.is_valid():
            # Create message
            message = ContactMessage.objects.create(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                subject="Quick Contact",
                message=form.cleaned_data['message'],
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Thank you for contacting us!'
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


# apps/core/views.py - Add these functions

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import ContactMessage
import json


@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff'])
def reply_contact_message(request, pk):
    """Reply to a contact message"""
    message = get_object_or_404(ContactMessage, pk=pk)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            reply_text = data.get('reply')
            
            if not reply_text:
                return JsonResponse({'success': False, 'error': 'Reply text is required'})
            
            message.reply_message = reply_text
            message.status = 'replied'
            message.replied_at = timezone.now()
            message.replied_by = request.user
            message.save()
            
            # Here you would send an email to the user
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff'])
@require_POST
def update_message_status(request, pk):
    """Update contact message status"""
    message = get_object_or_404(ContactMessage, pk=pk)
    
    try:
        data = json.loads(request.body)
        status = data.get('status')
        
        if status not in dict(ContactMessage.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'})
        
        message.status = status
        message.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})





from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import VideoVlog, VideoVlogComment, VideoVlogReport

@login_required
def videovlog_add_comment(request, pk):
    videovlog = get_object_or_404(VideoVlog, pk=pk)

    if request.method == "POST":
        content = request.POST.get("content")

        if content:
            VideoVlogComment.objects.create(
                videovlog=videovlog,
                user=request.user,
                content=content
            )

    return redirect('core:vlog_detail', pk=pk)

@login_required
def videovlog_reply_comment(request):
    if request.method == "POST":
        comment_id = request.POST.get("comment_id")
        content = request.POST.get("content")

        parent_comment = get_object_or_404(VideoVlogComment, id=comment_id)

        VideoVlogComment.objects.create(
            videovlog=parent_comment.videovlog,
            user=request.user,
            content=content,
            parent=parent_comment
        )

        return redirect('core:vlog_detail', pk=parent_comment.videovlog.id)

@login_required
def videovlog_report(request, pk):
    videovlog = get_object_or_404(VideoVlog, pk=pk)

    if request.method == "POST":
        reason = request.POST.get("reason")
        description = request.POST.get("description")

        VideoVlogReport.objects.create(
            videovlog=videovlog,
            user=request.user,
            reason=reason,
            description=description
        )

        messages.success(request, "Report submitted successfully.")
        return redirect("core:vlog_detail", pk=videovlog.id)

    return redirect("core:vlog_detail", pk=videovlog.id)

# apps/core/views.py
# apps/core/views.py

# apps/core/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import BlogPost, BlogComment
import json

def blog_detail(request, pk):
    """Display a single blog post"""
    blog = get_object_or_404(BlogPost, pk=pk, published=True)
    
    # Increment view count
    blog.views += 1
    blog.save(update_fields=['views'])
    
    # Get comments
    comments = blog.comments.filter(parent=None).order_by('-created_at')
    
    context = {
        'blog': blog,
        'comments': comments,
    }
    return render(request, 'core/blog_detail.html', context)


@login_required
@require_POST
def blog_add_comment(request, pk):
    """Add a comment to a blog post"""
    blog = get_object_or_404(BlogPost, pk=pk)
    
    content = request.POST.get('content', '').strip()
    
    if not content:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Comment cannot be empty'})
        messages.error(request, 'Comment cannot be empty')
        return redirect('core:blog_detail', pk=pk)
    
    # Create comment
    comment = BlogComment.objects.create(
        blog=blog,
        user=request.user,
        content=content
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
                'user_name': request.user.get_full_name() or request.user.username,
                'user_avatar': request.user.profile_image.url if request.user.profile_image else None,
            }
        })
    
    messages.success(request, 'Comment added successfully')
    return redirect('core:blog_detail', pk=pk)


@login_required
@require_POST
def blog_reply_comment(request):
    """Reply to a comment"""
    comment_id = request.POST.get('comment_id')
    content = request.POST.get('content', '').strip()
    
    if not comment_id or not content:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Invalid request'})
        messages.error(request, 'Invalid request')
        return redirect('core:blog_list')
    
    parent = get_object_or_404(BlogComment, pk=comment_id)
    
    reply = BlogComment.objects.create(
        blog=parent.blog,
        user=request.user,
        content=content,
        parent=parent
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'reply': {
                'id': reply.id,
                'content': reply.content,
                'created_at': reply.created_at.isoformat(),
                'user_name': request.user.get_full_name() or request.user.username,
                'parent_id': parent.id,
            }
        })
    
    messages.success(request, 'Reply added successfully')
    return redirect('core:blog_detail', pk=parent.blog.pk)


@login_required
@require_POST
def blog_comment_delete(request, pk):
    """Delete a comment"""
    comment = get_object_or_404(BlogComment, pk=pk, user=request.user)
    blog_id = comment.blog.id
    comment.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    messages.success(request, 'Comment deleted successfully')
    return redirect('core:blog_detail', pk=blog_id)


@login_required
@require_POST
def blog_like(request, pk):
    """Like a blog post"""
    blog = get_object_or_404(BlogPost, pk=pk)
    
    # This would require a BlogLike model
    # For now, just return success
    
    return JsonResponse({'success': True})
# apps/core/views.py

# apps/core/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login
from django.utils import timezone
from datetime import timedelta
import json
from django.conf import settings

# Simple passcode - store in settings for security
STUDENT_PASSCODE = getattr(settings, 'STUDENT_PASSCODE', '1234')

@csrf_exempt
def verify_student_passcode(request):
    """Verify student passcode for login"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            passcode = data.get('passcode', '')
            
            if passcode == STUDENT_PASSCODE:
                # Set session flag indicating passcode verified
                request.session['passcode_verified'] = True
                request.session['passcode_verified_time'] = timezone.now().isoformat()
                request.session.set_expiry(3600)  # Session expires in 1 HOUR
                
                # Force session save
                request.session.save()
                
                # Get the return URL from the request if any
                next_url = data.get('next', '/accounts/login/')
                
                return JsonResponse({
                    'success': True,
                    'message': 'Passcode verified',
                    'redirect_url': next_url
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid passcode'
                }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'message': 'Method not allowed'
    }, status=405)


from .models import PrivacyPolicy, TermsOfService
from .forms import PrivacyPolicyForm, TermsOfServiceForm


def privacy_policy(request):
    """Privacy policy page"""
    # Get current privacy policy
    privacy_policy = PrivacyPolicy.objects.filter(is_current=True).first()
    
    # If no policy exists, create a default one (for first time)
    if not privacy_policy:
        privacy_policy = PrivacyPolicy.objects.create(
            title="Privacy Policy",
            content="""<h1>Privacy Policy for MELTSA-TaTU</h1>
            
            <p>Effective Date: [Date]</p>
            
            <h2>1. Introduction</h2>
            <p>Welcome to the Medical Laboratory Science Students Association - Tamale Technical University (MELTSA-TaTU). We are committed to protecting your personal information and your right to privacy.</p>
            
            <h2>2. Information We Collect</h2>
            <p>We collect personal information that you voluntarily provide to us when you register on the platform, express an interest in obtaining information about us or our services, or otherwise contact us.</p>
            
            <h2>3. How We Use Your Information</h2>
            <p>We use personal information collected via our platform for a variety of business purposes described below:</p>
            <ul>
                <li>To facilitate account creation and login process</li>
                <li>To send administrative information to you</li>
                <li>To protect our services</li>
                <li>To enforce our terms, conditions, and policies</li>
            </ul>
            
            <h2>4. Will Your Information Be Shared With Anyone?</h2>
            <p>We only share information with your consent, to comply with laws, to provide you with services, to protect your rights, or to fulfill business obligations.</p>
            
            <h2>5. How Long Do We Keep Your Information?</h2>
            <p>We keep your information for as long as necessary to fulfill the purposes outlined in this privacy policy unless otherwise required by law.</p>
            
            <h2>6. How Do We Keep Your Information Safe?</h2>
            <p>We have implemented appropriate technical and organizational security measures designed to protect the security of any personal information we process.</p>
            
            <h2>7. What Are Your Privacy Rights?</h2>
            <p>You may review, change, or terminate your account at any time.</p>
            
            <h2>8. Updates to This Policy</h2>
            <p>We may update this privacy policy from time to time. The updated version will be indicated by an updated "Effective Date".</p>
            
            <h2>9. Contact Us</h2>
            <p>If you have questions or comments about this policy, you may contact us at:</p>
            <p>MELTSA-TaTU<br>
            Tamale Technical University<br>
            Email: privacy@meltsa.edu</p>""",
            version="v1.0",
            effective_date=timezone.now().date(),
            is_current=True
        )
    
    # Get all versions for history
    all_versions = PrivacyPolicy.objects.all().order_by('-effective_date')
    
    context = {
        'privacy_policy': privacy_policy,
        'all_versions': all_versions,
    }
    return render(request, 'core/privacy_policy.html', context)


def terms_of_service(request):
    """Terms of service page"""
    terms = TermsOfService.objects.filter(is_current=True).first()
    
    # If no terms exist, create a default one
    if not terms:
        terms = TermsOfService.objects.create(
            title="Terms of Service",
            content="""<h1>Terms of Service for MELTSA-TaTU</h1>
            
            <p>Effective Date: [Date]</p>
            
            <h2>1. Acceptance of Terms</h2>
            <p>By accessing or using the MELTSA-TaTU platform, you agree to be bound by these Terms of Service.</p>
            
            <h2>2. Description of Service</h2>
            <p>MELTSA-TaTU provides an online platform for medical laboratory science students to access course materials, announcements, events, and communicate with each other.</p>
            
            <h2>3. User Accounts</h2>
            <p>You are responsible for maintaining the confidentiality of your account and password. You agree to accept responsibility for all activities that occur under your account.</p>
            
            <h2>4. User Conduct</h2>
            <p>You agree not to use the service to:</p>
            <ul>
                <li>Upload any content that is illegal, harmful, or offensive</li>
                <li>Impersonate any person or entity</li>
                <li>Interfere with or disrupt the service</li>
                <li>Violate any applicable laws or regulations</li>
            </ul>
            
            <h2>5. Intellectual Property</h2>
            <p>The service and its original content, features, and functionality are owned by MELTSA-TaTU and are protected by copyright, trademark, and other intellectual property laws.</p>
            
            <h2>6. Termination</h2>
            <p>We may terminate or suspend your account immediately, without prior notice or liability, for any reason whatsoever.</p>
            
            <h2>7. Limitation of Liability</h2>
            <p>In no event shall MELTSA-TaTU be liable for any indirect, incidental, special, consequential or punitive damages.</p>
            
            <h2>8. Changes to Terms</h2>
            <p>We reserve the right to modify or replace these Terms at any time.</p>
            
            <h2>9. Contact Us</h2>
            <p>If you have any questions about these Terms, please contact us at terms@meltsa.edu</p>""",
            version="v1.0",
            effective_date=timezone.now().date(),
            is_current=True
        )
    
    all_versions = TermsOfService.objects.all().order_by('-effective_date')
    
    context = {
        'terms': terms,
        'all_versions': all_versions,
    }
    return render(request, 'core/terms_of_service.html', context)


@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def privacy_policy_edit(request):
    """Edit privacy policy (admin only)"""
    privacy_policy = PrivacyPolicy.objects.filter(is_current=True).first()
    
    if request.method == 'POST':
        form = PrivacyPolicyForm(request.POST, instance=privacy_policy)
        if form.is_valid():
            policy = form.save()
            messages.success(request, 'Privacy policy updated successfully.')
            return redirect('core:privacy_policy')
    else:
        form = PrivacyPolicyForm(instance=privacy_policy)
    
    return render(request, 'core/privacy_policy_edit.html', {'form': form})


@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def terms_of_service_edit(request):
    """Edit terms of service (admin only)"""
    terms = TermsOfService.objects.filter(is_current=True).first()
    
    if request.method == 'POST':
        form = TermsOfServiceForm(request.POST, instance=terms)
        if form.is_valid():
            terms = form.save()
            messages.success(request, 'Terms of service updated successfully.')
            return redirect('core:terms_of_service')
    else:
        form = TermsOfServiceForm(instance=terms)
    
    return render(request, 'core/terms_of_service_edit.html', {'form': form})

# apps/core/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import BlogPost, BlogComment

@login_required
def add_blog_comment(request, pk):
    """Add a comment to a blog post"""
    blog = get_object_or_404(BlogPost, pk=pk)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        
        if content:
            # Create the comment
            comment = BlogComment.objects.create(
                blog=blog,
                user=request.user,
                content=content
            )
            
            messages.success(request, 'Your comment has been added successfully!')
        else:
            messages.error(request, 'Comment cannot be empty.')
    
    return redirect('core:blog_detail', pk=pk)

# apps/core/views.py - Add these like views

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import BlogPost, BlogComment, BlogPostLike, BlogCommentLike

@login_required
@require_POST
def blog_post_like(request, pk):
    """Like or unlike a blog post"""
    try:
        blog = get_object_or_404(BlogPost, pk=pk)
        
        # Check if user already liked this post
        like, created = BlogPostLike.objects.get_or_create(
            blog=blog,
            user=request.user
        )
        
        if not created:
            # Unlike if already liked
            like.delete()
            liked = False
        else:
            liked = True
            
            # Create notification for blog author (if not self)
            if blog.author != request.user:
                Notification.objects.create(
                    user=blog.author,
                    title='New Like on Your Blog Post',
                    message=f'{request.user.get_full_name()} liked your blog post "{blog.title}"',
                    notification_type='info',
                    created_by=request.user
                )
        
        # Get updated like count
        like_count = blog.likes.count()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='like',
            ip_address=get_client_ip(request),
            details={
                'blog_id': blog.id,
                'title': blog.title,
                'action': 'liked' if liked else 'unliked'
            }
        )
        
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': like_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def blog_comment_like(request, pk):
    """Like or unlike a blog comment"""
    try:
        comment = get_object_or_404(BlogComment, pk=pk)
        
        # Check if user already liked this comment
        like, created = BlogCommentLike.objects.get_or_create(
            comment=comment,
            user=request.user
        )
        
        if not created:
            # Unlike if already liked
            like.delete()
            liked = False
        else:
            liked = True
            
            # Create notification for comment author (if not self)
            if comment.user != request.user:
                Notification.objects.create(
                    user=comment.user,
                    title='New Like on Your Comment',
                    message=f'{request.user.get_full_name()} liked your comment on "{comment.blog.title}"',
                    notification_type='info',
                    created_by=request.user
                )
        
        # Get updated like count
        like_count = comment.likes.count()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='like',
            ip_address=get_client_ip(request),
            details={
                'comment_id': comment.id,
                'blog_id': comment.blog.id,
                'action': 'liked' if liked else 'unliked'
            }
        )
        
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': like_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_user_likes_status(request, blog_id):
    """API endpoint to get which posts/comments the user has liked"""
    if not request.user.is_authenticated:
        return JsonResponse({'post_likes': [], 'comment_likes': []})
    
    try:
        # Get blog post likes
        post_likes = BlogPostLike.objects.filter(
            user=request.user,
            blog_id=blog_id
        ).values_list('blog_id', flat=True)
        
        # Get comment likes for this blog post
        comment_likes = BlogCommentLike.objects.filter(
            user=request.user,
            comment__blog_id=blog_id
        ).values_list('comment_id', flat=True)
        
        return JsonResponse({
            'success': True,
            'post_likes': list(post_likes),
            'comment_likes': list(comment_likes)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def vlog_post_like(request, pk):
    """Like or unlike a vlog post"""
    try:
        vlog = get_object_or_404(VideoVlog, pk=pk)
        
        # Check if user already liked this vlog
        like, created = VideoVlogLike.objects.get_or_create(
            videovlog=vlog,
            user=request.user
        )
        
        if not created:
            # Unlike if already liked
            like.delete()
            liked = False
        else:
            liked = True
            
            # Create notification for vlog author (if not self)
            if vlog.uploaded_by != request.user:
                Notification.objects.create(
                    user=vlog.uploaded_by,
                    title='New Like on Your Vlog',
                    message=f'{request.user.get_full_name()} liked your vlog "{vlog.title}"',
                    notification_type='info',
                    created_by=request.user
                )
        
        # Get updated like count
        like_count = vlog.likes.count()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='like',
            ip_address=get_client_ip(request),
            details={
                'vlog_id': vlog.id,
                'title': vlog.title,
                'action': 'liked' if liked else 'unliked'
            }
        )
        
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': like_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def vlog_comment_like(request, pk):
    """Like or unlike a vlog comment"""
    try:
        comment = get_object_or_404(VideoVlogComment, pk=pk)
        
        # Check if user already liked this comment
        like, created = VideoVlogCommentLike.objects.get_or_create(
            comment=comment,
            user=request.user
        )
        
        if not created:
            # Unlike if already liked
            like.delete()
            liked = False
        else:
            liked = True
            
            # Create notification for comment author (if not self)
            if comment.user != request.user:
                Notification.objects.create(
                    user=comment.user,
                    title='New Like on Your Comment',
                    message=f'{request.user.get_full_name()} liked your comment on "{comment.videovlog.title}"',
                    notification_type='info',
                    created_by=request.user
                )
        
        # Get updated like count
        like_count = comment.likes.count()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='like',
            ip_address=get_client_ip(request),
            details={
                'comment_id': comment.id,
                'vlog_id': comment.videovlog.id,
                'action': 'liked' if liked else 'unliked'
            }
        )
        
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': like_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def vlog_save(request, pk):
    """Save or unsave a vlog for later viewing"""
    try:
        # Using a generic save model or could use a SavedVlog model if available
        # For now, this will return a simple success response since there's no specific save model
        # This could be extended to save vlogs to user's saved list
        
        vlog = get_object_or_404(VideoVlog, pk=pk)
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='save',
            ip_address=get_client_ip(request),
            details={
                'vlog_id': vlog.id,
                'title': vlog.title,
                'action': 'saved'
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Vlog saved successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# core/views.py (add these error handler functions)

def handler404(request, exception):
    """404 error handler"""
    return render(request, 'core/404.html', status=404)

def handler500(request):
    """500 error handler"""
    return render(request, 'core/500.html', status=500)

def handler403(request, exception):
    """403 error handler"""
    return render(request, 'core/403.html', status=403)

def handler400(request, exception):
    """400 error handler"""
    return render(request, 'core/400.html', status=400)