# directory/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from django.template.loader import render_to_string
#from weasyprint import HTML
import csv
import tempfile
import os
from .models import StudentIDCard
from apps.accounts.models import User, StudentExecutive
from apps.events.models import EventAttendee

@login_required
def directory_home(request):
    """Directory home page"""
    # Statistics
    total_students = User.objects.filter(user_type='student').count()
    total_executives = User.objects.filter(user_type='executive').count()
    
    # Students by level
    students_by_level = User.objects.filter(
        user_type='student'
    ).values('level').annotate(
        count=Count('id')
    ).order_by('level')
    
    # Recent students
    recent_students = User.objects.filter(
        user_type='student'
    ).order_by('-date_joined')[:10]
    
    # Executives
    executives = StudentExecutive.objects.filter(
        is_active=True
    ).select_related('user')[:5]
    
    context = {
        'total_students': total_students,
        'total_executives': total_executives,
        'students_by_level': students_by_level,
        'recent_students': recent_students,
        'executives': executives,
    }
    return render(request, 'directory/directory_home.html', context)

@login_required
def student_list(request):
    """List all students"""
    students = User.objects.filter(
       user_type__in=['student', 'executive']
    ).select_related('account_executive_profile')  # or core_executive_profile
    
    # Filters
    level = request.GET.get('level')
    if level:
        students = students.filter(level=level)
    
    programs = [(p, p.capitalize()) for p in ['regular', 'weekend']]
    
    year = request.GET.get('year')
    if year:
        students = students.filter(year_of_admission=year)
    
    search = request.GET.get('search')
    if search:
        students = students.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(student_id__icontains=search)
        )
    
    # Sorting
    sort = request.GET.get('sort', 'last_name')
    if sort == 'name':
        students = students.order_by('last_name', 'first_name')
    elif sort == 'level':
        students = students.order_by('level', 'last_name')
    elif sort == 'id':
        students = students.order_by('student_id')
    
    paginator = Paginator(students, 20)
    page = request.GET.get('page')
    students = paginator.get_page(page)
    
    levels = [
      ('100', 'Level 100'),
      ('200', 'Level 200'),
      ('300', 'Level 300'),
      ('400', 'Level 400'),
   ]
    
    context = {
        'students': students,
        'levels': levels,
        'programs': programs,
        'current_filters': {
            'level': level,
            #'program': program,
            'year': year,
            'search': search,
            'sort': sort,
        }
    }
    return render(request, 'directory/student_list.html', context)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.accounts.models import User
from apps.directory.models import StudentIDCard
from apps.events.models import EventAttendee
from apps.core.models import StudentExecutive

@login_required
def student_detail(request, pk):
    """View student details"""
    # Attempt to fetch the student/executive
    try:
        student = User.objects.get(pk=pk, user_type__in=['student', 'executive'])
    except User.DoesNotExist:
        messages.error(request, "Student not found.")
        return redirect('directory:student_list')

    # Get ID card if it exists
    id_card = StudentIDCard.objects.filter(student=student).first()

    # Get recent event attendance (up to 10)
    events_attended = EventAttendee.objects.filter(
        user=student,
        attended=True
    ).select_related('event')[:10]

    # Get executive info if applicable
    executive_info = None
    if student.user_type == 'executive':
        executive_info = getattr(student, 'executive_profile', None)

    context = {
        'profile_user': student,
        'student': student,  # Add
        'id_card': id_card,
        'events_attended': events_attended,
        'executive_info': executive_info,
        'can_generate_id': request.user.user_type in ['admin', 'staff'] or request.user == student,
    }
    return render(request, 'directory/student_detail.html', context)

@login_required
def my_id_card(request):
    """View current user's ID card"""
    student = request.user
    
    if student.user_type not in ['student', 'executive']:
        messages.error(request, 'ID cards are only available for students.')
        return redirect('core:home')
    
    # Get or create ID card
    id_card, created = StudentIDCard.objects.get_or_create(
        student=student,
        defaults={'card_number': f"ID-{student.student_id}"}
    )
    
    context = {
        'id_card': id_card,
        'student': student,
    }
    return render(request, 'directory/my_id_card.html', context)

@login_required
def generate_id_card(request):
    """Generate new ID card"""
    student = request.user
    
    if student.user_type not in ['student', 'executive']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Delete existing card and create new one
    StudentIDCard.objects.filter(student=student).delete()
    
    id_card = StudentIDCard.objects.create(
        student=student,
        card_number=f"ID-{student.student_id}-{timezone.now().year}"
    )
    
    return JsonResponse({
        'success': True,
        'qr_code_url': id_card.qr_code.url if id_card.qr_code else None,
        'card_number': id_card.card_number,
    })
