"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, type Me } from "@/lib/api";
import Navbar from "@/components/Navbar";
import { detectUsbDevice, webUsbSupported, type DetectedDevice } from "@/lib/detect";

type Knowledge = {
  id: string;
  title: string;
  brand: string | null;
  model: string | null;
  category: string | null;
  tags: string[];
  like_count: number;
  success_count: number;
};

const TAG_COLORS: Record<string, string> = {
  "belum direview": "#b45309",
  "sudah direview": "#1d4ed8",
  "ada testimoni": "#15803d",
};

const PER_PAGE_OPTIONS = [10, 20, 50, 100];

function KnowledgeItem({ k }: { k: Knowledge }) {
  return (
    <li style={{ borderBottom: "1px solid #ddd", padding: "0.75rem 0" }}>
      <Link href={`/knowledge/${k.id}`} style={{ fontWeight: "bold" }}>
        {k.title}
      </Link>{" "}
      {k.tags.map((t) => (
        <span
          key={t}
          style={{
            background: TAG_COLORS[t] ?? "#666",
            color: "#fff",
            fontSize: "0.75rem",
            padding: "0.15rem 0.5rem",
            borderRadius: "1rem",
            marginRight: "0.25rem",
          }}
        >
          {t}
        </span>
      ))}
      <div style={{ color: "#666", fontSize: "0.85rem" }}>
        {[k.brand, k.model, k.category].filter(Boolean).join(" · ")}
        {(k.like_count > 0 || k.success_count > 0) &&
          ` · 👍 ${k.like_count} · ✅ ${k.success_count}`}
      </div>
    </li>
  );
}

export default function Home() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [results, setResults] = useState<Knowledge[]>([]);
  const [searched, setSearched] = useState(false);
  const [device, setDevice] = useState<DetectedDevice | null>(null);
  const [error, setError] = useState("");
  // jelajah artikel terbaru (tanpa pencarian)
  const [browse, setBrowse] = useState<Knowledge[]>([]);
  const [browsePage, setBrowsePage] = useState(1);
  const [browsePerPage, setBrowsePerPage] = useState(20);
  const [browseTotal, setBrowseTotal] = useState(0);

  useEffect(() => {
    api<Me>("/auth/me")
      .then(() => setReady(true))
      .catch(() => router.push("/login"));
  }, [router]);

  function loadBrowse(page: number, perPage: number) {
    const params = new URLSearchParams({
      order: "newest",
      page: String(page),
      per_page: String(perPage),
    });
    api<{ items: Knowledge[]; total: number; page: number; per_page: number }>(
      `/knowledge?${params.toString()}`
    )
      .then((r) => {
        setBrowse(r.items);
        setBrowseTotal(r.total);
        setBrowsePage(r.page);
        setBrowsePerPage(r.per_page);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat artikel"));
  }

  useEffect(() => {
    if (ready) loadBrowse(1, browsePerPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  function changePerPage(n: number) {
    loadBrowse(1, n);
  }

  function backToBrowse() {
    setSearched(false);
    setResults([]);
    setQ("");
    loadBrowse(1, browsePerPage);
  }

  async function doSearch(query?: string) {
    const keyword = (query ?? q).trim();
    if (!keyword) return;
    setError("");
    try {
      const params = new URLSearchParams({ q: keyword });
      if (category) params.set("category", category);
      const r = await api<Knowledge[]>(`/search?${params.toString()}`);
      setResults(r);
      setSearched(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Pencarian gagal");
    }
  }

  async function doDetect() {
    setError("");
    try {
      const d = await detectUsbDevice();
      setDevice(d);
      // catat ke histori
      await api("/history/detections", {
        method: "POST",
        body: JSON.stringify({
          method: "usb",
          vid: d.vid,
          pid: d.pid,
          label: d.label,
          raw: { productName: d.productName ?? null, kind: d.kind },
        }),
      });
      // isi kotak pencarian dengan label agar user bisa cari manual
      setQ(d.label);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Deteksi gagal");
    }
  }

  if (!ready) return <main style={{ padding: "2rem" }}>Memuat...</main>;

  return (
    <main style={{ maxWidth: 760, margin: "2rem auto", padding: "0 1rem" }}>
      <Navbar />
      <h1>Pencarian knowledge</h1>

      <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
        <input
          placeholder="Kata kunci, kode HP (misal SM-A546B), atau brand..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doSearch()}
          style={{ padding: "0.6rem", flex: 1 }}
        />
        <select value={category} onChange={(e) => setCategory(e.target.value)} style={{ padding: "0.6rem" }}>
          <option value="">Semua</option>
          <option value="hardware">Hardware</option>
          <option value="software">Software</option>
        </select>
        <button onClick={() => doSearch()} style={{ padding: "0.6rem 1rem" }}>
          Cari
        </button>
      </div>

      <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
        <button
          onClick={doDetect}
          disabled={!webUsbSupported()}
          title={webUsbSupported() ? "Deteksi perangkat via USB" : "Browser tidak mendukung WebUSB"}
          style={{ padding: "0.5rem 1rem" }}
        >
          Deteksi perangkat (USB)
        </button>
        <span style={{ color: "#666", fontSize: "0.85rem" }}>
          HP mati terdeteksi sampai level chipset (EDL 9008 / MTK preloader).
        </span>
      </div>

      {device && (
        <div style={{ background: "#eef6ff", padding: "0.75rem 1rem", marginTop: "0.75rem", borderRadius: "0.5rem" }}>
          Terdeteksi: <b>{device.label}</b>{" "}
          <span style={{ color: "#666" }}>({device.vid}:{device.pid})</span>
        </div>
      )}
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {searched ? (
        <>
          <h2 style={{ marginTop: "1.5rem" }}>
            Hasil pencarian ({results.length})
          </h2>
          <button onClick={backToBrowse} style={{ marginBottom: "0.5rem" }}>
            ← Kembali ke artikel terbaru
          </button>
          {results.length === 0 && <p>Tidak ada knowledge yang cocok.</p>}
          <ul style={{ listStyle: "none", padding: 0 }}>
            {results.map((k) => (
              <KnowledgeItem key={k.id} k={k} />
            ))}
          </ul>
        </>
      ) : (
        <>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginTop: "1.5rem",
            }}
          >
            <h2 style={{ margin: 0 }}>Artikel terbaru</h2>
            <label style={{ fontSize: "0.85rem", color: "#666" }}>
              Tampil:{" "}
              <select
                value={browsePerPage}
                onChange={(e) => changePerPage(Number(e.target.value))}
              >
                {PER_PAGE_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {browse.length === 0 && <p>Belum ada artikel.</p>}
          <ul style={{ listStyle: "none", padding: 0 }}>
            {browse.map((k) => (
              <KnowledgeItem key={k.id} k={k} />
            ))}
          </ul>
          {browseTotal > browsePerPage && (
            <div
              style={{
                display: "flex",
                gap: "0.75rem",
                alignItems: "center",
                marginTop: "1rem",
              }}
            >
              <button
                onClick={() => loadBrowse(browsePage - 1, browsePerPage)}
                disabled={browsePage <= 1}
              >
                ← Sebelumnya
              </button>
              <span style={{ fontSize: "0.85rem", color: "#666" }}>
                Halaman {browsePage} dari {Math.ceil(browseTotal / browsePerPage)}
              </span>
              <button
                onClick={() => loadBrowse(browsePage + 1, browsePerPage)}
                disabled={browsePage >= Math.ceil(browseTotal / browsePerPage)}
              >
                Berikutnya →
              </button>
            </div>
          )}
        </>
      )}
    </main>
  );
}
