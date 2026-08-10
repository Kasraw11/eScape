"use client";

import {
  useEffect,
  useState,
} from "react";

import { useRouter } from "next/navigation";

import {
  planRoute,
} from "../services/api.js";

import JourneyForm from "./JourneyForm.jsx";
import LoadingState from "./LoadingState.jsx";
import RouteList from "./RouteList.jsx";
import GoogleMapPreview from "./GoogleMapPreview.jsx";


export default function RoutePlannerPage() {
  const router = useRouter();


  // --------------------------------------------------
  // State
  // --------------------------------------------------

  // Routes returned by backend.
  const [
    routes,
    setRoutes,
  ] = useState([]);


  // Currently selected route.
  const [
    selectedRouteIdentifier,
    setSelectedRouteIdentifier,
  ] = useState(null);


  // Origin, destination and
  // selected crowd tolerance.
  const [
    journeyDetails,
    setJourneyDetails,
  ] = useState(null);


  // Calmer alternative passed
  // from Current Trip page.
  const [
    pendingAlternative,
    setPendingAlternative,
  ] = useState(null);


  // True while backend is planning.
  const [
    loading,
    setLoading,
  ] = useState(false);


  // Route-planning error.
  const [
    error,
    setError,
  ] = useState("");


  // --------------------------------------------------
  // Restore previous route plan
  // and calmer alternative.
  // --------------------------------------------------

useEffect(() => {
  try {
    // --------------------------------------------------
    // Only restore a previous plan when Current Trip
    // explicitly asks us to.
    // --------------------------------------------------

    const shouldRestore =
      globalThis.localStorage?.getItem(
        "escape-restore-route-plan"
      ) === "true";


    // Normal visit / refresh of /plan:
    // start with a clean planner.
    if (!shouldRestore) {
      return;
    }


    // --------------------------------------------------
    // 1. Check for a calmer alternative.
    // --------------------------------------------------

    const storedAlternative =
      globalThis.localStorage?.getItem(
        "escape-alternative-route"
      );

    const alternative =
      storedAlternative
        ? JSON.parse(
            storedAlternative
          )
        : null;


    if (alternative) {
      setPendingAlternative(
        alternative
      );
    }


    // --------------------------------------------------
    // 2. Restore previous plan.
    // --------------------------------------------------

    const storedPlan =
      globalThis.localStorage?.getItem(
        "escape-last-route-plan"
      );


    if (storedPlan) {
      const parsedPlan =
        JSON.parse(
          storedPlan
        );

    let restoredRoutes =
      parsedPlan.routes || [];

    if (alternative?.route_identifier) {
      restoredRoutes =
        restoredRoutes.map((route) => {
          if (
            route.route_identifier !==
            alternative.route_identifier
          ) {
            return route;
          }

          return {
            ...route,

            sensory_score:
              alternative.sensory_score ??
              route.sensory_score,

            sensory_indicator:
              alternative.sensory_indicator ??
              route.sensory_indicator,

            threshold_exceeded:
              alternative.threshold_exceeded ??
              route.threshold_exceeded,

            qualifies_preference:
              alternative.qualifies_preference ??
              route.qualifies_preference,

            data_freshness:
              alternative.data_freshness ??
              route.data_freshness,

            sensor_coverage_ratio:
              alternative.sensor_coverage_ratio ??
              route.sensor_coverage_ratio,

            estimated_travel_minutes:
              alternative.estimated_travel_minutes ??
              route.estimated_travel_minutes,
          };
        });
}


      // Restore route cards and map.
      setRoutes(
        restoredRoutes
      );


      // Restore:
      // - origin
      // - destination
      // - crowd tolerance
      setJourneyDetails(
        parsedPlan.journeyDetails ||
        null
      );


      // ------------------------------------------------
      // Prefer calmer alternative if one was supplied.
      // ------------------------------------------------

      const alternativeIdentifier =
        alternative
          ?.route_identifier;


      const alternativeExists =
        alternativeIdentifier &&
        restoredRoutes.some(
          (route) =>
            route.route_identifier ===
            alternativeIdentifier
        );


      if (alternativeExists) {
        setSelectedRouteIdentifier(
          alternativeIdentifier
        );

        setPendingAlternative(
          null
        );
      }

      // ------------------------------------------------
      // Otherwise restore recommended route.
      // ------------------------------------------------

      else if (
        parsedPlan
          .recommendedRouteIdentifier
      ) {
        setSelectedRouteIdentifier(
          parsedPlan
            .recommendedRouteIdentifier
        );
      }

      // ------------------------------------------------
      // Final fallback.
      // ------------------------------------------------

      else if (
        restoredRoutes.length > 0
      ) {
        setSelectedRouteIdentifier(
          restoredRoutes[0]
            .route_identifier
        );
      }
    }


    // --------------------------------------------------
    // 3. These are one-time navigation flags.
    // --------------------------------------------------

    globalThis.localStorage?.removeItem(
      "escape-restore-route-plan"
    );


    if (storedAlternative) {
      globalThis.localStorage?.removeItem(
        "escape-alternative-route"
      );
    }

  } catch (storageError) {
    console.error(
      "Unable to restore route plan:",
      storageError
    );
  }
}, []);


  // --------------------------------------------------
  // Submit new journey
  // --------------------------------------------------

  async function handleSubmit(
    payload,
    details
  ) {
    setLoading(
      true
    );

    setError(
      ""
    );


    // Clear previous search.
    setRoutes(
      []
    );

    setSelectedRouteIdentifier(
      null
    );


    // Keep resolved frontend journey info.
    setJourneyDetails(
      details
    );


    try {
      // ------------------------------------------
      // Request routes from backend.
      // ------------------------------------------

      const response =
        await planRoute(
          payload
        );


      const returnedRoutes =
        response.routes || [];


      setRoutes(
        returnedRoutes
      );


      // ------------------------------------------
      // Save full route plan.
      //
      // This lets Current Trip return to /plan
      // without forcing another search.
      // ------------------------------------------

      try {
        globalThis.localStorage?.setItem(
          "escape-last-route-plan",
          JSON.stringify({
            routes:
              returnedRoutes,

            journeyDetails:
              details,

            recommendedRouteIdentifier:
              response
                .recommended_route_identifier ||
              null,
          })
        );
      } catch (storageError) {
        console.error(
          "Unable to save route plan:",
          storageError
        );
      }


      // ------------------------------------------
      // If a calmer alternative is waiting,
      // prefer it.
      // ------------------------------------------

      const alternativeIdentifier =
        pendingAlternative
          ?.route_identifier;


      const alternativeExists =
        alternativeIdentifier &&
        returnedRoutes.some(
          (route) =>
            route.route_identifier ===
            alternativeIdentifier
        );


      if (alternativeExists) {
        setSelectedRouteIdentifier(
          alternativeIdentifier
        );

        setPendingAlternative(
          null
        );
      }

      // ------------------------------------------
      // Otherwise use backend recommendation.
      // ------------------------------------------

      else if (
        response
          .recommended_route_identifier
      ) {
        setSelectedRouteIdentifier(
          response
            .recommended_route_identifier
        );
      }

      // ------------------------------------------
      // Final fallback.
      // ------------------------------------------

      else if (
        returnedRoutes.length > 0
      ) {
        setSelectedRouteIdentifier(
          returnedRoutes[0]
            .route_identifier
        );
      }

    } catch (requestError) {
      console.error(
        "Route planning error:",
        requestError
      );


      setError(
        requestError.message ||
          "Unable to generate routes right now."
      );

    } finally {
      setLoading(
        false
      );
    }
  }


  // --------------------------------------------------
  // Select route manually
  // --------------------------------------------------

  function selectRoute(
    identifier
  ) {
    setSelectedRouteIdentifier(
      identifier
    );
  }


  // --------------------------------------------------
  // Start selected journey
  // --------------------------------------------------

  function startJourney(
    routeIdentifier
  ) {
    const selectedRoute =
      routes.find(
        (route) =>
          route.route_identifier ===
          routeIdentifier
      );


    if (!selectedRoute) {
      setError(
        "Unable to start this route."
      );

      return;
    }


    if (!journeyDetails) {
      setError(
        "Journey details are unavailable. Please search for the route again."
      );

      return;
    }


    const activeJourney = {
      startedAt:
        new Date().toISOString(),

      origin:
        journeyDetails.origin,

      destination:
        journeyDetails.destination,

      crowdThreshold:
        journeyDetails.crowdThreshold,

      route:
        selectedRoute,
    };


    try {
      globalThis.localStorage?.setItem(
        "escape-active-journey",
        JSON.stringify(
          activeJourney
        )
      );


      router.push(
        "/current-trip"
      );

    } catch (storageError) {
      console.error(
        "Unable to save active journey:",
        storageError
      );


      setError(
        "Unable to start the journey."
      );
    }
  }


  // --------------------------------------------------
  // Render
  // --------------------------------------------------

  return (
    <div>

      {/* ------------------------------------------
          Status messages
      ------------------------------------------- */}

      <div
        className="plan-status"
        aria-live="polite"
      >
        {error && (
          <div
            className="error-state"
            role="alert"
          >
            <strong>
              We couldn't find routes.
            </strong>

            <p>
              {error}
            </p>
          </div>
        )}


        {loading && (
          <LoadingState />
        )}
      </div>


      {/* ------------------------------------------
          Planning workspace
      ------------------------------------------- */}

      <div
        className="plan-workspace"
      >

        {/* ----------------------------------------
            Journey form
        ----------------------------------------- */}

        <section
          className="journey-panel glass-panel"
          aria-labelledby="journey-heading"
        >
          <div
            className="journey-panel__heading"
          >
            <h1
              id="journey-heading"
            >
              Plan your journey
            </h1>

            <p>
              Find a calmer way to reach
              your destination.
            </p>
          </div>


          <JourneyForm
            onSubmit={handleSubmit}
            loading={loading}
            initialValues={journeyDetails}
          />
        </section>


        {/* ----------------------------------------
            Map + route results
        ----------------------------------------- */}

        <div
          className="route-visual-column"
        >

          <GoogleMapPreview
            routes={
              loading
                ? []
                : routes
            }
            selectedRouteIdentifier={
              selectedRouteIdentifier
            }
            onSelectRoute={
              selectRoute
            }
          />


          <RouteList
            routes={
              loading
                ? []
                : routes
            }
            selectedRouteIdentifier={
              selectedRouteIdentifier
            }
            onSelectRoute={
              selectRoute
            }
            onStartJourney={
              startJourney
            }
          />

        </div>
      </div>
    </div>
  );
}