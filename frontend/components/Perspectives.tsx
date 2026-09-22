import type { PerspectiveGroup } from "@/lib/api";
import { t, type LocaleCode } from "@/lib/i18n";

const ROLE_LABEL_KEY = {
  industry: "desk.perspectives.role.industry",
  government: "desk.perspectives.role.government",
  academic: "desk.perspectives.role.academic",
  investor: "desk.perspectives.role.investor",
  consumer: "desk.perspectives.role.consumer",
  public: "desk.perspectives.role.public",
} as const;

/**
 * ADR 0013's Perspectives: a topic's recent articles grouped by who
 * published them, and nothing this component invents.
 *
 * The copy names the grouping, not a claim about what a sector thinks -
 * "Industry press", never "The Industry View". Every source listed is a
 * real link to that publisher, because the whole point of grounding this in
 * source role rather than an inferred stance is that a reader can check it.
 */
export function Perspectives({
  groups,
  locale,
  headingLevel = 2,
}: {
  groups: PerspectiveGroup[];
  locale: LocaleCode;
  /** 3 when this renders inside an Understand module, whose own heading is an
   * h2 - a group heading has to sit under it, not beside it, or the document
   * outline says these groups are siblings of the section containing them. */
  headingLevel?: 2 | 3;
}) {
  if (groups.length === 0) {
    return <p className="empty-note">{t(locale, "desk.perspectives.empty")}</p>;
  }

  const Heading = headingLevel === 3 ? "h3" : "h2";

  return (
    <div className="perspectives">
      {groups.map((group) => {
        const labelKey = ROLE_LABEL_KEY[group.role as keyof typeof ROLE_LABEL_KEY];
        return (
          <section className="perspectives__group" key={group.role}>
            <Heading className="perspectives__heading">
              {labelKey ? t(locale, labelKey) : group.role}
            </Heading>
            <p className="perspectives__count">
              {t(locale, "desk.perspectives.sourceCount", { count: group.sources.length })}
            </p>
            <ul className="perspectives__sources">
              {group.sources.map((source) => (
                <li key={source.id}>
                  <a href={source.homepage_url} target="_blank" rel="noopener noreferrer">
                    {source.name}
                  </a>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
