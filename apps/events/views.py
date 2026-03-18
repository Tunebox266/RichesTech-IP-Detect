# events/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.views.decorators.http import require_POST
import csv

from .models import Event, EventAttendee, AttendanceSession, AttendanceRecord, AttendanceCode, EventFeedback
from apps.accounts.models import User, ActivityLog
from .forms import (
    EventForm, AttendanceSessionForm,
    AttendanceCodeForm, EventFeedbackForm
)


def event_list(request):
    """List all events"""
    events = Event.objects.filter(is_active=True)
    
    # Filters
    event_type = request.GET.get('type')
    if event_type:
        events = events.filter(event_type=event_type)
    
    search = request.GET.get('search')
    if search:
        events = events.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Upcoming vs Past
    filter_type = request.GET.get('filter', 'upcoming')
    now = timezone.now()
    
    if filter_type == 'upcoming':
        events = events.filter(start_date__gte=now)
    elif filter_type == 'past':
        events = events.filter(end_date__lt=now)
    
    paginator = Paginator(events, 12)
    page = request.GET.get('page')
    events = paginator.get_page(page)
    
    context = {
        'events': events,
        'event_types': Event.EVENT_TYPES,
        'filter_type': filter_type,
    }
    return render(request, 'events/event_list.html', context)


def event_detail(request, pk):
    """View event details"""
    event = get_object_or_404(Event, pk=pk)
    
    # Check if user is registered
    is_registered = False
    has_attended = False
    
    if request.user.is_authenticated:
        try:
            attendee = EventAttendee.objects.get(event=event, user=request.user)
            is_registered = True
            has_attended = attendee.attended
        except EventAttendee.DoesNotExist:
            pass
    
    # Get attendance sessions
    sessions = event.attendance_sessions.filter(is_active=True)
    
    # Get user's attendance records
    user_attendance = []
    if request.user.is_authenticated:
        user_attendance = AttendanceRecord.objects.filter(
            session__event=event,
            user=request.user
        ).values_list('session_id', flat=True)
    
    context = {
        'event': event,
        'is_registered': is_registered,
        'has_attended': has_attended,
        'sessions': sessions,
        'user_attendance': user_attendance,
        'attendee_count': event.get_attendee_count(),
    }
    return render(request, 'events/event_detail.html', context)


@login_required
def event_register(request, pk):
    """Register for an event"""
    event = get_object_or_404(Event, pk=pk)
    
    # Check if event is in the future
    if event.start_date < timezone.now():
        messages.error(request, 'This event has already started or ended.')
        return redirect('events:event_detail', pk=pk)
    
    # Check if already registered
    if EventAttendee.objects.filter(event=event, user=request.user).exists():
        messages.info(request, 'You are already registered for this event.')
        return redirect('events:event_detail', pk=pk)
    
    # Check if event is full
    if event.is_full():
        messages.error(request, 'This event is already full.')
        return redirect('events:event_detail', pk=pk)
    
    # Register user
    attendee = EventAttendee.objects.create(
        event=event,
        user=request.user
    )
    
    messages.success(request, f'Successfully registered for {event.title}!')
    
    # Log activity
    ActivityLog.objects.create(
        user=request.user,
        action_type='event_registration',
        ip_address=get_client_ip(request),
        details={'event': event.title}
    )
    
    return redirect('events:event_detail', pk=pk)


@login_required
def event_unregister(request, pk):
    """Unregister from an event"""
    event = get_object_or_404(Event, pk=pk)
    
    attendee = get_object_or_404(EventAttendee, event=event, user=request.user)
    
    # Don't allow unregistration if already attended
    if attendee.attended:
        messages.error(request, 'You have already attended this event and cannot unregister.')
        return redirect('events:event_detail', pk=pk)
    
    attendee.delete()
    
    messages.success(request, f'Successfully unregistered from {event.title}.')
    
    return redirect('events:event_detail', pk=pk)


