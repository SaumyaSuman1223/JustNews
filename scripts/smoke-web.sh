#!/usr/bin/env bash
#
# Every locale must actually be served by the built app.
#
# This exists because of a real failure: sv, no and da were added to the locale
# registry, the Python test comparing the registry against LAUNCH_LANGUAGES
# passed (both sources agreed), the build reported eleven prerendered locales,
# and the running server still returned 404 for those three. A stale Next.js
# build cache had kept an older copy of the compiled route.
#
# No source-level test can catch that, because every source was correct. Only
# asking the built server catches it.
#
# Usage: scripts/smoke-web.sh [base-url]
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:3000}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Read the launch languages from their single source of truth rather than
# repeating them here, so this script cannot drift from the application.
mapfile -t LOCALES < <(
  python3 - "$REPO_ROOT" <<'PY'
import re, sys, pathlib
source = (pathlib.Path(sys.argv[1]) / "packages/core/src/justnews_core/language.py").read_text()
block = re.search(r"LAUNCH_LANGUAGES:[^=]*=\s*\(([^)]*)\)", source, re.S).group(1)
print("\n".join(re.findall(r'"([a-z-]+)"', block)))
PY
)

echo "Checking ${#LOCALES[@]} locales against ${BASE_URL}"

failures=0
for locale in "${LOCALES[@]}"; do
  status=$(curl -s -o /dev/null -w '%{http_code}' "${BASE_URL}/${locale}" || echo 000)
  if [[ "$status" != "200" ]]; then
    echo "  FAIL  /${locale} -> ${status}"
    failures=$((failures + 1))
    continue
  fi

  body=$(curl -s "${BASE_URL}/${locale}")
  if ! grep -q '<html' <<<"$body"; then
    echo "  FAIL  /${locale} -> 200 but no document"
    failures=$((failures + 1))
    continue
  fi

  # Arabic is the right-to-left canary: if the direction flag is wrong, every
  # logical CSS property in the design system mirrors the wrong way.
  expected_dir="ltr"
  [[ "$locale" == "ar" ]] && expected_dir="rtl"
  if ! grep -q "dir=\"${expected_dir}\"" <<<"$body"; then
    echo "  FAIL  /${locale} -> expected dir=\"${expected_dir}\""
    failures=$((failures + 1))
    continue
  fi

  echo "  ok    /${locale}"
done

# An unknown locale must 404 rather than render an empty page.
status=$(curl -s -o /dev/null -w '%{http_code}' "${BASE_URL}/zz" || echo 000)
if [[ "$status" != "404" ]]; then
  echo "  FAIL  /zz -> ${status}, expected 404"
  failures=$((failures + 1))
else
  echo "  ok    /zz -> 404"
fi

if (( failures > 0 )); then
  echo "${failures} locale check(s) failed"
  exit 1
fi
echo "All locales served."
