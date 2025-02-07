from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib import messages
from .models import Employee, Attendance, AllowedEmail, DefaultHoliday, EmployeeHoliday, MessageBox, MultiDefaultHoliday, Task, TaskHistoryKeeper, MonthSummary, SystemState, AttendanceTimeSettings, Position, Sector
from .forms import EmployeeRegistrationForm, EmployeeUpdateForm, AllowedEmailForm, AdminSetPasswordForm, UserUpdateForm, DefaultHolidayForm, MultiDateHolidayForm, MultiDefaultHolidaysForm, MessageForm, TaskForm, AdminUpdateForm, AttendanceTimeForm, PositionForm, SectorForm
from django.utils.timezone import localdate
from calendar import monthrange
from django.utils.dateparse import parse_date
import calendar
from datetime import datetime, date
import pandas as pd
from django.utils.timezone import now, localtime
from django.http import HttpResponse
    
def home(request):
    return render(request, 'home.html')

def register(request):
    # Redirect if the user is already logged in
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = EmployeeRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            employee = Employee.objects.get(user=user)
            
            current_month = datetime.now().strftime("%B")
            current_year = datetime.now().year

            # Create a new MonthSummary entry for the employee
            MonthSummary.objects.create(
                month=current_month,
                year=current_year,
                employee_id=employee.id,
                employee_name=user.get_full_name() or user.username,  # Store full name if available
                total_workdays=0,
                total_present_days=0,
                total_holidays_taken=0,
                total_occasional_holidays=0,
                total_task_assigned=0,
                assigned_task_ids_with_title="",
                total_task_completed=0,
                completed_task_ids_with_title="",
                joining_date = datetime.now(),
                employee_present_status="Running"
            )
            messages.success(request, "Registration successful! Please log in to access your dashboard.")
            return redirect('login')  # Redirect to the login page after successful registration
        else:
            messages.error(request, "Registration failed. Please check the form for errors.")
    else:
        form = EmployeeRegistrationForm()

    return render(request, 'register.html', {'form': form})


def user_login(request):
    # Redirect if the user is already logged in
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid credentials. Please try again.")
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})

def filtered_employees(request):
    filter_type = request.GET.get('filter_type', 'all')  # Default to "all"
    sector_id = request.GET.get('sector') if filter_type == "filter" else None
    position_id = request.GET.get('position') if filter_type == "filter" else None

    employees = Employee.objects.all()
    sectors = Sector.objects.all()
    positions = Position.objects.all()

    if filter_type == "filter":
        if sector_id:
            employees = employees.filter(sector_id=sector_id)
        if position_id:
            employees = employees.filter(position_id=position_id)

    return employees, sectors, positions, sector_id, position_id, filter_type

