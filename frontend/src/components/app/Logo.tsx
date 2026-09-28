import type { SVGProps } from "react";

/** The AutoHire mark — used in the app sidebar and the marketing header/footer.
 * Single source so the three places it appears never drift apart. */
export function Logo(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path
        d="M4 17 12 6 20 17"
        stroke="currentColor"
        strokeWidth={3.2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
