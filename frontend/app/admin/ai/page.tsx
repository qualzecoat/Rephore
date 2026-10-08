"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, type Me } from "@/lib/api";
import Navbar from "@/components/Navbar";

type Provider = {
  id: string;
  name: string;
  base_url: string;
  has_api_key: boolean;
  default_model: string;
  embedding_model: string | null;
  is_active: boolean;
};

type Job = {
  id: string;
  type: string;
  brand: string | null;
  phone_model: string | null;
  category: string | null;
  subcategory: string | null;
  topic: string | null;
  status: string;
  result_knowledge_id: string | null;
  error: string | null;
  created_at: string;
};

type Schedule = {
  id: string;
  name: string;
  provider_id: string;
  brand: string | null;
  phone_model: string | null;
  category: string | null;
  topic: string | null;
  run_hour: number;
  dedup_days: number | null;
  is_active: boolean;
  constraint: string | null;
  last_run_date: string | null;
};

const inputStyle = { padding: "0.5rem", margin: "0.15rem" } as const;

export default function AdminAiPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [error, setError] = useState("");

  // form provider
  const [pName, setPName] = useState("");
  const [pUrl, setPUrl] = useState("https://api.openai.com/v1");
  const [pKey, setPKey] = useState("");
  const [pModel, setPModel] = useState("");
  const [pEmb, setPEmb] = useState("");
  const [models, setModels] = useState<string[]>([]);

  // form job manual
  const [jProvider, setJProvider] = useState("");
  const [jBrand, setJBrand] = useState("");
  const [jModel, setJModel] = useState("");
  const [jCat, setJCat] = useState("software");
  const [jSub, setJSub] = useState("");
  const [jTopic, setJTopic] = useState("");

  // form schedule — 1 jadwal = 1 topik per hari
  const [sName, setSName] = useState("");
  const [sProvider, setSProvider] = useState("");
  const [sBrand, setSBrand] = useState("");
  const [sModel, setSModel] = useState("");
  const [sCat, setSCat] = useState("software");
  const [sTopic, setSTopic] = useState("root");
  const [sHour, setSHour] = useState(2);
  const [sDedup, setSDedup] = useState(30);
  const [sConstraint, setSConstraint] = useState("");

  function load() {
    api<Provider[]>("/ai/providers").then(setProviders).catch(() => {});
    api<Job[]>("/ai/jobs").then(setJobs).catch(() => {});
    api<Schedule[]>("/ai/schedules").then(setSchedules).catch(() => {});
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
    const t = setInterval(() => {
      api<Job[]>("/ai/jobs").then(setJobs).catch(() => {});
    }, 8000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  async function previewModels() {
    setError("");
    try {
      const r = await api<{ models: string[] }>("/ai/providers/preview-models", {
        method: "POST",
        body: JSON.stringify({ base_url: pUrl, api_key: pKey }),
      });
      setModels(r.models);
      if (r.models.length > 0 && !pModel) setPModel(r.models[0]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal mengambil model");
    }
  }

  async function saveProvider(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api("/ai/providers", {
        method: "POST",
        body: JSON.stringify({
          name: pName,
          base_url: pUrl,
          api_key: pKey,
          default_model: pModel,
          embedding_model: pEmb || null,
        }),
      });
      setPName(""); setPKey(""); setPModel(""); setPEmb(""); setModels([]);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal menyimpan provider");
    }
  }

  async function toggleProvider(p: Provider) {
    await api(`/ai/providers/${p.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !p.is_active }),
    });
    load();
  }

  async function deleteProvider(id: string) {
    if (!confirm("Hapus provider ini?")) return;
    setError("");
    try {
      await api(`/ai/providers/${id}`, { method: "DELETE" });
      load();
    } catch (e) {
      let msg = "Gagal menghapus provider";
      if (e instanceof Error) {
        try {
          msg = JSON.parse(e.message).detail ?? e.message;
        } catch {
          msg = e.message;
        }
      }
      setError(msg);
    }
  }

  async function submitJob(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api("/ai/jobs", {
        method: "POST",
        body: JSON.stringify({
          provider_id: jProvider,
          brand: jBrand || null,
          phone_model: jModel || null,
          category: jCat || null,
          subcategory: jSub || null,
          topic: jTopic || null,
        }),
      });
      setJTopic("");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal membuat job");
    }
  }

  async function submitSchedule(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api("/ai/schedules", {
        method: "POST",
        body: JSON.stringify({
          name: sName,
          provider_id: sProvider,
          brand: sBrand || null,
          phone_model: sModel || null,
          category: sCat || null,
          topic: sTopic,
          run_hour: sHour,
          dedup_days: sDedup,
          constraint: sConstraint.trim() || null,
        }),
      });
      setSName("");
      setSConstraint("");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal menyimpan jadwal");
    }
  }

  async function toggleSchedule(s: Schedule) {
    await api(`/ai/schedules/${s.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !s.is_active }),
    });
    load();
  }

  async function deleteSchedule(s: Schedule) {
    if (!confirm(`Hapus jadwal "${s.name}"? Tidak bisa dikembalikan.`)) return;
    try {
      await api(`/ai/schedules/${s.id}`, { method: "DELETE" });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal menghapus jadwal");
    }
  }

  if (!me) return <main style={{ padding: "2rem" }}>Memuat...</main>;

  return (
    <main style={{ maxWidth: 900, margin: "2rem auto", padding: "0 1rem" }}>
      <Navbar />
      <h1>AI Provider & Generate</h1>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <h2>Provider</h2>
      <ul>
        {providers.map((p) => (
          <li key={p.id} style={{ marginBottom: "0.4rem" }}>
            <b>{p.name}</b> <span style={{ color: "#666" }}>{p.base_url}</span>{" "}
            [{p.default_model || "-"}] {p.is_active ? "✅" : "⏸️"}
            <button onClick={() => toggleProvider(p)} style={{ marginLeft: "0.5rem" }}>
              {p.is_active ? "Nonaktifkan" : "Aktifkan"}
            </button>
            <button onClick={() => deleteProvider(p.id)} style={{ marginLeft: "0.25rem" }}>
              Hapus
            </button>
          </li>
        ))}
      </ul>
      <h3>Tambah provider</h3>
      <form onSubmit={saveProvider}>
        <input placeholder="Nama (misal OpenRouter)" value={pName} onChange={(e) => setPName(e.target.value)} required style={inputStyle} />
        <input placeholder="Base URL" value={pUrl} onChange={(e) => setPUrl(e.target.value)} required style={{ ...inputStyle, width: "16rem" }} />
        <input placeholder="API key" type="password" value={pKey} onChange={(e) => setPKey(e.target.value)} required style={inputStyle} />
        <button type="button" onClick={previewModels} style={{ ...inputStyle }}>
          Ambil daftar model
        </button>
        {models.length > 0 && (
          <select value={pModel} onChange={(e) => setPModel(e.target.value)} style={inputStyle}>
            {models.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        )}
        <input placeholder="Model default (atau pilih di atas)" value={pModel} onChange={(e) => setPModel(e.target.value)} style={inputStyle} />
        <input placeholder="Model embedding (opsional)" value={pEmb} onChange={(e) => setPEmb(e.target.value)} style={inputStyle} />
        <button type="submit" style={inputStyle}>Simpan provider</button>
      </form>

      <h2 style={{ marginTop: "2rem" }}>Minta AI buatkan knowledge</h2>
      <form onSubmit={submitJob}>
        <select value={jProvider} onChange={(e) => setJProvider(e.target.value)} required style={inputStyle}>
          <option value="">Pilih provider</option>
          {providers.filter((p) => p.is_active).map((p) => (
            <option key={p.id} value={p.id}>{p.name} ({p.default_model})</option>
          ))}
        </select>
        <input placeholder="Brand (misal Xiaomi)" value={jBrand} onChange={(e) => setJBrand(e.target.value)} style={inputStyle} />
        <input placeholder="Model HP" value={jModel} onChange={(e) => setJModel(e.target.value)} style={inputStyle} />
        <select value={jCat} onChange={(e) => setJCat(e.target.value)} style={inputStyle}>
          <option value="software">software</option>
          <option value="hardware">hardware</option>
        </select>
        <input placeholder="Subkategori (misal bypass FRP)" value={jSub} onChange={(e) => setJSub(e.target.value)} style={inputStyle} />
        <input placeholder="Topik khusus (opsional)" value={jTopic} onChange={(e) => setJTopic(e.target.value)} style={{ ...inputStyle, width: "16rem" }} />
        <button type="submit" style={inputStyle}>Kirim ke AI</button>
      </form>
      <p style={{ color: "#666", fontSize: "0.85rem" }}>
        Hasilnya masuk antrean worker (±1 menit), lalu tampil di daftar knowledge dengan tag belum direview.
      </p>

      <h2>Antrean job</h2>
      <ul>
        {jobs.map((j) => (
          <li key={j.id} style={{ marginBottom: "0.4rem" }}>
            [{j.status}]{j.status === "flagged" && " ⚠️ aturan tidak terpenuhi"} {j.type} — {[j.brand, j.phone_model, j.category, j.subcategory, j.topic].filter(Boolean).join(" · ")}
            {j.result_knowledge_id && (
              <> → <Link href={`/knowledge/${j.result_knowledge_id}`}>lihat hasil</Link></>
            )}
            {j.error && <span style={{ color: "crimson" }}> — {j.error.slice(0, 120)}</span>}
          </li>
        ))}
        {jobs.length === 0 && <li>Belum ada job.</li>}
      </ul>

      <h2 style={{ marginTop: "2rem" }}>Jadwal otomatis</h2>
      <p style={{ color: "#666", fontSize: "0.85rem" }}>
        1 jadwal = 1 topik yang dirilis tiap hari di jam yang ditentukan.
        Mau 2–3 artikel per hari? Buat 2–3 jadwal dengan topik berbeda.
      </p>
      <ul>
        {schedules.map((s) => (
          <li key={s.id} style={{ marginBottom: "0.4rem" }}>
            <b>{s.name}</b> — tiap hari jam {s.run_hour}:00, topik: {s.topic || "-"}
            <span style={{ color: "#666" }}> (anti-duplikat {s.dedup_days ?? 30} hari)</span>
            {s.constraint && <span style={{ color: "#a60" }}> ⛔ Aturan: {s.constraint}</span>}
            {[s.brand, s.phone_model, s.category].filter(Boolean).length > 0 &&
              ` (${[s.brand, s.phone_model, s.category].filter(Boolean).join(" · ")})`}
            {s.last_run_date && <span style={{ color: "#666" }}> (terakhir: {s.last_run_date})</span>}{" "}
            {s.is_active ? "✅" : "⏸️"}
            <button onClick={() => toggleSchedule(s)} style={{ marginLeft: "0.5rem" }}>
              {s.is_active ? "Nonaktifkan" : "Aktifkan"}
            </button>
            {!s.is_active && (
              <button onClick={() => deleteSchedule(s)} style={{ marginLeft: "0.5rem" }}>
                Hapus
              </button>
            )}
          </li>
        ))}
      </ul>
      <h3>Tambah jadwal</h3>
      <form onSubmit={submitSchedule}>
        <input placeholder="Nama jadwal (misal Root harian)" value={sName} onChange={(e) => setSName(e.target.value)} required style={inputStyle} />
        <select value={sProvider} onChange={(e) => setSProvider(e.target.value)} required style={inputStyle}>
          <option value="">Pilih provider</option>
          {providers.filter((p) => p.is_active).map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <input placeholder="Brand target (misal Xiaomi)" value={sBrand} onChange={(e) => setSBrand(e.target.value)} style={inputStyle} />
        <input placeholder="Model HP target (opsional)" value={sModel} onChange={(e) => setSModel(e.target.value)} style={inputStyle} />
        <select value={sCat} onChange={(e) => setSCat(e.target.value)} style={inputStyle}>
          <option value="software">software</option>
          <option value="hardware">hardware</option>
        </select>
        <input placeholder="Topik (misal root)" value={sTopic} onChange={(e) => setSTopic(e.target.value)} required style={inputStyle} />
        <input placeholder="Aturan keras (opsional, misal: tanpa akun Mi Cloud)" value={sConstraint} onChange={(e) => setSConstraint(e.target.value)} title="Dicek ke bahan riset sebelum AI menulis. Bila tidak terpenuhi, job ditandai — bukan ditulis diam-diam." style={{ ...inputStyle, width: "18rem" }} />
        <label style={inputStyle}>Jam: <input type="number" min={0} max={23} value={sHour} onChange={(e) => setSHour(Number(e.target.value))} style={{ width: "3rem" }} /></label>
        <label style={inputStyle} title="Jadwal dilewati bila artikel mirip sudah ada dalam N hari terakhir">Anti-duplikat (hari): <input type="number" min={1} max={365} value={sDedup} onChange={(e) => setSDedup(Number(e.target.value))} style={{ width: "3.5rem" }} /></label>
        <button type="submit" style={inputStyle}>Simpan jadwal</button>
      </form>
    </main>
  );
}