@login_required
def dashboard(request):
    if request.user.is_staff:
        if request.method == 'POST':
            if 'default_holiday' in request.POST:
                form = DefaultHolidayForm(request.POST)
                if form.is_valid():
                    DefaultHoliday.objects.all().delete()  # Only one default holiday allowed
                    form.save()
                        
                    messages.success(request, "Default holiday updated successfully!")
                    return redirect('dashboard')

            # Handle individual holiday form submission
            elif 'employee_holiday' in request.POST:
                form = MultiDateHolidayForm(request.POST)
                if form.is_valid():
                    employee = form.cleaned_data['employee']
                    holiday_dates = form.cleaned_data['holiday_dates'].split(",")  # Split the dates by comma
                    
                    for date in holiday_dates:
                        date = date.strip()
                        EmployeeHoliday.objects.create(employee=employee, holiday_date=date)

                    messages.success(request, f"Holidays added for {employee.user.username} on {', '.join(holiday_dates)}.")
                    return redirect('dashboard')
            
            elif 'occasional_holidays' in request.POST:
                form = MultiDefaultHolidaysForm(request.POST)
                if form.is_valid():
                    holiday_dates = form.cleaned_data['holiday_dates'].split(",")  # Split the dates by comma
                    
                    for date in holiday_dates:
                        date = date.strip()
                        MultiDefaultHoliday.objects.create(holiday_date=date)
                        
                    messages.success(request, f"Occasional holidays added on {', '.join(holiday_dates)}.")
                    return redirect('dashboard')
            
            elif 'set_attendance_time' in request.POST:
                settings = AttendanceTimeSettings.objects.first()  # Fetch existing settings
                form = AttendanceTimeForm(request.POST, instance=settings)
                if form.is_valid():
                        form.save()
                        messages.success(request, "Working time updated successfully!")
                        return redirect("dashboard")
        else:
            form = AttendanceTimeForm(instance=AttendanceTimeSettings.objects.first())
                    
                

        today = localdate()
        total_days = monthrange(today.year, today.month)[1]

        # Get default holiday
        default_holiday = DefaultHoliday.objects.first()
        default_holiday_day = default_holiday.day if default_holiday else "friday"
        
        # filtering employees
        all_filtered_employees, sectors, positions, sector_id, position_id, filter_type = filtered_employees(request)

        # Subtract default holidays from total workdays
        all_holidays = []  # Initialize a list to track all holidays
        employees = Employee.objects.all()

        # Add all default holidays for the current month
        for day in range(1, total_days + 1):
            date = today.replace(day=day)
            if default_holiday and date.strftime("%A").lower() == default_holiday.day.lower():
                all_holidays.append(date)

        # Add employee-specific extra holidays
        for employee in employees:
            employee_holidays = EmployeeHoliday.objects.filter(employee=employee)
            for emp_holiday in employee_holidays:
                all_holidays.append(emp_holiday.holiday_date)
                
        total_occasional_holidays = MultiDefaultHoliday.objects.all()
        occasional_holidays = list(set([
            f"{holiday.holiday_date} ({holiday.holiday_date.strftime('%A')})"
            for holiday in total_occasional_holidays
        ])) 
        occasional_holidays.sort(key=lambda x: x.split(" ")[0])
        
        for occasional_day in total_occasional_holidays:
            all_holidays.append(occasional_day.holiday_date)

        all_holidays = sorted(set(all_holidays))  # Remove duplicates and sort the holidays

        total_holidays = len(all_holidays)
        workdays = total_days - total_holidays
        
        #updating month summary
        for employee in employees:
            employee_holidays_taken = EmployeeHoliday.objects.filter(employee=employee).count()
            
            # Calculate workdays for the employee
            total_holidays = len(all_holidays) + len(employee_holidays)
            workdays = total_days - total_holidays

            # Update the existing MonthSummary for the employee
            MonthSummary.objects.filter(
                month=today.strftime("%B"),
                year=today.year,
                employee_id=employee.id
            ).update(
                total_occasional_holidays=len(occasional_holidays),
                total_holidays_taken=employee_holidays_taken,
                total_workdays=workdays
            )
        

        occasional_holidays_form = MultiDefaultHolidaysForm()
        multi_date_form = MultiDateHolidayForm()
        allowed_emails = AllowedEmail.objects.all()
        default_form = DefaultHolidayForm(instance=default_holiday)
        
        settings = AttendanceTimeSettings.objects.first()
        attendance_time_form = AttendanceTimeForm(request.POST or None, instance=settings)
        context = {
            'employees': employees,
            'default_form': default_form,
            'workdays': workdays,
            'emails': allowed_emails,
            'occasional_holi_days': occasional_holidays,
            'multi_date_form': multi_date_form,
            'attendance_time_form':attendance_time_form,
            'occasional_holidays_form': occasional_holidays_form,
            'all_holidays': all_holidays,  # Pass the holiday list to the template
            'filtered_employees': all_filtered_employees,
            'sectors': sectors,
            'positions': positions,
            'selected_sector': sector_id,
            'selected_position': position_id,
            'filter_type': filter_type
        }
        return render(request, 'admin_dashboard.html', context)

    else:
        employee = Employee.objects.get(user=request.user)
        tasks = Task.objects.filter(employee=employee).order_by('end_date')
        today = localdate()
        attendance = Attendance.objects.filter(employee=employee)
        attendance_day = Attendance.objects.filter(employee=employee, date=today).first()
        today_with_day = today.strftime("%Y-%m-%d (%A)")
        total_days = monthrange(today.year, today.month)[1]
        
        # Fetch holidays for the employee
        default_holiday = DefaultHoliday.objects.first()
        employee_holidays = EmployeeHoliday.objects.filter(employee=employee)
        total_occasional_holidays = MultiDefaultHoliday.objects.all()
        # Create a formatted list of holidays for occasional holidays
        occasional_holidays = list(set([
            f"{holiday.holiday_date} ({holiday.holiday_date.strftime('%A')})"
            for holiday in total_occasional_holidays
        ])) 
        occasional_holidays.sort(key=lambda x: x.split(" ")[0])

        # Collect and format default holidays
        default_holidays = []
        if default_holiday:
            for day in range(1, total_days + 1):
                date = today.replace(day=day)
                if date.strftime("%A").lower() == default_holiday.day.lower():
                    default_holidays.append(f"{date} ({date.strftime('%A')})")

        # Collect and format extra holidays
        extra_holidays = list(set([f"{holiday.holiday_date} ({holiday.holiday_date.strftime('%A')})" for holiday in employee_holidays]))
        extra_holidays.sort(key=lambda x: x.split(" ")[0])
            
        # Combine all holidays for total calculation
        all_holiday_dates = sorted(set([h.split(" ")[0] for h in default_holidays + extra_holidays + occasional_holidays]))  # Remove duplicates
        
        #holidays counting
        extra_holiday_count = len(extra_holidays)
        default_holiday_count = len(default_holidays)
        occasional_holiday_count = len(occasional_holidays)
        total_holidays = len(all_holiday_dates)
        tasks = Task.objects.filter(employee=employee)
    
        workdays = total_days - total_holidays
        present_count = attendance.count()
        absent_count = workdays - present_count
        
        # Calculate percentages
        present_percentage = (present_count / workdays) * 100 if workdays > 0 else 0
        absent_percentage = (absent_count / workdays) * 100 if workdays > 0 else 0
        holidays_percentage = (extra_holiday_count / workdays) * 100 if workdays > 0 else 0

        context = {
            'today_date':today,
            'today':today_with_day,
            'employee': employee,
            'attendance': attendance,
            'attendance_day':attendance_day,
            'present_count': present_count,
            'absent_count': absent_count,
            'extra_holiday_count': extra_holiday_count,
            'default_holiday_count': default_holiday_count,
            'occasional_holiday_count': occasional_holiday_count,
            'total_days': workdays,
            'default_holidays': default_holidays,
            'extra_holidays': extra_holidays,
            'occasional_holidays':occasional_holidays,
            'total_holidays':total_holidays,
            'present_percentage': round(present_percentage, 2),
            'absent_percentage': round(absent_percentage, 2),
            'holidays_percentage': round(holidays_percentage, 2),
            'tasks': tasks,
        }
        return render(request, 'employee_dashboard.html', context)

