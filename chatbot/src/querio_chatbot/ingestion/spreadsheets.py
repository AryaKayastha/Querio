"""Convert the data team's spreadsheets under data/ into Markdown that ingestion can read.

Ingestion only reads .md/.txt/.pdf. Every spreadsheet needs an explicit spec below naming the
sheets to convert and how to render a row -- never a blind dump -- because these workbooks mix
student-facing facts with things that must not reach students: personal mobile numbers, student
email IDs, internal data-quality notes, formula helper columns. A spreadsheet without a spec is
reported and skipped.

Each spreadsheet becomes `<name>.xlsx.md` next to it (keeping ".xlsx" in the name avoids clashing
with an existing .md on case-insensitive Windows). Sections are kept under the chunk size and each
repeats its intro sentence, so every chunk says what it lists. Re-run after a spreadsheet changes,
then re-run ingestion.

Usage: python -m querio_chatbot.ingestion.spreadsheets
"""

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import openpyxl

from querio_chatbot.config import DATA_ROOT

# Just under the 800-char chunk size, so a section never gets split away from its intro sentence.
MAX_SECTION_CHARS = 780


class Row:
    """One spreadsheet row: index by header text (first matching column) or by column index."""

    def __init__(self, headers: list[str], values: list[str]):
        self.values = values
        self._by_header: dict[str, str] = {}
        for header, value in zip(headers, values):
            if header and header not in self._by_header:
                self._by_header[header] = value

    def __getitem__(self, key: str | int) -> str:
        if isinstance(key, int):
            return self.values[key] if key < len(self.values) else ""
        return self._by_header.get(key, "")


Book = dict[str, list[Row]]


@dataclass(frozen=True)
class SheetSpec:
    sheet: str
    # "list": rows become bullets grouped into sections titled `title` (part 1, part 2...).
    # "records": each row becomes its own section, titled by `record_title(row)`. A record's first
    # line should name the row; a record too long for one chunk is split into parts that each
    # repeat that first line.
    mode: str
    render: Callable[[Row, Book], str | None]  # row -> text, or None to skip the row
    title: str = ""
    intro: str = ""
    record_title: Callable[[Row], str] | None = None
    header_row: int = 1
    # "list" only: one list per distinct value of this column; `title`/`intro` may use {group}.
    group_by: str = ""


@dataclass(frozen=True)
class FileSpec:
    path: str  # relative to data/
    source_name: str
    sheets: tuple[SheetSpec, ...]


def _clean(value) -> str:
    if value is None:
        return ""
    if isinstance(value, dt.datetime):
        return value.strftime("%d %b %Y").lstrip("0")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return " ".join(str(value).split())


def read_book(path: Path, header_rows: dict[str, int]) -> Book:
    # data_only=True returns each formula cell's saved value instead of the formula text.
    workbook = openpyxl.load_workbook(path, data_only=True)
    book: Book = {}
    for sheet in workbook.worksheets:
        header_row = header_rows.get(sheet.title, 1)
        rows = list(sheet.iter_rows(values_only=True))
        if len(rows) < header_row:
            book[sheet.title] = []
            continue
        headers = [_clean(v) for v in rows[header_row - 1]]
        book[sheet.title] = [
            Row(headers, [_clean(v) for v in values])
            for values in rows[header_row:]
            if any(v not in (None, "") for v in values)
        ]
    return book


def _section_length(intro: str, bullets: list[str]) -> int:
    return len("\n".join([intro, "", *bullets]))


def _greedy_groups(bullets: list[str], intro: str, limit: int) -> list[list[str]]:
    groups: list[list[str]] = [[]]
    for bullet in bullets:
        if groups[-1] and _section_length(intro, groups[-1] + [bullet]) > limit:
            groups.append([])
        groups[-1].append(bullet)
    return groups


def _balanced_groups(bullets: list[str], intro: str) -> list[list[str]]:
    """Fewest sections that fit, then the smallest size limit that keeps that count -- so parts
    come out similar in size instead of leaving a one-item tail."""
    if not bullets:
        return []
    fewest = len(_greedy_groups(bullets, intro, MAX_SECTION_CHARS))
    low = max(_section_length(intro, [b]) for b in bullets)
    high = max(low, MAX_SECTION_CHARS)
    while low < high:
        middle = (low + high) // 2
        if len(_greedy_groups(bullets, intro, middle)) <= fewest:
            high = middle
        else:
            low = middle + 1
    return _greedy_groups(bullets, intro, low)


