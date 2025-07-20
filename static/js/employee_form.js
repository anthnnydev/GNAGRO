// employee_form.js - JavaScript para manejar formulario de empleados simplificado

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar la lógica del formulario
    initEmployeeForm();
});

function initEmployeeForm() {
    const contractTypeField = document.getElementById('id_contract_type');
    const salaryField = document.getElementById('id_salary');
    
    if (contractTypeField && salaryField) {
        // Configurar el estado inicial
        toggleSalaryField(contractTypeField.value);
        
        // Agregar listener para cambios
        contractTypeField.addEventListener('change', function() {
            toggleSalaryField(this.value);
        });
        
        // Agregar tooltips informativos
        addEmployeeTypeTooltips();
    }
}

function toggleSalaryField(contractType) {
    const salaryField = document.getElementById('id_salary');
    const salaryLabel = document.querySelector('label[for="id_salary"]');
    const salaryHelpText = salaryField?.parentElement?.querySelector('.help-text');
    
    if (!salaryField) return;
    
    // Configurar campo según tipo de contrato
    if (contractType === 'permanent') {
        // Empleado permanente: salario obligatorio
        salaryField.required = true;
        salaryField.min = '0.01';
        salaryField.placeholder = 'Ej: 1200.00';
        salaryField.style.borderColor = '#d1d5db'; // Normal
        
        // Actualizar label y help text
        if (salaryLabel) {
            salaryLabel.innerHTML = 'Salario Mensual <span class="text-red-500">*</span>';
        }
        
        updateHelpText(salaryField, 'Sueldo fijo mensual (obligatorio para empleados permanentes)');
        
        // Mostrar tooltip informativo
        showFieldTooltip(salaryField, '✅ Empleados permanentes reciben sueldo fijo mensual');
        
    } else if (contractType === 'temporary') {
        // Jornalero: salario opcional (tarifa base)
        salaryField.required = false;
        salaryField.min = '0';
        salaryField.placeholder = 'Ej: 15.00 (opcional)';
        salaryField.style.borderColor = '#10b981'; // Verde
        
        // Actualizar label y help text
        if (salaryLabel) {
            salaryLabel.innerHTML = 'Tarifa Base por Hora (Opcional)';
        }
        
        updateHelpText(salaryField, 'Tarifa de referencia por hora. Los jornaleros cobran por tareas completadas.');
        
        // Mostrar tooltip informativo
        showFieldTooltip(salaryField, '⚡ Jornaleros cobran por tareas completadas, no por sueldo fijo');
        
    } else {
        // Reset a estado normal
        salaryField.required = false;
        salaryField.min = '0';
        salaryField.placeholder = '0.00';
        salaryField.style.borderColor = '#d1d5db';
        
        if (salaryLabel) {
            salaryLabel.innerHTML = 'Salario/Tarifa Base';
        }
        
        updateHelpText(salaryField, 'Selecciona un tipo de empleado primero');
    }
}

function updateHelpText(field, text) {
    // Buscar o crear elemento de help text
    let helpTextElement = field.parentElement.querySelector('.help-text');
    
    if (!helpTextElement) {
        helpTextElement = document.createElement('p');
        helpTextElement.className = 'help-text text-sm text-gray-600 mt-1';
        field.parentElement.appendChild(helpTextElement);
    }
    
    helpTextElement.textContent = text;
}

function showFieldTooltip(field, message) {
    // Remover tooltip anterior si existe
    const existingTooltip = field.parentElement.querySelector('.field-tooltip');
    if (existingTooltip) {
        existingTooltip.remove();
    }
    
    // Crear nuevo tooltip
    const tooltip = document.createElement('div');
    tooltip.className = 'field-tooltip bg-blue-50 border border-blue-200 rounded-md p-2 mt-2 text-sm text-blue-800';
    tooltip.innerHTML = `<i class="fas fa-info-circle mr-1"></i> ${message}`;
    
    field.parentElement.appendChild(tooltip);
    
    // Auto-remover después de 5 segundos
    setTimeout(() => {
        if (tooltip.parentElement) {
            tooltip.remove();
        }
    }, 5000);
}

