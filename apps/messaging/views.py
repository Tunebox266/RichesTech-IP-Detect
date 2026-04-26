# messaging/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Message, MessageAttachment
from apps.accounts.models import User, ActivityLog
from .forms import MessageForm, BroadcastForm

@login_required
def inbox(request):
    """View inbox messages with filter support"""
    # Determine active tab
    active_tab = request.GET.get('tab', 'inbox')
    
    # Base query
    if active_tab == 'drafts':
        messages_list = Message.objects.filter(
            sender=request.user,
            is_draft=True
        ).select_related('recipient').order_by('-sent_at')
    elif active_tab == 'archived':
        messages_list = Message.objects.filter(
            recipient=request.user,
            is_archived=True
        ).select_related('sender').order_by('-sent_at')
    else:  # inbox (default)
        messages_list = Message.objects.filter(
            recipient=request.user,
            is_archived=False
        ).select_related('sender').order_by('-sent_at')
    
    # Apply status filter
    status_filter = request.GET.get('status', '')
    if status_filter == 'unread':
        messages_list = messages_list.filter(read_at__isnull=True)
    elif status_filter == 'read':
        messages_list = messages_list.filter(read_at__isnull=False)
    elif status_filter == 'starred':
        messages_list = messages_list.filter(is_starred=True)
    
    # Apply date filter
    date_filter = request.GET.get('date', '')
    from datetime import timedelta
    today = timezone.now().date()
    if date_filter == 'today':
        messages_list = messages_list.filter(sent_at__date=today)
    elif date_filter == 'week':
        week_ago = today - timedelta(days=7)
        messages_list = messages_list.filter(sent_at__date__gte=week_ago)
    elif date_filter == 'month':
        month_ago = today - timedelta(days=30)
        messages_list = messages_list.filter(sent_at__date__gte=month_ago)
    
    # Apply search filter
    search_query = request.GET.get('q', '')
    if search_query:
        messages_list = messages_list.filter(
            Q(subject__icontains=search_query) |
            Q(body__icontains=search_query) |
            Q(sender__first_name__icontains=search_query) |
            Q(sender__last_name__icontains=search_query) |
            Q(recipient__first_name__icontains=search_query) |
            Q(recipient__last_name__icontains=search_query)
        )
    
    # Mark all as read option
    if request.GET.get('mark_all_read'):
        messages_list.filter(read_at__isnull=True).update(read_at=timezone.now())
        return redirect('messaging:inbox')
    
    # Statistics
    unread_count = Message.objects.filter(
        recipient=request.user,
        read_at__isnull=True,
        is_archived=False
    ).count()
    
    paginator = Paginator(messages_list, 20)
    page = request.GET.get('page')
    messages_page = paginator.get_page(page)
    
    context = {
        'messages': messages_page,
        'unread_count': unread_count,
        'active_tab': active_tab,
    }
    return render(request, 'messaging/inbox.html', context)

@login_required
def sent_messages(request):
    """View sent messages"""
    messages_list = Message.objects.filter(
        sender=request.user
    ).select_related('recipient').order_by('-sent_at')
    
    paginator = Paginator(messages_list, 20)
    page = request.GET.get('page')
    messages_page = paginator.get_page(page)
    
    context = {
        'messages': messages_page,
        'is_sent': True,
    }
    return render(request, 'messaging/sent.html', context)

@login_required
def compose_message(request):
    """Compose new message"""
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.save()
            
            # Handle attachments
            files = request.FILES.getlist('attachments')
            for f in files:
                MessageAttachment.objects.create(
                    message=message,
                    file=f,
                    filename=f.name
                )
            
            messages.success(request, 'Message sent successfully!')
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action_type='message',
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'recipient': message.recipient.username if message.recipient else 'broadcast'}
            )
            
            return redirect('messaging:sent')
    else:
        form = MessageForm(sender=request.user)
        
        # In your compose view
    recent_recipients = Message.objects.filter(
    sender=request.user
    ).values_list('recipient', flat=True).distinct()[:5]
    
    
    
    # Get recent contacts for quick compose
    recent_contacts = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).values_list('sender', 'recipient').distinct()[:10]
    
    contact_ids = set()
    for s, r in recent_contacts:
        if s != request.user.id:
            contact_ids.add(s)
        if r != request.user.id:
            contact_ids.add(r)
    
    contacts = User.objects.filter(id__in=contact_ids)[:10]
    
    context = {
        'form': form,
        'contacts': contacts,
        'action': 'Compose',
    }
    return render(request, 'messaging/compose.html', context)

