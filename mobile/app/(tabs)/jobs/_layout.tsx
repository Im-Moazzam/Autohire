import { Stack } from "expo-router";

export default function JobsStackLayout() {
  return (
    <Stack
      screenOptions={{
        headerTintColor: "#0058BE",
        headerTitleStyle: { color: "#0F172A" },
      }}
    >
      <Stack.Screen name="index" options={{ title: "Jobs" }} />
      <Stack.Screen name="[jobId]/index" options={{ title: "Job" }} />
      <Stack.Screen
        name="[jobId]/candidates/index"
        options={{ title: "Candidates" }}
      />
      <Stack.Screen
        name="[jobId]/candidates/[candidateId]"
        options={{ title: "Candidate" }}
      />
    </Stack>
  );
}
