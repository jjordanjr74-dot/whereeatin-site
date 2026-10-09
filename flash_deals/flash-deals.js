/*
 * Premium Flash Deal JavaScript - Professional Grade
 * For Where We Eatin' and Restaurant Radar
 */

class PremiumFlashDealSystem {
  constructor(platform) {
    this.platform = platform;
    this.activeDeals = [];
    this.bannerTimeout = null;
    this.dealHistory = [];
    this.analytics = {};
    this.init();
  }

  init() {
    // Initialize premium flash deal functionality
    this.setupBanner();
    this.startPolling();
    this.bindEvents();
    this.initializeAnalytics();
    
    console.log(`Premium Flash Deal System initialized for ${this.platform}`);
  }

  setupBanner() {
    // Create premium banner element
    this.banner = document.createElement('div');
    this.banner.id = 'premium-flash-deal-banner';
    this.banner.className = 'flash-deal-banner hidden';
    this.banner.innerHTML = `
      <div class="flash-deal-content">
        <span class="flash-deal-icon">⚡</span>
        <span class="flash-deal-text">PREMIUM FLASH DEAL ALERT!</span>
        <button class="flash-deal-close" onclick="window.${this.platform}FlashDealManager.closeBanner()">×</button>
      </div>
    `;
    
    document.body.appendChild(this.banner);
    console.log('Premium banner element created');
  }

  async startPolling() {
    // Start real-time polling for active deals
    setInterval(async () => {
      await this.checkForActiveDeals();
    }, 30000); // Check every 30 seconds
    
    // Initial check
    await this.checkForActiveDeals();
    console.log('Real-time deal polling started');
  }

  async checkForActiveDeals() {
    try {
      // Fetch active deals from API
      const response = await fetch(`/api/premium-flash-deals-${this.platform}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`,
          'X-Platform': this.platform
        },
        cache: 'no-cache'
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const deals = await response.json();
      this.updateFlashDeals(deals);
      
    } catch (error) {
      console.warn(`Error fetching ${this.platform} flash deals:`, error);
      // Fallback: check localStorage for cached deals
      this.checkCachedDeals();
    }
  }

  updateFlashDeals(deals) {
    const newActiveDeals = deals.filter(deal => deal.isActive && !deal.isExpired);
    
    if (newActiveDeals.length > 0 && newActiveDeals.length !== this.activeDeals.length) {
      this.showPremiumFlashDealBanner(newActiveDeals);
      this.playNotificationSound();
      this.updateTruckBadges(newActiveDeals);
      this.updateHeaderIndicator(newActiveDeals.length);
      this.logDealActivity(newActiveDeals);
    }
    
    this.activeDeals = newActiveDeals;
    this.updateFlashDealSection(newActiveDeals);
  }

  showPremiumFlashDealBanner(deals) {
    const banner = document.getElementById('premium-flash-deal-banner');
    if (!banner) return;

    // Animate the banner with premium effects
    banner.classList.remove('hidden');
    banner.classList.add('show');
    
    // Add premium pulsing animation
    banner.style.animation = 'premiumFlash 1.5s infinite alternate';
    
    // Auto-hide after 15 seconds
    clearTimeout(this.bannerTimeout);
    this.bannerTimeout = setTimeout(() => {
      this.closeBanner();
    }, 15000);

    // Log the event
    console.log(`Premium flash deal banner shown for ${deals.length} active deals`);
  }

  closeBanner() {
    const banner = document.getElementById('premium-flash-deal-banner');
    if (!banner) return;

    banner.classList.remove('show');
    banner.classList.add('hidden');
    
    console.log('Premium flash deal banner closed');
  }

  playNotificationSound() {
    // Play premium notification sound
    try {
      // Create audio context for premium sound
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.type = 'sine';
      oscillator.frequency.value = 800; // Premium alert frequency
      gainNode.gain.value = 0.3;

      oscillator.start();
      gainNode.gain.exponentialRampToValueAtTime(0.00001, audioContext.currentTime + 0.5);
      oscillator.stop(audioContext.currentTime + 0.5);

      console.log('Premium notification sound played');
    } catch (error) {
      console.warn('Could not play notification sound:', error);
    }
  }

  updateTruckBadges(deals) {
    // Update individual truck cards with premium deal badges
    const trucks = document.querySelectorAll('.truck-card');
    trucks.forEach(truck => {
      const truckId = truck.dataset.truckId;
      const deal = deals.find(d => d.truckId === truckId);
      
      if (deal) {
        this.addTruckFlashBadge(truck, deal);
      } else {
        this.removeTruckFlashBadge(truck);
      }
    });
  }

  addTruckFlashBadge(truck, deal) {
    // Remove existing badge
    this.removeTruckFlashBadge(truck);

    // Create premium flash deal badge
    const badge = document.createElement('div');
    badge.className = 'truck-flash-deal-badge';
    badge.innerHTML = `
      <span class="deal-icon">⚡</span>
      <span class="deal-text">${deal.discount}</span>
      <span class="deal-expiry">${deal.timeRemaining}</span>
    `;
    
    truck.appendChild(badge);
  }

