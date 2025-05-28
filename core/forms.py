from django import forms
from .models import Employee, EmployeeSchedule, Department, Attendance
from .models import LeaveRequest
from django.core.exceptions import ValidationError
from django.templatetags.static import static
from datetime import timedelta, datetime
from .models import Employee, Shift
from django.forms.widgets import DateInput, DateTimeInput, Select

class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ['shift_start', 'shift_end']
        widgets = {
            'shift_start': forms.TimeInput(
                attrs={
                    'type': 'time',
                    'class': 'form-control',
                    'placeholder': 'Start time'
                }
            ),
            'shift_end': forms.TimeInput(
                attrs={
                    'type': 'time',
                    'class': 'form-control',
                    'placeholder': 'End time'
                }
            ),
        }
        labels = {
            'shift_start': 'Shift Start',
            'shift_end': 'Shift End',
        }

class ShiftBulkCreateForm(forms.Form):
    employee = forms.ModelChoiceField(queryset=Employee.objects.all(), label="Employee")
    dates = forms.CharField(widget=forms.TextInput(attrs={'id': 'multi-date-picker'}), label="Select Dates")
    shift_start = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), label="Shift Start")
    shift_end = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), label="Shift End")

class RespondentSelectionForm(forms.ModelForm):
    shift_respondents = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.none(),  # Set default to none
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select Shift Respondents"
    )
    leave_respondents = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.none(),  # Set default to none
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select Leave Respondents"
    )

    class Meta:
        model = Department
        fields = []

    def __init__(self, *args, **kwargs):
        department = kwargs.pop('department', None)
        super().__init__(*args, **kwargs)

        if department:
            # Only include employees assigned to the same department
            employees_in_dept = Employee.objects.filter(department=department)
            self.fields['shift_respondents'].queryset = employees_in_dept
            self.fields['leave_respondents'].queryset = employees_in_dept

            # Pre-fill with existing selections
            self.fields['shift_respondents'].initial = department.shift_respondents.all()
            self.fields['leave_respondents'].initial = department.leave_respondents.all()

class DepartmentCreateForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter department name'
            })
        }

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_dates', 'reason_for_leave', 'leave_type']
        widgets = {
            'leave_dates': forms.HiddenInput(),  # Important!
            'reason_for_leave': forms.Textarea(attrs={'rows': 3}),
        }


class LeaveResponseForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        exclude = ['status', 'employee', 'leave_number', 'created_at'] 
        fields = ['department_approval', 'president_approval', 'hr_approval', 'remarks', 'leave_credit_deduction']
        widgets = {
            'department_approval': forms.Select(attrs={'class': 'form-select'}),
            'hr_approval': forms.Select(attrs={'class': 'form-select'}),
            'president_approval': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        exclude = ['leave_credits', 'leave_credits2'] 
        fields = ['company_id','first_name','middle_name','last_name','sex','role','department','contact_number', 'date_employed', 'user_account',] 
        
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_account:
            self.fields['user_account'].disabled = True  # Make it uneditable
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'    

    def clean_company_id(self):
        company_id = self.cleaned_data.get('company_id')
        if company_id:
            # Check if another employee has the same company_id
            existing_employee = Employee.objects.filter(company_id=company_id).exclude(pk=self.instance.pk).first()
            if existing_employee:
                raise ValidationError("An employee with this Company ID already exists. Please use a unique Company ID.")
        return company_id

    def clean(self):
        """Remove redundant validation in the form."""
        cleaned_data = super().clean()
        return cleaned_data
    
class EmployeeScheduleForm(forms.ModelForm):
    class Media:
        # Reference to the local static files using the static tag
        js = (static('js/flatpickr.js'), static('js/flatpickr_init.js'))  # Include Flatpickr JS from the static directory
        css = {
            'all': (static('css/flatpickr.min.css'),)  # Include Flatpickr CSS from the static directory
        }
    class Meta:
        model = EmployeeSchedule
        fields = [
            'employee', 'monday_start', 'monday_end',
            'tuesday_start', 'tuesday_end',
            'wednesday_start', 'wednesday_end',
            'thursday_start', 'thursday_end',
            'friday_start', 'friday_end',
            'saturday_start', 'saturday_end',
            'sunday_start', 'sunday_end',
        ]
        time_widget = forms.TimeInput(attrs={ 
                'class': 'flatpickr form-control',
                'placeholder': 'Set Time',
                'data-time_24hr': 'true',
                'autocomplete' : 'off',
            })
        widgets = {
        'employee': forms.Select(attrs={'class': 'form-control'}),
        'monday_start': time_widget,
        'monday_end': time_widget,
        'tuesday_start': time_widget,
        'tuesday_end': time_widget,
        'wednesday_start': time_widget,
        'wednesday_end': time_widget,
        'thursday_start': time_widget,
        'thursday_end': time_widget,
        'friday_start': time_widget,
        'friday_end': time_widget,
        'saturday_start': time_widget,
        'saturday_end': time_widget,
        'sunday_start': time_widget,
        'sunday_end': time_widget,
        }
    def __init__(self, *args, **kwargs):
        super(EmployeeScheduleForm, self).__init__(*args, **kwargs)
        
        # If the form is being used for editing (i.e., there is an instance), disable the employee field
        if self.instance and self.instance.pk:
            self.fields['employee'].disabled = True  # Disable the employee field
            self.fields['employee'].initial = self.instance.employee_id  # Pre-select the employee from the instance
        else:
            # If creating a new schedule, allow the user to select an employee
            self.fields['employee'].queryset = Employee.objects.all()  # Populate the employee field with all employees
    
    def clean(self):
        """Remove redundant validation in the form."""
        # Simply call the model's clean method to do the validation
        cleaned_data = super().clean()
        return cleaned_data

    
class FaceEmbeddingsForm(forms.Form):
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Select Employee"
    )

class AttendanceForm(forms.ModelForm):
    class Media:
        # Reference to the local static files using the static tag
        js = (static('js/flatpickr.js'), static('js/flatpickr_init.js'))  # Include Flatpickr JS from the static directory
        css = {
            'all': (static('css/flatpickr.min.css'),)  # Include Flatpickr CSS from the static directory
        }
    class Meta:
        model = Attendance 
        fields = [
            'employee',
            'date',
            'time_in',
            'time_out',
            'shift',
        ]

        widgets = {
            'employee': Select(attrs={'class': 'form-control'}),
            'date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time_in': DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'time_out': DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'arrival_status': Select(attrs={'class': 'form-control'}),
            'departure_status': Select(attrs={'class': 'form-control'}),
            'shift': Select(attrs={'class': 'form-control'}),
            'late_minutes': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'undertime_minutes': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }

    def clean_late_minutes(self):
        return self.instance.late_minutes

    def clean_undertime_minutes(self):
        return self.instance.undertime_minutes

class AttendanceFormEdit(forms.ModelForm):
    class Media:
        # Reference to the local static files using the static tag
        js = (static('js/flatpickr.js'), static('js/flatpickr_init.js'))  # Include Flatpickr JS from the static directory
        css = {
            'all': (static('css/flatpickr.min.css'),)  # Include Flatpickr CSS from the static directory
        }
    class Meta:
        model = Attendance 
        exclude = [
            'employee'
            'arrival_status',
            'departure_status',
            'shift',
            'late_minutes',
            'undertime_minutes']
        fields = [
            'date',
            'time_in',
            'time_out',
        ]

        widgets = {
            'employee': Select(attrs={'class': 'form-control'}),
            'date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time_in': DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'time_out': DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'arrival_status': Select(attrs={'class': 'form-control'}),
            'departure_status': Select(attrs={'class': 'form-control'}),
            'shift': Select(attrs={'class': 'form-control'}),
            'late_minutes': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'undertime_minutes': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }

    def clean_late_minutes(self):
        return self.instance.late_minutes

    def clean_undertime_minutes(self):
        return self.instance.undertime_minutes