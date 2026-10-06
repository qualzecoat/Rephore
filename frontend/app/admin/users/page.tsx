"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Me } from "@/lib/api";

type User = {
  id: string;
  username: string;
  role: string;
  created_at: string;
};

export default function AdminUsersPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");
  const [error, setError] = useState("");

  useEffect(() => {
    api<Me>("/auth/me")
      .then((m) => {
        if (m.role !== "admin") router.push("/login");
        else {
          setMe(m);
          return api<User[]>("/users").then(setUsers);
        }
      })
      .catch(() => router.push("/login"));
  }, [router]);

  async function createUser(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const u = await api<User>("/users", {
        method: "POST",
        body: JSON.stringify({ username, password, role }),
      });
      setUsers((prev) => [...prev, u]);
      setUsername("");
      setPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal membuat user");
    }
  }

  async function deleteUser(id: string) {
    if (!confirm("Hapus user ini?")) return;
    try {
      await api("/users/" + id, { method: "DELETE" });
      setUsers((prev) => prev.filter((u) => u.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal menghapus user");
    }
  }

  if (!me) return <main style={{ padding: "2rem" }}>Memuat...</main>;

  return (
    <main style={{ maxWidth: 720, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>Kelola User</h1>
      <p style={{ color: "#666" }}>
        Login sebagai <b>{me.username}</b> (admin)
      </p>

      <h2>Buat user baru</h2>
      <form
        onSubmit={createUser}
        style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}
      >
        <input
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          style={{ padding: "0.5rem" }}
        />
        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          style={{ padding: "0.5rem" }}
        />
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          style={{ padding: "0.5rem" }}
        >
          <option value="user">user</option>
          <option value="admin">admin</option>
        </select>
        <button type="submit" style={{ padding: "0.5rem 1rem" }}>
          Buat
        </button>
      </form>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <h2>Daftar user</h2>
      <ul>
        {users.map((u) => (
          <li key={u.id} style={{ marginBottom: "0.5rem" }}>
            {u.username} ({u.role})
            {u.id !== me.id && (
              <button
                onClick={() => deleteUser(u.id)}
                style={{ marginLeft: "0.75rem" }}
              >
                Hapus
              </button>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
