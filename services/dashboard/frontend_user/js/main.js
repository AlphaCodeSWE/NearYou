// Global state
let token = "";
let username = "";
let map, userMarker, userPopup, userPolyline;
let shopsMarkers = [];
let allShops = [];
let visitedShops = [];
let currentPosition = null;
let routePoints = [];
let notifications = [];
let startTime = null;
let categoryFilter = "all";
let isDarkTheme = false;
let userData = null;
let notificationsPage = 0;
let isLoadingMoreNotifications = false;
let lazyLoadObserver = null;
let isMapInitialized = false;
let isDataLoaded = false;

// OTTIMIZZAZIONE: Map per tracking marker esistenti
let markersMap = new Map();

// WebSocket variables
let websocket = null;
let isReconnecting = false;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_INTERVAL = 3000;

// OTTIMIZZAZIONE: Debouncing per map events
let mapMoveTimeout = null;
let shopsLoadTimeout = null;

// User profile data
const DEFAULT_USER_PROFILE = {
  id: null,
  age: "--",
  profession: "--",
  interests: "--"
};

// MAPPATURA CATEGORIE AGGIORNATA
const categoryMapping = {
  "all": "all",
  "abbigliamento": ["clothes", "shoes", "jewelry", "bag", "fashion_accessories", "boutique", "tailor"],
  "parrucchiere": ["hairdresser", "hairdresser_supply", "beauty", "cosmetics", "perfumery", "massage"],
  "supermercato": ["supermarket", "convenience", "minimarket", "greengrocer", "butcher"],
  "cibo": ["bakery", "pastry", "deli", "confectionery", "seafood", "cheese", "frozen_food", "tea", "coffee", "ice_cream", "chocolate", "wine", "alcohol", "beverages"],
  "auto": ["car_repair", "car", "car_parts", "motorcycle", "motorcycle_repair", "motorcycle_parts", "tyres", "bicycle"],
  "bellezza": ["beauty", "cosmetics", "perfumery", "massage", "tattoo", "erotic", "wellness"],
  "casa": ["furniture", "houseware", "interior_decoration", "bathroom_furnishing", "kitchen", "curtain", "lighting", "carpet", "tiles", "doors", "windows", "paint", "hardware", "doityourself"]
};

// Mapping per icone categorie
const categoryIcons = {
  "abbigliamento": "https://maps.google.com/mapfiles/ms/icons/pink.png",
  "parrucchiere": "https://maps.google.com/mapfiles/ms/icons/purple.png", 
  "supermercato": "https://maps.google.com/mapfiles/ms/icons/blue.png",
  "cibo": "https://maps.google.com/mapfiles/ms/icons/yellow.png",
  "auto": "https://maps.google.com/mapfiles/ms/icons/orange.png",
  "bellezza": "https://maps.google.com/mapfiles/ms/icons/ltblue.png",
  "casa": "https://maps.google.com/mapfiles/ms/icons/red.png"
};

// DOM Elements
const loadingOverlay = document.getElementById("loading-overlay");
const containerEl = document.querySelector(".container");
const loginCard = document.getElementById("login-card");
const sidebarEl = document.getElementById("sidebar");
const welcomeText = document.getElementById("welcomeText");
const userAvatar = document.getElementById("user-avatar");

// Local cache for fetched data
const localCache = {
  shopAreas: {},
  notifications: [],
  profile: null
};

// Initialize
document.addEventListener("DOMContentLoaded", function() {
  console.log("DOM Content Loaded - Inizializzazione app");
  
  // UI event handlers
  document.getElementById("btn").onclick = handleLogin;
  document.getElementById("logoutButton").onclick = handleLogout;
  document.getElementById("theme-toggle").onclick = toggleTheme;
  document.getElementById("center-map").onclick = centerMapOnUser;
  document.getElementById("clear-route").onclick = clearRoute;
  document.querySelector(".sidebar-toggle").onclick = toggleSidebar;
  document.getElementById("load-more-notifications").onclick = loadMoreNotifications;
  
  // Set up category filters
  setupCategoryFilters();
  
  // Set up Intersection Observer for lazy loading
  setupLazyLoadingObservers();
  
  // Check for stored theme preference
  const storedTheme = localStorage.getItem("nearYouTheme");
  if (storedTheme === "dark") {
    toggleTheme();
  }
  
  // Check for existing token
  const storedToken = sessionStorage.getItem("nearYouToken");
  if (storedToken) {
    token = storedToken;
    username = sessionStorage.getItem("nearYouUsername") || "";
    processLogin();
  } else {
    setTimeout(() => {
      loadingOverlay.style.display = "none";
    }, 500);
  }
});

