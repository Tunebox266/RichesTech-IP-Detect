# complaints/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q, Count 
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Complaint, ComplaintResponse
from apps.accounts.models import User, ActivityLog
from .forms import ComplaintForm, ComplaintResponseForm, ComplaintStatusForm
import csv

@login_required
def complaint_list(request):
    """List all complaints (for staff/executive)"""
    if request.user.user_type not in ['admin', 'staff', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    complaints = Complaint.objects.all().select_related('student').order_by('-created_at')
    
    # Filters
    status = request.GET.get('status')
    if status:
        complaints = complaints.filter(status=status)
    
    type_filter = request.GET.get('type')
    if type_filter:
        complaints = complaints.filter(complaint_type=type_filter)
    
    search = request.GET.get('search')
    if search:
        complaints = complaints.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(student__first_name__icontains=search) |
            Q(student__last_name__icontains=search)
        )
    
    paginator = Paginator(complaints, 20)
    page = request.GET.get('page')
    complaints = paginator.get_page(page)
    
    # Statistics
    stats = {
        'total': Complaint.objects.count(),
        'pending': Complaint.objects.filter(status='pending').count(),
        'under_review': Complaint.objects.filter(status='under_review').count(),
        'resolved': Complaint.objects.filter(status='resolved').count(),
    }
    
    context = {
        'complaints': complaints,
        'stats': stats,
        'status_choices': Complaint.STATUS_CHOICES,
        'type_choices': Complaint.COMPLAINT_TYPES,
        'current_filters': {
            'status': status,
            'type': type_filter,
            'search': search,
        }
    }
    return render(request, 'complaints/complaint_list.html', context)

@login_required
def my_complaints(request):
    """List current user's complaints"""
    complaints = Complaint.objects.filter(
        student=request.user
    ).order_by('-created_at')
    
    paginator = Paginator(complaints, 10)
    page = request.GET.get('page')
    complaints = paginator.get_page(page)
    
    context = {
        'complaints': complaints,
        'is_my_complaints': True,
    }
    return render(request, 'complaints/my_complaints.html', context)

@login_required
def complaint_detail(request, pk):
    """View complaint details"""
    complaint = get_object_or_404(Complaint, pk=pk)
    
    # Check permissions
    if not (request.user == complaint.student or 
            request.user.user_type in ['admin', 'staff', 'executive']):
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    # Get responses
    responses = complaint.responses.select_related('responder').order_by('created_at')
    
    # Response form (for staff/executive)
    response_form = None
    status_form = None
    if request.user.user_type in ['admin', 'staff', 'executive']:
        if request.method == 'POST' and 'respond' in request.POST:
            response_form = ComplaintResponseForm(request.POST, request.FILES)
            if response_form.is_valid():
                response = response_form.save(commit=False)
                response.complaint = complaint
                response.responder = request.user
                response.save()
                
                # Update complaint status if needed
                if complaint.status == 'pending':
                    complaint.status = 'under_review'
                    complaint.save()
                
                messages.success(request, 'Response added successfully!')
                return redirect('complaints:complaint_detail', pk=complaint.pk)
        else:
            response_form = ComplaintResponseForm()
        
        status_form = ComplaintStatusForm(instance=complaint)
    
    context = {
        'complaint': complaint,
        'responses': responses,
        'response_form': response_form,
        'status_form': status_form,
        'can_respond': request.user.user_type in ['admin', 'staff', 'executive'],
        'is_owner': request.user == complaint.student,
    }
    return render(request, 'complaints/complaint_detail.html', context)

@login_required
def submit_complaint(request):
    """Submit a new complaint"""
    if request.method == 'POST':
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.student = request.user
            complaint.save()
            
            messages.success(request, 'Complaint submitted successfully!')
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action_type='complaint',
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'complaint_id': complaint.id, 'type': complaint.complaint_type}
            )
            
            return redirect('complaints:my_complaints')
    else:
        form = ComplaintForm()
    
    return render(request, 'complaints/submit_complaint.html', {'form': form})