@login_required
def session_check_in(request, session_id):
    """Check in to a session via QR code or code"""
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    # Check if session is active
    if not session.is_active_now():
        return JsonResponse({
            'success': False,
            'error': 'This session is not currently active.'
        })
    
    # Check if already checked in
    if AttendanceRecord.objects.filter(session=session, user=request.user).exists():
        return JsonResponse({
            'success': False,
            'error': 'You have already checked in to this session.'
        })
    
    # Create attendance record
    record = AttendanceRecord.objects.create(
        session=session,
        user=request.user,
        check_in_method='qr_code',
        ip_address=get_client_ip(request),
        device_info=request.META.get('HTTP_USER_AGENT', '')[:200]
    )
    
    # Also mark event attendance if this is the first session
    try:
        attendee = EventAttendee.objects.get(event=session.event, user=request.user)
        if not attendee.attended:
            attendee.attended = True
            attendee.checked_in_at = timezone.now()
            attendee.check_in_method = 'qr_code'
            attendee.save()
    except EventAttendee.DoesNotExist:
        # Create attendee record if it doesn't exist
        EventAttendee.objects.create(
            event=session.event,
            user=request.user,
            attended=True,
            checked_in_at=timezone.now(),
            check_in_method='qr_code'
        )
    
    return JsonResponse({
        'success': True,
        'message': 'Check-in successful!',
        'check_in_time': record.checked_in_at.strftime('%H:%M:%S')
    })


@login_required
def session_check_in_code(request):
    """Check in using a session code"""
    if request.method == 'POST':
        code = request.POST.get('code')
        
        try:
            session = AttendanceSession.objects.get(session_code=code)
            return redirect('events:session_check_in', session_id=session.id)
        except AttendanceSession.DoesNotExist:
            messages.error(request, 'Invalid session code.')
    
    return render(request, 'events/check_in_form.html')


@login_required
@staff_member_required
def event_create(request):
    """Create new event (staff/admin only)"""
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            
            messages.success(request, f'Event "{event.title}" created successfully!')
            return redirect('events:event_detail', pk=event.pk)
    else:
        form = EventForm()
    
    return render(request, 'events/event_form.html', {'form': form, 'action': 'Create'})


@login_required
@staff_member_required
def event_edit(request, pk):
    """Edit event (staff/admin only)"""
    event = get_object_or_404(Event, pk=pk)
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f'Event "{event.title}" updated successfully!')
            return redirect('events:event_detail', pk=event.pk)
    else:
        form = EventForm(instance=event)
    
    return render(request, 'events/event_form.html', {
        'form': form, 
        'action': 'Edit',
        'event': event
    })


@login_required
@staff_member_required
def event_delete(request, pk):
    """Delete event (admin only)"""
    event = get_object_or_404(Event, pk=pk)
    
    if request.user.user_type != 'admin':
        messages.error(request, 'Only administrators can delete events.')
        return redirect('events:event_detail', pk=event.pk)
    
    if request.method == 'POST':
        event.delete()
        messages.success(request, f'Event "{event.title}" deleted successfully!')
        return redirect('events:event_list')
    
    return render(request, 'events/event_confirm_delete.html', {'event': event})


@login_required
@staff_member_required
def event_attendees(request, pk):
    """View and manage event attendees (staff/admin only)"""
    event = get_object_or_404(Event, pk=pk)
    
    attendees = event.attendees.select_related('user').order_by('-registered_at')
    
    # Filter by attendance status
    status = request.GET.get('status')
    if status == 'attended':
        attendees = attendees.filter(attended=True)
    elif status == 'registered':
        attendees = attendees.filter(attended=False)
    
    # Search
    search = request.GET.get('search')
    if search:
        attendees = attendees.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__student_id__icontains=search)
        )
    
    paginator = Paginator(attendees, 50)
    page = request.GET.get('page')
    attendees = paginator.get_page(page)
    
    # Get attendance sessions
    sessions = event.attendance_sessions.all()
    
    context = {
        'event': event,
        'attendees': attendees,
        'sessions': sessions,
        'total_registered': event.get_attendee_count(),
        'total_checked_in': event.get_checked_in_count(),
    }
    return render(request, 'events/event_attendees.html', context)


@login_required
@staff_member_required
def mark_attendance(request, attendee_id):
    """Manually mark attendance for an attendee"""
    attendee = get_object_or_404(EventAttendee, id=attendee_id)
    
    if request.method == 'POST':
        attendee.attended = True
        attendee.checked_in_at = timezone.now()
        attendee.check_in_method = 'manual'
        attendee.save()
        
        messages.success(request, f'Attendance marked for {attendee.user.get_full_name()}')
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='attendance_marked',
            ip_address=get_client_ip(request),
            details={'event': attendee.event.title, 'user': attendee.user.get_full_name()}
        )
    
    return redirect('events:event_attendees', pk=attendee.event.pk)


