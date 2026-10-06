"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken, type Me } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const tok = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setToken(tok.access_token);
      const me = await api<Me>("/auth/me");
      router.push(me.role === "admin" ? "/admin/users" : "/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login gagal");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 360, margin: "6rem auto", padding: "0 1rem" }}>
      <h1>Rephore — Login</h1>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.75rem" }}>
        <input
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          style={{ padding: "0.6rem" }}
        />
        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          style={{ padding: "0.6rem" }}
        />
        {error && <p style={{ color: "crimson" }}>{error}</p>}
        <button type="submit" disabled={loading} style={{ padding: "0.6rem" }}>
          {loading ? "Masuk..." : "Masuk"}
        </button>
      </form>
      <p style={{ color: "#666", fontSize: "0.85rem", marginTop: "1rem" }}>
        Akun hanya bisa dibuat oleh admin. Admin pertama dibuat via{" "}
        <code>POST /auth/seed-admin</code>.
      </p>
    </main>
  );
}
