from django.urls import path
from core.leaves.views import leaves

app_name = 'leaves'

urlpatterns = [
    # ===== LEAVE TYPES =====
    path('types/', leaves.LeaveTypeListView.as_view(), name='leave_type_list'),
    path('types/create/', leaves.LeaveTypeCreateView.as_view(), name='leave_type_create'),
    path('types/<int:pk>/', leaves.LeaveTypeDetailView.as_view(), name='leave_type_detail'),
    path('types/<int:pk>/update/', leaves.LeaveTypeUpdateView.as_view(), name='leave_type_update'),
    path('types/<int:pk>/delete/', leaves.LeaveTypeDeleteView.as_view(), name='leave_type_delete'),
    path('types/<int:pk>/toggle-status/', leaves.leave_type_toggle_status, name='leave_type_toggle_status'),
    
    # ===== LEAVE REQUESTS =====
    path('requests/', leaves.LeaveRequestListView.as_view(), name='leave_request_list'),
    path('requests/create/', leaves.LeaveRequestCreateView.as_view(), name='leave_request_create'),
    path('requests/<int:pk>/', leaves.LeaveRequestDetailView.as_view(), name='leave_request_detail'),
    path('requests/<int:pk>/update/', leaves.LeaveRequestUpdateView.as_view(), name='leave_request_update'),
    path('requests/<int:pk>/delete/', leaves.LeaveRequestDeleteView.as_view(), name='leave_request_delete'),
    path('requests/<int:pk>/approval/', leaves.LeaveRequestApprovalView.as_view(), name='leave_request_approval'),
    
    # ===== NUEVAS APIs PARA APROBACIÓN =====
    path('requests/<int:pk>/approve/', leaves.approve_leave_request, name='approve_leave_request'),
    path('requests/<int:pk>/reject/', leaves.reject_leave_request, name='reject_leave_request'),
    path('requests/bulk-actions/', leaves.leave_request_bulk_actions, name='leave_request_bulk_actions'),
    
    # ===== LEAVE BALANCES =====
    path('balances/', leaves.LeaveBalanceListView.as_view(), name='leave_balance_list'),
    path('balances/create/', leaves.LeaveBalanceCreateView.as_view(), name='leave_balance_create'),
    path('balances/<int:pk>/', leaves.LeaveBalanceDetailView.as_view(), name='leave_balance_detail'),
    path('balances/<int:pk>/update/', leaves.LeaveBalanceUpdateView.as_view(), name='leave_balance_update'),
    path('balances/<int:pk>/delete/', leaves.LeaveBalanceDeleteView.as_view(), name='leave_balance_delete'),
    
    # ===== AJAX ENDPOINTS =====
    path('ajax/employee-balance/', leaves.get_employee_balance, name='get_employee_balance'),
    path('ajax/calculate-days/', leaves.calculate_leave_days, name='calculate_leave_days'),
]