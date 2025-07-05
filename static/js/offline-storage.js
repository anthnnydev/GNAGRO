// Manejo de almacenamiento offline con IndexedDB
class OfflineStorage {
    constructor() {
        this.dbName = 'AttendanceOfflineDB';
        this.dbVersion = 1;
        this.db = null;
    }

    // Inicializar base de datos
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);
            
            request.onerror = () => {
                console.error('Error opening IndexedDB:', request.error);
                reject(request.error);
            };
            
            request.onsuccess = () => {
                this.db = request.result;
                console.log('IndexedDB opened successfully');
                resolve(this.db);
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Store para registros de asistencia offline
                if (!db.objectStoreNames.contains('attendance_records')) {
                    const attendanceStore = db.createObjectStore('attendance_records', {
                        keyPath: 'id',
                        autoIncrement: true
                    });
                    
                    attendanceStore.createIndex('timestamp', 'timestamp', { unique: false });
                    attendanceStore.createIndex('type', 'type', { unique: false });
                    attendanceStore.createIndex('synced', 'synced', { unique: false });
                }
                
                // Store para cache de estado
                if (!db.objectStoreNames.contains('app_state')) {
                    db.createObjectStore('app_state', { keyPath: 'key' });
                }
                
                // Store para datos de empleado
                if (!db.objectStoreNames.contains('employee_data')) {
                    db.createObjectStore('employee_data', { keyPath: 'key' });
                }
            };
        });
    }

    // Guardar registro de asistencia offline
    async saveAttendanceRecord(type, data, url, csrfToken) {
        if (!this.db) await this.init();
        
        const record = {
            type: type, // 'clock_in', 'clock_out', 'break_start', 'break_end'
            data: data,
            url: url,
            csrfToken: csrfToken,
            timestamp: new Date().toISOString(),
            synced: false,
            retryCount: 0
        };
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['attendance_records'], 'readwrite');
            const store = transaction.objectStore('attendance_records');
            
            const request = store.add(record);
            
            request.onsuccess = () => {
                console.log('Registro guardado offline:', record);
                resolve(request.result);
            };
            
            request.onerror = () => {
                console.error('Error guardando registro offline:', request.error);
                reject(request.error);
            };
        });
    }

    // Obtener registros pendientes de sincronizar
    async getPendingRecords() {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['attendance_records'], 'readonly');
            const store = transaction.objectStore('attendance_records');
            
            // Usar cursor en lugar de index.getAll con boolean
            const request = store.openCursor();
            const pendingRecords = [];
            
            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor) {
                    const record = cursor.value;
                    if (record.synced === false || record.synced === undefined) {
                        pendingRecords.push(record);
                    }
                    cursor.continue();
                } else {
                    resolve(pendingRecords);
                }
            };
            
            request.onerror = () => {
                reject(request.error);
            };
        });
    }

    // Marcar registro como sincronizado
    async markAsSynced(recordId) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['attendance_records'], 'readwrite');
            const store = transaction.objectStore('attendance_records');
            
            const getRequest = store.get(recordId);
            
            getRequest.onsuccess = () => {
                const record = getRequest.result;
                if (record) {
                    record.synced = true;
                    record.syncedAt = new Date().toISOString();
                    
                    const updateRequest = store.put(record);
                    updateRequest.onsuccess = () => resolve(true);
                    updateRequest.onerror = () => reject(updateRequest.error);
                } else {
                    reject(new Error('Record not found'));
                }
            };
            
            getRequest.onerror = () => reject(getRequest.error);
        });
    }

    // Guardar estado de la aplicación
    async saveAppState(key, value) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['app_state'], 'readwrite');
            const store = transaction.objectStore('app_state');
            
            const request = store.put({
                key: key,
                value: value,
                timestamp: new Date().toISOString()
            });
            
            request.onsuccess = () => resolve(true);
            request.onerror = () => reject(request.error);
        });
    }

    // Obtener estado de la aplicación
    async getAppState(key) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['app_state'], 'readonly');
            const store = transaction.objectStore('app_state');
            
            const request = store.get(key);
            
            request.onsuccess = () => {
                const result = request.result;
                resolve(result ? result.value : null);
            };
            
            request.onerror = () => reject(request.error);
        });
    }

    // Limpiar registros antiguos sincronizados
    async cleanupOldRecords(daysOld = 7) {
        if (!this.db) await this.init();
        
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - daysOld);
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['attendance_records'], 'readwrite');
            const store = transaction.objectStore('attendance_records');
            const index = store.index('timestamp');
            
            const range = IDBKeyRange.upperBound(cutoffDate.toISOString());
            const request = index.openCursor(range);
            
            let deletedCount = 0;
            
            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor) {
                    const record = cursor.value;
                    if (record.synced) {
                        cursor.delete();
                        deletedCount++;
                    }
                    cursor.continue();
                } else {
                    console.log(`Limpieza completada: ${deletedCount} registros eliminados`);
                    resolve(deletedCount);
                }
            };
            
            request.onerror = () => reject(request.error);
        });
    }

    // Obtener estadísticas de almacenamiento
    async getStorageStats() {
        if (!this.db) await this.init();
        
        const stats = {
            pendingRecords: 0,
            syncedRecords: 0,
            totalSize: 0
        };
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['attendance_records'], 'readonly');
            const store = transaction.objectStore('attendance_records');
            
            const request = store.getAll();
            
            request.onsuccess = () => {
                const records = request.result;
                
                stats.pendingRecords = records.filter(r => !r.synced).length;
                stats.syncedRecords = records.filter(r => r.synced).length;
                stats.totalSize = JSON.stringify(records).length;
                
                resolve(stats);
            };
            
            request.onerror = () => reject(request.error);
        });
    }
}

// Instancia global
const offlineStorage = new OfflineStorage();