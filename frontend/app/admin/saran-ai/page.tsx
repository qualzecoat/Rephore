"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Me } from "@/lib/api";
import Navbar from "@/components/Navbar";

type Suggestion = {
  id: string;
  signature: string;
  service: string;
  severity: string;
  probable_cause: string;
  suggested_fix: string;
  status: string;
  created_at: string;
};

type ErrorEvent = {
  id: string;
  service: string;
  signature: string;
  message: string;
  count: number;
  first_seen: string;
  last_seen: string;
};

type Run = {
  id: string;
  trigger: string;
  status: string;
  incidents_found: number;
  suggestions_created: number;
  error: string | null;
  created_at: string;
  finished_at: string | null;
};

const SEV_COLOR: Record<string, string> = {
  high: "#dc2626",
  medium: "#d97706",
  low: "#16a34a",
};

function fmt(dt: string | null) {
  return dt ? new Date(dt).toLocaleString("id-ID") : "-";
}

export default function AdminSaranAiPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [open, setOpen] = useState<Suggestion[]>([]);
  const [closed, setClosed] = useState<Suggestion[]>([]);
  const [events, setEvents] = useState<ErrorEvent[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState("");
  const [analyzing, setAnalyzing] = useState(false);

  function load() {
    api<Suggestion[]>("/logwatch/suggestions?status=open")
      .then(setOpen)
      .catch(() => {});
    api<Suggestion[]>("/logwatch/suggestions?status=resolved")
      .then(setClosed)
      .catch(() => {});
    api<ErrorEvent[]>("/logwatch/errors")
      .then((e) => setEvents(e.slice(0, 20)))
      .catch(() => {});
    api<Run[]>("/logwatch/analysis/runs")
      .then((r) => {
        setRuns(r.slice(0, 5));
        setAnalyzing(r.some((x) => x.status === "pending" || x.status === "running"));
      })
      .catch(() => {});
  }

  useEffect(() => {
    api<Me>("/auth/me")
      .then((m) => {
        if (m.role !== "admin") router.push("/login");
        else {
          setMe(m);
          load();
        }
      })
      .catch(() => router.push("/login"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  useEffect(() => {
    if (!analyzing) return;
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analyzing]);

  async function triggerAnalysis() {
    setError("");
    try {
      await api("/logwatch/analysis/run", { method: "POST" });
      setAnalyzing(true);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal meminta analisis");
    }
  }

  async function setStatus(s: Suggestion, status: string) {
    try {
      await api(`/logwatch/suggestions/${s.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal mengubah status");
    }
  }

  async function doDelete(s: Suggestion) {
    if (!confirm("Hapus saran ini?")) return;
    try {
      await api(`/logwatch/suggestions/${s.id}`, { method: "DELETE" });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal menghapus");
    }
  }

  if (!me) return <main style={{ padding: "2rem" }}>Memuat...</main>;

  const lastRun = runs[0];

  return (
    <main style={{ maxWidth: 900, margin: "2rem auto", padding: "0 1rem" }}>
      <Navbar />
      <h1>Saran AI dari Log</h1>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div
        style={{
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          borderRadius: "0.5rem",
          padding: "0.75rem 1rem",
          marginBottom: "1.5rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "1rem",
        }}
      >
        <div style={{ fontSize: "0.9rem", color: "#475569" }}>
          Analisis otomatis tiap 24 jam memakai AI provider aktif.
          {lastRun && (
            <>
              {" "}Terakhir: {lastRun.trigger === "manual" ? "manual" : "terjadwal"} —{" "}
              {lastRun.status}
              {lastRun.status === "done" &&
                ` (${lastRun.incidents_found} insiden, ${lastRun.suggestions_created} saran)`}
              {lastRun.status === "error" && lastRun.error && ` (${lastRun.error})`}{" "}
              · {fmt(lastRun.finished_at ?? lastRun.created_at)}
            </>
          )}
        </div>
        <button
          onClick={triggerAnalysis}
          disabled={analyzing}
          style={{ padding: "0.6rem 1.2rem", whiteSpace: "nowrap" }}
        >
          {analyzing ? "Menganalisis..." : "Analisa sekarang"}
        </button>
      </div>

      <h2>Saran terbuka ({open.length})</h2>
      {open.length === 0 && <p>Belum ada saran. Semua aman. 🎉</p>}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {open.map((s) => (
          <li
            key={s.id}
            style={{
              border: "1px solid #ddd",
              borderRadius: "0.5rem",
              padding: "0.75rem 1rem",
              marginBottom: "0.75rem",
            }}
          >
            <div style={{ marginBottom: "0.25rem" }}>
              <span
                style={{
                  background: SEV_COLOR[s.severity] ?? "#666",
                  color: "#fff",
                  fontSize: "0.75rem",
                  padding: "0.15rem 0.5rem",
                  borderRadius: "1rem",
                  marginRight: "0.5rem",
                }}
              >
                {s.severity}
              </span>
              <code style={{ fontSize: "0.8rem", color: "#475569" }}>
                [{s.service}] {s.signature}
              </code>
            </div>
            <p style={{ margin: "0.4rem 0" }}>
              <b>Kemungkinan penyebab:</b> {s.probable_cause || "-"}
            </p>
            <p style={{ margin: "0.4rem 0", whiteSpace: "pre-wrap" }}>
              <b>Saran perbaikan:</b> {s.suggested_fix || "-"}
            </p>
            <div style={{ color: "#999", fontSize: "0.8rem" }}>{fmt(s.created_at)}</div>
            <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
              <button onClick={() => setStatus(s, "resolved")}>Tandai selesai</button>
              <button onClick={() => setStatus(s, "dismissed")}>Abaikan</button>
              <button onClick={() => doDelete(s)}>Hapus</button>
            </div>
          </li>
        ))}
      </ul>

      {closed.length > 0 && (
        <>
          <h2>Selesai ({closed.length})</h2>
          <ul>
            {closed.map((s) => (
              <li key={s.id} style={{ marginBottom: "0.3rem", color: "#666" }}>
                <code style={{ fontSize: "0.8rem" }}>{s.signature}</code> — {s.status}
                <button
                  onClick={() => setStatus(s, "open")}
                  style={{ marginLeft: "0.5rem" }}
                >
                  Buka lagi
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      <h2>Insiden error terakhir</h2>
      {events.length === 0 && <p>Belum ada insiden tercatat.</p>}
      <ul>
        {events.map((e) => (
          <li key={e.id} style={{ marginBottom: "0.3rem", fontSize: "0.9rem" }}>
            <code style={{ fontSize: "0.8rem" }}>
              [{e.service}] {e.signature}
            </code>{" "}
            <span style={{ color: "#666" }}>
              ×{e.count} · terakhir {fmt(e.last_seen)}
            </span>
          </li>
        ))}
      </ul>
    </main>
  );
}
