from math import e
import django_tables2 as tables
from django.utils.html import format_html
from .models import Employee, EmployeeSchedule, Attendance
import os
from django.conf import settings
from django.utils.timezone import localtime
from django.urls import reverse


class EmployeeHTMxTable(tables.Table):
    full_name = tables.Column(accessor='full_name', orderable=True, verbose_name='FULL NAME')
    view = tables.Column(empty_values=(), orderable=False, verbose_name='ACTIONS')

    class Meta:
        model = Employee
        template_name = "htmx_template.html"
        exclude = ('employee_id', "sex", "date_employed", "first_name", "middle_name", "last_name",'leave_credits',)
        fields = (
            'company_id',
            'full_name',
            'role',
            'department',
            'contact_number',
            'status',
            'view',
        )
        attrs = {
            "class": "table table-bordered table-hover",
            "thead": {
                "class": "table-dark text-center text-uppercase",
            },
            "td": {
                "class": "text-center",
            },
            "th": {
                "class": "text-center",
            }
        }

    def render_full_name(self, value):
        return format_html('<span class="employee-name">{}</span>', value)

    def render_view(self, record):
        return format_html(
            '<a href="/employee/view/{}/" class="btn btn-sm btn-outline-primary me-1">View</a>',
            record.employee_id 
        )

        
class EmployeeScheduleHTMxTable(tables.Table):
    full_name = tables.Column(empty_values=(), orderable=False, verbose_name='FULL NAME')
    view = tables.Column(empty_values=(), orderable=True, verbose_name='ACTIONS')

    class Meta:
        model = Employee
        template_name = "htmx_template.html"
        exclude = ('employee_id', "sex", "date_employed", "first_name", "middle_name", "last_name",'leave_credits',)
        fields = (
            'company_id',
            'full_name', 
            'role',
            'view',
        )
        attrs = {
            "class": "table table-bordered table-hover",
            "thead": {
                "class": "table-dark text-center text-uppercase",
            },
            "td": {
                "class": "text-center",
            },
            "th": {
                "class": "text-center",
            }
        }

    def render_full_name(self, record):
        # Handle empty middle names gracefully
        middle = f" {record.middle_name}" if record.middle_name else ""
        return format_html(
            '<span class="employee-name">{}{} {}</span>',
            record.first_name,
            middle,
            record.last_name
        )

    def render_view(self, record):
        return format_html(
            '<a href="/employee/view/{}/" class="btn btn-sm btn-outline-primary me-1">View</a>',
            record.employee_id 
        )
#record.employee_id -> employee
#record.id -> schedule
#this is where the url takes the primary key and passese it

class EmployeeFaceEmbeddingsHTMxTable(tables.Table):
    full_name = tables.Column(empty_values=(), orderable=True, verbose_name='FULL NAME')
    face_embeddings = tables.Column(empty_values=(), orderable=False, verbose_name="FACE EMBEDDINGS")
    edit = tables.Column(empty_values=(), orderable=False, verbose_name='ACTION')
    
    class Meta:
        model = Employee
        template_name = "htmx_template.html"
        exclude = ('employee_id', "sex", "date_employed", "first_name", "middle_name", "last_name")
        fields = (
            'company_id',
            'full_name',
            'department',
            'face_embeddings',
        )
        attrs = {
            "class": "table table-bordered table-hover",
            "thead": {
                "class": "table-dark text-center text-uppercase",
            },
            "td": {
                "class": "text-center",
            },
            "th": {
                "class": "text-center",
            }
        }

    def get_embedding_directory(self, record):
        #VERY CHARACTER STRICT
        middle = f"{record.middle_name}" if record.middle_name else ""
        name = f"{record.first_name} {middle} {record.last_name}"
        #print(f"Names: {name}")
        return os.path.join(
            settings.BASE_DIR,
            'core',
            'static',
            'registered_faces', 
            f"{name}_{record.company_id}"
        )

    def render_face_embeddings(self, record):
        """Check if embeddings exist in directory"""
        embed_dir = self.get_embedding_directory(record)
        
        if os.path.exists(embed_dir) and len(os.listdir(embed_dir)) > 0:
            return format_html('<span class="text-success">Active</span>')
        return format_html('<span class="text-danger">Inactive</span>')

    def render_edit(self, record):
        """Render delete button to remove embeddings"""
        embed_dir = self.get_embedding_directory(record)
        
        if os.path.exists(embed_dir) and len(os.listdir(embed_dir)) > 0:
            return format_html(
                '''
                <button 
                    hx-delete="/face_embeddings/delete_embeddings/{}/" 
                    hx-confirm="Are you sure you want to delete the embeddings for this?" 
                    hx-target="closest tr"
                    hx-swap="outerHTML"
                    class="btn btn-sm btn-danger me-1">
                    Delete
                </button>
                ''',
                record.employee_id,
            )
        return "-"

    def render_full_name(self, record):
        middle = f"{record.middle_name}" if record.middle_name else ""
        return format_html(
            '<span class="employee-name">{} {} {}</span>',
            record.first_name,
            middle,
            record.last_name
        )
        
class EmployeeAttendanceHTMxTable(tables.Table):
    company_id = tables.Column(empty_values=(), verbose_name='COMPANY ID', orderable=True, order_by='employee__company_id')
    full_name = tables.Column(empty_values=(), verbose_name='FULL NAME', orderable=True,  order_by=("employee__last_name", "employee__first_name"))
    scheduled_start = tables.Column(empty_values=(), verbose_name='SCHEDULED START', orderable=False)
    scheduled_end = tables.Column(empty_values=(), verbose_name='SCHEDULED END', orderable=False)
    edit = tables.Column(empty_values=(), orderable=False, verbose_name='ACTION')
    date = tables.DateColumn(orderable=True, format="m/d/Y")
    arrival_status = tables.Column(orderable=False)
    departure_status = tables.Column(orderable=False)
   
    class Meta:
        model = Attendance
        orderable = False
        template_name = "htmx_template.html"
        fields = (
            'company_id',
            'full_name',
            'date',
            'scheduled_start',
            'time_in',
            'arrival_status',
            'scheduled_end',
            'time_out',
            'departure_status',
        )
        attrs = {
            "class": "table table-bordered table-hover",
            "thead": {
                "class": "table-dark text-center text-uppercase",
            },
            "td": {
                "class": "text-center",
            },
            "th": {
                "class": "text-center",
            }
        }
    def render_company_id(self, record):
        return f"{record.employee.company_id}"
    
    def render_full_name(self, record):
        """Combine employee first, middle, last name for display"""
        return f"{record.employee.first_name} {record.employee.middle_name or ''} {record.employee.last_name}".strip()

    def render_time_in(self, record):
        dt = record.time_in
        return dt.strftime("%m/%d/%Y (%a): %I:%M %p") if dt else "—"

    def render_time_out(self, record):
        dt = record.time_out
        return dt.strftime("%m/%d/%Y (%a    ): %I:%M %p") if dt else "—"

    def render_scheduled_start(self, record):
        dt = record.shift.shift_start if record.shift else None
        return dt.strftime("%I:%M %p") if dt else "None"

    def render_scheduled_end(self, record):
        dt = record.shift.shift_end if record.shift else None
        return dt.strftime("%I:%M %p") if dt else "None"
    
    def render_edit(self, record):
        url = reverse('employee_attendance_edit', kwargs={'pk': record.id})
        return format_html(
            '<a href="{}" class="btn btn-sm btn-outline-primary me-1">View</a>', url
        )   