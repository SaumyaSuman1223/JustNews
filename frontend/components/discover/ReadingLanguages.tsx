"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ChevronDownIcon } from "@/components/icons";
import { getLocale, locales, t, type LocaleCode } from "@/lib/i18n";

/**
 * "Read in": which languages Discover's stories come in, separate from the
 * language of the menus. A reader in Delhi can keep English menus and read
 * English and Hindi reporting in one feed - the thing this product exists
 * to do, available without an account.
 *
 * A disclosure, not a modal: a few checkboxes and a save, dismissed by
 * Escape or a click outside, with focus returned to the button.
 */
export function ReadingLanguages({ locale, selected }: { locale: LocaleCode; selected: string[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [choice, setChoice] = useState<string[]>(selected);
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);
  const panel = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    panel.current?.querySelector<HTMLInputElement>("input")?.focus();
    function close() {
      setOpen(false);
      trigger.current?.focus();
    }
    function onPointer(event: PointerEvent) {
      const target = event.target as Node;
      if (!panel.current?.contains(target) && !trigger.current?.contains(target)) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") close();
    }
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const names = selected.map((code) => getLocale(code).label);
  const summary = t(locale, "readIn.summary", { languages: names.join(", ") });

  async function save() {
    setSaving(true);
    setFailed(false);
    const response = await fetch("/api/reading-languages", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ languages: choice }),
    }).catch(() => null);
    setSaving(false);
    if (!response?.ok) {
      setFailed(true);
      return;
    }
    setOpen(false);
    trigger.current?.focus();
    // The page and its rail re-render from the new cookie; Discover's feed
    // is keyed by these languages, so it fetches the new one itself.
    router.refresh();
  }

  function toggle(code: string) {
    setChoice((current) =>
      current.includes(code) ? current.filter((item) => item !== code) : [...current, code],
    );
  }

  return (
    <div className="read-in">
      <button
        ref={trigger}
        type="button"
        className="discover__tool read-in__trigger"
        aria-expanded={open}
        aria-controls="read-in-panel"
        aria-label={summary}
        onClick={() => {
          setChoice(selected);
          setOpen((value) => !value);
        }}
      >
        <span className="read-in__long" aria-hidden="true">
          {t(locale, "readIn.label")}{" "}
          {selected.map((code, index) => (
            <span key={code}>
              {index > 0 && ", "}
              <span lang={getLocale(code).htmlLang}>{getLocale(code).label}</span>
            </span>
          ))}
        </span>
        <span className="read-in__short" aria-hidden="true">
          {selected.map((code) => code.toUpperCase()).join(" · ")}
        </span>
        <ChevronDownIcon className="read-in__chevron" />
      </button>
      {open && (
        <div className="read-in__panel" id="read-in-panel" ref={panel}>
          <fieldset className="read-in__fieldset">
            <legend className="read-in__legend">{t(locale, "readIn.legend")}</legend>
            {locales.map((option) => (
              <label key={option.code} className="read-in__option">
                <input
                  type="checkbox"
                  checked={choice.includes(option.code)}
                  onChange={() => toggle(option.code)}
                />
                <span lang={option.htmlLang}>{option.label}</span>
              </label>
            ))}
          </fieldset>
          <p className="read-in__note">
            {t(locale, "readIn.note", { language: getLocale(locale).label })}
          </p>
          <div className="read-in__actions">
            <button
              type="button"
              className="button button--primary"
              disabled={choice.length === 0 || saving}
              onClick={save}
            >
              {t(locale, saving ? "readIn.saving" : "readIn.save")}
            </button>
          </div>
          {failed && (
            <p className="form-error" role="alert">
              {t(locale, "readIn.failed")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
