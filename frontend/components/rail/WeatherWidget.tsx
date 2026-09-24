"use client";

import { useEffect, useRef, useState } from "react";

import { t, type LocaleCode, type MessageKey } from "@/lib/i18n";
import {
  TEMP_UNIT_COOKIE,
  WEATHER_COOKIE,
  serializeWeatherPlace,
  writePreferenceCookie,
  type WeatherPlace,
} from "@/lib/railPrefs";

interface Forecast {
  current: { temperature: number; code: number };
  days: { date: string; code: number; high: number; low: number }[];
}

interface Place {
  name: string;
  region: string | null;
  country: string | null;
  lat: number;
  lon: number;
}

type Condition =
  "clear" | "partlyCloudy" | "cloudy" | "fog" | "drizzle" | "rain" | "snow" | "showers" | "thunder";

/** WMO weather codes, as Open-Meteo reports them, grouped into what a
 * reader would call the sky. */
function condition(code: number): Condition {
  if (code === 0) return "clear";
  if (code <= 2) return "partlyCloudy";
  if (code === 3) return "cloudy";
  if (code === 45 || code === 48) return "fog";
  if (code >= 51 && code <= 57) return "drizzle";
  if ((code >= 61 && code <= 67) || code === 80 || code === 81 || code === 82) {
    return code >= 80 ? "showers" : "rain";
  }
  if ((code >= 71 && code <= 77) || code === 85 || code === 86) return "snow";
  if (code >= 95) return "thunder";
  return "cloudy";
}

/**
 * Weather for a city the reader chose - never one guessed from their IP
 * (docs/DISCOVER_PLAN.md §4). Asks once, remembers the answer in a cookie.
 * Celsius or Fahrenheit is the reader's toggle; the forecast is fetched in
 * Celsius once and converted here, so both share one cached answer.
 */