function setupCategoryFilters() {
  console.log("Setup filtri categorie");
  const categoryPills = document.querySelectorAll(".category-pill");
  categoryPills.forEach(pill => {
    pill.addEventListener("click", () => {
      console.log(`Filtro categoria selezionato: ${pill.dataset.category}`);
      
      // Aggiorna UI
      categoryPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      
      // Aggiorna filtro
      categoryFilter = pill.dataset.category;
      
      // Riapplica filtro solo se abbiamo dati
      if (isDataLoaded && allShops.length > 0) {
        filterShopsByCategory();
      } else {
        console.log("Dati non ancora caricati, filtro verrà applicato al caricamento");
      }
    });
  });
}

function setupLazyLoadingObservers() {
  // Observer for lazy loading notifications
  lazyLoadObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !isLoadingMoreNotifications) {
        console.log("Notification sentinel is visible, loading more notifications");
        loadMoreNotifications();
      }
    });
  }, {
    rootMargin: '0px 0px 100px 0px'
  });
  
  // Observe the sentinel element
  const sentinel = document.querySelector('.notification-sentinel');
  if (sentinel) {
    lazyLoadObserver.observe(sentinel);
  }
  
  // Observer for stats section
  const statsObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        console.log("Stats section is visible, fetching stats");
        fetchUserStats();
        statsObserver.unobserve(entry.target);
      }
    });
  });
  
  // Observe stats section
  const statsSection = document.querySelector('.stats-grid');
  if (statsSection) {
    statsObserver.observe(statsSection);
  }
}

function handleLogin() {
  const usernameInput = document.getElementById("user").value.trim();
  const pwd = document.getElementById("pass").value;
  document.getElementById("err").textContent = "";
  
  if (!usernameInput || !pwd) {
    document.getElementById("err").textContent = "Compila entrambi i campi.";
    return;
  }
  
  loadingOverlay.style.display = "flex";
  
  fetch("/api/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: usernameInput, password: pwd }),
  })
  .then(res => res.json())
  .then(data => {
    if (!data.access_token) {
      throw new Error("Token non ricevuto");
    }
    token = data.access_token;
    username = usernameInput;
    
    // Store in session storage
    sessionStorage.setItem("nearYouToken", token);
    sessionStorage.setItem("nearYouUsername", username);
    
    processLogin();
  })
  .catch(err => {
    loadingOverlay.style.display = "none";
    document.getElementById("err").textContent = err.message || "Errore di login";
  });
}

function processLogin() {
  console.log("Processando login...");
  
  // Set welcome text and avatar
  welcomeText.textContent = `${username}`;
  userAvatar.textContent = username.charAt(0).toUpperCase();
  
  // Hide login, show container
  loginCard.style.display = "none";
  containerEl.style.display = "flex";
  
  // Initialize map and start update loop
  initMap();
  fetchUserProfile();
  
  // Set timer
  startTime = new Date();
  
  // Setup WebSocket connection for real-time updates
  setupWebSocket();
  
  // Fallback to polling if WebSocket setup fails after 5 seconds
  setTimeout(() => {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
      console.log("WebSocket non disponibile, fallback al polling");
      fallbackToPolling();
    }
  }, 5000);
  
  // Update active time
  setInterval(updateActiveTime, 60000);
  
  // Load initial notifications
  loadMoreNotifications();
  
  // Hide loading overlay
  setTimeout(() => {
    loadingOverlay.style.display = "none";
  }, 500);
}

function handleLogout() {
  // Chiudi il WebSocket
  closeWebSocket();
  
  token = "";
  username = "";
  userData = { ...DEFAULT_USER_PROFILE };
  clearMap();
  notifications = [];
  notificationsPage = 0;
  visitedShops = [];
  isMapInitialized = false;
  isDataLoaded = false;
  
  // Clear storage
  sessionStorage.removeItem("nearYouToken");
  sessionStorage.removeItem("nearYouUsername");
  
  // Clear caches
  localCache.shopAreas = {};
  localCache.notifications = [];
  localCache.profile = null;
  
  // Clear markers map
  markersMap.clear();
  
  // Refresh the page
  window.location.reload();
}

