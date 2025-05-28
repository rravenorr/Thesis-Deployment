# decorators.py
from django.http import HttpResponseForbidden

def hr_only(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if hasattr(request.user, 'employee'):
            employee = request.user.employee
            if employee.department.name == "Human Resources":
                return view_func(request, *args, **kwargs)
        html = """
        <html>
            <head>
                <title>403 Forbidden</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background-color: #f8d7da;
                        color: #721c24;
                        text-align: center;
                        padding-top: 100px;
                    }
                    .button {
                        margin-top: 20px;
                        padding: 10px 20px;
                        background-color: #721c24;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        cursor: pointer;
                    }
                    .button:hover {
                        background-color: #a94442;
                    }
                </style>
            </head>
            <body>
                <h1>403 - Forbidden</h1>
                <p>You are not authorized to access this page.</p>
                <button class="button" onclick="window.history.back()">Go Back</button>
            </body>
        </html>
        """
        return HttpResponseForbidden(html)
    return _wrapped_view
