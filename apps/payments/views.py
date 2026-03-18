# payments/views.py
# payments/views.py
import json
import hashlib
import hmac
import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import Due, Payment, PaymentHistory
from apps.accounts.models import User, ActivityLog
from apps.core.models import AcademicSetting
from .forms import DueForm
import uuid

from django.db.models import Q

def due_list(request):
    """List all active dues"""
    current_academic = AcademicSetting.objects.filter(is_active=True).first()

    dues = Due.objects.filter(
        is_active=True,
        academic_setting=current_academic
    ).order_by('deadline')

    if request.user.is_authenticated and request.user.user_type in ['student', 'executive']:

        payments = Payment.objects.filter(
            student=request.user,
            status='success'
        )

        payment_map = {p.due_id: p for p in payments}

        for due in dues:
            payment = payment_map.get(due.id)
            due.paid = payment is not None
            due.payment_id = payment.id if payment else None

    context = {
        'dues': dues,
        'current_academic': current_academic,
    }

    return render(request, 'payments/due_list.html', context)

def due_detail(request, pk):
    """View due details"""
    due = get_object_or_404(Due, pk=pk, is_active=True)
    
    # Check if user has paid
    paid = False
    payment = None
    if request.user.is_authenticated and request.user.user_type in ['student', 'executive']:
        paid = Payment.objects.filter(
            student=request.user,
            due=due,
            status='success'
        ).first()
        
        paid = payment is not None
    
    # Get payment statistics (for admin/staff)
    if request.user.is_authenticated and request.user.user_type in ['admin', 'staff']:
        total_students = User.objects.filter(
            user_type='student',
            level__in=due.target_levels
        ).count()
        
        paid_count = Payment.objects.filter(
            due=due,
            status='success'
        ).values('student').distinct().count()
        
        total_collected = Payment.objects.filter(
            due=due,
            status='success'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        context = {
            'due': due,
            'paid': paid,
            'total_students': total_students,
            'paid_count': paid_count,
            'payment': payment,
            'total_collected': total_collected,
            'collection_rate': (paid_count / total_students * 100) if total_students > 0 else 0,
        }
    else:
        context = {'due': due, 'paid': paid, 'payment': payment}
    
    return render(request, 'payments/due_detail.html', context)

@login_required
def make_payment(request, due_id):
    """Initialize payment for a due"""
    if request.user.user_type not in ['student', 'executive']:
        messages.error(request, 'Only students can make payments.')
        return redirect('payments:due_list')
    
    # Executives are exempted from dues
    if request.user.user_type == 'executive':
        messages.info(request, 'Executives are exempted from paying dues.')
        return redirect('payments:due_list')
    
    due = get_object_or_404(Due, pk=due_id, is_active=True)
    
    # Check if already paid
    if Payment.objects.filter(student=request.user, due=due, status='success').exists():
        messages.info(request, 'You have already paid this due.')
        return redirect('payments:due_detail', pk=due.pk)
    
    # Check if deadline passed
    if due.deadline < timezone.now().date():
        messages.error(request, 'Payment deadline has passed.')
        return redirect('payments:due_detail', pk=due.pk)
    
    if request.method == 'POST':
        # Create payment record
        payment = Payment.objects.create(
            student=request.user,
            due=due,
            amount=due.amount,
            reference=f"MELTSA-{uuid.uuid4().hex[:10].upper()}",
            status='pending'
        )
        
        # Initialize Paystack payment
        # This would be handled by JavaScript on the frontend
        # We just pass the payment details to the template
        
        return render(request, 'payments/process_payment.html', {
            'payment': payment,
            'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        })
    
    return render(request, 'payments/confirm_payment.html', {'due': due})

@login_required
def verify_payment(request):
    """Verify payment after Paystack callback"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        reference = data.get('reference')
        due_id = data.get('due_id')
        
        # Here you would verify with Paystack API
        # This is a simplified example
        
        payment = get_object_or_404(
            Payment, 
            student=request.user,
            due_id=due_id,
            status='pending'
        )
        
        # Simulate verification (replace with actual Paystack verification)
        payment.status = 'success'
        payment.paystack_reference = reference
        payment.paid_at = timezone.now()
        payment.save()
        
        # Create payment history entry
        PaymentHistory.objects.create(
            payment=payment,
            status='success',
            notes='Payment verified successfully'
        )
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='payment',
            ip_address=get_client_ip(request),
            details={
                'due': payment.due.title,
                'amount': str(payment.amount),
                'reference': reference
            }
        )
        
        # Send email notification
        send_payment_confirmation_email(payment)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Payment verified successfully',
            'payment_id': payment.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def payment_history(request):
    """View user's payment history"""
    if request.user.user_type not in ['student', 'executive']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    payments = Payment.objects.filter(
        student=request.user
    ).select_related('due').order_by('-created_at')
    
    # Statistics
    total_paid = payments.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0
    payment_count = payments.filter(status='success').count()
    
    paginator = Paginator(payments, 20)
    page = request.GET.get('page')
    payments = paginator.get_page(page)
    
    context = {
        'payments': payments,
        'total_paid': total_paid,
        'payment_count': payment_count,
    }
    return render(request, 'payments/payment_history.html', context)

@login_required
def payment_receipt(request, pk):
    """View payment receipt"""
    payment = get_object_or_404(Payment, pk=pk)
    
    # Check if user can view (owner, admin, staff)
    if not (request.user == payment.student or 
            request.user.user_type in ['admin', 'staff']):
        messages.error(request, 'Access denied.')
        return redirect('payments:payment_history')
    
    return render(request, 'payments/payment_receipt.html', {'payment': payment})

@login_required
@staff_member_required
def due_create(request):
    """Create new due (staff/admin only)"""
    if request.method == 'POST':
        form = DueForm(request.POST)
        if form.is_valid():
            due = form.save(commit=False)
            due.created_by = request.user
            due.save()
            form.save_m2m()  # Save many-to-many relationships
            
            messages.success(request, f'Due "{due.title}" created successfully!')
            return redirect('payments:due_detail', pk=due.pk)
    else:
        form = DueForm()
    
    return render(request, 'payments/due_form.html', {'form': form, 'action': 'Create'})

@login_required
@staff_member_required
def due_edit(request, pk):
    """Edit due (staff/admin only)"""
    due = get_object_or_404(Due, pk=pk)
    
    if request.method == 'POST':
        form = DueForm(request.POST, instance=due)
        if form.is_valid():
            form.save()
            messages.success(request, f'Due "{due.title}" updated successfully!')
            return redirect('payments:due_detail', pk=due.pk)
    else:
        form = DueForm(instance=due)
    
    return render(request, 'payments/due_form.html', {
        'form': form, 
        'action': 'Edit',
        'due': due
    })

@login_required
@staff_member_required
def due_delete(request, pk):
    """Delete due (admin only)"""
    due = get_object_or_404(Due, pk=pk)
    
    if request.user.user_type != 'admin':
        messages.error(request, 'Only administrators can delete dues.')
        return redirect('payments:due_detail', pk=due.pk)
    
    if request.method == 'POST':
        due.delete()
        messages.success(request, f'Due "{due.title}" deleted successfully!')
        return redirect('payments:due_list')
    
    return render(request, 'payments/due_confirm_delete.html', {'due': due})

@login_required
@staff_member_required
def payment_reports(request):
    """View payment reports (staff/admin only)"""
    current_academic = AcademicSetting.objects.filter(is_active=True).first()
    
    # Summary statistics
    total_students = User.objects.filter(user_type='student').count()
    
    dues = Due.objects.filter(academic_setting=current_academic)
    
    report_data = []
    total_collected_all = 0
    total_paid_students = 0
    
    for due in dues:
        paid_count = Payment.objects.filter(
            due=due,
            status='success'
        ).values('student').distinct().count()
        
        total_collected = Payment.objects.filter(
            due=due,
            status='success'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_collected_all += total_collected
        total_paid_students = max(total_paid_students, paid_count)
        
        report_data.append({
            'due': due,
            'paid_count': paid_count,
            'total_collected': total_collected,
            'rate': (paid_count / total_students * 100) if total_students > 0 else 0,
        })
    
    # Payments by level
    payments_by_level = Payment.objects.filter(
        due__academic_setting=current_academic,
        status='success'
    ).values('student__level').annotate(
        count=Count('student', distinct=True),
        total=Sum('amount')
    ).order_by('student__level')
    
    context = {
        'report_data': report_data,
        'total_students': total_students,
        'total_paid_students': total_paid_students,
        'total_collected': total_collected_all,
        'payments_by_level': payments_by_level,
        'current_academic': current_academic,
    }
    return render(request, 'payments/payment_reports.html', context)

@login_required
@staff_member_required
def export_payments(request):
    """Export payments to CSV (staff/admin only)"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payments.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Student ID', 'Student Name', 'Due', 'Amount', 
        'Status', 'Reference', 'Date', 'Paystack Reference'
    ])
    
    payments = Payment.objects.select_related('student', 'due').order_by('-created_at')
    
    for payment in payments:
        writer.writerow([
            payment.student.student_id or '',
            payment.student.get_full_name(),
            payment.due.title,
            payment.amount,
            payment.get_status_display(),
            payment.reference,
            payment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            payment.paystack_reference or ''
        ])
    
    return response

@login_required
def export_unpaid(request):
    """Export students who have not paid a specific due"""
    
    due_id = request.GET.get('due')
    due = Due.objects.get(id=due_id)

    # Students who paid
    paid_students = Payment.objects.filter(due=due).values_list('student_id', flat=True)

    # Students who have not paid
    unpaid_students = User.objects.filter(user_type='student').exclude(id__in=paid_students)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="unpaid_students_{due.id}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Student ID', 'Name', 'Email'])

    for student in unpaid_students:
        writer.writerow([
            student.student_id,
            student.get_full_name(),
            student.email
        ])

    return response



@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Handle Paystack webhook"""
    # Verify webhook signature
    signature = request.headers.get('x-paystack-signature')
    if not signature:
        return HttpResponse(status=400)
    
    # Compute expected signature
    payload = request.body
    expected_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()
    
    if signature != expected_signature:
        return HttpResponse(status=400)
    
    # Process webhook
    data = json.loads(payload)
    event = data.get('event')
    
    if event == 'charge.success':
        # Get payment reference
        reference = data['data']['reference']
        
        try:
            payment = Payment.objects.get(reference=reference)
            payment.status = 'success'
            payment.paystack_reference = data['data']['id']
            payment.paid_at = timezone.now()
            payment.save()
            
            # Create payment history
            PaymentHistory.objects.create(
                payment=payment,
                status='success',
                notes='Payment verified via webhook'
            )
            
            # Log activity
            ActivityLog.objects.create(
                user=payment.student,
                action_type='payment',
                ip_address='webhook',
                details={
                    'due': payment.due.title,
                    'amount': str(payment.amount),
                    'reference': reference
                }
            )
            
            # Send email
            send_payment_confirmation_email(payment)
            
        except Payment.DoesNotExist:
            # Log but don't raise error
            pass
    
    return HttpResponse(status=200)

def send_payment_confirmation_email(payment):
    """Send payment confirmation email"""
    subject = f'Payment Confirmation - {payment.due.title}'
    message = render_to_string('emails/payment_confirmation.html', {
        'payment': payment,
        'student': payment.student,
    })
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [payment.student.email],
        fail_silently=True,
    )

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.accounts.models import User
from .models import Payment

@login_required
def student_payment(request, student_id):
    """View payments made by a specific student"""
    student = get_object_or_404(User, pk=student_id, user_type='student')
    
    payments = Payment.objects.filter(student=student).order_by('-created_at')
    
    context = {
        'student': student,
        'payments': payments,
    }
    return render(request, 'payments/student_payment.html', context)
  



# apps/payments/views.py

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .paystack import paystack
import uuid

@login_required
def initialize_payment(request, due_id):
    due = get_object_or_404(Due, id=due_id, is_active=True)
    
    # Generate unique reference
    reference = f"MELTSA-{uuid.uuid4().hex[:10].upper()}"
    
    # Prepare metadata
    metadata = {
        "user_id": request.user.id,
        "user_email": request.user.email,
        "due_id": due.id,
        "due_title": due.title
    }
    
    # Initialize transaction
    response = paystack.initialize_transaction(
        email=request.user.email,
        amount=float(due.amount),
        reference=reference,
        callback_url=request.build_absolute_uri('/payments/verify/'),
        metadata=metadata
    )
    
    if response['status']:
        # Create payment record (pending)
        payment = Payment.objects.create(
            student=request.user,
            due=due,
            amount=due.amount,
            reference=reference,
            status='pending'
        )
        
        # Redirect to Paystack payment page
        return redirect(response['data']['authorization_url'])
    else:
        messages.error(request, f"Payment initialization failed: {response.get('message', 'Unknown error')}")
        return redirect('payments:due_detail', pk=due_id)
# apps/payments/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

@login_required
def cancel_payment(request, reference):
    """Cancel payment"""
    try:
        payment = Payment.objects.get(reference=reference, student=request.user)
        payment.status = 'failed'
        payment.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='payment',
            ip_address=get_client_ip(request),
            details={
                'due': payment.due.title,
                'amount': str(payment.amount),
                'reference': reference,
                'status': 'cancelled'
            }
        )
        
        messages.warning(request, 'Payment was cancelled.')
    except Payment.DoesNotExist:
        messages.error(request, 'Payment record not found.')
    
    return render(request, 'payments/cancel_payment.html', {'reference': reference})