from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
import json
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import UpdateView, DeleteView
from django.core.exceptions import BadRequest
from pathlib import Path
from imutils.video import VideoStream
import imutils
from django.conf import settings
from datetime import datetime, date, timedelta

import os
import cv2
import time
import numpy as np
import mediapipe as mp
from skimage.metrics import structural_similarity as ssim
#from deepface import DeepFace
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
import pickle
import pytz

from .forms import EmployeeForm, EmployeeScheduleForm, FaceEmbeddingsForm, LeaveRequestForm, DepartmentCreateForm, RespondentSelectionForm, LeaveResponseForm, AttendanceForm, AttendanceFormEdit
from .models import Employee, EmployeeSchedule, User, LeaveRequest, Shift, Attendance
from .tables import EmployeeHTMxTable, EmployeeScheduleHTMxTable, EmployeeFaceEmbeddingsHTMxTable, EmployeeAttendanceHTMxTable
from .filters import EmployeeFilter, EmployeeScheduleFilter, EmployeeFaceEmbeddingsFilter, AttendanceFilter

from django_tables2 import SingleTableMixin
from django_filters.views import FilterView
from .models import Department
from datetime import date

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django import forms
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone
from .forms import ShiftBulkCreateForm,  ShiftForm
from django.db.models import Value, CharField
from django.db.models.functions import Concat
from django.http import HttpResponse, Http404
import shutil
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.hashers import make_password
from .decorators import hr_only
from core.mixins import HROnlyMixin

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.template.loader import render_to_string
from weasyprint import HTML
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from collections import defaultdict

def download_dtr_pdf(request, employee_id, start_date, end_date):
    employee = get_object_or_404(Employee, pk=employee_id)
    
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    # Get existing records in the range
    dtr_records = Attendance.objects.filter(
        employee=employee,
        date__range=[start, end]
    ).select_related('shift').order_by('date')

    # Map DTR records by date
    dtr_map = {record.date: record for record in dtr_records}
    
    # Build full date list and map to either a real record or a placeholder
    complete_records = []
    current_date = start
    while current_date <= end:
        if current_date in dtr_map:
            complete_records.append(dtr_map[current_date])
        else:
            # Create a dummy object with placeholder values
            complete_records.append({
                'date': current_date,
                'shift': None,
                'time_in': None,
                'time_out': None,
                'arrival_status': 'No Shift',
                'departure_status': 'No Shift',
                'worked_hours': 0,
            })
        current_date += timedelta(days=1)

    # Calculate total worked hours only from actual records
    total_hours = sum([record.worked_hours() if hasattr(record, 'worked_hours') else 0 for record in complete_records])

    html_string = render_to_string('dtr_pdf_template.html', {
        'employee': employee,
        'dtr_records': complete_records,
        'start_date': start,
        'end_date': end,
        'total_hours': total_hours,
    })

    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf_file = html.write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{employee.company_id}_DTR_{start_date}_to_{end_date}.pdf"'
    return response

def leave_summary_pdf(request):
    start_date = parse_date(request.GET.get('start_date'))
    end_date = parse_date(request.GET.get('end_date'))

    if not start_date or not end_date:
        return HttpResponse("Invalid dates provided.", status=400)

    # Get all leaves (you could optimize this if you expect a huge dataset)
    all_leaves = LeaveRequest.objects.all()

    # Filter manually
    filtered_leaves = []
    for leave in all_leaves:
        if not leave.leave_dates:
            continue

        for d in leave.leave_dates:
            d_obj = parse_date(d) if isinstance(d, str) else d
            if start_date <= d_obj <= end_date:
                filtered_leaves.append(leave)
                break  # No need to check other dates for this leave

    # Prepare serialized data for PDF rendering
    serialized_leaves = []
    for leave in filtered_leaves:
        serialized_leaves.append({
            'employee': leave.employee,
            'leave_number': leave.leave_number,
            'leave_dates': ', '.join(
                d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)
                for d in leave.leave_dates or []
            ),
            'reason_for_leave': leave.reason_for_leave,
            'leave_type': leave.leave_type,
            'remarks': leave.remarks,
            'status': leave.status,
            'paid_dates': leave.paid_dates,
            'unpaid_dates': leave.unpaid_dates,
        })

    html = render_to_string("leave_summary_template.html", {
        'leaves': serialized_leaves,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    })
    pdf_file = HTML(string=html).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="leave-summary.pdf"'
    return response