@login_required
@staff_member_required
def session_create(request, event_id):
    """Create attendance session for event"""
    event = get_object_or_404(Event, pk=event_id)
    
    if request.method == 'POST':
        form = AttendanceSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.event = event
            session.save()
            
            messages.success(request, f'Session "{session.name}" created successfully!')
            return redirect('events:event_attendees', pk=event.pk)
    else:
        form = AttendanceSessionForm()
    
    return render(request, 'events/session_form.html', {
        'form': form,
        'event': event,
        'action': 'Create'
    })

# apps/events/views.py

@login_required
def session_detail(request, pk):
    """View session details and attendance"""
    try:
        # Try to get the session with related event data
        session = get_object_or_404(AttendanceSession.objects.select_related('event'), pk=pk)
        
        # Log success for debugging
        print(f"Session found: {session.id} - {session.name} for event: {session.event.title}")
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error accessing session {pk}: {str(e)}")
        messages.error(request, f'Session not found or error: {str(e)}')
        return redirect('events:event_list')
    
    # Get attendance records with user data
    attendance = session.attendance_records.select_related('user').order_by('-checked_in_at')
    
    # Get all registered attendees for the event
    registered_attendees = EventAttendee.objects.filter(
        event=session.event
    ).select_related('user')
    
    # Mark who has checked in
    checked_in_ids = attendance.values_list('user_id', flat=True)
    not_checked_in = registered_attendees.exclude(user_id__in=checked_in_ids)
    
    # Calculate statistics
    total_registered = registered_attendees.count()
    checked_in_count = attendance.count()
    attendance_rate = (checked_in_count / total_registered * 100) if total_registered > 0 else 0
    
    context = {
        'session': session,
        'attendance': attendance,
        'not_checked_in': not_checked_in,
        'checked_in_count': checked_in_count,
        'total_registered': total_registered,
        'attendance_rate': attendance_rate,
        'now': timezone.now(),
    }
    return render(request, 'events/session_detail.html', context)
    
@login_required
def student_events(request, student_id):
    """List events attended by a specific student"""
    student = get_object_or_404(User, pk=student_id, user_type='student')
    
    events_attended = EventAttendee.objects.filter(
        user=student,
        attended=True
    ).select_related('event').order_by('-event__start_date')
    
    context = {
        'profile_user': student,
        'events_attended': events_attended,
    }
    return render(request, 'events/student_events.html', context)
  
@login_required  
@csrf_exempt
def bulk_mark_attendance(request, event_id):
    """Mark attendance for multiple attendees via POST request"""
    if request.method == 'POST':
        try:
            event = Event.objects.get(pk=event_id)
            data = json.loads(request.body)
            attendee_ids = data.get('attendee_ids', [])

            # Filter valid users for this event
            attendees = User.objects.filter(id__in=attendee_ids)
            marked_count = 0

            for attendee in attendees:
                obj, created = EventAttendance.objects.update_or_create(
                    event=event,
                    attendee=attendee,
                    defaults={'status': 'present'}
                )
                marked_count += 1

            return JsonResponse({
                'success': True,
                'message': f'Attendance marked for {marked_count} attendee(s).'
            })

        except Event.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Event not found.'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})
    

@login_required
def export_attendees(request, event_id):
    """
    Export attendees of an event as CSV.
    Optional GET parameters: status, search
    """
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        return HttpResponse("Event not found.", status=404)

    status = request.GET.get('status', None)  # e.g., 'present' or 'absent'
    search_query = request.GET.get('search', '')

    # Filter attendees
    attendees = EventAttendance.objects.filter(event=event)

    if status:
        attendees = attendees.filter(status=status)
    if search_query:
        attendees = attendees.filter(attendee__first_name__icontains=search_query) | attendees.filter(attendee__last_name__icontains=search_query)

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendees_event_{event.id}.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Full Name', 'Email', 'Status'])

    for record in attendees.select_related('attendee'):
        writer.writerow([
            record.attendee.id,
            record.attendee.get_full_name(),
            record.attendee.email,
            record.status
        ])

    return response