@login_required
def admin_edit_profile(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    if request.method == "POST":
        user_form = AdminUpdateForm(request.POST, instance=request.user)

        if user_form.is_valid():
            user_form.save()
            messages.success(request, "Admin profile has been updated successfully!")
            return redirect("dashboard")  # Redirect to avoid resubmission

    else:
        user_form = AdminUpdateForm(instance=request.user)

    return render(request, "admin_edit_profile.html", {"user_form": user_form})


@login_required
def mark_attendance(request):
    employee = Employee.objects.get(user=request.user)
    today = localdate()
    current_time = localtime().time() 
    
    current_month = today.strftime("%B")
    current_year = today.year
    
    settings = AttendanceTimeSettings.objects.first()
    if settings and not (settings.start_time <= current_time <= settings.end_time):
        messages.error(request, "You can only mark attendance during the allowed time.")
        return redirect("dashboard")
    
    # Check if today is a default holiday
    default_holiday = DefaultHoliday.objects.first()
    is_default_holiday = (
        default_holiday and today.strftime("%A").lower() == default_holiday.day
    )

    # Check if today is an individual holiday for the employee
    is_employee_holiday = EmployeeHoliday.objects.filter(employee=employee, holiday_date=today).exists()
    
    attendance = Attendance.objects.filter(employee=employee, date=today).first()
    
    if is_default_holiday or is_employee_holiday:
        messages.error(request, "It's your holiday, enjoy your day!")
    elif attendance:
        messages.error(request, "Attendance already given for today!")
    else:
        Attendance.objects.create(employee=employee, date=today, time=current_time)
        # Filter and update the employee's MonthSummary
        month_summary = MonthSummary.objects.filter(
            employee_id=employee.id,
            month=current_month,
            year=current_year
        ).first()

        if month_summary:
            month_summary.total_present_days += 1
            month_summary.save()
        else:
            # If no record exists, create a new one
            MonthSummary.objects.create(
                month=current_month,
                year=current_year,
                employee_id=employee.id,
                employee_name=employee.user.get_full_name() or employee.user.username,
                total_workdays=0,
                total_present_days=1,  # First attendance for the month
                total_holidays_taken=0,
                total_occasional_holidays=0,
                total_task_assigned=0,
                assigned_task_ids_with_title="",
                total_task_completed=0,
                completed_task_ids_with_title="",
                employee_present_status="Running"
            )
        messages.success(request, f"Attendance marked successfully at {current_time.strftime('%I:%M %p')}!")

    return redirect('dashboard')

@login_required
def quit(request):
    employee = Employee.objects.get(user=request.user)
    today = localdate()

    # Get the attendance record for today
    attendance = Attendance.objects.filter(employee=employee, date=today).first()

    if attendance and attendance.quit_time is None:
        # Update quit time
        attendance.quit_time = localtime().time()
        attendance.save()
        messages.success(request, f"Quit time recorded at {attendance.quit_time.strftime('%I:%M %p')}")
    else:
        messages.error(request, "You have not marked attendance yet or quit time is already recorded.")

    return redirect('dashboard') 

@login_required
def update_employee(request, employee_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    employee = get_object_or_404(Employee, id=employee_id)
    user = employee.user

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        employee_form = EmployeeUpdateForm(request.POST, instance=employee)

        if user_form.is_valid() and employee_form.is_valid():
            user_form.save()
            employee_form.save()
            messages.success(request, "Employee updated successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Failed to update employee. Please check the forms for errors.")
    else:
        user_form = UserUpdateForm(instance=user)
        employee_form = EmployeeUpdateForm(instance=employee)

    return render(request, 'update_employee.html', {
        'user_form': user_form,
        'employee_form': employee_form,
    })
@login_required
def self_update_employee(request):

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)

        if user_form.is_valid():
            user_form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Failed to update Profile. Please check the forms for errors.")
    else:
        user_form = UserUpdateForm(instance=request.user)
    return render(request, 'update_employee.html', {
        'user_form': user_form,'type':'for_employee'
    })

@login_required
def add_allowed_email(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AllowedEmailForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Email added successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Failed to add email. Please check the form for errors.")
    else:
        form = AllowedEmailForm()
    return render(request, 'add_allowed_email.html', {'form': form})

@login_required
def delete_allowed_email(request, email_id):
    if not request.user.is_staff:
        return redirect('dashboard')

    allowed_email = get_object_or_404(AllowedEmail, id=email_id)
    allowed_email.delete()

    messages.success(request, "Allowed email deleted successfully!")
    return redirect('dashboard')  # Redirect to a relevant page

@login_required
def delete_employee(request, employee_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    employee = get_object_or_404(Employee, id=employee_id)
    user = employee.user
    
    MonthSummary.objects.filter(employee_id=employee.id).update(employee_present_status="Removed", leaving_date=datetime.now())
    
    allowed_email = AllowedEmail.objects.filter(email=user.email).first()
    if allowed_email:
        allowed_email.delete()
        
    employee.delete()
    user.delete()
    messages.success(request, "Employee deleted successfully!")
    return redirect('dashboard')

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Password changed successfully!")
            return redirect('login')
        else:
            messages.error(request, "Failed to change password. Please check the form for errors.")
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'change_password.html', {'form': form})

@login_required
def admin_set_password(request, user_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = AdminSetPasswordForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Password for {user.username} updated successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Failed to update password. Please check the form for errors.")
    else:
        form = AdminSetPasswordForm(instance=user)
    return render(request, 'admin_set_password.html', {'form': form, 'user': user})

@login_required
def employee_attendance_detail(request, employee_id):
    if not request.user.is_staff:
        return redirect('dashboard')

    employee = get_object_or_404(Employee, id=employee_id)
    attendance = Attendance.objects.filter(employee=employee)

    today = localdate()
    total_days = monthrange(today.year, today.month)[1]

    # Fetch holidays
    default_holiday = DefaultHoliday.objects.first()
    total_occasional_holidays = MultiDefaultHoliday.objects.all()
    occasional_holidays = list(set([
        f"{holiday.holiday_date} ({holiday.holiday_date.strftime('%A')})"
        for holiday in total_occasional_holidays
    ]))
    occasional_holidays.sort(key=lambda x: datetime.strptime(x.split(" ")[0], "%Y-%m-%d"))

    employee_holidays = EmployeeHoliday.objects.filter(employee=employee)

    # Collect default holidays
    default_holidays = []
    if default_holiday:
        for day in range(1, total_days + 1):
            date = today.replace(day=day)
            if date.strftime("%A").lower() == default_holiday.day.lower():
                default_holidays.append(f"{date} ({date.strftime('%A')})")

    # Collect extra holidays
    extra_holidays = list(set([f"{holiday.holiday_date} ({holiday.holiday_date.strftime('%A')})" for holiday in employee_holidays]))
    extra_holidays.sort(key=lambda x: x.split(" ")[0])

    all_holiday_dates = sorted(set([h.split(" ")[0] for h in default_holidays + extra_holidays + occasional_holidays]))  

    # Holiday calculations
    extra_holiday_count = len(extra_holidays)
    default_holiday_count = len(default_holidays)
    occasional_holiday_count = len(occasional_holidays)
    total_holidays = len(all_holiday_dates)
    
    workdays = total_days - total_holidays

    present_count = attendance.count()
    absent_count = workdays - present_count
    
    workday_percentage = (workdays / total_days) * 100 if workdays > 0 else 0
    present_percentage = (present_count / workdays) * 100 if workdays > 0 else 0
    absent_percentage = (absent_count / workdays) * 100 if workdays > 0 else 0
    holidays_percentage = (extra_holiday_count / workdays) * 100 if workdays > 0 else 0

    # **Task Management**
    tasks = Task.objects.filter(employee=employee)

    if request.method == 'POST':
        task_form = TaskForm(request.POST)
        if task_form.is_valid():
            task = task_form.save(commit=False)
            task.employee = employee
            task.save()
            
            # Get or create the MonthSummary for the employee for the current month
            today = localdate()
            month_summary, created = MonthSummary.objects.get_or_create(
                month=today.strftime("%B"),
                year=today.year,
                employee_id=employee.id,
                defaults={"employee_name": employee.user.get_full_name() or employee.user.username}
            )

            # Add the new task to the assigned task list in MonthSummary
            assigned_task_ids_with_title = month_summary.assigned_task_ids_with_title
            task_info = f"{task.id}: {task.title}"
            
            # If there are already assigned tasks, append the new task
            if assigned_task_ids_with_title:
                assigned_task_ids_with_title += f", {task_info}"
            else:
                assigned_task_ids_with_title = task_info

            month_summary.assigned_task_ids_with_title = assigned_task_ids_with_title
            month_summary.total_task_assigned += 1
            month_summary.save()
            
            messages.success(request, "Task assigned successfully!")
            return redirect('employee_attendance_detail', employee_id=employee.id)
    else:
        task_form = TaskForm()

    context = {
        'employee': employee,
        'attendance': attendance,
        'present_count': present_count,
        'absent_count': absent_count,
        'extra_holiday_count': extra_holiday_count,
        'default_holiday_count': default_holiday_count,
        'occasional_holiday_count': occasional_holiday_count,
        'total_days': workdays,
        'default_holidays': default_holidays,
        'extra_holidays': extra_holidays,
        'total_holidays': total_holidays,
        'present_percentage': round(present_percentage, 2),
        'absent_percentage': round(absent_percentage, 2),
        'holidays_percentage': round(holidays_percentage, 2),
        'workday_percentage': round(workday_percentage, 2),
        'tasks': tasks,
        'task_form': task_form,
        'today': today,
    }

    return render(request, 'employee_attendance_detail.html', context)

@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out')
    return redirect('login')


@login_required
def add_employee_holiday(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    if request.method == "POST":
        employee_id = request.POST.get('employee_id')
        selected_dates = request.POST.getlist('holiday_dates')  # Multiple dates

        if not employee_id or not selected_dates:
            messages.error(request, "Please select an employee and dates.")
            return redirect('dashboard')

        employee = Employee.objects.get(id=employee_id)
        

        for date in selected_dates:
            holiday_date = parse_date(date)  # Ensure it's a valid date
            
            if holiday_date:
                EmployeeHoliday.objects.create(employee=employee, holiday_date=holiday_date)

        messages.success(request, f"Holidays added successfully for {employee.user.username}.")
        return redirect('dashboard')

    employees = Employee.objects.all()
    return render(request, 'add_employee_holiday.html', {'employees': employees})
    
    
@login_required
def set_default_holiday(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    if request.method == 'POST':
        selected_day = request.POST.get('day')
        
        # Update or create the default holiday
        default_holiday, created = DefaultHoliday.objects.get_or_create(id=1)
        default_holiday.day = selected_day
        default_holiday.save()

        messages.success(request, f"Default holiday set to {selected_day.capitalize()}!")
        return redirect('dashboard')
    

@login_required
def delete_extra_holiday_by_date(request, employee_id, holiday_date):
    if not request.user.is_staff:
        return redirect('dashboard')
    if request.method == "POST":
        try:
            holiday_date_cleaned = holiday_date.split(" ")[0]
            holiday_date_obj = datetime.strptime(holiday_date_cleaned, "%Y-%m-%d").date()

            # Use filter() to find all holidays for the employee on the given date
            holidays = EmployeeHoliday.objects.filter(employee_id=employee_id, holiday_date=holiday_date_obj)

            # If holidays exist, delete them
            if holidays.exists():
                holidays.delete()
                messages.success(request, "Holiday removed successfully.")
            else:
                messages.error(request, "Holiday not found.")
        except ValueError as e:
            messages.error(request, f"Invalid date format: {e}")

    return redirect("employee_attendance_detail", employee_id=employee_id)
@login_required
def delete_occasional_holiday_using_date(request, holiday_date):
    print(holiday_date)
    if not request.user.is_staff:
        return redirect('dashboard')
    if request.method == "POST":
        try:
            print("this is post")
            holiday_date_cleaned = holiday_date.split(" ")[0]
            holiday_date_obj = datetime.strptime(holiday_date_cleaned, "%Y-%m-%d").date()

            # Use filter() to find all holidays for the employee on the given date
            holidays = MultiDefaultHoliday.objects.filter(holiday_date=holiday_date_obj)

            # If holidays exist, delete them
            if holidays.exists():
                holidays.delete()
                messages.success(request, "Holiday removed successfully.")
            else:
                messages.error(request, "Holiday not found.")
        except ValueError as e:
            messages.error(request, f"Invalid date format: {e}")

    return redirect("dashboard")


def contact_view(request):
    if request.user.is_staff:
        return redirect('dashboard')
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your message has been sent successfully!")
            return redirect('login')  # Redirect to the same page after submission
    else:
        form = MessageForm()
    
    return render(request, 'contact.html', {'form': form})

@login_required
def message_list(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    messages = MessageBox.objects.all().order_by('-created_at')  # Fetch messages, newest first
    return render(request, 'admin_messages.html', {'user_messages': messages})

@login_required
def delete_message(request, message_id): 
    if not request.user.is_staff:
        return redirect('dashboard')
    message = get_object_or_404(MessageBox, id=message_id)
    message.delete()
    messages.success(request, "Message deleted successfully!")
    return redirect('admin_messages') 

# Edit Task
@login_required
def edit_task(request, task_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    task = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, "Task updated successfully!")
            return redirect('view_all_tasks')
    else:
        form = TaskForm(instance=task)
    return render(request, 'edit_task.html', {'form': form, 'task': task})

# Delete Task
@login_required
def delete_task(request, task_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    task = get_object_or_404(Task, id=task_id)
    employee_id = task.employee.id
    name = f"{task.employee.user.first_name} {task.employee.user.last_name}"
    # ✅ Store task history before deleting
    TaskHistoryKeeper.objects.create(
        task_id=task.id,
        task_title=task.title,
        description=task.description,
        assigned_to= name,
        start_date=task.start_date,
        end_date=task.end_date,
        extended_date=task.extended_date,
        revision_count=task.revision_count,
        rejected_count=task.rejected_count,
        status=task.status(),
        action_taken="Deleted",
        action_date=now()
    )
    task.delete()
    messages.success(request, "Task deleted successfully!")
    return redirect('employee_attendance_detail', employee_id=employee_id) 

@login_required
def view_all_tasks(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    today = localdate()
    tasks = Task.objects.select_related('employee').order_by('-start_date')  # Fetch all tasks sorted by start date
    return render(request, 'view_all_tasks.html', {'tasks': tasks, 'today': today})

@login_required
def deliver_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, employee=request.user.employee)
    
    if not task.is_completed:
        task.is_delivered = True  # Mark as delivered but not completed
        task.save()
        messages.success(request, "Task delivery requested. Awaiting admin approval.")
    
    return redirect('view_all_tasks')

@login_required
def approve_task(request, task_id):
    if not request.user.is_staff:
        return redirect('dashboard')

    task = get_object_or_404(Task, id=task_id)
    emp_id = task.employee.id
    if task.is_delivered:
        task.is_completed = True  # Mark task as completed
        task.is_delivered = False  # Reset delivery request
        task.save()

        # Get the current month and year
        today = localdate()
        current_month = today.strftime("%B")
        current_year = today.year

        # Filter MonthSummary by employee and current month/year
        month_summary = MonthSummary.objects.filter(
            employee_id=emp_id,
            month=current_month,
            year=current_year
        ).first()

        if month_summary:
            # Add the completed task to the completed_task_ids_with_title field
            completed_task_ids_with_title = month_summary.completed_task_ids_with_title
            task_info = f"{task.id}: {task.title}"

            # If there are already completed tasks, append the new task
            if completed_task_ids_with_title:
                completed_task_ids_with_title += f", {task_info}"
            else:
                completed_task_ids_with_title = task_info

            # Update the completed tasks field
            month_summary.completed_task_ids_with_title = completed_task_ids_with_title

            # Increment the total_task_completed count by 1
            month_summary.total_task_completed += 1

            # Save the updated MonthSummary
            month_summary.save()
            
        messages.success(request, f"Task '{task.title}' has been marked as completed.")

    return redirect(request.META.get('HTTP_REFERER', 'view_all_tasks'))

@login_required
def reject_task(request, task_id):
    if not request.user.is_staff:
        return redirect('dashboard')

    task = get_object_or_404(Task, id=task_id)

    if task.is_delivered:
        task.is_delivered = False  # Reset delivery status
        task.rejected_count += 1 # Number of rejected tasks
        task.save()
        messages.warning(request, f"Task '{task.title}' has been rejected. The employee can deliver again.")

    return redirect(request.META.get('HTTP_REFERER', 'view_all_tasks'))  # Redirect back to admin panel

@login_required
def extend_task_date(request, task_id):
    if not request.user.is_staff:
        return redirect('dashboard')

    task = get_object_or_404(Task, id=task_id)

    if request.method == 'POST':
        new_end_date_str = request.POST.get('new_end_date')

        if new_end_date_str:
            new_end_date = datetime.strptime(new_end_date_str, "%Y-%m-%d").date()  # Convert to date format
            today = date.today()

            # Validation checks
            if new_end_date < today:
                messages.error(request, "Extended date must be greater than or equal today.")
            elif new_end_date <= task.end_date:
                messages.error(request, "Extended date must be greater than the current end date.")
            else:
                # Update end_date with the new extension
                task.end_date = new_end_date  
                task.extended_date = new_end_date
                task.revision_count += 1  # Increase revision count
                task.save()

                messages.success(request, f"Task '{task.title}' deadline extended to {new_end_date}. Revision count: {task.revision_count}")
                return redirect('view_all_tasks')

    return render(request, 'extend_task_date.html', {'task': task})


def all_employee_attendance_details(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    employees = Employee.objects.all()
    today = localdate()
    total_days = monthrange(today.year, today.month)[1]

    attendance_summary = []

    for employee in employees:
        # Fetch attendance data for the employee
        attendance = Attendance.objects.filter(employee=employee)
        
        # Fetch task data for the employee
        tasks = Task.objects.filter(employee=employee)
        
        # Initialize counters for task statuses
        total_tasks = tasks.count()
        completed_tasks = 0
        pending_tasks = 0
        in_process_tasks = 0
        in_revision_tasks = 0
        date_over_tasks = 0
        
        # Categorize tasks based on the status method
        for task in tasks:
            status = task.status()  # Get the task status using the status method
            if status == 'Completed':
                completed_tasks += 1
            elif status == 'Pending Approval':
                pending_tasks += 1
            elif status == 'In Process':
                in_process_tasks += 1
            elif status.startswith('In Revision'):
                in_revision_tasks += 1
            elif status == 'Date Over':
                date_over_tasks += 1
        
        # Fetch holidays
        default_holiday = DefaultHoliday.objects.first()
        employee_holidays = EmployeeHoliday.objects.filter(employee=employee)
        total_occasional_holidays = MultiDefaultHoliday.objects.all()

        # Format occasional holidays
        occasional_holidays = list(set([ 
            f"{holiday.holiday_date} ({holiday.holiday_date.strftime('%A')})"
            for holiday in total_occasional_holidays
        ])) 
        occasional_holidays.sort(key=lambda x: x.split(" ")[0])

        # Collect default holidays
        default_holidays = []
        if default_holiday:
            for day in range(1, total_days + 1):
                date = today.replace(day=day)
                if date.strftime("%A").lower() == default_holiday.day.lower():
                    default_holidays.append(f"{date} ({date.strftime('%A')})")

        # Collect extra holidays
        extra_holidays = list(set([f"{holiday.holiday_date} ({holiday.holiday_date.strftime('%A')})" for holiday in employee_holidays]))
        extra_holidays.sort(key=lambda x: x.split(" ")[0])
            
        # Combine all holidays
        all_holiday_dates = sorted(set([h.split(" ")[0] for h in default_holidays + extra_holidays + occasional_holidays]))

        # Holiday counts
        extra_holiday_count = len(extra_holidays)
        default_holiday_count = len(default_holidays)
        occasional_holiday_count = len(occasional_holidays)
        total_holidays = len(all_holiday_dates)

        # Calculate workdays, present, and absent days
        workdays = total_days - total_holidays
        present_count = attendance.count()
        absent_count = workdays - present_count

        # Append the employee's attendance and task summary to the list
        attendance_summary.append({
            "employee_name": employee.user,  # Name of the employee
            "total_workdays": workdays,
            "present": present_count,
            "absent": absent_count,
            "default_holidays": default_holiday_count,
            "occasional_holidays": occasional_holiday_count,
            "extra_holidays": extra_holiday_count,
            "total_holidays": total_holidays,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "in_process_tasks": in_process_tasks,
            "in_revision_tasks": in_revision_tasks,
            "date_over_tasks": date_over_tasks,
        })
        
    # ✅ Export to Excel if requested
    if "export" in request.GET:
        df = pd.DataFrame(attendance_summary)
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="Employee_Attendance_Summary.xlsx"'

        with pd.ExcelWriter(response, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="All Employee Activity Summary")

        return response

    # Render the data in the 'attendance_summary.html' template
    return render(request, 'employee_task_and_attendance_status.html', {"attendance_summary": attendance_summary})


@login_required
def task_history_view(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    task_history = TaskHistoryKeeper.objects.all().order_by('-action_date')  # Show latest actions first
    return render(request, 'task_history.html', {'task_history': task_history})


@login_required
def delete_task_history(request, history_id):
    if not request.user.is_staff:  # Ensure only admins can delete
        return redirect('dashboard')

    task_history = get_object_or_404(TaskHistoryKeeper, id=history_id)
    task_history.delete()
    messages.success(request, "Task history deleted successfully!")

    return redirect('task_history')


def export_task_history_to_excel(request):
    if not request.user.is_staff:  # Ensure only admins can delete
        return redirect('dashboard')
    # Get all task history data
    task_history = TaskHistoryKeeper.objects.all()

    # Prepare data for the Excel file
    data = []
    for task in task_history:
        data.append({
            "Task ID": task.task_id,
            "Title": task.task_title,
            "Description": task.description,
            "Assigned To": task.assigned_to,
            "Start Date": task.start_date.strftime("%Y-%m-%d"),
            "End Date": task.end_date.strftime("%Y-%m-%d"),
            "Extended Date": task.extended_date.strftime("%Y-%m-%d") if task.extended_date else "N/A",
            "Revisions": task.revision_count,
            "Rejections": task.rejected_count,
            "Status": task.status,
            "Action Taken": task.action_taken,
            "Action Date": task.action_date.strftime("%Y-%m-%d %H:%M:%S"),
        })

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Create HTTP response for Excel file
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="Task_History.xlsx"'

    # Save the DataFrame to an Excel file in memory
    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Task History")

    return response



@login_required
def view_all_month_summaries(request):
    if not request.user.is_staff:  # Ensure only admins can delete
        return redirect('dashboard')
    # Get the current month and year
    today = date.today()
    current_month = today.strftime("%B")
    current_year = today.year

    # Retrieve all MonthSummary entries for the current month and year
    month_summaries = MonthSummary.objects.filter(month=current_month, year=current_year)

    # Process the assigned and completed task strings into lists
    for summary in month_summaries:
        if summary.assigned_task_ids_with_title:
            summary.assigned_task_list = [task.strip() for task in summary.assigned_task_ids_with_title.split(",")]
        else:
            summary.assigned_task_list = []  # Empty list if no assigned tasks

        if summary.completed_task_ids_with_title:
            summary.completed_task_list = [task.strip() for task in summary.completed_task_ids_with_title.split(",")]
        else:
            summary.completed_task_list = []  # Empty list if no completed tasks

    return render(request, 'all_month_summaries.html', {
        'month_summaries': month_summaries,
        'month': current_month,
        'year': current_year
    })

@login_required
def delteMonthSummary(request, id):
    if not request.user.is_staff:  # Ensure only admins can delete
        return redirect('dashboard')

    month_summary = get_object_or_404(MonthSummary, id=id)
    month_summary.delete()
    messages.success(request, "Month Summary deleted successfully!")

    return redirect('view_all_month_summaries')


@login_required
def export_month_summaries_to_excel(request):
    if not request.user.is_staff:  # Ensure only admins can delete
        return redirect('dashboard')
    # Get the current month and year
    today = date.today()
    current_month = today.strftime("%B")
    current_year = today.year
    today_date_str = today.strftime("%Y-%m-%d") 
    
    # Retrieve all MonthSummary entries for the current month and year
    month_summaries = MonthSummary.objects.filter(month=current_month, year=current_year)

    # Convert MonthSummary queryset into a list of dictionaries for Pandas DataFrame
    month_summary_data = [
        {
            'Employee Name': summary.employee_name,
            'Employee ID': summary.employee_id,
            'Total Workdays': summary.total_workdays,
            'Total Present Days': summary.total_present_days,
            'Total Holidays Taken': summary.total_holidays_taken,
            'Total Occasional Holidays': summary.total_occasional_holidays,
            'Total Task Assigned': summary.total_task_assigned,
            'Assigned Tasks': summary.assigned_task_ids_with_title,
            'Total Task Completed': summary.total_task_completed,
            'Completed Tasks': summary.completed_task_ids_with_title,
            'Employee Status': summary.employee_present_status
        }
        for summary in month_summaries
    ]

    # Create a Pandas DataFrame
    df = pd.DataFrame(month_summary_data)

    # Create an HTTP response with the Excel file
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response['Content-Disposition'] = f'attachment; filename="month_summary_{current_month}_{current_year}_{today_date_str}.xlsx"'

    # Write the DataFrame to the Excel file
    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name='Month Summary')

    return response



@login_required
def reset_attendance(request):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('dashboard')

    today = localdate()
    current_month = today.strftime("%B")
    current_year = today.year

    # Get or create SystemState object
    system_state, created = SystemState.objects.get_or_create(id=1)

    if system_state.last_processed_month == current_month and system_state.last_processed_year == current_year:
        messages.error(request, "Attendance has already been reset for this month.")
    else:
        # Delete all attendance records
        Attendance.objects.all().delete()
        
        # Update system state
        system_state.last_processed_month = current_month
        system_state.last_processed_year = current_year
        system_state.save()

        messages.success(request, "All attendance records have been cleared for the new month.")

    return redirect('dashboard')


@login_required
def add_position(request):
    if not request.user.is_staff:  # Ensure only admins can delete
        return redirect('dashboard')
    if request.method == 'POST':
        form = PositionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Position added successfully!")
            return redirect('list_positions')  # Redirect to position list page
        else:
            messages.error(request, "Error adding position. Please try again.")
    else:
        form = PositionForm()
    
    return render(request, 'add_position.html', {'form': form})

@login_required
def add_sector(request):
    if not request.user.is_staff:  # Ensure only admins can delete
        return redirect('dashboard')
    if request.method == 'POST':
        form = SectorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Sector added successfully!")
            return redirect('list_sectors')  # Redirect to sector list page
        else:
            messages.error(request, "Error adding sector. Please try again.")
    else:
        form = SectorForm()
    
    return render(request, 'add_sector.html', {'form': form})

@login_required
def list_positions(request):
    if not request.user.is_staff:  # Ensure only admins can delete
        return redirect('dashboard')
    positions = Position.objects.all()
    return render(request, 'list_positions.html', {'positions': positions})

@login_required
def list_sectors(request):
    if not request.user.is_staff:  # Ensure only admins can delete
        return redirect('dashboard')
    sectors = Sector.objects.all()
    return render(request, 'list_sectors.html', {'sectors': sectors})

@login_required
def delete_position(request, position_id):
    if not request.user.is_staff:  # Ensure only admins can delete
        return redirect('dashboard')
    position = get_object_or_404(Position, id=position_id)
    if request.method == "POST":
        position.delete()
        messages.success(request, "Position deleted successfully!")
        return redirect('list_positions')
    return render(request, 'dashboard/delete_position.html', {'position': position})

@login_required
def delete_sector(request, sector_id):
    if not request.user.is_staff:  # Ensure only admins can delete
        return redirect('dashboard')
    sector = get_object_or_404(Sector, id=sector_id)
    if request.method == "POST":
        sector.delete()
        messages.success(request, "Sector deleted successfully!")
        return redirect('list_sectors')
    return render(request, 'dashboard/delete_sector.html', {'sector': sector})

def display_all_employees_to_employee(request):
    employees = Employee.objects.all()
    return render(request, 'display_all_employees_to_employee.html', {'employees': employees})

