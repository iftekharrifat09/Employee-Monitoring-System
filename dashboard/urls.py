from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-edit/', views.admin_edit_profile, name='admin_edit'),
    path('mark_attendance/', views.mark_attendance, name='mark_attendance'),
    path('quit/', views.quit, name='quit'),
    path('update_employee/<int:employee_id>/', views.update_employee, name='update_employee'),
    path('my-profile-update/', views.self_update_employee, name='my_profile_update'),
    path('add_allowed_email/', views.add_allowed_email, name='add_allowed_email'),
    path('delete_employee/<int:employee_id>/', views.delete_employee, name='delete_employee'),
    path('change_password/', views.change_password, name='change_password'),
    path('admin_set_password/<int:user_id>/', views.admin_set_password, name='admin_set_password'),
    path('employee_details/<int:employee_id>/', views.employee_attendance_detail, name='employee_attendance_detail'),
    path('set_default_holiday/', views.set_default_holiday, name='set_default_holiday'),
    path('add_employee_holiday/', views.add_employee_holiday, name='add_employee_holiday'),
    path('delete-allowed-email/<int:email_id>/', views.delete_allowed_email, name='delete_allowed_email'),
    
    path(
        'delete-extra-holiday/<int:employee_id>/<str:holiday_date>/',
        views.delete_extra_holiday_by_date,
        name='delete_extra_holiday_by_date'
    ),
    path(
        'delete-occasional-holiday/<str:holiday_date>/',
        views.delete_occasional_holiday_using_date,
        name='delete_occasional_holiday'
    ),
    path('contact/', views.contact_view, name='contact'),
    path('messages/', views.message_list, name='admin_messages'),
    path('messages/delete/<int:message_id>/', views.delete_message, name='delete_message'),
    path('task/deliver/<int:task_id>/', views.deliver_task, name='deliver_task'),
    path('tasks/edit/<int:task_id>/', views.edit_task, name='edit_task'),
    path('tasks/delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('all-tasks/', views.view_all_tasks, name='view_all_tasks'),
    path('deliver_task/<int:task_id>/', views.deliver_task, name='deliver_task'),
    path('approve_task/<int:task_id>/', views.approve_task, name='approve_task'),
    path('extend_task_date/<int:task_id>/', views.extend_task_date, name='extend_task_date'),
    path('reject_task/<int:task_id>/', views.reject_task, name='reject_task'),
    path('attendance-summary/', views.all_employee_attendance_details, name='attendance_summary'),
    path('task-history/', views.task_history_view, name='task_history'),
    path('task-history/delete/<int:history_id>/', views.delete_task_history, name='delete_task_history'),
    path("export-task-history/", views.export_task_history_to_excel, name="export_task_history"),
    path("attendance-summary/", views.all_employee_attendance_details, name="attendance_summary"),
    path('month-summaries/', views.view_all_month_summaries, name='view_all_month_summaries'),
    path('month-summary/delete/<int:id>/', views.delteMonthSummary, name='delete_month_summary'),
    path("export-month-summary/", views.export_month_summaries_to_excel, name="export_month_summary"),
    path('reset-attendance/', views.reset_attendance, name='reset_attendance'),
    path('add-position/', views.add_position, name='add_position'),
    path('add-sector/', views.add_sector, name='add_sector'),
    path('positions/', views.list_positions, name='list_positions'),
    path('sectors/', views.list_sectors, name='list_sectors'),
    path('delete-position/<int:position_id>/', views.delete_position, name='delete_position'),
    path('delete-sector/<int:sector_id>/', views.delete_sector, name='delete_sector'),
    path('display-employees-to-employee/', views.display_all_employees_to_employee, name='display_employees_to_employee'),



]
