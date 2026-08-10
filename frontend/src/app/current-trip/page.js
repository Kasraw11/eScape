"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import { useRouter } from "next/navigation";

import CurrentTrip from "../../components/CurrentTrip.jsx";
import useCongestionPolling from "../../hooks/useCongestionPolling.js";

import {
  getCalmerAlternative,
} from "../../services/api.js";


export default function CurrentTripPage() {
  const router = useRouter();


  // --------------------------------------------------
  // State
  // --------------------------------------------------

  const [
    journey,
    setJourney,
  ] = useState(null);


  const [
    ready,
    setReady,
  ] = useState(false);


  const [
    dismissedAlertIds,
    setDismissedAlertIds,
  ] = useState(
    new Set()
  );


  const [
    selectedAlertId,
    setSelectedAlertId,
  ] = useState(null);


  const [
    alternatives,
    setAlternatives,
  ] = useState([]);


  const [
    alternativeError,
    setAlternativeError,
  ] = useState("");


  // --------------------------------------------------
  // Load active journey
  // --------------------------------------------------

  useEffect(() => {
    try {
      const stored =
        globalThis.localStorage?.getItem(
          "escape-active-journey"
        );

      if (stored) {
        setJourney(
          JSON.parse(
            stored
          )
        );
      }

    } catch (error) {
      console.error(
        "Unable to load active journey:",
        error
      );

    } finally {
      setReady(
        true
      );
    }
  }, []);


  // --------------------------------------------------
  // Active route identifier
  // --------------------------------------------------

  const routeId =
    journey
      ?.route
      ?.route_identifier ||
    null;


  // --------------------------------------------------
  // Live congestion polling
  // --------------------------------------------------

  const {
    congestion,
    updating,
    refreshError,
    notification,
    dismissNotification,
    lastCheckedAt,
  } = useCongestionPolling(
    routeId
  );


  // --------------------------------------------------
  // Check for calmer alternative
  // --------------------------------------------------

  useEffect(() => {
    if (!routeId) {
      setAlternatives(
        []
      );

      return;
    }


    const controller =
      new AbortController();


    async function loadAlternative() {
      try {
        setAlternativeError(
          ""
        );


        const response =
          await getCalmerAlternative(
            routeId,
            {
              signal:
                controller.signal,
            }
          );


        if (
          response.alternative_available &&
          response.alternative
        ) {
          setAlternatives(
            [
              response.alternative,
            ]
          );
        } else {
          setAlternatives(
            []
          );
        }

      } catch (error) {
        if (
          error?.name ===
          "AbortError"
        ) {
          return;
        }


        console.error(
          "Unable to load calmer alternative:",
          error
        );


        setAlternativeError(
          error.message ||
            "Unable to check alternative routes."
        );


        setAlternatives(
          []
        );
      }
    }


    loadAlternative();


    return () => {
      controller.abort();
    };

  }, [
    routeId,
    congestion?.sensory_score,
    congestion?.threshold_exceeded,
  ]);


  // --------------------------------------------------
  // Build live alert
  // --------------------------------------------------

  const alerts =
    useMemo(() => {
      if (!notification) {
        return [];
      }


      const alertId =
        notification.change_key ||
        `${routeId}-congestion`;


      if (
        dismissedAlertIds.has(
          alertId
        )
      ) {
        return [];
      }


      return [
        {
          ...notification,

          id:
            alertId,

          type:
            "live",

          severity:
            notification
              .congestion_level ||
            congestion
              ?.sensory_indicator ||
            "Unavailable",

          title:
            notification
              .threshold_exceeded
              ? "Crowd level exceeds your preference"
              : "Route congestion update",

          message:
            notification.message ||
            (
              notification
                .threshold_exceeded
                ? "Crowding on this route is above your selected comfort level."
                : "Crowding on this route has changed."
            ),

          timestamp:
            notification.updated_at ||
            congestion?.updated_at,

          routeImpact:
            notification
              .threshold_exceeded
              ? "This section may be less comfortable based on your crowd preference."
              : "This route is still within your selected crowd preference.",

          threshold_exceeded:
            notification
              .threshold_exceeded,
        },
      ];
    }, [
      notification,
      congestion,
      dismissedAlertIds,
      routeId,
    ]);


  // --------------------------------------------------
  // Dismiss alert
  // --------------------------------------------------

  function dismissAlert(
    alertId
  ) {
    setDismissedAlertIds(
      (current) => {
        const next =
          new Set(
            current
          );

        next.add(
          alertId
        );

        return next;
      }
    );


    dismissNotification();
  }


  // --------------------------------------------------
  // End journey
  // --------------------------------------------------

  function endJourney() {
    try {
      globalThis.localStorage
        ?.removeItem(
          "escape-active-journey"
        );

      globalThis.localStorage
        ?.removeItem(
          "escape-restore-route-plan"
        );

      globalThis.localStorage
        ?.removeItem(
          "escape-alternative-route"
        );

    } catch {
      // Ignore storage cleanup errors.
    }


    setJourney(
      null
    );


    router.push(
      "/plan"
    );
  }


  // --------------------------------------------------
  // Review previous route options
  // --------------------------------------------------

  function reviewRoutes() {
    try {
      // Tell /plan that this is an intentional
      // return to the previous route plan.
      globalThis.localStorage?.setItem(
        "escape-restore-route-plan",
        "true"
      );

      // Make sure Review Route Options does NOT
      // accidentally behave like View Calmer Route.
      globalThis.localStorage?.removeItem(
        "escape-alternative-route"
      );

    } catch {
      // Continue even if storage fails.
    }


    router.push(
      "/plan"
    );
  }


  // --------------------------------------------------
  // View calmer alternative
  // --------------------------------------------------

  function viewAlternative() {
    // There is nothing to open if no calmer
    // alternative is currently available.
    if (
      alternatives.length === 0
    ) {
      return;
    }


    const alternative =
      alternatives[0];


    try {
      // Save the live alternative information.
      globalThis.localStorage?.setItem(
        "escape-alternative-route",
        JSON.stringify(
          alternative
        )
      );


      // Tell /plan to restore the previous
      // journey and route cards.
      globalThis.localStorage?.setItem(
        "escape-restore-route-plan",
        "true"
      );

    } catch {
      // Continue even if storage fails.
    }


    router.push(
      "/plan"
    );
  }


  // --------------------------------------------------
  // Loading
  // --------------------------------------------------

  if (!ready) {
    return (
      <p>
        Loading current journey…
      </p>
    );
  }


  // --------------------------------------------------
  // Render
  // --------------------------------------------------

  return (
    <>
      {alternativeError && (
        <p
          className="field-error"
          role="alert"
        >
          {alternativeError}
        </p>
      )}


      <CurrentTrip
        journey={
          journey
        }

        congestion={
          congestion
        }

        lastCheckedAt={
          lastCheckedAt
        }

        updating={
          updating
        }

        refreshError={
          refreshError
        }

        alerts={
          alerts
        }

        selectedAlertId={
          selectedAlertId
        }

        alternatives={
          alternatives
        }

        onViewAlternative={
          viewAlternative
        }

        onDismissAlert={
          dismissAlert
        }

        onSelectAlert={
          setSelectedAlertId
        }

        onPlan={
          reviewRoutes
        }

        onEnd={
          endJourney
        }
      />
    </>
  );
}