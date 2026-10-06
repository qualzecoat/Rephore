"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Me } from "@/lib/api";

type Knowledge = {
  id: string;
  title: string;
  brand: string | null;
  model: string | null;
  category: string | null;
  status: string;
  tag: string;
  like_count: number;
  success_count: number;
};

type Parsed = {
  data: {
    title: string;
    meta: Record<string, unknown>;
    tools: string[];
    steps: { n: number; instruksi: string; commands: string[]; warnings: string[] }[];
    troubleshooting: string;
    warnings: string[];
  };
  warnings: string[];
};

const TEMPLATE = `[knowledge]
[title]Judul tutorial[/title]
[meta brand="" model="" codes="" category="hardware" subcategory="" difficulty="" est_time=""]
[tools]
- Alat 1
- Alat 2
[/tools]
[steps]
[step n="1"]
[instruksi]Langkah pertama...[/instruksi]
[command]adb ...[/command]
[warning]Hal yang perlu diwaspadai...[/warning]
[/step]
[/steps]
[troubleshooting]Jika gagal, coba...[/troubleshooting]
[/knowledge]`;

const TAG_COLORS: Record<string, string> = {
  "belum direview": "#b45309",
  "sudah direview": "#1d4ed8",
  "ada testimoni": "#15803d",
};

export default function AdminKnowledgePage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [items, setItems] = useState<Knowledge[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [q, setQ] = useState("");
  const [bbcode, setBbcode] = useState(TEMPLATE);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [preview, setPreview] = useState<Parsed | null>(null);
  const [error, setError] = useState("");

  function load() {
    const params = new URLSearchParams();
    if (statusFilter) params.set("status_filter", statusFilter);
    if (q) params.set("q", q);
    api<Knowledge[]>(`/knowledge?${params.toString()}`).then(setItems).catch((e) => setError(String(e)));
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

  useEffect(() => {
    if (me) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me]);

  async function doPreview() {
    setError("");
    try {
      const p = await api<Parsed>("/knowledge/parse", {
        method: "POST",
        body: JSON.stringify({ bbcode }),
      });
      setPreview(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Parse gagal");
    }
  }

  async function doSave() {
    setError("");
    try {
      if (editingId) {
        await api(`/knowledge/${editingId}`, {
          method: "PATCH",
          body: JSON.stringify({ bbcode }),
        });
      } else {
        await api("/knowledge", {
          method: "POST",
          body: JSON.stringify({ bbcode, source: "manual" }),
        });
      }
      setBbcode(TEMPLATE);
      setEditingId(null);
      setPreview(null);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simpan gagal");
    }
  }

  async function doEdit(id: string) {
    setError("");
    try {
      const d = await api<{ content_markdown: string }>(`/knowledge/${id}`);
      setBbcode(d.content_markdown);
      setEditingId(id);
      window.scrollTo({ top: 0 });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal memuat");
    }
  }

  async function doReview(id: string) {
    await api(`/knowledge/${id}/review`, { method: "POST" });
    load();
  }

  async function doDelete(id: string) {
    if (!confirm("Hapus knowledge ini?")) return;
    await api(`/knowledge/${id}`, { method: "DELETE" });
    if (id === editingId) {
      setEditingId(null);
      setBbcode(TEMPLATE);
      setPreview(null);
    }
    load();
  }

  if (!me) return <main style={{ padding: "2rem" }}>Memuat...</main>;

  return (
    <main style={{ maxWidth: 900, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>Kelola Knowledge</h1>

      <h2>{editingId ? "Edit knowledge" : "Buat knowledge baru"}</h2>
      <textarea
        value={bbcode}
        onChange={(e) => setBbcode(e.target.value)}
        rows={14}
        style={{ width: "100%", fontFamily: "monospace", padding: "0.5rem" }}
      />
      <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
        <button onClick={doPreview} style={{ padding: "0.5rem 1rem" }}>
          Preview parse
        </button>
        <button onClick={doSave} style={{ padding: "0.5rem 1rem" }}>
          {editingId ? "Simpan perubahan" : "Simpan knowledge"}
        </button>
        {editingId && (
          <button
            onClick={() => {
              setEditingId(null);
              setBbcode(TEMPLATE);
              setPreview(null);
            }}
            style={{ padding: "0.5rem 1rem" }}
          >
            Batal
          </button>
        )}
      </div>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {preview && (
        <div style={{ background: "#f5f5f5", padding: "1rem", marginTop: "1rem" }}>
          <h3>Hasil parse</h3>
          {preview.warnings.length > 0 && (
            <div style={{ color: "#b45309" }}>
              <b>Warnings:</b>
              <ul>
                {preview.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
          <p>
            <b>{preview.data.title}</b> — {preview.data.steps.length} langkah,{" "}
            {preview.data.tools.length} alat
          </p>
          <pre style={{ fontSize: "0.8rem", overflow: "auto" }}>
            {JSON.stringify(preview.data, null, 1)}
          </pre>
        </div>
      )}

      <h2 style={{ marginTop: "2rem" }}>Daftar knowledge</h2>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ padding: "0.5rem" }}>
          <option value="">Semua status</option>
          <option value="belum_direview">Belum direview</option>
          <option value="sudah_direview">Sudah direview</option>
        </select>
        <input
          placeholder="Cari judul / brand / model..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          style={{ padding: "0.5rem", flex: 1 }}
        />
        <button onClick={load} style={{ padding: "0.5rem 1rem" }}>
          Cari
        </button>
      </div>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {items.map((k) => (
          <li key={k.id} style={{ borderBottom: "1px solid #ddd", padding: "0.75rem 0" }}>
            <div>
              <b>{k.title}</b>{" "}
              <span
                style={{
                  background: TAG_COLORS[k.tag] ?? "#666",
                  color: "#fff",
                  fontSize: "0.75rem",
                  padding: "0.15rem 0.5rem",
                  borderRadius: "1rem",
                }}
              >
                {k.tag}
              </span>
            </div>
            <div style={{ color: "#666", fontSize: "0.85rem" }}>
              {[k.brand, k.model, k.category].filter(Boolean).join(" · ")}
              {(k.like_count > 0 || k.success_count > 0) &&
                ` · 👍 ${k.like_count} · ✅ ${k.success_count}`}
            </div>
            <div style={{ marginTop: "0.4rem", display: "flex", gap: "0.5rem" }}>
              <button onClick={() => doEdit(k.id)}>Edit</button>
              {k.status === "belum_direview" && (
                <button onClick={() => doReview(k.id)}>Tandai direview</button>
              )}
              <button onClick={() => doDelete(k.id)}>Hapus</button>
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}
