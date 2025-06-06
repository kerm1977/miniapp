// Este es el archivo pwa separado de la lógica

// static/js/pwa.js

// 1. Registro del Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/js/sw.js') // Asegúrate de que esta ruta es correcta para sw.js
      .then(registration => {
        console.log('Service Worker registrado con éxito:', registration);
      })
      .catch(error => {
        console.error('Fallo en el registro del Service Worker:', error);
      });
  });
}

// 2. Aquí puedes añadir más lógica JS específica de tu PWA si la necesitas
// Por ejemplo, lógica para la sincronización en segundo plano, notificaciones, etc.
// ...