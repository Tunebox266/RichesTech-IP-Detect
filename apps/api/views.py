# api/views.py
from rest_framework import viewsets, status, generics, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.shortcuts import get_object_or_404
import qrcode
from io import BytesIO
import base64

from apps.accounts.models import User, StudentExecutive, ActivityLog
from apps.courses.models import Course, CourseRegistration, CourseMaterial
from apps.payments.models import Due, Payment
from apps.events.models import Event, EventAttendee, AttendanceSession, AttendanceRecord
from apps.messaging.models import Message, Broadcast, Complaint, ComplaintResponse
from apps.core.models import Announcement, AcademicSetting

from .serializers import (
    # Auth serializers
    UserSerializer, UserDetailSerializer, UserCreateSerializer,
    LoginSerializer, ChangePasswordSerializer,
    
    # Course serializers
    CourseSerializer, CourseDetailSerializer, CourseRegistrationSerializer,
    CourseMaterialSerializer,
    
    # Payment serializers
    DueSerializer, DueDetailSerializer, PaymentSerializer, PaymentInitSerializer,
    
    # Event serializers
    EventSerializer, EventDetailSerializer, EventAttendeeSerializer,
    AttendanceSessionSerializer, AttendanceRecordSerializer,
    
    # Announcement serializers
    AnnouncementSerializer,
    
    # Messaging serializers
    MessageSerializer, MessageDetailSerializer, BroadcastSerializer,
    ComplaintSerializer, ComplaintDetailSerializer,
    
    # Directory serializers
    StudentDirectorySerializer,
    
    # Dashboard serializers
    StudentDashboardSerializer, AdminDashboardSerializer,
)


# ========== CUSTOM PAGINATION ==========

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ========== USER VIEWSETS ==========

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for users
    """
    queryset = User.objects.all().order_by('-date_joined')
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email', 'student_id', 'staff_id']
    ordering_fields = ['date_joined', 'last_login', 'level']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'retrieve':
            return UserDetailSerializer
        return UserSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAdminUser]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get'])
    def students(self, request):
        """Get all students"""
        students = self.get_queryset().filter(user_type='student')
        page = self.paginate_queryset(students)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(students, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def executives(self, request):
        """Get all executives"""
        executives = self.get_queryset().filter(user_type='executive')
        page = self.paginate_queryset(executives)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(executives, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def staff(self, request):
        """Get all staff"""
        staff = self.get_queryset().filter(user_type='staff')
        page = self.paginate_queryset(staff)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(staff, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a user (admin only)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'status': 'user deactivated'})


# ========== COURSE VIEWSETS ==========

class CourseViewSet(viewsets.ModelViewSet):
    """
    API endpoint for courses
    """
    queryset = Course.objects.all().order_by('code')
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'title']
    ordering_fields = ['code', 'level', 'semester']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['get'])
    def materials(self, request, pk=None):
        """Get course materials"""
        course = self.get_object()
        materials = course.materials.all()
        serializer = CourseMaterialSerializer(materials, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def registered_students(self, request, pk=None):
        """Get students registered for this course"""
        course = self.get_object()
        registrations = course.registrations.select_related('student')
        students = [reg.student for reg in registrations]
        serializer = UserSerializer(students, many=True)
        return Response(serializer.data)


# ========== DUE VIEWSETS ==========

class DueViewSet(viewsets.ModelViewSet):
    """
    API endpoint for dues
    """
    queryset = Due.objects.all().order_by('-deadline')
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['deadline', 'amount', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DueDetailSerializer
        return DueSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        """Get payments for this due"""
        due = self.get_object()
        payments = due.payments.all()
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active dues for current academic setting"""
        current_academic = AcademicSetting.objects.filter(is_active=True).first()
        if current_academic:
            dues = self.queryset.filter(
                academic_setting=current_academic,
                is_active=True
            )
        else:
            dues = self.queryset.none()
        serializer = self.get_serializer(dues, many=True)
        return Response(serializer.data)