  removeTruckFlashBadge(truck) {
    const existingBadge = truck.querySelector('.truck-flash-deal-badge');
    if (existingBadge) {
      existingBadge.remove();
    }
  }

  updateHeaderIndicator(count) {
    const indicator = document.getElementById('flash-deal-indicator');
    if (!indicator) return;

    const countElement = indicator.querySelector('.deal-count');
    if (countElement) {
      countElement.textContent = count;
    }

    if (count > 0) {
      indicator.style.display = 'flex';
      indicator.classList.add('active');
    } else {
      indicator.style.display = 'none';
      indicator.classList.remove('active');
    }
  }

  updateFlashDealSection(deals) {
    const section = document.getElementById('flash-deals-section');
    if (!section) return;

    if (deals.length === 0) {
      section.style.display = 'none';
      return;
    }

    section.style.display = 'block';
    const container = section.querySelector('.flash-deals-container');
    if (!container) return;

    container.innerHTML = deals.map(deal => this.renderFlashDealItem(deal)).join('');
  }

  renderFlashDealItem(deal) {
    return `
      <div class="flash-deal-item" data-deal-id="${deal.id}" data-platform="${this.platform}">
        <div class="deal-header">
          <span class="deal-icon">🔥</span>
          <h3>${deal.truckName}</h3>
          <span class="deal-time">${deal.timeRemaining}</span>
        </div>
        <div class="deal-details">
          <p class="deal-description"><strong>${deal.discount}</strong> ${deal.description}</p>
          <p class="deal-location">📍 ${deal.location}</p>
          <p class="deal-distance">📏 ${deal.distance}</p>
          <div class="deal-conditions">
            <small>Valid until ${deal.expiryTime} • ${deal.conditions}</small>
          </div>
          <button class="deal-action" onclick="window.${this.platform}FlashDealManager.claimDeal('${deal.id}')">
            Claim Premium Deal →
          </button>
        </div>
      </div>
    `;
  }

  claimDeal(dealId) {
    // Handle premium deal claiming
    const deal = this.activeDeals.find(d => d.id === dealId);
    if (!deal) return;

    // Track the claim
    this.trackDealClaim(dealId);
    
    // Redirect to deal page or initiate purchase
    window.open(`/deals/${dealId}?platform=${this.platform}`, '_blank');
    
    console.log(`Premium deal claimed: ${dealId} on ${this.platform}`);
  }

  trackDealClaim(dealId) {
    // Track deal claim for analytics
    fetch('/api/track-premium-deal-claim', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAuthToken()}`
      },
      body: JSON.stringify({
        dealId: dealId,
        userId: this.getUserId(),
        platform: this.platform,
        timestamp: new Date().toISOString()
      })
    }).catch(error => {
      console.warn('Could not track premium deal claim:', error);
    });
  }

  bindEvents() {
    // Bind premium event handlers
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        // Refresh premium deals when user returns to page
        this.checkForActiveDeals();
      }
    });
  }

  getAuthToken() {
    // Get auth token from storage
    return localStorage.getItem('premiumAuthToken') || sessionStorage.getItem('premiumAuthToken');
  }

  getUserId() {
    // Get user ID from storage
    return localStorage.getItem('premiumUserId') || sessionStorage.getItem('premiumUserId');
  }

  checkCachedDeals() {
    // Check for cached premium deals in localStorage
    try {
      const cached = localStorage.getItem('premiumFlashDeals');
      if (cached) {
        const deals = JSON.parse(cached);
        const now = new Date();
        
        // Filter out expired premium deals
        const validDeals = deals.filter(deal => {
          const expiry = new Date(deal.expiry);
          return expiry > now;
        });
        
        if (validDeals.length > 0) {
          this.updateFlashDeals(validDeals);
        }
      }
    } catch (error) {
      console.warn('Could not check cached premium deals:', error);
    }
  }

  initializeAnalytics() {
    // Initialize premium analytics tracking
    this.analytics = {
      dealsShown: 0,
      dealsClaimed: 0,
      engagementRate: 0,
      conversionRate: 0,
      revenueGenerated: 0
    };
  }

  logDealActivity(deals) {
    // Log premium deal activity for analytics
    this.analytics.dealsShown += deals.length;
    this.analytics.engagementRate = (this.analytics.dealsClaimed / this.analytics.dealsShown) * 100;
    
    console.log(`Premium deal analytics: ${deals.length} deals shown, ${this.analytics.dealsShown} total`);
  }

  // Public methods for external integration
  getActiveDeals() {
    return this.activeDeals;
  }

  hasActiveDeals() {
    return this.activeDeals.length > 0;
  }

  getDealCount() {
    return this.activeDeals.length;
  }

  getPlatform() {
    return this.platform;
  }
}

// Initialize premium flash deal managers for both platforms
document.addEventListener('DOMContentLoaded', () => {
  window.whereeatinFlashDealManager = new PremiumFlashDealSystem('whereeatin');
  window.restaurantradarFlashDealManager = new PremiumFlashDealSystem('restaurantradar');
});

console.log('Premium Flash Deal System loaded successfully for both platforms');