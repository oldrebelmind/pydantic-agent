/**
 * IP Geolocation Service
 *
 * Fetches user's location and timezone data using ipgeolocation.io API
 */

export interface GeolocationData {
  ip: string;
  city: string;
  state_prov: string;
  country_name: string;
  country_code2: string;
  latitude: number;
  longitude: number;
  timezone: {
    name: string;
    offset: number;
    current_time: string;
    is_dst: boolean;
  };
  isp: string;
}

let cachedLocation: GeolocationData | null = null;

/**
 * Fetch user's IP geolocation data
 * Caches the result to avoid unnecessary API calls
 */
export async function fetchGeolocation(): Promise<GeolocationData | null> {
  // Return cached data if available
  if (cachedLocation) {
    console.log('[GEOLOCATION] Using cached location data');
    return cachedLocation;
  }

  const API_KEY = process.env.NEXT_PUBLIC_IPGEOLOCATION_API_KEY;

  if (!API_KEY || API_KEY === 'your-ipgeolocation-api-key-here') {
    console.warn('[GEOLOCATION] API key not configured');
    return null;
  }

  try {
    console.log('[GEOLOCATION] Fetching location data...');

    // Fetch IP geolocation with timezone data
    const response = await fetch(
      `https://api.ipgeolocation.io/ipgeo?apiKey=${API_KEY}`,
      {
        method: 'GET',
        cache: 'force-cache', // Cache in browser
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    // Debug: Log raw API response to see timezone data
    console.log('[GEOLOCATION] Raw API response:', {
      timezone: data.time_zone,
      timezone_name: data.time_zone?.name,
      timezone_offset: data.time_zone?.offset,
    });

    // Validate the response has required fields
    if (!data || typeof data !== 'object') {
      console.error('[GEOLOCATION] Invalid response format:', data);
      return null;
    }

    // Create properly typed GeolocationData with fallbacks
    const geoData: GeolocationData = {
      ip: data.ip || '',
      city: data.city || '',
      state_prov: data.state_prov || '',
      country_name: data.country_name || '',
      country_code2: data.country_code2 || '',
      latitude: data.latitude || 0,
      longitude: data.longitude || 0,
      timezone: (data.timezone && typeof data.timezone === 'object') ? {
        name: data.timezone?.name || '',
        offset: data.timezone?.offset || 0,
        current_time: data.timezone?.current_time || '',
        is_dst: data.timezone?.is_dst || false,
      } : {
        name: '',
        offset: 0,
        current_time: '',
        is_dst: false,
      },
      isp: data.isp || '',
    };

    // Cache the result
    cachedLocation = geoData;

    console.log('[GEOLOCATION] Location fetched:', {
      city: geoData.city,
      state: geoData.state_prov,
      country: geoData.country_name,
      timezone: geoData.timezone?.name,
    });

    return geoData;
  } catch (error) {
    console.error('[GEOLOCATION] Error fetching location:', error);
    return null;
  }
}

/**
 * Get a formatted location string for display
 */
export function formatLocation(data: GeolocationData | null): string {
  if (!data) return 'Unknown location';

  const parts = [];
  if (data.city) parts.push(data.city);
  if (data.state_prov) parts.push(data.state_prov);
  if (data.country_name) parts.push(data.country_name);

  return parts.join(', ');
}

/**
 * Get timezone information string
 */
export function getTimezoneInfo(data: GeolocationData | null): string {
  if (!data || !data.timezone) return 'Unknown timezone';

  const tz = data.timezone;
  const offsetHours = tz.offset / 3600;
  const sign = offsetHours >= 0 ? '+' : '';

  return `${tz.name} (UTC${sign}${offsetHours})`;
}

/**
 * Clear cached location data (useful for testing or manual refresh)
 */
export function clearLocationCache(): void {
  cachedLocation = null;
  console.log('[GEOLOCATION] Cache cleared');
}
