"use client";

import {
  forwardRef,
  useEffect,
  useId,
  useImperativeHandle,
  useState,
} from "react";
import AppIcon from "./app/AppIcon.jsx";

// Approximate Melbourne CBD bounds: Flagstaff to Parliament and the Yarra.
const MELBOURNE_CBD_VIEWBOX = "144.9510,-37.8060,144.9745,-37.8255";
const SEARCH_DELAY_MS = 550;

const LocationInput = forwardRef(function LocationInput(
  {
    label,
    accessibleLabel,
    placeholder,
    selectedPlace,
    loading,
    error,
    showCurrentLocation = false,
    onSelectSuggestion,
    onClear,
    onUseCurrentLocation,
  },
  ref
) {
  const id = useId();

  // Text visible in the input.
  const [value, setValue] = useState("");

  // Places returned from OpenStreetMap/Nominatim.
  const [suggestions, setSuggestions] = useState([]);

  // Controls the suggestions dropdown.
  const [open, setOpen] = useState(false);

  // Search status message.
  const [notice, setNotice] = useState("");

  // Prevent repeated searches.
  const [searching, setSearching] = useState(false);

  function placeArea(item) {
    const address = item.address || {};
    const area = address.suburb || address.city_district || address.neighbourhood
      || address.city || address.town || address.village;
    return [area, address.postcode].filter(Boolean).join(" · ");
  }

  /**
   * Keep the input synchronized with the selected place.
   */
  useEffect(() => {
    if (selectedPlace) {
      setValue(selectedPlace.label || "");
    }
  }, [selectedPlace]);

  /**
   * Converts one Nominatim result into the format
   * expected by JourneyForm.
   */
  function convertPlace(item, fallbackLabel = "Unknown location") {
    return {
      id: String(item.place_id),

      label:
        item.namedetails?.name ||
        item.name ||
        item.display_name?.split(",")[0] ||
        fallbackLabel,

      formattedAddress: item.display_name,
      areaLabel: placeArea(item),

      latitude: Number(item.lat),
      longitude: Number(item.lon),
    };
  }

  async function fetchLocations(query, limit, signal) {
    const params = new globalThis.URLSearchParams({
      q: `${query}, Victoria, Australia`,
      format: "jsonv2",
      addressdetails: "1",
      namedetails: "1",
      limit: String(limit),
      countrycodes: "au",
      "accept-language": "en",
      viewbox: MELBOURNE_CBD_VIEWBOX,
      bounded: "1",
    });

    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?${params.toString()}`,
      { signal },
    );

    if (!response.ok) {
      throw new Error(`Location search failed with status ${response.status}`);
    }

    const data = await response.json();
    return data
      .map((item) => convertPlace(item))
      .filter((place) => Number.isFinite(place.latitude) && Number.isFinite(place.longitude));
  }

  useEffect(() => {
    const query = value.trim();
    if (selectedPlace || query.length < 3) return undefined;

    const controller = new globalThis.AbortController();
    const timer = globalThis.setTimeout(async () => {
      try {
        setSearching(true);
        setNotice("Searching Melbourne CBD locations...");
        const places = await fetchLocations(query, 5, controller.signal);
        setSuggestions(places);
        setOpen(places.length > 0);
        setNotice(places.length ? "" : "No locations found within Melbourne CBD.");
      } catch (searchError) {
        if (searchError.name !== "AbortError") {
          setSuggestions([]);
          setOpen(false);
          setNotice("Unable to search locations right now.");
        }
      } finally {
        if (!controller.signal.aborted) setSearching(false);
      }
    }, SEARCH_DELAY_MS);

    return () => {
      globalThis.clearTimeout(timer);
      controller.abort();
    };
  }, [selectedPlace, value]);

  /**
   * Searches OpenStreetMap/Nominatim and shows
   * multiple location suggestions.
   */
  async function searchLocations() {
    const query = value.trim();

    if (query.length < 3) {
      setNotice("Enter at least 3 characters.");
      setSuggestions([]);
      setOpen(false);
      return;
    }

    try {
      setSearching(true);
      setNotice("Searching...");
      setSuggestions([]);
      setOpen(false);

      const places = await fetchLocations(query, 5);

      setSuggestions(places);

      if (places.length > 0) {
        setOpen(true);
        setNotice("");
      } else {
        setOpen(false);
        setNotice("No locations found.");
      }
    } catch (searchError) {
      console.error(
        "OSM location search error:",
        searchError
      );

      setSuggestions([]);
      setOpen(false);
      setNotice(
        "Unable to search locations right now."
      );
    } finally {
      setSearching(false);
    }
  }

  /**
   * Automatically resolves the typed text into
   * one location.
   *
   * JourneyForm uses this when Find routes is clicked.
   */
  async function resolveLocation() {
    // Already selected, so no search is needed.
    if (selectedPlace) {
      return selectedPlace;
    }

    const query = value.trim();

    // Nothing entered.
    if (!query) {
      return null;
    }

    if (query.length < 3) {
      setNotice("Enter at least 3 characters.");
      return null;
    }

    try {
      setSearching(true);
      setNotice("Finding location...");

      const places = await fetchLocations(query, 1);

      if (!places.length) {
        setNotice(`No Melbourne CBD location found for "${query}".`);
        return null;
      }

      const place = places[0];

      if (
        !Number.isFinite(place.latitude) ||
        !Number.isFinite(place.longitude)
      ) {
        setNotice("Invalid location coordinates.");
        return null;
      }

      // Store the resolved location in JourneyForm.
      onSelectSuggestion?.(place);

      setValue(place.label);
      setSuggestions([]);
      setOpen(false);
      setNotice("");

      return place;
    } catch (searchError) {
      console.error(
        "OSM automatic location search error:",
        searchError
      );

      setNotice(
        "Unable to find this location right now."
      );

      return null;
    } finally {
      setSearching(false);
    }
  }

  /**
   * Exposes resolveLocation() to JourneyForm.
   */
  useImperativeHandle(ref, () => ({
    resolveLocation,
  }));

  /**
   * Update input while typing.
   */
  function handleChange(event) {
    const newValue = event.target.value;

    setValue(newValue);
    setSuggestions([]);
    setOpen(false);
    setNotice("");

    if (selectedPlace) {
      onClear?.();
    }
  }

  /**
   * Select a location from the suggestion list.
   */
  function handleSelect(place) {
    setValue(place.label);

    onSelectSuggestion?.(place);

    setSuggestions([]);
    setOpen(false);
    setNotice("");
  }

  /**
   * Clear the location.
   */
  function handleClear() {
    setValue("");
    setSuggestions([]);
    setOpen(false);
    setNotice("");

    onClear?.();
  }

  /**
   * Enter still allows manual searching.
   */
  function handleKeyDown(event) {
    if (event.key === "Enter") {
      event.preventDefault();

      if (
        !searching &&
        value.trim().length >= 3
      ) {
        searchLocations();
      }
    }
  }

  return (
    <div className="location-input">
      <label htmlFor={id}>
        {label}
      </label>

      <div className="location-input__control">
        <AppIcon className="location-input__pin" name="pin" size={20} />
        <input
          id={id}
          aria-label={accessibleLabel}
          aria-invalid={Boolean(error)}
          value={value}
          placeholder={placeholder}
          disabled={loading}
          autoComplete="off"
          onChange={handleChange}
          onKeyDown={handleKeyDown}
        />

        {value && (
          <button
            type="button"
            className="location-input__clear"
            onClick={handleClear}
            aria-label={`Clear ${(
              accessibleLabel || label
            ).toLowerCase()}`}
          >
            <AppIcon name="close" size={18} />
          </button>
        )}
      </div>

      {showCurrentLocation && (
        <button
          type="button"
          className="current-location-button"
          onClick={onUseCurrentLocation}
          disabled={loading}
        >
          <AppIcon name="locate" size={19} />
          <span>Use current location</span>
        </button>
      )}

      {open && suggestions.length > 0 && (
        <ul className="place-suggestions" aria-label={`${label} suggestions`}>
          {suggestions.map((place) => (
            <li key={place.id}>
              <button
                type="button"
                onClick={() =>
                  handleSelect(place)
                }
              >
                <strong>
                  {place.label}
                </strong>

                <small>
                  {place.areaLabel || place.formattedAddress}
                </small>
              </button>
            </li>
          ))}
        </ul>
      )}

      {selectedPlace && (
        <div className="location-input__selected" role="status">
          <AppIcon name="check" size={16} />
          <span><strong>{selectedPlace.label} selected</strong><small>{selectedPlace.formattedAddress}</small></span>
        </div>
      )}

      {notice && (
        <small
          className="field-notice"
          role="status"
        >
          {notice}
        </small>
      )}

      {error && (
        <strong
          className="field-error"
          role="alert"
        >
          {error}
        </strong>
      )}
    </div>
  );
});

export default LocationInput;
