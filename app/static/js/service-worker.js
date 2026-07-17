const CACHE_NAME = 'hn-ai-summerizer-v2';
const CACHE_DURATION = 3 * 24 * 60 * 60 * 1000; // 3 days in milliseconds

// Files to cache
const urlsToCache = [
    '/',
    '/static/css/style.css',
    '/static/js/base.js',
    '/static/js/i18n.js'
];

// Install event
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
    );
});

// Fetch event
self.addEventListener('fetch', event => {
    // Only cache API requests for stories
    if (event.request.url.includes('/api/stories/')) {
        event.respondWith(
            // First try to get from cache
            caches.match(event.request)
                .then(cachedResponse => {
                    // Return cached response if it exists and is not expired
                    if (cachedResponse) {
                        const cachedTime = cachedResponse.headers.get('x-cache-time');
                        if (cachedTime && (Date.now() - parseInt(cachedTime)) < CACHE_DURATION) {
                            return cachedResponse;
                        }
                    }
                    
                    // If not in cache or expired, fetch from network
                    return fetch(event.request)
                        .then(networkResponse => {
                            // Check if we received a valid response
                            if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                                return networkResponse;
                            }
                            
                            // Clone the response
                            const responseToCache = networkResponse.clone();
                            
                            // Cache the response with timestamp
                            caches.open(CACHE_NAME)
                                .then(cache => {
                                    // Add timestamp to headers
                                    const headers = new Headers(responseToCache.headers);
                                    headers.append('x-cache-time', Date.now().toString());
                                    
                                    const responseWithTimestamp = new Response(responseToCache.body, {
                                        status: responseToCache.status,
                                        statusText: responseToCache.statusText,
                                        headers: headers
                                    });
                                    
                                    cache.put(event.request, responseWithTimestamp);
                                });
                            
                            return networkResponse;
                        })
                        .catch(() => {
                            // If network request fails and we have cached response, return it even if expired
                            if (cachedResponse) {
                                return cachedResponse;
                            }
                            // If no cached response, throw error
                            throw new Error('Network request failed and no cached response available');
                        });
                })
        );
    }
    
    // For other requests, try network first, then cache
    if (!event.request.url.includes('/api/')) {
        event.respondWith(
            fetch(event.request)
                .catch(() => caches.match(event.request))
        );
    }
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    const cacheWhitelist = [CACHE_NAME];
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (!cacheWhitelist.includes(cacheName)) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Periodic cache cleanup function
function cleanUpOldCache() {
    caches.open(CACHE_NAME).then(cache => {
        cache.keys().then(requests => {
            requests.forEach(request => {
                cache.match(request).then(response => {
                    const cachedTime = response.headers.get('x-cache-time');
                    if (cachedTime && (Date.now() - parseInt(cachedTime)) > CACHE_DURATION) {
                        cache.delete(request);
                        console.log('Deleted expired cache entry:', request.url);
                    }
                });
            });
        });
    });
}

// Run cleanup every hour
setInterval(cleanUpOldCache, 60 * 60 * 1000);

// Run cleanup on activation
cleanUpOldCache();