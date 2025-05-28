from django import forms
from django.contrib import admin
from django.forms.widgets import TextInput
from django.templatetags.static import static
from .models import Employee, EmployeeSchedule, Department, LeaveRequest, Shift, Attendance


class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        'employee_id', 'company_id', 'first_name', 'middle_name', 'last_name',
        'sex', 'role', 'get_department', 'contact_number', 'date_employed', 'leave_credits' , 'leave_credits2', 'user_account'
    )
    list_filter = ('role', 'sex', 'department', 'date_employed')
    search_fields = ('first_name', 'last_name', 'company_id', 'employee_id')
    list_per_page = 20

    fields = (
        'employee_id', 'company_id', 'first_name', 'middle_name', 'last_name',
        'sex', 'role', 'department', 'contact_number', 'date_employed', 'leave_credits', 'leave_credits2'
    )

    readonly_fields = ('employee_id',)

    def get_department(self, obj):
        return obj.department.name if obj.department else "Unassigned"
    get_department.short_description = "Department"


class DepartmentAdminForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields['leave_respondents'].queryset = Employee.objects.filter(department=self.instance)
            self.fields['shift_respondents'].queryset = Employee.objects.filter(department=self.instance)


class DepartmentAdmin(admin.ModelAdmin):
    form = DepartmentAdminForm
    list_display = ('name', 'get_leave_respondents', 'get_shift_respondents')

    def get_leave_respondents(self, obj):
        return ", ".join([str(emp) for emp in obj.leave_respondents.all()])
    get_leave_respondents.short_description = "Leave Respondents"

    def get_shift_respondents(self, obj):
        return ", ".join([str(emp) for emp in obj.shift_respondents.all()])
    get_shift_respondents.short_description = "Shift Respondents"


class EmployeeScheduleAdminForm(forms.ModelForm):
    time_widget = forms.TimeField(
        
        required=False,
        widget=TextInput(attrs={'class': 'flatpickr', 'data-enableTime': 'true', 'data-noCalendar': 'true', 'data-dateFormat': 'h:i K'})
    )

    class Meta:
        model = EmployeeSchedule
        fields = '__all__'

    # Apply time_widget to all time fields
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
        locals()[f"{day}_start"] = time_widget
        locals()[f"{day}_end"] = time_widget


class EmployeeScheduleAdmin(admin.ModelAdmin):
    form = EmployeeScheduleAdminForm

    list_display = (
        'id', 'employee', 'monday_start', 'monday_end', 'tuesday_start', 'tuesday_end', 
        'wednesday_start', 'wednesday_end', 'thursday_start', 'thursday_end', 
        'friday_start', 'friday_end', 'saturday_start', 'saturday_end', 
        'sunday_start', 'sunday_end'
    )

    search_fields = ('employee__first_name', 'employee__last_name')
    list_filter = ('employee__department',)  # Corrected filter

    class Media:
        js = (static('js/flatpickr.js'), static('js/flatpickr_init.js'))
        css = {'all': (static('css/flatpickr.min.css'),)}

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('leave_number', 'employee', 'leave_type', 'leave_dates', 'status')
    list_filter = ('leave_type', 'status', 'department_approval', 'hr_approval', 'president_approval')
    search_fields = ('employee__first_name', 'employee__last_name', 'leave_number')
    ordering = ('-created_at',)

@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('employee', 'department', 'shift_date', 'shift_start', 'shift_end')
    list_filter = ('department', 'shift_date')
    search_fields = ('employee__first_name', 'employee__last_name', 'department__name')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'time_in', 'time_out', 'arrival_status', 'departure_status', 'shift')
    list_filter = ('arrival_status', 'departure_status', 'date', 'employee__department')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_id')
    #readonly_fields = ('status', 'shift')  # Optional: Make these non-editable in admin

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('employee', 'shift')  # Optimizes query for performance
    
# Register models
admin.site.register(Employee, EmployeeAdmin)
admin.site.register(EmployeeSchedule, EmployeeScheduleAdmin)
admin.site.register(Department, DepartmentAdmin)
