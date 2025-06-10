# utils.py
from datetime import date

def update_leave_credits(employee):
    date_hired = employee.date_employed
    today = date.today()
    
    if not hasattr(employee, 'last_credit_update') or employee.last_credit_update.year < today.year:
        days_since_hired = (today - date_hired).days
        
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

        employee.last_credit_update = today
        employee.save()
