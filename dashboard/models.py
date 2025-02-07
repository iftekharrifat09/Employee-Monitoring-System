from django.contrib.auth.models import User
from django.db import models
from datetime import date
from django.utils.timezone import now
from datetime import datetime

class Position(models.Model):
    position = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.position
    
class Sector(models.Model):
    sector = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.sector

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, related_name="employees")
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, related_name="employees")
    def __str__(self):
        return self.user.username

class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(default=now)
    quit_time = models.TimeField(null=True, blank=True)  # Quit time, nullable

    def __str__(self):
        return f"{self.employee.user.username} - {self.date} {self.time} / {self.quit_time if self.quit_time else 'Not Quit Yet'}"

class AttendanceTimeSettings(models.Model):
    start_time = models.TimeField()  # Allowed check-in time
    end_time = models.TimeField()    # Allowed check-out time

    def __str__(self):
        return f"Attendance Time: {self.start_time} - {self.end_time}"
    
    
class AllowedEmail(models.Model):
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.email
    
class DefaultHoliday(models.Model):
    day = models.CharField(
        max_length=10,
        choices=[
            ('monday', 'Monday'),
            ('tuesday', 'Tuesday'),
            ('wednesday', 'Wednesday'),
            ('thursday', 'Thursday'),
            ('friday', 'Friday'),
            ('saturday', 'Saturday'),
            ('sunday', 'Sunday'),
        ],
        default='friday',  # Default holiday is Friday
    )

    def __str__(self):
        return f"Default Holiday: {self.get_day_display()}"
    

class MultiDefaultHoliday(models.Model):
    holiday_date = models.DateField()
    def __str__(self):
        return f"Holidays on {self.holiday_date}" 
    


class EmployeeHoliday(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="holidays")
    holiday_date = models.DateField()

    def __str__(self):
        return f"Holiday for {self.employee.name} on {self.holiday_date}"
    
class MessageBox(models.Model):
    name = models.CharField(max_length=100)  # Name of the sender (optional)
    email = models.EmailField()  # Email of the sender (optional)
    message = models.TextField()  # Message content
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for sorting

    def __str__(self):
        return f"Message from {self.name or 'Anonymous'} - {self.email}"
    
    

class Task(models.Model):
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_completed = models.BooleanField(default=False)
    is_delivered = models.BooleanField(default=False)
    extended_date = models.DateField(null=True, blank=True)
    revision_count = models.IntegerField(default=0)  # Tracks the number of revisions
    rejected_count = models.IntegerField(default=0) # Tracks the number of rejected

    def status(self):
        today = date.today()
        if self.is_completed:
            return "Completed"
        elif self.is_delivered:
            return "Pending Approval"
        elif self.extended_date and self.revision_count:
            return f"In Revision ({self.revision_count})"  # Show revision count
        elif today > self.end_date and not self.extended_date:
            return "Date Over"
        else:
            return "In Process"

    def __str__(self):
        return f"{self.title} - {self.employee.user.username}"
    

class TaskHistoryKeeper(models.Model):
    task_id = models.IntegerField()  # Store the task ID separately
    task_title = models.CharField(max_length=255)
    description = models.TextField()
    assigned_to = models.CharField(max_length=50, default='employee_name')  # The employee assigned the task
    start_date = models.DateField()
    end_date = models.DateField()
    extended_date = models.DateField(null=True, blank=True)
    revision_count = models.IntegerField(default=0)
    rejected_count = models.IntegerField(default=0)
    status = models.CharField(max_length=50)
    action_taken = models.CharField(max_length=50, choices=[('Approved', 'Approved'), ('Deleted', 'Deleted')])  # Track if task was approved or deleted
    action_date = models.DateTimeField(auto_now_add=True)  # Timestamp when stored

    def __str__(self):
        return f"{self.task_title} ({self.action_taken})"
    
class MonthSummary(models.Model):
    month = models.CharField(max_length=10, default=datetime.now().strftime("%B"))  # Example: "January"
    year = models.PositiveIntegerField(default=datetime.now().year)  # Example: 2024

    # Store employee details instead of ForeignKey (to keep records even if employee is deleted)
    employee_id = models.PositiveIntegerField()  
    employee_name = models.CharField(max_length=50)  

    total_workdays = models.PositiveIntegerField()
    total_present_days = models.PositiveIntegerField()
    total_holidays_taken = models.PositiveIntegerField()
    total_occasional_holidays = models.PositiveIntegerField()

    total_task_assigned = models.PositiveIntegerField(default=0)
    assigned_task_ids_with_title = models.TextField(blank=True, null=True)  # Store task IDs with titles

    total_task_completed = models.PositiveIntegerField(default=0)
    completed_task_ids_with_title = models.TextField(blank=True, null=True)  # Store completed task IDs with titles
    
    joining_date = models.DateTimeField(null=True, blank=True)
    leaving_date = models.DateTimeField(null=True, blank=True)

    employee_present_status = models.CharField(max_length=20, choices=[
        ("Running", "Running"),
        ("Removed", "Removed"),
    ], default="Running")

    @property
    def total_absent_days(self):
        """Dynamically calculates total absent days"""
        return self.total_workdays - self.total_present_days

    def __str__(self):
        return f"{self.employee_name} ({self.employee_id}) - {self.month} {self.year}"
    
    

class SystemState(models.Model):
    last_processed_month = models.CharField(max_length=10, null=True, blank=True)
    last_processed_year = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Last Reset: {self.last_processed_month} {self.last_processed_year}"
    



    
    