@login_required
def compose_to_user(request, recipient_id):
    """Compose message to specific user"""
    recipient = get_object_or_404(User, pk=recipient_id)
    
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES, sender=request.user)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.recipient = recipient
            message.save()
            
            # Handle attachments
            files = request.FILES.getlist('attachments')
            for f in files:
                MessageAttachment.objects.create(
                    message=message,
                    file=f,
                    filename=f.name
                )
            
            messages.success(request, f'Message sent to {recipient.get_full_name()}!')
            return redirect('messaging:sent')
    else:
        form = MessageForm(sender=request.user, initial={'recipient': recipient})
     
    context = {
        'form': form,
        'recipient': recipient,
        'action': f'Compose to {recipient.get_full_name()}',
    }
    return render(request, 'messaging/compose.html', context)

@login_required
def reply_message(request, pk):
    """Reply to a message"""
    original = get_object_or_404(Message, pk=pk)
    
    # Check if user can reply (must be recipient or sender)
    if request.user not in [original.sender, original.recipient]:
        messages.error(request, 'Access denied.')
        return redirect('messaging:inbox')
    
    # Determine recipient (the other party)
    recipient = original.sender if request.user == original.recipient else original.recipient
    
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.recipient = recipient
            message.parent_message = original
            message.save()
            
            # Handle attachments
            files = request.FILES.getlist('attachments')
            for f in files:
                MessageAttachment.objects.create(
                    message=message,
                    file=f,
                    filename=f.name
                )
            
            messages.success(request, 'Reply sent successfully!')
            return redirect('messaging:view_message', pk=original.pk)
    else:
        form = MessageForm(
            user=request.user, 
            initial={
                'recipient': recipient,
                'subject': f"Re: {original.subject}"
            }
        )
    
    context = {
        'form': form,
        'original': original,
        'recipient': recipient,
        'action': 'Reply',
    }
    return render(request, 'messaging/compose.html', context)

@login_required
def view_message(request, pk):
    """View a single message"""
    message = get_object_or_404(Message, pk=pk)
    
    # Check if user can view (must be sender or recipient)
    if request.user not in [message.sender, message.recipient]:
        messages.error(request, 'Access denied.')
        return redirect('messaging:inbox')
    
    # Mark as read if recipient
    if request.user == message.recipient and not message.read_at:
        message.read_at = timezone.now()
        message.save()
    
    # Get thread (all messages in conversation)
    thread = []
    if message.parent_message:
        # Traverse up to root
        current = message
        while current.parent_message:
            current = current.parent_message
            thread.insert(0, current)
        
        # Add all replies
        thread.append(message)
        thread.extend(Message.objects.filter(parent_message=message).order_by('sent_at'))
    else:
        thread = [message]
        thread.extend(Message.objects.filter(parent_message=message).order_by('sent_at'))
    
    context = {
        'message': message,
        'thread': thread,
        'can_reply': request.user != message.sender,  # Can reply if not sender
    }
    return render(request, 'messaging/view_message.html', context)

@login_required
def delete_message(request, pk):
    """Delete a message"""
    message = get_object_or_404(Message, pk=pk)
    
    # Check if user can delete (must be sender or recipient)
    if request.user not in [message.sender, message.recipient]:
        messages.error(request, 'Access denied.')
        return redirect('messaging:inbox')
    
    if request.method == 'POST':
        message.delete()
        messages.success(request, 'Message deleted successfully!')
        return redirect('messaging:inbox')
    
    return render(request, 'messaging/delete_confirm.html', {'message': message})

