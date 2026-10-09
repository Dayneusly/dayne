"""Pack a CSV into a compact JavaScript data module.

Usage:
    python convert_csv_to_js.py latihan1.csv latihan1_data.js
"""
import base64
import csv
import gzip
import json
import sys
from pathlib import Path


def convert_csv_to_js(source_path, destination_path):
    source_path = Path(source_path)
    destination_path = Path(destination_path)
    raw_csv = source_path.read_bytes()
    with source_path.open("r", encoding="utf-8-sig", newline="") as source:
        row_count = max(0, sum(1 for _ in csv.reader(source)) - 1)
    if row_count == 0:
        raise ValueError("CSV tidak memiliki header kolom atau baris data.")

    compressed = gzip.compress(raw_csv, mtime=0)
    encoded = base64.b64encode(compressed).decode("ascii")
    javascript = "const studentCsvGzipBase64 = " + json.dumps(encoded) + ";\n"
    destination_path.write_text(javascript, encoding="utf-8")
    return row_count, destination_path.stat().st_size


if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "latihan1.csv"
    js_file = sys.argv[2] if len(sys.argv) > 2 else "latihan1_data.js"
    row_count, byte_count = convert_csv_to_js(csv_file, js_file)
    print(f"Selesai: {row_count} baris dikompresi ke {js_file} ({byte_count} byte).")
