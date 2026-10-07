"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Reply = {
  id: string;
  username: string;
  role: string;
  message: string;
  created_at: string;
};

/** Thread balasan sebuah laporan. Aturan: admin selalu boleh membalas;
 *  user biasa hanya setelah admin membalas; tidak ada yang bisa membalas
 *  bila balasan ditutup. */
export default function ReportThread({
  reportId,
  isAdmin,
  repliesClosed,
}: {
  reportId: string;
  isAdmin: boolean;
  repliesClosed: boolean;
}) {
  const [replies, setReplies] = useState<Reply[]>([]);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  function load() {
    api<Reply[]>(`/reports/${reportId}/replies`)
      .then(setReplies)
      .catch(() => {});
  }

  useEffect(load, [reportId]);

  const adminReplied = replies.some((r) => r.role === "admin");
  const canReply = !repliesClosed && (isAdmin || adminReplied);

  async function send() {
    if (!msg.trim()) return;
    setError("");
    try {
      await api(`/reports/${reportId}/replies`, {
        method: "POST",
        body: JSON.stringify({ message: msg }),
      });
      setMsg("");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal mengirim balasan");
    }
  }

  return (
    <div
      style={{
        marginTop: "0.75rem",
        paddingTop: "0.75rem",
        borderTop: "1px dashed #ccc",
      }}
    >
      {replies.length === 0 && (
        <p style={{ color: "#999", fontSize: "0.85rem" }}>Belum ada balasan.</p>
      )}
      {replies.map((r) => (
        <div key={r.id} style={{ marginBottom: "0.6rem" }}>
          <div style={{ fontSize: "0.8rem", color: "#666" }}>
            <b>{r.username}</b>
            {r.role === "admin" && (
              <span
                style={{
                  background: "#1d4ed8",
                  color: "#fff",
                  fontSize: "0.7rem",
                  padding: "0.1rem 0.4rem",
                  borderRadius: "1rem",
                  marginLeft: "0.4rem",
                }}
              >
                admin
              </span>
            )}{" "}
            · {new Date(r.created_at).toLocaleString("id-ID")}
          </div>
          <div style={{ whiteSpace: "pre-wrap" }}>{r.message}</div>
        </div>
      ))}

      {error && <p style={{ color: "crimson", fontSize: "0.85rem" }}>{error}</p>}

      {canReply ? (
        <div style={{ marginTop: "0.5rem" }}>
          <textarea
            value={msg}
            onChange={(e) => setMsg(e.target.value)}
            rows={2}
            placeholder="Tulis balasan..."
            style={{ width: "100%", padding: "0.5rem", boxSizing: "border-box" }}
          />
          <button onClick={send} style={{ marginTop: "0.25rem" }}>
            Kirim balasan
          </button>
        </div>
      ) : (
        <p style={{ color: "#999", fontSize: "0.85rem", marginTop: "0.5rem" }}>
          {repliesClosed
            ? "🔒 Balasan ditutup oleh admin."
            : "Menunggu balasan admin — kamu bisa membalas setelah admin merespons."}
        </p>
      )}
    </div>
  );
}