# apps/directory/views.py

# apps/directory/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string
#from weasyprint import HTML
from .models import StudentIDCard
from .forms import StudentIDCardForm
from apps.accounts.models import User

@login_required
def my_id_card(request):
    """View your own ID card"""
    student = request.user
    
    if student.user_type not in ['student', 'executive']:
        messages.error(request, 'ID cards are only available for students and executives.')
        return redirect('core:home')
    
    # Get or create ID card
    id_card, created = StudentIDCard.objects.get_or_create(
        student=student,
        defaults={'card_number': f"ID-{student.student_id}"}
    )
    
    return render(request, 'directory/my_id_card.html', {
        'student': student,
        'id_card': id_card,
    })

@login_required
def admin_view_id_card(request, student_id):
    """View another student's ID card (staff/admin only)"""
    if request.user.user_type not in ['admin', 'staff']:
        messages.error(request, 'Access denied.')
        return redirect('directory:student_list')
    
    student = get_object_or_404(User, pk=student_id, user_type__in=['student', 'executive'])
    
    # Get or create ID card
    id_card, created = StudentIDCard.objects.get_or_create(
        student=student,
        defaults={'card_number': f"ID-{student.student_id}"}
    )
    
    context = {
        'student': student,
        'id_card': id_card,
        'is_admin_view': True,
    }
    return render(request, 'directory/admin_id_card.html', context)