function toggleTheme() {
  isDarkTheme = !isDarkTheme;
  if (isDarkTheme) {
    document.body.classList.add("dark-theme");
    document.getElementById("theme-toggle").innerHTML = '<i class="fas fa-sun"></i>';
    localStorage.setItem("nearYouTheme", "dark");
  } else {
    document.body.classList.remove("dark-theme");
    document.getElementById("theme-toggle").innerHTML = '<i class="fas fa-moon"></i>';
    localStorage.setItem("nearYouTheme", "light");
  }
}

function toggleSidebar() {
  sidebarEl.classList.toggle("active");
}

function initMap() {
  console.log("Inizializzazione mappa...");
  
  map = L.map("map").setView([45.4642, 9.19], 15);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors"
  }).addTo(map);
  
  const userIcon = L.icon({
    iconUrl: "https://maps.google.com/mapfiles/kml/shapes/cycling.png",
    iconSize: [32, 32],
    iconAnchor: [16, 32],
  });
  
  userMarker = L.marker([45.4642, 9.19], { icon: userIcon });
  userPolyline = L.polyline([], { color: 'blue', weight: 3 });
  
  // Force map size calculation
  setTimeout(() => {
    map.invalidateSize();
    isMapInitialized = true;
    console.log("Mappa inizializzata con successo");
    
    // Setup map event listeners for lazy loading
    setupMapListeners();
  }, 300);
}

// OTTIMIZZAZIONE: Setup listeners mappa con debouncing
function setupMapListeners() {
  console.log("Setup listeners mappa...");
  
  // DEBOUNCING: Aspetta 300ms dopo stop movimento prima di caricare shops
  map.on('moveend', function() {
    // Cancella timeout precedente
    if (mapMoveTimeout) {
      clearTimeout(mapMoveTimeout);
    }
    
    // Imposta nuovo timeout
    mapMoveTimeout = setTimeout(() => {
      console.log("Map view changed (debounced), loading shops for visible area");
      if (token && isMapInitialized) {
        fetchShopsInVisibleArea();
      }
    }, 300);
  });
  
  // Also load shops when map is first initialized
  if (token && isMapInitialized) {
    console.log("Caricamento iniziale negozi");
    fetchShopsInVisibleArea();
  }
}

function clearMap() {
  if (map) {
    if (userMarker && userMarker._map) map.removeLayer(userMarker);
    if (userPolyline && userPolyline._map) map.removeLayer(userPolyline);
    
    // Clear shop markers
    markersMap.forEach(marker => {
      if (marker._map) map.removeLayer(marker);
    });
    markersMap.clear();
    shopsMarkers = [];
    
    // Reset route
    routePoints = [];
  }
}

// WebSocket setup and management
function setupWebSocket() {
  if (!token || websocket) return;
  
  // Determina il protocollo corretto
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const wsUrl = `${protocol}//${host}/ws/positions`;
  
  console.log(`Connecting to WebSocket at ${wsUrl}`);
  
  websocket = new WebSocket(wsUrl);
  
  websocket.onopen = () => {
    console.log('WebSocket connection established');
    reconnectAttempts = 0;
    
    websocket.send(JSON.stringify({
      token: token
    }));
  };
  
  websocket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      
      if (data.type === 'connection_established') {
        console.log(`WebSocket connection confirmed for user ${data.user_id}`);
      }
      else if (data.type === 'position_update') {
        updateUserPosition(data.data);
      }
      else if (data.error) {
        console.error(`WebSocket error: ${data.error}`);
        closeWebSocket();
      }
    } catch (e) {
      console.error('Error parsing WebSocket message:', e);
    }
  };
  
  websocket.onerror = (error) => {
    console.error('WebSocket error:', error);
  };
  
  websocket.onclose = (event) => {
    console.log(`WebSocket connection closed with code ${event.code}`);
    websocket = null;
    
    if (!isReconnecting && event.code !== 1000) {
      reconnectWebSocket();
    }
  };
}

