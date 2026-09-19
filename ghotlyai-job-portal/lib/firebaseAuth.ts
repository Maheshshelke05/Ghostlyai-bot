/**
 * Phone-auth wrapper around @react-native-firebase/auth (modular API, v22+).
 *
 * On Android, Firebase's own phone-auth flow already includes automatic SMS-code
 * verification via Google Play Services' SMS Retriever - when it fires, `confirmationResult`
 * resolves before the user ever types anything, so the OTP screen should treat that as an
 * instant success rather than assuming the user must always enter a code. iOS has no such
 * mechanism (Apple platform limitation) and always needs the code typed in, though
 * `textContentType="oneTimeCode"` on the input still gives it iOS's own autofill suggestion.
 *
 * getPhoneNumberHint() is a placeholder for Android's Google Identity Services "Phone Number
 * Hint" API (auto-suggests the device's own SIM number so the user never types it at all).
 * There is no first-party Expo/Firebase module for this yet - it needs either a vetted
 * community wrapper or a small custom Expo config plugin around
 * com.google.android.gms:play-services-auth, neither of which is wired up here yet. It always
 * returns null today, so the login screen's manual phone-entry field is the real, working path;
 * wiring a real hint implementation in here is the only change needed to upgrade that screen to
 * the fully auto-filled flow, with no other code to touch.
 */
import { getApp } from "@react-native-firebase/app";
import {
  getAuth,
  signInWithPhoneNumber,
  type FirebaseAuthTypes,
} from "@react-native-firebase/auth";

export type Confirmation = FirebaseAuthTypes.ConfirmationResult;

// A ConfirmationResult can't be serialized through expo-router's string params, so it's kept
// here in memory between the login and OTP screens instead - fine for this single linear flow
// (if the app is killed mid-OTP, the user just requests a fresh code on return).
let pendingConfirmation: Confirmation | null = null;

export async function sendOtp(e164Phone: string): Promise<void> {
  const auth = getAuth(getApp());
  pendingConfirmation = await signInWithPhoneNumber(auth, e164Phone);
}

export function hasPendingConfirmation(): boolean {
  return pendingConfirmation !== null;
}

/** Resolves to the Firebase ID token to send to POST /student/auth/phone, or throws on a
 * wrong/expired code (FirebaseAuthTypes error codes like auth/invalid-verification-code). */
export async function confirmOtp(code: string): Promise<string> {
  if (!pendingConfirmation) throw new Error("Your code expired. Please request a new one.");
  const credential = await pendingConfirmation.confirm(code);
  const idToken = await credential?.user.getIdToken();
  pendingConfirmation = null;
  if (!idToken) throw new Error("Could not verify the code. Please try again.");
  return idToken;
}

export async function getPhoneNumberHint(): Promise<string | null> {
  return null;
}
