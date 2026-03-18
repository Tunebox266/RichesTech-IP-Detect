# courses/urls.py
from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # Course listing
    path('', views.course_list, name='course_list'),
    path('<int:pk>/', views.course_detail, name='course_detail'),
    
    # Course registration
    path('register/', views.register_courses, name='register_courses'),
    path('my-courses/', views.my_courses, name='my_courses'),
    path('registered/<int:pk>/', views.registered_course_detail, name='registered_course_detail'),
    path("<int:pk>/students/", views.course_students, name="course_students"),
    
    # Course materials
    path('materials/', views.material_list, name='material_list'),
    path('materials/<int:pk>/', views.material_detail, name='material_detail'),
    path('materials/<int:pk>/download/', views.download_material, name='download_material'),
    path("materials/create/", views.create_material, name="create_material"),
    path("materials/<int:pk>/edit/", views.edit_material, name="edit_material"),
    path("materials/<int:pk>/comment/", views.add_material_comment, name="add_material_comment"),
    path('materials/<int:pk>/report/', views.report_material, name='report_material'),
    path('materials/download/<int:pk>/', views.download_material, name='download_material'),
    path('materials/upload/', views.upload_material, name='upload_material'),
    
    # Admin/Staff only
    path('create/', views.course_create, name='course_create'),
    path('<int:pk>/edit/', views.course_edit, name='course_edit'),
    path('<int:pk>/delete/', views.course_delete, name='course_delete'),
    path('bulk-upload/', views.bulk_upload_courses, name='bulk_upload_courses'),
    path('export/', views.export_courses, name='export_courses'),
]