@login_required
def respond_to_complaint(request, pk):
    """Add response to complaint (staff/executive only)"""
    complaint = get_object_or_404(Complaint, pk=pk)
    
    if request.user.user_type not in ['admin', 'staff', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('complaints:complaint_detail', pk=pk)
    
    if request.method == 'POST':
        form = ComplaintResponseForm(request.POST, request.FILES)
        if form.is_valid():
            response = form.save(commit=False)
            response.complaint = complaint
            response.responder = request.user
            response.save()
            
            # Update complaint status
            if complaint.status == 'pending':
                complaint.status = 'under_review'
                complaint.save()
            
            messages.success(request, 'Response added successfully!')
    
    return redirect('complaints:complaint_detail', pk=pk)

@login_required
def update_complaint_status(request, pk):
    """Update complaint status (staff/executive only)"""
    complaint = get_object_or_404(Complaint, pk=pk)
    
    if request.user.user_type not in ['admin', 'staff', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('complaints:complaint_detail', pk=pk)
    
    if request.method == 'POST':
        form = ComplaintStatusForm(request.POST, instance=complaint)
        if form.is_valid():
            form.save()
            messages.success(request, f'Complaint status updated to {complaint.get_status_display()}')
    
    return redirect('complaints:complaint_detail', pk=pk)

@login_required
def manage_complaints(request):
    """Manage complaints dashboard (staff/admin only)"""
    if request.user.user_type not in ['admin', 'staff']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    # Statistics
    total_complaints = Complaint.objects.count()
    
    by_status = Complaint.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    by_type = Complaint.objects.values('complaint_type').annotate(
        count=Count('id')
    ).order_by('complaint_type')
    
    # Response time statistics
    resolved_complaints = Complaint.objects.filter(status='resolved')
    avg_response_time = 0
    if resolved_complaints.exists():
        total_time = sum(
            (c.updated_at - c.created_at).total_seconds() 
            for c in resolved_complaints
        )
        avg_response_time = total_time / resolved_complaints.count() / 3600  # hours
    
    # Recent complaints
    recent = Complaint.objects.select_related('student').order_by('-created_at')[:10]
    
    context = {
        'total_complaints': total_complaints,
        'by_status': by_status,
        'by_type': by_type,
        'avg_response_time': round(avg_response_time, 1),
        'recent_complaints': recent,
    }
    return render(request, 'complaints/manage.html', context)

@login_required
def export_complaints(request):
    """Export complaints to CSV (staff/admin only)"""
    if request.user.user_type not in ['admin', 'staff']:
        messages.error(request, 'Access denied.')
        return redirect('complaints:complaint_list')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="complaints.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Student', 'Student ID', 'Type', 'Title', 
        'Status', 'Created', 'Updated', 'Response Count'
    ])
    
    complaints = Complaint.objects.select_related('student').annotate(
        response_count=Count('responses')
    )
    
    for complaint in complaints:
        writer.writerow([
            complaint.id,
            complaint.student.get_full_name(),
            complaint.student.student_id or '',
            complaint.get_complaint_type_display(),
            complaint.title,
            complaint.get_status_display(),
            complaint.created_at.strftime('%Y-%m-%d %H:%M'),
            complaint.updated_at.strftime('%Y-%m-%d %H:%M'),
            complaint.response_count
        ])
    
    return response

@login_required
def complaint_stats(request):
    """AJAX endpoint for complaint statistics"""
    if request.user.user_type not in ['admin', 'staff', 'executive']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    stats = {
        'total': Complaint.objects.count(),
        'pending': Complaint.objects.filter(status='pending').count(),
        'under_review': Complaint.objects.filter(status='under_review').count(),
        'resolved': Complaint.objects.filter(status='resolved').count(),
    }
    
    # Monthly trend (last 6 months)
    from django.db.models import Count
    from django.db.models.functions import TruncMonth
    
    six_months_ago = timezone.now() - timezone.timedelta(days=180)
    monthly = Complaint.objects.filter(
        created_at__gte=six_months_ago
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    stats['monthly'] = list(monthly)
    
    return JsonResponse(stats)