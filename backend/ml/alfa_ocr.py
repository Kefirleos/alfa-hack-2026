import json
import time
import shutil
import argparse
import pymupdf as fitz
import pytesseract
from PIL import Image

from ml import config

OUT_FILE = config.PROCESSED_DIR / "alfa_pages.jsonl"
DPI = 300
LANG = "rus+eng"

def ocr_page(page) -> tuple[str, float]:
    text = page.get_text().strip()
    if len(text) > 200:
        return text, 100.0
    pix = page.get_pixmap(dpi=DPI)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    text = pytesseract.image_to_string(img, lang=LANG)
    data = pytesseract.image_to_data(img, lang=LANG, output_type=pytesseract.Output.DICT)

    confs = [float(c) for c in data["conf"] if float(c) >=0]
    confidence = sum(confs) / len(confs) if confs else 0.0
    return text, confidence


def main():
    parser = argparse.ArgumentParser(description="OCR аналитики банка")
    parser.add_argument("--force", action="store_true", help = "распознать все заново")
    args = parser.parse_args()

    path = shutil.which("tesseract")
    if path is None:
        print("Need install tesseract-ocr")
        return

    done = set()
    if OUT_FILE.exists() and not args.force:
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():   
                    row = json.loads(line)
                    done.add((row["file"], row["page"]))

    pdfs = sorted(config.RAW_DIR.glob("*.pdf"))
    if not pdfs:
        print("pdfs haven't")
        return

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    mode = "w" if args.force else "a"

    new_pages = 0
    low_conf = 0
    with open(OUT_FILE, mode, encoding="utf-8") as f:
        for pdf in pdfs:
            doc = fitz.open(pdf)
            for i, page in enumerate(doc):
                page_no = i + 1
                if (pdf.name, page_no) in done:
                    continue
                started = time.time()
                text, conf = ocr_page(page)
                record = {
                    "file": pdf.name, 
                    "page": page_no,
                    "text": text,
                    "confidence": round(conf, 1),
                    "chars": len(text)
                }
                f.write(json.dumps(record, ensure_ascii = False) + "\n")
                f.flush()

                new_pages += 1
                if conf < 60:
                    low_conf += 1

        print(f"new_pages: {new_pages}, len(done): {len(done)}, low_conf: {low_conf}, OUT_FILE: {OUT_FILE}")

    
                

if __name__ == "__main__":
    main()