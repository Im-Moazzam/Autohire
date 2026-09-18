import { useLocalSearchParams, useRouter } from "expo-router";
import { FlatList, RefreshControl, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  Badge,
  EmptyState,
  PressableCard,
  ScreenLoading,
} from "../../../../../components/ui";
import {
  SUBMISSION_STATUS_COLORS,
  SUBMISSION_STATUS_LABELS,
  useCandidates,
  type Candidate,
} from "../../../../../lib/candidates";
import { apiErrorMessage } from "../../../../../lib/http";

export default function CandidatesList() {
  const { jobId } = useLocalSearchParams<{ jobId: string }>();
  const router = useRouter();
  const candidates = useCandidates(jobId);

  if (candidates.isLoading) return <ScreenLoading />;

  if (candidates.isError) {
    return (
      <SafeAreaView className="flex-1 bg-canvas" edges={["bottom"]}>
        <EmptyState
          variant="error"
          title="Couldn't load candidates"
          description={apiErrorMessage(candidates.error)}
          actionLabel="Retry"
          onAction={() => candidates.refetch()}
        />
      </SafeAreaView>
    );
  }

  const items = candidates.data?.items ?? [];

  return (
    <SafeAreaView className="flex-1 bg-canvas" edges={["bottom"]}>
      <FlatList
        data={items}
        keyExtractor={(c) => c.candidate_id}
        contentContainerClassName="gap-3 p-4"
        refreshControl={
          <RefreshControl
            refreshing={candidates.isFetching}
            onRefresh={() => candidates.refetch()}
          />
        }
        ListEmptyComponent={
          <EmptyState
            title="No candidates yet"
            description="Applications for this job will show up here."
          />
        }
        renderItem={({ item }: { item: Candidate }) => (
          <PressableCard
            onPress={() =>
              router.push(`/jobs/${jobId}/candidates/${item.candidate_id}`)
            }
          >
            <View className="flex-row items-start justify-between gap-2">
              <View className="flex-1">
                <Text className="text-card font-semibold text-ink">
                  {item.full_name}
                </Text>
                <Text className="text-helper text-muted">{item.email}</Text>
              </View>
              <Badge
                label={SUBMISSION_STATUS_LABELS[item.submission_status]}
                tone={SUBMISSION_STATUS_COLORS[item.submission_status]}
              />
            </View>
          </PressableCard>
        )}
      />
    </SafeAreaView>
  );
}
