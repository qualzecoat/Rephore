"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, API_URL, getToken, type Me } from "@/lib/api";
import Navbar from "@/components/Navbar";
import KnowledgeContent, {
  type KnowledgeContentData,
} from "@/components/KnowledgeContent";
import {
  fmtSize,
  type Attachment,
  type LinkedArticle,
} from "@/components/KnowledgeExtras";

type Detail = KnowledgeContentData & {
  id: string;
  source: string;
  status: string;
  like_count: number;
  success_count: number;
  created_at: string;
  prerequisites: LinkedArticle[];
  required_by: LinkedArticle[];
  related: LinkedArticle[];
  attachments: Attachment[];
};

type SearchHit = {
  id: string;
  title: string;
  brand: string | null;
  model: string | null;
};

/** Halaman review admin: baca isi lengkap, lalu tandai direview / hapus. */
export default function AdminKnowledgeReviewPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [d, setD] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  // kelola tautan
  const [linkQuery, setLinkQuery] = useState("");
  const [linkResults, setLinkResults] = useState<SearchHit[]>([]);
  // upload lampiran
  const [upFile, setUpFile] = useState<File | null>(null);
  const [upDesc, setUpDesc] = useState("");
  const [uploading, setUploading] = useState(false);
  const [upReset, setUpReset] = useState(0);

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

  async function doUnreview() {
    if (!params.id) return;
    if (!confirm("Kembalikan artikel ini ke status belum direview?")) return;
    try {
      const updated = await api<Detail>(`/knowledge/${params.id}/unreview`, {
        method: "POST",
      });
      setD(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal membatalkan review");
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

  // ---------- tautan artikel ----------

  function linkedIds(): Set<string> {
    const s = new Set<string>();
    d?.prerequisites.forEach((l) => s.add(l.knowledge_id));
    d?.related.forEach((l) => s.add(l.knowledge_id));
    d?.required_by.forEach((l) => s.add(l.knowledge_id));
    return s;
  }

  async function searchLinks() {
    if (!linkQuery.trim()) return;
    try {
      const r = await api<{ items: SearchHit[] }>(
        `/knowledge?q=${encodeURIComponent(linkQuery.trim())}&per_page=10`
      );
      const skip = linkedIds();
      setLinkResults(
        r.items.filter((h) => h.id !== params.id && !skip.has(h.id))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Pencarian gagal");
    }
  }

  async function addLink(toId: string, relation: "prerequisite" | "related") {
    if (!params.id) return;
    try {
      await api(`/knowledge/${params.id}/links`, {
        method: "POST",
        body: JSON.stringify({ to_knowledge_id: toId, relation }),
      });
      setLinkResults((rs) => rs.filter((h) => h.id !== toId));
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal menambah tautan");
    }
  }

  async function removeLink(linkId: string) {
    if (!confirm("Hapus tautan ini?")) return;
    try {
      await api(`/knowledge/links/${linkId}`, { method: "DELETE" });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal menghapus tautan");
    }
  }

  // ---------- lampiran file ----------

  async function doUpload() {
    if (!upFile || !params.id) return;
    setUploading(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", upFile);
      fd.append("description", upDesc);
      const token = getToken();
      const res = await fetch(
        `${API_URL}/knowledge/${params.id}/attachments`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: fd,
        }
      );
      if (!res.ok) {
        const t = await res.text();
        let msg = t || "Upload gagal";
        try {
          msg = JSON.parse(t).detail ?? msg;
        } catch {
          /* pakai teks mentah */
        }
        throw new Error(msg);
      }
      setUpFile(null);
      setUpDesc("");
      setUpReset((x) => x + 1);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload gagal");
    } finally {
      setUploading(false);
    }
  }

  async function removeAttachment(attId: string, name: string) {
    if (!confirm(`Hapus lampiran "${name}"? File di server ikut terhapus.`))
      return;
    try {
      await api(`/knowledge/attachments/${attId}`, { method: "DELETE" });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal menghapus lampiran");
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

      <h2>🔗 Tautan artikel</h2>
      <div
        style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}
      >
        <input
          placeholder="Cari artikel untuk ditautkan..."
          value={linkQuery}
          onChange={(e) => setLinkQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && searchLinks()}
          style={{ padding: "0.5rem", flex: 1 }}
        />
        <button onClick={searchLinks}>Cari</button>
      </div>
      {linkResults.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0, marginBottom: "1rem" }}>
          {linkResults.map((h) => (
            <li
              key={h.id}
              style={{
                borderBottom: "1px solid #eee",
                padding: "0.4rem 0",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <span>
                {h.title}{" "}
                <span style={{ color: "#666", fontSize: "0.85rem" }}>
                  {[h.brand, h.model].filter(Boolean).join(" ")}
                </span>
              </span>
              <span style={{ display: "flex", gap: "0.25rem" }}>
                <button
                  onClick={() => addLink(h.id, "prerequisite")}
                  title="Artikel ini mewajibkan membaca artikel tersebut dulu"
                >
                  + Prasyarat
                </button>
                <button onClick={() => addLink(h.id, "related")}>
                  + Terkait
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}

      {d.prerequisites.length > 0 && (
        <>
          <h3>📚 Prasyarat</h3>
          <ul>
            {d.prerequisites.map((l) => (
              <li key={l.id} style={{ marginBottom: "0.3rem" }}>
                <Link href={`/admin/knowledge/${l.knowledge_id}`}>
                  {l.title}
                </Link>
                <button
                  onClick={() => removeLink(l.id)}
                  style={{ marginLeft: "0.5rem", color: "crimson" }}
                  title="Hapus tautan"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
      {d.related.length > 0 && (
        <>
          <h3>🔗 Terkait</h3>
          <ul>
            {d.related.map((l) => (
              <li key={l.id} style={{ marginBottom: "0.3rem" }}>
                <Link href={`/admin/knowledge/${l.knowledge_id}`}>
                  {l.title}
                </Link>
                <button
                  onClick={() => removeLink(l.id)}
                  style={{ marginLeft: "0.5rem", color: "crimson" }}
                  title="Hapus tautan"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
      {d.required_by.length > 0 && (
        <>
          <h3>🧭 Menjadi prasyarat untuk</h3>
          <ul>
            {d.required_by.map((l) => (
              <li key={l.id} style={{ marginBottom: "0.3rem" }}>
                <Link href={`/admin/knowledge/${l.knowledge_id}`}>
                  {l.title}
                </Link>
                <button
                  onClick={() => removeLink(l.id)}
                  style={{ marginLeft: "0.5rem", color: "crimson" }}
                  title="Hapus tautan"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      <h2>📦 File lampiran</h2>
      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          marginBottom: "0.75rem",
          flexWrap: "wrap",
        }}
      >
        <input
          key={upReset}
          type="file"
          onChange={(e) => setUpFile(e.target.files?.[0] ?? null)}
        />
        <input
          placeholder="Deskripsi file (opsional)"
          value={upDesc}
          onChange={(e) => setUpDesc(e.target.value)}
          style={{ padding: "0.5rem", flex: 1, minWidth: 200 }}
        />
        <button onClick={doUpload} disabled={!upFile || uploading}>
          {uploading ? "Mengunggah..." : "Upload"}
        </button>
      </div>
      {d.attachments.length === 0 && (
        <p style={{ color: "#999" }}>Belum ada lampiran.</p>
      )}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {d.attachments.map((a) => (
          <li
            key={a.id}
            style={{
              borderBottom: "1px solid #eee",
              padding: "0.4rem 0",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <span>
              <b>{a.original_name}</b>{" "}
              <span style={{ color: "#666", fontSize: "0.85rem" }}>
                ({fmtSize(a.size_bytes)})
              </span>
              {a.description && (
                <div style={{ color: "#666", fontSize: "0.85rem" }}>
                  {a.description}
                </div>
              )}
            </span>
            <button
              onClick={() => removeAttachment(a.id, a.original_name)}
              style={{ color: "crimson" }}
            >
              Hapus
            </button>
          </li>
        ))}
      </ul>

      <hr style={{ margin: "2rem 0 1rem" }} />
      <div style={{ display: "flex", gap: "0.75rem", paddingBottom: "2rem" }}>
        {d.status !== "sudah_direview" ? (
          <button
            onClick={doReview}
            style={{ padding: "0.7rem 1.4rem", fontWeight: 600 }}
          >
            Tandai direview
          </button>
        ) : (
          <button
            onClick={doUnreview}
            style={{ padding: "0.7rem 1.4rem" }}
          >
            Batalkan direview
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
