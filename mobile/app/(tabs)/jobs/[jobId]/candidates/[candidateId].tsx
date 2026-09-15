import { useLocalSearchParams } from "expo-router";
import { Linking, ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ScreenLoading,
  SectionLabel,
} from "../../../../../components/ui";
import {
  canReject,
  SUBMISSION_STATUS_COLORS,
  SUBMISSION_STATUS_LABELS,
  useCandidate,
  useUpdateCandidateStatus,
} from "../../../../../lib/candidates";
import { apiErrorMessage } from "../../../../../lib/http";

export default function CandidateDetailScreen() {
  const { jobId, candidateId } = useLocalSearchParams<{
    jobId: string;
    candidateId: string;
  }>();
  const candidate = useCandidate(candidateId);
  const updateStatus = useUpdateCandidateStatus(jobId);

  if (candidate.isLoading) return <ScreenLoading />;

  if (candidate.isError || !candidate.data) {
    return (
      <SafeAreaView className="flex-1 bg-canvas" edges={["bottom"]}>
        <EmptyState
          variant="error"
          title="Couldn't load this candidate"
          description={apiErrorMessage(candidate.error)}
          actionLabel="Retry"
          onAction={() => candidate.refetch()}
        />
      </SafeAreaView>
    );
  }

  const data = candidate.data;
  const isRejected = data.submission_status === "REJECTED";
  const isInvited = data.submission_status === "INVITED";

  return (
    <SafeAreaView className="flex-1 bg-canvas" edges={["bottom"]}>
      <ScrollView
        className="flex-1 px-4"
        contentContainerClassName="gap-4 py-4"
      >
        <View className="flex-row items-start justify-between gap-2">
          <View className="flex-1">
            <Text className="text-page font-semibold text-ink">
              {data.full_name}
            </Text>
            <Text className="text-body text-muted">{data.email}</Text>
            {data.phone_number ? (
              <Text className="text-body text-muted">{data.phone_number}</Text>
            ) : null}
          </View>
          <Badge
            label={SUBMISSION_STATUS_LABELS[data.submission_status]}
            tone={SUBMISSION_STATUS_COLORS[data.submission_status]}
          />
        </View>

        {data.parse_error ? (
          <Card className="border-error/30 bg-error/5">
            <SectionLabel>Resume parse failed</SectionLabel>
            <Text className="text-body text-error">{data.parse_error}</Text>
          </Card>
        ) : null}

        {data.resume_url ? (
          <Button
            label="Open resume"
            variant="secondary"
            onPress={() => Linking.openURL(data.resume_url!)}
          />
        ) : null}

        {isInvited ? (
          <View className="flex-row items-center justify-center gap-2 rounded-control bg-success/10 px-4 py-3">
            <Text className="text-body font-semibold text-success">
              Invite sent for interview
            </Text>
          </View>
        ) : isRejected ? (
          <Button
            label="Undo rejection"
            variant="warning"
            loading={updateStatus.isPending}
            onPress={() =>
              updateStatus.mutate({
                candidateId: data.candidate_id,
                status: data.restorable_status,
              })
            }
          />
        ) : canReject(data.submission_status) ? (
          <Button
            label="Reject candidate"
            variant="destructive"
            loading={updateStatus.isPending}
            onPress={() =>
              updateStatus.mutate({
                candidateId: data.candidate_id,
                status: "REJECTED",
              })
            }
          />
        ) : null}

        {updateStatus.isError ? (
          <Text className="text-helper text-error">
            {apiErrorMessage(updateStatus.error)}
          </Text>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}
