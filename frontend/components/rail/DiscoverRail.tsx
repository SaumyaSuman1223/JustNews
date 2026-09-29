"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import type { DiscoverTopic } from "@/components/discover/Discover";
import { ChevronDownIcon, CloseIcon, SlidersIcon } from "@/components/icons";
import { CompaniesWidget, MarketsWidget } from "@/components/rail/MarketWidgets";
import {
  AcrossLanguagesModule,
  MostReadModule,
  TodaysAquilaModule,
} from "@/components/rail/NewsModules";
import { TopicPerspectives } from "@/components/rail/TopicPerspectives";
import { WeatherWidget } from "@/components/rail/WeatherWidget";
import type {
  AcrossLanguages,
  Article,
  Issue,
  IssuePageContent,
  MarketTile,
  TrendingCompany,
} from "@/lib/api";
import { CUSTOMIZE_EVENT, INTERESTS_EVENT, REFRESH_EVENT } from "@/lib/discoverEvents";
import { t, tPlural, type LocaleCode, type MessageKey } from "@/lib/i18n";
import {
  RAIL_COOKIE,
  serializeRailPrefs,
  writePreferenceCookie,
  type RailPrefs,
  type WeatherPlace,
  type WidgetId,
} from "@/lib/railPrefs";

export interface RailData {
  locale: LocaleCode;
  acrossLanguages: AcrossLanguages[];
  issue: Issue | null;
  issueFront: IssuePageContent | null;
  mostRead: Article[];
  markets: MarketTile[];
  companies: TrendingCompany[];
  weatherPlace: WeatherPlace | null;
  tempUnit: "c" | "f";
}

type Widget = {
  titleKey: MessageKey;
  render: (data: RailData) => ReactNode;
  /** A news module with nothing to say is left out rather than shown empty;
   * the customize panel still lists it. */
  empty?: (data: RailData) => boolean;
};

/**
 * The rail's modules. Adding one is a component and an entry here (plus its
 * id in lib/railPrefs.ts): the rail, the customize panel and the reader's
 * saved order all read this.
 */
const WIDGETS: Record<WidgetId, Widget> = {
  languages: {
    titleKey: "across.title",
    render: (data) => <AcrossLanguagesModule locale={data.locale} stories={data.acrossLanguages} />,
    empty: (data) => data.acrossLanguages.length === 0,
  },
  aquila: {
    titleKey: "aquila.today",
    render: (data) =>
      data.issue ? (
        <TodaysAquilaModule locale={data.locale} issue={data.issue} front={data.issueFront} />
      ) : null,
    empty: (data) => data.issue === null,
  },
  trending: {
    titleKey: "mostRead.title",
    render: (data) => <MostReadModule locale={data.locale} articles={data.mostRead} />,
    empty: (data) => data.mostRead.length === 0,
  },
  weather: {
    titleKey: "weather.title",
    render: (data) => (
      <WeatherWidget
        locale={data.locale}
        initialPlace={data.weatherPlace}
        initialUnit={data.tempUnit}
      />
    ),
  },
  markets: {
    titleKey: "markets.title",
    render: (data) => <MarketsWidget locale={data.locale} tiles={data.markets} />,
  },
  companies: {
    titleKey: "companies.title",
    render: (data) => <CompaniesWidget locale={data.locale} companies={data.companies} />,
  },
};

/**
 * Discover's rail: the topics question for a reader who has not answered it,
 * then their modules in their own order - what only JustNews has first
 * (the same story across languages, today's Aquila, what readers are
 * opening), and weather or markets for a reader who turns them on. Every
 * module renders from data the page already fetched, except the weather,
 * which asks for its city.
 */
