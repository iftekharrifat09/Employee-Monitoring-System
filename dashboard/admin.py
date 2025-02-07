from django.contrib import admin
from . import models
# Register your models here.
admin.site.register(models.Employee)
admin.site.register(models.Attendance)
admin.site.register(models.AllowedEmail)
admin.site.register(models.Position)
admin.site.register(models.Sector)
admin.site.register(models.AttendanceTimeSettings)
admin.site.register(models.DefaultHoliday)
admin.site.register(models.MultiDefaultHoliday)
admin.site.register(models.EmployeeHoliday)
admin.site.register(models.MessageBox)
admin.site.register(models.Task)
admin.site.register(models.TaskHistoryKeeper)
admin.site.register(models.MonthSummary)
admin.site.register(models.SystemState)