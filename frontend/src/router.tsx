import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "./components/app/AppShell";
import { PublicLayout } from "./components/app/PublicLayout";
import { Home } from "./pages/Home";
import { Apply } from "./pages/Apply";
import { Dashboard } from "./pages/Dashboard";
import { AuthError } from "./pages/AuthError";

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
  {
    element: <AppShell />,
    children: [
      { path: "/dashboard", element: <Dashboard /> },
      { path: "/auth/error", element: <AuthError /> },
    ],
  },
  {
    element: <PublicLayout />,
    children: [{ path: "/apply/:slug", element: <Apply /> }],
  },
  ...devRoutes,
]);