def leave_pdf_view(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    html = render_to_string("leave_pdf_template.html", {'leave': leave})
    pdf_file = HTML(string=html).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="leave-request-{}.pdf"'.format(leave.leave_number)
    return response


@login_required
def leave_request_detail(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk, employee=request.user.employee)
    return render(request, 'leave_request_detail.html', {'leave': leave})

@hr_only
def reset_employee_password(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    if request.method == "POST":
        if employee.user_account:
            employee.user_account.password = make_password(employee.company_id)
            employee.user_account.save()
            messages.success(request, f"{employee.first_name}'s password has been reset to their Company ID.")
        else:
            messages.error(request, "This employee does not have an associated user account.")
    
    return redirect('employee_edit', pk=pk)


class AccountSettingsView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'account_settings.html'
    success_url = reverse_lazy('dashboard')  # Change to wherever you want to redirect after success
    success_message = "Your password was updated successfully."

def delete_shift_view(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)

    if request.method == 'POST':
        shift.delete()
        messages.success(request, "Shift deleted successfully.")
        return redirect('view_schedule_list')

    return redirect('view_schedule_list') 

def edit_shift_view(request, pk):
    shift = get_object_or_404(Shift, pk=pk)
    print(shift.employee)
    print(type(shift.employee))
    print(dir(shift.employee))
    employee_id = shift.employee.employee_id

    if request.method == 'POST':
        form = ShiftForm(request.POST, instance=shift)
        if form.is_valid():
            form.save()
            return redirect('employee_information', pk=employee_id)
    else:
        form = ShiftForm(instance=shift)

    return render(request, 'edit_shift.html', {'form': form, 'shift': shift})

def create_bulk_shifts(request):
    if request.method == 'POST':
        form = ShiftBulkCreateForm(request.POST, user=request.user)  # Pass user here
        if form.is_valid():
            employee = form.cleaned_data['employee']
            shift_start = form.cleaned_data['shift_start']
            shift_end = form.cleaned_data['shift_end']
            date_list = request.POST.get('dates').split(',')

            overwritten_dates = []
            created_dates = []

            for date_str in date_list:
                shift_date = datetime.strptime(date_str.strip(), '%Y-%m-%d').date()

                obj, created = Shift.objects.update_or_create(
                    employee=employee,
                    shift_date=shift_date,
                    defaults={
                        'department': employee.department,
                        'shift_start': shift_start,
                        'shift_end': shift_end,
                    }
                )

                if created:
                    created_dates.append(str(shift_date))
                else:
                    overwritten_dates.append(str(shift_date))

            if created_dates:
                messages.success(request, f"Shifts created for: {', '.join(created_dates)}.")
            if overwritten_dates:
                messages.info(request, f"Shifts updated for: {', '.join(overwritten_dates)}.")

            return redirect('view_schedule_list')
    else:
        form = ShiftBulkCreateForm(user=request.user)  # Also pass user here

    return render(request, 'create_bulk_shifts.html', {
        'form': form,
    })



def my_leave_requests(request):
    leave_requests = LeaveRequest.objects.filter(employee=request.user.employee).order_by('-created_at')
    return render(request, 'my_leave_requests.html', {
        'leave_requests': leave_requests
    })

@hr_only
def department_respondents_view(request, department_id):
    department = get_object_or_404(Department, id=department_id)

    if request.method == 'POST':
        form = RespondentSelectionForm(request.POST, department=department)
        if form.is_valid():
            department.shift_respondents.set(form.cleaned_data['shift_respondents'])
            department.leave_respondents.set(form.cleaned_data['leave_respondents'])
            return redirect('view_department_list')  # or your actual redirect
    else:
        form = RespondentSelectionForm(department=department)

    return render(request, 'department_respondents.html', {
        'form': form,
        'department': department
    })

def submit_leave_request(request):
    employee = request.user.employee
    leave_credits = employee.leave_credits
    leave_credits2 = employee.leave_credits2

    if request.method == 'POST':
        post_data = request.POST.copy()
        
        # Parse JSON string from the leave_dates hidden input
        try:
            leave_dates_str = post_data.get('leave_dates', '[]')
            leave_dates_list = json.loads(leave_dates_str)
            post_data['leave_dates'] = leave_dates_list  # assign parsed list to cleaned data
        except json.JSONDecodeError:
            post_data['leave_dates'] = []

        form = LeaveRequestForm(post_data)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.employee = employee
            leave_request.save()
            messages.success(request, "Leave request submitted successfully.")
            return redirect('dashboard')
    else:
        form = LeaveRequestForm()

    context = {
        'form': form,
        'leave_credits': leave_credits,
        'leave_credits2': leave_credits2,
    }
    return render(request, 'leave_request_form.html', context)


def custom_login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
        messages.error(request, "Invalid username or password.")

    return render(request, 'base.html', {'form': form})

def custom_logout_view(request):
    logout(request) 
    return redirect('login') 

class EmployeeHTMxTableView(HROnlyMixin, SingleTableMixin, FilterView):
    table_class = EmployeeHTMxTable
    queryset = Employee.objects.all()
    filterset_class = EmployeeFilter
    paginate_by = 10

    def get_template_names(self):
        if self.request.htmx:
            template_name = "view_employee_list_htmx_partial.html"
        else:
            template_name = "view_employee_list_htmx.html"

        return template_name

class EmployeeScheduleHTMxTableView(HROnlyMixin, SingleTableMixin, FilterView):
    table_class = EmployeeScheduleHTMxTable
    filterset_class = EmployeeScheduleFilter
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'employee') and user.employee.department:
            return Employee.objects.filter(department=user.employee.department)
        return Employee.objects.none()
    
    def get_template_names(self):
        if self.request.htmx:
            return "view_schedule_list_htmx_partial.html"
        return "view_schedule_list_htmx.html"

class EmployeeFaceEmbeddingsHTMxTableView(HROnlyMixin, SingleTableMixin, FilterView):
    table_class = EmployeeFaceEmbeddingsHTMxTable
    queryset = Employee.objects.all()
    filterset_class = EmployeeFaceEmbeddingsFilter
    paginate_by = 10

    def get_template_names(self):
        if self.request.htmx:
            template_name = "view_face_embeddings_list_htmx_partial.html"
        else:
            template_name = "view_face_embeddings_list_htmx.html"

        return template_name

class EmployeeAttendanceHTMxTableView(HROnlyMixin, SingleTableMixin, FilterView):
    table_class = EmployeeAttendanceHTMxTable
    queryset = Attendance.objects.all()
    filterset_class = AttendanceFilter
    paginate_by = 10

    def get_template_names(self):
        if self.request.htmx:
            template_name = "view_attendance_list_htmx_partial.html"
        else:
            template_name = "view_attendance_list_htmx.html"

        return template_name

def respond_leave_request(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    leave_days = len(leave.leave_dates)

    # Prevent editing finalized leaves
    if leave.status == 'APPROVED' and leave.deduction_applied:
        messages.info(request, "This leave request has already been finalized.")
        return redirect('gen_leave')

    if request.method == 'POST':
        form = LeaveResponseForm(request.POST, instance=leave)
        if form.is_valid():
            leave = form.save(commit=False)

            # Determine overall status
            if leave.department_approval == 'REJECTED':
                leave.status = 'DENIED'
            elif (leave.department_approval == 'APPROVED' and
                  leave.hr_approval == 'APPROVED' and
                  leave.president_approval == 'APPROVED'):

                if not leave.deduction_applied:
                    total_days = len(leave.leave_dates or [])
                    deduction = leave.leave_credit_deduction or 0  # default to 0 if None

                    # Calculate paid/unpaid days based on deduction vs total days
                    paid_count = min(deduction, total_days)
                    unpaid_count = total_days - paid_count

                    leave.paid_dates = paid_count
                    leave.unpaid_dates = unpaid_count

                    # Deduct from appropriate leave credit type
                    if leave.leave_type in ['VACATION', 'EMERGENCY']:
                        leave.employee.leave_credits2 -= deduction
                    else:
                        leave.employee.leave_credits -= deduction

                    leave.employee.save()
                    leave.deduction_applied = True

                leave.status = 'APPROVED'
            else:
                leave.status = 'PENDING'

            leave.save()
            messages.success(request, 'Leave request updated.')
            return redirect('gen_leave')
    else:
        form = LeaveResponseForm(instance=leave)

    return render(request, 'respond_leave.html', {
        'form': form,
        'leave': leave,
        'leave_days': leave_days
    })





class EmployeeEditView(HROnlyMixin,UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employee_edit_form.html'
    success_url = reverse_lazy('view_employee_list')

    def get_object(self, queryset=None):
        # Retrieve the employee object by primary key (from the URL)
        return get_object_or_404(Employee, pk=self.kwargs['pk'])

    def form_valid(self, form):
        # Save the form and redirect to the success URL
        self.object = form.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        # If the form is invalid, render the same form with error messages
        return self.render_to_response(self.get_context_data(form=form))

class EmployeeDeleteView(DeleteView):
    model = Employee
    #template_name = 'employee_confirm_delete.html'  # Optional: Confirmation template
    success_url = reverse_lazy('view_employee_list')  # Redirect after successful deletion

    def get_object(self, queryset=None):
        return get_object_or_404(Employee, pk=self.kwargs['pk'])

class EmployeeScheduleEditView(UpdateView):
    model = EmployeeSchedule
    form_class = EmployeeScheduleForm
    template_name = 'employee_schedule_edit_form.html'
    success_url = reverse_lazy('view_schedule_list')  # Redirect to the employee list page after successful edit

    def get_object(self, queryset=None):
        # Retrieve the employee object by primary key (from the URL)
        return get_object_or_404(EmployeeSchedule, employee=self.kwargs['pk'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # The context will automatically include the form and the employee
        return context

    def form_valid(self, form):
        # Save the form and redirect to the success URL
        self.object = form.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        # If the form is invalid, render the same form with error messages
        return self.render_to_response(self.get_context_data(form=form))
    
class EmployeeScheduleDeleteView(DeleteView):
    model = EmployeeSchedule
    success_url = reverse_lazy('view_schedule_list')

    def get_object(self, queryset=None):
        """
        Get the schedule using the employee ID from the URL
        The URL pattern should capture this as 'pk' (employee ID)
        """
        # Get the employee ID from URL parameters
        employee_id = self.kwargs['pk']
        
        # Return the schedule associated with this employee
        return get_object_or_404(EmployeeSchedule, employee__employee_id=employee_id)

class EmployeeAttendanceEditView(UpdateView):
    model = Attendance
    form_class = AttendanceFormEdit
    template_name = 'attendance_edit_form.html'
    success_url = reverse_lazy('view_attendance_list')

    def get_object(self, queryset=None):
        # Retrieve the employee object by primary key (from the URL)
        print("Get Success")
        return get_object_or_404(Attendance, pk=self.kwargs['pk'])

    def form_valid(self, form):
        # Save the form and redirect to the success URL
        self.object = form.save()
        print("Form save uccess")
        return super().form_valid(form)

    def form_invalid(self, form):
        # If the form is invalid, render the same form with error messages
        print("Form is INVALID:", form.errors)
        return self.render_to_response(self.get_context_data(form=form))
    
class EmployeeAttendanceDeleteView(DeleteView):
    model = Attendance
    template_name = 'attendance_confirm_delete.html'  
    success_url = reverse_lazy('view_attendance_list') 

    def get_object(self, queryset=None):
        return get_object_or_404(Attendance, pk=self.kwargs['pk'])
        
def camera_view(request):
    return render(request, 'attendance_open_camera.html')

@login_required
def dashboard(request):
    # Get employee linked to user (your DTR code uses user_account)
    employee = get_object_or_404(Employee, user_account=request.user)

    print("First Name:", employee.first_name)
    print("Last Name:", employee.last_name)
    print("Company ID:", employee.company_id)

    leave_depts = employee.leave_departments.all()
    shift_depts = employee.shift_departments.all()

    print("Leave Respondent for Departments:")
    for dept in leave_depts:
        print(f"- {dept.name}")

    print("Shift Respondent for Departments:")
    for dept in shift_depts:
        print(f"- {dept.name}")

    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)

    week_days = []

    shifts_this_week = Shift.objects.filter(
        employee=employee,
        shift_date__range=[start_of_week, end_of_week]
    ).values('shift_date', 'shift_start', 'shift_end')

    # Map shifts by date for quick lookup
    shifts_map = {shift['shift_date']: shift for shift in shifts_this_week}

    for i in range(7):
        day = start_of_week + timedelta(days=i)
        shift_info = shifts_map.get(day)

        week_days.append({
            'label': day.strftime('%A'),
            'date': day.strftime('%Y-%m-%d'),
            'is_today': day == today,
            'shift_start': shift_info['shift_start'] if shift_info else None,
            'shift_end': shift_info['shift_end'] if shift_info else None,
        })

    recent_leaves = LeaveRequest.objects.filter(employee=employee).order_by('-created_at')[:5]

    departments = Department.objects.prefetch_related('shift_respondents', 'leave_respondents').all()

    # --- DTR integration with detailed columns ---
    start_date = today - timedelta(days=13)
    end_date = today

    # Get attendance records for the last 14 days
    attendance_dict = {
        record.date: record
        for record in Attendance.objects.filter(
            employee=employee,
            date__range=(start_date, end_date)
        ).select_related('shift')
    }
    # DTR data
    dtr_data = []

    current_date = start_date
    total_hours = 0
    while current_date <= end_date:
        record = attendance_dict.get(current_date)
        worked_hours = 0 

        if record:
            shift = record.shift
            worked_hours = record.worked_hours()
            print(round(worked_hours))
            total_hours += round(worked_hours)
            
            if shift:
                shift_start = shift.shift_start.strftime('%I:%M %p') if shift.shift_start else 'N/A'
                shift_end = shift.shift_end.strftime('%I:%M %p') if shift.shift_end else 'N/A'
                shift_range = f"{shift_start} - {shift_end}"
            else:
                shift_range = 'No Shift'

            time_in = record.time_in.strftime('%I:%M %p') if record.time_in else 'N/A'
            time_out = record.time_out.strftime('%I:%M %p') if record.time_out else 'N/A'

            arrival_status = record.arrival_status or 'N/A'
            departure_status = record.departure_status or 'N/A'

        else:
            shift_range = 'None'
            time_in = 'None'
            time_out = 'None'
            arrival_status = 'Off'
            departure_status = 'Off'

        dtr_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day': current_date.strftime('%A'),
            'shift': shift_range,
            'time_in': time_in,
            'time_out': time_out,
            'arrival_status': arrival_status,
            'departure_status': departure_status,
            'worked_hours': round(worked_hours),
        })

        current_date += timedelta(days=1)
        # ------------------------------------------------
    context = {
        'departments': departments,
        'employee': employee,
        'recent_leaves': recent_leaves,
        'today': today,
        'week_days': week_days,
        'dtr_records': dtr_data,
        'start_date': start_date,
        'end_date': end_date,
        'total_hours': total_hours
    }

    return render(request, 'dashboard.html', context)

def dept_leave(request):
    return render(request, 'leave_response_specific.html')

def gen_leave(request):
    user = request.user
    role = user.employee.role
    department = user.employee.department

    if role == "President" or department.name == "Human Resources":
        # Show all leave requests
        leave_requests = LeaveRequest.objects.select_related('employee').order_by('-created_at')
    else:
        # Show only leave requests from the user's department
        leave_requests = LeaveRequest.objects.select_related('employee').filter(employee__department=department).order_by('-created_at')

    return render(request, 'leave_response_general.html', {'leave_requests': leave_requests})

@hr_only
def delete_department(request, pk):
    department = get_object_or_404(Department, pk=pk)
    department.delete()
    messages.success(request, "Department deleted successfully.")
    return redirect('view_department_list')

@hr_only
def view_departments(request):    
    if request.method == 'POST':
        form = DepartmentCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('view_department_list')  # Replace with your actual URL name
    else:
        form = DepartmentCreateForm()

    departments = Department.objects.all()
    return render(request, 'view_department_list.html', {
        'form': form,
        'departments': departments
    })

@hr_only
def add_employee(request):
    if request.method == 'POST':
        employee_form = EmployeeForm(request.POST)
        if employee_form.is_valid():

            employee = employee_form.save(commit=False)

            first_name = employee_form.cleaned_data.get('first_name')
            last_name = employee_form.cleaned_data.get('last_name')
            company_id = employee_form.cleaned_data.get('company_id')
            date_hired = employee_form.cleaned_data.get('date_employed')

            # Calculate number of days since hired
            days_since_hired = (date.today() - date_hired).days
            print(days_since_hired)
            # Assign leave credits based on days since hired
            if 365 <= days_since_hired <= 730:
                employee.leave_credits = 2
                employee.leave_credits2 = 3
            elif 731 <= days_since_hired <= 1095:
                employee.leave_credits = 3
                employee.leave_credits2 = 3
            elif 1096 <= days_since_hired <= 1460:
                employee.leave_credits = 4
                employee.leave_credits2 = 4
            elif 1461 <= days_since_hired <= 1825:
                employee.leave_credits = 5
                employee.leave_credits2 = 5
            elif 1826 <= days_since_hired <= 2190:
                employee.leave_credits = 6
                employee.leave_credits2 = 6
            elif 2191 <= days_since_hired <= 2555:
                employee.leave_credits = 7
                employee.leave_credits2 = 7
            elif days_since_hired > 2555:
                employee.leave_credits = 8
                employee.leave_credits2 = 7
            else:
                employee.leave_credits = 0
                employee.leave_credits2 = 0

            if not employee.status:
                employee.status = 'Active'
            
            # Create a user account
            username = f"{first_name.lower()}{last_name.lower()}".replace(" ", "")
            user = User.objects.create_user(
                username=username,
                password=str(company_id), 
                first_name=first_name,
                last_name=last_name
            )

            employee.user_account = user

            employee.save()

            return redirect('view_employee_list')
        else:
            print(employee_form.errors)
    else:
        employee_form = EmployeeForm()

    users = User.objects.exclude(employee__isnull=False)
    departments = Department.objects.all()

    return render(request, 'add_employee.html', {
        'employee_form': employee_form,
        'users': users,
        'departments': departments
    })
@hr_only
def add_employee_attendance(request):
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('view_attendance_list')  # Or redirect to another page if you prefer
    else:
        form = AttendanceForm()

    return render(request, 'add_attendance.html', {
        'attendance_form': form
    })

@hr_only
@login_required
def employee_dtr(request, pk):
    # Get employee linked to user (your DTR code uses user_account)
    employee = get_object_or_404(Employee, employee_id=pk)
    
    # --- DTR integration with detailed columns ---
    today = timezone.now().date()
    start_date = today - timedelta(days=13)
    end_date = today
    dtr_data = []

    # Get attendance records for the last 14 days
    attendance_dict = {
        record.date: record
        for record in Attendance.objects.filter(
            employee=employee,
            date__range=(start_date, end_date)
        ).select_related('shift')
    }
    
    current_date = start_date
    total_hours = 0
    while current_date <= end_date:
        record = attendance_dict.get(current_date)
        worked_hours = 0 

        if record:
            shift = record.shift
            worked_hours = record.worked_hours()
            print(round(worked_hours))
            total_hours += round(worked_hours)
            
            if shift:
                shift_start = shift.shift_start.strftime('%I:%M %p') if shift.shift_start else 'N/A'
                shift_end = shift.shift_end.strftime('%I:%M %p') if shift.shift_end else 'N/A'
                shift_range = f"{shift_start} - {shift_end}"
            else:
                shift_range = 'No Shift'

            time_in = record.time_in.strftime('%I:%M %p') if record.time_in else 'N/A'
            time_out = record.time_out.strftime('%I:%M %p') if record.time_out else 'N/A'

            arrival_status = record.arrival_status or 'N/A'
            departure_status = record.departure_status or 'N/A'

        else:
            shift_range = 'None'
            time_in = 'None'
            time_out = 'None'
            arrival_status = 'Off'
            departure_status = 'Off'

        dtr_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day': current_date.strftime('%A'),
            'shift': shift_range,
            'time_in': time_in,
            'time_out': time_out,
            'arrival_status': arrival_status,
            'departure_status': departure_status,
            'worked_hours': round(worked_hours),
        })

        current_date += timedelta(days=1)
        # ------------------------------------------------
    context = {
        'employee': employee,
        'dtr_records': dtr_data,
        'start_date': start_date,
        'end_date': end_date,
        'total_hours': total_hours
    }

    return render(request, 'employee_dtr.html', context)
 
