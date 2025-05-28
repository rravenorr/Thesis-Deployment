from django.http import HttpResponseForbidden

class HROnlyMixin:
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and hasattr(user, 'employee'):
            if user.employee.department and user.employee.department.name == "Human Resources":
                return super().dispatch(request, *args, **kwargs)
        
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
