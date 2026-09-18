import { useRef } from "react";
import { StyleSheet } from "react-native";
import WebView, { type WebViewMessageEvent } from "react-native-webview";
import { API_ORIGIN } from "./config";

/** Why this exists: the backend's session cookie is httponly, so it can
 * never be read by JS — not even inside the WebView's own page. Any *native*
 * module that reads it (cookie-manager libraries) requires custom native
 * code, which Expo Go's app binary doesn't ship (it only bundles the Expo
 * SDK itself) — that's exactly what crashed on a real device.
 *
 * The fix needs no native code at all: keep one persistent, invisible
 * WebView loaded on the API's origin. Since it shares the same app-level
 * cookie jar as the visible login WebView (same origin, same app, default
 * WKWebsiteDataStore/CookieManager — no special config), a `fetch()` run
 * *inside* that WebView's own page context carries the httponly cookie
 * automatically, exactly the way a real browser tab does for the web app.
 * We just relay the request/response across the JS bridge instead of
 * reading the cookie value into React Native at all.
 *
 * Module-level (not React Context) because lib/http.ts's request() is
 * called from TanStack Query's queryFn callbacks, not component render
 * bodies — there's no hook call site to thread a context value through. */

type PendingRequest = {
  resolve: (value: { status: number; body: unknown }) => void;
  reject: (err: Error) => void;
};

const pending = new Map<string, PendingRequest>();
let nextId = 0;
let webviewRef: WebView | null = null;
let readyWaiters: Array<() => void> = [];
let isReady = false;

function markReady() {
  isReady = true;
  readyWaiters.forEach((resolve) => resolve());
  readyWaiters = [];
}

function waitUntilReady(): Promise<void> {
  if (isReady) return Promise.resolve();
  return new Promise((resolve) => readyWaiters.push(resolve));
}

function onMessage(event: WebViewMessageEvent) {
  let parsed: { id: string; status?: number; body?: unknown; error?: string };
  try {
    parsed = JSON.parse(event.nativeEvent.data);
  } catch {
    return;
  }
  const entry = pending.get(parsed.id);
  if (!entry) return;
  pending.delete(parsed.id);
  if (parsed.error) {
    entry.reject(new Error(parsed.error));
  } else {
    entry.resolve({ status: parsed.status ?? 0, body: parsed.body });
  }
}

export async function bridgeRequest(
  path: string,
  init?: RequestInit,
): Promise<{ status: number; body: unknown }> {
  await waitUntilReady();
  return new Promise((resolve, reject) => {
    if (!webviewRef) {
      reject(new Error("Bridge WebView not mounted"));
      return;
    }
    const id = String(nextId++);
    pending.set(id, { resolve, reject });

    // One JSON blob for the whole call, decoded inside the injected script
    // — far less error-prone than hand-splicing each field into the JS
    // source as a separate serialized fragment.
    const call = JSON.stringify({
      id,
      url: `${API_ORIGIN}${path}`,
      method: init?.method ?? "GET",
      headers: { "Content-Type": "application/json", ...init?.headers },
      body: init?.body,
    });

    const script = `
      (function () {
        var call = ${call};
        fetch(call.url, {
          method: call.method,
          credentials: "include",
          headers: call.headers,
          body: call.body,
        })
          .then(function (res) {
            return res.text().then(function (text) {
              var parsedBody = null;
              try { parsedBody = text ? JSON.parse(text) : null; } catch (e) {}
              window.ReactNativeWebView.postMessage(JSON.stringify({ id: call.id, status: res.status, body: parsedBody }));
            });
          })
          .catch(function (err) {
            window.ReactNativeWebView.postMessage(JSON.stringify({ id: call.id, error: String(err) }));
          });
      })();
      true;
    `;
    webviewRef.injectJavaScript(script);
  });
}

/** Mount once, near the root — see mobile/app/_layout.tsx. */
export function WebViewBridge() {
  const ref = useRef<WebView>(null);

  return (
    <WebView
      ref={(instance) => {
        ref.current = instance;
        webviewRef = instance;
      }}
      source={{ uri: `${API_ORIGIN}/docs` }}
      onLoadEnd={markReady}
      onMessage={onMessage}
      style={styles.hidden}
    />
  );
}

const styles = StyleSheet.create({
  // Not `display: none` — some WebView implementations pause/never load a
  // display:none view. 1x1 and clipped off-screen keeps it fully alive.
  hidden: { position: "absolute", top: -1000, left: 0, width: 1, height: 1 },
});
