"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, type Me } from "@/lib/api";
import Navbar from "@/components/Navbar";

type Step = {
  n: number;
  instruksi: string;
  commands: string[];
  warnings: string[];
};

type Detail = {
  id: string;
  title: string;
  brand: string | null;
  model: string | null;
  category: string | null;
  subcategory: string | null;
  difficulty: string | null;
  est_time: string | null;
  tools: string[];
  troubleshooting: string | null;
  tags: string[];
  like_count: number;
  success_count: number;
  content_json: { steps: Step[] };
};

export default function KnowledgeDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [d, setD] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [votedLike, setVotedLike] = useState(false);
  const [votedSuccess, setVotedSuccess] = useState(false);

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
        // cek apakah user sudah menandai berhasil (1x per user)
        api<{ success_given: boolean }>(`/knowledge/${params.id}/my-feedback`)
          .then((f) => setVotedSuccess(f.success_given))
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

  if (error) return <main style={{ padding: "2rem" }}><p style={{ color: "crimson" }}>{error}</p><Link href="/">Kembali</Link></main>;
  if (!d) return <main style={{ padding: "2rem" }}>Memuat...</main>;

  return (
    <main style={{ maxWidth: 760, margin: "2rem auto", padding: "0 1rem" }}>
      <Navbar />
      <h1 style={{ marginBottom: "0.25rem" }}>{d.title}</h1>
      <p style={{ color: "#666", marginTop: 0 }}>
        {[d.brand, d.model, d.category, d.subcategory, d.difficulty, d.est_time]
          .filter(Boolean)
          .join(" · ")}
      </p>
      <p>
        {d.tags.map((t) => (
          <span
            key={t}
            style={{
              background: "#eee",
              padding: "0.2rem 0.6rem",
              borderRadius: "1rem",
              fontSize: "0.8rem",
              marginRight: "0.25rem",
            }}
          >
            {t}
          </span>
        ))}
      </p>

      {d.tools.length > 0 && (
        <>
          <h2>Alat yang dibutuhkan</h2>
          <ul>
            {d.tools.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </>
      )}

      <h2>Langkah-langkah</h2>
      <ol>
        {d.content_json.steps.map((s) => (
          <li key={s.n} style={{ marginBottom: "1rem" }}>
            <p style={{ margin: "0.25rem 0", whiteSpace: "pre-wrap" }}>{s.instruksi}</p>
            {s.commands.map((c, i) => (
              <pre key={i} style={{ background: "#1e1e1e", color: "#d4d4d4", padding: "0.5rem", borderRadius: "0.25rem", overflowX: "auto" }}>
                {c}
              </pre>
            ))}
            {s.warnings.map((w, i) => (
              <p key={i} style={{ background: "#fef3c7", padding: "0.5rem", borderRadius: "0.25rem" }}>
                ⚠️ {w}
              </p>
            ))}
          </li>
        ))}
      </ol>

      {d.troubleshooting && (
        <>
          <h2>Troubleshooting</h2>
          <p style={{ whiteSpace: "pre-wrap" }}>{d.troubleshooting}</p>
        </>
      )}

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
    </main>
  );
}