@login_required
def my_events(request):
    """View events the user is registered for"""
    if request.user.user_type not in ['student', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    registrations = EventAttendee.objects.filter(
        user=request.user
    ).select_related('event').order_by('-event__start_date')
    
    # Separate upcoming and past events
    now = timezone.now()
    upcoming = registrations.filter(event__start_date__gte=now)
    past = registrations.filter(event__end_date__lt=now)
    
    # Get attendance records
    attendance_records = AttendanceRecord.objects.filter(
        user=request.user
    ).select_related('session')
    
    attended_sessions = {}
    for record in attendance_records:
        attended_sessions[record.session_id] = record
    
    context = {
        'upcoming_events': upcoming,
        'past_events': past,
        'attended_sessions': attended_sessions,
    }
    return render(request, 'events/my_events.html', context)


# apps/events/views.py

@login_required
@require_POST
def manual_checkin(request, session_id):
    """Manual check-in form submission"""
    session = get_object_or_404(AttendanceSession, id=session_id)
    student_id = request.POST.get('student_id')
    
    if not student_id:
        messages.error(request, 'Please enter a student ID')
        return redirect('events:session_detail', pk=session_id)
    
    try:
        student = User.objects.get(
            Q(student_id=student_id) | Q(username=student_id),
            user_type='student',
            is_active=True
        )
        
        # Check if registered for the event
        if not EventAttendee.objects.filter(event=session.event, user=student).exists():
            messages.error(request, f'{student.get_full_name()} is not registered for this event')
            return redirect('events:session_detail', pk=session_id)
        
        # Check if already checked in
        if AttendanceRecord.objects.filter(session=session, user=student).exists():
            messages.warning(request, f'{student.get_full_name()} already checked in')
            return redirect('events:session_detail', pk=session_id)
        
        # Create attendance record
        record = AttendanceRecord.objects.create(
            session=session,
            user=student,
            check_in_method='manual',
            ip_address=get_client_ip(request)
        )
        
        # Update event attendee
        attendee = EventAttendee.objects.get(event=session.event, user=student)
        attendee.attended = True
        attendee.checked_in_at = timezone.now()
        attendee.check_in_method = 'manual'
        attendee.save()
        
        messages.success(request, f'Successfully checked in {student.get_full_name()}')
        
    except User.DoesNotExist:
        messages.error(request, f'Student with ID {student_id} not found')
    
    return redirect('events:session_detail', pk=session_id)



def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# apps/events/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
import csv
import json
from datetime import timedelta

from .models import Event, EventAttendee, AttendanceSession, AttendanceRecord
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
def download_session_qr(request, session_id):
    """Download QR code for session"""
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    if not session.qr_code:
        session.generate_qr_code()
        session.save()
    
    response = FileResponse(session.qr_code)
    response['Content-Disposition'] = f'attachment; filename="session_{session.session_code}_qrcode.png"'
    return response


@login_required
def export_session_attendance(request, session_id):
    """Export attendance records for a session to CSV"""
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="session_{session.id}_attendance.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student ID', 'Name', 'Level', 'Program', 'Check-in Time', 'Method', 'IP Address'])
    
    records = AttendanceRecord.objects.filter(session=session).select_related('user').order_by('checked_in_at')
    
    for record in records:
        writer.writerow([
            record.user.student_id,
            record.user.get_full_name(),
            record.user.level,
            record.user.get_program_type_display(),
            record.checked_in_at.strftime('%Y-%m-%d %H:%M:%S') if record.checked_in_at else '',
            record.get_check_in_method_display(),
            record.ip_address or ''
        ])
    
    return response


@login_required
def print_attendance(request, session_id):
    """Print-friendly attendance list"""
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    # Get all registered attendees
    attendees = EventAttendee.objects.filter(
        event=session.event
    ).select_related('user').order_by('user__last_name', 'user__first_name')
    
    # Get checked in records
    checked_in = AttendanceRecord.objects.filter(session=session).values_list('user_id', flat=True)
    
    # Mark checked in status
    for attendee in attendees:
        attendee.checked_in = attendee.user_id in checked_in
        if attendee.checked_in:
            record = AttendanceRecord.objects.filter(session=session, user=attendee.user).first()
            attendee.checked_in_at = record.checked_in_at if record else None
    
    context = {
        'session': session,
        'attendees': attendees,
        'checked_in_count': len(checked_in),
        'total_count': attendees.count(),
        'now': timezone.now(),
    }
    
    return render(request, 'events/print_attendance.html', context)


@login_required
@require_POST
def send_session_reminder(request, session_id):
    """Send reminder to pending attendees"""
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    # Get pending attendees (not checked in)
    checked_in = AttendanceRecord.objects.filter(session=session).values_list('user_id', flat=True)
    pending_attendees = EventAttendee.objects.filter(
        event=session.event
    ).exclude(user_id__in=checked_in).select_related('user')
    
    # Here you would implement actual email/SMS sending logic
    # For now, just count and return success
    
    # Log the action
    ActivityLog.objects.create(
        user=request.user,
        action_type='executive_action',
        ip_address=get_client_ip(request),
        details={
            'action': 'send_reminder',
            'session_id': session_id,
            'session_name': session.name,
            'pending_count': pending_attendees.count()
        }
    )
    
    return JsonResponse({
        'success': True,
        'message': f'Reminders sent to {pending_attendees.count()} attendees'
    })


@login_required
@require_POST
def extend_session(request, session_id):
    """Extend session end time"""
    try:
        data = json.loads(request.body)
        minutes = int(data.get('minutes', 15))
        
        if minutes < 1 or minutes > 120:
            return JsonResponse({
                'success': False, 
                'error': 'Minutes must be between 1 and 120'
            })
        
        session = get_object_or_404(AttendanceSession, id=session_id)
        session.end_time += timedelta(minutes=minutes)
        session.save()
        
        # Log the action
        ActivityLog.objects.create(
            user=request.user,
            action_type='executive_action',
            ip_address=get_client_ip(request),
            details={
                'action': 'extend_session',
                'session_id': session_id,
                'session_name': session.name,
                'minutes': minutes
            }
        )
        
        return JsonResponse({
            'success': True,
            'new_end_time': session.end_time.strftime('%H:%M'),
            'message': f'Session extended by {minutes} minutes'
        })
        
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid minutes value'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def lookup_student_api(request):
    """API endpoint to lookup student by ID for a specific session"""
    student_id = request.GET.get('student_id')
    session_id = request.GET.get('session_id')
    
    if not student_id or not session_id:
        return JsonResponse({'found': False, 'error': 'Missing parameters'})
    
    try:
        student = User.objects.get(
            Q(student_id=student_id) | Q(username=student_id),
            user_type='student',
            is_active=True
        )
        
        session = get_object_or_404(AttendanceSession, id=session_id)
        
        # Check if registered for the event
        is_registered = EventAttendee.objects.filter(
            event=session.event,
            user=student
        ).exists()
        
        # Check if already checked in
        already_checked = AttendanceRecord.objects.filter(
            session=session,
            user=student
        ).exists()
        
        return JsonResponse({
            'found': True,
            'name': student.get_full_name(),
            'level': student.level,
            'program': student.get_program_type_display(),
            'is_registered': is_registered,
            'already_checked': already_checked
        })
        
    except User.DoesNotExist:
        return JsonResponse({'found': False, 'error': 'Student not found'})
    except Exception as e:
        return JsonResponse({'found': False, 'error': str(e)})


@login_required
@require_POST
def manual_checkin_api(request):
    """API endpoint for manual check-in (AJAX)"""
    student_id = request.POST.get('student_id')
    session_id = request.POST.get('session_id')
    
    if not student_id or not session_id:
        return JsonResponse({'success': False, 'error': 'Missing required fields'})
    
    try:
        student = User.objects.get(
            Q(student_id=student_id) | Q(username=student_id),
            user_type='student',
            is_active=True
        )
        
        session = get_object_or_404(AttendanceSession, id=session_id)
        
        # Check if registered for the event
        if not EventAttendee.objects.filter(event=session.event, user=student).exists():
            return JsonResponse({
                'success': False, 
                'error': f'{student.get_full_name()} is not registered for this event'
            })
        
        # Check if already checked in
        if AttendanceRecord.objects.filter(session=session, user=student).exists():
            return JsonResponse({
                'success': False, 
                'error': f'{student.get_full_name()} already checked in'
            })
        
        # Create attendance record
        record = AttendanceRecord.objects.create(
            session=session,
            user=student,
            check_in_method='manual',
            ip_address=get_client_ip(request),
            device_info=request.META.get('HTTP_USER_AGENT', '')[:200]
        )
        
        # Update event attendee
        attendee = EventAttendee.objects.get(event=session.event, user=student)
        attendee.attended = True
        attendee.checked_in_at = timezone.now()
        attendee.check_in_method = 'manual'
        attendee.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='attendance_marked',
            ip_address=get_client_ip(request),
            details={
                'session': session.name,
                'event': session.event.title,
                'student': student.get_full_name(),
                'method': 'manual_api'
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Checked in {student.get_full_name()}',
            'student_name': student.get_full_name(),
            'check_in_time': record.checked_in_at.strftime('%H:%M:%S')
        })
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student not found'})
    except AttendanceSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Session not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})








