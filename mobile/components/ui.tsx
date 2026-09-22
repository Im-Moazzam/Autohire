import { Ionicons } from "@expo/vector-icons";
import { ReactNode, useState } from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";

/** Same palette as docs/design.md / frontend/src/styles/tokens.css, keyed by
 * the generic names lib/*.ts already uses (JOB_STATUS_COLORS etc.) so a
 * status maps to a badge tone in one lookup, no per-screen switch statements. */
const TONE_CLASSES: Record<string, { bg: string; text: string }> = {
  primary: { bg: "bg-primary/10", text: "text-primary" },
  navy: { bg: "bg-navy/10", text: "text-navy" },
  cyan: { bg: "bg-cyan/10", text: "text-cyan" },
  ai: { bg: "bg-ai/10", text: "text-ai" },
  success: { bg: "bg-success/10", text: "text-success" },
  warning: { bg: "bg-warning/10", text: "text-warning" },
  error: { bg: "bg-error/10", text: "text-error" },
  muted: { bg: "bg-muted/10", text: "text-muted" },
};

const TONE_HEX: Record<string, string> = {
  primary: "#0058BE",
  navy: "#0F172A",
  cyan: "#06B6D4",
  ai: "#7C3AED",
  success: "#16A34A",
  warning: "#F59E0B",
  error: "#DC2626",
  muted: "#64748B",
};

export function Badge({
  label,
  tone = "muted",
}: {
  label: string;
  tone?: string;
}) {
  const { bg, text } = TONE_CLASSES[tone] ?? TONE_CLASSES.muted;
  return (
    <View className={`self-start rounded-full px-2.5 py-1 ${bg}`}>
      <Text className={`text-helper font-semibold ${text}`}>{label}</Text>
    </View>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <View
      className={`rounded-card border border-border bg-surface p-4 shadow-sm ${className}`}
    >
      {children}
    </View>
  );
}

export function PressableCard({
  children,
  onPress,
  className = "",
  chevron = true,
}: {
  children: ReactNode;
  onPress: () => void;
  className?: string;
  chevron?: boolean;
}) {
  const [pressed, setPressed] = useState(false);
  return (
    <Pressable
      onPress={onPress}
      onPressIn={() => setPressed(true)}
      onPressOut={() => setPressed(false)}
      className={`rounded-card border border-border bg-surface p-4 shadow-sm ${pressed ? "opacity-60" : ""} ${className}`}
    >
      <View className="flex-row items-center gap-2">
        <View className="flex-1">{children}</View>
        {chevron ? (
          <Ionicons name="chevron-forward" size={18} color="#94A3B8" />
        ) : null}
      </View>
    </Pressable>
  );
}

export function Avatar({
  name,
  size = 40,
  tone = "primary",
}: {
  name: string;
  size?: number;
  tone?: string;
}) {
  const initial = name?.trim()?.[0]?.toUpperCase() ?? "?";
  const { bg, text } = TONE_CLASSES[tone] ?? TONE_CLASSES.primary;
  return (
    <View
      style={{ width: size, height: size, borderRadius: size / 2 }}
      className={`items-center justify-center ${bg}`}
    >
      <Text
        style={{ fontSize: size * 0.42 }}
        className={`font-semibold ${text}`}
      >
        {initial}
      </Text>
    </View>
  );
}

export function IconBubble({
  name,
  tone = "primary",
  size = 36,
}: {
  name: keyof typeof Ionicons.glyphMap;
  tone?: string;
  size?: number;
}) {
  const { bg } = TONE_CLASSES[tone] ?? TONE_CLASSES.primary;
  return (
    <View
      style={{ width: size, height: size, borderRadius: size / 2 }}
      className={`items-center justify-center ${bg}`}
    >
      <Ionicons
        name={name}
        size={size * 0.52}
        color={TONE_HEX[tone] ?? TONE_HEX.primary}
      />
    </View>
  );
}

type ButtonVariant = "primary" | "secondary" | "warning" | "destructive";

const BUTTON_CLASSES: Record<ButtonVariant, string> = {
  primary: "bg-primary",
  secondary: "bg-surface border border-border",
  warning: "bg-warning",
  destructive: "bg-error",
};

const BUTTON_TEXT_CLASSES: Record<ButtonVariant, string> = {
  primary: "text-white",
  secondary: "text-navy",
  warning: "text-white",
  destructive: "text-white",
};

export function Button({
  label,
  onPress,
  variant = "primary",
  loading = false,
  disabled = false,
  icon,
}: {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  loading?: boolean;
  disabled?: boolean;
  icon?: ReactNode;
}) {
  const isDisabled = disabled || loading;
  const [pressed, setPressed] = useState(false);
  return (
    <Pressable
      onPress={onPress}
      onPressIn={() => setPressed(true)}
      onPressOut={() => setPressed(false)}
      disabled={isDisabled}
      className={`flex-row items-center justify-center gap-2 rounded-control px-4 py-3 ${BUTTON_CLASSES[variant]} ${
        isDisabled ? "opacity-50" : pressed ? "opacity-80" : ""
      }`}
    >
      {loading ? (
        <ActivityIndicator
          color={variant === "secondary" ? "#0F172A" : "#FFFFFF"}
          size="small"
        />
      ) : (
        icon
      )}
      <Text
        className={`text-body font-semibold ${BUTTON_TEXT_CLASSES[variant]}`}
      >
        {label}
      </Text>
    </Pressable>
  );
}

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  variant = "empty",
}: {
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  variant?: "empty" | "error" | "info";
}) {
  const iconName =
    variant === "error"
      ? "alert-circle-outline"
      : variant === "info"
        ? "information-circle-outline"
        : "file-tray-outline";

  return (
    <View className="flex-1 items-center justify-center gap-3 px-8 py-16">
      <View
        className={`h-14 w-14 items-center justify-center rounded-full ${
          variant === "error" ? "bg-error/10" : "bg-primary-soft"
        }`}
      >
        <Ionicons
          name={iconName}
          size={28}
          color={variant === "error" ? "#DC2626" : "#0058BE"}
        />
      </View>
      <Text className="text-center text-card font-semibold text-ink">
        {title}
      </Text>
      {description ? (
        <Text className="text-center text-body text-muted">{description}</Text>
      ) : null}
      {actionLabel && onAction ? (
        <View className="mt-2">
          <Button
            label={actionLabel}
            onPress={onAction}
            variant={variant === "error" ? "secondary" : "primary"}
          />
        </View>
      ) : null}
    </View>
  );
}

export function ScreenLoading() {
  return (
    <View className="flex-1 items-center justify-center bg-canvas">
      <ActivityIndicator size="large" color="#0058BE" />
    </View>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <Text className="mb-2 text-helper font-semibold uppercase text-muted">
      {children}
    </Text>
  );
}
