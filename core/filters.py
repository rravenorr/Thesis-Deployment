from decimal import Decimal
from django.db.models import Q, Value
from django.db.models.functions import Concat,  Coalesce, Lower, Replace
from django.forms import TextInput
import django_filters
import re
from .models import Employee, EmployeeSchedule, Attendance
from datetime import datetime

class EmployeeFilter(django_filters.FilterSet):
    query = django_filters.CharFilter(
        method='universal_search',
        label="",
        widget=TextInput(attrs={'placeholder': 'Search with Company ID, Name, Role, or Department'})
    )

    class Meta:
        model = Employee
        fields = ['query']

    def universal_search(self, queryset, name, value):
        normalized_value = " ".join(value.lower().split())  # Normalize search input (e.g., trims extra spaces)

        # Annotate full_name for searching
        queryset = queryset.annotate(
            full_name=Lower(
                Concat(
                    'first_name', Value(' '),
                    Coalesce('middle_name', Value('')), Value(' '),
                    'last_name'
                )
            )
        )

        # Do the filtering using lowercase version of everything
        return queryset.filter(
            Q(company_id__icontains=value) |
            Q(role__icontains=value) |
            Q(department__name__icontains=value) |
            Q(full_name__icontains=normalized_value)
        )
        
class EmployeeScheduleFilter(django_filters.FilterSet):
    query = django_filters.CharFilter(
        method='universal_search', 
        label="", 
        widget=TextInput(attrs={'placeholder': 'Search by Last Name or Department'})
    )

    class Meta:
        model = EmployeeSchedule
        fields = ['query']

    def universal_search(self, queryset, name, value):
        # Handle numeric searches first
        if value.replace(".", "", 1).isdigit():
            return queryset.filter(
                Q(employee_id=value) | Q(leave_credits=value)
            )

        # Split search terms while preserving quoted phrases
        search_terms = re.findall(r'\w+|\".*?\"', value)
        search_terms = [term.strip('"') for term in search_terms]

        # Create combinations for name matching
        q_objects = Q()
        
        # Check all possible name combinations
        for i in range(len(search_terms)):
            # Check for first+middle+last (3 terms)
            if i+2 < len(search_terms):
                q_objects |= Q(
                    first_name__iexact=search_terms[i],
                    middle_name__iexact=search_terms[i+1],
                    last_name__iexact=search_terms[i+2]
                )
            
            # Check for first+last (2 terms)
            if i+1 < len(search_terms):
                q_objects |= Q(
                    first_name__iexact=search_terms[i],
                    last_name__iexact=search_terms[i+1]
                )
                
                # Also check first/middle combination
                q_objects |= Q(
                    first_name__iexact=search_terms[i],
                    middle_name__iexact=search_terms[i+1]
                )

            # Check individual fields
            q_objects |= Q(
                Q(company_id__icontains=search_terms[i]) |
                Q(first_name__icontains=search_terms[i]) |
                Q(middle_name__icontains=search_terms[i]) |
                Q(last_name__icontains=search_terms[i]) |
                Q(department__icontains=search_terms[i]) |
                Q(role__icontains=search_terms[i])
            )

        return queryset.filter(q_objects)
class EmployeeFaceEmbeddingsFilter(django_filters.FilterSet):
    query = django_filters.CharFilter(
        method='universal_search',
        label="",
        widget=TextInput(attrs={'placeholder' : 'Search with Company ID, Name, or Department'}))
    
    class Meta:
        model = Employee
        fields = ['query']

    
    def universal_search(self, queryset, name, value):
        # Handle numeric searches first
        if value.replace(".", "", 1).isdigit():
            return queryset.filter(
                Q(employee_id=value) | Q(leave_credits=value)
            )

        # Split search terms while preserving quoted phrases
        search_terms = re.findall(r'\w+|\".*?\"', value)
        search_terms = [term.strip('"') for term in search_terms]

        # Create combinations for name matching
        q_objects = Q()
        
        # Check all possible name combinations
        for i in range(len(search_terms)):
            # Check for first+middle+last (3 terms)
            if i+2 < len(search_terms):
                q_objects |= Q(
                    first_name__iexact=search_terms[i],
                    middle_name__iexact=search_terms[i+1],
                    last_name__iexact=search_terms[i+2]
                )
            
            # Check for first+last (2 terms)
            if i+1 < len(search_terms):
                q_objects |= Q(
                    first_name__iexact=search_terms[i],
                    last_name__iexact=search_terms[i+1]
                )
                
                # Also check first/middle combination
                q_objects |= Q(
                    first_name__iexact=search_terms[i],
                    middle_name__iexact=search_terms[i+1]
                )

            # Check individual fields
            q_objects |= Q(
                Q(company_id__icontains=search_terms[i]) |
                Q(first_name__icontains=search_terms[i]) |
                Q(middle_name__icontains=search_terms[i]) |
                Q(last_name__icontains=search_terms[i]) |
                Q(department__icontains=search_terms[i]) |
                Q(role__icontains=search_terms[i])
            )

        return queryset.filter(q_objects)

class AttendanceFilter(django_filters.FilterSet):
    query = django_filters.CharFilter(
        method='universal_search',
        label="",
        widget=TextInput(attrs={'placeholder': 'Search by Company ID, Name, or Date'})
    )
    class Meta:
        model = Attendance
        fields = ['query']

    def universal_search(self, queryset, name, value):
        normalized_value = " ".join(value.lower().split())  # Clean the search input
        print("Searching for:", normalized_value)

        # Annotate full_name on the related employee, concatenating first, middle, last names
        queryset = queryset.annotate(
            full_name=Lower(
                Concat(
                    'employee__first_name', Value(' '),
                    Coalesce('employee__middle_name', Value('')), Value(' '),
                    'employee__last_name'
                )
            )
        )
        date_filter = None
        for fmt in ('%m/%d/%Y', '%Y-%m-%d'):
            try:
                parsed_date = datetime.strptime(value, fmt).date()
                date_filter = parsed_date
                break
            except ValueError:
                continue

        base_filter = (
            Q(employee__company_id__icontains=value) |
            Q(employee__role__icontains=value) |
            Q(employee__department__name__icontains=value) |
            Q(full_name__icontains=normalized_value)
        )

        if date_filter:
            # If date parsed successfully, add exact date filter
            return queryset.filter(base_filter | Q(date=date_filter))
        else:
            # If not a date, fallback to partial string match on date field as text
            return queryset.filter(base_filter | Q(date__icontains=value))