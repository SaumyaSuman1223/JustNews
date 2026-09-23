import "server-only";

/**
 * Open-Meteo, for Discover's Weather widget: free, no key, and no account -
 * the widget's only third party. Called from route handlers, never from the
 * page render, so a slow forecast can only ever delay the widget.
 *
 * Coordinates are rounded to two decimals (~1 km) before they leave the
 * server: precise enough for a forecast, coarse enough not to pinpoint a
 * reader who used "my location", and it lets every reader in a city share
 * one cached answer.
 */
const FORECAST = "https://api.open-meteo.com/v1/forecast";
const GEOCODE = "https://geocoding-api.open-meteo.com/v1/search";
const TIMEOUT_MS = 4000;

export interface Forecast {
  current: { temperature: number; code: number };
  days: { date: string; code: number; high: number; low: number }[];
}

export interface Place {
  name: string;
  region: string | null;
  country: string | null;
  lat: number;
  lon: number;
}

export function roundCoordinate(value: number): number {
  return Math.round(value * 100) / 100;
}

/** One GET with a timeout, retried once on a network error or 5xx. */
async function getJson(url: string, revalidate: number): Promise<unknown> {
  let last: unknown;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await fetch(url, {
        signal: AbortSignal.timeout(TIMEOUT_MS),
        next: { revalidate },
      });
      if (response.ok) return await response.json();
      if (response.status < 500) throw new Error(`HTTP ${response.status}`);
      last = new Error(`HTTP ${response.status}`);
    } catch (error) {
      last = error;
    }
  }
  throw last;
}

export async function forecast(lat: number, lon: number): Promise<Forecast> {
  const query = new URLSearchParams({
    latitude: String(roundCoordinate(lat)),
    longitude: String(roundCoordinate(lon)),
    current: "temperature_2m,weather_code",
    daily: "weather_code,temperature_2m_max,temperature_2m_min",
    timezone: "auto",
    forecast_days: "6",
  });
  // 30 minutes: the forecast itself only updates hourly.
  const data = (await getJson(`${FORECAST}?${query}`, 1800)) as {
    current?: { temperature_2m?: number; weather_code?: number };
    daily?: {
      time?: string[];
      weather_code?: number[];
      temperature_2m_max?: number[];
      temperature_2m_min?: number[];
    };
  };
  const daily = data.daily ?? {};
  const days = (daily.time ?? []).map((date, index) => ({
    date,
    code: daily.weather_code?.[index] ?? 0,
    high: daily.temperature_2m_max?.[index] ?? 0,
    low: daily.temperature_2m_min?.[index] ?? 0,
  }));
  if (typeof data.current?.temperature_2m !== "number" || days.length === 0) {
    throw new Error("incomplete forecast");
  }
  return {
    current: { temperature: data.current.temperature_2m, code: data.current.weather_code ?? 0 },
    days,
  };
}

export async function searchPlaces(name: string, language: string): Promise<Place[]> {
  const query = new URLSearchParams({ name, count: "6", language, format: "json" });
  // A day: a city does not move.
  const data = (await getJson(`${GEOCODE}?${query}`, 86400)) as {
    results?: {
      name: string;
      admin1?: string;
      country?: string;
      latitude: number;
      longitude: number;
    }[];
  };
  return (data.results ?? []).map((result) => ({
    name: result.name,
    region: result.admin1 ?? null,
    country: result.country ?? null,
    lat: roundCoordinate(result.latitude),
    lon: roundCoordinate(result.longitude),
  }));
}