export function WeatherWidget({
  locale,
  initialPlace,
  initialUnit,
}: {
  locale: LocaleCode;
  initialPlace: WeatherPlace | null;
  initialUnit: "c" | "f";
}) {
  const [place, setPlace] = useState(initialPlace);
  const [unit, setUnit] = useState(initialUnit);
  const [data, setData] = useState<Forecast | null>(null);
  const [failed, setFailed] = useState(false);
  const [choosing, setChoosing] = useState(initialPlace === null);

  useEffect(() => {
    if (!place) return;
    let cancelled = false;
    fetch(`/api/widgets/weather?lat=${place.lat}&lon=${place.lon}`)
      .then((response) => (response.ok ? (response.json() as Promise<Forecast>) : Promise.reject()))
      .then((forecast) => {
        if (cancelled) return;
        setData(forecast);
        setFailed(false);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [place]);

  function choose(next: WeatherPlace) {
    writePreferenceCookie(WEATHER_COOKIE, serializeWeatherPlace(next));
    setData(null);
    setPlace(next);
    setChoosing(false);
  }

  function toggleUnit() {
    const next = unit === "c" ? "f" : "c";
    writePreferenceCookie(TEMP_UNIT_COOKIE, next);
    setUnit(next);
  }

  const show = (celsius: number) => Math.round(unit === "f" ? (celsius * 9) / 5 + 32 : celsius);
  const weekday = new Intl.DateTimeFormat(locale, { weekday: "short" });
  const today = data?.days[0];

  if (choosing || !place) {
    return (
      <PlacePicker
        locale={locale}
        onChoose={choose}
        onCancel={place ? () => setChoosing(false) : undefined}
      />
    );
  }

  return (
    <div className="weather">
      {failed ? (
        <p className="rail-widget__empty">{t(locale, "weather.error")}</p>
      ) : !data || !today ? (
        <div className="weather__loading" aria-hidden="true">
          <span className="skel__line skel__line--xl" />
          <span className="skel__line" />
        </div>
      ) : (
        <>
          <div className="weather__now">
            <span className="weather__temp">
              <WeatherIcon kind={condition(data.current.code)} className="weather__icon" />
              {show(data.current.temperature)}°
              <button
                type="button"
                className="weather__unit"
                onClick={toggleUnit}
                aria-label={t(locale, "weather.unit", { unit: unit === "c" ? "F" : "C" })}
              >
                <span aria-hidden="true">
                  {unit === "c" ? "C" : "F"}
                  <span className="weather__unit-alt">/{unit === "c" ? "F" : "C"}</span>
                </span>
              </button>
            </span>
            <span className="weather__sky">
              {t(locale, `weather.code.${condition(data.current.code)}` as MessageKey)}
            </span>
          </div>
          <div className="weather__place">
            <button type="button" className="weather__change" onClick={() => setChoosing(true)}>
              {place.name}
              <span className="visually-hidden"> - {t(locale, "weather.change")}</span>
            </button>
            <span>
              {t(locale, "weather.highLow", { high: show(today.high), low: show(today.low) })}
            </span>
          </div>
          <ol className="weather__days">
            {data.days.slice(1, 6).map((day) => (
              <li key={day.date}>
                <WeatherIcon kind={condition(day.code)} className="weather__day-icon" />
                <span className="weather__day-high">{show(day.high)}°</span>
                <span className="weather__day-name">
                  {weekday.format(new Date(`${day.date}T12:00:00`))}
                </span>
              </li>
            ))}
          </ol>
        </>
      )}
      <p className="rail-widget__source">{t(locale, "weather.attribution")}</p>
    </div>
  );
}

function PlacePicker({
  locale,
  onChoose,
  onCancel,
}: {
  locale: LocaleCode;
  onChoose: (place: WeatherPlace) => void;
  onCancel?: () => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Place[] | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (query.trim().length < 2) return;
    // A short pause after typing, so a city name is one request, not six.
    timer.current = setTimeout(() => {
      fetch(`/api/widgets/places?q=${encodeURIComponent(query.trim())}&locale=${locale}`)
        .then((response) => (response.ok ? (response.json() as Promise<Place[]>) : []))
        .then(setResults)
        .catch(() => setResults([]));
    }, 250);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [query, locale]);

  function useLocation() {
    navigator.geolocation?.getCurrentPosition(
      (position) =>
        onChoose({
          // Rounded here too, before it is ever stored: ~1 km is plenty.
          lat: Math.round(position.coords.latitude * 100) / 100,
          lon: Math.round(position.coords.longitude * 100) / 100,
          name: t(locale, "weather.myLocation"),
        }),
      () => {
        // Refused or unavailable: the search is still right there.
      },
      { maximumAge: 60 * 60 * 1000, timeout: 8000 },
    );
  }

  return (
    <div className="weather weather--picker">
      <p className="weather__prompt">{t(locale, "weather.setCity")}</p>
      <input
        type="search"
        className="weather__search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={t(locale, "weather.search")}
        aria-label={t(locale, "weather.search")}
        autoComplete="off"
      />
      {results !== null && query.trim().length >= 2 && (
        <ul className="weather__results">
          {results.length === 0 ? (
            <li className="rail-widget__empty">{t(locale, "weather.noResults")}</li>
          ) : (
            results.map((result) => (
              <li key={`${result.lat},${result.lon}`}>
                <button
                  type="button"
                  onClick={() => onChoose({ name: result.name, lat: result.lat, lon: result.lon })}
                >
                  {result.name}
                  <span>{[result.region, result.country].filter(Boolean).join(", ")}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}
      <div className="weather__picker-actions">
        <button type="button" className="rail-link-button" onClick={useLocation}>
          {t(locale, "weather.useLocation")}
        </button>
        {onCancel && (
          <button type="button" className="rail-link-button" onClick={onCancel}>
            {t(locale, "rail.customize.done")}
          </button>
        )}
      </div>
    </div>
  );
}

function WeatherIcon({ kind, className }: { kind: Condition; className?: string }) {
  const sun = (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4" />
    </>
  );
  const cloud = <path d="M7.5 18h9a4 4 0 0 0 .5-8 5.5 5.5 0 0 0-10.6 1.6A3.3 3.3 0 0 0 7.5 18z" />;
  const shapes: Record<Condition, React.ReactNode> = {
    clear: sun,
    partlyCloudy: (
      <>
        <path d="M8 4.5v1.2M3.8 8.7H5M5 5.7l.9.9M11.1 5.7l-.9.9" />
        <path d="M10.2 8.3a3 3 0 0 0-5.3 2.2" />
        <path d="M8.5 19h8a3.6 3.6 0 0 0 .4-7.2 5 5 0 0 0-9.6 1.4A2.9 2.9 0 0 0 8.5 19z" />
      </>
    ),
    cloudy: cloud,
    fog: (
      <>
        {cloud}
        <path d="M5 21h14" />
      </>
    ),
    drizzle: (
      <>
        {cloud}
        <path d="M9 21v.5M13 21v.5" />
      </>
    ),
    rain: (
      <>
        {cloud}
        <path d="m9 20-1 2M13 20l-1 2M17 20l-1 2" />
      </>
    ),
    showers: (
      <>
        {cloud}
        <path d="m10 20-1 2M15 20l-1 2" />
      </>
    ),
    snow: (
      <>
        {cloud}
        <path d="M9 21h.01M13 21h.01M17 21h.01" />
      </>
    ),
    thunder: (
      <>
        {cloud}
        <path d="m12 18-2 3h3l-2 3" />
      </>
    ),
  };
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="1.4em"
      height="1.4em"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {shapes[kind]}
    </svg>
  );
}
