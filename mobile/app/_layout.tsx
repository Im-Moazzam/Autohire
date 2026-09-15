import "../global.css";
import { QueryClientProvider } from "@tanstack/react-query";
import { Redirect, Slot, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { Platform } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { useCurrentRecruiter } from "../lib/auth";
import { queryClient } from "../lib/query-client";
import { WebViewBridge } from "../lib/webviewBridge";
import { ScreenLoading } from "../components/ui";

// Web already carries the httponly cookie automatically via a real
// browser's credentials: "include" fetch — the bridge WebView is a
// native-only workaround, see lib/webviewBridge.tsx.
const NativeBridge = Platform.OS !== "web" ? WebViewBridge : () => null;

function AuthGate() {
  const segments = useSegments();
  const { data: recruiter, isLoading } = useCurrentRecruiter();
  const onLoginScreen = segments[0] === "login";

  if (isLoading) return <ScreenLoading />;
  if (!recruiter && !onLoginScreen) return <Redirect href="/login" />;
  if (recruiter && onLoginScreen) return <Redirect href="/" />;

  return <Slot />;
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <StatusBar style="dark" />
        <NativeBridge />
        <AuthGate />
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
