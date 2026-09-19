import { BottomSheetModal } from "@gorhom/bottom-sheet";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useRef, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { OnboardingProgress } from "@/components/OnboardingProgress";
import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import { SelectSheet } from "@/components/ui/SelectSheet";
import { apiErrorMessage, getDistricts, setDistrict } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

export default function DistrictScreen() {
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sheetRef = useRef<BottomSheetModal>(null);
  const applyMe = useAuthStore((s) => s.applyMe);

  const { data } = useQuery({ queryKey: ["districts"], queryFn: getDistricts });

  async function onNext() {
    if (!selected) return;
    setError(null);
    setLoading(true);
    try {
      const me = await setDistrict(selected);
      applyMe(me);
      router.push("/(onboarding)/resume");
    } catch (err) {
      setError(apiErrorMessage(err, "Could not save your district."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-background px-6" edges={["top", "bottom"]}>
      <View className="flex-1 pt-4">
        <OnboardingProgress step={2} />
        <Text className="font-display text-ink text-[26px] mb-2">Where are you based?</Text>
        <Text className="font-body text-muted text-[15px] mb-6">
          Pick your district, or search if it's not shown below.
        </Text>

        <View className="flex-row flex-wrap">
          {(data?.top ?? []).map((d) => (
            <Chip key={d} label={d} selected={selected === d} onPress={() => setSelected(d)} />
          ))}
        </View>

        <Pressable onPress={() => sheetRef.current?.present()} className="mt-2">
          <Text className="font-body-strong text-brand text-[15px]">Search all districts →</Text>
        </Pressable>

        {selected ? (
          <View className="bg-brand-soft rounded-2xl px-4 py-3 mt-6">
            <Text className="font-body-strong text-brand text-[15px]">Selected: {selected}</Text>
          </View>
        ) : null}
        {error ? <Text className="text-danger text-[13px] mt-2">{error}</Text> : null}
      </View>

      <View className="mb-4">
        <Button label="Continue" onPress={onNext} loading={loading} disabled={!selected} />
      </View>

      <SelectSheet
        ref={sheetRef}
        title="Select your district"
        options={(data?.districts ?? []).map((d) => ({ label: d, value: d }))}
        onSelect={(value) => {
          setSelected(value);
          sheetRef.current?.dismiss();
        }}
      />
    </SafeAreaView>
  );
}