def add_schedule(request):
    if request.method == 'POST':
        schedule_form = EmployeeScheduleForm(request.POST)
        if schedule_form.is_valid():
            # Save the schedule data
            schedule_form.save()
            return redirect('view_schedule_list')  # Redirect to a list or detail view
        else:
            print(schedule_form.errors)
    else:
        schedule_form = EmployeeScheduleForm()

    return render(request, 'add_schedule.html', {'schedule_form': schedule_form})

def view_employee_information(request, pk):
    employee = get_object_or_404(Employee, employee_id=pk)
    shifts = Shift.objects.filter(employee=employee).order_by('shift_date', 'shift_start')

    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)          # Sunday

    context = {
        'employee': employee,
        'shifts': shifts,
        'today': today,
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
    }

    return render(request, 'view_employee_information.html', context)

@hr_only
def add_face_embeddings(request):
    if request.method == 'POST':
        form = FaceEmbeddingsForm(request.POST)
        if form.is_valid():
            employee = form.cleaned_data['employee']
            # Create directory path using all name components
            middle = f"{employee.middle_name}" if employee.middle_name else ""
            name = f"{employee.first_name} {middle} {employee.last_name}"
            company_id = employee.company_id
            print(f"Names: {name} and Company ID: {company_id}")
            create_dataset(name, company_id)
            return redirect('view_face_embeddings_list')
    else:
        form = FaceEmbeddingsForm()

    return render(request, 'add_face_embeddings.html', {'form': form})

