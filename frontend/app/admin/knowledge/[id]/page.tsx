"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, type Me } from "@/lib/api";
import Navbar from "@/components/Navbar";
import KnowledgeContent, {
  type KnowledgeContentData,
} from "@/components/KnowledgeContent";

type Detail = KnowledgeContentData & {
  id: string;
  source: string;
  status: string;
  like_count: number;
  success_count: number;
  created_at: string;
};

/** Halaman review admin: baca isi lengkap, lalu tandai direview / hapus. */
export default function AdminKnowledgeReviewPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [d, setD] = useState<Detail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Me>("/auth/me")
      .then((m) => {
        if (m.role !== "admin") router.push("/login");
      })
      .catch(() => router.push("/login"));
  }, [router]);

  function load() {
    if (!params.id) return;
    api<Detail>(`/knowledge/${params.id}`)
      .then(setD)
      .catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat"));
  }

  useEffect(load, [params.id]);

  async function doReview() {
    if (!params.id) return;
    try {
      const updated = await api<Detail>(`/knowledge/${params.id}/review`, {
        method: "POST",
      });
      setD(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal menandai direview");
    }
  }

  async function doDelete() {
    if (!d) return;
    const testi = d.like_count + d.success_count;
    const msg =
      testi > 0
        ? `Knowledge ini sudah punya ${d.like_count} suka dan ${d.success_count} testimoni berhasil — menghapusnya sangat disayangkan. Tetap hapus?`
        : "Hapus knowledge ini?";
    if (!confirm(msg)) return;
    try {
      await api(`/knowledge/${d.id}`, { method: "DELETE" });
      router.push("/admin/knowledge");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal menghapus knowledge");
    }
  }

  if (error)
    return (
      <main style={{ padding: "2rem" }}>
        <p style={{ color: "crimson" }}>{error}</p>
        <Link href="/admin/knowledge">Kembali ke daftar</Link>
      </main>
    );
  if (!d) return <main style={{ padding: "2rem" }}>Memuat...</main>;

  return (
    <main style={{ maxWidth: 760, margin: "2rem auto", padding: "0 1rem" }}>
      <Navbar />
      <p
        style={{
          background: d.status === "sudah_direview" ? "#dbeafe" : "#fef3c7",
          padding: "0.6rem 1rem",
          borderRadius: "0.5rem",
          fontSize: "0.9rem",
        }}
      >
        Status: <b>{d.status === "sudah_direview" ? "sudah direview" : "belum direview"}</b>
        {" · "}Sumber: {d.source}
        {" · "}👍 {d.like_count} · ✅ {d.success_count}
      </p>

      <KnowledgeContent d={d} />

      <hr style={{ margin: "2rem 0 1rem" }} />
      <div style={{ display: "flex", gap: "0.75rem", paddingBottom: "2rem" }}>
        {d.status !== "sudah_direview" && (
          <button
            onClick={doReview}
            style={{ padding: "0.7rem 1.4rem", fontWeight: 600 }}
          >
            Tandai direview
          </button>
        )}
        <button
          onClick={doDelete}
          style={{ padding: "0.7rem 1.4rem", color: "crimson" }}
        >
          Hapus
        </button>
      </div>
    </main>
  );
}
