export const PLACEHOLDER_MAPS_KEY = "PASTE_YOUR_GOOGLE_MAPS_BROWSER_KEY_HERE";
export const MISSING_MAPS_KEY_MESSAGE = "Map preview is unavailable until `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY` is configured.";
export const MELBOURNE_CBD_CENTER = { lat: -37.8136, lng: 144.9631 };

let mapsLoaderPromise;

export function hasConfiguredMapsKey(key) {
  return Boolean(key && key.trim() && key !== PLACEHOLDER_MAPS_KEY);
}

export function loadGoogleMaps(apiKey) {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return Promise.reject(new Error("Google Maps is only available in the browser."));
  }
  if (window.google?.maps) return Promise.resolve(window.google.maps);
  if (mapsLoaderPromise) return mapsLoaderPromise;

  mapsLoaderPromise = new Promise((resolve, reject) => {
    const existingScript = document.querySelector("script[data-escape-google-maps]");
    const script = existingScript || document.createElement("script");
    const handleLoad = () => {
      if (window.google?.maps) resolve(window.google.maps);
      else reject(new Error("Google Maps script loaded without the maps API."));
    };
    const handleError = () => reject(new Error("Google Maps could not load."));
    script.addEventListener("load", handleLoad, { once: true });
    script.addEventListener("error", handleError, { once: true });
    if (!existingScript) {
      script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&libraries=places`;
      script.async = true;
      script.defer = true;
      script.dataset.escapeGoogleMaps = "true";
      document.head.appendChild(script);
    }
  }).catch((error) => {
    mapsLoaderPromise = undefined;
    throw error;
  });
  return mapsLoaderPromise;
}
