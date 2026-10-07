"use client";

export type ContentStep = {
  n: number;
  instruksi: string;
  commands: string[];
  warnings: string[];
};

export type KnowledgeContentData = {
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
  content_json: { steps: ContentStep[] };
};

/** Render isi knowledge (judul, meta, tag, alat, langkah, troubleshooting). */
export default function KnowledgeContent({ d }: { d: KnowledgeContentData }) {
  return (
    <>
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
              <pre
                key={i}
                style={{
                  background: "#1e1e1e",
                  color: "#d4d4d4",
                  padding: "0.5rem",
                  borderRadius: "0.25rem",
                  overflowX: "auto",
                }}
              >
                {c}
              </pre>
            ))}
            {s.warnings.map((w, i) => (
              <p
                key={i}
                style={{ background: "#fef3c7", padding: "0.5rem", borderRadius: "0.25rem" }}
              >
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
    </>
  );
}
