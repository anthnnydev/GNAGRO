// static/js/dashboard-notifications.js

// Variables globales para notificaciones
let notificationInterval;
let currentNotifications = [];

// Función para obtener CSRF token
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
           document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || 
           '';
}

// Cargar notificaciones del dashboard
async function loadDashboardNotifications() {
    console.log('🔄 Cargando notificaciones del dashboard...');
    
    try {
        const response = await fetch('/notifications/api/dashboard/', {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCSRFToken(),
                'Content-Type': 'application/json'
            }
        });
        
        console.log('📡 Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('📊 Datos recibidos:', data);
        
        if (data.success) {
            currentNotifications = data.notifications;
            renderDashboardNotifications(data.notifications);
            updateNotificationBadge(data.total_unread);
            updateMarkAllButton(data.total_unread);
        } else {
            console.error('❌ Error en los datos:', data.error);
            showNotificationError(data.error || 'Error desconocido');
        }
        
    } catch (error) {
        console.error('❌ Error en la solicitud de notificaciones:', error);
        showNotificationError('Error de conexión: ' + error.message);
    }
}

// Renderizar notificaciones en el dashboard
function renderDashboardNotifications(notifications) {
    console.log('🎨 Renderizando notificaciones:', notifications.length);
    
    const container = document.querySelector('#notifications-container') || 
                     document.querySelector('.space-y-4.max-h-64.overflow-y-auto');
    
    if (!container) {
        console.error('❌ Contenedor de notificaciones no encontrado');
        return;
    }
    
    // Ocultar loading si existe
    const loading = document.getElementById('notifications-loading');
    if (loading) {
        loading.classList.add('hidden');
        console.log('🔄 Loading oculto');
    }
    
    if (notifications.length === 0) {
        container.innerHTML = getEmptyNotificationsHTML();
        console.log('📭 No hay notificaciones');
        return;
    }
    
    // Mostrar máximo 5 notificaciones en el dashboard
    const limitedNotifications = notifications.slice(0, 5);
    console.log(`📋 Mostrando ${limitedNotifications.length} notificaciones`);
    
    const notificationsHTML = limitedNotifications.map(notification => {
        const colorClass = getNotificationColorClass(notification.color);
        const iconClass = notification.icon || 'fa-bell';
        
        return `
            <div class="flex items-start space-x-3 p-3 ${colorClass} rounded-lg hover:opacity-75 transition-opacity cursor-pointer"
                 onclick="handleNotificationClick('${notification.url}', ${notification.id || 'null'})">
                <div class="bg-${notification.color}-600 p-1 rounded-full">
                    <i class="fas ${iconClass} text-white text-xs"></i>
                </div>
                <div class="flex-1">
                    <p class="text-sm font-medium text-gray-900">
                        ${notification.title}
                    </p>
                    <p class="text-xs text-gray-600">${notification.message}</p>
                    <div class="flex items-center justify-between mt-1">
                        <p class="text-xs text-gray-400">${notification.time_ago}</p>
                        ${notification.count ? `<span class="bg-red-500 text-white text-xs px-2 py-1 rounded-full">${notification.count}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = notificationsHTML;
    
    // Agregar enlace para ver todas si hay más notificaciones
    if (notifications.length > 5) {
        container.innerHTML += `
            <div class="text-center pt-4">
                <a href="/notifications/" 
                   class="text-primary-600 hover:text-primary-700 text-sm font-medium">
                    Ver todas las notificaciones (${notifications.length - 5} más)
                </a>
            </div>
        `;
    } else if (notifications.length > 0) {
        container.innerHTML += `
            <div class="text-center pt-4">
                <a href="/notifications/" 
                   class="text-primary-600 hover:text-primary-700 text-sm font-medium">
                    Ver todas las notificaciones
                </a>
            </div>
        `;
    }
    
    console.log('✅ Notificaciones renderizadas correctamente');
}

// Obtener clase CSS para el color de notificación
function getNotificationColorClass(color) {
    const colorMap = {
        'primary': 'bg-blue-50',
        'success': 'bg-green-50',
        'warning': 'bg-yellow-50',
        'danger': 'bg-red-50',
        'info': 'bg-blue-50',
        'secondary': 'bg-gray-50'
    };
    
    return colorMap[color] || 'bg-blue-50';
}

// HTML para cuando no hay notificaciones
function getEmptyNotificationsHTML() {
    return `
        <div class="text-center text-gray-500 py-8">
            <i class="fas fa-bell-slash text-3xl mb-3 text-gray-300"></i>
            <p class="text-sm">No tienes notificaciones</p>
            <p class="text-xs text-gray-400 mt-1">Las nuevas notificaciones aparecerán aquí</p>
        </div>
    `;
}

// Mostrar error de notificaciones
function showNotificationError(errorMessage) {
    const container = document.querySelector('#notifications-container') || 
                     document.querySelector('.space-y-4.max-h-64.overflow-y-auto');
    
    if (container) {
        container.innerHTML = `
            <div class="text-center text-red-500 py-8">
                <i class="fas fa-exclamation-triangle text-3xl mb-3"></i>
                <p class="text-sm">Error cargando notificaciones</p>
                <p class="text-xs text-gray-500 mt-1">${errorMessage}</p>
                <button onclick="loadDashboardNotifications()" 
                        class="text-xs text-blue-600 hover:text-blue-800 mt-2 underline">
                    Intentar nuevamente
                </button>
            </div>
        `;
    }
}

// Actualizar badge de notificaciones
function updateNotificationBadge(count) {
    const badge = document.getElementById('notification-badge');
    
    if (badge) {
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }
    
    // También actualizar otros badges en la página si existen
    const otherBadges = document.querySelectorAll('.notification-count');
    otherBadges.forEach(badge => {
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    });
}

// Actualizar botón "Marcar como leídas"
function updateMarkAllButton(unreadCount) {
    const markAllBtn = document.getElementById('mark-all-read-btn');
    
    if (markAllBtn) {
        if (unreadCount > 0) {
            markAllBtn.classList.remove('hidden');
            markAllBtn.textContent = `Marcar como leídas (${unreadCount})`;
        } else {
            markAllBtn.classList.add('hidden');
        }
    }
}

// Manejar click en notificación
async function handleNotificationClick(url, notificationId = null) {
    console.log(`🔗 Click en notificación: ${url}, ID: ${notificationId}`);
    
    // Marcar como leída si es una notificación del sistema
    if (notificationId && notificationId !== 'null') {
        try {
            await fetch(`/notifications/api/${notificationId}/mark-read/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCSRFToken(),
                }
            });
            
            console.log('✅ Notificación marcada como leída');
            
            // Recargar notificaciones después de marcar como leída
            setTimeout(loadDashboardNotifications, 500);
            
        } catch (error) {
            console.error('❌ Error marcando notificación como leída:', error);
        }
    }
    
    // Navegar a la URL
    if (url && url !== '#') {
        window.location.href = url;
    }
}

// Marcar todas las notificaciones como leídas
async function markAllNotificationsAsRead() {
    console.log('📝 Marcando todas las notificaciones como leídas...');
    
    try {
        const response = await fetch('/notifications/api/mark-all-read/', {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCSRFToken(),
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Mostrar mensaje de éxito
            showNotificationMessage('Todas las notificaciones han sido marcadas como leídas', 'success');
            
            // Recargar notificaciones
            loadDashboardNotifications();
        } else {
            showNotificationMessage('Error al marcar notificaciones como leídas', 'error');
        }
        
    } catch (error) {
        console.error('❌ Error marcando todas las notificaciones:', error);
        showNotificationMessage('Error de conexión al marcar notificaciones', 'error');
    }
}

// Mostrar mensaje de notificación temporal
function showNotificationMessage(message, type = 'info') {
    // Crear elemento de notificación
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transform transition-all duration-300 translate-x-full`;
    
    // Configurar colores según el tipo
    const typeClasses = {
        'success': 'bg-green-500 text-white',
        'error': 'bg-red-500 text-white',
        'warning': 'bg-yellow-500 text-black',
        'info': 'bg-blue-500 text-white'
    };
    
    notification.className += ` ${typeClasses[type] || typeClasses.info}`;
    
    notification.innerHTML = `
        <div class="flex items-center space-x-2">
            <i class="fas ${type === 'success' ? 'fa-check' : type === 'error' ? 'fa-times' : 'fa-info'}-circle"></i>
            <span>${message}</span>
        </div>
    `;
    
    // Agregar al DOM
    document.body.appendChild(notification);
    
    // Mostrar con animación
    setTimeout(() => {
        notification.classList.remove('translate-x-full');
    }, 100);
    
    // Ocultar después de 3 segundos
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// Función para actualizar contador en tiempo real (para header/navbar)
function updateHeaderNotificationCount() {
    fetch('/notifications/api/unread-count/', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCSRFToken(),
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateNotificationBadge(data.unread_count);
        }
    })
    .catch(error => {
        console.error('Error obteniendo contador de notificaciones:', error);
    });
}

// Función para refrescar notificaciones manualmente
function refreshNotifications() {
    console.log('🔄 Refrescando notificaciones manualmente...');
    loadDashboardNotifications();
}

// Inicializar notificaciones del dashboard
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM cargado, inicializando notificaciones...');
    
    // Cargar notificaciones iniciales
    loadDashboardNotifications();
    
    // Actualizar cada 30 segundos
    notificationInterval = setInterval(loadDashboardNotifications, 30000);
    
    // También actualizar cuando se cambie de pestaña y regrese
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            console.log('👁️ Página visible, actualizando notificaciones...');
            loadDashboardNotifications();
        }
    });
});

// Limpiar intervalos al salir de la página
window.addEventListener('beforeunload', function() {
    if (notificationInterval) {
        clearInterval(notificationInterval);
    }
});

// Exponer funciones globalmente para uso en templates
window.markAllNotificationsAsRead = markAllNotificationsAsRead;
window.handleNotificationClick = handleNotificationClick;
window.refreshNotifications = refreshNotifications;
window.loadDashboardNotifications = loadDashboardNotifications;
window.updateHeaderNotificationCount = updateHeaderNotificationCount;

console.log('✅ Dashboard notifications script cargado correctamente');