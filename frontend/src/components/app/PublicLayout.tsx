import { Outlet } from "react-router-dom";

/**
 * Bare shell for candidate-facing pages (e.g. /apply/{slug}) — no sidebar,
 * no recruiter chrome, per docs/design.md "Screens not covered by Stitch".
 */
export function PublicLayout() {
  return (
    <div className="min-h-screen bg-canvas text-ink flex justify-center">
      <div className="w-full max-w-[640px] px-4 py-12">
        <Outlet />
      </div>
    </div>
  );
}