export function DiscoverRail({
  data,
  initialPrefs,
  askInterests,
  interestTopics,
}: {
  data: RailData;
  initialPrefs: RailPrefs;
  askInterests: boolean;
  interestTopics: DiscoverTopic[];
}) {
  const { locale } = data;
  const [prefs, setPrefs] = useState(initialPrefs);
  const [customizing, setCustomizing] = useState(false);
  const [asking, setAsking] = useState(askInterests);

  useEffect(() => {
    const open = () => setCustomizing(true);
    window.addEventListener(CUSTOMIZE_EVENT, open);
    return () => window.removeEventListener(CUSTOMIZE_EVENT, open);
  }, []);

  // Asked again, and this time the reader asked: focus goes to the card.
  const [askedByReader, setAskedByReader] = useState(false);
  useEffect(() => {
    function ask() {
      setAsking(true);
      setAskedByReader(true);
    }
    window.addEventListener(INTERESTS_EVENT, ask);
    return () => window.removeEventListener(INTERESTS_EVENT, ask);
  }, []);

  function update(next: RailPrefs) {
    setPrefs(next);
    writePreferenceCookie(RAIL_COOKIE, serializeRailPrefs(next));
  }

  const visible = prefs.order.filter(
    (id) => !prefs.hidden.includes(id) && !WIDGETS[id].empty?.(data),
  );

  return (
    <aside className="discover-rail" aria-label={t(locale, "rail.label")}>
      {asking && (
        <MakeItYours
          locale={locale}
          topics={interestTopics}
          focusOnOpen={askedByReader}
          onDone={() => setAsking(false)}
        />
      )}

      {customizing && (
        <CustomizePanel
          locale={locale}
          data={data}
          prefs={prefs}
          onChange={update}
          onClose={() => setCustomizing(false)}
        />
      )}

      <TopicPerspectives locale={locale} />

      {/* One group, so a narrow screen can scroll the widgets sideways
          beneath the interests card rather than beside it. */}
      <div className="discover-rail__widgets">
        {visible.map((id) => (
          <section
            className={`rail-widget rail-widget--${id}`}
            key={id}
            aria-labelledby={`rail-${id}`}
          >
            <h2 className="rail-widget__title" id={`rail-${id}`}>
              {t(locale, WIDGETS[id].titleKey)}
            </h2>
            {WIDGETS[id].render(data)}
          </section>
        ))}

        <button
          type="button"
          className="rail-link-button rail__customize"
          onClick={() => setCustomizing(true)}
        >
          <SlidersIcon />
          {t(locale, "rail.customize")}
        </button>
      </div>
    </aside>
  );
}

/** The topics offered first: the ones most of the day's reporting falls
 * under, so the short list serves most readers without "More". */
const FIRST_TOPICS = [
  "medtop:11000000", // politics
  "medtop:16000000", // conflict
  "medtop:04000000", // economy and business
  "medtop:13000000", // science and technology
  "medtop:06000000", // environment and climate
  "medtop:15000000", // sport
];

function MakeItYours({
  locale,
  topics,
  focusOnOpen,
  onDone,
}: {
  locale: LocaleCode;
  topics: DiscoverTopic[];
  focusOnOpen: boolean;
  onDone: () => void;
}) {
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (focusOnOpen) title.current?.focus();
  }, [focusOnOpen]);
  const [chosen, setChosen] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);
  const [showAll, setShowAll] = useState(false);
  // A short list first: twenty topics at once is a form, not a question.
  const leading = FIRST_TOPICS.flatMap((id) => topics.filter((topic) => topic.id === id));
  const rest = topics.filter((topic) => !FIRST_TOPICS.includes(topic.id));
  const shown = showAll || leading.length === 0 ? [...leading, ...rest] : leading;

  async function send(body: object): Promise<boolean> {
    const response = await fetch("/api/interests", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      // A reader who closes the card and leaves at once still has it closed.
      keepalive: true,
    }).catch(() => null);
    return Boolean(response?.ok);
  }

  async function save() {
    setSaving(true);
    setFailed(false);
    const ok = await send({ topics: chosen });
    setSaving(false);
    if (!ok) {
      setFailed(true);
      return;
    }
    onDone();
    window.dispatchEvent(new Event(REFRESH_EVENT));
  }

  async function dismiss() {
    onDone();
    await send({ dismiss: true });
  }

  function toggle(id: string) {
    setChosen((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  }

  return (
    <section className="interests" aria-labelledby="interests-title">
      <button
        type="button"
        className="interests__close"
        onClick={dismiss}
        aria-label={t(locale, "interests.close")}
        title={t(locale, "interests.close")}
      >
        <CloseIcon />
      </button>
      <h2 className="interests__title" id="interests-title" tabIndex={-1} ref={title}>
        {t(locale, "interests.title")}
      </h2>
      <p className="interests__body">{t(locale, "interests.body")}</p>
      <ul className="interests__chips">
        {shown.map((topic) => (
          <li key={topic.id}>
            <button
              type="button"
              className="chip interests__chip"
              aria-pressed={chosen.includes(topic.id)}
              onClick={() => toggle(topic.id)}
            >
              {topic.label}
            </button>
          </li>
        ))}
        {!showAll && leading.length > 0 && rest.length > 0 && (
          <li>
            <button type="button" className="chip interests__more" onClick={() => setShowAll(true)}>
              {tPlural(locale, "interests.more", rest.length)}
            </button>
          </li>
        )}
      </ul>
      <button
        type="button"
        className="button button--primary interests__save"
        disabled={chosen.length === 0 || saving}
        onClick={save}
      >
        {t(locale, saving ? "interests.saving" : "interests.save")}
      </button>
      {failed && (
        <p className="form-error" role="alert">
          {t(locale, "interests.failed")}
        </p>
      )}
    </section>
  );
}

function CustomizePanel({
  locale,
  data,
  prefs,
  onChange,
  onClose,
}: {
  locale: LocaleCode;
  data: RailData;
  prefs: RailPrefs;
  onChange: (prefs: RailPrefs) => void;
  onClose: () => void;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  const close = useRef(onClose);
  useEffect(() => {
    close.current = onClose;
  });
  // Focus moves into the panel once, when it opens - not on every change
  // made inside it.
  useEffect(() => {
    heading.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") close.current();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function move(id: WidgetId, by: -1 | 1) {
    const order = [...prefs.order];
    const from = order.indexOf(id);
    const to = from + by;
    if (to < 0 || to >= order.length) return;
    [order[from], order[to]] = [order[to]!, order[from]!];
    onChange({ ...prefs, order });
  }

  function toggle(id: WidgetId) {
    const hidden = prefs.hidden.includes(id)
      ? prefs.hidden.filter((item) => item !== id)
      : [...prefs.hidden, id];
    onChange({ ...prefs, hidden });
  }

  return (
    <section className="rail-customize" aria-labelledby="rail-customize-title">
      <h2 className="rail-widget__title" id="rail-customize-title" tabIndex={-1} ref={heading}>
        {t(locale, "rail.customize.title")}
      </h2>
      <ol className="rail-customize__list">
        {prefs.order.map((id, index) => {
          const name = t(locale, WIDGETS[id].titleKey);
          return (
            <li key={id}>
              <label className="rail-customize__toggle">
                <input
                  type="checkbox"
                  checked={!prefs.hidden.includes(id)}
                  onChange={() => toggle(id)}
                />
                <span>{name}</span>
                {/* On, but with nothing to show: said here, since the rail
                    leaves an empty module out. */}
                {WIDGETS[id].empty?.(data) && (
                  <span className="rail-customize__empty">
                    {t(locale, "rail.customize.nothingYet")}
                  </span>
                )}
              </label>
              <span className="rail-customize__moves">
                <button
                  type="button"
                  onClick={() => move(id, -1)}
                  disabled={index === 0}
                  aria-label={t(locale, "rail.customize.up", { widget: name })}
                >
                  <ChevronDownIcon className="rail-customize__up" />
                </button>
                <button
                  type="button"
                  onClick={() => move(id, 1)}
                  disabled={index === prefs.order.length - 1}
                  aria-label={t(locale, "rail.customize.down", { widget: name })}
                >
                  <ChevronDownIcon />
                </button>
              </span>
            </li>
          );
        })}
      </ol>
      <button type="button" className="button button--secondary" onClick={onClose}>
        {t(locale, "rail.customize.done")}
      </button>
    </section>
  );
}
