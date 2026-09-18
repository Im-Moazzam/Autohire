import * as Clipboard from "expo-clipboard";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ScreenLoading,
  SectionLabel,
} from "../../../../components/ui";
import { apiErrorMessage } from "../../../../lib/http";
import {
  JOB_STATUS_COLORS,
  JOB_STATUS_LABELS,
  useJob,
} from "../../../../lib/jobs";

export default function JobDetailScreen() {
  const { jobId } = useLocalSearchParams<{ jobId: string }>();
  const router = useRouter();
  const job = useJob(jobId);
  const [copied, setCopied] = useState(false);

  if (job.isLoading) return <ScreenLoading />;

  if (job.isError || !job.data) {
    return (
      <SafeAreaView className="flex-1 bg-canvas" edges={["bottom"]}>
        <EmptyState
          variant="error"
          title="Couldn't load this job"
          description={apiErrorMessage(job.error)}
          actionLabel="Retry"
          onAction={() => job.refetch()}
        />
      </SafeAreaView>
    );
  }

  const data = job.data;

  async function copyLink() {
    await Clipboard.setStringAsync(data.apply_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <SafeAreaView className="flex-1 bg-canvas" edges={["bottom"]}>
      <ScrollView
        className="flex-1 px-4"
        contentContainerClassName="gap-4 py-4"
      >
        <View className="flex-row items-start justify-between gap-2">
          <Text className="flex-1 text-page font-semibold text-ink">
            {data.job_title}
          </Text>
          <Badge
            label={JOB_STATUS_LABELS[data.status]}
            tone={JOB_STATUS_COLORS[data.status]}
          />
        </View>

        <View className="flex-row gap-3">
          <Card className="flex-1">
            <Text className="text-page font-semibold text-ink">
              {data.submission_count}
            </Text>
            <Text className="text-helper text-muted">Applications</Text>
          </Card>
          <Card className="flex-1">
            <Text className="text-card font-semibold text-ink">
              {new Date(data.expires_at).toLocaleDateString()}
            </Text>
            <Text className="text-helper text-muted">Closes</Text>
          </Card>
        </View>

        {data.is_accepting_responses ? (
          <Card>
            <SectionLabel>Application link</SectionLabel>
            <Text className="mb-3 text-body text-muted" numberOfLines={1}>
              {data.apply_url}
            </Text>
            <Button
              label={copied ? "Copied!" : "Copy application link"}
              onPress={copyLink}
              variant={copied ? "secondary" : "primary"}
            />
          </Card>
        ) : null}

        <Card>
          <SectionLabel>Description</SectionLabel>
          <Text className="text-body text-ink">{data.job_description}</Text>
        </Card>

        <Button
          label="View candidates"
          variant="secondary"
          onPress={() => router.push(`/jobs/${data.job_id}/candidates`)}
        />
      </ScrollView>
    </SafeAreaView>
  );
}