def _parts(title: str, intro: str, groups: list[list[str]], blank_after_intro: bool = True) -> list[tuple[str, str]]:
    spacer = [""] if blank_after_intro else []
    return [
        (title if len(groups) == 1 else f"{title} (part {i} of {len(groups)})", "\n".join([intro, *spacer, *lines]))
        for i, lines in enumerate(groups, start=1)
    ]


def render_sections(spec: SheetSpec, book: Book) -> list[tuple[str, str]]:
    rendered = [(row, spec.render(row, book)) for row in book.get(spec.sheet, [])]
    rendered = [(row, text) for row, text in rendered if text]

    if spec.mode == "records":
        sections = []
        for row, text in rendered:
            head, *lines = text.split("\n")
            groups = [lines] if len(text) <= MAX_SECTION_CHARS else _balanced_groups(lines, head)
            sections += _parts(spec.record_title(row), head, groups, blank_after_intro=False)
        return sections

    grouped: dict[str, list[str]] = {}
    for row, text in rendered:
        grouped.setdefault(row[spec.group_by] if spec.group_by else "", []).append(f"- {text}")
    sections = []
    for group, bullets in grouped.items():
        intro = spec.intro.format(group=group)
        sections += _parts(spec.title.format(group=group), intro, _balanced_groups(bullets, intro))
    return sections


def to_markdown(spec: FileSpec, book: Book) -> str:
    lines = [
        "---",
        f"source_name: {spec.source_name}",
        "source_type: spreadsheet",
        f"owner_contact: Converted from {Path(spec.path).name} -- verify with the data team",
        "---",
    ]
    for sheet in spec.sheets:
        for title, body in render_sections(sheet, book):
            lines += ["", f"## {title}", "", body]
    return "\n".join(lines) + "\n"


def convert(spec: FileSpec, data_root: Path = DATA_ROOT) -> Path:
    source = data_root / spec.path
    book = read_book(source, {s.sheet: s.header_row for s in spec.sheets})
    missing = [s.sheet for s in spec.sheets if s.sheet not in book]
    if missing:
        raise ValueError(f"{source.name} has no sheet(s) {missing} -- update its spec")
    target = source.with_name(source.name + ".md")
    target.write_text(to_markdown(spec, book), encoding="utf-8")
    return target


# --- specs -----------------------------------------------------------------------------------


def _joined(*parts: str) -> str:
    return "; ".join(p for p in parts if p)


def _club_record(row: Row, book: Book) -> str | None:
    if not row["Club"]:
        return None
    events = [
        f"{e['Event']} ({e['Date']})" if e["Date"] and e["Date"] != "Not listed" else e["Event"]
        for e in book.get("Events", [])
        if e["Club"] == row["Club"]
    ]
    lines = [f"{row['Club']} is a student club at CSPIT (CHARUSAT)."]
    lines.append(f"- Focus: {row['Focus']}")
    if row["Website"]:
        lines.append(f"- Website: {row['Website']}")
    lines.append(f"- Faculty coordinators: {row['Faculty Coordinators'] or 'not listed'}")
    if row["Student Coordinators"]:
        lines.append(f"- Student coordinators: {row['Student Coordinators']}")
    if events:
        lines.append(f"- Past events: {'; '.join(events)}")
    return "\n".join(lines)


def _club_overview(row: Row, book: Book) -> str | None:
    if not row["Club"]:
        return None
    website = f" ({row['Website']})" if row["Website"] else ""
    return f"{row['Club']} -- {row['Focus']}{website}"


def _nss_officer(row: Row, book: Book) -> str | None:
    institute, officer = row["Name of College/Institutions/ Department/School"], row["Name of PO of each unit"]
    if not institute or not officer:
        return None
    email = row["Email ID of as PO"]
    # Official staff addresses only; mobile numbers are left out on purpose.
    email = email if email.endswith("@charusat.ac.in") else ""
    village = row["Name of Villages/slums adopted by adopted by NSS unit"]
    return f"{institute} -- Program Officer: {officer}" + (f" ({email})" if email else "") + (
        f"; adopted village: {village}" if village else ""
    )


