"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, clearToken, type Me } from "@/lib/api";

type Detection = {
  id: string;
  method: string;
  vid: string | null;
  pid: string | null;
  label: string;
  created_at: string;
};

type Usage = {
  id: string;
  knowledge_id: string;
  knowledge_title: string;
  action: string;
  created_at: string;
};

type Feedback = {
  id: string;
  knowledge_id: string;
  knowledge_title: string;
  kind: string;
  created_at: string;
};

function fmt(dt: string) {
  return new Date(dt).toLocaleString("id-ID");
}

export default function UserHistoryPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [usages, setUsages] = useState<Usage[]>([]);
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([]);

  useEffect(() => {
    api<Me>("/auth/me")
      .then((m) => {
        setMe(m);
        api<Detection[]>("/history/me/detections").then(setDetections).catch(() => {});
        api<Usage[]>("/history/me/usages").then(setUsages).catch(() => {});
        api<Feedback[]>("/history/me/feedbacks").then(setFeedbacks).catch(() => {});
      })
      .catch(() => router.push("/login"));
  }, [router]);

  if (!me) return <main style={{ padding: "2rem" }}>Memuat...</main>;

  return (
    <main style={{ maxWidth: 900, margin: "2rem auto", padding: "0 1rem" }}>
      <Link href="/">← Beranda</Link>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>Riwayat saya</h1>
        <button
          onClick={() => {
            clearToken();
            router.push("/login");
          }}
        >
          Keluar
        </button>
      </div>

      <h2>Deteksi perangkat</h2>
      {detections.length === 0 && <p>Belum ada.</p>}
      <ul>
        {detections.map((d) => (
          <li key={d.id} style={{ marginBottom: "0.4rem" }}>
            {d.label}
            {d.vid && <span style={{ color: "#666" }}> ({d.vid}:{d.pid})</span>}{" "}
            <span style={{ color: "#999", fontSize: "0.8rem" }}>{fmt(d.created_at)}</span>
          </li>
        ))}
      </ul>

      <h2>Knowledge yang dibuka</h2>
      {usages.length === 0 && <p>Belum ada.</p>}
      <ul>
        {usages.map((u) => (
          <li key={u.id} style={{ marginBottom: "0.4rem" }}>
            <Link href={`/knowledge/${u.knowledge_id}`}>{u.knowledge_title}</Link>{" "}
            <span style={{ color: "#999", fontSize: "0.8rem" }}>{fmt(u.created_at)}</span>
          </li>
        ))}
      </ul>

      <h2>Testimoni saya</h2>
      {feedbacks.length === 0 && <p>Belum ada.</p>}
      <ul>
        {feedbacks.map((f) => (
          <li key={f.id} style={{ marginBottom: "0.4rem" }}>
            {f.kind === "success" ? "✅ Berhasil" : "👍 Suka"} —{" "}
            <Link href={`/knowledge/${f.knowledge_id}`}>{f.knowledge_title}</Link>{" "}
            <span style={{ color: "#999", fontSize: "0.8rem" }}>{fmt(f.created_at)}</span>
          </li>
        ))}
      </ul>
    </main>
  );
}