function addEmployeeTypeTooltips() {
    const contractTypeField = document.getElementById('id_contract_type');
    
    if (contractTypeField) {
        // Agregar descripción visual debajo del select
        const descriptionsContainer = document.createElement('div');
        descriptionsContainer.className = 'contract-type-descriptions mt-3 space-y-2';
        descriptionsContainer.innerHTML = `
            <div class="permanent-description bg-green-50 border border-green-200 rounded-md p-3 text-sm" style="display: none;">
                <div class="flex items-start">
                    <span class="text-2xl mr-3">👔</span>
                    <div>
                        <h4 class="font-semibold text-green-800">Empleado Permanente</h4>
                        <ul class="text-green-700 mt-1 space-y-1">
                            <li>• Recibe sueldo fijo mensual</li>
                            <li>• Las tareas son para gestión del trabajo</li>
                            <li>• No recibe pago adicional por tareas</li>
                            <li>• Beneficios laborales completos</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <div class="temporary-description bg-blue-50 border border-blue-200 rounded-md p-3 text-sm" style="display: none;">
                <div class="flex items-start">
                    <span class="text-2xl mr-3">⚡</span>
                    <div>
                        <h4 class="font-semibold text-blue-800">Jornalero/Temporal</h4>
                        <ul class="text-blue-700 mt-1 space-y-1">
                            <li>• Solo se paga por tareas completadas</li>
                            <li>• No tiene sueldo fijo</li>
                            <li>• Pago variable según productividad</li>
                            <li>• Tarifa base opcional de referencia</li>
                        </ul>
                    </div>
                </div>
            </div>
        `;
        
        contractTypeField.parentElement.appendChild(descriptionsContainer);
        
        // Función para mostrar/ocultar descripciones
        function updateDescriptions(contractType) {
            const permanentDesc = descriptionsContainer.querySelector('.permanent-description');
            const temporaryDesc = descriptionsContainer.querySelector('.temporary-description');
            
            // Ocultar todas
            permanentDesc.style.display = 'none';
            temporaryDesc.style.display = 'none';
            
            // Mostrar la correspondiente
            if (contractType === 'permanent') {
                permanentDesc.style.display = 'block';
            } else if (contractType === 'temporary') {
                temporaryDesc.style.display = 'block';
            }
        }
        
        // Mostrar descripción inicial
        updateDescriptions(contractTypeField.value);
        
        // Actualizar al cambiar
        contractTypeField.addEventListener('change', function() {
            updateDescriptions(this.value);
        });
    }
}

// Función para validación en tiempo real
function validateEmployeeForm() {
    const contractType = document.getElementById('id_contract_type')?.value;
    const salary = document.getElementById('id_salary')?.value;
    const salaryField = document.getElementById('id_salary');
    
    let isValid = true;
    
    // Validar salario según tipo de contrato
    if (contractType === 'permanent') {
        if (!salary || parseFloat(salary) <= 0) {
            showFieldError(salaryField, 'El salario es obligatorio para empleados permanentes');
            isValid = false;
        } else {
            clearFieldError(salaryField);
        }
    } else if (contractType === 'temporary') {
        // Para temporales, el salario es opcional, pero si se ingresa debe ser >= 0
        if (salary && parseFloat(salary) < 0) {
            showFieldError(salaryField, 'La tarifa no puede ser negativa');
            isValid = false;
        } else {
            clearFieldError(salaryField);
        }
    }
    
    return isValid;
}

function showFieldError(field, message) {
    // Cambiar color del borde
    field.style.borderColor = '#ef4444';
    
    // Buscar o crear elemento de error
    let errorElement = field.parentElement.querySelector('.field-error');
    
    if (!errorElement) {
        errorElement = document.createElement('p');
        errorElement.className = 'field-error text-sm text-red-600 mt-1';
        field.parentElement.appendChild(errorElement);
    }
    
    errorElement.textContent = message;
}

function clearFieldError(field) {
    // Restaurar color del borde
    field.style.borderColor = '#d1d5db';
    
    // Remover mensaje de error
    const errorElement = field.parentElement.querySelector('.field-error');
    if (errorElement) {
        errorElement.remove();
    }
}

