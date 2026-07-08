// Main JavaScript file for the application
console.log('HN AI SUmmerizer loaded');

// Check for service worker support
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/js/service-worker.js')
        .then(registration => {
            console.log('Service Worker registered with scope:', registration.scope);
        })
        .catch(error => {
            console.log('Service Worker registration failed:', error);
        });
}