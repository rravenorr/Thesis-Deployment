"""
URL configuration for ShipCheck project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from core import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from core.views import AccountSettingsView


urlpatterns = [
    path("admin/", admin.site.urls),
    path('camera/', views.camera_view, name='camera'),
    path('', views.dashboard, name='dashboard'),
    path('dept_leave/', views.dept_leave, name='dept_leave'),
    path('gen_leave/', views.gen_leave, name='gen_leave'),
    path('login/', views.custom_login_view, name='login'),
    path('logout/', views.custom_logout_view, name='logout'),
    path('departments/<int:pk>/delete/', views.delete_department, name='delete_department'),
    path('submit-leave/', views.submit_leave_request, name='submit_leave_request'),
    path('leave/respond/<int:pk>/', views.respond_leave_request, name='respond_leave_request'),
    path("my-leave-requests/", views.my_leave_requests, name="my_leave_requests"),
    path('department/<int:department_id>/respondents/', views.department_respondents_view, name='department_respondents'),
    path('shifts/create/', views.create_bulk_shifts, name='create_bulk_shifts'),
    path('shift/edit/<int:pk>/', views.edit_shift_view, name='edit_shift'),
    path('shift/<int:shift_id>/delete/', views.delete_shift_view, name='delete_shift'),
    path('account/settings/', AccountSettingsView.as_view(), name='account_settings'),
    path('employee/<int:pk>/reset-password/', views.reset_employee_password, name='reset_employee_password'),
    path('leave/<int:pk>/', views.leave_request_detail, name='leave_request_detail'),
    path('leave/<int:pk>/pdf/', views.leave_pdf_view, name='leave_pdf'),


    
    #! CRUD operations for employees | HR side
    path('employee/view/', views.EmployeeHTMxTableView.as_view(), name='view_employee_list'), 
    path('employee/view_dep/', views.view_departments, name='view_department_list'), 
    path('employee/register/', views.add_employee, name='add_employee'),
    path('employee/view/<int:pk>/', views.view_employee_information, name='employee_information'),
    path('employee/edit/<int:pk>/', views.EmployeeEditView.as_view(), name='employee_edit'),
    path('employee/delete/<int:pk>/', views.EmployeeDeleteView.as_view(), name='employee_delete'),
    path('employee/dtr/<int:pk>/', views.employee_dtr, name='employee_dtr'),
    #!
    
    #! CRUD operations for employee schedules | HR Side
    path('schedule/create/', views.add_schedule, name='add_schedule'), 
    path('schedule/view/', views.EmployeeScheduleHTMxTableView.as_view(), name='view_schedule_list'),
    path('schedule/edit/<int:pk>/', views.EmployeeScheduleEditView.as_view(), name='employee_schedule_edit'),
    path('schedule/delete/<int:pk>/', views.EmployeeScheduleDeleteView.as_view(), name='employee_schedule_delete'),
    
    #! Attendance module
    #path('attendance/camera/', views.open_camera, name='open_camera'),
    path('attendance/camera/predict', views.predict_face, name='predict_face'),
    path('attendance/register/', views.add_employee_attendance, name='add_employee_attendance'),
    path('attendance/view', views.EmployeeAttendanceHTMxTableView.as_view(), name='view_attendance_list'),
    path('attendance/edit/<int:pk>/', views.EmployeeAttendanceEditView.as_view(), name='employee_attendance_edit'),
    path('attendance/delete/<int:pk>/', views.EmployeeAttendanceDeleteView.as_view(), name='employee_delete_attendance'),
    #path('attendance/time-in/', views.attendance_time_in, name='attendance_time_in'),

    #!! Face Recognition Dataset and Trainings
    path('face_embeddings/view/', views.EmployeeFaceEmbeddingsHTMxTableView.as_view(), name='view_face_embeddings_list'),
    path('face_embeddings/register_face/', views.add_face_embeddings, name='register_face'),
    path('face_embeddings/train_dataset/', views.train_dataset, name='train_dataset'),
    path('face_embeddings/delete_embeddings/<int:employee_id>/', views.delete_face_embeddings, name='delete_face_embeddings'),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)