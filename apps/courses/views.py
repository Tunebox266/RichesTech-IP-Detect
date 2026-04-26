# courses/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
import csv
import os
from .models import Course, CourseRegistration, CourseMaterial, MaterialComment, MaterialReport
from apps.accounts.models import User, ActivityLog
from apps.core.models import AcademicSetting
from .forms import CourseForm, CourseMaterialForm, CourseRegistrationForm, MaterialCommentForm

@login_required
def course_list(request):
    """List all courses"""
    courses = Course.objects.filter(is_active=True)
    
    # Filters
    level = request.GET.get('level')
    if level:
        courses = courses.filter(level=level)
    
    semester = request.GET.get('semester')
    if semester:
        courses = courses.filter(semester=semester)
    
    search = request.GET.get('search')
    if search:
        courses = courses.filter(
            Q(code__icontains=search) |
            Q(title__icontains=search)
        )
    
    paginator = Paginator(courses, 20)
    page = request.GET.get('page')
    courses = paginator.get_page(page)
    
    context = {
        'courses': courses,
        'levels': Course.LEVEL_CHOICES,
        'semesters': Course.SEMESTER_CHOICES,
    }
    return render(request, 'courses/course_list.html', context)
@login_required
def course_detail(request, pk):
    """View course details"""
    course = get_object_or_404(Course, pk=pk, is_active=True)
    
    # Get materials for this course
    materials = CourseMaterial.objects.filter(course=course).order_by('-uploaded_at')
    
    # Course statistics
    registered_students = CourseRegistration.objects.filter(course=course).count()

    total_materials = materials.count()

    total_downloads = materials.aggregate(
        total=Sum('download_count')
    )['total'] or 0
    # Check if current user is registered
    current_academic = AcademicSetting.objects.filter(is_active=True).first()

    is_registered = False
    if request.user.is_authenticated and request.user.user_type in ['student', 'executive']:
       is_registered = CourseRegistration.objects .filter(
         student=request.user,
         course=course,
         academic_setting=current_academic
      ).exists()
    
    context = {
        'course': course,
        'materials': materials,
        'is_registered': is_registered,
         'registered_students': CourseRegistration.objects.filter(course=course).count(),
         'total_materials': materials.count(),
         'total_downloads': total_downloads,
    }
    return render(request, 'courses/course_detail.html', context)

