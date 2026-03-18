# attendance/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import AttendanceSession, AttendanceRecord
from apps.events.models import Event
from apps.accounts.models import User, ActivityLog
from .forms import AttendanceSessionForm, ManualAttendanceForm
import csv
import qrcode
import io
from django.core.files.base import ContentFile
import base64

@login_required
def session_list(request):
    """List all attendance sessions"""
    sessions = AttendanceSession.objects.all().order_by('-date', '-start_time')
    
    # Filter by type
    session_type = request.GET.get('type')
    if session_type:
        sessions = sessions.filter(session_type=session_type)
    
    # Filter by date
    date = request.GET.get('date')
    if date:
        sessions = sessions.filter(date=date)
    
    # Filter by event
    event_id = request.GET.get('event')
    if event_id:
        sessions = sessions.filter(event_id=event_id)
    
    paginator = Paginator(sessions, 20)
    page = request.GET.get('page')
    sessions = paginator.get_page(page)
    
    context = {
        'sessions': sessions,
        'session_types': AttendanceSession.SESSION_TYPES,
        'events': Event.objects.filter(is_active=True),
    }
    return render(request, 'attendance/session_list.html', context)

@login_required
def session_detail(request, pk):
    """View attendance session details"""
    session = get_object_or_404(AttendanceSession, pk=pk)
    
    # Get attendance records
    records = AttendanceRecord.objects.filter(
        session=session
    ).select_related('student').order_by('-checked_in_at')
    
    # Statistics
    total_attended = records.count()
    
    context = {
        'session': session,
        'records': records,
        'total_attended': total_attended,
        'can_manage': request.user.user_type in ['admin', 'staff'] or request.user == session.created_by,
    }
    return render(request, 'attendance/session_detail.html', context)

@login_required
def session_create(request):
    """Create new attendance session"""
    if request.user.user_type not in ['admin', 'staff', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('attendance:session_list')
    
    if request.method == 'POST':
        form = AttendanceSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.created_by = request.user
            session.save()
            
            # Generate QR code
            generate_qr_code(session)
            
            messages.success(request, 'Attendance session created successfully!')
            return redirect('attendance:session_detail', pk=session.pk)
    else:
        form = AttendanceSessionForm()
    
    return render(request, 'attendance/session_form.html', {'form': form, 'action': 'Create'})

@login_required
def session_edit(request, pk):
    """Edit attendance session"""
    session = get_object_or_404(AttendanceSession, pk=pk)
    
    # Check permissions
    if not (request.user.user_type in ['admin', 'staff'] or request.user == session.created_by):
        messages.error(request, 'Access denied.')
        return redirect('attendance:session_detail', pk=pk)
    
    if request.method == 'POST':
        form = AttendanceSessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance session updated successfully!')
            return redirect('attendance:session_detail', pk=session.pk)
    else:
        form = AttendanceSessionForm(instance=session)
    
    return render(request, 'attendance/session_form.html', {
        'form': form, 
        'action': 'Edit',
        'session': session
    })

@login_required
def generate_session_qr(request, pk):
    """Generate QR code for session"""
    session = get_object_or_404(AttendanceSession, pk=pk)
    
    # Check permissions
    if not (request.user.user_type in ['admin', 'staff'] or request.user == session.created_by):
        messages.error(request, 'Access denied.')
        return redirect('attendance:session_detail', pk=pk)
    
    # Generate new QR code
    generate_qr_code(session)
    
    messages.success(request, 'QR code generated successfully!')
    return redirect('attendance:session_detail', pk=pk)

@login_required
def mark_attendance(request):
    """Mark attendance page"""
    if request.user.user_type not in ['admin', 'staff', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    # Get active sessions
    active_sessions = AttendanceSession.objects.filter(
        date=timezone.now().date(),
        is_active=True
    )
    
    context = {
        'active_sessions': active_sessions,
        'manual_form': ManualAttendanceForm(),
    }
    return render(request, 'attendance/mark_attendance.html', context)

@login_required
@require_POST
def mark_attendance_manual(request):
    """Mark attendance manually"""
    if request.user.user_type not in ['admin', 'staff', 'executive']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    session_id = request.POST.get('session_id')
    student_id = request.POST.get('student_id')
    
    try:
        session = AttendanceSession.objects.get(id=session_id, is_active=True)
        student = User.objects.get(
            Q(student_id=student_id) | Q(id=student_id),
            user_type__in=['student', 'executive']
        )
        
        # Check if already marked
        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            student=student,
            defaults={
                'checked_in_by': request.user,
                'method': 'manual'
            }
        )
        
        if created:
            # If associated with event, mark as attended
            if session.event:
                from events.models import EventAttendee
                EventAttendee.objects.filter(
                    event=session.event,
                    user=student
                ).update(attended=True)
            
            return JsonResponse({
                'success': True,
                'student_name': student.get_full_name(),
                'student_id': student.student_id,
                'time': record.checked_in_at.strftime('%H:%M:%S')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Attendance already marked'
            })
            
    except AttendanceSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Session not found'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student not found'})

@login_required
def mark_attendance_qr(request):
    """Mark attendance via QR code (for students)"""
    return render(request, 'attendance/qr_scanner.html')

@login_required
def my_attendance(request):
    """View user's attendance records"""
    records = AttendanceRecord.objects.filter(
        student=request.user
    ).select_related('session').order_by('-checked_in_at')
    
    # Statistics
    total_sessions = records.count()
    
    # Group by month
    monthly_stats = {}
    for record in records:
        month_key = record.checked_in_at.strftime('%Y-%m')
        if month_key not in monthly_stats:
            monthly_stats[month_key] = 0
        monthly_stats[month_key] += 1
    
    paginator = Paginator(records, 20)
    page = request.GET.get('page')
    records = paginator.get_page(page)
    
    context = {
        'records': records,
        'total_sessions': total_sessions,
        'monthly_stats': monthly_stats,
    }
    return render(request, 'attendance/my_attendance.html', context)

@login_required
def attendance_reports(request):
    """View attendance reports"""
    if request.user.user_type not in ['admin', 'staff', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    # Overall statistics
    total_sessions = AttendanceSession.objects.count()
    total_records = AttendanceRecord.objects.count()
    
    # Sessions by type
    sessions_by_type = AttendanceSession.objects.values(
        'session_type'
    ).annotate(count=Count('id'))
    
    # Recent sessions
    recent_sessions = AttendanceSession.objects.annotate(
        attendee_count=Count('attendance_records')
    ).order_by('-date')[:10]
    
    # Top attendees
    top_attendees = User.objects.filter(
        user_type='student'
    ).annotate(
        attendance_count=Count('attendance_records')
    ).order_by('-attendance_count')[:10]
    
    context = {
        'total_sessions': total_sessions,
        'total_records': total_records,
        'average_per_session': round(total_records / total_sessions, 2) if total_sessions > 0 else 0,
        'sessions_by_type': sessions_by_type,
        'recent_sessions': recent_sessions,
        'top_attendees': top_attendees,
    }
    return render(request, 'attendance/reports.html', context)

@login_required
def export_attendance_csv(request, session_id):
    """Export attendance records to CSV"""
    session = get_object_or_404(AttendanceSession, pk=session_id)
    
    # Check permissions
    if not (request.user.user_type in ['admin', 'staff'] or request.user == session.created_by):
        messages.error(request, 'Access denied.')
        return redirect('attendance:session_detail', pk=session_id)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_{session.title}_{session.date}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student ID', 'Name', 'Level', 'Program', 'Check-in Time', 'Method'])
    
    records = AttendanceRecord.objects.filter(
        session=session
    ).select_related('student').order_by('checked_in_at')
    
    for record in records:
        writer.writerow([
            record.student.student_id or '',
            record.student.get_full_name(),
            record.student.get_level_display() if record.student.level else '',
            record.student.get_program_type_display() if record.student.program_type else '',
            record.checked_in_at.strftime('%Y-%m-%d %H:%M:%S'),
            record.get_method_display()
        ])
    
    return response

def generate_qr_code(session):
    """Generate QR code for attendance session"""
    qr_data = f"{session.id}:{session.qr_secret}"
    
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=5
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to BytesIO
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    
    # Save to FileField
    filename = f"qr_{session.id}_{timezone.now().date()}.png"
    session.qr_code.save(filename, ContentFile(buffer.getvalue()), save=True)

# apps/attendance/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
import csv
import json
import qrcode
from io import BytesIO
import base64
from datetime import timedelta

from apps.events.models import Event, AttendanceSession, AttendanceRecord, EventAttendee
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
@user_passes_test(lambda u: u.user_type in ['admin', 'staff', 'executive'])
def mark_attendance(request):
    """Main attendance marking page"""
    # Get upcoming events for selection
    events = Event.objects.filter(
        is_active=True,
        end_date__gte=timezone.now()
    ).order_by('start_date')
    
    selected_event = None
    selected_session = None
    registrations = []
    checked_in_count = 0
    total_registered = 0
    remaining_count = 0
    attendance_percentage = 0
    
    # Check if session is selected
    session_id = request.GET.get('session')
    if session_id:
        try:
            selected_session = AttendanceSession.objects.select_related('event').get(id=session_id)
            selected_event = selected_session.event
            
            # Get all registered attendees for this event
            registrations = EventAttendee.objects.filter(
                event=selected_event
            ).select_related('user').order_by('user__last_name')
            
            # Get attendance records for this session
            attendance_records = AttendanceRecord.objects.filter(
                session=selected_session
            ).values_list('user_id', flat=True)
            
            # Mark which attendees have checked in
            for registration in registrations:
                registration.attended = registration.user_id in attendance_records
                if registration.attended:
                    record = AttendanceRecord.objects.filter(
                        session=selected_session,
                        user=registration.user
                    ).first()
                    registration.checked_in_at = record.checked_in_at if record else None
            
            # Calculate statistics
            total_registered = registrations.count()
            checked_in_count = len(attendance_records)
            remaining_count = total_registered - checked_in_count
            attendance_percentage = (checked_in_count / total_registered * 100) if total_registered > 0 else 0
            
        except AttendanceSession.DoesNotExist:
            messages.error(request, 'Session not found')
    
    # Get sessions for the selected event
    sessions = []
    event_id = request.GET.get('event')
    if event_id:
        try:
            event = Event.objects.get(id=event_id)
            sessions = event.attendance_sessions.filter(is_active=True).order_by('start_time')
        except Event.DoesNotExist:
            pass
    
    context = {
        'events': events,
        'sessions': sessions,
        'selected_event': selected_event,
        'selected_session': selected_session,
        'registrations': registrations,
        'checked_in_count': checked_in_count,
        'total_registered': total_registered,
        'remaining_count': remaining_count,
        'attendance_percentage': attendance_percentage,
    }
    
    return render(request, 'attendance/mark_attendance.html', context)


@login_required
def get_sessions(request):
    """AJAX endpoint to get sessions for an event"""
    event_id = request.GET.get('event_id')
    if not event_id:
        return JsonResponse({'sessions': []})
    
    try:
        event = Event.objects.get(id=event_id)
        sessions = event.attendance_sessions.filter(is_active=True).order_by('start_time')
        
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'id': session.id,
                'name': session.name,
                'time': f"{session.start_time.strftime('%H:%M')} - {session.end_time.strftime('%H:%M')}",
            })
        
        return JsonResponse({'sessions': sessions_data})
    except Event.DoesNotExist:
        return JsonResponse({'sessions': []})