// Función para filtrar empleados en selects (para otros formularios)
function filterEmployees(contractType) {
    const employeeSelect = document.getElementById('id_employee');
    
    if (!employeeSelect) return;
    
    const options = employeeSelect.querySelectorAll('option');
    
    options.forEach(option => {
        if (option.value === '') return; // Mantener opción vacía
        
        const optionContractType = option.dataset.contractType;
        
        if (contractType === '' || contractType === optionContractType) {
            option.style.display = '';
        } else {
            option.style.display = 'none';
        }
    });
    
    // Reset selection if current option is hidden
    const currentOption = employeeSelect.querySelector(`option[value="${employeeSelect.value}"]`);
    if (currentOption && currentOption.style.display === 'none') {
        employeeSelect.value = '';
    }
}

// Función para mostrar estadísticas por tipo de empleado
function showEmployeeTypeStats() {
    // Esta función se puede llamar desde el dashboard o listados
    const permanentCount = document.querySelectorAll('[data-contract-type="permanent"]').length;
    const temporaryCount = document.querySelectorAll('[data-contract-type="temporary"]').length;
    
    console.log(`Empleados Permanentes: ${permanentCount}`);
    console.log(`Jornaleros/Temporales: ${temporaryCount}`);
    
    // Actualizar elementos de estadísticas si existen
    const permanentStat = document.getElementById('permanent-employees-count');
    const temporaryStat = document.getElementById('temporary-employees-count');
    
    if (permanentStat) permanentStat.textContent = permanentCount;
    if (temporaryStat) temporaryStat.textContent = temporaryCount;
}

// Función para calcular pago estimado (para uso en otros módulos)
function calculateEstimatedPay(contractType, salary, hoursOrTasks) {
    if (contractType === 'permanent') {
        // Para permanentes: salario fijo + horas extra
        const basePay = parseFloat(salary) || 0;
        const extraHours = parseFloat(hoursOrTasks) || 0;
        const hourlyRate = basePay / 160; // Asumiendo 160 horas/mes
        const overtimePay = extraHours * hourlyRate * 1.5; // 50% extra
        
        return basePay + overtimePay;
        
    } else if (contractType === 'temporary') {
        // Para temporales: solo pago por tareas
        const tasksCompleted = parseFloat(hoursOrTasks) || 0;
        const ratePerTask = parseFloat(salary) || 15; // Tarifa por defecto
        
        return tasksCompleted * ratePerTask;
    }
    
    return 0;
}

// Función para formatear montos
function formatCurrency(amount) {
    return new Intl.NumberFormat('es-EC', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(amount);
}

// Función para validar formulario antes de envío
function validateFormBeforeSubmit(event) {
    if (!validateEmployeeForm()) {
        event.preventDefault();
        
        // Mostrar mensaje de error general
        const errorMessage = document.createElement('div');
        errorMessage.className = 'bg-red-50 border border-red-200 rounded-md p-4 mb-4 text-red-800';
        errorMessage.innerHTML = `
            <div class="flex">
                <i class="fas fa-exclamation-triangle mr-2 mt-0.5"></i>
                <div>
                    <h4 class="font-semibold">Errores en el formulario</h4>
                    <p class="text-sm mt-1">Por favor corrige los errores indicados antes de continuar.</p>
                </div>
            </div>
        `;
        
        const form = event.target;
        form.insertBefore(errorMessage, form.firstChild);
        
        // Scroll al primer error
        const firstError = form.querySelector('.field-error');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        
        // Remover mensaje después de 5 segundos
        setTimeout(() => {
            if (errorMessage.parentElement) {
                errorMessage.remove();
            }
        }, 5000);
    }
}

// Agregar listener al formulario cuando se carga la página
document.addEventListener('DOMContentLoaded', function() {
    const employeeForm = document.getElementById('employee-form');
    
    if (employeeForm) {
        employeeForm.addEventListener('submit', validateFormBeforeSubmit);
        
        // Validación en tiempo real al perder el foco
        const salaryField = document.getElementById('id_salary');
        if (salaryField) {
            salaryField.addEventListener('blur', validateEmployeeForm);
        }
    }
});

// Exportar funciones para uso en otros módulos
window.EmployeeFormUtils = {
    toggleSalaryField,
    filterEmployees,
    calculateEstimatedPay,
    formatCurrency,
    validateEmployeeForm,
    showEmployeeTypeStats
};