"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Me } from "@/lib/api";
import Navbar from "@/components/Navbar";

type Setting = {
  key: string;
  section: string;
  label: string;
  desc: string;
  type: "text" | "password" | "number" | "boolean" | "textarea";
  placeholders: string[];
  default: string;
  value: string;
  is_set: boolean;
  source: "db" | "env" | "default";
};

const inputStyle = {
  padding: "0.5rem",
  margin: "0.15rem 0",
  width: "100%",
  boxSizing: "border-box",
} as const;

const cardStyle = {
  border: "1px solid #e5e5e5",
  borderRadius: "8px",
  padding: "1rem",
  marginBottom: "1rem",
} as const;

const sourceLabel: Record<string, string> = {
  db: "diubah",
  env: "dari environment",
  default: "default",
};

export default function AdminPengaturanPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [settings, setSettings] = useState<Setting[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try {
      const m = await api<Me>("/auth/me");
      if (m.role !== "admin") {
        router.push("/");
        return;
      }
      setMe(m);
      const list = await api<Setting[]>("/settings");
      setSettings(list);
      const d: Record<string, string> = {};
      for (const s of list) {
        // password selalu mulai kosong: kosong = biarkan nilai lama
        d[s.key] = s.type === "password" ? "" : s.value;
      }
      setDrafts(d);
      setMsg("");
    } catch (e) {
      setError(String((e as Error).message || e));
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function save(key: string) {
    setError("");
    setMsg("");
    try {
      await api(`/settings/${key}`, {
        method: "PUT",
        body: JSON.stringify({ value: drafts[key] ?? "" }),
      });
      setMsg(`Tersimpan: ${key}`);
      load();
    } catch (e) {
      setError(String((e as Error).message || e));
    }
  }

  async function reset(key: string) {
    if (!confirm(`Kembalikan "${key}" ke nilai default?`)) return;
    setError("");
    setMsg("");
    try {
      await api(`/settings/${key}`, { method: "DELETE" });
      setMsg(`Dikembalikan ke default: ${key}`);
      load();
    } catch (e) {
      setError(String((e as Error).message || e));
    }
  }

  function renderInput(s: Setting) {
    const v = drafts[s.key] ?? "";
    const set = (val: string) => setDrafts({ ...drafts, [s.key]: val });
    if (s.type === "boolean") {
      return (
        <label>
          <input
            type="checkbox"
            checked={v === "1"}
            onChange={(e) => set(e.target.checked ? "1" : "0")}
          />{" "}
          Aktif
        </label>
      );
    }
    if (s.type === "number") {
      return (
        <input
          type="number"
          value={v}
          onChange={(e) => set(e.target.value)}
          style={inputStyle}
        />
      );
    }
    if (s.type === "password") {
      return (
        <input
          type="password"
          value={v}
          placeholder={
            s.is_set ? "Tersimpan — kosongkan untuk tidak mengubah" : "Belum diset"
          }
          onChange={(e) => set(e.target.value)}
          style={inputStyle}
          autoComplete="new-password"
        />
      );
    }
    if (s.type === "textarea") {
      return (
        <textarea
          value={v}
          onChange={(e) => set(e.target.value)}
          rows={10}
          style={{ ...inputStyle, fontFamily: "monospace", fontSize: "0.85rem" }}
        />
      );
    }
    return (
      <input
        type="text"
        value={v}
        onChange={(e) => set(e.target.value)}
        style={inputStyle}
      />
    );
  }

  const sections: string[] = [];
  for (const s of settings) {
    if (!sections.includes(s.section)) sections.push(s.section);
  }

  return (
    <main style={{ maxWidth: "900px", margin: "0 auto", padding: "1rem" }}>
      <Navbar />
      <h1>Pengaturan AI</h1>
      <p style={{ color: "#666" }}>
        Semua pengaturan fitur AI &amp; generate artikel. Nilai default bawaan
        kode dipakai bila tidak diubah — tombol &ldquo;Reset&rdquo; mengembalikan
        ke default kapan saja.
      </p>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {msg && <p style={{ color: "green" }}>{msg}</p>}
      {!me ? (
        <p>Memuat...</p>
      ) : (
        sections.map((sec) => (
          <section key={sec} style={{ marginTop: "1.5rem" }}>
            <h2>{sec}</h2>
            {settings
              .filter((s) => s.section === sec)
              .map((s) => (
                <div key={s.key} style={cardStyle}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "baseline",
                    }}
                  >
                    <strong>{s.label}</strong>
                    <span
                      style={{
                        fontSize: "0.8rem",
                        color: "#666",
                        background: "#f0f0f0",
                        padding: "0.15rem 0.5rem",
                        borderRadius: "4px",
                      }}
                    >
                      {sourceLabel[s.source]} · <code>{s.key}</code>
                    </span>
                  </div>
                  {s.desc && (
                    <p style={{ color: "#666", fontSize: "0.9rem" }}>{s.desc}</p>
                  )}
                  {s.placeholders.length > 0 && (
                    <p style={{ fontSize: "0.85rem", color: "#666" }}>
                      Variabel:{" "}
                      {s.placeholders.map((p) => (
                        <code key={p} style={{ marginRight: "0.4rem" }}>
                          {"{" + p + "}"}
                        </code>
                      ))}
                    </p>
                  )}
                  <div style={{ marginTop: "0.5rem" }}>{renderInput(s)}</div>
                  <div style={{ marginTop: "0.5rem" }}>
                    <button onClick={() => save(s.key)} style={{ marginRight: "0.5rem" }}>
                      Simpan
                    </button>
                    <button onClick={() => reset(s.key)}>Reset ke default</button>
                  </div>
                </div>
              ))}
          </section>
        ))
      )}
    </main>
  );
}
