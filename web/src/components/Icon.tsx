/**
 * Small monochrome line icons drawn inline: no icon font, no requests, and they take the colour of
 * the text around them (`currentColor`), so they follow the fixed palette. Square caps and mitred
 * joins match the site's square geometry. Purely decorative: always hidden from assistive tech,
 * the text next to each icon carries the meaning.
 */
const PATHS = {
  // A scout's crosshair: 真實實力 looks through the noise at the real player.
  scout: (
    <>
      <circle cx="12" cy="12" r="7.5" />
      <circle cx="12" cy="12" r="2.5" />
      <path d="M12 1.5v4M12 18.5v4M1.5 12h4M18.5 12h4" />
    </>
  ),
  // The diamond with its three bases and home plate: the lineup lab.
  diamond: (
    <>
      <path d="M12 3.5 20.5 12 12 20.5 3.5 12Z" />
      <path d="M10.6 3.5h2.8v2.8h-2.8zM18.2 10.6h2.8v2.8h-2.8zM3 10.6h2.8v2.8H3zM10.6 18h2.8v2.8h-2.8z" />
    </>
  ),
  trophy: (
    <>
      <path d="M7 3.5h10v5a5 5 0 0 1-10 0Z" />
      <path d="M7 5.5H3.5v1.5A3.5 3.5 0 0 0 7 10.5M17 5.5h3.5v1.5a3.5 3.5 0 0 1-3.5 3.5" />
      <path d="M12 13.5v4M8 20.5h8M9.5 17.5h5v3h-5z" />
    </>
  ),
  shield: (
    <>
      <path d="M12 2.5 20 5.5v6c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10v-6Z" />
      <path d="m8.2 12 2.6 2.6 5-5" />
    </>
  ),
  compare: (
    <>
      <path d="M4 7.5h14M14.5 4 18 7.5 14.5 11" />
      <path d="M20 16.5H6M9.5 13 6 16.5 9.5 20" />
    </>
  ),
  // A baseball with its two seams.
  ball: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M7.3 4.9c1.8 2 2.7 4.4 2.7 7.1s-.9 5.1-2.7 7.1M16.7 4.9c-1.8 2-2.7 4.4-2.7 7.1s.9 5.1 2.7 7.1" />
    </>
  ),
  up: <path d="M3 17.5 9 11.5l4 4 8-8M15.5 7.5H21V13" />,
  down: <path d="M3 6.5 9 12.5l4-4 8 8M15.5 16.5H21V11" />,
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m15.5 15.5 5.5 5.5" />
    </>
  ),
  chart: <path d="M3.5 20.5h17M6.5 17V11M11 17V5.5M15.5 17v-8M20 17v-4" />,
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 18, className }: { name: IconName; size?: number; className?: string }) {
  return (
    <svg
      className={className ? `icon ${className}` : "icon"}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="square"
      strokeLinejoin="miter"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}
