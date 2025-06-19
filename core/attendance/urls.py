from django.urls import path
from core.attendance.views import Attendance

app_name = 'attendance'

urlpatterns = [
    # ============ WORK SCHEDULE URLS ============
    path('schedules/', Attendance.WorkScheduleListView.as_view(), name='work_schedule_list'),
    path('schedules/create/', Attendance.WorkScheduleCreateView.as_view(), name='work_schedule_create'),
    path('schedules/<int:pk>/', Attendance.WorkScheduleDetailView.as_view(), name='work_schedule_detail'),
    path('schedules/<int:pk>/edit/', Attendance.WorkScheduleUpdateView.as_view(), name='work_schedule_edit'),
    path('schedules/<int:pk>/delete/', Attendance.WorkScheduleDeleteView.as_view(), name='work_schedule_delete'),
    
    # Toggle status (AJAX)
    path('schedules/<int:schedule_id>/toggle-status/', Attendance.toggle_schedule_status, name='toggle_schedule_status'),

    # ============ EMPLOYEE SCHEDULE URLS ============
    path('employee-schedules/', Attendance.EmployeeScheduleListView.as_view(), name='employee_schedule_list'),
    path('employee-schedules/create/', Attendance.EmployeeScheduleCreateView.as_view(), name='employee_schedule_create'),
    path('employee-schedules/<int:pk>/edit/', Attendance.EmployeeScheduleUpdateView.as_view(), name='employee_schedule_edit'),

    # ============ HOLIDAY URLS ============
    path('holidays/', Attendance.HolidayListView.as_view(), name='holiday_list'),
    path('holidays/create/', Attendance.HolidayCreateView.as_view(), name='holiday_create'),
    path('holidays/<int:pk>/edit/', Attendance.HolidayUpdateView.as_view(), name='holiday_edit'),
    path('holidays/<int:pk>/delete/', Attendance.HolidayDeleteView.as_view(), name='holiday_delete'),

    # ============ ATTENDANCE RULE URLS ============
    path('rules/', Attendance.AttendanceRuleListView.as_view(), name='attendance_rule_list'),
    path('rules/create/', Attendance.AttendanceRuleCreateView.as_view(), name='attendance_rule_create'),
    path('rules/<int:pk>/edit/', Attendance.AttendanceRuleUpdateView.as_view(), name='attendance_rule_edit'),
    path('rules/<int:pk>/delete/', Attendance.AttendanceRuleDeleteView.as_view(), name='attendance_rule_delete'),
]