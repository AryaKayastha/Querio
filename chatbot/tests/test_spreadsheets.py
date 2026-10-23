import re

import openpyxl
import pytest

from querio_chatbot.config import DATA_ROOT
from querio_chatbot.ingestion import spreadsheets
from querio_chatbot.ingestion.spreadsheets import (
    MAX_SECTION_CHARS,
    SPECS,
    FileSpec,
    SheetSpec,
    convert,
    read_book,
    render_sections,
    to_markdown,
)


def _workbook(tmp_path, rows, name="clubs.xlsx", sheet="Clubs"):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = sheet
    for row in rows:
        worksheet.append(row)
    path = tmp_path / name
    workbook.save(path)
    return path


def test_list_sections_stay_under_the_chunk_size_and_are_balanced(tmp_path):
    rows = [["Club", "Focus"]] + [[f"Club number {i}", "x" * 60] for i in range(30)]
    book = read_book(_workbook(tmp_path, rows), {})
    spec = SheetSpec("Clubs", "list", lambda r, b: f"{r['Club']} -- {r['Focus']}", title="All clubs",
                     intro="Student clubs:")

    sections = render_sections(spec, book)

    assert len(sections) > 1
    assert all(len(body) <= MAX_SECTION_CHARS for _, body in sections)
    assert all(body.startswith("Student clubs:") for _, body in sections)
    sizes = [body.count("\n- ") for _, body in sections]
    assert max(sizes) - min(sizes) <= 1
    assert sum(sizes) == 30


def test_long_record_is_split_into_parts_that_repeat_its_first_line(tmp_path):
    rows = [["Name", "Notes"], ["AWS Cloud Practitioner", "note " * 300]]
    book = read_book(_workbook(tmp_path, rows, sheet="Certs"), {})
    spec = SheetSpec("Certs", "records", record_title=lambda r: r["Name"],
                     render=lambda r, b: "\n".join([f"{r['Name']} is a certification."] +
                                                   [f"- detail {i}: {'y' * 80}" for i in range(12)]))

    sections = render_sections(spec, book)

    assert len(sections) == 2
    assert [title for title, _ in sections] == ["AWS Cloud Practitioner (part 1 of 2)", "AWS Cloud Practitioner (part 2 of 2)"]
    assert all(body.startswith("AWS Cloud Practitioner is a certification.") for _, body in sections)
    assert all(len(body) <= MAX_SECTION_CHARS for _, body in sections)


def test_only_columns_the_spec_renders_reach_the_markdown(tmp_path):
    rows = [["Name", "Mobile Number"], ["Prof. A", 9876543210]]
    book = read_book(_workbook(tmp_path, rows, sheet="Staff"), {})
    spec = FileSpec("x.xlsx", "Staff", (SheetSpec("Staff", "list", lambda r, b: r["Name"], title="Staff", intro="Staff:"),))

    markdown = to_markdown(spec, book)

    assert "Prof. A" in markdown
    assert "9876543210" not in markdown


def test_convert_writes_xlsx_md_and_rejects_a_missing_sheet(tmp_path):
    _workbook(tmp_path, [["Club", "Focus"], ["Robotics Club", "Robotics"]])
    good = FileSpec("clubs.xlsx", "Clubs", (SheetSpec("Clubs", "list", lambda r, b: r["Club"], title="Clubs", intro="Clubs:"),))
    assert convert(good, tmp_path).name == "clubs.xlsx.md"

    bad = FileSpec("clubs.xlsx", "Clubs", (SheetSpec("Renamed", "list", lambda r, b: r["Club"]),))
    with pytest.raises(ValueError, match="Renamed"):
        convert(bad, tmp_path)


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.path)
def test_real_spreadsheets_convert_without_personal_contact_details(spec):
    source = DATA_ROOT / spec.path
    if not source.exists():
        pytest.skip(f"{spec.path} not present")
    book = read_book(source, {s.sheet: s.header_row for s in spec.sheets})

    markdown = to_markdown(spec, book)

    assert not re.search(r"(?<!\d)[6-9]\d{9}(?!\d)", markdown), "a mobile number reached the output"
    assert "@charusat.edu.in" not in markdown.lower(), "a student email reached the output"
    assert "Total SC" not in markdown


def test_main_reports_spreadsheets_without_a_spec(tmp_path, monkeypatch, capsys):
    (tmp_path / "D9_new").mkdir()
    _workbook(tmp_path / "D9_new", [["A"], ["b"]], name="mystery.xlsx")
    monkeypatch.setattr(spreadsheets, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(spreadsheets, "SPECS", [])

    spreadsheets.main()

    assert "D9_new/mystery.xlsx has no spec" in capsys.readouterr().out
    assert not (tmp_path / "D9_new" / "mystery.xlsx.md").exists()
