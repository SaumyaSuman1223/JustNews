/**
 * The order and visibility of Discover's rail widgets.
 *
 * A cookie, so the server renders the reader's rail in their order on the
 * first request; written by the customize panel. `weather,-markets,companies`
 * is weather first, markets hidden, companies last. A widget added later that
 * the cookie does not mention appears at the end, shown - a new feature is
 * visible until the reader says otherwise.
 */
export const RAIL_COOKIE = "jn_rail";
export const WEATHER_COOKIE = "jn_weather";
export const TEMP_UNIT_COOKIE = "jn_temp_unit";

export const WIDGET_IDS = ["weather", "markets", "companies"] as const;
export type WidgetId = (typeof WIDGET_IDS)[number];

export interface RailPrefs {
  order: WidgetId[];
  hidden: WidgetId[];
}

function isWidgetId(value: string): value is WidgetId {
  return (WIDGET_IDS as readonly string[]).includes(value);
}

export function parseRailPrefs(value: string | undefined): RailPrefs {
  const order: WidgetId[] = [];
  const hidden: WidgetId[] = [];
  for (const raw of (value ?? "").split(",")) {
    const off = raw.startsWith("-");
    const id = off ? raw.slice(1) : raw;
    if (!isWidgetId(id) || order.includes(id)) continue;
    order.push(id);
    if (off) hidden.push(id);
  }
  for (const id of WIDGET_IDS) if (!order.includes(id)) order.push(id);
  return { order, hidden };
}

export function serializeRailPrefs(prefs: RailPrefs): string {
  return prefs.order.map((id) => (prefs.hidden.includes(id) ? `-${id}` : id)).join(",");
}

export interface WeatherPlace {
  name: string;
  lat: number;
  lon: number;
}

/** `lat,lon,name` - the name last, since it may contain anything but its
 * own encoding. */
export function parseWeatherPlace(value: string | undefined): WeatherPlace | null {
  if (!value) return null;
  const [lat, lon, ...rest] = value.split(",");
  const place = {
    lat: Number(lat),
    lon: Number(lon),
    name: rest.length ? decodeURIComponent(rest.join(",")) : "",
  };
  if (!Number.isFinite(place.lat) || !Number.isFinite(place.lon) || !place.name) return null;
  return place;
}

export function serializeWeatherPlace(place: WeatherPlace): string {
  return `${place.lat},${place.lon},${encodeURIComponent(place.name)}`;
}

/** `; secure` over HTTPS, so a preference never travels in the clear; left
 * off on plain-HTTP local development, where the browser would drop it. */
export function secureFlag(): string {
  return window.location.protocol === "https:" ? "; secure" : "";
}

/** Client-side cookie write for a preference: a year, lax, whole site. */
export function writePreferenceCookie(name: string, value: string): void {
  document.cookie = `${name}=${value}; path=/; max-age=${60 * 60 * 24 * 365}; samesite=lax${secureFlag()}`;
}