function reconnectWebSocket() {
  if (isReconnecting || reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return;
  
  isReconnecting = true;
  reconnectAttempts++;
  
  console.log(`Attempting to reconnect WebSocket (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
  
  showReconnectingNotification();
  
  setTimeout(() => {
    isReconnecting = false;
    setupWebSocket();
  }, RECONNECT_INTERVAL);
}

function closeWebSocket() {
  if (websocket) {
    websocket.close(1000, "Disconnessione volontaria");
    websocket = null;
  }
}

function showReconnectingNotification() {
  const reconnectDiv = document.createElement('div');
  reconnectDiv.className = 'reconnect-notification';
  reconnectDiv.innerHTML = `<i class="fas fa-sync-alt fa-spin"></i> Riconnessione in corso...`;
  
  const existingNotification = document.querySelector('.reconnect-notification');
  if (existingNotification) {
    existingNotification.replaceWith(reconnectDiv);
  } else {
    document.getElementById('map-container').appendChild(reconnectDiv);
  }
  
  setTimeout(() => {
    reconnectDiv.remove();
  }, 3000);
}

// Fallback al polling HTTP
async function pollUserPosition() {
  if (!token) return;
  try {
    const res = await fetch("/api/user/positions", {
      headers: { Authorization: `Bearer ${token}` }
    });
    const { positions } = await res.json();
    
    if (positions && positions.length > 0) {
      updateUserPosition(positions[0]);
    }
  } catch (err) {
    console.error("Error fetching position:", err);
  }
}

function fallbackToPolling() {
  console.log("Fallback to HTTP polling due to WebSocket failure");
  
  pollUserPosition();
  setInterval(pollUserPosition, 5000); // Ogni 5 secondi invece di 3
}

function updateUserPosition(positionData) {
  const { latitude, longitude, message, user_id, visited_shops: visitedShopsData } = positionData;
  const latlng = [latitude, longitude];
  
  console.log(`Aggiornamento posizione utente: [${latitude}, ${longitude}]`);
  
  // Store position and update route
  currentPosition = latlng;
  routePoints.push(latlng);
  
  // Limit route points for performance
  if (routePoints.length > 100) {
    routePoints = routePoints.slice(-100);
  }
  
  // Update map
  if (!userMarker._map) {
    userMarker.setLatLng(latlng).addTo(map);
    map.setView(latlng, 15);
  } else {
    userMarker.setLatLng(latlng);
  }
  
  // Update polyline
  userPolyline.setLatLngs(routePoints);
  if (!userPolyline._map) {
    userPolyline.addTo(map);
  }
  
  // Aggiorna negozi visitati se ci sono dati
  if (visitedShopsData && visitedShopsData.length > 0) {
    visitedShops = visitedShopsData;
    if (isDataLoaded) {
      filterShopsByCategory();
    }
    console.log(`Aggiornati ${visitedShopsData.length} negozi visitati`);
  }
  
  // Update notification if we have a message
  if (message && message.trim() !== "") {
    const isNewMessage = !notifications.some(n => n.message === message);
    
    if (isNewMessage) {
      const timestamp = new Date().toLocaleTimeString();
      
      let closestShop = null;
      if (allShops.length > 0) {
        closestShop = findClosestShop(latlng);
      }
      
      const notification = {
        id: Date.now(),
        message: message,
        timestamp: timestamp,
        shopName: closestShop ? closestShop.name : "Negozio nelle vicinanze",
        category: closestShop ? closestShop.category : "shopping"
      };
      
      notifications.unshift(notification);
      localCache.notifications.unshift(notification);
      updateNotifications();
      
      if (userPopup) {
        map.closePopup(userPopup);
      }
      
      userPopup = L.popup({
        className: 'custom-popup'
      })
      .setLatLng(latlng)
      .setContent(`
        <div class="popup-header">${notification.shopName}</div>
        <div class="popup-content">
          <div>Sei vicino a questo negozio!</div>
          <div class="popup-message">${message}</div>
        </div>
      `)
      .openOn(map);
      
      document.getElementById("total-notifications").textContent = notifications.length;
    }
  }
  
  // Update total distance
  if (routePoints.length > 1) {
    const totalDistance = calculateRouteDistance(routePoints);
    document.getElementById("total-distance").textContent = totalDistance.toFixed(1);
  }
  
  // Check if we need to load shops for this area - OTTIMIZZATO
  if (map && shouldLoadShopsForPosition(latlng)) {
    // DEBOUNCING anche per position updates
    if (shopsLoadTimeout) {
      clearTimeout(shopsLoadTimeout);
    }
    
    shopsLoadTimeout = setTimeout(() => {
      fetchShopsInVisibleArea();
    }, 500);
  }
}

function shouldLoadShopsForPosition(position) {
  const bounds = map.getBounds();
  if (!bounds.contains(position)) {
    return true;
  }
  
  if (allShops.length < 5) {
    return true;
  }
  
  return false;
}

function updateNotifications() {
  const container = document.getElementById("notifications-container");
  
  const recentNotifications = localCache.notifications.slice(0, 10);
  
  container.innerHTML = "";
  
  if (recentNotifications.length === 0) {
    container.innerHTML = '<div class="notification-item">Nessuna notifica ricevuta</div>';
    return;
  }
  
  recentNotifications.forEach(notification => {
    let iconClass = "fas fa-shopping-bag";
    if (notification.category === "ristorante" || notification.category === "bar") {
      iconClass = "fas fa-utensils";
    } else if (notification.category === "abbigliamento") {
      iconClass = "fas fa-tshirt";
    } else if (notification.category === "supermercato") {
      iconClass = "fas fa-shopping-cart";
    } else if (notification.category === "elettronica") {
      iconClass = "fas fa-laptop";
    }
    
    const notificationEl = document.createElement("div");
    notificationEl.className = "notification-item";
    notificationEl.innerHTML = `
      <div class="notification-icon">
        <i class="${iconClass}"></i>
      </div>
      <div class="notification-content">
        <div class="notification-title">${notification.shopName}</div>
        <div class="notification-desc">${notification.message}</div>
        <div class="notification-time">${notification.timestamp}</div>
      </div>
    `;
    container.appendChild(notificationEl);
  });
}

async function fetchUserProfile() {
  if (!token) return;
  
  if (localCache.profile) {
    userData = { ...localCache.profile };
    updateProfileUI();
    return;
  }
  
  try {
    const res = await fetch("/api/user/profile", {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    let profileData;
    
    try {
      profileData = await res.json();
      
      localCache.profile = {
        id: profileData.user_id,
        age: profileData.age,
        profession: profileData.profession,
        interests: profileData.interests
      };
      
    } catch (e) {
      console.error("Error parsing profile data:", e);
      profileData = {
        user_id: 1,
        age: Math.floor(Math.random() * 30) + 20,
        profession: ["Ingegnere", "Avvocato", "Medico", "Insegnante", "Studente"][Math.floor(Math.random() * 5)],
        interests: ["Tecnologia, Sport, Cinema", "Viaggi, Cibo, Libri", "Musica, Arte, Fotografia"][Math.floor(Math.random() * 3)]
      };
    }
    
    userData = {
      id: profileData.user_id,
      age: profileData.age,
      profession: profileData.profession,
      interests: profileData.interests
    };
    
    updateProfileUI();
    
  } catch (err) {
    console.error("Error fetching user profile:", err);
  }
}

function updateProfileUI() {
  document.getElementById("user-id").textContent = `ID: ${userData.id}`;
  document.getElementById("user-age").textContent = `Età: ${userData.age}`;
  document.getElementById("user-job").textContent = `Professione: ${userData.profession}`;
  document.getElementById("user-interests").textContent = `Interessi: ${userData.interests}`;
}

async function fetchUserStats() {
  if (!token) return;
  
  try {
    const res = await fetch("/api/user/stats", {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    const stats = await res.json();
    
    document.getElementById("total-notifications").textContent = stats.notifications || "0";
    
  } catch (err) {
    console.error("Error fetching user stats:", err);
  }
}

// OTTIMIZZAZIONE: fetchShopsInVisibleArea con limit
async function fetchShopsInVisibleArea() {
  if (!token || !map || !isMapInitialized) {
    console.log("Non posso caricare negozi: token, mappa o inizializzazione mancanti", {
      token: !!token,
      map: !!map,
      initialized: isMapInitialized
    });
    return;
  }
  
  const bounds = map.getBounds();
  const visibleArea = {
    north: bounds.getNorth(),
    south: bounds.getSouth(),
    east: bounds.getEast(),
    west: bounds.getWest()
  };
  
  const cacheKey = `${visibleArea.west.toFixed(4)},${visibleArea.south.toFixed(4)},${visibleArea.east.toFixed(4)},${visibleArea.north.toFixed(4)}`;
  
  if (localCache.shopAreas[cacheKey]) {
    console.log("Using cached shops for this area");
    allShops = localCache.shopAreas[cacheKey];
    isDataLoaded = true;
    filterShopsByCategory();
    return;
  }
  
  try {
    console.log("Fetching shops for visible area:", visibleArea);
    
    const res = await fetch(`/api/user/shops/inArea?n=${visibleArea.north}&s=${visibleArea.south}&e=${visibleArea.east}&w=${visibleArea.west}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    let shops;
    try {
      shops = await res.json();
    } catch (e) {
      console.error("Error parsing shops data:", e);
      shops = generateFallbackShopsInArea(visibleArea);
    }
    
    // OTTIMIZZAZIONE: Limita il numero di shops processati
    const maxShops = 100;
    if (shops.length > maxShops) {
      console.log(`Limitando shops da ${shops.length} a ${maxShops}`);
      shops = shops.slice(0, maxShops);
    }
    
    const normalizedShops = shops.map(shop => ({
      id: shop.id || shop.shop_id,
      name: shop.shop_name || shop.name,
      category: shop.category,
      lat: shop.lat || (shop.geom ? shop.geom.coordinates[1] : 0),
      lon: shop.lon || (shop.geom ? shop.geom.coordinates[0] : 0)
    }));
    
    allShops = normalizedShops;
    isDataLoaded = true;
    
    localCache.shopAreas[cacheKey] = normalizedShops;
    
    console.log(`Caricati ${normalizedShops.length} negozi per l'area visibile`);
    
    filterShopsByCategory();
    updateShopCount();
    
  } catch (err) {
    console.error("Error fetching shops:", err);
  }
}

function generateFallbackShopsInArea(area) {
  const categories = Object.keys(categoryMapping).filter(cat => cat !== "all");
  const shops = [];
  
  // RIDOTTO: max 50 shops invece di 60
  for (let i = 1; i <= 50; i++) {
    const lat = area.south + (Math.random() * (area.north - area.south));
    const lon = area.west + (Math.random() * (area.east - area.west));
    
    const categoryName = categories[Math.floor(Math.random() * categories.length)];
    const realCategories = categoryMapping[categoryName];
    const realCategory = realCategories[Math.floor(Math.random() * realCategories.length)];
    
    shops.push({
      id: i,
      shop_name: `${categoryName.charAt(0).toUpperCase() + categoryName.slice(1)} ${i}`,
      category: realCategory,
      lat: lat,
      lon: lon
    });
  }
  
  console.log("Generated fallback shops:", shops);
  return shops;
}

// OTTIMIZZAZIONE: Update incrementali marker - MIGLIORATO
function updateShopMarkersOptimized(shops) {
  console.log(`Update incrementale per ${shops.length} negozi`);
  
  const currentShopIds = new Set(shops.map(shop => shop.id));
  
  // BATCH DOM OPERATIONS: Rimuovi marker in batch
  const markersToRemove = [];
  for (const [shopId, marker] of markersMap.entries()) {
    if (!currentShopIds.has(shopId)) {
      markersToRemove.push({ shopId, marker });
    }
  }
  
  // Rimuovi in batch
  markersToRemove.forEach(({ shopId, marker }) => {
    map.removeLayer(marker);
    markersMap.delete(shopId);
  });
  
  // BATCH DOM OPERATIONS: Aggiungi marker in batch  
  const markersToAdd = [];
  shops.forEach(shop => {
    const existingMarker = markersMap.get(shop.id);
    
    if (!existingMarker) {
      const marker = createShopMarker(shop);
      markersToAdd.push({ marker, shopId: shop.id });
    } else {
      updateExistingMarker(existingMarker, shop);
    }
  });
  
  // Aggiungi in batch
  markersToAdd.forEach(({ marker, shopId }) => {
    marker.addTo(map);
    markersMap.set(shopId, marker);
  });
  
  console.log(`Marker ottimizzati: ${markersMap.size} totali sulla mappa`);
}

function createShopMarker(shop) {
  const isVisited = visitedShops.some(v => v.shop_id === shop.id);
  
  let iconUrl = isVisited ? 
    "https://maps.google.com/mapfiles/ms/icons/green.png" :
    getShopCategoryIcon(shop.category);
  
  const shopIcon = L.icon({
    iconUrl: iconUrl,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32]
  });
  
  const marker = L.marker([shop.lat, shop.lon], { icon: shopIcon });
  
  const popupContent = createPopupContent(shop, isVisited);
  marker.bindPopup(popupContent);
  
  marker._shopData = {
    id: shop.id,
    visited: isVisited,
    category: shop.category,
    lat: shop.lat,
    lon: shop.lon
  };
  
  return marker;
}

