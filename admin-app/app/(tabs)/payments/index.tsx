import { FlashList } from "@shopify/flash-list";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as Clipboard from "expo-clipboard";
import { Directory, Paths, File as ExpoFile } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage, listPayments, paymentsExportUrl, syncPayment, type PaymentRow } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

type FilterKey = "all" | "paid" | "created" | "expired";

const STATUS_TONE = { paid: "go", created: "info", expired: "muted" } as const;

export default function PaymentsScreen() {
  const [filter, setFilter] = useState<FilterKey>("all");
  const insets = useSafeAreaInsets();
  const { show } = useToast();
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["payments", filter],
    queryFn: () => listPayments({ status: filter === "all" ? undefined : filter, page: 1, size: 50 }),
  });

  const syncMutation = useMutation({
    mutationFn: (id: number) => syncPayment(id),
    onSuccess: (payment) => {
      show(payment.status === "paid" ? "Payment activated!" : `Status: ${payment.status}`, "success");
      queryClient.invalidateQueries({ queryKey: ["payments"] });
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  const exportCsv = async () => {
    try {
      const file = await ExpoFile.downloadFileAsync(paymentsExportUrl({}), new Directory(Paths.cache), {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        idempotent: true,
      });
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(file.uri, { mimeType: "text/csv" });
      }
    } catch (err) {
      show(apiErrorMessage(err, "Export fail zala"), "error");
    }
  };

  const items = data?.items ?? [];
  const totalPaid = items.filter((p) => p.status === "paid").reduce((sum, p) => sum + p.amount_inr, 0);

  return (
    <View className="flex-1 bg-background" style={{ paddingTop: insets.top + 8 }}>
      <View className="px-4 flex-row items-center justify-between mb-3">
        <Text className="text-2xl font-extrabold text-ink">Payments</Text>
        <Pressable onPress={exportCsv}>
          <Text className="text-info text-sm font-semibold">Export CSV</Text>
        </Pressable>
      </View>

      <View className="px-4 mb-2">
        <Text className="text-sm text-muted">
          Showing total: <Text className="font-bold text-go">₹{totalPaid.toLocaleString("en-IN")}</Text>
        </Text>
      </View>

      <View className="px-4 flex-row flex-wrap">
        <Chip label="Sagle" selected={filter === "all"} onPress={() => setFilter("all")} />
        <Chip label="Paid" selected={filter === "paid"} onPress={() => setFilter("paid")} />
        <Chip label="Created" selected={filter === "created"} onPress={() => setFilter("created")} />
        <Chip label="Expired" selected={filter === "expired"} onPress={() => setFilter("expired")} />
      </View>

      {isLoading ? (
        <ListSkeleton />
      ) : items.length === 0 ? (
        <EmptyState emoji="💳" title="Kontihi payments nahit." />
      ) : (
        <FlashList
          data={items}
          keyExtractor={(item) => String(item.id)}
          refreshing={isRefetching}
          onRefresh={refetch}
          contentContainerStyle={{ paddingTop: 8, paddingBottom: 40 }}
          renderItem={({ item }) => (
            <PaymentRowCard
              payment={item}
              onSync={() => syncMutation.mutate(item.id)}
              syncing={syncMutation.isPending}
            />
          )}
        />
      )}
    </View>
  );
}

function PaymentRowCard({
  payment,
  onSync,
  syncing,
}: {
  payment: PaymentRow;
  onSync: () => void;
  syncing: boolean;
}) {
  const { show } = useToast();
  return (
    <View className="bg-surface border border-line/60 rounded-[18px] p-4 mb-3 mx-4">
      <View className="flex-row justify-between items-start">
        <View className="flex-1 pr-2">
          <Text className="text-base font-semibold text-ink">{payment.user_name || "Unknown"}</Text>
          <Text className="text-xs text-muted">{payment.user_phone}</Text>
        </View>
        <Text className="text-lg font-extrabold text-ink">₹{payment.amount_inr.toFixed(0)}</Text>
      </View>
      <View className="flex-row items-center justify-between mt-2">
        <Badge label={payment.status} tone={STATUS_TONE[payment.status as keyof typeof STATUS_TONE] ?? "muted"} />
        <Text className="text-xs text-muted">
          {new Date(payment.paid_at || payment.created_at).toLocaleDateString("en-IN")}
        </Text>
      </View>
      {payment.razorpay_payment_id ? (
        <Pressable
          onPress={async () => {
            await Clipboard.setStringAsync(payment.razorpay_payment_id!);
            show("Payment ID copied", "success");
          }}
          className="mt-2"
        >
          <Text className="text-xs text-info">{payment.razorpay_payment_id} (tap to copy)</Text>
        </Pressable>
      ) : null}
      {payment.status === "created" ? (
        <View className="mt-3">
          <Button label="Razorpay var check" variant="ghost" onPress={onSync} loading={syncing} fullWidth={false} />
        </View>
      ) : null}
    </View>
  );
}