@login_required
def view_id_card_printable(request):
    """Show printable ID card template for current user"""
    student = request.user
    
    if student.user_type not in ['student', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    # Get or create ID card
    id_card, created = StudentIDCard.objects.get_or_create(
        student=student,
        defaults={'card_number': f"ID-{student.student_id}"}
    )
    
    return render(request, 'directory/id_card_printable.html', {
        'student': student,
        'id_card': id_card,
    })

@login_required
def download_id_card_pdf(request):
    """Download your own ID card as PDF"""
    student = request.user
    
    if student.user_type not in ['student', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    # Get or create ID card
    id_card, created = StudentIDCard.objects.get_or_create(
        student=student,
        defaults={'card_number': f"ID-{student.student_id}"}
    )
    
    # Render HTML template
    html_string = render_to_string('directory/id_card_pdf.html', {
        'student': student,
        'id_card': id_card,
    })
    
    # Generate PDF
    html = HTML(string=html_string)
    pdf = html.write_pdf()
    
    # Update download tracking
    id_card.download_count += 1
    id_card.last_downloaded = timezone.now()
    id_card.save()
    
    # Create response
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="id_card_{student.student_id}.pdf"'
    
    return response

@login_required
def upload_signature(request):
    """Upload student signature"""
    student = request.user
    
    if student.user_type not in ['student', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    id_card, created = StudentIDCard.objects.get_or_create(
        student=student,
        defaults={'card_number': f"ID-{student.student_id}"}
    )
    
    if request.method == 'POST' and request.FILES.get('signature'):
        signature = request.FILES['signature']
        
        # Validate file type
        if not signature.content_type.startswith('image/'):
            messages.error(request, 'Please upload an image file.')
            return redirect('directory:upload_signature')
        
        # Validate file size (max 2MB)
        if signature.size > 2 * 1024 * 1024:
            messages.error(request, 'File size must be less than 2MB.')
            return redirect('directory:upload_signature')
        
        # Save signature
        id_card.student_signature = signature
        id_card.save()
        messages.success(request, 'Signature uploaded successfully!')
        return redirect('directory:my_id_card')
    
    return render(request, 'directory/upload_signature.html', {'id_card': id_card})

@login_required
def clear_signature(request):
    """Clear student signature"""
    student = request.user
    
    if student.user_type not in ['student', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    try:
        id_card = StudentIDCard.objects.get(student=student)
        id_card.student_signature = None
        id_card.save()
        messages.success(request, 'Signature removed successfully.')
    except StudentIDCard.DoesNotExist:
        messages.error(request, 'ID card not found.')
    
    return redirect('directory:upload_signature')

@login_required
def edit_id_card(request):
    """Edit your own ID card information"""
    student = request.user
    
    if student.user_type not in ['student', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    id_card, created = StudentIDCard.objects.get_or_create(
        student=student,
        defaults={'card_number': f"ID-{student.student_id}"}
    )
    
    if request.method == 'POST':
        form = StudentIDCardForm(request.POST, instance=id_card)
        if form.is_valid():
            form.save()
            messages.success(request, 'ID card information updated successfully!')
            return redirect('directory:my_id_card')
    else:
        form = StudentIDCardForm(instance=id_card)
    
    return render(request, 'directory/edit_id_card.html', {'form': form, 'id_card': id_card})

@login_required
def directory_search(request):
    """AJAX search for directory"""
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    students = User.objects.filter(
        user_type__in=['student', 'executive']
    ).filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(student_id__icontains=query)
    )[:10]
    
    results = [{
        'id': s.id,
        'name': s.get_full_name(),
        'student_id': s.student_id,
        'level': s.get_level_display() if s.level else '',
        'program': s.get_program_type_display() if s.program_type else '',
        'photo': s.profile_image.url if s.profile_image else None,
    } for s in students]
    
    return JsonResponse({'results': results})

@login_required
def directory_filter(request):
    """Filter directory via AJAX"""
    students = User.objects.filter(user_type__in=['student', 'executive'])
    
    # Apply filters
    level = request.GET.get('level')
    if level:
        students = students.filter(level=level)
    
    program = request.GET.get('program')
    if program:
        students = students.filter(program_type=program)
    
    year = request.GET.get('year')
    if year:
        students = students.filter(year_of_admission=year)
    
    # Paginate
    paginator = Paginator(students, 20)
    page = request.GET.get('page', 1)
    students_page = paginator.get_page(page)
    
    # Render HTML
    html = render_to_string('directory/_student_list_items.html', {
        'students': students_page
    })
    
    return JsonResponse({
        'html': html,
        'has_next': students_page.has_next(),
        'has_previous': students_page.has_previous(),
        'page': page,
        'total_pages': paginator.num_pages,
    })

@login_required
@staff_member_required
def export_directory(request):
    """Export directory to CSV (staff/admin only)"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_directory.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Student ID', 'Name', 'Email', 'Program', 'Level', 
        'Year of Admission', 'Phone', 'Status'
    ])
    
    students = User.objects.filter(
        user_type__in=['student', 'executive']
    ).order_by('last_name', 'first_name')
    
    for student in students:
        writer.writerow([
            student.student_id or '',
            student.get_full_name(),
            student.email,
            student.get_program_type_display() if student.program_type else '',
            student.get_level_display() if student.level else '',
            student.year_of_admission or '',
            student.phone_number or '',
            'Executive' if student.user_type == 'executive' else 'Student'
        ])
    
    return response

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
import os
import csv
from datetime import datetime, timedelta

from .models import PastQuestion, StudentHandbook, AcademicCalendar, StudentIDCard
from .forms import (
    PastQuestionForm, PastQuestionSearchForm, 
    StudentHandbookForm, AcademicCalendarForm, 
    AcademicCalendarFilterForm, StudentIDCardForm
)
from apps.accounts.models import User


# ========== PAST QUESTIONS VIEWS ==========
@login_required
def past_question_list(request):
    """List all past questions"""
    past_questions = PastQuestion.objects.filter(is_approved=True, is_active=True)
    
    # Search and filter
    search_form = PastQuestionSearchForm(request.GET)
    if search_form.is_valid():
        query = search_form.cleaned_data.get('query')
        level = search_form.cleaned_data.get('level')
        semester = search_form.cleaned_data.get('semester')
        year = search_form.cleaned_data.get('year')
        
        if query:
            past_questions = past_questions.filter(
                Q(course_code__icontains=query) |
                Q(course_name__icontains=query) |
                Q(title__icontains=query)
            )
        
        if level:
            past_questions = past_questions.filter(level=level)
        
        if semester:
            past_questions = past_questions.filter(semester=semester)
        
        if year:
            past_questions = past_questions.filter(exam_year=year)
    
    # Get distinct years for filter
    years = past_questions.values_list('exam_year', flat=True).distinct().order_by('-exam_year')
    
    # Pagination
    paginator = Paginator(past_questions, 12)
    page = request.GET.get('page')
    past_questions = paginator.get_page(page)
    
    # Update choices for year filter
    search_form.fields['year'].choices = [('', 'All Years')] + [(y, y) for y in years]
    
    context = {
        'past_questions': past_questions,
        'search_form': search_form,
        'total_count': past_questions.paginator.count if past_questions.paginator else len(past_questions),
        'years': years,
    }
    return render(request, 'directory/past_question_list.html', context)

@login_required
def past_question_detail(request, pk):
    """View past question details"""
    past_question = get_object_or_404(PastQuestion, pk=pk, is_active=True)
    
    # Increment views
    past_question.views += 1
    past_question.save(update_fields=['views'])
    
    # Get related past questions (same course code)
    related = PastQuestion.objects.filter(
        course_code=past_question.course_code,
        is_active=True
    ).exclude(pk=past_question.pk)[:4]
    
    context = {
        'past_question': past_question,
        'related': related,
    }
    return render(request, 'directory/past_question_detail.html', context)


def download_past_question(request, pk):
    """Download past question file"""
    past_question = get_object_or_404(PastQuestion, pk=pk, is_active=True)
    
    # Increment download count
    past_question.downloads += 1
    past_question.save(update_fields=['downloads'])
    
    # Serve file
    response = FileResponse(past_question.file)
    response['Content-Disposition'] = f'attachment; filename="{past_question.filename()}"'
    return response


@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff', 'executive'])
def past_question_upload(request):
    """Upload past question (staff/executive only)"""
    if request.method == 'POST':
        form = PastQuestionForm(request.POST, request.FILES)
        if form.is_valid():
            past_question = form.save(commit=False)
            past_question.uploaded_by = request.user
            
            # Auto-approve for admin/staff, pending for executives
            if request.user.user_type in ['admin', 'staff']:
                past_question.is_approved = True
            else:
                past_question.is_approved = False
            
            past_question.save()
            
            if past_question.is_approved:
                messages.success(request, 'Past question uploaded successfully!')
            else:
                messages.info(request, 'Past question uploaded and pending approval.')
            
            return redirect('directory:past_question_detail', pk=past_question.pk)
    else:
        form = PastQuestionForm()
    
    return render(request, 'directory/past_question_upload.html', {'form': form})


@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff'])
def past_question_approve(request, pk):
    """Approve past question (admin/staff only)"""
    past_question = get_object_or_404(PastQuestion, pk=pk)
    past_question.is_approved = True
    past_question.save()
    messages.success(request, 'Past question approved successfully.')
    return redirect('directory:past_question_detail', pk=pk)


@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def past_question_delete(request, pk):
    """Delete past question (admin only)"""
    past_question = get_object_or_404(PastQuestion, pk=pk)
    past_question.delete()
    messages.success(request, 'Past question deleted successfully.')
    return redirect('directory:past_question_list')


# ========== STUDENT HANDBOOK VIEWS ==========
@login_required
def student_handbook_list(request):
    """List all student handbooks"""
    handbooks = StudentHandbook.objects.all().order_by('-effective_date')
    
    # Get current handbook
    current_handbook = handbooks.filter(is_current=True).first()
    
    # Pagination
    paginator = Paginator(handbooks, 10)
    page = request.GET.get('page')
    handbooks = paginator.get_page(page)
    
    context = {
        'handbooks': handbooks,
        'current_handbook': current_handbook,
    }
    return render(request, 'directory/student_handbook_list.html', context)


@login_required
def student_handbook_detail(request, pk):
    """View student handbook details"""
    handbook = get_object_or_404(StudentHandbook, pk=pk)
    
    # Increment views
    handbook.views += 1
    handbook.save(update_fields=['views'])
    
    context = {
        'handbook': handbook,
    }
    return render(request, 'directory/student_handbook_detail.html', context)


def download_student_handbook(request, pk):
    """Download student handbook file"""
    handbook = get_object_or_404(StudentHandbook, pk=pk)
    
    # Increment download count
    handbook.downloads += 1
    handbook.save(update_fields=['downloads'])
    
    # Serve file
    response = FileResponse(handbook.file)
    response['Content-Disposition'] = f'attachment; filename="{handbook.file.name.split("/")[-1]}"'
    return response


@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff'])
def student_handbook_upload(request):
    """Upload student handbook (admin/staff only)"""
    if request.method == 'POST':
        form = StudentHandbookForm(request.POST, request.FILES)
        if form.is_valid():
            handbook = form.save(commit=False)
            handbook.uploaded_by = request.user
            handbook.save()
            
            messages.success(request, 'Student handbook uploaded successfully!')
            return redirect('directory:student_handbook_detail', pk=handbook.pk)
    else:
        form = StudentHandbookForm()
    
    return render(request, 'directory/student_handbook_upload.html', {'form': form})


@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def student_handbook_delete(request, pk):
    """Delete student handbook (admin only)"""
    handbook = get_object_or_404(StudentHandbook, pk=pk)
    handbook.delete()
    messages.success(request, 'Student handbook deleted successfully.')
    return redirect('directory:student_handbook_list')


# ========== ACADEMIC CALENDAR VIEWS ==========

def academic_calendar_list(request):
    """List academic calendar events"""
    events = AcademicCalendar.objects.filter(is_active=True)
    
    # Filter form
    filter_form = AcademicCalendarFilterForm(request.GET)
    if filter_form.is_valid():
        year = filter_form.cleaned_data.get('year')
        month = filter_form.cleaned_data.get('month')
        event_type = filter_form.cleaned_data.get('event_type')
        
        if year:
            events = events.filter(start_date__year=year)
        if month:
            events = events.filter(start_date__month=month)
        if event_type:
            events = events.filter(event_type=event_type)
    
    # Get upcoming events
    today = timezone.now().date()
    upcoming_events = events.filter(start_date__gte=today).order_by('start_date')[:10]
    
    # Get past events
    past_events = events.filter(start_date__lt=today).order_by('-start_date')[:10]
    
    # Get events by month for calendar view
    events_by_month = {}
    for event in events.order_by('start_date'):
        month_key = event.start_date.strftime('%Y-%m')
        if month_key not in events_by_month:
            events_by_month[month_key] = []
        events_by_month[month_key].append(event)
    
    # Get distinct years for filter
    years = events.dates('start_date', 'year').values_list('start_date__year', flat=True).distinct()
    filter_form.fields['year'].choices = [('', 'All Years')] + [(y, y) for y in years]
    
    context = {
        'events': events,
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'events_by_month': events_by_month,
        'filter_form': filter_form,
    }
    return render(request, 'directory/academic_calendar_list.html', context)


def academic_calendar_detail(request, pk):
    """View academic calendar event details"""
    event = get_object_or_404(AcademicCalendar, pk=pk, is_active=True)
    
    context = {
        'event': event,
    }
    return render(request, 'directory/academic_calendar_detail.html', context)


@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff'])
def academic_calendar_create(request):
    """Create academic calendar event (admin/staff only)"""
    if request.method == 'POST':
        form = AcademicCalendarForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            
            messages.success(request, 'Event created successfully!')
            return redirect('directory:academic_calendar_detail', pk=event.pk)
    else:
        form = AcademicCalendarForm()
    
    return render(request, 'directory/academic_calendar_form.html', {'form': form, 'action': 'Create'})


@login_required
@user_passes_test(lambda u: u.user_type in ['admin', 'staff'])
def academic_calendar_edit(request, pk):
    """Edit academic calendar event (admin/staff only)"""
    event = get_object_or_404(AcademicCalendar, pk=pk)
    
    if request.method == 'POST':
        form = AcademicCalendarForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully!')
            return redirect('directory:academic_calendar_detail', pk=event.pk)
    else:
        form = AcademicCalendarForm(instance=event)
    
    return render(request, 'directory/academic_calendar_form.html', {'form': form, 'action': 'Edit', 'event': event})


@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def academic_calendar_delete(request, pk):
    """Delete academic calendar event (admin only)"""
    event = get_object_or_404(AcademicCalendar, pk=pk)
    event.delete()
    messages.success(request, 'Event deleted successfully.')
    return redirect('directory:academic_calendar_list')


def academic_calendar_export(request):
    """Export academic calendar as CSV"""
    events = AcademicCalendar.objects.filter(is_active=True).order_by('start_date')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="academic_calendar.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Title', 'Type', 'Start Date', 'End Date', 'Academic Year', 'Semester', 'Level', 'Venue'])
    
    for event in events:
        writer.writerow([
            event.title,
            event.get_event_type_display(),
            event.start_date.strftime('%Y-%m-%d'),
            event.end_date.strftime('%Y-%m-%d') if event.end_date else '',
            event.academic_year,
            event.get_semester_display() if event.semester else '',
            event.get_level_display(),
            event.venue,
        ])
    
    return response


def academic_calendar_ical(request):
    """Export academic calendar as iCal file"""
    events = AcademicCalendar.objects.filter(is_active=True).order_by('start_date')
    
    ical_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//MELTSA-TaTU//Academic Calendar//EN\n"
    
    for event in events:
        start_date = event.start_date.strftime('%Y%m%d')
        end_date = event.end_date.strftime('%Y%m%d') if event.end_date else start_date
        
        ical_content += f"""
BEGIN:VEVENT
UID:{event.pk}@meltsa.edu
DTSTART;VALUE=DATE:{start_date}
DTEND;VALUE=DATE:{end_date}
SUMMARY:{event.title}
DESCRIPTION:{event.description}
LOCATION:{event.venue or ''}
END:VEVENT
"""
    
    ical_content += "END:VCALENDAR"
    
    response = HttpResponse(ical_content, content_type='text/calendar')
    response['Content-Disposition'] = 'attachment; filename="academic_calendar.ics"'
    return response