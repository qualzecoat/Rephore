"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, type Me } from "@/lib/api";
import Navbar from "@/components/Navbar";

type Detection = {
  id: string;
  username: string;
  method: string;
  vid: string | null;
  pid: string | null;
  label: string;
  created_at: string;
};

type Usage = {
  id: string;
  username: string;
  knowledge_id: string;
  knowledge_title: string;
  action: string;
  created_at: string;
};

export default function AdminHistoryPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [usages, setUsages] = useState<Usage[]>([]);

  useEffect(() => {
    api<Me>("/auth/me")
      .then((m) => {
        if (m.role !== "admin") router.push("/login");
        else {
          setMe(m);
          api<Detection[]>("/history/detections").then(setDetections).catch(() => {});
          api<Usage[]>("/history/usages").then(setUsages).catch(() => {});
        }
      })
      .catch(() => router.push("/login"));
  }, [router]);

  if (!me) return <main style={{ padding: "2rem" }}>Memuat...</main>;

  return (
    <main style={{ maxWidth: 900, margin: "2rem auto", padding: "0 1rem" }}>
      <Navbar />
      <h1>Histori</h1>

      <h2>Deteksi perangkat oleh user</h2>
      {detections.length === 0 && <p>Belum ada.</p>}
      <ul>
        {detections.map((d) => (
          <li key={d.id} style={{ marginBottom: "0.4rem" }}>
            <b>{d.username}</b> — {d.label}
            {d.vid && <span style={{ color: "#666" }}> ({d.vid}:{d.pid})</span>}{" "}
            <span style={{ color: "#999", fontSize: "0.8rem" }}>
              {new Date(d.created_at).toLocaleString("id-ID")}
            </span>
          </li>
        ))}
      </ul>

      <h2>Pemakaian knowledge oleh user</h2>
      {usages.length === 0 && <p>Belum ada.</p>}
      <ul>
        {usages.map((u) => (
          <li key={u.id} style={{ marginBottom: "0.4rem" }}>
            <b>{u.username}</b> membuka{" "}
            <Link href={`/knowledge/${u.knowledge_id}`}>{u.knowledge_title}</Link>{" "}
            <span style={{ color: "#999", fontSize: "0.8rem" }}>
              {new Date(u.created_at).toLocaleString("id-ID")}
            </span>
          </li>
        ))}
      </ul>
    </main>
  );
}