@login_required
def my_courses(request):
    """View registered courses for current student"""
    if request.user.user_type not in ['student', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    current_academic = AcademicSetting.objects.filter(is_active=True).first()
    
    registrations = CourseRegistration.objects.filter(
        student=request.user,
        academic_setting=current_academic
    ).select_related('course').order_by('course__code')
    
    registered_courses = registrations.count()
    
    # Group by semester
    first_semester = registrations.filter(course__semester=1)
    second_semester = registrations.filter(course__semester=2)
    
    context = {
         'registrations': registrations,
        'registered_courses': registered_courses,
        'first_semester': first_semester,
        'second_semester': second_semester,
        'current_academic': current_academic,
        'total_credits': sum(r.course.credit_hours for r in registrations),
    }
    return render(request, 'courses/my_courses.html', context)

@login_required
def register_courses(request):
    """Register for courses"""
    if request.user.user_type not in ['student', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    current_academic = AcademicSetting.objects.filter(is_active=True).first()
    
    # Get already registered courses
    registered = CourseRegistration.objects.filter(
        student=request.user,
        academic_setting=current_academic
    ).values_list('course_id', flat=True)
    
    # Get available courses for student's level
    available_courses = Course.objects.filter(
        level=request.user.level,
        semester=current_academic.current_semester,
        is_active=True
    ).exclude(id__in=registered)
    
    if request.method == 'POST':
        selected_courses = request.POST.getlist('courses')
        
        if selected_courses:
            created = 0
            for course_id in selected_courses:
                course = Course.objects.get(id=course_id)
                registration, created_flag = CourseRegistration.objects.get_or_create(
                    student=request.user,
                    course=course,
                    academic_setting=current_academic,
                    defaults={'registered_by': request.user}
                )
                if created_flag:
                    created += 1
            
            messages.success(request, f'Successfully registered for {created} courses!')
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action_type='course_registration',
                ip_address=get_client_ip(request),
                details={'courses': list(selected_courses)}
            )
            
            return redirect('courses:my_courses')
        else:
            messages.warning(request, 'No courses selected.')
    
    context = {
        'available_courses': available_courses,
        'current_academic': current_academic,
        'registered_count': len(registered),
    }
    return render(request, 'courses/register_courses.html', context)

@login_required
def registered_course_detail(request, pk):
    """View details of a registered course"""
    registration = get_object_or_404(
        CourseRegistration, 
        pk=pk, 
        student=request.user
    )
    
    # Get materials for this course
    materials = CourseMaterial.objects.filter(
        course=registration.course
    ).order_by('-uploaded_at')
    
    context = {
        'registration': registration,
        'materials': materials,
    }
    return render(request, 'courses/registered_course_detail.html', context)

@login_required
def material_list(request):
    """List all course materials"""
    materials = CourseMaterial.objects.select_related(
        'course', 'uploaded_by'
    ).order_by('-uploaded_at')
    
    # Filters
    course_id = request.GET.get('course')
    if course_id:
        materials = materials.filter(course_id=course_id)
    
    material_type = request.GET.get('type')
    if material_type:
        materials = materials.filter(material_type=material_type)
    
    level = request.GET.get('level')
    if level:
        materials = materials.filter(course__level=level)
    
    search = request.GET.get('search')
    if search:
        materials = materials.filter(
            Q(title__icontains=search) |
            Q(course__title__icontains=search) |
            Q(course__code__icontains=search)
        )
    
    paginator = Paginator(materials, 20)
    page = request.GET.get('page')
    materials = paginator.get_page(page)
    
    context = {
        'materials': materials,
        'courses': Course.objects.all(),
        'material_types': CourseMaterial.MATERIAL_TYPES,
    }
    return render(request, 'courses/material_list.html', context)
@login_required
def material_detail(request, pk):
    """View material details"""
    material = get_object_or_404(CourseMaterial, pk=pk)
    
    # Check if user can access (registered students, staff, admin)
    can_access = False
    if request.user.is_authenticated:
        if request.user.user_type in ['admin', 'staff']:
            can_access = True
        elif request.user.user_type in ['student', 'executive']:
            can_access = CourseRegistration.objects.filter(
                student=request.user,
                course=material.course,
                academic_setting=AcademicSetting.objects.filter(is_active=True).first()
            ).exists()
    
    context = {
        'material': material,
        'can_access': can_access,
    }
    return render(request, 'courses/material_detail.html', context)

import os
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import FileResponse
from django.contrib.auth.decorators import login_required

#from .utils import get_client_ip  # your existing helper

@login_required
def download_material(request, pk):
    """Download course material with permission checks, logging, and download count"""
    material = get_object_or_404(CourseMaterial, pk=pk)
    
    # Check permissions
    if request.user.user_type in ['admin', 'staff']:
        pass  # full access
    elif request.user.user_type in ['student', 'executive']:
        active_setting = AcademicSetting.objects.filter(is_active=True).first()
        registered = CourseRegistration.objects.filter(
            student=request.user,
            course=material.course,
            academic_setting=active_setting
        ).exists()
        
        if not registered:
            messages.error(request, 'You must be registered for this course to download materials.')
            return redirect('courses:material_detail', pk=pk)
    else:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    # Increment download count
    material.downloads = material.downloads + 1 if hasattr(material, 'downloads') else 1
    material.save()
    
    # Log activity
    ActivityLog.objects.create(
        user=request.user,
        action_type='file_download',
        ip_address=get_client_ip(request),
        details={'action': 'download', 'material': material.title}
    )
    
    # Serve file as download
    if material.file and os.path.exists(material.file.path):
        response = FileResponse(material.file.open('rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(material.file.name)}"'
        return response
    else:
        messages.error(request, 'File not found.')
        return redirect('courses:material_detail', pk=pk)


@login_required
@staff_member_required
def upload_material(request):
    """Upload course material (staff/admin only)"""
    if request.method == 'POST':
        form = CourseMaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.uploaded_by = request.user
            material.save()
            
            messages.success(request, 'Material uploaded successfully!')
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action_type='file_upload',
                ip_address=get_client_ip(request),
                details={'action': 'upload', 'material': material.title}
            )
            
            return redirect('courses:material_detail', pk=material.pk)
    else:
        form = CourseMaterialForm()
    
    return render(request, 'courses/upload_material.html', {'form': form})

from .models import CourseMaterial, MaterialReport

@login_required
def report_material(request, pk):
    """Report a material issue"""
    material = get_object_or_404(CourseMaterial, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if reason:
            MaterialReport.objects.create(
                material=material,
                reported_by=request.user,
                reason=reason
            )
            messages.success(request, "Material reported successfully!")
        else:
            messages.error(request, "Please provide a reason to report.")
    
    return redirect('courses:material_detail', pk=material.pk)


@login_required
@staff_member_required
def course_create(request):
    """Create new course (staff/admin only)"""
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(request, f'Course {course.code} created successfully!')
            return redirect('courses:course_detail', pk=course.pk)
    else:
        form = CourseForm()
    
    return render(request, 'courses/course_form.html', {'form': form, 'action': 'Create'})

@login_required
@staff_member_required
def course_edit(request, pk):
    """Edit course (staff/admin only)"""
    course = get_object_or_404(Course, pk=pk)
    
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, f'Course {course.code} updated successfully!')
            return redirect('courses:course_detail', pk=course.pk)
    else:
        form = CourseForm(instance=course)
    
    return render(request, 'courses/course_form.html', {
        'form': form, 
        'action': 'Edit',
        'course': course
    })

@login_required
def course_students(request, pk):
    course = get_object_or_404(Course, pk=pk)

    students = course.students.all() if hasattr(course, "students") else []

    return render(request, "courses/course_students.html", {
        "course": course,
        "students": students
    })

# Create new material (staff/admin only)
@login_required
def create_material(request):
    if request.user.user_type not in ['staff','admin']:
        return HttpResponseForbidden("You cannot add material.")
    
    if request.method == "POST":
        form = CourseMaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.uploaded_by = request.user
            material.save()
            messages.success(request, "Material added successfully.")
            return redirect("courses:material_detail", pk=material.id)
    else:
        form = CourseMaterialForm()
    
    return render(request, "courses/material_form.html", {"form": form, "action": "Create"})


# Edit material (staff/admin or uploader)
@login_required
def edit_material(request, pk):
    material = get_object_or_404(CourseMaterial, pk=pk)

    if request.user.user_type not in ['staff','admin'] and request.user != material.uploaded_by:
        return HttpResponseForbidden("You cannot edit this material.")

    if request.method == "POST":
        form = CourseMaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, "Material updated successfully.")
            return redirect("courses:material_detail", pk=material.id)
    else:
        form = CourseMaterialForm(instance=material)

    return render(request, "courses/material_form.html", {"form": form, "action": "Edit"})


@login_required
def add_material_comment(request, pk):
    """Add comment to a material"""
    material = get_object_or_404(CourseMaterial, pk=pk)

    # Only students in course or staff/admin can comment
    if request.user.user_type not in ['staff','admin'] and not material.course.students.filter(id=request.user.id).exists():
        return HttpResponseForbidden("You cannot comment on this material.")

    if request.method == "POST":
        form = MaterialCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.material = material
            comment.user = request.user
            comment.save()
            return redirect("courses:material_detail", pk=material.id)

    return redirect("courses:material_detail", pk=material.id)

@login_required
@staff_member_required
def course_delete(request, pk):
    """Delete course (admin only)"""
    course = get_object_or_404(Course, pk=pk)
    
    if request.user.user_type != 'admin':
        messages.error(request, 'Only administrators can delete courses.')
        return redirect('courses:course_detail', pk=pk)
    
    if request.method == 'POST':
        course.delete()
        messages.success(request, f'Course {course.code} deleted successfully!')
        return redirect('courses:course_list')
    
    return render(request, 'courses/course_confirm_delete.html', {'course': course})

@login_required
@staff_member_required
def bulk_upload_courses(request):
    """Bulk upload courses via CSV (staff/admin only)"""
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        
        if file.name.endswith('.csv'):
            decoded_file = file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            created = 0
            for row in reader:
                try:
                    course, created_flag = Course.objects.get_or_create(
                        code=row['code'],
                        defaults={
                            'title': row['title'],
                            'level': row['level'],
                            'semester': row['semester'],
                            'credit_hours': row.get('credit_hours', 3),
                            'description': row.get('description', '')
                        }
                    )
                    if created_flag:
                        created += 1
                except Exception as e:
                    messages.error(request, f'Error creating course {row.get("code")}: {str(e)}')
            
            messages.success(request, f'{created} courses created successfully!')
            return redirect('courses:course_list')
    
    return render(request, 'courses/bulk_upload.html')

@login_required
@staff_member_required
def export_courses(request):
    """Export courses to CSV (staff/admin only)"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="courses.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Code', 'Title', 'Level', 'Semester', 'Credit Hours', 'Description'])
    
    courses = Course.objects.all()
    for course in courses:
        writer.writerow([
            course.code,
            course.title,
            course.get_level_display(),
            course.get_semester_display(),
            course.credit_hours,
            course.description
        ])
    
    return response

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip