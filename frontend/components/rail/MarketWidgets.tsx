"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import type { MarketTile, TrendingCompany } from "@/lib/api";
import { t, tPlural, type LocaleCode } from "@/lib/i18n";

function formatPrice(value: number, locale: LocaleCode): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: value >= 1000 ? 0 : 2,
  }).format(value);
}

function formatChange(pct: number, locale: LocaleCode): string {
  return new Intl.NumberFormat(locale, {
    style: "percent",
    signDisplay: "exceptZero",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(pct / 100);
}

function direction(pct: number): "up" | "down" | "flat" {
  return pct > 0 ? "up" : pct < 0 ? "down" : "flat";
}

/** An arrow as well as a colour: a move is never shown by colour alone. */
function Arrow({ pct }: { pct: number }) {
  const dir = direction(pct);
  if (dir === "flat") return null;
  return (
    <svg viewBox="0 0 12 12" width="0.8em" height="0.8em" aria-hidden="true">
      <path
        d={dir === "up" ? "M3 9 9 3M4 3h5v5" : "M3 3l6 6M9 4v5H4"}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** The day's prices as a line with a faint area under it, drawn to its own
 * range so a quiet day still shows its shape. */
function Sparkline({ series, pct }: { series: number[]; pct: number }) {
  if (series.length < 2)
    return <div className="spark spark--empty" aria-hidden="true" />;
  const min = Math.min(...series);
  const max = Math.max(...series);
  const span = max - min || 1;
  const points = series.map((value, index) => {
    const x = (index / (series.length - 1)) * 100;
    const y = 28 - ((value - min) / span) * 24;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });
  return (
    <svg
      className={`spark spark--${direction(pct)}`}
      viewBox="0 0 100 32"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        className="spark__area"
        d={`M0,32 L${points.join(" L")} L100,32 Z`}
      />
      <polyline
        className="spark__line"
        points={points.join(" ")}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

/** Market Outlook: four tiles, each a price, the day's move and its line. */
export function MarketsWidget({
  locale,
  tiles,
}: {
  locale: LocaleCode;
  tiles: MarketTile[];
}) {
  if (tiles.length === 0)
    return <p className="rail-widget__empty">{t(locale, "markets.empty")}</p>;
  return (
    <>
      <ul className="markets">
        {tiles.map((tile) => (
          <li
            key={tile.symbol}
            className="markets__tile"
            aria-label={t(locale, "markets.tile", {
              label: tile.label,
              price: formatPrice(tile.price, locale),
              change: formatChange(tile.change_pct, locale),
            })}
          >
            <div className="markets__head" aria-hidden="true">
              <span className="markets__label">
                {tile.label}
                {tile.symbol !== "BTC" && (
                  <span className="markets__symbol">{tile.symbol}</span>
                )}
              </span>
              <span
                className={`markets__change markets__change--${direction(tile.change_pct)}`}
              >
                <Arrow pct={tile.change_pct} />
                {formatChange(tile.change_pct, locale)}
              </span>
            </div>
            <div className="markets__price" aria-hidden="true">
              {formatPrice(tile.price, locale)}
            </div>
            <Sparkline series={tile.series} pct={tile.change_pct} />
          </li>
        ))}
      </ul>
      <p className="rail-widget__source">{t(locale, "markets.note")}</p>
    </>
  );
}

/** Trending Companies: most named in the last day's news - a count of real
 * articles - each leading to a search for it. */
export function CompaniesWidget({
  locale,
  companies,
}: {
  locale: LocaleCode;
  companies: TrendingCompany[];
}) {
  if (companies.length === 0) {
    return <p className="rail-widget__empty">{t(locale, "companies.empty")}</p>;
  }
  return (
    <>
      <p className="rail-widget__sub">{t(locale, "companies.subtitle")}</p>
      <ul className="companies">
        {companies.map((company) => (
          <li key={`${company.ticker}-${company.name}`}>
            <Link
              className="companies__row"
              href={`/${locale}/search?q=${encodeURIComponent(company.name)}`}
            >
              <CompanyMark name={company.name} domain={company.domain} />
              <span className="companies__name">
                {company.name}
                <span className="companies__meta">
                  {company.ticker} ·{" "}
                  {tPlural(locale, "companies.stories", company.mentions)}
                </span>
              </span>
              {company.price !== null && company.change_pct !== null ? (
                <span className="companies__quote">
                  {formatPrice(company.price, locale)}
                  <span
                    className={`markets__change markets__change--${direction(company.change_pct)}`}
                  >
                    <Arrow pct={company.change_pct} />
                    {formatChange(company.change_pct, locale)}
                  </span>
                </span>
              ) : (
                <span className="companies__quote companies__quote--none">
                  {company.exchange}
                </span>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}

/** The company's own favicon, over its initial - which is what stays when
 * the icon does not load. */
function CompanyMark({ name, domain }: { name: string; domain: string }) {
  const [failed, setFailed] = useState(false);
  return (
    <span className="companies__mark" aria-hidden="true">
      <span className="companies__initial">{name.slice(0, 1)}</span>
      {!failed && (
        <Image
          className="companies__logo"
          src={`https://${domain}/favicon.ico`}
          alt=""
          width={28}
          height={28}
          unoptimized
          onError={() => setFailed(true)}
        />
      )}
    </span>
  );
}
