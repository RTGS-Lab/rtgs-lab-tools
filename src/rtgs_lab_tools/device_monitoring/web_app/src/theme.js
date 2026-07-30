// Shared visual tokens for the dashboard's chrome: page/card surfaces, borders,
// text and accent colors, the type scale, and the two font stacks.
//
// Diagnostic colors deliberately do NOT live here. Battery / system / humidity
// gauge colors come from utils.js, and the NEEDS ATTN / ALL GOOD / CRITICAL /
// error-code colors are written at their call sites. Those encode meaning and
// are kept exactly as they were.

export const font = {
  sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  mono: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, 'Courier New', monospace",
};

// Type scale. Every step is 2-3px larger than the previous dark theme so the
// smallest labels ("BATTERY", sensor names like "Talon-I2C [2]") stay legible,
// while the spread between steps is preserved.
export const size = {
  micro: 11, // was 9
  tiny: 12, // was 10
  xs: 13, // was 11
  sm: 14, // was 12
  base: 15, // was 13
  md: 16, // was 14
  lg: 17, // was 15
  xl: 18, // was 16
  h1: 27, // was 22
};

export const color = {
  // Surfaces
  pageBg: "#f6f7f9",
  surface: "#ffffff",
  surfaceHover: "#eef2f7",
  surfaceSunken: "#f1f4f8",

  // Lines
  border: "#dbe1e8",
  borderStrong: "#c3ccd6",
  divider: "#e7ebf0",

  // Text, darkest to lightest
  text: "#151b23", // headings, product names, data values
  textMuted: "#54606d", // field labels, prose
  textFaint: "#79838f", // footer, timestamps in meta position
  decor: "#a6b0bb", // arrows, eyebrow rules — decoration only

  // Accents. Three hues keep the section cards visually distinct the way the
  // old sky / violet / blue accents did, all at >=5:1 contrast on white.
  accent: "#0f4c81",
  accentTint: "#e9f0f7",
  violet: "#6d28d9",
  violetTint: "#f2ecfd",
  teal: "#0e7490",
  tealTint: "#e5f1f5",
};

// Cards sit on an off-white page, so they need a hairline shadow to read as
// raised rather than relying on a background contrast the way the dark UI did.
export const cardShadow = "0 1px 2px rgba(16, 24, 40, 0.05)";
