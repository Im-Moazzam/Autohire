import { Ionicons } from "@expo/vector-icons";
import { useMemo, useState } from "react";
import {
  Modal,
  Pressable,
  RefreshControl,
  ScrollView,
  Text,
  View,
} from "react-native";
import { PieChart } from "react-native-gifted-charts";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  Avatar,
  Card,
  EmptyState,
  IconBubble,
  ScreenLoading,
  SectionLabel,
} from "../../components/ui";
import { useCurrentRecruiter, useLogout } from "../../lib/auth";
import { topEntries, useDashboardStats } from "../../lib/dashboard";
import { apiErrorMessage } from "../../lib/http";
import { JOB_STATUS_COLORS, JOB_STATUS_DESCRIPTIONS, JOB_STATUS_LABELS } from "../../lib/jobs";
import {
  SLOT_STATUS_COLORS,
  SLOT_STATUS_DESCRIPTIONS,
  SLOT_STATUS_LABELS,
} from "../../lib/scheduling";
import {
  DELIVERY_STATUS_COLORS,
  DELIVERY_STATUS_DESCRIPTIONS,
  DELIVERY_STATUS_LABELS,
} from "../../lib/emails";

const HEX: Record<string, string> = {
  primary: "#0058BE",
  navy: "#0F172A",
  cyan: "#06B6D4",
  ai: "#7C3AED",
  success: "#16A34A",
  warning: "#F59E0B",
  error: "#DC2626",
  muted: "#94A3B8",
};

const FUNNEL_ORDER = [
  "SUBMITTED",
  "PARSED",
  "RANKED",
  "INVITED",
  "CONFIRMED",
] as const;
const FUNNEL_LABELS: Record<string, string> = {
  SUBMITTED: "Submitted",
  PARSED: "Parsed",
  RANKED: "Ranked",
  INVITED: "Invited",
  CONFIRMED: "Confirmed",
};
const FUNNEL_COLORS: Record<string, string> = {
  SUBMITTED: HEX.primary,
  PARSED: HEX.cyan,
  RANKED: HEX.ai,
  INVITED: HEX.navy,
  CONFIRMED: HEX.success,
};

function KpiTile({
  label,
  value,
  tone,
  icon,
}: {
  label: string;
  value: number;
  tone: keyof typeof HEX;
  icon: keyof typeof import("@expo/vector-icons").Ionicons.glyphMap;
}) {
  return (
    <View className="flex-1 gap-2 rounded-card border border-border bg-surface p-4">
      <IconBubble name={icon} tone={tone} size={32} />
      <Text className="text-page font-semibold text-ink">{value}</Text>
      <Text className="text-helper text-muted">{label}</Text>
    </View>
  );
}

/** Plain Views scaled by percentage width instead of react-native-gifted-charts'
 * BarChart — that needed barWidth/spacing/labelWidth/height hand-tuned in pixels
 * to avoid clipping the last bar or overlapping labels on a real phone; a flex
 * bar can't overflow its row no matter the screen width. */
function FunnelBars({
  data,
}: {
  data: { label: string; value: number; color: string }[];
}) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <View className="gap-3">
      {data.map((d) => (
        <View key={d.label} className="flex-row items-center gap-3">
          <Text className="w-20 text-helper text-muted" numberOfLines={1}>
            {d.label}
          </Text>
          <View className="h-2.5 flex-1 overflow-hidden rounded-full bg-border">
            {d.value > 0 ? (
              <View
                className="h-full rounded-full"
                style={{
                  width: `${Math.max((d.value / max) * 100, 6)}%`,
                  backgroundColor: d.color,
                }}
              />
            ) : null}
          </View>
          <Text className="w-6 text-right text-helper font-semibold text-ink">
            {d.value}
          </Text>
        </View>
      ))}
    </View>
  );
}

/** Dot + label + count legend, one line each — replaces stacking status Badge
 * pills as a legend, which reads as a wall of pills rather than a legend. */