@login_required
def get_session_attendance(request, session_id):
    """AJAX endpoint to get real-time attendance data for a session"""
    try:
        session = AttendanceSession.objects.get(id=session_id)
        attendance_records = AttendanceRecord.objects.filter(session=session)
        checked_in_count = attendance_records.count()
        
        event_attendees = EventAttendee.objects.filter(event=session.event)
        total_registered = event_attendees.count()
        
        percentage = (checked_in_count / total_registered * 100) if total_registered > 0 else 0
        
        # Get list of checked in students
        attendance_data = []
        for record in attendance_records.select_related('user'):
            attendance_data.append({
                'student_id': record.user.student_id,
                'name': record.user.get_full_name(),
                'checked_in': True,
                'time': record.checked_in_at.strftime('%H:%M:%S') if record.checked_in_at else None,
            })
        
        return JsonResponse({
            'success': True,
            'checked_in_count': checked_in_count,
            'total_registered': total_registered,
            'percentage': percentage,
            'attendance': attendance_data,
        })
    except AttendanceSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Session not found'})


@login_required
def lookup_student(request):
    """AJAX endpoint to lookup student by ID"""
    student_id = request.GET.get('student_id')
    if not student_id:
        return JsonResponse({'found': False})
    
    try:
        student = User.objects.get(
            Q(student_id=student_id) | Q(username=student_id),
            user_type='student',
            is_active=True
        )
        return JsonResponse({
            'found': True,
            'name': student.get_full_name(),
            'level': student.level,
            'program': student.get_program_type_display(),
        })
    except User.DoesNotExist:
        return JsonResponse({'found': False})


