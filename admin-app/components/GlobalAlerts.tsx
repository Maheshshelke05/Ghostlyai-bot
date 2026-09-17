import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { firstOfNumber } from "@/lib/ghostlyFormat";
import { getGhostlyStats, listGhostlySupport } from "@/lib/ghostlyApi";
import { getDashboard, listSupportThreads } from "@/lib/api";
import { useAuthStore, useIsOwner } from "@/store/auth";
import { useToast } from "./ui/Toast";

const POLL_MS = 60_000;

/**
 * "msg aala pahije screen ver" - a message on screen when a new student signs up or someone
 * submits a support request, for BOTH workspaces, no matter which screen is currently open.
 * Mounted once at the root, independent of which tab/workspace is showing.
 *
 * This runs only while the app is open (foreground or backgrounded-but-alive) - it's a poll
 * against our own API every 60s, not an OS-level push notification that would also fire while
 * the app is fully closed. That's a bigger separate feature (Expo push tokens + a backend
 * event hook / push-sending service); this covers "on screen while using the app".
 *
 * Both Job Alert Bot's own queries and GhostlyAI's proxied ones run regardless of which
 * workspace is currently selected, and share query keys with each workspace's own dashboard
 * screen, so when that screen is visible this doesn't add extra network calls beyond what it
 * already does.
 */
export function GlobalAlerts() {
  const token = useAuthStore((s) => s.token);
  // Every source query below is owner-only on the backend (dashboard, support inbox, and the
  // whole /admin/ghostly/* proxy) - an uploader account would just get 403s every poll.
  const isOwner = useIsOwner();
  const enabled = !!token && isOwner;
  const { show } = useToast();

  const jaDashboard = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
    enabled,
    refetchInterval: POLL_MS,
  });
  const jaSupport = useQuery({
    queryKey: ["support", "open", ""],
    queryFn: () => listSupportThreads({ status: "open", page: 1, size: 1 }),
    enabled,
    refetchInterval: POLL_MS,
  });
  const ghStats = useQuery({
    queryKey: ["ghostly-stats"],
    queryFn: getGhostlyStats,
    enabled,
    refetchInterval: POLL_MS,
    retry: false,
  });
  const ghSupport = useQuery({
    queryKey: ["ghostly-support-summary"],
    queryFn: listGhostlySupport,
    enabled,
    refetchInterval: POLL_MS,
    retry: false,
  });

  // undefined = "haven't established a baseline yet" - the first observed value never alerts,
  // only real increases after that do.
  const seen = useRef<{ jaNewToday?: number; jaOpenSupport?: number; ghNewToday?: number; ghTicketCount?: number }>({});

  useEffect(() => {
    const v = jaDashboard.data?.users.new_today;
    if (v === undefined) return;
    if (seen.current.jaNewToday !== undefined && v > seen.current.jaNewToday) {
      show(`🎓 New student signed up — Job Alert Bot (${v} today)`, "success");
    }
    seen.current.jaNewToday = v;
  }, [jaDashboard.data, show]);

  useEffect(() => {
    const v = jaSupport.data?.total;
    if (v === undefined) return;
    if (seen.current.jaOpenSupport !== undefined && v > seen.current.jaOpenSupport) {
      show("💬 New support message — Job Alert Bot", "warn");
    }
    seen.current.jaOpenSupport = v;
  }, [jaSupport.data, show]);

  useEffect(() => {
    if (!ghStats.data) return;
    const v = firstOfNumber(ghStats.data, ["newUsersToday", "new_users_today"]);
    if (seen.current.ghNewToday !== undefined && v > seen.current.ghNewToday) {
      show(`👻 New user signed up — GhostlyAI.in (${v} today)`, "success");
    }
    seen.current.ghNewToday = v;
  }, [ghStats.data, show]);

  useEffect(() => {
    if (!ghSupport.data) return;
    const v = ghSupport.data.length;
    if (seen.current.ghTicketCount !== undefined && v > seen.current.ghTicketCount) {
      show("👻 New support ticket — GhostlyAI.in", "warn");
    }
    seen.current.ghTicketCount = v;
  }, [ghSupport.data, show]);

  return null;
}
