"""Rephore AI worker — generate knowledge terjadwal (Fase 0 scaffold).

Fase berikutnya: scheduler harian (2-3 knowledge), antrean Redis,
dan pemanggil AI provider generik (OpenAI-compatible).
"""

import time


def main() -> None:
    print("rephore worker started (fase 0 placeholder)")
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