function updateExistingMarker(marker, shop) {
  const oldData = marker._shopData;
  const isVisited = visitedShops.some(v => v.shop_id === shop.id);
  
  const needsUpdate = (
    oldData.visited !== isVisited ||
    oldData.category !== shop.category ||
    Math.abs(oldData.lat - shop.lat) > 0.0001 ||
    Math.abs(oldData.lon - shop.lon) > 0.0001
  );
  
  if (needsUpdate) {
    if (oldData.lat !== shop.lat || oldData.lon !== shop.lon) {
      marker.setLatLng([shop.lat, shop.lon]);
    }
    
    if (oldData.visited !== isVisited || oldData.category !== shop.category) {
      const newIconUrl = isVisited ? 
        "https://maps.google.com/mapfiles/ms/icons/green.png" :
        getShopCategoryIcon(shop.category);
        
      const newIcon = L.icon({
        iconUrl: newIconUrl,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
      });
      
      marker.setIcon(newIcon);
    }
    
    const newPopupContent = createPopupContent(shop, isVisited);
    marker.setPopupContent(newPopupContent);
    
    marker._shopData = {
      id: shop.id,
      visited: isVisited,
      category: shop.category,
      lat: shop.lat,
      lon: shop.lon
    };
    
    console.log(`Aggiornato marker per ${shop.name || shop.shop_name}`);
  }
}