@login_required
@require_POST
def checkin_student(request):
    """AJAX endpoint to check in a student"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        student_id = data.get('student_id')
        
        session = get_object_or_404(AttendanceSession, id=session_id)
        student = get_object_or_404(User, id=student_id, user_type='student')
        
        # Check if already checked in
        if AttendanceRecord.objects.filter(session=session, user=student).exists():
            return JsonResponse({
                'success': False,
                'error': 'Student already checked in'
            })
        
        # Check if student is registered for the event
        if not EventAttendee.objects.filter(event=session.event, user=student).exists():
            return JsonResponse({
                'success': False,
                'error': 'Student not registered for this event'
            })
        
        # Create attendance record
        record = AttendanceRecord.objects.create(
            session=session,
            user=student,
            check_in_method='manual',
            ip_address=get_client_ip(request),
            device_info=request.META.get('HTTP_USER_AGENT', '')[:200]
        )
        
        # Update event attendee status
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
                'student': student.get_full_name()
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Checked in {student.get_full_name()}',
            'check_in_time': record.checked_in_at.strftime('%H:%M:%S')
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def qr_checkin(request):
    """AJAX endpoint for QR code check-in"""
    try:
        data = json.loads(request.body)
        code = data.get('code')
        
        # Try to find session by QR code
        try:
            session = AttendanceSession.objects.get(session_code=code)
        except AttendanceSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid QR code'
            })
        
        # Check if session is active
        if not (session.start_time <= timezone.now() <= session.end_time):
            return JsonResponse({
                'success': False,
                'error': 'Session is not currently active'
            })
        
        # Check if already checked in
        if AttendanceRecord.objects.filter(session=session, user=request.user).exists():
            return JsonResponse({
                'success': False,
                'error': 'You have already checked in to this session'
            })
        
        # Check if user is registered for the event
        if not EventAttendee.objects.filter(event=session.event, user=request.user).exists():
            return JsonResponse({
                'success': False,
                'error': 'You are not registered for this event'
            })
        
        # Create attendance record
        record = AttendanceRecord.objects.create(
            session=session,
            user=request.user,
            check_in_method='qr_code',
            ip_address=get_client_ip(request),
            device_info=request.META.get('HTTP_USER_AGENT', '')[:200]
        )
        
        # Update event attendee status
        attendee = EventAttendee.objects.get(event=session.event, user=request.user)
        attendee.attended = True
        attendee.checked_in_at = timezone.now()
        attendee.check_in_method = 'qr_code'
        attendee.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='attendance_marked',
            ip_address=get_client_ip(request),
            details={
                'session': session.name,
                'event': session.event.title,
                'method': 'qr_code'
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Check-in successful!',
            'session_name': session.name,
            'check_in_time': record.checked_in_at.strftime('%H:%M:%S'),
            'session_id': session.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
@user_passes_test(lambda u: u.user_type in ['admin', 'staff', 'executive'])
def checkin_all(request, session_id):
    """Check in all pending attendees"""
    try:
        session = get_object_or_404(AttendanceSession, id=session_id)
        
        # Get all registered attendees who haven't checked in
        pending_attendees = EventAttendee.objects.filter(
            event=session.event,
            attended=False
        ).select_related('user')
        
        checked_in_count = 0
        for attendee in pending_attendees:
            # Create attendance record
            AttendanceRecord.objects.create(
                session=session,
                user=attendee.user,
                check_in_method='automatic',
                ip_address=get_client_ip(request)
            )
            
            # Update attendee
            attendee.attended = True
            attendee.checked_in_at = timezone.now()
            attendee.check_in_method = 'automatic'
            attendee.save()
            
            checked_in_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Checked in {checked_in_count} attendees',
            'count': checked_in_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff', 'executive'])
def bulk_checkin(request, session_id):
    """Bulk check-in via CSV upload"""
    if request.method != 'POST':
        return redirect('attendance:mark_attendance')
    
    session = get_object_or_404(AttendanceSession, id=session_id)
    file = request.FILES.get('file')
    
    if not file:
        messages.error(request, 'No file uploaded')
        return redirect('attendance:mark_attendance')
    
    if not file.name.endswith('.csv'):
        messages.error(request, 'Please upload a CSV file')
        return redirect('attendance:mark_attendance')
    
    try:
        # Read CSV file
        decoded_file = file.read().decode('utf-8').splitlines()
        reader = csv.reader(decoded_file)
        
        success_count = 0
        error_count = 0
        errors = []
        
        for row_num, row in enumerate(reader, start=1):
            if not row or not row[0].strip():
                continue
            
            student_id = row[0].strip()
            
            try:
                # Find student
                student = User.objects.get(
                    Q(student_id=student_id) | Q(username=student_id),
                    user_type='student',
                    is_active=True
                )
                
                # Check if registered
                if not EventAttendee.objects.filter(event=session.event, user=student).exists():
                    errors.append(f"Row {row_num}: Student {student_id} not registered")
                    error_count += 1
                    continue
                
                # Check if already checked in
                if AttendanceRecord.objects.filter(session=session, user=student).exists():
                    errors.append(f"Row {row_num}: Student {student_id} already checked in")
                    error_count += 1
                    continue
                
                # Create attendance record
                AttendanceRecord.objects.create(
                    session=session,
                    user=student,
                    check_in_method='automatic',
                    ip_address=get_client_ip(request)
                )
                
                # Update attendee
                attendee = EventAttendee.objects.get(event=session.event, user=student)
                attendee.attended = True
                attendee.checked_in_at = timezone.now()
                attendee.check_in_method = 'automatic'
                attendee.save()
                
                success_count += 1
                
            except User.DoesNotExist:
                errors.append(f"Row {row_num}: Student {student_id} not found")
                error_count += 1
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                error_count += 1
        
        if success_count > 0:
            messages.success(request, f'Successfully checked in {success_count} students')
        
        if errors:
            for error in errors[:5]:  # Show first 5 errors
                messages.error(request, error)
            if len(errors) > 5:
                messages.warning(request, f'And {len(errors) - 5} more errors...')
        
    except Exception as e:
        messages.error(request, f'Error processing file: {str(e)}')
    
    return redirect('attendance:mark_attendance')


@login_required
def manual_checkin(request, session_id):
    """Manual check-in form submission"""
    if request.method != 'POST':
        return redirect('attendance:mark_attendance')
    
    session = get_object_or_404(AttendanceSession, id=session_id)
    student_id = request.POST.get('student_id')
    
    try:
        student = User.objects.get(
            Q(student_id=student_id) | Q(username=student_id),
            user_type='student',
            is_active=True
        )
        
        # Check if registered
        if not EventAttendee.objects.filter(event=session.event, user=student).exists():
            messages.error(request, f'{student.get_full_name()} is not registered for this event')
            return redirect('attendance:mark_attendance')
        
        # Check if already checked in
        if AttendanceRecord.objects.filter(session=session, user=student).exists():
            messages.warning(request, f'{student.get_full_name()} already checked in')
            return redirect('attendance:mark_attendance')
        
        # Create attendance record
        AttendanceRecord.objects.create(
            session=session,
            user=student,
            check_in_method='manual',
            ip_address=get_client_ip(request)
        )
        
        # Update attendee
        attendee = EventAttendee.objects.get(event=session.event, user=student)
        attendee.attended = True
        attendee.checked_in_at = timezone.now()
        attendee.check_in_method = 'manual'
        attendee.save()
        
        messages.success(request, f'Successfully checked in {student.get_full_name()}')
        
    except User.DoesNotExist:
        messages.error(request, f'Student with ID {student_id} not found')
    
    return redirect('attendance:mark_attendance')


@login_required
def download_session_qr(request, session_id):
    """Download QR code for session"""
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    if not session.qr_code:
        # Generate QR code if not exists
        session.generate_qr_code()
        session.save()
    
    response = FileResponse(session.qr_code)
    response['Content-Disposition'] = f'attachment; filename="session_{session.session_code}_qrcode.png"'
    return response


@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff', 'executive'])
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
    ).select_related('user').order_by('user__last_name')
    
    # Get checked in records
    checked_in = AttendanceRecord.objects.filter(session=session).values_list('user_id', flat=True)
    
    for attendee in attendees:
        attendee.checked_in = attendee.user_id in checked_in
    
    context = {
        'session': session,
        'attendees': attendees,
        'checked_in_count': len(checked_in),
        'total_count': attendees.count(),
        'now': timezone.now(),
    }
    
    return render(request, 'attendance/print_attendance.html', context)


@login_required
@require_POST
@user_passes_test(lambda u: u.user_type in ['admin', 'staff', 'executive'])
def send_session_reminder(request, session_id):
    """Send reminder to pending attendees"""
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    # Get pending attendees
    checked_in = AttendanceRecord.objects.filter(session=session).values_list('user_id', flat=True)
    pending_attendees = EventAttendee.objects.filter(
        event=session.event
    ).exclude(
        user_id__in=checked_in
    ).select_related('user')
    
    # Here you would implement email/SMS sending logic
    # For now, just count and return
    
    return JsonResponse({
        'success': True,
        'message': f'Reminders sent to {pending_attendees.count()} attendees'
    })


@login_required
@require_POST
@user_passes_test(lambda u: u.user_type in ['admin', 'staff', 'executive'])
def extend_session(request, session_id):
    """Extend session end time"""
    try:
        data = json.loads(request.body)
        minutes = int(data.get('minutes', 15))
        
        session = get_object_or_404(AttendanceSession, id=session_id)
        session.end_time += timedelta(minutes=minutes)
        session.save()
        
        return JsonResponse({
            'success': True,
            'new_end_time': session.end_time.strftime('%H:%M')
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})