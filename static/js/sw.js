// Service Worker para modo offline
const CACHE_NAME = 'attendance-cache-v1';
const OFFLINE_CACHE = 'attendance-offline-v1';

// Archivos críticos para funcionar offline
const CRITICAL_FILES = [
    '/static/css/tailwind.min.css',
    '/static/js/attendance.js'
    // Removemos rutas dinámicas que pueden fallar
];

// URLs de APIs que se pueden cachear
const API_CACHE_PATTERNS = [
    '/employees/api/attendance-status/',
    '/employees/time/'
];

// Instalación del Service Worker
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Service Worker: Caching critical files');
                // Cache solo archivos estáticos que sabemos que existen
                return cache.addAll(CRITICAL_FILES).catch(error => {
                    console.warn('Some files failed to cache:', error);
                    // Continuar aunque algunos archivos fallen
                    return Promise.resolve();
                });
            })
            .then(() => self.skipWaiting())
    );
});

// Activación del Service Worker
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME && cacheName !== OFFLINE_CACHE) {
                        console.log('Service Worker: Deleting old cache', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// Interceptar requests para manejo offline
self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Solo manejar requests GET de nuestro dominio
    if (request.method !== 'GET' || !url.origin.includes(self.location.origin)) {
        return;
    }
    
    // Estrategia: Network First para APIs, Cache First para assets
    if (isAPIRequest(request.url)) {
        event.respondWith(networkFirstStrategy(request));
    } else {
        event.respondWith(cacheFirstStrategy(request));
    }
});

// Manejar requests POST para asistencia cuando está offline
self.addEventListener('sync', event => {
    console.log('Service Worker: Background sync triggered');
    
    if (event.tag === 'attendance-sync') {
        event.waitUntil(syncOfflineAttendance());
    }
});

// Estrategia Network First para APIs
async function networkFirstStrategy(request) {
    try {
        // Intentar obtener de la red primero
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // Cachear respuesta exitosa
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('Service Worker: Network failed, trying cache for', request.url);
        
        // Si falla la red, intentar cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Si no hay cache, retornar respuesta offline
        return new Response(
            JSON.stringify({
                offline: true,
                message: 'Sin conexión - usando datos locales',
                timestamp: new Date().toISOString()
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Estrategia Cache First para assets estáticos
async function cacheFirstStrategy(request) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('Service Worker: Failed to fetch', request.url);
        
        // Retornar página offline para navegación
        if (request.destination === 'document') {
            return caches.match('/offline.html');
        }
        
        return new Response('Sin conexión', { status: 503 });
    }
}

// Verificar si es un request a API
function isAPIRequest(url) {
    return API_CACHE_PATTERNS.some(pattern => url.includes(pattern)) ||
           url.includes('/api/') ||
           url.includes('ajax');
}

// Sincronizar datos de asistencia cuando vuelva la conexión
async function syncOfflineAttendance() {
    try {
        // Obtener datos guardados offline
        const offlineData = await getOfflineAttendanceData();
        
        if (offlineData.length === 0) {
            console.log('No hay datos offline para sincronizar');
            return;
        }
        
        console.log('Sincronizando', offlineData.length, 'registros offline');
        
        // Sincronizar cada registro
        for (const record of offlineData) {
            try {
                const response = await fetch(record.url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': record.csrfToken
                    },
                    body: JSON.stringify(record.data)
                });
                
                if (response.ok) {
                    console.log('Registro sincronizado exitosamente:', record.id);
                    await removeOfflineRecord(record.id);
                } else {
                    console.error('Error sincronizando registro:', record.id);
                }
            } catch (error) {
                console.error('Error en sincronización:', error);
            }
        }
        
        // Notificar a las ventanas abiertas
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'SYNC_COMPLETE',
                synced: offlineData.length
            });
        });
        
    } catch (error) {
        console.error('Error en sincronización offline:', error);
    }
}

// Obtener datos guardados offline (implementar con IndexedDB)
async function getOfflineAttendanceData() {
    // Implementar con IndexedDB
    return [];
}

// Remover registro offline después de sincronizar
async function removeOfflineRecord(recordId) {
    // Implementar con IndexedDB
    console.log('Removing offline record:', recordId);
}