import Constants from "expo-constants";
import { Platform } from "react-native";

/** The phone can't resolve "localhost" to the dev machine, so the API host
 * must be a real LAN IP. Set EXPO_PUBLIC_API_HOST in mobile/.env (see
 * mobile/.env.example) to your machine's LAN IP, found via `ipconfig`.
 * The browser web preview runs on the same machine as the API, and a LAN
 * IP is cross-site there (blocks SameSite=Lax cookies) — use localhost.
 *
 * Google OAuth rejects raw LAN IPs as a redirect_uri (public-domain-only
 * policy), so real-phone Google sign-in needs a tunnel (e.g. `ngrok http
 * api:8000`) instead. Set EXPO_PUBLIC_API_ORIGIN to the tunnel's full
 * https URL to use that instead of HOST/PORT — it's registered as the
 * Google Cloud Console redirect URI the same way a LAN IP would be. */
const API_HOST =
  Platform.OS === "web" ? "localhost" : process.env.EXPO_PUBLIC_API_HOST;
const API_PORT = process.env.EXPO_PUBLIC_API_PORT ?? "8000";

if (!process.env.EXPO_PUBLIC_API_ORIGIN && !API_HOST) {
  throw new Error(
    "Neither EXPO_PUBLIC_API_ORIGIN nor EXPO_PUBLIC_API_HOST is set — copy mobile/.env.example to mobile/.env (see mobile/README.md).",
  );
}

export const API_ORIGIN =
  process.env.EXPO_PUBLIC_API_ORIGIN ?? `http://${API_HOST}:${API_PORT}`;
export const API_URL = `${API_ORIGIN}/api/v1`;

/** Same redirect-chain login the web app uses (login -> Google consent ->
 * callback that sets an httponly session cookie) — see mobile/app/login.tsx
 * for how the WebView captures that cookie for use outside the WebView. */
export const googleLoginUrl = `${API_URL}/auth/google/login`;

/** The backend redirects here on a successful callback (settings.frontend_url,
 * default unchanged). The phone doesn't need this URL to actually load —
 * the WebView just needs to see navigation reach it to know auth is done. */
export const authCompleteUrlPattern = "/dashboard";

export const isExpoGo = Constants.appOwnership === "expo";
