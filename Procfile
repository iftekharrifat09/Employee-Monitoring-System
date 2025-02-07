web: gunicorn employee_management.wsgi --log-file - 
#or works good with external database
web: python manage.py migrate && gunicorn employee_management.wsgi