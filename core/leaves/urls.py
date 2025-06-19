# core/leaves/urls.py
from django.urls import path
from core.leaves.views import leaves

app_name = 'leaves'

urlpatterns = [
    # ==================== LEAVE TYPE URLS ====================
    path('types/', leaves.LeaveTypeListView.as_view(), name='leave_type_list'),
    path('types/create/', leaves.LeaveTypeCreateView.as_view(), name='leave_type_create'),
    path('types/<int:pk>/', leaves.LeaveTypeDetailView.as_view(), name='leave_type_detail'),
    path('types/<int:pk>/edit/', leaves.LeaveTypeUpdateView.as_view(), name='leave_type_edit'),
    path('types/<int:pk>/delete/', leaves.LeaveTypeDeleteView.as_view(), name='leave_type_delete'),
    
    # ==================== LEAVE REQUEST URLS ====================
    path('', leaves.LeaveRequestListView.as_view(), name='leave_request_list'),
    path('requests/', leaves.LeaveRequestListView.as_view(), name='leave_request_list_alt'),
    path('requests/create/', leaves.LeaveRequestCreateView.as_view(), name='leave_request_create'),
    path('requests/<int:pk>/', leaves.LeaveRequestDetailView.as_view(), name='leave_request_detail'),
    path('requests/<int:pk>/edit/', leaves.LeaveRequestUpdateView.as_view(), name='leave_request_edit'),
    path('requests/<int:pk>/delete/', leaves.LeaveRequestDeleteView.as_view(), name='leave_request_delete'),
    path('requests/<int:pk>/approve/', leaves.LeaveRequestApprovalView.as_view(), name='leave_request_approve'),
    
    # ==================== LEAVE BALANCE URLS ====================
    path('balances/', leaves.LeaveBalanceListView.as_view(), name='leave_balance_list'),
    path('balances/create/', leaves.LeaveBalanceCreateView.as_view(), name='leave_balance_create'),
    path('balances/<int:pk>/', leaves.LeaveBalanceDetailView.as_view(), name='leave_balance_detail'),
    path('balances/<int:pk>/edit/', leaves.LeaveBalanceUpdateView.as_view(), name='leave_balance_edit'),
    path('balances/<int:pk>/delete/', leaves.LeaveBalanceDeleteView.as_view(), name='leave_balance_delete'),
    
    # ==================== AJAX URLS ====================
    path('ajax/employee-balance/', leaves.get_employee_balance, name='get_employee_balance'),
    path('ajax/calculate-days/', leaves.calculate_leave_days, name='calculate_leave_days'),
    path('leave-types/<int:pk>/toggle-status/', leaves.leave_type_toggle_status, name='leave_type_toggle_status'),
]