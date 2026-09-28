import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "./components/app/AppShell";
import { AdminShell } from "./components/app/AdminShell";
import { PublicLayout } from "./components/app/PublicLayout";
import { Home } from "./pages/Home";
import { Apply } from "./pages/Apply";
import { Dashboard } from "./pages/Dashboard";
import { AuthError } from "./pages/AuthError";
import { Templates } from "./pages/Templates";
import { TemplateBuilder } from "./pages/TemplateBuilder";
import { Jobs } from "./pages/Jobs";
import { JobBuilder } from "./pages/JobBuilder";
import { Candidates } from "./pages/Candidates";
import { Scheduling } from "./pages/Scheduling";
import { Emails } from "./pages/Emails";
import { Settings } from "./pages/Settings";
import { Admin } from "./pages/Admin";

const devRoutes = import.meta.env.DEV
  ? [
      {
        path: "/kitchen-sink",
        lazy: async () => {
          const { KitchenSink } = await import("./pages/KitchenSink");
          return { Component: KitchenSink };
        },
      },
    ]
  : [];

export const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  { path: "/auth/error", element: <AuthError /> },
  {
    element: <AppShell />,
    children: [
      { path: "/dashboard", element: <Dashboard /> },
      { path: "/templates", element: <Templates /> },
      { path: "/templates/new", element: <TemplateBuilder /> },
      { path: "/templates/:templateId/edit", element: <TemplateBuilder /> },
      { path: "/jobs", element: <Jobs /> },
      { path: "/jobs/new", element: <JobBuilder /> },
      { path: "/jobs/:jobId/edit", element: <JobBuilder /> },
      { path: "/jobs/:jobId/candidates", element: <Candidates /> },
      { path: "/scheduling", element: <Scheduling /> },
      { path: "/emails", element: <Emails /> },
      { path: "/settings", element: <Settings /> },
    ],
  },
  {
    // Deliberately not AppShell/Sidebar — a separate, hidden operator tool,
    // not another item inside the normal recruiter shell. Gated server-side
    // by get_current_admin and client-side by Admin's own redirect-on-403.
    // Reachable only by typing the URL.
    element: <AdminShell />,
    children: [{ path: "/admin", element: <Admin /> }],
  },
  {
    element: <PublicLayout />,
    children: [{ path: "/apply/:slug", element: <Apply /> }],
  },
  ...devRoutes,
]);
