# courses/models.py
from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models import AcademicSetting
from django.conf import settings

User = get_user_model()

class Course(models.Model):
    LEVEL_CHOICES = (
        (100, 'Level 100'),
        (200, 'Level 200'),
        (300, 'Level 300'),
        (400, 'Level 400'),
    )
    
    SEMESTER_CHOICES = (
        (1, 'First Semester'),
        (2, 'Second Semester'),
    )
    
    code = models.CharField(max_length=10, unique=True)
    title = models.CharField(max_length=200)
    level = models.IntegerField(choices=LEVEL_CHOICES)
    semester = models.IntegerField(choices=SEMESTER_CHOICES)
    credit_hours = models.IntegerField(default=3)
    description = models.TextField(blank=True)
    staff = models.ForeignKey(
        User, 
        limit_choices_to={'user_type': 'staff'},  # only staff can be assigned
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
        related_name='courses'
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['level', 'semester', 'code']
    
    def __str__(self):
        return f"{self.code} - {self.title}"

class CourseRegistration(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registered_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='registrations')
    academic_setting = models.ForeignKey(AcademicSetting, on_delete=models.CASCADE)
    registered_at = models.DateTimeField(auto_now_add=True)
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='registered_students')
    
    class Meta:
        unique_together = ['student', 'course', 'academic_setting']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.course.code}"

class CourseMaterial(models.Model):
    MATERIAL_TYPES = (
        ('lecture_note', 'Lecture Note'),
        ('slide', 'Slide'),
        ('past_question', 'Past Question'),
        ('lab_manual', 'Lab Manual'),
        ('other', 'Other'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=200)
    material_type = models.CharField(max_length=15, choices=MATERIAL_TYPES)
    file = models.FileField(upload_to='course_materials/')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_materials')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)
    downloads = models.IntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)  # NEW FIELD
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.course.code} - {self.title}"

class MaterialComment(models.Model):
    material = models.ForeignKey('CourseMaterial', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.comment[:20]}"


class MaterialReport(models.Model):
    material = models.ForeignKey('CourseMaterial', on_delete=models.CASCADE)
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField()
    reported_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reported_by} reported {self.material}"