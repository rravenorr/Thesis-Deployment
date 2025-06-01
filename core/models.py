from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import timedelta, datetime
from django.utils import timezone
from django.db.models import Max
from django.core.validators import MaxValueValidator
import pytz
from django.db.models import JSONField
import math

class Shift(models.Model):
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='shifts'
    )
    department = models.ForeignKey(
        'Department',
        on_delete=models.CASCADE,
        related_name='shifts'
    )
    shift_date = models.DateField(default=timezone.now)
    shift_start = models.TimeField()
    shift_end = models.TimeField()

    class Meta:
        verbose_name = 'Shift'
        verbose_name_plural = 'Shifts'
        db_table = 'shift_table'
        ordering = ['shift_date', 'shift_start']

    def __str__(self):
        return f"{self.employee} - {self.shift_date} ({self.shift_start} to {self.shift_end})"

class LeaveRequest(models.Model):
    class LeaveType(models.TextChoices):
        SICK = 'SICK', 'Sick Leave'
        MATERNITY = 'MATERNITY', 'Maternity Leave'
        PATERNITY = 'PATERNITY', 'Paternity Leave'
        VACATION = 'VACATION', 'Vacation Leave'
        EMERGENCY = 'EMERGENCY', 'Emergency Leave'

    class ApprovalStatus(models.TextChoices):
        PENDING = 'PENDING', 'PENDING'
        APPROVED = 'APPROVED', 'APPROVED'
        REJECTED = 'REJECTED', 'REJECTED'

    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='leave_requests')
    leave_number = models.PositiveIntegerField(unique=True, editable=False)

    leave_dates = JSONField(default=list, blank=True, null=True)
    reason_for_leave = models.TextField()
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices)
    remarks = models.TextField(blank=True, null=True)
    leave_credit_deduction = models.PositiveIntegerField(default=0)
    deduction_applied = models.BooleanField(default=False)

    department_approval = models.CharField(max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    hr_approval = models.CharField(max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    president_approval = models.CharField(max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    status = models.CharField(max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)

    paid_dates = models.PositiveIntegerField(default=0)
    unpaid_dates = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    
    

    def save(self, *args, **kwargs):
        # Auto-generate leave number
        if not self.leave_number:
            max_leave_number = LeaveRequest.objects.aggregate(Max('leave_number'))['leave_number__max'] or 0
            self.leave_number = max_leave_number + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Leave {self.leave_number} - {self.employee}"

class Department(models.Model):
    name = models.CharField(max_length=255, unique=True)

    leave_respondents = models.ManyToManyField(
        'Employee',
        related_name='leave_departments',
        blank=True,
        limit_choices_to={'department__isnull': False}
    )
    shift_respondents = models.ManyToManyField(
        'Employee',
        related_name='shift_departments',
        blank=True,
        limit_choices_to={'department__isnull': False}
    )

    def __str__(self):
        return self.name

    def get_leave_respondents(self):
        return ", ".join([str(emp) for emp in self.leave_respondents.all()]) if self.leave_respondents.exists() else "Unassigned"

    def get_shift_respondents(self):
        return ", ".join([str(emp) for emp in self.shift_respondents.all()]) if self.shift_respondents.exists() else "Unassigned"


class Employee(models.Model):
    SEX_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Prefer not to Say'),
    ]

    ROLE_CHOICES = [
        ('Regular Employee', 'Regular Employee'),
        ('Department Head', 'Department Head'),
        ('Admin(HR)', 'Admin(HR)'),
        ('Supervisor', 'Supervisor'),
        ('President', 'President')
    ]

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    employee_id = models.AutoField(primary_key=True)
    company_id = models.CharField(max_length=20, blank=False, unique=True)
    first_name = models.CharField(max_length=100, blank=False)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=False)
    sex = models.CharField(max_length=20, choices=SEX_CHOICES, blank=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Regular Employee', blank=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')

    department = models.ForeignKey(
        Department,
        related_name="employees",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    contact_number = models.CharField(max_length=15, blank=False)
    date_employed = models.DateField()
    leave_credits = models.IntegerField(default=0, blank=False)
    leave_credits2 = models.IntegerField(default=0, blank=False)

    user_account = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee')

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
        db_table = 'employee_table'

    def clean(self):
        if not self.contact_number.isdigit():
            raise ValidationError("Contact number must only contain digits.")
        if len(self.contact_number) < 10:
            raise ValidationError("Contact number must be at least 10 digits long.")
        if self.leave_credits < 0:
            raise ValidationError("Leave credits cannot be negative.")

    def __str__(self):
        return f"{self.company_id} - {self.first_name} {self.middle_name if self.middle_name else ''} {self.last_name}"


class EmployeeSchedule(models.Model):
    employee = models.OneToOneField('Employee', on_delete=models.CASCADE)

    monday_start = models.TimeField(null=True, blank=True)
    monday_end = models.TimeField(null=True, blank=True)
    tuesday_start = models.TimeField(null=True, blank=True)
    tuesday_end = models.TimeField(null=True, blank=True)
    wednesday_start = models.TimeField(null=True, blank=True)
    wednesday_end = models.TimeField(null=True, blank=True)
    thursday_start = models.TimeField(null=True, blank=True)
    thursday_end = models.TimeField(null=True, blank=True)
    friday_start = models.TimeField(null=True, blank=True)
    friday_end = models.TimeField(null=True, blank=True)
    saturday_start = models.TimeField(null=True, blank=True)
    saturday_end = models.TimeField(null=True, blank=True)
    sunday_start = models.TimeField(null=True, blank=True)
    sunday_end = models.TimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Employee Schedule"
        verbose_name_plural = "Employee Schedules"
        db_table = "employee_schedule_table"

    def clean(self):
        if EmployeeSchedule.objects.filter(employee=self.employee).exclude(pk=self.pk).exists():
            raise ValidationError(f"Employee {self.employee} already has a schedule.")

        days = [
            ("Monday", self.monday_start, self.monday_end),
            ("Tuesday", self.tuesday_start, self.tuesday_end),
            ("Wednesday", self.wednesday_start, self.wednesday_end),
            ("Thursday", self.thursday_start, self.thursday_end),
            ("Friday", self.friday_start, self.friday_end),
            ("Saturday", self.saturday_start, self.saturday_end),
            ("Sunday", self.sunday_start, self.sunday_end),
        ]

        working_days = 0
        rest_days = 0

        for day, start, end in days:
            if start and end:
                start_datetime = datetime.combine(datetime.today(), start)
                end_datetime = datetime.combine(datetime.today(), end)

                if start_datetime >= end_datetime:
                    end_datetime += timedelta(days=1)

                if start_datetime >= end_datetime:
                    raise ValidationError({f"{day.lower()}_start": f"{day}: Start time must be earlier than end time."})

                duration = (end_datetime - start_datetime).seconds / 3600

                if duration != 9:
                    raise ValidationError({f"{day.lower()}_start": f"{day}: The work shift must be exactly 9 hours."})

                working_days += 1
            elif start or end:
                raise ValidationError({f"{day.lower()}_start": f"{day}: Both start and end times must be provided, or neither."})
            else:
                rest_days += 1

        if rest_days < 1:
            raise ValidationError("Employee must have at least one rest day in the week.")
        if working_days < 5:
            raise ValidationError(f"Employee must have at least 5 working days, but only {working_days} are set.")

    def get_schedule_for_day(self, day):
        start = getattr(self, f"{day.lower()}_start")
        end = getattr(self, f"{day.lower()}_end")

        if start and end:
            if start >= end:
                end = (datetime.combine(datetime.today(), end) + timedelta(days=1)).time()
            return f"{day}: {start.strftime('%H:%M')} to {end.strftime('%H:%M')}"
        return f"{day}: Rest Day"

    def is_rest_day(self, day):
        return not getattr(self, f"{day.lower()}_start") and not getattr(self, f"{day.lower()}_end")

    def __str__(self):
        return f"Schedule for {self.employee}"

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('On-Time', 'On-Time'),
        ('Late', 'Late'),
        ('Absent', 'Absent'),
        ('Rest Day', 'Rest Day'),
    ]

    employee = models.ForeignKey('Employee', on_delete=models.CASCADE)
    date = models.DateField()
    time_in = models.DateTimeField(null=True, blank=True)
    time_out = models.DateTimeField(null=True, blank=True)

    arrival_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Absent',
        help_text="Status based on time-in"
    )

    departure_status = models.CharField(
        max_length=20,
        choices=[
            ('On-Time', 'On-Time'),
            ('Undertime', 'Undertime'),
            ('Absent', 'Absent'),
            ('Rest Day', 'Rest Day')
        ],
        default='Absent',
        help_text="Status based on time-out"
    )

    shift = models.ForeignKey(
        'Shift',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Associated shift for this attendance record"
    )

    late_minutes = models.PositiveIntegerField(default=0)
    undertime_minutes = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        self._capture_shift_data()
        self._determine_attendance_status()
        super().save(*args, **kwargs)

    def _capture_shift_data(self):
        """Link to shift and capture schedule snapshot"""
        try:
            self.shift = Shift.objects.get(
                employee=self.employee,
                shift_date=self.date
            )
            self.scheduled_start = self.shift.shift_start
            self.scheduled_end = self.shift.shift_end
            self.is_rest_day = False
        except Shift.DoesNotExist:
            self.is_rest_day = True
            self.scheduled_start = None
            self.scheduled_end = None

    def _determine_attendance_status(self):
        if self.is_rest_day:
            self.arrival_status = 'Rest Day'
            self.departure_status = 'Rest Day'
        else:
            if self.time_in:
                self._calculate_lateness()
            else:
                self.arrival_status = 'Absent'

            if self.time_out:
                self._calculate_undertime()
            else:
                self.departure_status = 'Absent'

    def _calculate_lateness(self):
        scheduled_start_dt = datetime.combine(self.date, self.scheduled_start)
        grace_period_minutes = getattr(self.employee, 'grace_period_minutes', 15)
        grace_cutoff = scheduled_start_dt + timedelta(minutes=grace_period_minutes)

        # Convert self.time_in to naive if it's timezone-aware
        if self.time_in and self.time_in.tzinfo is not None:
            time_in_naive = self.time_in.replace(tzinfo=None)
        else:
            time_in_naive = self.time_in

        if time_in_naive > grace_cutoff:
            self.late_minutes = int((time_in_naive - scheduled_start_dt).total_seconds() // 60)
            self.arrival_status = 'Late'
        else:
            self.arrival_status = 'On-Time'
            self.late_minutes = 0

    def _calculate_undertime(self):
        if self.scheduled_end < self.scheduled_start:
            scheduled_end_dt = datetime.combine(self.date + timedelta(days=1), self.scheduled_end)
        else:
            scheduled_end_dt = datetime.combine(self.date, self.scheduled_end)

        undertime_grace_minutes = getattr(self.employee, 'undertime_grace_minutes', 5)
        grace_cutoff = scheduled_end_dt - timedelta(minutes=undertime_grace_minutes)
        
        # Convert self.time_out to naive if it's timezone-aware
        if self.time_out and self.time_out.tzinfo is not None:
            time_out_naive = self.time_out.replace(tzinfo=None)
        else:
            time_out_naive = self.time_out
            
        if time_out_naive < grace_cutoff:
            self.undertime_minutes = int((scheduled_end_dt - time_out_naive).total_seconds() // 60)
            self.departure_status = 'Undertime'
        else:
            self.departure_status = 'On-Time'
            self.undertime_minutes = 0
            
    def worked_hours(self):
        """
        Calculates the total worked hours excluding overtime.
        Dynamically fetches scheduled_start and scheduled_end from linked Shift.
        """
        print(f"\n--- DEBUG worked_hours for {self.date} ---")

        if not self.shift:
            print("No shift assigned")
            return 0

        scheduled_start = self.shift.shift_start
        scheduled_end = self.shift.shift_end
        is_rest_day = False  # You may also store this in Shift

        print(f"scheduled_start: {scheduled_start}")
        print(f"scheduled_end: {scheduled_end}")
        print(f"time_in: {self.time_in}")
        print(f"time_out: {self.time_out}")

        if not self.time_in or not self.time_out:
            print("Missing time_in or time_out")
            return 0

        # Combine shift times with date
        scheduled_start_dt = datetime.combine(self.date, scheduled_start)
        scheduled_end_dt = (
            datetime.combine(self.date + timedelta(days=1), scheduled_end)
            if scheduled_end < scheduled_start
            else datetime.combine(self.date, scheduled_end)
        )

        time_in = self.time_in.replace(tzinfo=None) if self.time_in.tzinfo else self.time_in
        time_out = self.time_out.replace(tzinfo=None) if self.time_out.tzinfo else self.time_out

        start = max(time_in, scheduled_start_dt)
        end = min(time_out, scheduled_end_dt)

        if end <= start:
            print("End is before or equal to start")
            return 0

        worked_seconds = (end - start).total_seconds()
        worked_hours = worked_seconds / 3600

        # Subtract 1 hour for break if worked hours > 1
        if worked_hours > 1:
            worked_hours -= 1

        # Prevent negative or zero hours after subtracting break
        worked_hours = max(worked_hours, 0)

        return worked_hours