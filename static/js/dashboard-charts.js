// dashboard-charts.js
// Script para manejar los gráficos del dashboard usando Chart.js

document.addEventListener('DOMContentLoaded', function() {
    // Configuración global de Chart.js
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.color = '#6B7280';
    
    // Inicializar gráfico de empleados por departamento
    initDepartmentChart();
    
    // Inicializar otros gráficos si es necesario
    initStatsAnimations();
});

/**
 * Inicializa el gráfico de empleados por departamento
 */
function initDepartmentChart() {
    const ctx = document.getElementById('departmentChart');
    if (!ctx) {
        console.warn('Canvas departmentChart no encontrado');
        return;
    }

    // Datos de ejemplo - en producción estos vendrían del backend
    const departmentData = getDepartmentData();
    
    // Configuración del gráfico - Optimizado para empresa agrícola
    const config = {
        type: 'bar',
        data: {
            labels: departmentData.labels,
            datasets: [{
                label: 'Número de Empleados',
                data: departmentData.data,
                backgroundColor: [
                    '#22C55E', // green-500 - Campo/Producción
                    '#F59E0B', // yellow-500 - Administración
                    '#3B82F6', // blue-500 - Logística
                    '#EF4444', // red-500 - Mantenimiento
                    '#8B5CF6', // purple-500 - Calidad
                    '#06B6D4', // cyan-500 - Recursos Humanos
                    '#F97316', // orange-500 - Seguridad
                    '#84CC16', // lime-500 - Otros
                ],
                borderColor: '#E5E7EB',
                borderWidth: 1,
                borderRadius: 6,
                borderSkipped: false,
                hoverBackgroundColor: [
                    '#16A34A', // green-600
                    '#D97706', // yellow-600
                    '#2563EB', // blue-600
                    '#DC2626', // red-600
                    '#7C3AED', // purple-600
                    '#0891B2', // cyan-600
                    '#EA580C', // orange-600
                    '#65A30D', // lime-600
                ],
                hoverBorderColor: '#9CA3AF',
                hoverBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false // Ocultar leyenda para barras
                },
                tooltip: {
                    backgroundColor: '#1F2937',
                    titleColor: '#F9FAFB',
                    bodyColor: '#F9FAFB',
                    borderColor: '#374151',
                    borderWidth: 1,
                    cornerRadius: 8,
                    callbacks: {
                        title: function(context) {
                            return `Departamento: ${context[0].label}`;
                        },
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return [
                                `Empleados: ${context.raw}`,
                                `Porcentaje: ${percentage}%`
                            ];
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        color: '#6B7280',
                        font: {
                            size: 12
                        }
                    },
                    grid: {
                        color: '#F3F4F6',
                        borderDash: [2, 2]
                    },
                    title: {
                        display: true,
                        text: 'Cantidad de Empleados',
                        color: '#374151',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    }
                },
                x: {
                    ticks: {
                        color: '#6B7280',
                        font: {
                            size: 12
                        },
                        maxRotation: 45,
                        minRotation: 0
                    },
                    grid: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Departamentos',
                        color: '#374151',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    }
                }
            },
            animation: {
                duration: 1200,
                easing: 'easeOutQuart',
                delay: (context) => {
                    return context.dataIndex * 150; // Animación escalonada
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    };

    // Crear el gráfico
    const departmentChart = new Chart(ctx, config);
    
    // Guardar referencia para actualizaciones futuras
    window.departmentChart = departmentChart;
}

/**
 * Obtiene los datos de empleados por departamento
 * En producción, esto haría una llamada AJAX al backend
 */
function getDepartmentData() {
    // Verificar si hay datos del backend en el template
    if (typeof window.departmentStats !== 'undefined') {
        return window.departmentStats;
    }
    
    // Datos de ejemplo para empresa agrícola
    return {
        labels: [
            'Campo/Producción',
            'Administración', 
            'Logística/Almacén',
            'Mantenimiento',
            'Control de Calidad',
            'Recursos Humanos',
            'Seguridad',
            'Procesamiento'
        ],
        data: [25, 8, 12, 6, 4, 3, 5, 15]
    };
}

/**
 * Inicializa animaciones para las estadísticas
 */
function initStatsAnimations() {
    // Animar números de las tarjetas de estadísticas
    const statNumbers = document.querySelectorAll('[data-stat-number]');
    
    statNumbers.forEach(element => {
        const finalValue = parseInt(element.textContent.replace(/[^0-9]/g, ''));
        if (finalValue > 0) {
            animateNumber(element, 0, finalValue, 1500);
        }
    });
}

/**
 * Anima un número desde start hasta end
 */
function animateNumber(element, start, end, duration) {
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= end) {
            current = end;
            clearInterval(timer);
        }
        
        // Mantener formato original (con símbolo de moneda si existe)
        const originalText = element.textContent;
        if (originalText.includes('$')) {
            element.textContent = '$' + Math.floor(current).toLocaleString();
        } else {
            element.textContent = Math.floor(current).toLocaleString();
        }
    }, 16);
}

