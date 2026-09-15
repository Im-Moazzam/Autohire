import { useRouter } from "expo-router";
import { FlatList, RefreshControl, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  Badge,
  EmptyState,
  PressableCard,
  ScreenLoading,
} from "../../../components/ui";
import { apiErrorMessage } from "../../../lib/http";
import {
  JOB_STATUS_COLORS,
  JOB_STATUS_LABELS,
  useJobs,
  type Job,
} from "../../../lib/jobs";

export default function JobsList() {
  const router = useRouter();
  const jobs = useJobs();

  if (jobs.isLoading) return <ScreenLoading />;

  if (jobs.isError) {
    return (
      <SafeAreaView className="flex-1 bg-canvas" edges={["bottom"]}>
        <EmptyState
          variant="error"
          title="Couldn't load jobs"
          description={apiErrorMessage(jobs.error)}
          actionLabel="Retry"
          onAction={() => jobs.refetch()}
        />
      </SafeAreaView>
    );
  }

  const items = jobs.data?.items ?? [];

  return (
    <SafeAreaView className="flex-1 bg-canvas" edges={["bottom"]}>
      <FlatList
        data={items}
        keyExtractor={(job) => job.job_id}
        contentContainerClassName="gap-3 p-4"
        refreshControl={
          <RefreshControl
            refreshing={jobs.isFetching}
            onRefresh={() => jobs.refetch()}
          />
        }
        ListEmptyComponent={
          <EmptyState
            title="No jobs yet"
            description="Jobs you post on the web app will show up here."
          />
        }
        renderItem={({ item }: { item: Job }) => (
          <PressableCard onPress={() => router.push(`/jobs/${item.job_id}`)}>
            <View className="flex-row items-start justify-between gap-2">
              <Text className="flex-1 text-card font-semibold text-ink">
                {item.job_title}
              </Text>
              <Badge
                label={JOB_STATUS_LABELS[item.status]}
                tone={JOB_STATUS_COLORS[item.status]}
              />
            </View>
            <Text className="mt-1 text-helper text-muted">
              {item.submission_count} application
              {item.submission_count === 1 ? "" : "s"}
            </Text>
          </PressableCard>
        )}
      />
    </SafeAreaView>
  );
}
