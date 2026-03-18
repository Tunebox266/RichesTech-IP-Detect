# apps/courses/admin.py

from django.contrib import admin
from .models import Course, CourseRegistration, CourseMaterial
from apps.accounts.models import User


# ===================================
# Course Material Inline
# ===================================

class CourseMaterialInline(admin.TabularInline):
    model = CourseMaterial
    extra = 0
    readonly_fields = ("uploaded_at", "downloads")


# ===================================
# Course Registration Inline
# ===================================

class CourseRegistrationInline(admin.TabularInline):
    model = CourseRegistration
    extra = 0
    readonly_fields = ("registered_at",)


# ===================================
# Course Admin
# ===================================
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "level",
        "semester",
        "credit_hours",
        "staff",       # added staff/lecturer display
        "is_active",
    )

    list_filter = (
        "level",
        "semester",
        "is_active",
        "staff",       # optional: filter by staff
    )

    search_fields = (
        "code",
        "title",
        "staff__first_name",  # search by staff name
        "staff__last_name",
        "staff__email",
    )

    inlines = [
        CourseMaterialInline,
        CourseRegistrationInline
    ]

    # limit staff selection to only staff users
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "staff":
            kwargs["queryset"] = User.objects.filter(user_type='staff')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ===================================
# Course Registration Admin
# ===================================

@admin.register(CourseRegistration)
class CourseRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "course",
        "academic_setting",
        "registered_at",
        "registered_by",
    )

    list_filter = (
        "academic_setting",
        "course__level",
        "course__semester",
    )

    search_fields = (
        "student__username",
        "student__first_name",
        "student__last_name",
        "course__code",
    )

    readonly_fields = ("registered_at",)

  
# ===================================
# Course Material Admin
# ===================================

@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "title",
        "material_type",
        "uploaded_by",
        "uploaded_at",
        "downloads",
    )

    list_filter = (
        "material_type",
        "uploaded_at",
    )

    search_fields = (
        "course__code",
        "course__title",
        "title",
    )

    readonly_fields = ("uploaded_at", "downloads")