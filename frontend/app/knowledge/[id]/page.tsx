"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, type Me } from "@/lib/api";
import Navbar from "@/components/Navbar";
import KnowledgeContent, {
  type KnowledgeContentData,
} from "@/components/KnowledgeContent";
import KnowledgeExtras, {
  type Attachment,
  type LinkedArticle,
} from "@/components/KnowledgeExtras";

type Detail = KnowledgeContentData & {
  id: string;
  like_count: number;
  success_count: number;
  prerequisites: LinkedArticle[];
  required_by: LinkedArticle[];
  related: LinkedArticle[];
  attachments: Attachment[];
};

export default function KnowledgeDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [d, setD] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [votedLike, setVotedLike] = useState(false);
  const [votedSuccess, setVotedSuccess] = useState(false);
  // form laporan / saran: null | "report" | "suggestion"
  const [reportKind, setReportKind] = useState<null | "report" | "suggestion">(null);
  const [reportMsg, setReportMsg] = useState("");
  const [reportSent, setReportSent] = useState(false);

  useEffect(() => {
    api<Me>("/auth/me")
      .then(setMe)
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (!me || !params.id) return;
    api<Detail>(`/knowledge/${params.id}`)
      .then((det) => {
        setD(det);
        // catat histori pemakaian
        api(`/knowledge/${params.id}/view`, { method: "POST" }).catch(() => {});
        // cek testimoni yang sudah diberikan (1x per user)
        api<{ success_given: boolean; like_given: boolean }>(
          `/knowledge/${params.id}/my-feedback`
        )
          .then((f) => {
            setVotedSuccess(f.success_given);
            setVotedLike(f.like_given);
          })
          .catch(() => {});
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat"));
  }, [me, params.id]);

  async function sendFeedback(type: "like" | "success") {
    if (!params.id) return;
    if (type === "like" && votedLike) return;
    if (type === "success" && votedSuccess) return;
    try {
      const r = await api<{ like_count: number; success_count: number }>(
        `/knowledge/${params.id}/feedback`,
        { method: "POST", body: JSON.stringify({ type }) }
      );
      if (type === "like") setVotedLike(true);
      else setVotedSuccess(true);
      setD((prev) =>
        prev ? { ...prev, like_count: r.like_count, success_count: r.success_count } : prev
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal mengirim testimoni");
    }
  }

  async function sendReport() {
    if (!params.id || !reportKind) return;
    if (!reportMsg.trim()) {
      setError("Isi dulu alasan/sarannya.");
      return;
    }
    try {
      await api(`/reports/knowledge/${params.id}`, {
        method: "POST",
        body: JSON.stringify({ kind: reportKind, message: reportMsg }),
      });
      setReportKind(null);
      setReportMsg("");
      setReportSent(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal mengirim");
    }
  }

  if (error) return <main style={{ padding: "2rem" }}><p style={{ color: "crimson" }}>{error}</p><Link href="/">Kembali</Link></main>;
  if (!d) return <main style={{ padding: "2rem" }}>Memuat...</main>;

  return (
    <main style={{ maxWidth: 760, margin: "2rem auto", padding: "0 1rem" }}>
      <Navbar />
      <KnowledgeContent d={d} />
      <KnowledgeExtras
        prerequisites={d.prerequisites ?? []}
        requiredBy={d.required_by ?? []}
        related={d.related ?? []}
        attachments={d.attachments ?? []}
      />

      <h2>Testimoni</h2>
      <p style={{ color: "#666", fontSize: "0.9rem" }}>
        Apakah tutorial ini benar dan berhasil?
      </p>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button
          onClick={() => sendFeedback("like")}
          disabled={votedLike}
          style={{ padding: "0.6rem 1.2rem" }}
        >
          👍 Suka ({d.like_count})
        </button>
        <button
          onClick={() => sendFeedback("success")}
          disabled={votedSuccess}
          style={{ padding: "0.6rem 1.2rem" }}
        >
          ✅ Berhasil ({d.success_count})
        </button>
      </div>
      {(votedLike || votedSuccess) && <p style={{ color: "#15803d" }}>Terima kasih atas testimoninya!</p>}

      <h2>Laporkan / Saran</h2>
      <p style={{ color: "#666", fontSize: "0.9rem" }}>
        Menemukan kesalahan atau punya saran perbaikan untuk tutorial ini?
      </p>
      {reportSent && <p style={{ color: "#15803d" }}>Terima kasih, masukanmu sudah terkirim ke admin.</p>}
      {!reportKind ? (
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button onClick={() => { setReportKind("report"); setReportSent(false); }} style={{ padding: "0.6rem 1.2rem" }}>
            🚩 Laporkan masalah
          </button>
          <button onClick={() => { setReportKind("suggestion"); setReportSent(false); }} style={{ padding: "0.6rem 1.2rem" }}>
            💡 Saran perbaikan
          </button>
        </div>
      ) : (
        <div>
          <p style={{ fontWeight: 600 }}>
            {reportKind === "report" ? "🚩 Alasan pelaporan:" : "💡 Saran perbaikan:"}
          </p>
          <textarea
            value={reportMsg}
            onChange={(e) => setReportMsg(e.target.value)}
            rows={4}
            placeholder={
              reportKind === "report"
                ? "Contoh: langkah 3 tidak sesuai untuk varian SM-A546E..."
                : "Contoh: tambahkan cara cek via fastboot..."
            }
            style={{ width: "100%", padding: "0.6rem", boxSizing: "border-box" }}
          />
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
            <button onClick={sendReport} style={{ padding: "0.6rem 1.2rem" }}>
              Kirim
            </button>
            <button
              onClick={() => { setReportKind(null); setReportMsg(""); }}
              style={{ padding: "0.6rem 1.2rem" }}
            >
              Batal
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