# apps/events/views.py

def session_edit(request, session_id):
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    if request.user.user_type not in ['admin', 'staff', 'executive']:
        messages.error(request, 'You do not have permission to edit sessions.')
        return redirect('events:session_detail', pk=session_id)
    
    if request.method == 'POST':
        form = AttendanceSessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, 'Session updated successfully.')
            return redirect('events:session_detail', pk=session_id)
    else:
        form = AttendanceSessionForm(instance=session)
    
    context = {
        'form': form,
        'session': session,
        'action': 'Edit'
    }
    return render(request, 'events/session_form.html', context)


def session_delete(request, session_id):
    session = get_object_or_404(AttendanceSession, id=session_id)
    event_id = session.event.id
    
    if request.user.user_type not in ['admin', 'staff', 'executive']:
        messages.error(request, 'You do not have permission to delete sessions.')
        return redirect('events:session_detail', pk=session_id)
    
    if request.method == 'POST':
        session.delete()
        messages.success(request, 'Session deleted successfully.')
        return redirect('events:event_detail', pk=event_id)
    
    context = {
        'session': session
    }
    return render(request, 'events/session_confirm_delete.html', context)


def download_session_qr(request, session_id):
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    if not session.qr_code:
        session.generate_qr_code()
        session.save()
    
    response = FileResponse(session.qr_code)
    response['Content-Disposition'] = f'attachment; filename="session_{session.session_code}_qrcode.png"'
    return response


