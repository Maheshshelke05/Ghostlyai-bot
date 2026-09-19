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

export default function PrivacyPolicyScreen() {
  return (
    <SafeAreaView className="flex-1 bg-background" edges={["bottom"]}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        <Text className="text-muted text-[13px] mb-5">Last updated: September 2026</Text>

        <Section title="What we collect">
          When you upload your resume, we read your name, phone number, email, education,
          skills and experience directly from it. If you type your name or phone number
          yourself, we store exactly what you enter. We also store the categories and job
          types you pick, and your device's push notification token if you allow notifications.
        </Section>

        <Section title="How we use it">
          We use your details only to match you with relevant job alerts in the categories you
          picked, to let you apply through verified links, and to respond to your support
          messages. We never sell your information to third parties.
        </Section>

        <Section title="Who we share it with">
          Your resume file is stored securely with Cloudinary. Resumes are parsed using
          Google's Gemini AI to extract your details - the file and extracted text are not used
          to train any AI model. Payments are processed by Razorpay; we never see or store your
          card or UPI details. Push notifications are delivered through Expo's notification
          service.
        </Section>

        <Section title="Your resume and data">
          Your resume is stored only to power your job matching and can be replaced anytime by
          uploading a new one from your profile. To have your account and data deleted, message
          us from the Support tab.
        </Section>

        <Section title="Data retention">
          We keep your account data as long as your account is active. If you stop using the
          app, your data stays until you ask us to delete it via Support.
        </Section>

        <Section title="Contact">
          For any privacy questions, reach out through the Support tab in this app.
        </Section>
      </ScrollView>
    </SafeAreaView>
  );
}
