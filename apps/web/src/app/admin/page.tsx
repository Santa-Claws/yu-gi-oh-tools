"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

function adminFetch<T>(path: string, opts: Parameters<typeof apiFetch>[1] = {}) {
  return apiFetch<T>(path, { ...opts, token: getToken() ?? undefined });
}

interface Job {
  id: string;
  job_type: string;
  status: string;
  progress: number;
  created_at: string | null;
  completed_at: string | null;
}

interface AnalyticsData {
  event_counts: { event_type: string; count: number }[];
  total_tokens: number;
  days: number;
}

export default function AdminPage() {
  const { data: jobs, refetch: refetchJobs } = useQuery({
    queryKey: ["admin-jobs"],
    queryFn: () => adminFetch<{ jobs: Job[] }>("/admin/jobs"),
    refetchInterval: 10000,
  });

  const { data: analytics } = useQuery({
    queryKey: ["admin-analytics"],
    queryFn: () => adminFetch<AnalyticsData>("/admin/analytics"),
  });

  const importCards = useMutation({
    mutationFn: () => adminFetch("/admin/import/cards", { method: "POST" }),
    onSuccess: () => refetchJobs(),
  });

  const runScrape = useMutation({
    mutationFn: () => adminFetch("/admin/scrape/run", { method: "POST" }),
    onSuccess: () => refetchJobs(),
  });

  const rebuildEmbed = useMutation({
    mutationFn: () => adminFetch("/admin/index/embed", { method: "POST" }),
    onSuccess: () => refetchJobs(),
  });

  const scrapeMetaDecks = useMutation({
    mutationFn: () => adminFetch("/admin/scrape/meta-decks", { method: "POST" }),
    onSuccess: () => refetchJobs(),
  });

  const statusColor: Record<string, string> = {
    completed: "bg-green-100 text-green-800",
    running: "bg-blue-100 text-blue-800",
    pending: "bg-gray-100 text-gray-800",
    failed: "bg-red-100 text-red-800",
  };

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold">Admin</h1>

      {/* Actions */}
      <section>
        <h2 className="mb-4 text-xl font-semibold">Actions</h2>
        <div className="flex flex-wrap gap-3">
          <Button loading={importCards.isPending} onClick={() => importCards.mutate()}>
            Import Cards (YGOProDeck)
          </Button>
          <Button loading={runScrape.isPending} variant="outline" onClick={() => runScrape.mutate()}>
            Run Meta Scraper
          </Button>
          <Button loading={rebuildEmbed.isPending} variant="outline" onClick={() => rebuildEmbed.mutate()}>
            Rebuild Embeddings
          </Button>
          <Button loading={scrapeMetaDecks.isPending} variant="outline" onClick={() => scrapeMetaDecks.mutate()}>
            Scrape Meta Decks
          </Button>
        </div>
      </section>

      {/* Analytics */}
      {analytics && (
        <section>
          <h2 className="mb-4 text-xl font-semibold">Analytics (last {analytics.days} days)</h2>
          <div className="mb-4 rounded-xl border border-blue-200 bg-blue-50 p-4">
            <p className="text-sm text-blue-700">
              Total tokens used: <strong>{analytics.total_tokens.toLocaleString()}</strong>
            </p>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {analytics.event_counts.map((e) => (
              <div key={e.event_type} className="flex justify-between rounded-lg border border-gray-200 bg-white px-4 py-3">
                <span className="text-sm">{e.event_type}</span>
                <span className="text-sm font-semibold">{e.count.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Jobs */}
      <section>
        <h2 className="mb-4 text-xl font-semibold">Recent Jobs</h2>
        {!jobs?.jobs.length ? (
          <p className="text-gray-400">No jobs yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-gray-200">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {["Type", "Status", "Progress", "Created", "Completed"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {jobs.jobs.map((job) => (
                  <tr key={job.id}>
                    <td className="px-4 py-3">{job.job_type}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor[job.status] ?? ""}`}>
                        {job.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">{job.progress}%</td>
                    <td className="px-4 py-3 text-gray-500">
                      {job.created_at ? new Date(job.created_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {job.completed_at ? new Date(job.completed_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