def export_session_attendance(request, session_id):
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="session_{session.id}_attendance.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student ID', 'Name', 'Level', 'Program', 'Check-in Time', 'Method', 'IP Address'])
    
    records = AttendanceRecord.objects.filter(session=session).select_related('user').order_by('checked_in_at')
    
    for record in records:
        writer.writerow([
            record.user.student_id,
            record.user.get_full_name(),
            record.user.level,
            record.user.get_program_type_display(),
            record.checked_in_at.strftime('%Y-%m-%d %H:%M:%S') if record.checked_in_at else '',
            record.get_check_in_method_display(),
            record.ip_address or ''
        ])
    
    return response


def print_attendance(request, session_id):
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    attendees = EventAttendee.objects.filter(
        event=session.event
    ).select_related('user').order_by('user__last_name', 'user__first_name')
    
    checked_in = AttendanceRecord.objects.filter(session=session).values_list('user_id', flat=True)
    
    for attendee in attendees:
        attendee.checked_in = attendee.user_id in checked_in
        if attendee.checked_in:
            record = AttendanceRecord.objects.filter(session=session, user=attendee.user).first()
            attendee.checked_in_at = record.checked_in_at if record else None
    
    context = {
        'session': session,
        'attendees': attendees,
        'checked_in_count': len(checked_in),
        'total_count': attendees.count(),
        'now': timezone.now(),
    }
    
    return render(request, 'events/print_attendance.html', context)


@require_POST
def send_session_reminder(request, session_id):
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    checked_in = AttendanceRecord.objects.filter(session=session).values_list('user_id', flat=True)
    pending_attendees = EventAttendee.objects.filter(
        event=session.event
    ).exclude(user_id__in=checked_in).select_related('user')
    
    ActivityLog.objects.create(
        user=request.user,
        action_type='executive_action',
        ip_address=get_client_ip(request),
        details={
            'action': 'send_reminder',
            'session_id': session_id,
            'session_name': session.name,
            'pending_count': pending_attendees.count()
        }
    )
    
    return JsonResponse({
        'success': True,
        'message': f'Reminders sent to {pending_attendees.count()} attendees'
    })


