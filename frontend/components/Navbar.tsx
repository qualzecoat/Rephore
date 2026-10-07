"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, clearToken, type Me } from "@/lib/api";

const linkStyle = { marginRight: "0.9rem" } as const;

/** Navbar bersama untuk semua halaman — mengambil info login sendiri. */
export default function Navbar() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null | undefined>(undefined);

  useEffect(() => {
    api<Me>("/auth/me")
      .then(setMe)
      .catch(() => setMe(null));
  }, []);

  // v1 log watcher: laporkan JS error ke backend (dibatasi 1x/menit)
  useEffect(() => {
    if (!me) return;
    let lastSent = 0;
    function send(message: string, stack?: string) {
      const now = Date.now();
      if (now - lastSent < 60000) return;
      lastSent = now;
      api("/logwatch/errors", {
        method: "POST",
        body: JSON.stringify({
          message: message.slice(0, 500),
          stack: (stack ?? "").slice(0, 2000),
        }),
      }).catch(() => {});
    }
    const onError = (e: ErrorEvent) =>
      send(e.message || "Unknown error", (e as any).error?.stack);
    const onRejection = (e: PromiseRejectionEvent) => {
      const r = e.reason as any;
      send(String(r?.message ?? r ?? "Unhandled rejection").slice(0, 500), r?.stack);
    };
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, [me]);

  function logout() {
    clearToken();
    router.push("/login");
  }

  return (
    <nav
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0.75rem 0",
        marginBottom: "1rem",
        borderBottom: "1px solid #e5e5e5",
      }}
    >
      <div style={{ display: "flex", alignItems: "center" }}>
        <Link href="/" style={{ ...linkStyle, fontWeight: 700, fontSize: "1.1rem" }}>
          Rephore
        </Link>
        {me && (
          <Link href="/history" style={linkStyle}>
            Riwayat
          </Link>
        )}
        {me?.role === "admin" && (
          <span style={{ color: "#666" }}>
            <Link href="/admin/knowledge" style={linkStyle}>
              Knowledge
            </Link>
            <Link href="/admin/users" style={linkStyle}>
              Users
            </Link>
            <Link href="/admin/ai" style={linkStyle}>
              AI
            </Link>
            <Link href="/admin/reports" style={linkStyle}>
              Laporan
            </Link>
            <Link href="/admin/saran-ai" style={linkStyle}>
              Saran AI
            </Link>
            <Link href="/admin/history" style={linkStyle}>
              Histori
            </Link>
          </span>
        )}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        {me === undefined ? null : me ? (
          <>
            <span style={{ color: "#666", fontSize: "0.9rem" }}>{me.username}</span>
            <button onClick={logout}>Keluar</button>
          </>
        ) : (
          <Link href="/login">Masuk</Link>
        )}
      </div>
    </nav>
  );
}