@login_required
def broadcast_message(request):
    """Send broadcast message (staff/executive only)"""
    if request.user.user_type not in ['admin', 'staff', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('messaging:inbox')
    
    if request.method == 'POST':
        form = BroadcastForm(request.POST, request.FILES)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            body = form.cleaned_data['body']
            groups = form.cleaned_data['groups']
            
            # Create broadcast message
            message = Message.objects.create(
                sender=request.user,
                subject=subject,
                body=body,
                is_broadcast=True,
                broadcast_groups=groups
            )
            
            # Handle attachments
            files = request.FILES.getlist('attachments')
            for f in files:
                MessageAttachment.objects.create(
                    message=message,
                    file=f,
                    filename=f.name
                )
            
            # Send to all users in groups
            recipients = User.objects.filter(
                user_type__in=groups
            ).exclude(id=request.user.id)
            
            # Create individual messages for each recipient
            for recipient in recipients:
                Message.objects.create(
                    sender=request.user,
                    recipient=recipient,
                    subject=subject,
                    body=body,
                    parent_message=message,
                    is_broadcast=True
                )
            
            messages.success(request, f'Broadcast sent to {recipients.count()} users!')
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action_type='broadcast',
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'groups': groups, 'recipient_count': recipients.count()}
            )
            
            return redirect('messaging:sent')
    else:
        form = BroadcastForm()
    
    # Get counts for each group
    group_counts = {
        'students': User.objects.filter(user_type='student').count(),
        'executives': User.objects.filter(user_type='executive').count(),
        'staff': User.objects.filter(user_type='staff').count(),
    }
    
    context = {
        'form': form,
        'group_counts': group_counts,
    }
    return render(request, 'messaging/broadcast.html', context)

@login_required
def unread_count(request):
    """AJAX endpoint for unread count"""
    count = Message.objects.filter(
        recipient=request.user,
        read_at__isnull=True
    ).count()
    
    return JsonResponse({'count': count})

@login_required
@require_POST
def mark_read(request, pk):
    """AJAX endpoint to mark message as read"""
    message = get_object_or_404(Message, pk=pk, recipient=request.user)
    
    if not message.read_at:
        message.read_at = timezone.now()
        message.save()
    
    return JsonResponse({'success': True})


# apps/messaging/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
import json
import csv

from .models import Message, MessageAttachment, Conversation, ConversationMessage
from apps.accounts.models import User, ActivityLog


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def inbox(request):
    """Display inbox messages"""
    # Get messages where user is recipient
    messages_list = Message.objects.filter(
        recipient=request.user
    ).select_related('sender').order_by('-sent_at')
    
    # Get unread count
    unread_count = messages_list.filter(read_at__isnull=True).count()
    
    # Apply filters
    status = request.GET.get('status')
    if status == 'unread':
        messages_list = messages_list.filter(read_at__isnull=True)
    elif status == 'read':
        messages_list = messages_list.filter(read_at__isnull=False)
    elif status == 'starred':
        messages_list = messages_list.filter(is_starred=True)
    
    # Search
    search_query = request.GET.get('q')
    if search_query:
        messages_list = messages_list.filter(
            Q(subject__icontains=search_query) |
            Q(body__icontains=search_query) |
            Q(sender__first_name__icontains=search_query) |
            Q(sender__last_name__icontains=search_query)
        )
    
    # Date filter
    date_filter = request.GET.get('date')
    if date_filter == 'today':
        messages_list = messages_list.filter(sent_at__date=timezone.now().date())
    elif date_filter == 'week':
        week_ago = timezone.now() - timezone.timedelta(days=7)
        messages_list = messages_list.filter(sent_at__gte=week_ago)
    elif date_filter == 'month':
        month_ago = timezone.now() - timezone.timedelta(days=30)
        messages_list = messages_list.filter(sent_at__gte=month_ago)
    
    # Pagination
    paginator = Paginator(messages_list, 20)
    page = request.GET.get('page')
    messages_page = paginator.get_page(page)
    
    context = {
        'messages': messages_page,
        'unread_count': unread_count,
        'active_tab': 'inbox',
        'users': User.objects.filter(is_active=True)[:10],  # For quick compose
    }
    
    return render(request, 'messaging/inbox.html', context)