def _nss_coordinators(row: Row, book: Book) -> str | None:
    # Two header rows, with repeated "Name"/"Email ID"/"Mobile Number" columns, so use indexes.
    # Column 0 unit, 1 PO name, 5 student coordinator 1 name, 9 student coordinator 2 name.
    # Student emails and mobile numbers (columns 3-4, 7-8, 11-12) are personal data: not used.
    unit, officer = row[0], row[1]
    students = ", ".join(n for n in (row[5], row[9]) if n)
    # The sheet ends with tally rows ("Total SC Male", "Total PO Vacant", ...), not units.
    if not unit or unit.startswith("Total ") or not (officer or students):
        return None
    return _joined(f"{unit} -- Program Officer: {officer or 'not listed'}",
                   f"student coordinators: {students}" if students else "")


def _nss_activity(row: Row, book: Book) -> str | None:
    activity = row["Name of Activity"]
    if not activity:
        return None
    start, end = row["Date of Start"], row["Date of End"]
    when = start if not end or end == start else f"{start} to {end}"
    return _joined(
        activity,
        f"{row['Name of Scheme']} scheme" if row["Name of Scheme"] else "",
        f"organised by {row['Organising Institute']}" if row["Organising Institute"] else "",
        when,
        f"at {row['Venue']}" if row["Venue"] else "",
        f"{row['No.of Volunteers Participated']} volunteers" if row["No.of Volunteers Participated"] else "",
        f"Program Officer: {row['Program Officer']}" if row["Program Officer"] else "",
    )


CERT = "Certification Name"


def _cert_record(row: Row, book: Book) -> str | None:
    if not row[CERT]:
        return None
    validity = row["Validity Period"]
    if validity and not validity.lower().startswith(("does not", "no ", "never", "lifetime")):
        validity = f"valid for {validity}"
    fields = [  # most useful first, in case the record is split across chunks
        ("Official link", row["Official Link"]),
        ("Exam cost", row["Exam Cost (USD)"]),
        ("Prerequisites", _joined(row["Prerequisites / Eligibility"],
                                   f"recommended: {row['Recommended Experience']}" if row["Recommended Experience"] else "")),
        ("Exam format", _joined(row["Exam Format"], row["Duration / Time Limit"], validity)),
        ("Best for", row["Best For (Career Path)"]),
        ("Student discounts / free resources", row["Student Discounts / Free Resources"]),
        ("Topics", row["Topics Covered"]),
        ("Preparation resources", row["Preparation Resources"]),
        ("Study materials", row["Study Materials"]),
        ("Mock exams", row["Mock Exams / Practice Tests"]),
        ("Tips", row["Notes / Tips for Students"]),
    ]
    level = row["Level"]
    article = "an" if level[:1].lower() in "aeiou" else "a"
    head = f"{row[CERT]} is {article} {level} {row['Domain']} certification from {row['Provider / Issuing Body']}."
    return "\n".join([head, *(f"- {label}: {value}" for label, value in fields if value)])


def _cert_overview(row: Row, book: Book) -> str | None:
    if not row[CERT]:
        return None
    details = _joined(row["Level"], row["Exam Cost (USD)"])
    return f"{row[CERT]} ({details}) -- {row['Official Link']}" if row["Official Link"] else f"{row[CERT]} ({details})"


def _spoural_event(row: Row, book: Book) -> str | None:
    event = row["Event Name"]
    if not event:
        return None
    return f"{event} -- faculty coordinator: {row['Faculty Coordinator'] or 'not listed'}"


