import { Outlet } from 'react-router-dom'

/**
 * Authenticated recruiter shell. Sidebar/PageHeader land with the first real
 * screen story — this is just the route boundary they'll hang off.
 */
export function AppShell() {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <Outlet />
    </div>
  )
}
