# api/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from apps.accounts.models import User, ActivityLog, StudentExecutive
from apps.courses.models import Course, CourseMaterial, CourseRegistration
from apps.payments.models import Due, Payment
from apps.core.models import Announcement, AcademicSetting, ContactMessage, Notification
from apps.events.models import Event, EventAttendee, AttendanceSession, AttendanceRecord
from apps.messaging.models import Message, MessageAttachment, Broadcast, Complaint, ComplaintResponse
from apps.directory.models import StudentIDCard


# ========== AUTH SERIALIZERS ==========

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile_photo = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'student_id', 'staff_id', 'program_type', 'level',
            'year_of_admission', 'profile_image', 'profile_photo', 'phone_number',
            'date_of_birth', 'address', 'is_active', 'date_joined', 'last_login',
            'requires_password_change'
        ]
        read_only_fields = ['date_joined', 'last_login']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_profile_photo(self, obj):
        if obj.profile_image:
            return obj.profile_image.url
        return None


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed user serializer with related data
    """
    full_name = serializers.SerializerMethodField()
    profile_photo = serializers.SerializerMethodField()
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    program_type_display = serializers.CharField(source='get_program_type_display', read_only=True)
    level_display = serializers.SerializerMethodField()
    executive_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'user_type_display', 'student_id', 'staff_id', 
            'program_type', 'program_type_display', 'level', 'level_display',
            'year_of_admission', 'profile_image', 'profile_photo', 'phone_number',
            'date_of_birth', 'address', 'is_active', 'date_joined', 'last_login',
            'requires_password_change', 'failed_login_attempts', 'account_locked_until',
            'executive_profile'
        ]
        read_only_fields = ['date_joined', 'last_login', 'failed_login_attempts']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_profile_photo(self, obj):
        if obj.profile_image:
            return obj.profile_image.url
        return None
    
    def get_level_display(self, obj):
        if obj.level:
            return dict(User._meta.get_field('level').choices).get(obj.level, '')
        return None
    
    def get_executive_profile(self, obj):
        if obj.user_type == 'executive' and hasattr(obj, 'executive_profile'):
            return StudentExecutiveSerializer(obj.executive_profile).data
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users
    """
    password = serializers.CharField(write_only=True, required=False)
    confirm_password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'confirm_password', 'first_name', 
            'last_name', 'user_type', 'program_type', 'level', 'year_of_admission',
            'phone_number', 'date_of_birth', 'address', 'profile_image', 'is_active'
        ]
    
    def validate(self, data):
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        
        if password and password != confirm_password:
            raise serializers.ValidationError("Passwords do not match")
        
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)
        
        user = User.objects.create(**validated_data)
        
        if password:
            user.set_password(password)
        else:
            # Generate random password
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for i in range(12))
            user.set_password(password)
            user.requires_password_change = True
        
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for login
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        if username and password:
            # Try to find user by student_id or staff_id
            try:
                user = User.objects.get(student_id=username)
                username = user.username
            except User.DoesNotExist:
                try:
                    user = User.objects.get(staff_id=username)
                    username = user.username
                except User.DoesNotExist:
                    pass
            
            user = authenticate(username=username, password=password)
            
            if user:
                if not user.is_active:
                    raise serializers.ValidationError('Account is disabled')
                
                data['user'] = user
            else:
                raise serializers.ValidationError('Invalid credentials')
        else:
            raise serializers.ValidationError('Must include "username" and "password"')
        
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change
    """
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords do not match")
        
        if len(data['new_password']) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long")
        
        return data


# ========== ACTIVITY LOG SERIALIZER ==========

class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'user_name', 'action_type', 'action_type_display', 
                  'timestamp', 'ip_address', 'details']


# ========== STUDENT EXECUTIVE SERIALIZER ==========

class StudentExecutiveSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    position_display = serializers.CharField(source='get_position_display', read_only=True)
    executive_level_display = serializers.CharField(source='get_executive_level_display', read_only=True)
    tenure_status_display = serializers.CharField(source='get_tenure_status_display', read_only=True)
    is_active_executive = serializers.BooleanField(read_only=True)
    remaining_tenure_days = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = StudentExecutive
        fields = '__all__'


# ========== COURSE SERIALIZERS ==========

class CourseSerializer(serializers.ModelSerializer):
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    semester_display = serializers.CharField(source='get_semester_display', read_only=True)
    
    class Meta:
        model = Course
        fields = '__all__'


class CourseDetailSerializer(serializers.ModelSerializer):
    """
    Detailed course serializer with related data
    """
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    semester_display = serializers.CharField(source='get_semester_display', read_only=True)
    materials_count = serializers.SerializerMethodField()
    registrations_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = '__all__'
    
    def get_materials_count(self, obj):
        return obj.materials.count()
    
    def get_registrations_count(self, obj):
        return obj.registrations.count()


class CourseMaterialSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source='course.code', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    material_type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    
    class Meta:
        model = CourseMaterial
        fields = '__all__'
    
    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class CourseRegistrationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_details = CourseSerializer(source='course', read_only=True)
    registered_by_name = serializers.CharField(source='registered_by.get_full_name', read_only=True)
    academic_year = serializers.CharField(source='academic_setting.academic_year', read_only=True)
    
    class Meta:
        model = CourseRegistration
        fields = '__all__'


# ========== DUE SERIALIZERS ==========

class DueSerializer(serializers.ModelSerializer):
    academic_year = serializers.CharField(source='academic_setting.academic_year', read_only=True)
    due_type_display = serializers.CharField(source='get_due_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    total_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    paid_students_count = serializers.IntegerField(read_only=True)
    total_students_target = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Due
        fields = '__all__'


class DueDetailSerializer(serializers.ModelSerializer):
    """
    Detailed due serializer with payment information
    """
    academic_year = serializers.CharField(source='academic_setting.academic_year', read_only=True)
    due_type_display = serializers.CharField(source='get_due_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    total_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    paid_students_count = serializers.IntegerField(read_only=True)
    total_students_target = serializers.IntegerField(read_only=True)
    collection_rate = serializers.FloatField(read_only=True)
    recent_payments = serializers.SerializerMethodField()
    
    class Meta:
        model = Due
        fields = '__all__'
    
    def get_recent_payments(self, obj):
        payments = obj.payments.filter(status='success')[:10]
        return PaymentSerializer(payments, many=True).data


# ========== PAYMENT SERIALIZERS ==========

class PaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    due_title = serializers.CharField(source='due.title', read_only=True)
    due_details = DueSerializer(source='due', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = '__all__'


class PaymentInitSerializer(serializers.Serializer):
    """
    Serializer for initiating a payment
    """
    due_id = serializers.IntegerField()
    email = serializers.EmailField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    def validate_due_id(self, value):
        try:
            due = Due.objects.get(id=value, is_active=True)
            
            # Check deadline
            if due.deadline < timezone.now().date():
                raise serializers.ValidationError("Payment deadline has passed")
            
            return value
        except Due.DoesNotExist:
            raise serializers.ValidationError("Invalid due")


# ========== ANNOUNCEMENT SERIALIZER ==========

class AnnouncementSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    created_by_photo = serializers.SerializerMethodField()
    
    class Meta:
        model = Announcement
        fields = '__all__'
    
    def get_created_by_photo(self, obj):
        if obj.created_by and obj.created_by.profile_image:
            return obj.created_by.profile_image.url
        return None


# ========== ACADEMIC SETTING SERIALIZER ==========

class AcademicSettingSerializer(serializers.ModelSerializer):
    current_semester_display = serializers.CharField(source='get_current_semester_display', read_only=True)
    
    class Meta:
        model = AcademicSetting
        fields = '__all__'


# ========== EVENT SERIALIZERS ==========

class EventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    attendee_count = serializers.SerializerMethodField()
    registered_count = serializers.SerializerMethodField()
    checked_in_count = serializers.SerializerMethodField()
    is_full = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Event
        fields = '__all__'
    
    def get_attendee_count(self, obj):
        return obj.get_attendee_count()
    
    def get_registered_count(self, obj):
        return obj.get_registered_count()
    
    def get_checked_in_count(self, obj):
        return obj.get_checked_in_count()


class EventDetailSerializer(serializers.ModelSerializer):
    """
    Detailed event serializer with sessions and attendees
    """
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    attendee_count = serializers.IntegerField(read_only=True)
    registered_count = serializers.IntegerField(read_only=True)
    checked_in_count = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    sessions = serializers.SerializerMethodField()
    recent_attendees = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = '__all__'
    
    def get_sessions(self, obj):
        sessions = obj.attendance_sessions.filter(is_active=True)
        return AttendanceSessionSerializer(sessions, many=True).data
    
    def get_recent_attendees(self, obj):
        attendees = obj.attendees.select_related('user')[:10]
        return EventAttendeeSerializer(attendees, many=True).data


class EventAttendeeSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    event_details = EventSerializer(source='event', read_only=True)
    
    class Meta:
        model = EventAttendee
        fields = '__all__'


class AttendanceSessionSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    session_type_display = serializers.CharField(source='get_session_type_display', read_only=True)
    attendance_count = serializers.SerializerMethodField()
    qr_code_url = serializers.SerializerMethodField()
    is_active_now = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = AttendanceSession
        fields = '__all__'
    
    def get_attendance_count(self, obj):
        return obj.get_checked_in_count()
    
    def get_qr_code_url(self, obj):
        if obj.qr_code:
            return obj.qr_code.url
        return None


class AttendanceRecordSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_id = serializers.CharField(source='user.student_id', read_only=True)
    session_title = serializers.CharField(source='session.name', read_only=True)
    event_title = serializers.CharField(source='session.event.title', read_only=True)
    check_in_method_display = serializers.CharField(source='get_check_in_method_display', read_only=True)
    
    class Meta:
        model = AttendanceRecord
        fields = '__all__'


# ========== MESSAGING SERIALIZERS ==========

class MessageAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageAttachment
        fields = '__all__'
    
    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_photo = serializers.SerializerMethodField()
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = '__all__'
    
    def get_sender_photo(self, obj):
        if obj.sender and obj.sender.profile_image:
            return obj.sender.profile_image.url
        return None
    
    def get_is_read(self, obj):
        if obj.recipient and obj.read_at:
            return True
        return False


class MessageDetailSerializer(serializers.ModelSerializer):
    """
    Detailed message serializer with replies
    """
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_photo = serializers.SerializerMethodField()
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    replies = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = '__all__'
    
    def get_sender_photo(self, obj):
        if obj.sender and obj.sender.profile_image:
            return obj.sender.profile_image.url
        return None
    
    def get_is_read(self, obj):
        if obj.recipient and obj.read_at:
            return True
        return False
    
    def get_replies(self, obj):
        replies = obj.replies.all()
        return MessageSerializer(replies, many=True).data


class BroadcastSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    recipient_count = serializers.IntegerField(read_only=True)
    acknowledgment_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Broadcast
        fields = '__all__'


# ========== COMPLAINT SERIALIZERS ==========

class ComplaintResponseSerializer(serializers.ModelSerializer):
    responder_name = serializers.CharField(source='responder.get_full_name', read_only=True)
    
    class Meta:
        model = ComplaintResponse
        fields = '__all__'


class ComplaintSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_id = serializers.CharField(source='user.student_id', read_only=True)
    complaint_type_display = serializers.CharField(source='get_complaint_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    responses = ComplaintResponseSerializer(many=True, read_only=True)
    response_count = serializers.SerializerMethodField()
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = Complaint
        fields = '__all__'
    
    def get_response_count(self, obj):
        return obj.responses.count()


class ComplaintDetailSerializer(serializers.ModelSerializer):
    """
    Detailed complaint serializer with all responses
    """
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_id = serializers.CharField(source='user.student_id', read_only=True)
    user_photo = serializers.SerializerMethodField()
    complaint_type_display = serializers.CharField(source='get_complaint_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    responses = ComplaintResponseSerializer(many=True, read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = Complaint
        fields = '__all__'
    
    def get_user_photo(self, obj):
        if obj.user and obj.user.profile_image:
            return obj.user.profile_image.url
        return None


# ========== DIRECTORY SERIALIZERS ==========

class StudentIDCardSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    level = serializers.IntegerField(source='student.level', read_only=True)
    program = serializers.CharField(source='student.get_program_type_display', read_only=True)
    photo = serializers.SerializerMethodField()
    qr_code_url = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentIDCard
        fields = '__all__'
    
    def get_photo(self, obj):
        if obj.student and obj.student.profile_image:
            return obj.student.profile_image.url
        return None
    
    def get_qr_code_url(self, obj):
        if obj.qr_code:
            return obj.qr_code.url
        return None


class StudentDirectorySerializer(serializers.ModelSerializer):
    """
    Simplified serializer for student directory
    """
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    level_display = serializers.SerializerMethodField()
    program_display = serializers.CharField(source='get_program_type_display', read_only=True)
    profile_photo = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'student_id', 'full_name', 'first_name', 'last_name',
            'level', 'level_display', 'program_type', 'program_display',
            'profile_photo', 'email'
        ]
    
    def get_level_display(self, obj):
        if obj.level:
            return dict(User._meta.get_field('level').choices).get(obj.level, '')
        return None
    
    def get_profile_photo(self, obj):
        if obj.profile_image:
            return obj.profile_image.url
        return None


# ========== DASHBOARD SERIALIZERS ==========

class StudentDashboardSerializer(serializers.Serializer):
    """
    Serializer for student dashboard data
    """
    student_info = UserSerializer()
    current_academic = AcademicSettingSerializer()
    registered_courses = CourseRegistrationSerializer(many=True)
    upcoming_events = EventAttendeeSerializer(many=True)
    total_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    unread_messages = serializers.IntegerField()
    pending_dues = serializers.IntegerField()
    recent_announcements = AnnouncementSerializer(many=True)


class AdminDashboardSerializer(serializers.Serializer):
    """
    Serializer for admin dashboard data
    """
    user_stats = serializers.DictField()
    payment_stats = serializers.DictField()
    event_stats = serializers.DictField()
    complaint_stats = serializers.DictField()
    recent_activity = ActivityLogSerializer(many=True)
    recent_payments = PaymentSerializer(many=True)
    upcoming_events = EventSerializer(many=True)


# apps/api/serializers.py - Add these serializers

class ContactMessageSerializer(serializers.ModelSerializer):
    """Serializer for contact message list view"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'name', 'email', 'phone', 'subject', 'message',
            'status', 'status_display', 'created_at'
        ]


class ContactMessageDetailSerializer(serializers.ModelSerializer):
    """Serializer for contact message detail view"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    replied_by_name = serializers.CharField(source='replied_by.get_full_name', read_only=True)
    
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'name', 'email', 'phone', 'subject', 'message',
            'status', 'status_display', 'ip_address', 'user_agent',
            'reply_message', 'replied_at', 'replied_by_name',
            'created_at'
        ]


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'content', 'notification_type', 'type_display',
            'is_read', 'created_at', 'time_ago'
        ]
    
    def get_time_ago(self, obj):
        from django.utils.timesince import timesince
        return timesince(obj.created_at)