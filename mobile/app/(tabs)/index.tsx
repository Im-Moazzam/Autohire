import { useMemo } from "react";
import { RefreshControl, ScrollView, Text, View } from "react-native";
import { BarChart, PieChart } from "react-native-gifted-charts";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  Badge,
  Card,
  EmptyState,
  ScreenLoading,
  SectionLabel,
} from "../../components/ui";
import { useCurrentRecruiter, useLogout } from "../../lib/auth";
import { topEntries, useDashboardStats } from "../../lib/dashboard";
import { apiErrorMessage } from "../../lib/http";
import {
  JOB_STATUS_COLORS,
  JOB_STATUS_LABELS,
  type JobStatus,
} from "../../lib/jobs";
import {
  SLOT_STATUS_COLORS,
  SLOT_STATUS_LABELS,
  type SlotStatus,
} from "../../lib/scheduling";
import {
  DELIVERY_STATUS_COLORS,
  DELIVERY_STATUS_LABELS,
  type DeliveryStatus,
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
}: {
  label: string;
  value: number;
  tone: keyof typeof HEX;
}) {
  return (
    <View className="flex-1 rounded-card border border-border bg-surface p-4">
      <Text className="text-page font-semibold text-ink">{value}</Text>
      <Text className="text-helper text-muted">{label}</Text>
      <View
        className="mt-2 h-1 w-8 rounded-full"
        style={{ backgroundColor: HEX[tone] }}
      />
    </View>
  );
}

function donutData(
  counts: Record<string, number>,
  colors: Record<string, string>,
) {
  return Object.entries(counts)
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({ value, color: HEX[colors[key] ?? "muted"] }));
}

export default function Dashboard() {
  const { data: recruiter } = useCurrentRecruiter();
  const stats = useDashboardStats();
  const logout = useLogout();

  const funnelData = useMemo(() => {
    if (!stats.data) return [];
    return FUNNEL_ORDER.map((key) => ({
      value:
        stats.data!.candidates_by_status[
          key as keyof typeof stats.data.candidates_by_status
        ] ?? 0,
      label: FUNNEL_LABELS[key],
      frontColor: FUNNEL_COLORS[key],
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
        <View className="flex-row items-start justify-between">
          <View>
            <Text className="text-page font-semibold text-ink">
              Hi, {recruiter?.name?.split(" ")[0]}
            </Text>
            <Text className="text-body text-muted">
              Your hiring pipeline, live.
            </Text>
          </View>
          <Text
            className="pt-1 text-helper font-semibold text-muted"
            onPress={() => logout.mutate()}
          >
            Sign out
          </Text>
        </View>

        <View className="flex-row gap-3">
          <KpiTile label="Jobs" value={data.total_jobs} tone="primary" />
          <KpiTile label="Candidates" value={data.total_candidates} tone="ai" />
        </View>
        <View className="-mt-3 flex-row gap-3">
          <KpiTile
            label="Interviews"
            value={data.total_interviews}
            tone="cyan"
          />
          <KpiTile label="Emails" value={data.total_emails} tone="success" />
        </View>

        <Card>
          <SectionLabel>Candidate pipeline</SectionLabel>
          {funnelData.some((d) => d.value > 0) ? (
            <BarChart
              data={funnelData}
              horizontal
              barWidth={22}
              spacing={18}
              hideRules
              hideYAxisText
              xAxisThickness={0}
              yAxisThickness={0}
              showValuesAsTopLabel
              topLabelTextStyle={{
                color: "#0F172A",
                fontSize: 12,
                fontWeight: "600",
              }}
              labelWidth={80}
              height={180}
            />
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
            total={data.total_jobs}
          />
          <DonutCard
            title="Interviews"
            counts={data.interviews_by_status}
            colors={SLOT_STATUS_COLORS}
            labels={SLOT_STATUS_LABELS as Record<string, string>}
            total={data.total_interviews}
          />
        </View>
        <DonutCard
          title="Email delivery"
          counts={data.emails_by_status}
          colors={DELIVERY_STATUS_COLORS}
          labels={DELIVERY_STATUS_LABELS as Record<string, string>}
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
  total,
  wide = false,
}: {
  title: string;
  counts: Record<string, number>;
  colors: Record<string, string>;
  labels: Record<string, string>;
  total: number;
  wide?: boolean;
}) {
  const data = donutData(counts, colors);
  const top = topEntries(counts, 4);

  return (
    <Card className={wide ? "flex-1" : "flex-1"}>
      <SectionLabel>{title}</SectionLabel>
      <View className="flex-row items-center gap-4">
        {total > 0 ? (
          <PieChart
            data={data}
            donut
            radius={44}
            innerRadius={30}
            centerLabelComponent={() => (
              <Text className="text-card font-semibold text-ink">{total}</Text>
            )}
          />
        ) : (
          <View className="h-[88px] w-[88px] items-center justify-center rounded-full border-4 border-border">
            <Text className="text-card font-semibold text-muted">0</Text>
          </View>
        )}
        <View className="flex-1 gap-1.5">
          {top.length > 0 ? (
            top.map(([key, count]) => (
              <Badge
                key={key}
                label={`${labels[key] ?? key} · ${count}`}
                tone={colors[key]}
              />
            ))
          ) : (
            <Text className="text-helper text-muted">No data yet</Text>
          )}
        </View>
      </View>
    </Card>
  );
}