/**
 * Actualiza los datos del gráfico
 * Función para llamar desde el backend via AJAX
 */
function updateDepartmentChart(newData) {
    if (window.departmentChart) {
        window.departmentChart.data.labels = newData.labels;
        window.departmentChart.data.datasets[0].data = newData.data;
        window.departmentChart.update('active');
    }
}

/**
 * Función para actualizar estadísticas en tiempo real
 */
function updateDashboardStats() {
    // Hacer llamada AJAX para obtener datos actualizados
    fetch('/api/dashboard/stats/')
        .then(response => response.json())
        .then(data => {
            // Actualizar gráfico de departamentos
            if (data.departments) {
                updateDepartmentChart(data.departments);
            }
            
            // Actualizar números de estadísticas
            if (data.stats) {
                updateStatNumbers(data.stats);
            }
        })
        .catch(error => {
            console.log('Error actualizando estadísticas:', error);
        });
}

/**
 * Actualiza los números de las tarjetas de estadísticas
 */
function updateStatNumbers(stats) {
    const mappings = {
        'total-employees': stats.total_employees,
        'active-employees': stats.active_employees,
        'monthly-payroll': stats.monthly_payroll,
        'pending-requests': stats.pending_requests
    };
    
    Object.entries(mappings).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element && value !== undefined) {
            const currentValue = parseInt(element.textContent.replace(/[^0-9]/g, ''));
            if (currentValue !== value) {
                animateNumber(element, currentValue, value, 800);
            }
        }
    });
}

/**
 * Exportar gráfico como imagen
 */
function exportChartAsImage() {
    if (window.departmentChart) {
        const url = window.departmentChart.toBase64Image();
        const link = document.createElement('a');
        link.download = 'empleados-por-departamento.png';
        link.href = url;
        link.click();
    }
}

/**
 * Cambiar tipo de gráfico
 */
function toggleChartType(newType) {
    if (window.departmentChart) {
        window.departmentChart.config.type = newType;
        
        // Ajustar configuraciones específicas por tipo
        if (newType === 'bar') {
            window.departmentChart.options.scales = {
                y: { beginAtZero: true },
                x: { ticks: { maxRotation: 45 } }
            };
            window.departmentChart.options.plugins.legend.display = false;
        } else if (newType === 'doughnut') {
            window.departmentChart.options.scales = {};
            window.departmentChart.options.cutout = '60%';
            window.departmentChart.options.plugins.legend.display = true;
            window.departmentChart.options.plugins.legend.position = 'bottom';
        } else if (newType === 'line') {
            window.departmentChart.options.scales = {
                y: { beginAtZero: true },
                x: { ticks: { maxRotation: 0 } }
            };
            window.departmentChart.options.plugins.legend.display = false;
        }
        
        window.departmentChart.update();
    }
}

// Configurar actualizaciones automáticas cada 5 minutos
setInterval(updateDashboardStats, 300000);

// Exponer funciones globalmente para uso en el template
window.dashboardCharts = {
    updateDepartmentChart,
    updateDashboardStats,
    exportChartAsImage,
    toggleChartType
};