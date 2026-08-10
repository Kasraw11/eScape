"use client";

import {
  forwardRef,
  useEffect,
  useId,
  useImperativeHandle,
  useState,
} from "react";


const MELBOURNE_CBD_LATITUDE_RANGE = [
  -37.8255,
  -37.8050,
];

const MELBOURNE_CBD_LONGITUDE_RANGE = [
  144.9440,
  144.9765,
];


const LocationInput = forwardRef(
  function LocationInput(
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
    const [
      value,
      setValue,
    ] = useState("");

    // Places returned from OpenStreetMap/Nominatim.
    const [
      suggestions,
      setSuggestions,
    ] = useState([]);

    // Controls the suggestions dropdown.
    const [
      open,
      setOpen,
    ] = useState(false);

    // Search status message.
    const [
      notice,
      setNotice,
    ] = useState("");

    // Prevent repeated searches.
    const [
      searching,
      setSearching,
    ] = useState(false);


    // --------------------------------------------------
    // Keep input synchronized with selected place
    // --------------------------------------------------

    useEffect(() => {
      if (selectedPlace) {
        setValue(
          selectedPlace.label || ""
        );
      }
    }, [selectedPlace]);


    // --------------------------------------------------
    // Convert Nominatim result
    // --------------------------------------------------

    function convertPlace(
      item,
      fallbackLabel = "Unknown location"
    ) {
      return {
        id:
          String(
            item.place_id
          ),

        label:
          item.namedetails?.name ||
          item.name ||
          item.display_name
            ?.split(",")[0] ||
          fallbackLabel,

        formattedAddress:
          item.display_name,

        latitude:
          Number(
            item.lat
          ),

        longitude:
          Number(
            item.lon
          ),
      };
    }


    // --------------------------------------------------
    // Check Melbourne CBD boundary
    // --------------------------------------------------

    function isInsideMelbourneCBD(
      place
    ) {
      const [
        minLat,
        maxLat,
      ] =
        MELBOURNE_CBD_LATITUDE_RANGE;

      const [
        minLng,
        maxLng,
      ] =
        MELBOURNE_CBD_LONGITUDE_RANGE;

      return (
        place.latitude >= minLat &&
        place.latitude <= maxLat &&
        place.longitude >= minLng &&
        place.longitude <= maxLng
      );
    }


    // --------------------------------------------------
    // Build several search variants
    // --------------------------------------------------

    function buildSearchQueries(
      rawQuery
    ) {
      const query =
        rawQuery.trim();

      const lower =
        query.toLowerCase();

      const queries = [
        `${query}, Melbourne VIC, Australia`,
        `${query}, Melbourne, Victoria, Australia`,
      ];


      // Common railway station searches.
      if (
        lower.includes("station") &&
        !lower.includes("railway")
      ) {
        queries.push(
          `${query.replace(
            /station/i,
            "Railway Station"
          )}, Melbourne VIC, Australia`
        );
      }


      // If user only enters a station/place name,
      // try adding "Station".
      if (
        !lower.includes("station")
      ) {
        queries.push(
          `${query} Station, Melbourne VIC, Australia`
        );
      }


      return [
        ...new Set(
          queries
        ),
      ];
    }


    // --------------------------------------------------
    // Search Nominatim once
    // --------------------------------------------------

    async function requestLocations(
      query,
      limit = 8
    ) {
      const params =
        new URLSearchParams({
          q: query,

          format:
            "jsonv2",

          addressdetails:
            "1",

          namedetails:
            "1",

          limit:
            String(limit),

          countrycodes:
            "au",

          "accept-language":
            "en",
        });


      const response =
        await fetch(
          `https://nominatim.openstreetmap.org/search?${params.toString()}`
        );


      if (!response.ok) {
        throw new Error(
          `Location search failed with status ${response.status}`
        );
      }


      return (
        await response.json()
      );
    }


    // --------------------------------------------------
    // Search using multiple Melbourne-specific queries
    // --------------------------------------------------

    async function findLocations(
      rawQuery
    ) {
      const searchQueries =
        buildSearchQueries(
          rawQuery
        );


      const collected =
        [];

      const seen =
        new Set();


      for (
        const searchQuery
        of searchQueries
      ) {
        const data =
          await requestLocations(
            searchQuery
          );


        for (
          const item
          of data
        ) {
          const place =
            convertPlace(
              item,
              rawQuery
            );


          if (
            !Number.isFinite(
              place.latitude
            ) ||
            !Number.isFinite(
              place.longitude
            )
          ) {
            continue;
          }


          // eScape currently supports
          // Melbourne CBD only.
          if (
            !isInsideMelbourneCBD(
              place
            )
          ) {
            continue;
          }


          const key =
            `${place.latitude}-${place.longitude}`;


          if (
            seen.has(
              key
            )
          ) {
            continue;
          }


          seen.add(
            key
          );

          collected.push(
            place
          );
        }


        // Once we already have enough CBD results,
        // there is no need to keep querying.
        if (
          collected.length >= 5
        ) {
          break;
        }
      }


      return collected;
    }


    // --------------------------------------------------
    // Manual location search
    // --------------------------------------------------

    async function searchLocations() {
      const query =
        value.trim();


      if (
        query.length < 3
      ) {
        setNotice(
          "Enter at least 3 characters."
        );

        setSuggestions(
          []
        );

        setOpen(
          false
        );

        return;
      }


      try {
        setSearching(
          true
        );

        setNotice(
          "Searching..."
        );

        setSuggestions(
          []
        );

        setOpen(
          false
        );


        const places =
          await findLocations(
            query
          );


        setSuggestions(
          places.slice(
            0,
            5
          )
        );


        if (
          places.length > 0
        ) {
          setOpen(
            true
          );

          setNotice(
            ""
          );
        } else {
          setOpen(
            false
          );

          setNotice(
            `No Melbourne CBD location found for "${query}".`
          );
        }

      } catch (
        searchError
      ) {
        console.error(
          "OSM location search error:",
          searchError
        );

        setSuggestions(
          []
        );

        setOpen(
          false
        );

        setNotice(
          "Unable to search locations right now."
        );

      } finally {
        setSearching(
          false
        );
      }
    }


    // --------------------------------------------------
    // Automatically resolve typed location
    // --------------------------------------------------

    async function resolveLocation() {
      // Already selected.
      if (
        selectedPlace
      ) {
        return (
          selectedPlace
        );
      }


      const query =
        value.trim();


      if (!query) {
        return null;
      }


      if (
        query.length < 3
      ) {
        setNotice(
          "Enter at least 3 characters."
        );

        return null;
      }


      try {
        setSearching(
          true
        );

        setNotice(
          "Finding location..."
        );


        const places =
          await findLocations(
            query
          );


        if (
          !places.length
        ) {
          setNotice(
            `No Melbourne CBD location found for "${query}".`
          );

          return null;
        }


        // Use best matching CBD result.
        const place =
          places[0];


        onSelectSuggestion?.(
          place
        );


        setValue(
          place.label
        );

        setSuggestions(
          []
        );

        setOpen(
          false
        );

        setNotice(
          ""
        );


        return place;

      } catch (
        searchError
      ) {
        console.error(
          "OSM automatic location search error:",
          searchError
        );


        setNotice(
          "Unable to find this location right now."
        );


        return null;

      } finally {
        setSearching(
          false
        );
      }
    }


    // --------------------------------------------------
    // Expose resolveLocation() to JourneyForm
    // --------------------------------------------------

    useImperativeHandle(
      ref,
      () => ({
        resolveLocation,
      })
    );


    // --------------------------------------------------
    // Update input while typing
    // --------------------------------------------------

    function handleChange(
      event
    ) {
      const newValue =
        event.target.value;


      setValue(
        newValue
      );


      setSuggestions(
        []
      );

      setOpen(
        false
      );

      setNotice(
        ""
      );


      if (
        selectedPlace
      ) {
        onClear?.();
      }
    }


    // --------------------------------------------------
    // Select suggestion
    // --------------------------------------------------

    function handleSelect(
      place
    ) {
      setValue(
        place.label
      );


      onSelectSuggestion?.(
        place
      );


      setSuggestions(
        []
      );

      setOpen(
        false
      );

      setNotice(
        ""
      );
    }


    // --------------------------------------------------
    // Clear
    // --------------------------------------------------

    function handleClear() {
      setValue(
        ""
      );

      setSuggestions(
        []
      );

      setOpen(
        false
      );

      setNotice(
        ""
      );


      onClear?.();
    }


    // --------------------------------------------------
    // Enter key search
    // --------------------------------------------------

    function handleKeyDown(
      event
    ) {
      if (
        event.key ===
        "Enter"
      ) {
        event.preventDefault();


        if (
          !searching &&
          value
            .trim()
            .length >= 3
        ) {
          searchLocations();
        }
      }
    }


    // --------------------------------------------------
    // Render
    // --------------------------------------------------

    return (
      <div className="location-input">

        <label
          htmlFor={id}
        >
          {label}
        </label>


        <div className="location-input__field">

          <input
            id={id}

            aria-label={
              accessibleLabel
            }

            aria-invalid={
              Boolean(
                error
              )
            }

            value={
              value
            }

            placeholder={
              placeholder
            }

            disabled={
              loading
            }

            autoComplete="off"

            onChange={
              handleChange
            }

            onKeyDown={
              handleKeyDown
            }
          />


          {value && (
            <button
              type="button"

              className="location-input__clear"

              onClick={
                handleClear
              }

              aria-label={
                `Clear ${(
                  accessibleLabel ||
                  label
                ).toLowerCase()}`
              }
            >
              ×
            </button>
          )}

        </div>


        <button
          type="button"

          className="location-search-button"

          onClick={
            searchLocations
          }

          disabled={
            loading ||
            searching ||
            value
              .trim()
              .length < 3
          }
        >
          {
            searching
              ? "Searching..."
              : "Search location"
          }
        </button>


        {showCurrentLocation && (
          <button
            type="button"

            className="current-location-button"

            onClick={
              onUseCurrentLocation
            }

            disabled={
              loading
            }
          >
            Use current location
          </button>
        )}


        {open &&
          suggestions.length > 0 && (
            <ul className="place-suggestions">

              {suggestions.map(
                (place) => (
                  <li
                    key={
                      place.id
                    }
                  >
                    <button
                      type="button"

                      onClick={() =>
                        handleSelect(
                          place
                        )
                      }
                    >
                      <strong>
                        {
                          place.label
                        }
                      </strong>

                      <small>
                        {
                          place.formattedAddress
                        }
                      </small>
                    </button>
                  </li>
                )
              )}

            </ul>
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
  }
);


export default LocationInput;