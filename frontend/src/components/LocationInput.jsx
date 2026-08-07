"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { hasConfiguredMapsKey, loadGoogleMaps } from "../services/googleMapsLoader.js";

export default function LocationInput({ label, accessibleLabel, value, placeholder, suggestions = [], selectedPlace, loading, error, showCurrentLocation = false, onChange, onSelectSuggestion, onClear, onUseCurrentLocation }) {
  const id = useId();
  const listId = `${id}-suggestions`;
  const [remoteSuggestions, setRemoteSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [notice, setNotice] = useState("");
  const requestId = useRef(0);
  const mapsKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
  const configured = hasConfiguredMapsKey(mapsKey);

  const localSuggestions = useMemo(() => {
    const query = value.trim().toLowerCase();
    if (query.length < 2) return [];
    return suggestions.filter((item) => item.label.toLowerCase().includes(query)).slice(0, 5);
  }, [suggestions, value]);
  const visibleSuggestions = remoteSuggestions.length ? remoteSuggestions : localSuggestions;

  useEffect(() => {
    const query = value.trim();
    if (query.length < 3 || selectedPlace) { setRemoteSuggestions([]); return undefined; }
    if (!configured) { setNotice("Google location suggestions are unavailable. You can still type or choose a known Melbourne CBD location."); return undefined; }
    const currentRequest = ++requestId.current;
    const timer = window.setTimeout(() => {
      loadGoogleMaps(mapsKey).then((maps) => {
        const service = new maps.places.AutocompleteService();
        service.getPlacePredictions({ input: query, componentRestrictions: { country: "au" }, locationBias: { center: { lat: -37.8136, lng: 144.9631 }, radius: 8000 } }, (predictions, status) => {
          if (currentRequest !== requestId.current) return;
          if (status === maps.places.PlacesServiceStatus.OK) {
            setRemoteSuggestions((predictions || []).slice(0, 5).map((prediction) => ({ id: prediction.place_id, label: prediction.description, placeId: prediction.place_id })));
            setNotice(""); setOpen(true);
          } else setRemoteSuggestions([]);
        });
      }).catch(() => setNotice("Google location suggestions could not load. Manual typing remains available."));
    }, 300);
    return () => window.clearTimeout(timer);
  }, [configured, mapsKey, selectedPlace, value]);

  function select(item) {
    if (item.latitude != null) { onSelectSuggestion(item); setOpen(false); setActiveIndex(-1); return; }
    loadGoogleMaps(mapsKey).then((maps) => {
      const node = document.createElement("div");
      new maps.places.PlacesService(node).getDetails({ placeId: item.placeId, fields: ["place_id", "name", "formatted_address", "geometry"] }, (place, status) => {
        if (status !== maps.places.PlacesServiceStatus.OK || !place?.geometry?.location) { setNotice("That location could not be resolved. Try another suggestion."); return; }
        onSelectSuggestion({ id: place.place_id, placeId: place.place_id, label: place.name || item.label, formattedAddress: place.formatted_address || item.label, latitude: place.geometry.location.lat(), longitude: place.geometry.location.lng() });
        setOpen(false); setActiveIndex(-1);
      });
    }).catch(() => setNotice("That location could not be resolved. Manual typing remains available."));
  }

  return <div className="location-input form-field"><label htmlFor={id}>{label}</label><div className="location-input__control"><input id={id} aria-label={accessibleLabel} role="combobox" aria-autocomplete="list" aria-expanded={open && visibleSuggestions.length > 0} aria-controls={listId} aria-activedescendant={activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined} aria-invalid={Boolean(error)} aria-describedby={[error ? `${id}-error` : "", notice ? `${id}-notice` : ""].filter(Boolean).join(" ") || undefined} value={value} placeholder={placeholder} disabled={loading} autoComplete="off" onChange={(event) => { onChange(event.target.value); setOpen(true); setActiveIndex(-1); }} onFocus={() => visibleSuggestions.length && setOpen(true)} onKeyDown={(event) => {
    if (event.key === "ArrowDown" && visibleSuggestions.length) { event.preventDefault(); setOpen(true); setActiveIndex((current) => Math.min(current + 1, visibleSuggestions.length - 1)); }
    if (event.key === "ArrowUp" && visibleSuggestions.length) { event.preventDefault(); setActiveIndex((current) => Math.max(current - 1, 0)); }
    if (event.key === "Enter" && activeIndex >= 0) { event.preventDefault(); select(visibleSuggestions[activeIndex]); }
    if (event.key === "Escape") { setOpen(false); setActiveIndex(-1); }
  }} />{value ? <button type="button" className="location-input__clear" onClick={onClear} aria-label={`Clear ${(accessibleLabel || label).toLowerCase()}`}>×</button> : null}</div>
    {showCurrentLocation ? <button type="button" className="text-button" onClick={onUseCurrentLocation}>Use current location</button> : null}
    {open && visibleSuggestions.length ? <ul className="place-suggestions" id={listId} role="listbox" aria-label={`${label} suggestions`}>{visibleSuggestions.map((item, index) => <li id={`${listId}-${index}`} key={item.id || item.placeId || item.label} role="option" aria-selected={index === activeIndex} onMouseDown={(event) => event.preventDefault()} onClick={() => select(item)}>{item.label}</li>)}</ul> : null}
    <span className="sr-only" aria-live="polite">{open ? `${visibleSuggestions.length} suggestions available.` : ""}</span>{error ? <strong className="field-error" id={`${id}-error`}>{error}</strong> : null}{notice ? <small className="field-notice" id={`${id}-notice`}>{notice}</small> : null}</div>;
}
