"use client";

import {
  useEffect,
  useRef,
  useState,
} from "react";

import LocationInput from "./LocationInput.jsx";
import CrowdToleranceSelector from "./CrowdToleranceSelector.jsx";


export default function JourneyForm({
  onSubmit,
  loading,
  initialValues = null,
}) {
  // Selected locations.
  const [origin, setOrigin] =
    useState(null);

  const [
    destination,
    setDestination,
  ] = useState(null);

  // User-selected crowd tolerance.
  const [
    crowdThreshold,
    setCrowdThreshold,
  ] = useState(null);


  // References to LocationInput components.
  const originInputRef =
    useRef(null);

  const destinationInputRef =
    useRef(null);


  // Messages shown to the user.
  const [
    error,
    setError,
  ] = useState("");

  const [
    crowdThresholdError,
    setCrowdThresholdError,
  ] = useState("");

  const [
    locationNotice,
    setLocationNotice,
  ] = useState("");


  // --------------------------------------------------
  // Restore previous journey details when supplied
  // by RoutePlannerPage.
  // --------------------------------------------------

  useEffect(() => {
    if (!initialValues) {
      return;
    }

    setOrigin(
      initialValues.origin ||
      null
    );

    setDestination(
      initialValues.destination ||
      null
    );

    setCrowdThreshold(
      initialValues.crowdThreshold ??
      null
    );

    setError("");
    setCrowdThresholdError("");
    setLocationNotice("");
  }, [initialValues]);


  // --------------------------------------------------
  // Current location
  // --------------------------------------------------

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

    navigator.geolocation
      .getCurrentPosition(
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


  // --------------------------------------------------
  // Submit journey
  // --------------------------------------------------

  async function submit(event) {
    event.preventDefault();

    setError("");
    setCrowdThresholdError("");
    setLocationNotice("");


    // Require crowd preference.
    if (crowdThreshold === null) {
      setCrowdThresholdError(
        "Please select your crowd tolerance."
      );

      return;
    }


    const resolvedOrigin =
      origin ||
      (
        await originInputRef
          .current
          ?.resolveLocation()
      );


    const resolvedDestination =
      destination ||
      (
        await destinationInputRef
          .current
          ?.resolveLocation()
      );


    if (
      !resolvedOrigin ||
      !resolvedDestination
    ) {
      setError(
        "Please enter a valid starting location and destination."
      );

      return;
    }


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


    await onSubmit(
      {
        origin_latitude:
          resolvedOrigin.latitude,

        origin_longitude:
          resolvedOrigin.longitude,

        destination_latitude:
          resolvedDestination.latitude,

        destination_longitude:
          resolvedDestination.longitude,

        crowd_threshold:
          crowdThreshold,
      },

      {
        origin:
          resolvedOrigin,

        destination:
          resolvedDestination,

        crowdThreshold,
      }
    );
  }


  // --------------------------------------------------
  // Render
  // --------------------------------------------------

  return (
    <form
      className="journey-form"
      onSubmit={submit}
    >

      {/* STEP 1: Crowd tolerance */}

      <div className="journey-form__preference">
        <h2>
          Your crowd preference
        </h2>

        <p>
          Choose how much crowding you are
          comfortable with. We use this to
          recommend a calmer route.
        </p>

        <CrowdToleranceSelector
          value={crowdThreshold}
          onChange={(value) => {
            setCrowdThreshold(
              value
            );

            if (value !== null) {
              setCrowdThresholdError(
                ""
              );
            }
          }}
          disabled={loading}
          error={
            crowdThresholdError
          }
        />
      </div>


      {/* STEP 2: Journey locations */}

      <div className="journey-form__locations">

        <LocationInput
          ref={originInputRef}
          label="From"
          accessibleLabel="Origin"
          placeholder="Enter starting location"
          selectedPlace={origin}
          loading={loading}
          showCurrentLocation
          onSelectSuggestion={
            setOrigin
          }
          onClear={() =>
            setOrigin(null)
          }
          onUseCurrentLocation={
            useCurrentLocation
          }
        />


        <LocationInput
          ref={destinationInputRef}
          label="To"
          accessibleLabel="Destination"
          placeholder="Enter destination"
          selectedPlace={
            destination
          }
          loading={loading}
          onSelectSuggestion={
            setDestination
          }
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
            <span>
              Find routes
            </span>

            <span aria-hidden="true">
              →
            </span>
          </>
        )}
      </button>

    </form>
  );
}