@require_POST
def extend_session(request, session_id):
    try:
        data = json.loads(request.body)
        minutes = int(data.get('minutes', 15))
        
        if minutes < 1 or minutes > 120:
            return JsonResponse({
                'success': False, 
                'error': 'Minutes must be between 1 and 120'
            })
        
        session = get_object_or_404(AttendanceSession, id=session_id)
        session.end_time += timedelta(minutes=minutes)
        session.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action_type='executive_action',
            ip_address=get_client_ip(request),
            details={
                'action': 'extend_session',
                'session_id': session_id,
                'session_name': session.name,
                'minutes': minutes
            }
        )
        
        return JsonResponse({
            'success': True,
            'new_end_time': session.end_time.strftime('%H:%M'),
            'message': f'Session extended by {minutes} minutes'
        })
        
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid minutes value'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def lookup_student_api(request):
    student_id = request.GET.get('student_id')
    session_id = request.GET.get('session_id')
    
    if not student_id or not session_id:
        return JsonResponse({'found': False, 'error': 'Missing parameters'})
    
    try:
        student = User.objects.get(
            Q(student_id=student_id) | Q(username=student_id),
            user_type='student',
            is_active=True
        )
        
        session = get_object_or_404(AttendanceSession, id=session_id)
        
        is_registered = EventAttendee.objects.filter(
            event=session.event,
            user=student
        ).exists()
        
        already_checked = AttendanceRecord.objects.filter(
            session=session,
            user=student
        ).exists()
        
        return JsonResponse({
            'found': True,
            'name': student.get_full_name(),
            'level': student.level,
            'program': student.get_program_type_display(),
            'is_registered': is_registered,
            'already_checked': already_checked
        })
        
    except User.DoesNotExist:
        return JsonResponse({'found': False, 'error': 'Student not found'})
    except Exception as e:
        return JsonResponse({'found': False, 'error': str(e)})


@require_POST
def manual_checkin_api(request):
    student_id = request.POST.get('student_id')
    session_id = request.POST.get('session_id')
    
    if not student_id or not session_id:
        return JsonResponse({'success': False, 'error': 'Missing required fields'})
    
    try:
        student = User.objects.get(
            Q(student_id=student_id) | Q(username=student_id),
            user_type='student',
            is_active=True
        )
        
        session = get_object_or_404(AttendanceSession, id=session_id)
        
        if not EventAttendee.objects.filter(event=session.event, user=student).exists():
            return JsonResponse({
                'success': False, 
                'error': f'{student.get_full_name()} is not registered for this event'
            })
        
        if AttendanceRecord.objects.filter(session=session, user=student).exists():
            return JsonResponse({
                'success': False, 
                'error': f'{student.get_full_name()} already checked in'
            })
        
        record = AttendanceRecord.objects.create(
            session=session,
            user=student,
            check_in_method='manual',
            ip_address=get_client_ip(request),
            device_info=request.META.get('HTTP_USER_AGENT', '')[:200]
        )
        
        attendee = EventAttendee.objects.get(event=session.event, user=student)
        attendee.attended = True
        attendee.checked_in_at = timezone.now()
        attendee.check_in_method = 'manual'
        attendee.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action_type='attendance_marked',
            ip_address=get_client_ip(request),
            details={
                'session': session.name,
                'event': session.event.title,
                'student': student.get_full_name(),
                'method': 'manual_api'
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Checked in {student.get_full_name()}',
            'student_name': student.get_full_name(),
            'check_in_time': record.checked_in_at.strftime('%H:%M:%S')
        })
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student not found'})
    except AttendanceSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Session not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# apps/events/views.py

@login_required
def event_feedback(request, pk):
    """Submit feedback for an event"""
    event = get_object_or_404(Event, pk=pk)
    
    # Check if user attended the event
    attendee = get_object_or_404(EventAttendee, event=event, user=request.user)
    
    if not attendee.attended:
        messages.error(request, 'You can only give feedback for events you attended.')
        return redirect('events:my_events')
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        # Create feedback
        feedback = EventFeedback.objects.create(
            event=event,
            user=request.user,
            rating=rating,
            comment=comment
        )
        
        messages.success(request, 'Thank you for your feedback!')
        return redirect('events:my_events')
    
    return render(request, 'events/feedback_form.html', {'event': event})



def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip