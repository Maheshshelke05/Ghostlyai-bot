declare module "react-native-razorpay" {
  interface RazorpayOptions {
    key: string;
    amount: number;
    currency?: string;
    order_id: string;
    name?: string;
    description?: string;
    image?: string;
    prefill?: { email?: string; contact?: string; name?: string };
    theme?: { color?: string };
    [key: string]: unknown;
  }

  interface RazorpaySuccess {
    razorpay_payment_id: string;
    razorpay_order_id: string;
    razorpay_signature: string;
  }

  const RazorpayCheckout: {
    open(options: RazorpayOptions): Promise<RazorpaySuccess>;
  };

  export default RazorpayCheckout;
}