function getShopCategoryIcon(category) {
  const cat = category ? category.toLowerCase() : "";
  
  for (const [key, values] of Object.entries(categoryMapping)) {
    if (key === "all") continue;
    if (values.some(val => cat.includes(val) || val.includes(cat))) {
      return categoryIcons[key] || "https://maps.google.com/mapfiles/ms/icons/red.png";
    }
  }
  
  return "https://maps.google.com/mapfiles/ms/icons/red.png";
}

function createPopupContent(shop, isVisited) {
  return `
    <div class="custom-popup">
      <div class="popup-header ${isVisited ? 'visited' : ''}">${shop.name || shop.shop_name}</div>
      <div class="popup-content">
        ${isVisited ? '<div class="visited-badge">Visitato!</div>' : ''}
        <div>Categoria: ${shop.category}</div>
        <div>ID: ${shop.id}</div>
        ${shop.distance ? `<div>Distanza: ${(shop.distance * 1000).toFixed(0)}m</div>` : ''}
      </div>
    </div>
  `;
}

function filterShopsByCategory() {
  if (!isDataLoaded || allShops.length === 0) {
    console.log("Impossibile filtrare: dati non ancora caricati");
    return;
  }
  
  console.log(`Applicando filtro categoria: ${categoryFilter}`);
  console.log(`Totale negozi disponibili: ${allShops.length}`);
  
  let finalShops = [];
  let categoryCount = 0;
  
  if (categoryFilter === "all") {
    finalShops = [...allShops];
    categoryCount = allShops.length;
  } else {
    const targetCategories = categoryMapping[categoryFilter] || [categoryFilter];
    
    const categoryShops = allShops.filter(shop => {
      if (!shop.category) return false;
      
      const shopCategory = shop.category.toLowerCase().trim();
      
      return targetCategories.some(target => {
        return shopCategory === target || 
               shopCategory.includes(target) ||
               target.includes(shopCategory);
      });
    });
    
    categoryCount = categoryShops.length;
    
    const visitedShopIds = visitedShops.map(v => v.shop_id);
    const visitedShopsOnMap = allShops.filter(shop => 
      visitedShopIds.includes(shop.id) && 
      !categoryShops.some(filtered => filtered.id === shop.id)
    );
    
    finalShops = [...categoryShops, ...visitedShopsOnMap];
    
    if (visitedShopsOnMap.length > 0) {
      console.log(`Negozi visitati sempre visibili:`, visitedShopsOnMap.map(s => s.name || s.shop_name));
    }
  }
  
  console.log(`Filtro "${categoryFilter}": ${categoryCount} della categoria + ${finalShops.length - categoryCount} visitati extra = ${finalShops.length} totali mostrati`);
  
  updateShopMarkersOptimized(finalShops);
  updateShopCount(finalShops, categoryCount);
}

