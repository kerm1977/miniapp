// static/js/sw.js

const CACHE_NAME = 'factugest-pwa-cache-v1'; // Cambia 'v1' si haces cambios significativos
const urlsToCache = [
  '/', // Ruta principal
  '/login', // Por ejemplo, si quieres que la página de login esté disponible offline
  '/static/css/main.css',
  '/static/js/pwa.js',
  '/static/js/script.js', // Asegúrate de cachear tu script.js también
  // Añade aquí todas las rutas HTML estáticas que quieras que estén disponibles offline
  // Por ejemplo, si tienes una ruta '/dashboard' o '/contactos' que renderiza una plantilla:
  // '/dashboard',
  // '/contactos',
  // Si tienes un favicon:
  // '/static/favicon.ico',
  // Y tus iconos de PWA:
  '/static/images/icons/icon-192x192.png',
  '/static/images/icons/icon-512x512.png'
  // Ojo: Las rutas de API de Flask (ej. /api/facturas) NO se cachean directamente aquí
  // ya que sus datos cambian dinámicamente. Para datos offline, necesitas IndexedDB.
];

self.addEventListener('install', event => {
  console.log('[Service Worker] Instalando Service Worker...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Cacheando shell de la aplicación');
        return cache.addAll(urlsToCache);
      })
      .catch(error => {
        console.error('[Service Worker] Error al cachear recursos durante la instalación:', error);
      })
  );
});

self.addEventListener('fetch', event => {
  // Estrategia: Cache-First, Network-Fallback
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Si el recurso está en la caché, lo devolvemos
        if (response) {
          return response;
        }
        // Si no está en la caché, intentamos obtenerlo de la red
        return fetch(event.request).then(
          response => {
            // Si la respuesta de la red es válida (status 200), la cacheamos para futuras visitas
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response; // No cachear respuestas no válidas
            }
            const responseToCache = response.clone(); // Clonar la respuesta porque la original es un stream
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
            return response;
          }
        ).catch(error => {
          console.error('[Service Worker] Error al obtener recurso de la red:', event.request.url, error);
          // Aquí podrías servir una página offline personalizada si la solicitud falla
          // Por ejemplo: return caches.match('/offline.html');
        });
      })
  );
});

self.addEventListener('activate', event => {
  console.log('[Service Worker] Activando Service Worker...');
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            // Eliminar cachés antiguos
            console.log('[Service Worker] Eliminando caché antiguo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Opcional: Para manejar notificaciones push o sincronización en segundo plano
// self.addEventListener('push', event => { ... });
// self.addEventListener('sync', event => { ... });