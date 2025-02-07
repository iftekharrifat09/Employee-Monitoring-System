from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, UserChangeForm
from django.contrib.auth.models import User
from .models import Employee, AllowedEmail, DefaultHoliday, EmployeeHoliday, MessageBox, Task, AttendanceTimeSettings, Position, Sector

class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['position']
        widgets = {
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Position Name'}),
        }

class SectorForm(forms.ModelForm):
    class Meta:
        model = Sector
        fields = ['sector']
        widgets = {
            'sector': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Sector Name'}),
        }
class EmployeeRegistrationForm(UserCreationForm):
    email = forms.EmailField()
    sector = forms.ModelChoiceField(
        queryset=Sector.objects.all(),
        empty_label="Select Sector",
        required=True
    )
    
    position = forms.ModelChoiceField(
        queryset=Position.objects.all(),
        empty_label="Select Position",
        required=True
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'sector', 'position']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not AllowedEmail.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is not allowed. Please contact admin.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            Employee.objects.create(
                user=user, 
                sector=self.cleaned_data['sector'], 
                position=self.cleaned_data['position']
            )
        return user

class EmployeeUpdateForm(UserChangeForm):
    password = None
    class Meta:
        model = Employee
        fields = ['sector', 'position']
        

class AllowedEmailForm(forms.ModelForm):
    class Meta:
        model = AllowedEmail
        fields = ['email']
        
class AdminUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"] 

class AdminSetPasswordForm(forms.ModelForm):
    new_password = forms.CharField(widget=forms.PasswordInput, label="New Password")

    class Meta:
        model = User
        fields = []

    def save(self, commit=True):
        user = self.instance
        user.set_password(self.cleaned_data['new_password'])
        if commit:
            user.save()
        return user

class UserUpdateForm(UserChangeForm):
    password = None
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        
class DefaultHolidayForm(forms.ModelForm):
    class Meta:
        model = DefaultHoliday
        fields = ['day']

class MultiDateHolidayForm(forms.Form):
    employee = forms.ModelChoiceField(queryset=Employee.objects.all(), label="Select Employee",empty_label="Select Employee")
    holiday_dates = forms.CharField(widget=forms.TextInput(attrs={'class': 'multi-date-picker', 'placeholder': 'Select multiple dates'}), label="Holiday Dates")
    
class MultiDefaultHolidaysForm(forms.Form):
    holiday_dates = forms.CharField(widget=forms.TextInput(attrs={'class': 'multi-date-picker', 'placeholder': 'Select multiple dates'}), label="Holiday Dates")
        

class MessageForm(forms.ModelForm):
    class Meta:
        model = MessageBox
        fields = ['name', 'email', 'message']
        

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date cannot be after end date.")
        
        return cleaned_data
    

class AttendanceTimeForm(forms.ModelForm):
    class Meta:
        model = AttendanceTimeSettings
        fields = ["start_time", "end_time"]
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'timePicker'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'timePicker'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time:
            if start_time >= end_time:
                raise forms.ValidationError("End time must be later than start time.")
        return cleaned_data