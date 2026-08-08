"use client";

import { useRef, useState } from "react";
import LocationInput from "./LocationInput.jsx";

export default function JourneyForm({
  onSubmit,
  loading,
}) {
  // Selected locations.
  const [origin, setOrigin] = useState(null);
  const [destination, setDestination] =
    useState(null);

  // References to LocationInput components.
  const originInputRef = useRef(null);
  const destinationInputRef = useRef(null);

  // Messages shown to the user.
  const [error, setError] = useState("");
  const [locationNotice, setLocationNotice] =
    useState("");

  /**
   * Gets the user's current browser location
   * and uses it as the journey origin.
   */
  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setLocationNotice(
        "Current location is unavailable."
      );
      return;
    }

    setLocationNotice(
      "Finding your location..."
    );

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setOrigin({
          id: "current",
          label: "Current location",
          formattedAddress:
            "Current location",
          latitude:
            position.coords.latitude,
          longitude:
            position.coords.longitude,
        });

        setLocationNotice(
          "Current location selected."
        );
      },
      () => {
        setLocationNotice(
          "Unable to access your location. Enter it manually."
        );
      }
    );
  }

  /**
   * Resolves typed place names automatically,
   * validates them, then sends coordinates
   * to RoutePlannerPage.
   */
  async function submit(event) {
    event.preventDefault();

    setError("");
    setLocationNotice("");

    // Use already-selected locations when available.
    // Otherwise automatically search the typed text.
    const resolvedOrigin =
      origin ||
      (await originInputRef.current?.resolveLocation());

    const resolvedDestination =
      destination ||
      (await destinationInputRef.current?.resolveLocation());

    // Missing or unresolved location.
    if (
      !resolvedOrigin ||
      !resolvedDestination
    ) {
      setError(
        "Please enter a valid starting location and destination."
      );
      return;
    }

    // Prevent the same place being used twice.
    if (
      resolvedOrigin.latitude ===
        resolvedDestination.latitude &&
      resolvedOrigin.longitude ===
        resolvedDestination.longitude
    ) {
      setError(
        "Origin and destination cannot be the same."
      );
      return;
    }

    // Send only coordinates to the route-planning backend.
    await onSubmit({
      origin_latitude:
        resolvedOrigin.latitude,
      origin_longitude:
        resolvedOrigin.longitude,
      destination_latitude:
        resolvedDestination.latitude,
      destination_longitude:
        resolvedDestination.longitude,
    });
  }

  return (
    <form
      className="journey-form"
      onSubmit={submit}
    >
      <div className="field-grid">
        {/* Starting location */}
        <LocationInput
          ref={originInputRef}
          label="From"
          accessibleLabel="Origin"
          placeholder="Enter starting location"
          selectedPlace={origin}
          loading={loading}
          showCurrentLocation
          onSelectSuggestion={setOrigin}
          onClear={() => setOrigin(null)}
          onUseCurrentLocation={
            useCurrentLocation
          }
        />

        {/* Destination */}
        <LocationInput
          ref={destinationInputRef}
          label="To"
          accessibleLabel="Destination"
          placeholder="Enter destination"
          selectedPlace={destination}
          loading={loading}
          onSelectSuggestion={setDestination}
          onClear={() =>
            setDestination(null)
          }
        />
      </div>

      {locationNotice && (
        <p
          className="field-notice"
          role="status"
        >
          {locationNotice}
        </p>
      )}

      {error && (
        <p
          className="field-error"
          role="alert"
        >
          {error}
        </p>
      )}

      <button
        className="primary-button journey-form__submit"
        type="submit"
        disabled={loading}
      >
        {loading ? (
          "Finding routes…"
        ) : (
          <>
            <span>Find routes</span>
            <span aria-hidden="true">
              →
            </span>
          </>
        )}
      </button>
    </form>
  );
}