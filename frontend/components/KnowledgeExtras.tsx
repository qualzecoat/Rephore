"use client";

import Link from "next/link";
import { API_URL, getToken } from "@/lib/api";

export type LinkedArticle = {
  id: string;
  knowledge_id: string;
  title: string;
  brand: string | null;
  model: string | null;
  relation: string;
};

export type Attachment = {
  id: string;
  original_name: string;
  size_bytes: number;
  mime_type: string | null;
  description: string;
  created_at: string;
};

export function fmtSize(b: number): string {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  if (b < 1024 * 1024 * 1024) return `${(b / 1024 / 1024).toFixed(1)} MB`;
  return `${(b / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function LinkList({ items }: { items: LinkedArticle[] }) {
  return (
    <ul style={{ margin: "0.4rem 0", paddingLeft: "1.2rem" }}>
      {items.map((l) => (
        <li key={l.id} style={{ marginBottom: "0.25rem" }}>
          <Link href={`/knowledge/${l.knowledge_id}`}>{l.title}</Link>
          {[l.brand, l.model].filter(Boolean).length > 0 && (
            <span style={{ color: "#666", fontSize: "0.85rem" }}>
              {" "}
              — {[l.brand, l.model].filter(Boolean).join(" ")}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}

async function downloadAttachment(a: Attachment) {
  const token = getToken();
  try {
    const res = await fetch(`${API_URL}/knowledge/attachments/${a.id}/download`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error();
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const el = document.createElement("a");
    el.href = url;
    el.download = a.original_name;
    document.body.appendChild(el);
    el.click();
    el.remove();
    URL.revokeObjectURL(url);
  } catch {
    alert("Gagal mengunduh file");
  }
}

/** Kotak prasyarat / terkait / dibutuhkan-oleh / lampiran di bawah isi artikel. */
export default function KnowledgeExtras({
  prerequisites,
  requiredBy,
  related,
  attachments,
}: {
  prerequisites: LinkedArticle[];
  requiredBy: LinkedArticle[];
  related: LinkedArticle[];
  attachments: Attachment[];
}) {
  return (
    <>
      {prerequisites.length > 0 && (
        <section
          style={{
            background: "#fef3c7",
            border: "1px solid #f59e0b",
            borderRadius: "0.5rem",
            padding: "0.75rem 1rem",
            marginTop: "1.5rem",
          }}
        >
          <b>📚 Prasyarat</b>
          <p style={{ margin: "0.25rem 0", fontSize: "0.9rem" }}>
            Sebelum mengikuti tutorial ini, pahami dulu:
          </p>
          <LinkList items={prerequisites} />
        </section>
      )}

      {attachments.length > 0 && (
        <section style={{ marginTop: "1.5rem" }}>
          <h2>📦 File lampiran ({attachments.length})</h2>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {attachments.map((a) => (
              <li
                key={a.id}
                style={{
                  border: "1px solid #ddd",
                  borderRadius: "0.5rem",
                  padding: "0.6rem 0.9rem",
                  marginBottom: "0.5rem",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "1rem",
                }}
              >
                <div>
                  <b>{a.original_name}</b>{" "}
                  <span style={{ color: "#666", fontSize: "0.85rem" }}>
                    ({fmtSize(a.size_bytes)})
                  </span>
                  {a.description && (
                    <div style={{ color: "#666", fontSize: "0.85rem" }}>
                      {a.description}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => downloadAttachment(a)}
                  style={{ padding: "0.4rem 0.9rem", whiteSpace: "nowrap" }}
                >
                  ⬇ Unduh
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {(related.length > 0 || requiredBy.length > 0) && (
        <section style={{ marginTop: "1.5rem" }}>
          {related.length > 0 && (
            <>
              <h2>🔗 Artikel terkait</h2>
              <LinkList items={related} />
            </>
          )}
          {requiredBy.length > 0 && (
            <>
              <h2>🧭 Artikel ini menjadi prasyarat untuk</h2>
              <LinkList items={requiredBy} />
            </>
          )}
        </section>
      )}
    </>
  );
}
