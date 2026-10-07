"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, type Me } from "@/lib/api";
import Navbar from "@/components/Navbar";
import ReportThread from "@/components/ReportThread";

type Report = {
  id: string;
  knowledge_id: string;
  knowledge_title: string;
  username: string;
  kind: string;
  message: string;
  status: string;
  replies_closed: boolean;
  replies_count: number;
  created_at: string;
};

const KIND_LABEL: Record<string, string> = {
  report: "🚩 Laporan",
  suggestion: "💡 Saran",
};

export default function AdminReportsPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [fStatus, setFStatus] = useState("");
  const [fKind, setFKind] = useState("");
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  function load() {
    const params = new URLSearchParams();
    if (fStatus) params.set("status", fStatus);
    if (fKind) params.set("kind", fKind);
    api<Report[]>(`/reports?${params.toString()}`)
      .then(setReports)
      .catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat"));
  }

  useEffect(() => {
    api<Me>("/auth/me")
      .then((m) => {
        if (m.role !== "admin") router.push("/login");
        else setMe(m);
      })
      .catch(() => router.push("/login"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  useEffect(load, [fStatus, fKind]);

  async function setStatus(r: Report, status: string) {
    try {
      await api(`/reports/${r.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal mengubah status");
    }
  }

  async function doDelete(r: Report) {
    if (!confirm("Hapus laporan ini?")) return;
    try {
      await api(`/reports/${r.id}`, { method: "DELETE" });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal menghapus");
    }
  }

  async function toggleCloseReplies(r: Report) {
    try {
      await api(`/reports/${r.id}`, {
        method: "PATCH",
        body: JSON.stringify({ replies_closed: !r.replies_closed }),
      });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal mengubah status balasan");
    }
  }

  if (!me) return <main style={{ padding: "2rem" }}>Memuat...</main>;

  return (
    <main style={{ maxWidth: 900, margin: "2rem auto", padding: "0 1rem" }}>
      <Navbar />
      <h1>Laporan & Saran User</h1>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <select value={fStatus} onChange={(e) => setFStatus(e.target.value)}>
          <option value="">Semua status</option>
          <option value="open">Belum ditangani</option>
          <option value="resolved">Selesai</option>
        </select>
        <select value={fKind} onChange={(e) => setFKind(e.target.value)}>
          <option value="">Semua jenis</option>
          <option value="report">Laporan masalah</option>
          <option value="suggestion">Saran perbaikan</option>
        </select>
      </div>

      {reports.length === 0 && <p>Belum ada laporan.</p>}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {reports.map((r) => (
          <li
            key={r.id}
            style={{
              border: "1px solid #ddd",
              borderRadius: "0.5rem",
              padding: "0.75rem 1rem",
              marginBottom: "0.75rem",
              opacity: r.status === "resolved" ? 0.65 : 1,
            }}
          >
            <div style={{ marginBottom: "0.25rem" }}>
              <b>{KIND_LABEL[r.kind] ?? r.kind}</b>{" "}
              <span
                style={{
                  background: r.status === "open" ? "#fef3c7" : "#dcfce7",
                  fontSize: "0.75rem",
                  padding: "0.15rem 0.5rem",
                  borderRadius: "1rem",
                }}
              >
                {r.status === "open" ? "belum ditangani" : "selesai"}
              </span>
            </div>
            <p style={{ margin: "0.25rem 0", whiteSpace: "pre-wrap" }}>{r.message}</p>
            <div style={{ color: "#666", fontSize: "0.85rem" }}>
              <Link href={`/admin/knowledge/${r.knowledge_id}`}>{r.knowledge_title}</Link>
              {" · "}oleh <b>{r.username}</b>
              {" · "}{new Date(r.created_at).toLocaleString("id-ID")}
            </div>
            <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem", flexWrap: "wrap" }}>
              {r.status === "open" ? (
                <button onClick={() => setStatus(r, "resolved")}>Tandai selesai</button>
              ) : (
                <button onClick={() => setStatus(r, "open")}>Buka lagi</button>
              )}
              <button
                onClick={() =>
                  setExpandedId(expandedId === r.id ? null : r.id)
                }
              >
                💬 Balasan ({r.replies_count})
                {expandedId === r.id ? " ▲" : " ▼"}
              </button>
              <button onClick={() => toggleCloseReplies(r)}>
                {r.replies_closed ? "🔓 Buka balasan" : "🔒 Tutup balasan"}
              </button>
              <button onClick={() => doDelete(r)}>Hapus</button>
            </div>
            {expandedId === r.id && (
              <ReportThread
                reportId={r.id}
                isAdmin={true}
                repliesClosed={r.replies_closed}
              />
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