SPECS = [
    FileSpec(
        path="D1_clubs/CSPIT_Clubs.xlsx",
        source_name="CSPIT Clubs",
        sheets=(
            SheetSpec("Clubs", "list", _club_overview, title="All CSPIT clubs",
                      intro="Student clubs at CSPIT (CHARUSAT) and what each focuses on (website in brackets):"),
            SheetSpec("Clubs", "records", _club_record, record_title=lambda r: f"{r['Club']} (CSPIT club)"),
            # "Data Issues" is the data team's internal QA notes, not student-facing.
        ),
    ),
    FileSpec(
        path="D1_clubs/CHARUSAT NSS Cell.xlsx",
        source_name="CHARUSAT NSS Cell",
        sheets=(
            SheetSpec("POs Details", "list", _nss_officer, title="NSS units and Program Officers",
                      intro="CHARUSAT NSS (National Service Scheme) units, one per institute/department, with each "
                            "unit's Program Officer and adopted village:"),
            SheetSpec("POs_and_SC_Details", "list", _nss_coordinators, title="NSS student coordinators",
                      intro="Student coordinators of each CHARUSAT NSS unit, with the unit's Program Officer:",
                      header_row=2),
            SheetSpec("Sheet6", "list", _nss_activity, title="NSS activities",
                      intro="Activities conducted by CHARUSAT NSS units (activity, scheme, organiser, date, venue, "
                            "volunteers):"),
        ),
    ),
    FileSpec(
        path="D2_certifications/CS_Certifications_Guide.xlsx",
        source_name="CS Certifications Guide",
        sheets=(
            # All 52 certifications: cs_certifications_guide.md only covers 25 of them. "FAQs" is
            # skipped because the .md already has the same FAQs.
            SheetSpec("All Certifications", "list", _cert_overview, group_by="Domain",
                      title="{group} certifications",
                      intro="{group} certifications for computer science students (level, exam cost, official link):"),
            SheetSpec("All Certifications", "records", _cert_record, record_title=lambda r: r[CERT]),
            SheetSpec("Cost Comparison", "list",
                      lambda r, b: r["Certification"] and _joined(
                          f"{r['Tier']}: {r['Certification']} ({r['Provider']}) -- {r['Cost (USD)']}", r["Domain"]),
                      title="Certification cost comparison",
                      intro="Computer science certifications compared by exam cost in USD, from free upwards:"),
            SheetSpec("Student Discounts", "list",
                      lambda r, b: r["Program / Provider"] and (
                          f"{r['Program / Provider']}: {r['What Students Get']}. How to get it: "
                          f"{r['How to Access']}. Applies to: {r['Applicable Certifications']}."),
                      title="Student discounts for certifications",
                      intro="Student discounts and free resources for computer science certifications:"),
            SheetSpec("Career Roadmaps", "list",
                      lambda r, b: r["Career Goal"] and (
                          f"{r['Career Goal']}: 1) {r['Step 1 (Foundational)']} -> 2) {r['Step 2 (Associate)']} "
                          f"-> 3) {r['Step 3 (Professional)']} -> 4) {r['Step 4 (Expert/Specialty)']}"),
                      title="Certification roadmaps by career goal",
                      intro="Recommended certification path for each career goal, from foundational to expert:"),
        ),
    ),
    FileSpec(
        path="D3_eca_sports/Spoural_CSPIT.xlsx",
        source_name="Spoural events (CSPIT Computer Engineering)",
        sheets=(
            SheetSpec("Boys Sports", "list", _spoural_event, title="Spoural boys' sports events",
                      intro="Spoural boys' sports events for CSPIT Computer Engineering and their faculty coordinators:"),
            SheetSpec("Girls Sports", "list", _spoural_event, title="Spoural girls' sports events",
                      intro="Spoural girls' sports events for CSPIT Computer Engineering and their faculty "
                            "coordinators:"),
            SheetSpec("Cultural (Updated)", "list", _spoural_event, title="Spoural cultural events",
                      intro="Spoural cultural events for CSPIT Computer Engineering and their faculty coordinators:"),
        ),
    ),
]


def main() -> None:
    specced = {spec.path for spec in SPECS}
    for spec in SPECS:
        if (DATA_ROOT / spec.path).exists():
            print(f"[xlsx] wrote {convert(spec).relative_to(DATA_ROOT)}")
        else:
            print(f"[xlsx] {spec.path} not found -- skipped")
    for path in sorted(DATA_ROOT.glob("*/*.xlsx")):
        relative = path.relative_to(DATA_ROOT).as_posix()
        if relative not in specced:
            print(f"[xlsx] {relative} has no spec in ingestion/spreadsheets.py -- not converted")


if __name__ == "__main__":
    main()
