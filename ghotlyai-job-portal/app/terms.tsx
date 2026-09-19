import { ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

function Section({ title, children }: { title: string; children: string }) {
  return (
    <View className="mb-5">
      <Text className="font-body-strong text-ink text-[15px] mb-1.5">{title}</Text>
      <Text className="font-body text-muted text-[14px] leading-6">{children}</Text>
    </View>
  );
}

export default function TermsScreen() {
  return (
    <SafeAreaView className="flex-1 bg-background" edges={["bottom"]}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        <Text className="text-muted text-[13px] mb-5">Last updated: September 2026</Text>

        <Section title="What this service is">
          GhotlyAI Job Portal is a job-alert service. We surface verified job postings with
          official apply links that match the categories and job types you choose. This is not
          a job placement or guarantee service - we don't promise you'll get hired, and we
          don't run the hiring process for any listed job.
        </Section>

        <Section title="Free trial and subscription">
          New accounts get a free trial. After it ends, continued access to job alerts requires
          an active subscription, shown with its price and duration on the Subscription tab.
          Subscriptions renew only when you manually pay again - there is no auto-renewal.
        </Section>

        <Section title="Payments and refunds">
          Payments are processed securely through Razorpay. Since a subscription unlocks
          immediate access to job alerts, payments are generally non-refundable once your
          access period has started, except where required by law. Contact Support if a
          payment was made in error.
        </Section>

        <Section title="Job listings">
          Jobs are added by our team and are meant to be genuine, verified postings with real
          apply links. We are not the employer for any listed job and are not responsible for
          hiring decisions, interview processes, or outcomes at the companies you apply to.
        </Section>

        <Section title="Your account">
          You're responsible for the accuracy of the information in your resume and profile.
          We may suspend accounts that abuse the service (spam, fake resumes, or attempts to
          disrupt the platform).
        </Section>

        <Section title="Changes">
          We may update these terms as the service evolves. Continued use of the app after an
          update means you accept the revised terms.
        </Section>

        <Section title="Contact">
          Questions about these terms can be sent through the Support tab in this app.
        </Section>
      </ScrollView>
    </SafeAreaView>
  );
}
