from pathlib import Path
import textwrap


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT = 48
TOP = 800
BOTTOM = 48
FONT_SIZE = 11
LINE_HEIGHT = 15
MAX_WIDTH_CHARS = 92


def escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_lines(source_text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in source_text.splitlines():
        if not raw_line.strip():
            lines.append("")
            continue
        wrapped = textwrap.wrap(
            raw_line,
            width=MAX_WIDTH_CHARS,
            break_long_words=False,
            break_on_hyphens=False,
        )
        lines.extend(wrapped or [""])
    return lines


def paginate(lines: list[str]) -> list[list[str]]:
    page_capacity = ((TOP - BOTTOM) // LINE_HEIGHT) - 1
    return [lines[i:i + page_capacity] for i in range(0, len(lines), page_capacity)]


def make_stream(page_lines: list[str]) -> bytes:
    parts = ["BT", f"/F1 {FONT_SIZE} Tf", f"{LEFT} {TOP} Td"]
    first = True
    for line in page_lines:
        if not first:
            parts.append(f"0 -{LINE_HEIGHT} Td")
        text = escape_pdf_text(line)
        parts.append(f"({text}) Tj")
        first = False
    parts.append("ET")
    return "\n".join(parts).encode("latin-1", errors="replace")


def write_pdf(output_path: Path, pages: list[list[str]]) -> None:
    objects: list[bytes] = []

    def add_object(data: bytes) -> int:
        objects.append(data)
        return len(objects)

    font_id = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []
    content_ids: list[int] = []

    for page_lines in pages:
        stream = make_stream(page_lines)
        content_id = add_object(
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream"
        )
        content_ids.append(content_id)
        page_ids.append(0)

    kids_placeholder = "__KIDS__"
    pages_id = add_object(f"<< /Type /Pages /Kids {kids_placeholder} /Count {len(pages)} >>".encode("latin-1"))

    for idx, content_id in enumerate(content_ids):
        page_id = add_object(
            (
                f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode("latin-1")
        )
        page_ids[idx] = page_id

    kids_ref = "[ " + " ".join(f"{page_id} 0 R" for page_id in page_ids) + " ]"
    objects[pages_id - 1] = (
        f"<< /Type /Pages /Kids {kids_ref} /Count {len(page_ids)} >>".encode("latin-1")
    )

    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("latin-1"))

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for obj_num, obj_data in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{obj_num} 0 obj\n".encode("latin-1"))
        pdf.extend(obj_data)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("latin-1")
    )

    output_path.write_bytes(pdf)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    source_path = base_dir / "viva_notes.txt"
    output_path = base_dir / "Wild_Animals_Alert_Viva_Notes.pdf"
    text = source_path.read_text(encoding="utf-8")
    lines = build_lines(text)
    pages = paginate(lines)
    write_pdf(output_path, pages)
    print(output_path)


if __name__ == "__main__":
    main()
