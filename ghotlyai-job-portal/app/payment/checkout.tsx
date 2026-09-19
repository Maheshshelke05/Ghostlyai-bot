import { router } from "expo-router";
import { useState } from "react";
import { Text, View } from "react-native";
import RazorpayCheckout from "react-native-razorpay";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { apiErrorMessage, createPaymentOrder, verifyPayment } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

export default function CheckoutScreen() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const user = useAuthStore((s) => s.user);
  const refreshMe = useAuthStore((s) => s.refreshMe);

  async function onPay() {
    setError(null);
    setLoading(true);
    try {
      const order = await createPaymentOrder();
      const result = await RazorpayCheckout.open({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        order_id: order.order_id,
        name: "GhotlyAI Job Portal",
        description: "Job alerts subscription",
        prefill: {
          contact: user?.phone?.replace("+91", "") ?? "",
          name: user?.full_name ?? "",
        },
        theme: { color: "#EA580C" },
      });

      await verifyPayment({
        razorpay_order_id: result.razorpay_order_id,
        razorpay_payment_id: result.razorpay_payment_id,
        razorpay_signature: result.razorpay_signature,
      });
      await refreshMe();
      router.back();
    } catch (err: any) {
      // react-native-razorpay rejects with { code, description } on cancel/failure - a user
      // cancelling the sheet is not an error worth showing.
      if (err?.description === "Payment Cancelled" || err?.code === 0) {
        // no-op
      } else {
        setError(err?.description || apiErrorMessage(err, "Payment failed. Please try again."));
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-background px-6" edges={["bottom"]}>
      <View className="flex-1 justify-center">
        <Text className="font-display text-ink text-[24px] mb-2 text-center">Subscribe to GhotlyAI</Text>
        <Text className="font-body text-muted text-[15px] text-center mb-8">
          ₹99 for 30 days of job alerts in your chosen categories.
        </Text>
        {error ? <Text className="text-danger text-[13px] text-center mb-4">{error}</Text> : null}
      </View>
      <View className="mb-6">
        <Button label="Pay ₹99" onPress={onPay} loading={loading} />
      </View>
    </SafeAreaView>
  );
}