function Legend({
  items,
}: {
  items: { label: string; count: number; tone: string }[];
}) {
  if (items.length === 0) {
    return <Text className="text-helper text-muted">No data yet</Text>;
  }
  return (
    <View className="flex-1 gap-2">
      {items.map((item) => (
        <View key={item.label} className="flex-row items-center gap-2">
          <View
            className="h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: HEX[item.tone] ?? HEX.muted }}
          />
          <Text className="flex-1 text-helper text-ink" numberOfLines={1}>
            {item.label}
          </Text>
          <Text className="text-helper font-semibold text-muted">
            {item.count}
          </Text>
        </View>
      ))}
    </View>
  );
}

export default function Dashboard() {
  const { data: recruiter } = useCurrentRecruiter();
  const stats = useDashboardStats();
  const logout = useLogout();

  const funnelData = useMemo(() => {
    if (!stats.data) return [];
    return FUNNEL_ORDER.map((key) => ({
      label: FUNNEL_LABELS[key],
      value:
        stats.data!.candidates_by_status[
          key as keyof typeof stats.data.candidates_by_status
        ] ?? 0,
      color: FUNNEL_COLORS[key],
    }));
  }, [stats.data]);

  if (stats.isLoading) return <ScreenLoading />;

  if (stats.isError) {
    return (
      <SafeAreaView className="flex-1 bg-canvas">
        <EmptyState
          variant="error"
          title="Couldn't load your dashboard"
          description={apiErrorMessage(stats.error)}
          actionLabel="Retry"
          onAction={() => stats.refetch()}
        />
      </SafeAreaView>
    );
  }

  const data = stats.data!;

  if (data.total_jobs === 0) {
    return (
      <SafeAreaView className="flex-1 bg-canvas">
        <EmptyState
          title="Welcome to AutoHire"
          description="Once you post a job on the web app, your live stats will show up here."
        />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-canvas" edges={["top"]}>
      <ScrollView
        className="flex-1 px-4"
        contentContainerClassName="gap-6 pb-10 pt-2"
        refreshControl={
          <RefreshControl
            refreshing={stats.isFetching}
            onRefresh={() => stats.refetch()}
          />
        }
      >
        <View className="flex-row items-center justify-between">
          <View className="flex-row items-center gap-3">
            <Avatar name={recruiter?.name ?? "?"} />
            <View>
              <Text className="text-page font-semibold text-ink">
                Hi, {recruiter?.name?.split(" ")[0]}
              </Text>
              <Text className="text-body text-muted">
                Your hiring pipeline, live.
              </Text>
            </View>
          </View>
          <Text
            className="text-helper font-semibold text-muted"
            onPress={() => logout.mutate()}
          >
            Sign out
          </Text>
        </View>

        <View className="flex-row gap-3">
          <KpiTile
            label="Jobs"
            value={data.total_jobs}
            tone="primary"
            icon="briefcase-outline"
          />
          <KpiTile
            label="Candidates"
            value={data.total_candidates}
            tone="ai"
            icon="people-outline"
          />
        </View>
        <View className="flex-row gap-3">
          <KpiTile
            label="Interviews"
            value={data.total_interviews}
            tone="cyan"
            icon="videocam-outline"
          />
          <KpiTile
            label="Emails"
            value={data.total_emails}
            tone="success"
            icon="mail-outline"
          />
        </View>

        <Card>
          <SectionLabel>Candidate pipeline</SectionLabel>
          {funnelData.some((d) => d.value > 0) ? (
            <FunnelBars data={funnelData} />
          ) : (
            <Text className="text-body text-muted">No candidates yet.</Text>
          )}
        </Card>

        <View className="flex-row gap-3">
          <DonutCard
            title="Jobs"
            counts={data.jobs_by_status}
            colors={JOB_STATUS_COLORS}
            labels={JOB_STATUS_LABELS as Record<string, string>}
            descriptions={JOB_STATUS_DESCRIPTIONS as Record<string, string>}
            total={data.total_jobs}
          />
          <DonutCard
            title="Interviews"
            counts={data.interviews_by_status}
            colors={SLOT_STATUS_COLORS}
            labels={SLOT_STATUS_LABELS as Record<string, string>}
            descriptions={SLOT_STATUS_DESCRIPTIONS as Record<string, string>}
            total={data.total_interviews}
          />
        </View>
        <DonutCard
          title="Email delivery"
          counts={data.emails_by_status}
          colors={DELIVERY_STATUS_COLORS}
          labels={DELIVERY_STATUS_LABELS as Record<string, string>}
          descriptions={
            DELIVERY_STATUS_DESCRIPTIONS as Record<string, string>
          }
          total={data.total_emails}
          wide
        />
      </ScrollView>
    </SafeAreaView>
  );
}

function DonutCard({
  title,
  counts,
  colors,
  labels,
  descriptions,
  total,
  wide = false,
}: {
  title: string;
  counts: Record<string, number>;
  colors: Record<string, string>;
  labels: Record<string, string>;
  descriptions: Record<string, string>;
  total: number;
  wide?: boolean;
}) {
  const [open, setOpen] = useState(false);

  // Every nonzero status, largest first — the same order and the same
  // color lookup feed both the pie slices and the legend rows below, so
  // the biggest wedge (drawn first, from 12 o'clock clockwise) is always
  // legend row 1. Previously the legend was capped to topEntries(4) while
  // the pie plotted every status in raw object order, so a 5th status
  // (scheduling has 5) could paint a wedge with no matching legend row.
  const entries = topEntries(counts, Object.keys(colors).length);
  const data = entries.map(([key, value]) => ({
    value,
    color: HEX[colors[key] ?? "muted"],
  }));
  const legendItems = entries.map(([key, count]) => ({
    key,
    label: labels[key] ?? key,
    count,
    tone: colors[key],
  }));
  const radius = wide ? 52 : 44;
  const innerRadius = wide ? 36 : 30;

  return (
    <>
      <Pressable
        className="flex-1"
        onPress={() => setOpen(true)}
        disabled={total === 0}
      >
        <Card className="flex-1">
          <View className="flex-row items-center justify-between">
            <SectionLabel>{title}</SectionLabel>
            {total > 0 ? (
              <Ionicons
                name="information-circle-outline"
                size={16}
                color="#94A3B8"
              />
            ) : null}
          </View>
          <View
            className={`flex-row items-center ${wide ? "gap-6" : "gap-4"}`}
          >
            {total > 0 ? (
              <PieChart
                data={data}
                donut
                radius={radius}
                innerRadius={innerRadius}
                centerLabelComponent={() => (
                  <Text className="text-card font-semibold text-ink">
                    {total}
                  </Text>
                )}
              />
            ) : (
              <View
                style={{ height: radius * 2, width: radius * 2 }}
                className="items-center justify-center rounded-full border-4 border-border"
              >
                <Text className="text-card font-semibold text-muted">0</Text>
              </View>
            )}
            <Legend items={legendItems} />
          </View>
        </Card>
      </Pressable>

      <Modal
        visible={open}
        transparent
        animationType="slide"
        onRequestClose={() => setOpen(false)}
      >
        <Pressable
          className="flex-1 justify-end bg-navy/40"
          onPress={() => setOpen(false)}
        >
          <Pressable
            className="gap-4 rounded-t-xl bg-surface p-6"
            onPress={(e) => e.stopPropagation()}
          >
            <View className="flex-row items-center justify-between">
              <Text className="text-card font-semibold text-ink">
                {title} · what each status means
              </Text>
              <Pressable onPress={() => setOpen(false)} hitSlop={12}>
                <Ionicons name="close" size={22} color="#64748B" />
              </Pressable>
            </View>
            <View className="gap-4">
              {legendItems.map((item) => (
                <View key={item.key} className="flex-row items-start gap-3">
                  <View
                    className="mt-1.5 h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: HEX[item.tone] ?? HEX.muted }}
                  />
                  <View className="flex-1">
                    <View className="flex-row items-center justify-between">
                      <Text className="text-body font-semibold text-ink">
                        {item.label}
                      </Text>
                      <Text className="text-body font-semibold text-muted">
                        {item.count}
                      </Text>
                    </View>
                    <Text className="text-helper text-muted">
                      {descriptions[item.key] ?? ""}
                    </Text>
                  </View>
                </View>
              ))}
            </View>
          </Pressable>
        </Pressable>
      </Modal>
    </>
  );
}
