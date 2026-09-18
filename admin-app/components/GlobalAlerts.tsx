import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { firstOfString, namesSummary, type AnyRecord } from "@/lib/ghostlyFormat";
import { listGhostlySupport, listGhostlyUsers } from "@/lib/ghostlyApi";
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
 * the app is fully closed (see PushRegistration + the backend's ghostly_alerts worker for that).
 *
 * The GhostlyAI side tracks actual user/ticket IDs (not just a count) so the toast can name who
 * signed up or what came in, the same way the backend's push notification does - a bare "3 new
 * users today" without saying who is not very useful on its own.
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
  const ghNewUsers = useQuery({
    queryKey: ["ghostly-users", undefined, "new_today"],
    queryFn: () => listGhostlyUsers({ filter: "new_today" }),
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
  // only real changes after that do.
  const seen = useRef<{ jaNewToday?: number; jaOpenSupport?: number; ghUserIds?: Set<string>; ghTicketIds?: Set<string> }>({});

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
    if (!ghNewUsers.data) return;
    const idOf = (u: AnyRecord) => firstOfString(u, ["user_id", "id"]);
    const currentIds = new Set(ghNewUsers.data.map(idOf).filter(Boolean));
    if (seen.current.ghUserIds) {
      const newOnes = ghNewUsers.data.filter((u) => idOf(u) && !seen.current.ghUserIds!.has(idOf(u)));
      if (newOnes.length > 0) {
        const names = newOnes.map((u) => firstOfString(u, ["name", "email"], "Someone"));
        show(`👻 ${namesSummary(names, "users")} signed up — GhostlyAI.in`, "success");
      }
    }
    seen.current.ghUserIds = currentIds;
  }, [ghNewUsers.data, show]);

  useEffect(() => {
    if (!ghSupport.data) return;
    const idOf = (t: AnyRecord) => firstOfString(t, ["id"]);
    const currentIds = new Set(ghSupport.data.map(idOf).filter(Boolean));
    if (seen.current.ghTicketIds) {
      const newOnes = ghSupport.data.filter((t) => idOf(t) && !seen.current.ghTicketIds!.has(idOf(t)));
      if (newOnes.length > 0) {
        const subjects = newOnes.map((t) => firstOfString(t, ["subject", "user_name"], "New ticket"));
        show(`👻 ${namesSummary(subjects, "tickets")} — GhostlyAI.in`, "warn");
      }
    }
    seen.current.ghTicketIds = currentIds;
  }, [ghSupport.data, show]);

  return null;
}
