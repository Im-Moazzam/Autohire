import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "./components/app/AppShell";
import { PublicLayout } from "./components/app/PublicLayout";
import { Home } from "./pages/Home";
import { Apply } from "./pages/Apply";

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
  {
    element: <AppShell />,
    children: [{ path: "/", element: <Home /> }],
  },
  {
    element: <PublicLayout />,
    children: [{ path: "/apply/:slug", element: <Apply /> }],
  },
  ...devRoutes,
]);