@login_required
def sent_messages(request):
    """Display sent messages"""
    messages_list = Message.objects.filter(
        sender=request.user
    ).select_related('recipient').order_by('-sent_at')
    
    # Search
    search_query = request.GET.get('q')
    if search_query:
        messages_list = messages_list.filter(
            Q(subject__icontains=search_query) |
            Q(body__icontains=search_query) |
            Q(recipient__first_name__icontains=search_query) |
            Q(recipient__last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(messages_list, 20)
    page = request.GET.get('page')
    messages_page = paginator.get_page(page)
    
    context = {
        'messages': messages_page,
        'active_tab': 'sent',
    }
    
    return render(request, 'messaging/sent.html', context)


@login_required
def message_detail(request, pk):
    """Display a single message"""
    message = get_object_or_404(
        Message.objects.select_related('sender', 'recipient').prefetch_related('attachments'),
        pk=pk
    )
    
    # Check if user is either sender or recipient
    if request.user != message.sender and request.user != message.recipient:
        messages.error(request, 'You do not have permission to view this message.')
        return redirect('messaging:inbox')
    
    # Mark as read if recipient and not read
    if request.user == message.recipient and not message.read_at:
        message.read_at = timezone.now()
        message.save()
    
    context = {
        'message': message,
    }
    
    return render(request, 'messaging/message_detail.html', context)


@login_required
def compose(request):
    """Compose a new message"""
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient')
        subject = request.POST.get('subject')
        body = request.POST.get('body')
        is_urgent = request.POST.get('is_urgent') == 'on'
        
        try:
            recipient = User.objects.get(id=recipient_id)
            
            # Create message
            message = Message.objects.create(
                sender=request.user,
                recipient=recipient,
                subject=subject,
                body=body,
                is_urgent=is_urgent
            )
            
            # Handle attachments
            attachments = request.FILES.getlist('attachments')
            for file in attachments:
                MessageAttachment.objects.create(
                    message=message,
                    file=file,
                    filename=file.name,
                    file_size=file.size,
                    content_type=file.content_type
                )
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action_type='message_sent',
                ip_address=get_client_ip(request),
                details={'recipient': recipient.email, 'subject': subject}
            )
            
            messages.success(request, 'Message sent successfully!')
            return redirect('messaging:sent')
            
        except User.DoesNotExist:
            messages.error(request, 'Recipient not found.')
        except Exception as e:
            messages.error(request, f'Error sending message: {str(e)}')
    
    # Get users for recipient dropdown (filter based on permissions)
    if request.user.user_type == 'admin':
        users = User.objects.filter(is_active=True).exclude(id=request.user.id)
    elif request.user.user_type == 'staff':
        users = User.objects.filter(
            Q(user_type__in=['student', 'executive']) | Q(id=request.user.id),
            is_active=True
        ).exclude(id=request.user.id)
    else:
        users = User.objects.filter(
            Q(user_type__in=['executive', 'staff']) | Q(id=request.user.id),
            is_active=True
        ).exclude(id=request.user.id)
    
    context = {
        'users': users,
    }
    
    return render(request, 'messaging/compose.html', context)


@login_required
def save_draft(request):
    """Save a message draft (AJAX endpoint)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        # For now, just acknowledge the draft save request
        # In a production system, you would store this in a cache or Draft model
        subject = request.POST.get('subject', '')
        body = request.POST.get('body', '')
        
        # You could implement draft storage here:
        # - Store in cache for temporary persistence
        # - Store in database Draft model
        # - Store in browser localStorage on client-side (recommended)
        
        return JsonResponse({
            'success': True,
            'message': 'Draft saved successfully',
            'draft': {
                'subject': subject[:50],
                'body_preview': body[:100],
                'saved_at': timezone.now().isoformat()
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def drafts(request):
    """Redirect to inbox with drafts filter"""
    return redirect(f"{reverse('messaging:inbox')}?tab=drafts")


@login_required
def archived(request):
    """Redirect to inbox with archived filter"""
    return redirect(f"{reverse('messaging:inbox')}?tab=archived")


@login_required
def reply_message(request, pk):
    """Reply to a message"""
    original = get_object_or_404(Message, pk=pk)
    
    # Check if user can reply
    if request.user != original.recipient and request.user != original.sender:
        messages.error(request, 'You cannot reply to this message.')
        return redirect('messaging:inbox')
    
    if request.method == 'POST':
        body = request.POST.get('body')
        
        # Determine recipient (reply to sender)
        recipient = original.sender if request.user == original.recipient else original.recipient
        
        # Create reply
        reply = Message.objects.create(
            sender=request.user,
            recipient=recipient,
            subject=f"Re: {original.subject}",
            body=body,
            parent_message=original
        )
        
        # Handle attachments
        attachments = request.FILES.getlist('attachments')
        for file in attachments:
            MessageAttachment.objects.create(
                message=reply,
                file=file,
                filename=file.name
            )
        
        # Mark original as replied
        original.is_replied = True
        original.save()
        
        messages.success(request, 'Reply sent successfully!')
        return redirect('messaging:message_detail', pk=original.id)
    
    context = {
        'original': original,
    }
    
    return render(request, 'messaging/reply.html', context)


@login_required
@require_POST
def toggle_star(request, pk):
    """Toggle star status of a message"""
    try:
        message = get_object_or_404(Message, pk=pk)
        
        # Check if user owns this message (sender or recipient)
        if request.user != message.sender and request.user != message.recipient:
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        message.is_starred = not message.is_starred
        message.save()
        
        return JsonResponse({
            'success': True,
            'is_starred': message.is_starred
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def delete_message(request, pk):
    """Delete a message"""
    try:
        message = get_object_or_404(Message, pk=pk)
        
        # Check if user owns this message (sender or recipient)
        if request.user != message.sender and request.user != message.recipient:
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        # Soft delete or hard delete? Using soft delete with is_deleted flag
        # For now, hard delete
        message.delete()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='message_deleted',
            ip_address=get_client_ip(request),
            details={'message_id': pk}
        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def bulk_mark_read(request):
    """Mark multiple messages as read"""
    try:
        data = json.loads(request.body)
        message_ids = data.get('message_ids', [])
        
        if not message_ids:
            return JsonResponse({
                'success': False,
                'error': 'No messages selected'
            }, status=400)
        
        # Update only messages where user is recipient
        updated = Message.objects.filter(
            id__in=message_ids,
            recipient=request.user,
            read_at__isnull=True
        ).update(read_at=timezone.now())
        
        return JsonResponse({
            'success': True,
            'updated': updated
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def bulk_star(request):
    """Star/unstar multiple messages"""
    try:
        data = json.loads(request.body)
        message_ids = data.get('message_ids', [])
        
        if not message_ids:
            return JsonResponse({
                'success': False,
                'error': 'No messages selected'
            }, status=400)
        
        # Toggle star for selected messages
        messages = Message.objects.filter(
            id__in=message_ids
        ).filter(
            Q(sender=request.user) | Q(recipient=request.user)
        )
        
        # Check current state of first message to determine action
        # This is simplistic - in production you might want to track which ones to star/unstar
        first = messages.first()
        if first:
            new_starred = not first.is_starred
            messages.update(is_starred=new_starred)
        
        return JsonResponse({
            'success': True,
            'is_starred': first.is_starred if first else False
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def bulk_delete(request):
    """Delete multiple messages"""
    try:
        data = json.loads(request.body)
        message_ids = data.get('message_ids', [])
        
        if not message_ids:
            return JsonResponse({
                'success': False,
                'error': 'No messages selected'
            }, status=400)
        
        # Delete only messages where user is sender or recipient
        messages = Message.objects.filter(
            id__in=message_ids
        ).filter(
            Q(sender=request.user) | Q(recipient=request.user)
        )
        
        count = messages.count()
        messages.delete()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='bulk_delete',
            ip_address=get_client_ip(request),
            details={'message_count': count}
        )
        
        return JsonResponse({
            'success': True,
            'deleted': count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def get_unread_count(request):
    """Get unread messages count (AJAX)"""
    try:
        count = Message.objects.filter(
            recipient=request.user,
            read_at__isnull=True
        ).count()
        
        return JsonResponse({
            'success': True,
            'count': count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def search_users(request):
    """Search users for messaging (AJAX)"""
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Search users
    users = User.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query) |
        Q(student_id__icontains=query) |
        Q(staff_id__icontains=query)
    ).filter(
        is_active=True
    ).exclude(
        id=request.user.id
    )[:10]
    
    results = []
    for user in users:
        results.append({
            'id': user.id,
            'name': user.get_full_name(),
            'email': user.email,
            'user_type': user.user_type,
            'avatar': user.profile_image.url if user.profile_image else None,
            'user_type_display': user.get_user_type_display(),
        })
    
    return JsonResponse({'results': results})








# apps/messaging/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
import json
from datetime import timedelta

from .models import Message, MessageAttachment, Notification, NotificationPreference
from apps.accounts.models import User, ActivityLog


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ===== NOTIFICATION VIEWS =====

@login_required
def notification_list(request):
    """List all notifications for the current user"""
    notifications = Notification.objects.filter(user=request.user)
    
    # Filter by read status
    status = request.GET.get('status')
    if status == 'read':
        notifications = notifications.filter(is_read=True)
    elif status == 'unread':
        notifications = notifications.filter(is_read=False)
    
    # Filter by type
    notif_type = request.GET.get('type')
    if notif_type:
        notifications = notifications.filter(notification_type=notif_type)
    
    # Date filter
    date_filter = request.GET.get('date')
    if date_filter == 'today':
        notifications = notifications.filter(created_at__date=timezone.now().date())
    elif date_filter == 'week':
        week_ago = timezone.now() - timedelta(days=7)
        notifications = notifications.filter(created_at__gte=week_ago)
    elif date_filter == 'month':
        month_ago = timezone.now() - timedelta(days=30)
        notifications = notifications.filter(created_at__gte=month_ago)
    
    # Search
    search = request.GET.get('search')
    if search:
        notifications = notifications.filter(
            Q(title__icontains=search) |
            Q(content__icontains=search)
        )
    
    # Order by most recent
    notifications = notifications.order_by('-created_at')
    
    # Get counts for stats
    total_count = notifications.count()
    unread_count = notifications.filter(is_read=False).count()
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page = request.GET.get('page')
    notifications_page = paginator.get_page(page)
    
    context = {
        'notifications': notifications_page,
        'total_count': total_count,
        'unread_count': unread_count,
        'notification_types': Notification.NOTIFICATION_TYPES,
        'filter_status': status,
        'filter_type': notif_type,
    }
    
    return render(request, 'messaging/notification_list.html', context)


@login_required
def notification_unread_count(request):
    """Get unread notifications count (AJAX endpoint)"""
    try:
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return JsonResponse({
            'success': True,
            'count': count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def notification_mark_read(request, pk):
    """Mark a notification as read"""
    try:
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.mark_as_read()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='notification_read',
            ip_address=get_client_ip(request),
            details={'notification_id': pk, 'title': notification.title}
        )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        messages.success(request, 'Notification marked as read.')
        return redirect('messaging:notification_list')
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        messages.error(request, f'Error: {str(e)}')
        return redirect('messaging:notification_list')


@login_required
@require_POST
def notification_mark_unread(request, pk):
    """Mark a notification as unread"""
    try:
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.mark_as_unread()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        messages.success(request, 'Notification marked as unread.')
        return redirect('messaging:notification_list')
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        messages.error(request, f'Error: {str(e)}')
        return redirect('messaging:notification_list')


@login_required
@require_POST
def notification_delete(request, pk):
    """Delete a notification"""
    try:
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        messages.success(request, 'Notification deleted.')
        return redirect('messaging:notification_list')
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        messages.error(request, f'Error: {str(e)}')
        return redirect('messaging:notification_list')


@login_required
@require_POST
def notification_mark_all_read(request):
    """Mark all notifications as read for the current user"""
    try:
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='notification_mark_all_read',
            ip_address=get_client_ip(request),
            details={'count': count}
        )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'count': count,
                'message': f'{count} notifications marked as read.'
            })
        
        messages.success(request, f'{count} notifications marked as read.')
        return redirect('messaging:notification_list')
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        messages.error(request, f'Error: {str(e)}')
        return redirect('messaging:notification_list')


@login_required
@require_POST
def notification_delete_all_read(request):
    """Delete all read notifications for the current user"""
    try:
        count = Notification.objects.filter(
            user=request.user,
            is_read=True
        ).delete()[0]
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'count': count,
                'message': f'{count} read notifications deleted.'
            })
        
        messages.success(request, f'{count} read notifications deleted.')
        return redirect('messaging:notification_list')
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        messages.error(request, f'Error: {str(e)}')
        return redirect('messaging:notification_list')


# ===== NOTIFICATION PREFERENCES VIEWS =====

@login_required
def notification_preferences(request):
    """View notification preferences"""
    try:
        preferences = NotificationPreference.objects.get(user=request.user)
    except NotificationPreference.DoesNotExist:
        preferences = NotificationPreference.objects.create(user=request.user)
    
    return render(request, 'messaging/notification_preferences.html', {
        'preferences': preferences
    })


@login_required
@require_POST
def notification_preferences_update(request):
    """Update notification preferences"""
    try:
        preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
        
        # Email preferences
        preferences.email_messages = request.POST.get('email_messages') == 'on'
        preferences.email_broadcasts = request.POST.get('email_broadcasts') == 'on'
        preferences.email_events = request.POST.get('email_events') == 'on'
        preferences.email_payments = request.POST.get('email_payments') == 'on'
        
        # In-app preferences
        preferences.in_app_messages = request.POST.get('in_app_messages') == 'on'
        preferences.in_app_broadcasts = request.POST.get('in_app_broadcasts') == 'on'
        preferences.in_app_events = request.POST.get('in_app_events') == 'on'
        preferences.in_app_payments = request.POST.get('in_app_payments') == 'on'
        
        # Digest settings
        preferences.email_digest = request.POST.get('email_digest', 'never')
        
        # Quiet hours
        quiet_start = request.POST.get('quiet_hours_start')
        quiet_end = request.POST.get('quiet_hours_end')
        
        preferences.quiet_hours_start = quiet_start if quiet_start else None
        preferences.quiet_hours_end = quiet_end if quiet_end else None
        
        preferences.save()
        
        messages.success(request, 'Notification preferences updated successfully.')
        
    except Exception as e:
        messages.error(request, f'Error updating preferences: {str(e)}')
    
    return redirect('messaging:notification_preferences')


# ===== API ENDPOINTS FOR NOTIFICATIONS =====

@login_required
def api_notifications(request):
    """API endpoint for notifications (for dropdown)"""
    try:
        # Get recent notifications
        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:10]
        
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        data = []
        for notif in notifications:
            data.append({
                'id': notif.id,
                'title': notif.title,
                'content': notif.content[:100],
                'type': notif.notification_type,
                'is_read': notif.is_read,
                'created_at': notif.created_at.isoformat(),
                'time_ago': timesince(notif.created_at),
            })
        
        return JsonResponse({
            'success': True,
            'unread_count': unread_count,
            'notifications': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def api_notification_mark_read(request, pk):
    """API endpoint to mark notification as read"""
    try:
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.mark_as_read()
        
        # Get updated unread count
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return JsonResponse({
            'success': True,
            'unread_count': unread_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def api_notification_mark_all_read(request):
    """API endpoint to mark all notifications as read"""
    try:
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        return JsonResponse({
            'success': True,
            'count': count,
            'message': f'{count} notifications marked as read.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# Helper function for timesince
def timesince(dt, default="just now"):
    """
    Returns string representing "time since" e.g.
    3 days ago, 5 hours ago etc.
    """
    from django.utils.timesince import timesince as django_timesince
    from django.utils.timezone import now
    
    if dt:
        return django_timesince(dt, now()).split(',')[0] + ' ago'
    return default


# apps/messaging/views.py

from django.shortcuts import get_object_or_404
from django.http import JsonResponse

@login_required
def notification_detail(request, pk):
    """Get notification details as JSON (AJAX endpoint)"""
    try:
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        
        # Build response data
        data = {
            'success': True,
            'notification': {
                'id': notification.id,
                'title': notification.title,
                'content': notification.content,
                'notification_type': notification.notification_type,
                'type_display': notification.get_notification_type_display(),
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat(),
                'related_message': None,
                'related_broadcast': None,
            }
        }
        
        # Add related message info if exists
        if notification.related_message:
            data['notification']['related_message'] = {
                'id': notification.related_message.id,
                'subject': notification.related_message.subject,
                'sender_name': notification.related_message.sender.get_full_name(),
            }
        
        # Add related broadcast info if exists
        if notification.related_broadcast:
            data['notification']['related_broadcast'] = {
                'id': notification.related_broadcast.id,
                'title': notification.related_broadcast.title,
                'created_by_name': notification.related_broadcast.created_by.get_full_name(),
            }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


