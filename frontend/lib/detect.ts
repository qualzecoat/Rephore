/** Deteksi perangkat via WebUSB (VID/PID).
 *
 * Untuk HP mati: yang terdeteksi hanya level chipset (misal EDL 9008 /
 * MediaTek preloader) — sesuai keputusan, ini cukup untuk Fase 3.
 * Deteksi ADB penuh (HP hidup) direncanakan menyusul.
 */

export type DetectedDevice = {
  vid: string;
  pid: string;
  label: string;
  kind: "edl" | "preloader" | "download-mode" | "unknown";
  productName?: string;
};

// Tabel VID:PID yang dikenal -> keterangan chipset/mode.
// Tabel ini bisa ditambah kapan saja tanpa mengubah kode lain.
const KNOWN: Record<string, { label: string; kind: DetectedDevice["kind"] }> = {
  "05c6:9008": { label: "Qualcomm EDL 9008", kind: "edl" },
  "05c6:900e": { label: "Qualcomm Diagnostic 900E", kind: "edl" },
  "0e8d:2000": { label: "MediaTek Preloader", kind: "preloader" },
  "0e8d:0003": { label: "MediaTek Preloader", kind: "preloader" },
  "04e8:6860": { label: "Samsung Download Mode (Odin)", kind: "download-mode" },
  "18d1:4ee0": { label: "Fastboot Mode", kind: "download-mode" },
};

export function webUsbSupported(): boolean {
  return typeof navigator !== "undefined" && "usb" in navigator;
}

/** Minta user memilih perangkat USB, kembalikan info VID/PID + label. */
export async function detectUsbDevice(): Promise<DetectedDevice> {
  if (!webUsbSupported()) {
    throw new Error("Browser tidak mendukung WebUSB. Pakai Chrome/Edge di desktop.");
  }
  // Harus dipanggil dari user gesture (klik tombol)
  const device = await (navigator as unknown as { usb: { requestDevice(o: object): Promise<{ vendorId: number; productId: number; productName?: string }> } }).usb.requestDevice({
    filters: [],
  });
  const vid = device.vendorId.toString(16).padStart(4, "0");
  const pid = device.productId.toString(16).padStart(4, "0");
  const known = KNOWN[`${vid}:${pid}`];
  return {
    vid,
    pid,
    label: known?.label ?? `Perangkat USB tidak dikenal (${vid}:${pid})`,
    kind: known?.kind ?? "unknown",
    productName: device.productName,
  };
}
