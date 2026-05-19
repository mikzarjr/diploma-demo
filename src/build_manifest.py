from pathlib import Path

DATASET_ROOT = Path("data/raw/openstt/asr_calls_2_val")
OUTPUT_FILE = Path("data/manifests/asr_calls_2_val_manifest.tsv")


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    wav_files = sorted(DATASET_ROOT.rglob("*.wav"))
    written = 0
    skipped = 0

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for wav_path in wav_files:
            txt_path = wav_path.with_suffix(".txt")

            if not txt_path.exists():
                skipped += 1
                continue

            text = txt_path.read_text(encoding="utf-8").strip()
            if not text:
                skipped += 1
                continue

            out.write(f"{wav_path.resolve()}\t{text}\n")
            written += 1

    print("Готово.")
    print(f"Записано: {written}")
    print(f"Пропущено: {skipped}")
    print(f"Manifest: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
