import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Platform, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { WebViewNavigation } from "react-native-webview";
import { Button, EmptyState } from "../components/ui";
import { authCompleteUrlPattern, googleLoginUrl } from "../lib/config";

// WebView IS bundled in Expo Go (confirmed — it's part of Expo Go's
// included native modules, unlike a third-party cookie-manager, which
// isn't and crashes on import there). Still guarded for the web-preview
// target, where a real Google sign-in can't run in a browser tab anyway.
const WebView =
  Platform.OS !== "web" ? require("react-native-webview").default : null;

type Phase = "welcome" | "webview" | "error";

export default function Login() {
  const [phase, setPhase] = useState<Phase>("welcome");
  const queryClient = useQueryClient();

  if (Platform.OS === "web") {
    return (
      <SafeAreaView className="flex-1 bg-canvas">
        <EmptyState
          title="Sign in on your phone"
          description="Google sign-in runs through a native WebView and isn't available in this browser preview. Open the app in Expo Go to sign in for real."
        />
      </SafeAreaView>
    );
  }

  function handleNavigation(nav: WebViewNavigation) {
    if (nav.url.includes("/auth/error")) {
      setPhase("error");
      return;
    }
    if (!nav.url.includes(authCompleteUrlPattern)) return;

    // No cookie to read or store here — the hidden bridge WebView
    // (mobile/lib/webviewBridge.tsx) shares this same WebView's cookie
    // jar automatically, so it's already authenticated. Just re-check who
    // we are; AuthGate in app/_layout.tsx redirects away from /login once
    // useCurrentRecruiter resolves to a real recruiter.
    queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
  }

  if (phase === "webview") {
    return (
      <SafeAreaView className="flex-1 bg-canvas" edges={["top"]}>
        <WebView
          source={{ uri: googleLoginUrl }}
          onNavigationStateChange={handleNavigation}
          startInLoadingState
        />
      </SafeAreaView>
    );
  }

  if (phase === "error") {
    return (
      <SafeAreaView className="flex-1 bg-canvas">
        <EmptyState
          variant="error"
          title="Sign-in didn't complete"
          description="Something went wrong finishing Google sign-in. Check that your phone and this app's backend are on the same network, then try again."
          actionLabel="Try again"
          onAction={() => setPhase("welcome")}
        />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 items-center justify-center gap-6 bg-canvas px-8">
      <View className="h-16 w-16 items-center justify-center rounded-2xl bg-primary">
        <Text className="text-2xl font-extrabold text-white">A</Text>
      </View>
      <View className="items-center gap-2">
        <Text className="text-page font-semibold text-ink">AutoHire</Text>
        <Text className="text-center text-body text-muted">
          Check your jobs, candidates, interviews, and emails on the go.
        </Text>
      </View>
      <View className="w-full">
        <Button
          label="Sign in with Google"
          onPress={() => setPhase("webview")}
        />
      </View>
    </SafeAreaView>
  );
}