function updateShopCount(shopsDisplayed = null, categoryCount = null, visitedExtraCount = null) {
  let countText;
  
  if (categoryFilter === "all") {
    const total = shopsDisplayed ? shopsDisplayed.length : allShops.length;
    countText = `${total}`;
  } else {
    const actualCategoryCount = categoryCount || 0;
    countText = `${actualCategoryCount}`;
  }
  
  document.getElementById("shops-nearby").textContent = countText;
}

function findClosestShop(position) {
  if (!allShops || allShops.length === 0) return null;
  
  let closestShop = null;
  let minDistance = Infinity;
  
  allShops.forEach(shop => {
    const distance = calculateHaversineDistance(
      position[0], position[1], 
      shop.lat, shop.lon
    );
    
    if (distance < minDistance) {
      minDistance = distance;
      closestShop = shop;
    }
  });
  
  return closestShop;
}

async function loadMoreNotifications() {
  if (!token || isLoadingMoreNotifications) return;
  
  isLoadingMoreNotifications = true;
  
  try {
    const loadMoreBtn = document.getElementById("load-more-notifications");
    loadMoreBtn.textContent = "Caricamento...";
    
    const res = await fetch(`/api/user/promotions?offset=${notificationsPage * 10}&limit=10`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    const data = await res.json();
    
    if (data.promotions && data.promotions.length > 0) {
      const newNotifications = data.promotions.map(p => ({
        id: p.event_id,
        message: p.message,
        timestamp: new Date(p.timestamp).toLocaleTimeString(),
        shopName: p.shop_name,
        category: determineCategory(p.shop_name)
      }));
      
      localCache.notifications = [...localCache.notifications, ...newNotifications];
      
      updateNotifications();
      
      notificationsPage++;
      
      if (data.promotions.length < 10) {
        loadMoreBtn.style.display = "none";
      } else {
        loadMoreBtn.textContent = "Carica altre notifiche";
      }
    } else {
      loadMoreBtn.style.display = "none";
    }
  } catch (err) {
    console.error("Error loading more notifications:", err);
  } finally {
    isLoadingMoreNotifications = false;
  }
}

function determineCategory(shopName) {
  shopName = shopName.toLowerCase();
  
  if (shopName.includes("ristorante") || shopName.includes("trattoria") || shopName.includes("pizzeria")) {
    return "ristorante";
  } else if (shopName.includes("bar") || shopName.includes("caffè") || shopName.includes("cafe")) {
    return "bar";
  } else if (shopName.includes("super") || shopName.includes("market")) {
    return "supermercato";
  } else if (shopName.includes("tech") || shopName.includes("elettro")) {
    return "elettronica";
  } else if (shopName.includes("moda") || shopName.includes("abbiglia")) {
    return "abbigliamento";
  }
  
  return "shopping";
}

function centerMapOnUser() {
  if (currentPosition) {
    map.setView(currentPosition, 15);
  }
}

function clearRoute() {
  routePoints = [];
  if (currentPosition) {
    routePoints.push(currentPosition);
  }
  userPolyline.setLatLngs(routePoints);
  document.getElementById("total-distance").textContent = "0";
}

function updateActiveTime() {
  if (!startTime) return;
  
  const now = new Date();
  const diffMinutes = Math.floor((now - startTime) / 60000);
  document.getElementById("active-time").textContent = diffMinutes;
}

// Utility Functions
function calculateHaversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * 
    Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  const d = R * c;
  return d;
}

function toRad(deg) {
  return deg * Math.PI / 180;
}

function calculateRouteDistance(points) {
  let distance = 0;
  for (let i = 1; i < points.length; i++) {
    distance += calculateHaversineDistance(
      points[i-1][0], points[i-1][1],
      points[i][0], points[i][1]
    );
  }
  return distance;
}