import { FlatList, Linking, RefreshControl, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Badge, Card, EmptyState, ScreenLoading } from "../../components/ui";
import { apiErrorMessage } from "../../lib/http";
import {
  SLOT_STATUS_COLORS,
  SLOT_STATUS_LABELS,
  useInterviews,
  type InterviewSlot,
} from "../../lib/scheduling";

export default function Scheduling() {
  const interviews = useInterviews();

  if (interviews.isLoading) return <ScreenLoading />;

  if (interviews.isError) {
    return (
      <SafeAreaView className="flex-1 bg-canvas" edges={["top", "bottom"]}>
        <EmptyState
          variant="error"
          title="Couldn't load interviews"
          description={apiErrorMessage(interviews.error)}
          actionLabel="Retry"
          onAction={() => interviews.refetch()}
        />
      </SafeAreaView>
    );
  }

  const items = interviews.data?.items ?? [];

  return (
    <SafeAreaView className="flex-1 bg-canvas" edges={["top", "bottom"]}>
      <View className="px-4 pb-2 pt-1">
        <Text className="text-page font-semibold text-ink">Scheduling</Text>
      </View>
      <FlatList
        data={items}
        keyExtractor={(slot) => slot.slot_id}
        contentContainerClassName="gap-3 p-4"
        refreshControl={
          <RefreshControl
            refreshing={interviews.isFetching}
            onRefresh={() => interviews.refetch()}
          />
        }
        ListEmptyComponent={
          <EmptyState
            title="No interviews yet"
            description="Scheduled interviews will show up here."
          />
        }
        renderItem={({ item }: { item: InterviewSlot }) => (
          <Card>
            <View className="flex-row items-start justify-between gap-2">
              <View className="flex-1">
                <Text className="text-card font-semibold text-ink">
                  {item.candidate_name}
                </Text>
                <Text className="text-helper text-muted">
                  {new Date(item.scheduled_at).toLocaleString()} ·{" "}
                  {item.duration_minutes}m
                </Text>
              </View>
              <Badge
                label={SLOT_STATUS_LABELS[item.status]}
                tone={SLOT_STATUS_COLORS[item.status]}
              />
            </View>
            {item.google_meet_link ? (
              <Text
                className="mt-2 text-helper font-semibold text-primary"
                onPress={() => Linking.openURL(item.google_meet_link!)}
              >
                Join Google Meet
              </Text>
            ) : null}
          </Card>
        )}
      />
    </SafeAreaView>
  );
}