# Face Recognition Module #

# Path to Haarcascade file
HAAR_CASCADE_PATH = os.path.join(settings.BASE_DIR, "core", "static", "haarcascades", "haarcascade_frontalface_default.xml")

def create_dataset(name, company_id):
    # Create directory for the user inside the static folder
    directory = os.path.join(settings.BASE_DIR, 'core', 'static', 'registered_faces', f"{name}_{company_id}")
    os.makedirs(directory, exist_ok=True)

    # --- MediaPipe Face Detection and Landmarks ---
    mp_face_detection = mp.solutions.face_detection
    mp_face_mesh = mp.solutions.face_mesh

    face_detection = mp_face_detection.FaceDetection(
        model_selection=0, min_detection_confidence=0.5
    )
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    # --- Video Stream ---
    print("[INFO] Initializing Video stream")
    #0 for laptop webcam, 1 for external (ONLY ME)
    vs = VideoStream(src=0).start()
    sampleNum = 0

    previous_frame = None
    previous_image = None
    target_size = (128, 128) #set the target size

    while True:
        frame = vs.read()
        frame = imutils.resize(frame, width=800)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_frame = cv2.GaussianBlur(gray_frame, (21, 21), 0)

        if previous_frame is not None:
            # --- Motion Detection ---
            frame_delta = cv2.absdiff(previous_frame, gray_frame)
            thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            motion_detected = cv2.countNonZero(thresh) > 1000  # Motion threshold

            if motion_detected:
                # --- Face Detection ---
                results_detection = face_detection.process(frame_rgb)

                if results_detection.detections:
                    # --- Choose the Largest Face ---
                    largest_face = None
                    largest_area = 0

                    for detection in results_detection.detections:
                        bboxC = detection.location_data.relative_bounding_box
                        ih, iw, _ = frame.shape
                        x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), int(bboxC.width * iw), int(bboxC.height * ih)
                        area = w * h

                        if area > largest_area:
                            largest_area = area
                            largest_face = detection

                    # --- Process Only the Largest Face ---
                    if largest_face is not None:
                        bboxC = largest_face.location_data.relative_bounding_box
                        ih, iw, _ = frame.shape
                        x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), int(bboxC.width * iw), int(bboxC.height * ih)

                        # --- Expand the bounding box ---
                        expansion_factor = 0.2  # Adjust this value to control the zoom out level

                        x_expansion = int(w * expansion_factor)
                        y_expansion = int(h * expansion_factor)

                        # Make sure expanded bounding box coordinates are within frame boundaries
                        x_new = max(0, x - x_expansion)
                        y_new = max(0, y - y_expansion)
                        w_new = min(iw - x_new, w + 2 * x_expansion)  # Use x_new to calculate max width
                        h_new = min(ih - y_new, h + 2 * y_expansion)  # Use y_new to calculate max height

                        # --- Face Landmarks and Alignment ---
                        results_landmarks = face_mesh.process(frame_rgb)
                        if results_landmarks.multi_face_landmarks:
                            # Assume first set of landmarks is for the largest face
                            face_landmarks = results_landmarks.multi_face_landmarks[0] 
                            landmarks = face_landmarks.landmark
                            left_eye_inner = landmarks[362]
                            right_eye_inner = landmarks[263]
                            lx, ly = int(left_eye_inner.x * iw), int(left_eye_inner.y * ih)
                            rx, ry = int(right_eye_inner.x * iw), int(right_eye_inner.y * ih)
                            dx = rx - lx
                            dy = ry - ly
                            angle = np.degrees(np.arctan2(dy, dx))

                            # Calculate the center of the original bounding box
                            center_x = x + w // 2
                            center_y = y + h // 2

                            # Perform rotation
                            M = cv2.getRotationMatrix2D((center_x, center_y), angle, 1.0)
                            rotated_face = cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))

                            # Calculate new bounding box coordinates after rotation
                            # Expand the bounding box ---
                            expansion_factor = 0.2  # Adjust this value to control the zoom out level

                            x_expansion = int(w * expansion_factor)
                            y_expansion = int(h * expansion_factor)

                            # Apply rotation to the corners of the expanded bounding box
                            corners = np.array([
                                [x - x_expansion, y - y_expansion],
                                [x + w + x_expansion, y - y_expansion],
                                [x - x_expansion, y + h + y_expansion],
                                [x + w + x_expansion, y + h + y_expansion]
                            ])
                            corners_rotated = cv2.transform(corners.reshape(-1, 1, 2), M).reshape(-1, 2)

                            # Find the new bounding box coordinates
                            x_new, y_new = np.min(corners_rotated, axis=0)
                            x_max, y_max = np.max(corners_rotated, axis=0)

                            # Ensure the new bounding box coordinates are within frame boundaries
                            x_new = max(0, int(x_new))
                            y_new = max(0, int(y_new))
                            w_new = min(iw - x_new, int(x_max - x_new))
                            h_new = min(ih - y_new, int(y_max - y_new))

                            # Crop the rotated face using the new bounding box
                            rotated_face = rotated_face[y_new:y_new+h_new, x_new:x_new+w_new]

                            if rotated_face is not None and rotated_face.size > 0:
                                # --- Similarity Check (Corrected Logic) ---
                                if previous_image is not None:
                                    gray_rotated = cv2.cvtColor(rotated_face, cv2.COLOR_BGR2GRAY)
                                    gray_previous = cv2.cvtColor(previous_image, cv2.COLOR_BGR2GRAY)

                                    # Resize for SSIM comparison
                                    gray_rotated = cv2.resize(gray_rotated, target_size)
                                    gray_previous = cv2.resize(gray_previous, target_size)

                                    similarity_score = ssim(gray_rotated, gray_previous)

                                    if similarity_score > 0.7:  # Too similar
                                        print(
                                            f"Image too similar (similarity: {similarity_score:.2f}), not saving."
                                        )
                                    else:  # Different enough
                                        cv2.imwrite(f'{directory}/{sampleNum}.jpg', rotated_face)
                                        previous_image = rotated_face.copy()
                                        sampleNum += 1
                                        print(f"Saved image {sampleNum} (similarity: {similarity_score:.2f})")
                                else:
                                    cv2.imwrite(f'{directory}/{sampleNum}.jpg', rotated_face)
                                    previous_image = rotated_face.copy()
                                    sampleNum += 1

                                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
                                cv2.waitKey(50)
                                time.sleep(0.1)  # Short delay

        previous_frame = gray_frame.copy()

        cv2.imshow("Register Face Embeddings (Press 'q' to cancel)", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or sampleNum > 50:
            break

    vs.stop()
    cv2.destroyAllWindows()

#Call Facenet Model
_face_model = None

def get_face_model():
    from deepface import DeepFace
    global _face_model
    if _face_model is None:
        print("Loading FaceNet model...")
        _face_model = DeepFace.build_model("Facenet")
        print("FaceNet model loaded.")
    return _face_model

def train_dataset(request):
    from deepface import DeepFace
    # --- Main training directory ---
    dataset = os.path.join(settings.BASE_DIR, 'core', 'static', 'registered_faces')

    X = []  # List to store face embeddings
    y = []  # List to store corresponding labels (person names)

    # --- Iterate through each person's directory ---
    for person_dir in os.listdir(dataset):
        person_path = os.path.join(dataset, person_dir)

        # Extract name and company ID from directory name
        try:
            person_name, company_id = person_dir.split("_")
        except ValueError:
            print(f"Skipping directory with invalid name and format: {person_dir}")
            continue

        if not os.path.isdir(person_path):
            continue

        #call the model once
        model = get_face_model()
        # --- Iterate through each image in the person's directory ---
        for imagefile in os.listdir(person_path):
            image_path = os.path.join(person_path, imagefile)
            image = cv2.imread(image_path)
            if image is None:
                print(f"Could not load image: {image_path}")
                continue

            try:
                embedding = DeepFace.represent(image, model_name="SFace", enforce_detection=False)[0]['embedding']
                X.append(embedding)
                y.append(person_name)
            except Exception as e:
                print(f"Error processing {imagefile}: {e}")

    # --- Label Encoding ---
    encoder = LabelEncoder()
    y = encoder.fit_transform(y)

    # --- SVM Training ---
    svc = SVC(kernel='linear', probability=True)
    svc.fit(X, y)

    # --- Saving the Model and Encoder ---
    # Create a directory for saving models within your static folder
    model_dir = os.path.join(settings.BASE_DIR, 'core', 'static', 'trained_model')
    os.makedirs(model_dir, exist_ok=True)  # Create the directory if it doesn't exist

    svc_save_path = os.path.join(model_dir, "svc.sav")
    with open(svc_save_path, 'wb') as f:
        pickle.dump(svc, f)

    encoder_save_path = os.path.join(model_dir, "classes.npy")  # Use os.path.join and model_dir
    np.save(encoder_save_path, encoder.classes_)

    messages.success(request, f'Training Complete.')
    print("Training Complete!")
    return render(request, "base.html")


# Load the trained SVM model and label encoder (global variables)
_loaded_model = None
def load_trained_model():
    global _loaded_model
    if _loaded_model is None:
        model_dir = os.path.join(settings.BASE_DIR, 'core', 'static', 'trained_model')
        svc_load_path = os.path.join(model_dir, "svc.sav")
        encoder_load_path = os.path.join(model_dir, "classes.npy")

        with open(svc_load_path, 'rb') as f:
            svc = pickle.load(f)

        encoder_classes = np.load(encoder_load_path)
        _loaded_model = (svc, encoder_classes)

"""
"SFace" (good balance)

"VGG-Face" (lightweight)

"OpenFace" (very fast, less accurate)
"""

def predict_face(request):
    from deepface import DeepFace
    # Call Model
    # Call Model
    load_trained_model()
    svc, encoder_classes = _loaded_model
    # MediaPipe face detection setup (global)
    mp_face_detection = mp.solutions.face_detection
    face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.5)
    if request.method == "POST":
        time.sleep(1.0)

        recognized_employee = None
        attendance_recorded = False
        face_detected_time = None
        delay_duration = 1.5

        vs = VideoStream(src=0).start()
        time.sleep(1.0)

        recognized_employee = None
        attendance_recorded = False
        face_detected_time = None
        delay_duration = 1.5

        model = get_face_model()

        # Flag to break the entire while loop after recording attendance
        exit_loop = False


        # Flag to break the entire while loop after recording attendance
        exit_loop = False

        while True:
            frame = vs.read()
            if frame is None:
                break

            frame = imutils.resize(frame, width=720)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(frame_rgb)


            if results.detections:
                if face_detected_time is None:
                    face_detected_time = time.time()
                    face_detected_time = time.time()

                for detection in results.detections:
                    bboxC = detection.location_data.relative_bounding_box
                    ih, iw, _ = frame.shape
                    x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), int(bboxC.width * iw), int(bboxC.height * ih)

                    face_roi = frame[y:y + h, x:x + w]

                    if time.time() - face_detected_time >= delay_duration:
                        try:
                            embedding = DeepFace.represent(face_roi, model_name="SFace", enforce_detection=False, detector_backend='opencv')[0]['embedding']
                            embedding = np.array(embedding).reshape(1, -1)

                            probabilities = svc.predict_proba(embedding)[0]
                            predicted_class_index = np.argmax(probabilities)
                            confidence_threshold = 0.7
                            confidence_threshold = 0.7

                            confidence = probabilities[predicted_class_index]
                            if confidence >= confidence_threshold:
                                predicted_name = encoder_classes[predicted_class_index]
                                print(predicted_name)
                                try:
                                    employee = (
                                        Employee.objects.annotate(
                                            full_name=Concat(
                                                'first_name', Value(' '),
                                                'middle_name', Value(' '),
                                                'last_name',
                                                output_field=CharField()
                                            )
                                        )
                                        .filter(full_name__iexact=predicted_name.strip())
                                        .first()
                                    )
                                    print(employee)
                                except Employee.DoesNotExist:
                                    break

                                now = datetime.now()

                                attendance = Attendance.objects.filter(employee=employee, date=now.date()).first()

                                #Check if employee has a shift scheduled today
                                try:
                                    shift = Shift.objects.get(employee=employee, shift_date=now.date())
                                except Shift.DoesNotExist:
                                    print(f"No shift found for {employee} on {now.date()}. Skipping attendance recording.")
                                    label = "No scheduled shift"
                                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                                    y_label = y - 15 if y - 15 > 15 else y + 15
                                    cv2.putText(frame, label, (x, y_label), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                                    continue  # Skip this iteration of the loop


                                if attendance:
                                    if not attendance.time_out:
                                        attendance.time_out = now
                                        attendance.save()
                                        print("Time-out recorded.")
                                        attendance_recorded = True
                                        exit_loop = True
                                        break
                                    else:
                                        print("Time-out already recorded.")
                                        exit_loop = True
                                        break
                                else:
                                    Attendance.objects.create(
                                        employee=employee,
                                        date=now.date(),
                                        time_in=now
                                    )
                                    print("Time-in recorded.")
                                    attendance_recorded = True
                                    exit_loop = True
                                    break
                            else:
                                predicted_name = "Unknown"

                            #label = f"{predicted_name}: {confidence:.2f}" if predicted_name != "Unknown" else "Unknown"
                            #label = f"{predicted_name}: {confidence:.2f}" if predicted_name != "Unknown" else "Unknown"
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            y_label = y - 15 if y - 15 > 15 else y + 15
                            cv2.putText(frame, label, (x, y_label), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                        except Exception as e:
                            print(f"Error during feature extraction or prediction: {e}")

            else:
                face_detected_time = None
                face_detected_time = None

            cv2.imshow("Real-time Face Recognition", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or exit_loop:
                break

        cv2.destroyAllWindows()
        vs.stop()

        # Redirect or render your attendance page after exiting loop
        return redirect("camera")
    return JsonResponse({'error': 'Invalid request method'}, status=405)
@hr_only
def delete_face_embeddings(request, employee_id):
    if request.method == "DELETE":
        try:
            employee = Employee.objects.get(pk=employee_id)

            # Generate the embedding directory path
            middle = f"{employee.middle_name}" if employee.middle_name else ""
            name = f"{employee.first_name} {middle} {employee.last_name}"
            embed_dir = os.path.join(
                settings.BASE_DIR, 'core', 'static', 'registered_faces', f"{name}_{employee.company_id}"
            )

            # Delete folder if it exists
            if os.path.exists(embed_dir):
                shutil.rmtree(embed_dir)
                
            response = HttpResponse()
            response["HX-Redirect"] = "/face_embeddings/view/"  # adjust to your actual view URL
            return response
        except Employee.DoesNotExist:
            raise Http404("Employee not found")

    return HttpResponse(status=405)  # Method not allowed