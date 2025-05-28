from decimal import Decimal
from django.db.models import Q
from django.forms import TextInput
import django_filters
import re
from .models import Employee, EmployeeSchedule, Attendance

class EmployeeFilter(django_filters.FilterSet):
    query = django_filters.CharFilter(
        method='universal_search',
        label="",
        widget=TextInput(attrs={'placeholder' : 'Search with Company ID, Last Name, Role, or Department'}))
    
    class Meta:
        model = Employee
        fields = ['query']

    
    def universal_search(self, queryset, name, value):
        #Search
        if value.replace(".", "", 1).isdigit():
            # If the value is a number (like an employee_id or leave credits), filter by ID or leave credits
            return queryset.filter(
                Q(employee_id=value) | Q(leave_credits=value)
            )
        # Default search by first_name, last_name, department, and role
        return queryset.filter(
            Q(company_id__icontains=value) |
            Q(first_name__icontains=value) |
            Q(middle_name__icontains=value) |
            Q(last_name__icontains=value) |
            Q(department__icontains=value) |
            Q(role__icontains=value)
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
        widget=TextInput(attrs={'placeholder' : 'Search with Company ID, Last Name, or Department'}))
    
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
        widget=TextInput(attrs={'placeholder': 'Search by Name, Company ID, Department, or Date'})
    )

    class Meta:
        model = Attendance
        fields = ['query']

    def universal_search(self, queryset, name, value):
        # Split search terms while preserving quoted phrases
        search_terms = re.findall(r'\w+|\".*?\"', value)
        search_terms = [term.strip('"') for term in search_terms]

        q_objects = Q()

        for i in range(len(search_terms)):
            term = search_terms[i]

            # Full name combinations
            if i + 2 < len(search_terms):
                q_objects |= Q(
                    employee__first_name__iexact=search_terms[i],
                    employee__middle_name__iexact=search_terms[i+1],
                    employee__last_name__iexact=search_terms[i+2]
                )

            if i + 1 < len(search_terms):
                q_objects |= Q(
                    employee__first_name__iexact=search_terms[i],
                    employee__last_name__iexact=search_terms[i+1]
                )

            # Generic search across fields
            q_objects |= Q(
                Q(employee__first_name__icontains=term) |
                Q(employee__middle_name__icontains=term) |
                Q(employee__last_name__icontains=term) |
                Q(employee__company_id__icontains=term) |
                Q(employee__department__icontains=term) |
                Q(arrival_status__icontains=term) |
                Q(departure_status__icontains=term) |
                Q(date__icontains=term)
            )

        return queryset.filter(q_objects)