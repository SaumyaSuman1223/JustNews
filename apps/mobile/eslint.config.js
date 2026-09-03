const expoConfig = require("eslint-config-expo/flat");
const { defineConfig } = require("eslint/config");

module.exports = defineConfig([
  expoConfig,
  {
    // .expo is Expo's own build/type-generation cache, not ours to lint -
    // the same reasoning frontend/eslint.config.mjs applies to .next.
    ignores: ["dist/**", ".expo/**", "node_modules/**"],
  },
  {
    rules: {
      // This rule (from eslint-plugin-react-hooks' React Compiler-era
      // preset) objects to the plain fetch-on-mount-then-setState pattern
      // used throughout this app's screens - exactly the approach the
      // mobile plan deliberately chose over pulling in a data-fetching
      // library for this first slice. Its own fix is to adopt such a
      // library or Suspense-based fetching, which is a real architectural
      // change, not a code-shape fix - contorting every screen to dodge a
      // static-analysis heuristic would be the "clever code" CLAUDE.md
      // warns against. Kept as a warning rather than off: it's still worth
      // a human glancing at when a genuinely careless case shows up.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
]);
