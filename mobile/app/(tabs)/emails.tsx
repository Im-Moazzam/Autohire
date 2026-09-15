import { FlatList, RefreshControl, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Badge, Card, EmptyState, ScreenLoading } from "../../components/ui";
import {
  DELIVERY_STATUS_COLORS,
  DELIVERY_STATUS_LABELS,
  EMAIL_TYPE_LABELS,
  useEmails,
  type EmailLog,
} from "../../lib/emails";
import { apiErrorMessage } from "../../lib/http";

export default function Emails() {
  const emails = useEmails();

  if (emails.isLoading) return <ScreenLoading />;

  if (emails.isError) {
    return (
      <SafeAreaView className="flex-1 bg-canvas" edges={["top", "bottom"]}>
        <EmptyState
          variant="error"
          title="Couldn't load emails"
          description={apiErrorMessage(emails.error)}
          actionLabel="Retry"
          onAction={() => emails.refetch()}
        />
      </SafeAreaView>
    );
  }

  const items = emails.data?.items ?? [];

  return (
    <SafeAreaView className="flex-1 bg-canvas" edges={["top", "bottom"]}>
      <View className="px-4 pb-2 pt-1">
        <Text className="text-page font-semibold text-ink">Emails</Text>
      </View>
      <FlatList
        data={items}
        keyExtractor={(e) => e.email_id}
        contentContainerClassName="gap-3 p-4"
        refreshControl={
          <RefreshControl
            refreshing={emails.isFetching}
            onRefresh={() => emails.refetch()}
          />
        }
        ListEmptyComponent={
          <EmptyState
            title="No emails yet"
            description="Emails sent to candidates will show up here."
          />
        }
        renderItem={({ item }: { item: EmailLog }) => (
          <Card>
            <View className="flex-row items-start justify-between gap-2">
              <View className="flex-1">
                <Text
                  className="text-card font-semibold text-ink"
                  numberOfLines={1}
                >
                  {item.subject}
                </Text>
                <Text className="text-helper text-muted">
                  {EMAIL_TYPE_LABELS[item.email_type]} · to{" "}
                  {item.candidate_name}
                </Text>
                <Text className="mt-1 text-helper text-muted">
                  {new Date(item.sent_at).toLocaleString()}
                </Text>
              </View>
              <Badge
                label={DELIVERY_STATUS_LABELS[item.delivery_status]}
                tone={DELIVERY_STATUS_COLORS[item.delivery_status]}
              />
            </View>
          </Card>
        )}
      />
    </SafeAreaView>
  );
}
