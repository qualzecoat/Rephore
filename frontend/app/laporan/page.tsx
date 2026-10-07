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
  report: "🚩 Laporan masalah",
  suggestion: "💡 Saran perbaikan",
};

const STATUS_LABEL: Record<string, string> = {
  open: "belum ditangani",
  resolved: "selesai",
};

export default function MyReportsPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [fStatus, setFStatus] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  function load() {
    const params = new URLSearchParams();
    if (fStatus) params.set("status", fStatus);
    api<Report[]>(`/reports/me?${params.toString()}`)
      .then(setReports)
      .catch(() => router.push("/login"));
  }

  useEffect(() => {
    api<Me>("/auth/me")
      .then((m) => setMe(m))
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(load, [fStatus]);

  if (!me) return <main style={{ padding: "2rem" }}>Memuat...</main>;

  return (
    <main style={{ maxWidth: 900, margin: "2rem auto", padding: "0 1rem" }}>
      <Navbar />
      <h1>Laporan & saran saya</h1>
      <p style={{ color: "#666", fontSize: "0.9rem" }}>
        Pantau laporan masalah dan saran perbaikan yang kamu kirim beserta
        status penanganannya oleh admin.
      </p>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <select value={fStatus} onChange={(e) => setFStatus(e.target.value)}>
          <option value="">Semua status</option>
          <option value="open">Belum ditangani</option>
          <option value="resolved">Selesai</option>
        </select>
      </div>

      {reports.length === 0 && (
        <p>
          Belum ada laporan. Kamu bisa mengirim laporan atau saran dari halaman
          artikel.
        </p>
      )}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {reports.map((r) => (
          <li
            key={r.id}
            style={{
              border: "1px solid #ddd",
              borderRadius: "0.5rem",
              padding: "0.75rem 1rem",
              marginBottom: "0.75rem",
              opacity: r.status === "resolved" ? 0.7 : 1,
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
                {STATUS_LABEL[r.status] ?? r.status}
              </span>
            </div>
            <p style={{ margin: "0.25rem 0", whiteSpace: "pre-wrap" }}>{r.message}</p>
            <div style={{ color: "#666", fontSize: "0.85rem" }}>
              Artikel:{" "}
              <Link href={`/knowledge/${r.knowledge_id}`}>{r.knowledge_title}</Link>
              {" · "}dikirim {new Date(r.created_at).toLocaleString("id-ID")}
            </div>
            <button
              onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}
              style={{ marginTop: "0.5rem" }}
            >
              💬 Balasan ({r.replies_count}){expandedId === r.id ? " ▲" : " ▼"}
            </button>
            {expandedId === r.id && (
              <ReportThread
                reportId={r.id}
                isAdmin={me.role === "admin"}
                repliesClosed={r.replies_closed}
              />
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