# ========== PAYMENT VIEWSETS ==========

class PaymentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for payments
    """
    queryset = Payment.objects.all().order_by('-created_at')
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference', 'student__first_name', 'student__last_name']
    ordering_fields = ['created_at', 'amount', 'status']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentInitSerializer
        return PaymentSerializer
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'student':
            return self.queryset.filter(student=user)
        return self.queryset
    
    @action(detail=False, methods=['get'])
    def my_payments(self, request):
        """Get current user's payments"""
        payments = self.queryset.filter(student=request.user)
        serializer = self.get_serializer(payments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify payment (admin only)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        payment = self.get_object()
        payment.status = 'success'
        payment.paid_at = timezone.now()
        payment.save()
        return Response({'status': 'payment verified'})


# ========== ANNOUNCEMENT VIEWSETS ==========

class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    API endpoint for announcements
    """
    queryset = Announcement.objects.all().order_by('-created_at')
    serializer_class = AnnouncementSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'priority']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent announcements"""
        recent = self.queryset[:10]
        serializer = self.get_serializer(recent, many=True)
        return Response(serializer.data)


# ========== EVENT VIEWSETS ==========

class EventViewSet(viewsets.ModelViewSet):
    """
    API endpoint for events
    """
    queryset = Event.objects.all().order_by('-start_date')
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'venue']
    ordering_fields = ['start_date', 'end_date', 'event_type']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EventDetailSerializer
        return EventSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def register(self, request, pk=None):
        """Register for an event"""
        event = self.get_object()
        
        # Check if already registered
        if EventAttendee.objects.filter(event=event, user=request.user).exists():
            return Response(
                {'error': 'Already registered for this event'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Register
        attendee = EventAttendee.objects.create(
            event=event,
            user=request.user
        )
        
        serializer = EventAttendeeSerializer(attendee)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def unregister(self, request, pk=None):
        """Unregister from an event"""
        event = self.get_object()
        
        try:
            attendee = EventAttendee.objects.get(event=event, user=request.user)
            attendee.delete()
            return Response({'status': 'unregistered'})
        except EventAttendee.DoesNotExist:
            return Response(
                {'error': 'Not registered for this event'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def attendees(self, request, pk=None):
        """Get event attendees"""
        event = self.get_object()
        attendees = event.attendees.all()
        serializer = EventAttendeeSerializer(attendees, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming events"""
        upcoming = self.queryset.filter(
            start_date__gte=timezone.now(),
            is_active=True
        )[:10]
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)


# ========== MESSAGE VIEWSETS ==========

class MessageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for messages
    """
    queryset = Message.objects.all().order_by('-sent_at')
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['subject', 'body']
    ordering_fields = ['sent_at', 'read_at']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MessageDetailSerializer
        return MessageSerializer
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(
            Q(sender=user) | Q(recipient=user)
        ).distinct()
    
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)
    
    @action(detail=False, methods=['get'])
    def inbox(self, request):
        """Get received messages"""
        messages = self.queryset.filter(recipient=request.user)
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def sent(self, request):
        """Get sent messages"""
        messages = self.queryset.filter(sender=request.user)
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread messages count"""
        count = self.queryset.filter(
            recipient=request.user,
            read_at__isnull=True
        ).count()
        return Response({'unread_count': count})
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark message as read"""
        message = self.get_object()
        message.mark_as_read()
        return Response({'status': 'marked as read'})


# ========== COMPLAINT VIEWSETS ==========

class ComplaintViewSet(viewsets.ModelViewSet):
    """
    API endpoint for complaints
    """
    queryset = Complaint.objects.all().order_by('-created_at')
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['subject', 'description']
    ordering_fields = ['created_at', 'status', 'complaint_type']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ComplaintDetailSerializer
        return ComplaintSerializer
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'staff', 'executive']:
            return self.queryset
        return self.queryset.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_complaints(self, request):
        """Get current user's complaints"""
        complaints = self.queryset.filter(user=request.user)
        serializer = self.get_serializer(complaints, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """Respond to complaint (staff/executive only)"""
        complaint = self.get_object()
        
        if request.user.user_type not in ['admin', 'staff', 'executive']:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        response = ComplaintResponse.objects.create(
            complaint=complaint,
            responder=request.user,
            content=request.data.get('content', '')
        )
        
        complaint.status = 'under_review'
        complaint.assigned_to = request.user
        complaint.save()
        
        return Response({'status': 'response added'})


# ========== ATTENDANCE VIEWSET ==========

class AttendanceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for attendance
    """
    queryset = AttendanceRecord.objects.all().order_by('-checked_in_at')
    serializer_class = AttendanceRecordSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'staff']:
            return self.queryset
        return self.queryset.filter(user=user)
    
    @action(detail=False, methods=['post'])
    def check_in(self, request):
        """Check in to a session using QR code or code"""
        session_code = request.data.get('session_code')
        
        try:
            session = AttendanceSession.objects.get(session_code=session_code)
            
            # Check if already checked in
            if AttendanceRecord.objects.filter(
                session=session,
                user=request.user
            ).exists():
                return Response(
                    {'error': 'Already checked in'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if session is active
            if not session.is_active_now():
                return Response(
                    {'error': 'Session not active'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create attendance record
            record = AttendanceRecord.objects.create(
                session=session,
                user=request.user,
                check_in_method='qr_code',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            serializer = self.get_serializer(record)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except AttendanceSession.DoesNotExist:
            return Response(
                {'error': 'Invalid session code'},
                status=status.HTTP_400_BAD_REQUEST
            )


# ========== AUTHENTICATION VIEWS ==========

@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """API login endpoint"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                
                # Log activity
                ActivityLog.objects.create(
                    user=user,
                    action_type='login',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details={'via': 'api'}
                )
                
                return Response({
                    'success': True,
                    'user': UserSerializer(user).data,
                    'requires_password_change': user.requires_password_change
                })
            else:
                return Response(
                    {'error': 'Account is disabled'},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """API logout endpoint"""
    logout(request)
    return Response({'success': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_me(request):
    """Get current user info"""
    serializer = UserDetailSerializer(request.user)
    return Response(serializer.data)


# ========== SEARCH VIEW ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_search(request):
    """Global search endpoint"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return Response({'error': 'Search query too short'}, status=status.HTTP_400_BAD_REQUEST)
    
    results = {
        'users': [],
        'courses': [],
        'events': [],
        'announcements': [],
    }
    
    # Search users
    users = User.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query) |
        Q(student_id__icontains=query)
    )[:10]
    results['users'] = UserSerializer(users, many=True).data
    
    # Search courses
    courses = Course.objects.filter(
        Q(code__icontains=query) |
        Q(title__icontains=query)
    )[:10]
    results['courses'] = CourseSerializer(courses, many=True).data
    
    # Search events
    events = Event.objects.filter(
        Q(title__icontains=query) |
        Q(description__icontains=query) |
        Q(venue__icontains=query)
    )[:10]
    results['events'] = EventSerializer(events, many=True).data
    
    # Search announcements
    announcements = Announcement.objects.filter(
        Q(title__icontains=query) |
        Q(content__icontains=query)
    )[:10]
    results['announcements'] = AnnouncementSerializer(announcements, many=True).data
    
    return Response(results)


# ========== DASHBOARD VIEWS ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_dashboard_data(request):
    """Get student dashboard data"""
    if request.user.user_type not in ['student', 'executive']:
        return Response(
            {'error': 'Not a student'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    current_academic = AcademicSetting.objects.filter(is_active=True).first()
    
    # Get registered courses
    registered_courses = CourseRegistration.objects.filter(
        student=request.user,
        academic_setting=current_academic
    ).select_related('course') if current_academic else []
    
    # Get upcoming events
    upcoming_events = EventAttendee.objects.filter(
        user=request.user,
        event__start_date__gte=timezone.now()
    ).select_related('event')[:5]
    
    # Get payment status
    total_paid = Payment.objects.filter(
        student=request.user,
        status='success'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get unread messages
    unread_messages = Message.objects.filter(
        recipient=request.user,
        read_at__isnull=True
    ).count()
    
    data = {
        'student_info': {
            'name': request.user.get_full_name(),
            'student_id': request.user.student_id,
            'level': request.user.level,
            'program': request.user.get_program_type_display(),
        },
        'current_academic': {
            'name': str(current_academic) if current_academic else None,
            'semester': current_academic.current_semester if current_academic else None,
        },
        'registered_courses': CourseRegistrationSerializer(registered_courses, many=True).data,
        'upcoming_events': EventAttendeeSerializer(upcoming_events, many=True).data,
        'total_paid': str(total_paid),
        'unread_messages': unread_messages,
        'requires_password_change': request.user.requires_password_change,
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_dashboard_data(request):
    """Get admin dashboard data"""
    current_academic = AcademicSetting.objects.filter(is_active=True).first()
    
    # Statistics
    total_students = User.objects.filter(user_type='student').count()
    total_staff = User.objects.filter(user_type='staff').count()
    total_executives = User.objects.filter(user_type='executive').count()
    
    # Payment statistics
    total_collected = Payment.objects.filter(
        status='success'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    payments_this_month = Payment.objects.filter(
        status='success',
        created_at__month=timezone.now().month
    ).count()
    
    # Event statistics
    upcoming_events = Event.objects.filter(
        start_date__gte=timezone.now()
    ).count()
    
    # Complaint statistics
    pending_complaints = Complaint.objects.filter(status='pending').count()
    
    data = {
        'user_stats': {
            'total_students': total_students,
            'total_staff': total_staff,
            'total_executives': total_executives,
        },
        'payment_stats': {
            'total_collected': str(total_collected),
            'payments_this_month': payments_this_month,
        },
        'event_stats': {
            'upcoming_events': upcoming_events,
        },
        'complaint_stats': {
            'pending_complaints': pending_complaints,
        },
        'recent_activity': [],  # Add recent activity here
    }
    
    return Response(data)


# ========== DIRECTORY VIEWS ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def directory_list(request):
    """Get student directory"""
    level = request.GET.get('level')
    program = request.GET.get('program')
    search = request.GET.get('search')
    
    students = User.objects.filter(user_type='student', is_active=True)
    
    if level:
        students = students.filter(level=level)
    
    if program:
        students = students.filter(program_type=program)
    
    if search:
        students = students.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(student_id__icontains=search)
        )
    
    students = students.order_by('level', 'last_name')
    
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(students, request)
    serializer = StudentDirectorySerializer(page, many=True)
    
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def directory_detail(request, pk):
    """Get student directory detail"""
    student = get_object_or_404(User, pk=pk, user_type='student')
    serializer = StudentDirectorySerializer(student)
    return Response(serializer.data)


# ========== ATTENDANCE API VIEWS ==========

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_attendance_api(request):
    """Mark attendance via API"""
    session_id = request.data.get('session_id')
    
    try:
        session = AttendanceSession.objects.get(id=session_id)
        
        # Check if already marked
        if AttendanceRecord.objects.filter(session=session, user=request.user).exists():
            return Response(
                {'error': 'Already marked'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        record = AttendanceRecord.objects.create(
            session=session,
            user=request.user,
            check_in_method='api',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        serializer = AttendanceRecordSerializer(record)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except AttendanceSession.DoesNotExist:
        return Response(
            {'error': 'Session not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def attendance_sessions(request):
    """Get attendance sessions for an event"""
    event_id = request.GET.get('event')
    
    if not event_id:
        return Response(
            {'error': 'Event ID required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    sessions = AttendanceSession.objects.filter(event_id=event_id, is_active=True)
    serializer = AttendanceSessionSerializer(sessions, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_attendance_qr(request, session_id):
    """Generate QR code for attendance session"""
    session = get_object_or_404(AttendanceSession, id=session_id)
    
    if session.qr_code:
        # Return existing QR code URL
        return Response({'qr_code_url': session.qr_code.url})
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=5
    )
    
    qr_data = f"{session.session_code}"
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return Response({'qr_code': img_str})


# ========== INBOX/OUTBOX VIEWS ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def inbox(request):
    """Get inbox messages"""
    messages = Message.objects.filter(recipient=request.user).order_by('-sent_at')
    serializer = MessageSerializer(messages, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sent_messages(request):
    """Get sent messages"""
    messages = Message.objects.filter(sender=request.user).order_by('-sent_at')
    serializer = MessageSerializer(messages, many=True)
    return Response(serializer.data)


# apps/api/views.py - Add this function

from apps.messaging.models import Message
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_count(request):
    """Get unread messages count"""
    try:
        count = Message.objects.filter(
            recipient=request.user,
            read_at__isnull=True
        ).count()
        
        return Response({
            'unread_count': count
        })
    except Exception as e:
        return Response({
            'unread_count': 0,
            'error': str(e)
        }, status=500)


# apps/api/views.py

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_messages_count(reques):  # Changed from unread_count
    """Get unread messages count"""
    try:
        count = Message.objects.filter(
            recipient=request.user,
            read_at__isnull=True
        ).count()
        return Response({'unread_count': count})
    except Exception as e:
        return Response({'unread_count': 0, 'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_message_read(request, pk):
    """Mark message as read"""
    message = get_object_or_404(Message, pk=pk, recipient=request.user)
    message.mark_as_read()
    return Response({'status': 'marked as read'})


# ========== MY COMPLAINTS VIEW ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_complaints(request):
    """Get current user's complaints"""
    complaints = Complaint.objects.filter(user=request.user).order_by('-created_at')
    serializer = ComplaintSerializer(complaints, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def respond_to_complaint(request, pk):
    """Respond to a complaint (staff/executive only)"""
    if request.user.user_type not in ['admin', 'staff', 'executive']:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    complaint = get_object_or_404(Complaint, pk=pk)
    content = request.data.get('content')
    
    if not content:
        return Response(
            {'error': 'Response content required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    response = ComplaintResponse.objects.create(
        complaint=complaint,
        responder=request.user,
        content=content
    )
    
    complaint.status = 'under_review'
    complaint.assigned_to = request.user
    complaint.save()
    
    return Response({'status': 'response added'})


# ========== STATISTICS VIEWS ==========

@api_view(['GET'])
@permission_classes([IsAdminUser])
def payment_statistics(request):
    """Get payment statistics (admin only)"""
    due_id = request.GET.get('due')
    
    if due_id:
        due = get_object_or_404(Due, id=due_id)
        total_students = User.objects.filter(
            user_type='student',
            level__in=due.target_levels
        ).count()
        
        paid_students = Payment.objects.filter(
            due=due,
            status='success'
        ).values('student').distinct().count()
        
        total_collected = Payment.objects.filter(
            due=due,
            status='success'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        return Response({
            'due': DueSerializer(due).data,
            'total_students': total_students,
            'paid_students': paid_students,
            'completion_rate': (paid_students / total_students * 100) if total_students > 0 else 0,
            'total_collected': str(total_collected),
        })
    else:
        # Overall statistics
        total_payments = Payment.objects.filter(status='success').count()
        total_amount = Payment.objects.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0
        
        return Response({
            'total_payments': total_payments,
            'total_amount': str(total_amount),
            'payments_by_level': list(Payment.objects.filter(
                status='success'
            ).values('student__level').annotate(
                count=Count('id'),
                total=Sum('amount')
            )),
        })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def attendance_statistics(request):
    """Get attendance statistics (admin only)"""
    event_id = request.GET.get('event')
    
    if event_id:
        event = get_object_or_404(Event, id=event_id)
        total_registered = event.get_attendee_count()
        total_attended = event.get_checked_in_count()
        
        return Response({
            'event': EventSerializer(event).data,
            'total_registered': total_registered,
            'total_attended': total_attended,
            'attendance_rate': (total_attended / total_registered * 100) if total_registered > 0 else 0,
            'by_session': AttendanceSessionSerializer(
                event.attendance_sessions.all(),
                many=True
            ).data
        })
    else:
        # Overall statistics
        total_events = Event.objects.count()
        total_attendance = AttendanceRecord.objects.count()
        
        return Response({
            'total_events': total_events,
            'total_attendance': total_attendance,
            'recent_attendance': AttendanceRecordSerializer(
                AttendanceRecord.objects.select_related('session__event', 'user')[:10],
                many=True
            ).data
        })


# apps/api/views.py - Add these functions

# apps/api/views.py - Add/update these functions

from apps.messaging.models import Message
from apps.core.models import ContactMessage, Notification
from django.db.models import Q, Count
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_messages_count(request):
    """Get unread messages count"""
    try:
        # Simple database query - no cache/throttling issues
        count = Message.objects.filter(
            recipient=request.user,
            read_at__isnull=True
        ).count()
        
        return Response({
            'success': True,
            'count': count
        })
    except Exception as e:
        logger.error(f"Error in unread_messages_count: {e}")
        return Response({
            'success': False,
            'error': 'Unable to fetch message count',
            'count': 0  # Return 0 as fallback
        }, status=status.HTTP_200_OK)  # Return 200 with count=0 instead of 500

# apps/api/views.py - Fix the notification functions

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_notifications_count(request):
    """Get unread notifications count"""
    try:
        # Count notifications where user is in target_users AND not in read_by
        count = Notification.objects.filter(
            Q(target_users=request.user) | Q(is_global=True),
            ~Q(read_by=request.user)
        ).distinct().count()
        
        return Response({
            'success': True,
            'count': count
        })
    except Exception as e:
        logger.error(f"Error in unread_notifications_count: {e}")
        return Response({
            'success': False,
            'count': 0,
            'error': str(e)
        }, status=200)  # Return 200 with count 0 to avoid breaking UI


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_list(request):
    """Get user notifications with pagination"""
    try:
        from django.core.paginator import Paginator
        
        # Get notifications for this user (either targeted or global)
        notifications = Notification.objects.filter(
            Q(target_users=request.user) | Q(is_global=True)
        ).distinct().order_by('-created_at')
        
        # Pagination
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 20)
        
        paginator = Paginator(notifications, page_size)
        try:
            notifications_page = paginator.page(page)
        except:
            return Response({
                'success': False,
                'error': 'Invalid page'
            }, status=400)
        
        # Serialize manually without serializer
        results = []
        for notification in notifications_page:
            results.append({
                'id': notification.id,
                'title': notification.title,
                'content': notification.message,  # Note: field is 'message' not 'content'
                'notification_type': notification.notification_type,
                'type_display': dict(notification.NOTIFICATION_TYPES).get(notification.notification_type, ''),
                'is_read': notification.is_read_by(request.user),
                'created_at': notification.created_at.isoformat() if notification.created_at else None,
            })
        
        return Response({
            'success': True,
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': notifications_page.number,
            'results': results
        })
    except Exception as e:
        logger.error(f"Error in notifications_list: {e}")
        return Response({
            'success': False,
            'error': str(e),
            'results': []
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, pk):
    """Mark a notification as read"""
    try:
        notification = get_object_or_404(Notification, pk=pk)
        
        # Check if this notification is for this user
        if not (notification.is_global or notification.target_users.filter(id=request.user.id).exists()):
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        notification.mark_as_read(request.user)
        
        return Response({
            'success': True,
            'message': 'Notification marked as read'
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    try:
        # Get all notifications for this user that are not read
        notifications = Notification.objects.filter(
            Q(target_users=request.user) | Q(is_global=True)
        ).exclude(read_by=request.user).distinct()
        
        for notification in notifications:
            notification.mark_as_read(request.user)
        
        return Response({
            'success': True,
            'message': 'All notifications marked as read'
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)
        
        
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def new_contact_messages_count(request):
    """Get new contact messages count (admin/staff only)"""
    try:
        # Check if user has permission
        if request.user.user_type not in ['admin', 'staff']:
            return Response({
                'success': True,
                'count': 0
            })
        
        # Check if ContactMessage model exists
        from django.apps import apps
        if apps.is_installed('apps.core') and hasattr(ContactMessage, 'objects'):
            count = ContactMessage.objects.filter(
                status='new'
            ).count()
        else:
            count = 0
        
        return Response({
            'success': True,
            'count': count
        })
    except Exception as e:
        logger.error(f"Error in new_contact_messages_count: {e}")
        return Response({
            'success': False,
            'error': 'Unable to fetch contact count',
            'count': 0
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contact_messages_list(request):
    """Get contact messages list (admin/staff only)"""
    try:
        # Check if user has permission
        if request.user.user_type not in ['admin', 'staff']:
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        messages = ContactMessage.objects.all().order_by('-created_at')
        
        # Apply filters
        status_filter = request.GET.get('status')
        if status_filter:
            messages = messages.filter(status=status_filter)
        
        search = request.GET.get('search')
        if search:
            messages = messages.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(subject__icontains=search) |
                Q(message__icontains=search)
            )
        
        # Pagination
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 20)
        
        paginator = Paginator(messages, page_size)
        try:
            messages_page = paginator.page(page)
        except:
            return Response({
                'success': False,
                'error': 'Invalid page'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Serialize messages
        from .serializers import ContactMessageSerializer
        serializer = ContactMessageSerializer(messages_page, many=True)
        
        return Response({
            'success': True,
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': messages_page.number,
            'results': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contact_message_detail(request, pk):
    """Get single contact message details (admin/staff only)"""
    try:
        # Check if user has permission
        if request.user.user_type not in ['admin', 'staff']:
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        message = get_object_or_404(ContactMessage, pk=pk)
        
        # Mark as read if it's new
        if message.status == 'new':
            message.status = 'read'
            message.save()
        
        # Serialize message
        from .serializers import ContactMessageDetailSerializer
        serializer = ContactMessageDetailSerializer(message)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_contact_message_read(request, pk):
    """Mark contact message as read (admin/staff only)"""
    try:
        # Check if user has permission
        if request.user.user_type not in ['admin', 'staff']:
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        message = get_object_or_404(ContactMessage, pk=pk)
        message.status = 'read'
        message.save()
        
        return Response({
            'success': True,
            'message': 'Message marked as read'
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reply_contact_message_api(request, pk):
    """Reply to contact message (admin/staff only)"""
    try:
        # Check if user has permission
        if request.user.user_type not in ['admin', 'staff']:
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        message = get_object_or_404(ContactMessage, pk=pk)
        
        # Get reply text from request
        data = request.data
        reply_text = data.get('reply')
        
        if not reply_text:
            return Response({
                'success': False,
                'error': 'Reply text is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update message
        message.reply_message = reply_text
        message.status = 'replied'
        message.replied_at = timezone.now()
        message.replied_by = request.user
        message.save()
        
        # Here you would send email notification
        # send_reply_email(message)
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='admin_action',
            ip_address=get_client_ip(request),
            details={
                'action': 'replied_to_contact',
                'message_id': message.id,
                'subject': message.subject
            }
        )
        
        return Response({
            'success': True,
            'message': 'Reply sent successfully'
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# apps/api/views.py

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_messages_count(request):
    """Get unread messages count"""
    try:
        from apps.messaging.models import Message
        
        count = Message.objects.filter(
            recipient=request.user,
            read_at__isnull=True
        ).count()
        
        return Response({
            'success': True,
            'count': count
        })
    except Exception as e:
        print(f"Error in unread_messages_count: {e}")
        return Response({
            'success': False,
            'count': 0,
            'error': str(e)
        }, status=200)  # Return 200 with count 0 to avoid breaking UI