import dataclasses
import json
import re
import datetime

import jinja2

from txtparse import CV, SmartDate

ENVIRONMENT = jinja2.Environment(
    block_start_string="<!",
    block_end_string="!>",
    variable_start_string="<<",
    variable_end_string=">>",
    comment_start_string="<#",
    comment_end_string="#>",
    trim_blocks=False,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


@dataclasses.dataclass
class Settings:
    # ug/grad-specific information
    show_activity_locations: bool = True
    show_time_commitments: bool = True

    # global font options
    main_font: str = ""
    heading_font: str = ""
    title_font: str = ""
    font_size_in_point: int = 11
    heading_relative_size: str = "large"
    title_relative_size: str = "LARGE"
    proportional_numbers: bool = True
    old_style_numbers: bool = False

    # paper size and spacing
    paper: str = "a4paper"
    top_margin_in_inch: float = 0.8
    bottom_margin_in_inch: float = 1.0
    left_margin_in_inch: float = 1.0
    right_margin_in_inch: float = 1.0
    line_spread: float = 1.0
    paragraph_skip_in_pt: int = 0
    entry_skip_in_pt: int = 6
    before_sectitle_skip_in_pt: int = 12
    after_sectitle_skip_in_pt: int = 3

    # heading appearance
    bold_headings: bool = True
    all_cap_headings: bool = True
    default_activities_section_title: str = "Activities"
    awards_section_title: str = "Awards"
    skills_section_title: str = "Skills"

    # awards & skills appearance
    bold_award_names: bool = False
    bold_skillset_names: bool = True

    # item appearance
    bullet_text: str = "•"  # U+2022
    bullet_indent_in_em: float = 0.0
    bullet_item_sep_in_em: float = 1.0
    ending_period_policy: str = ""

    # date formatting
    date_style: str = "american"

    # contact divider
    contact_divider: str = "|"

    # url appearance
    url_font_follows_text: bool = True
    color_links: bool = False
    url_color: str = "black"

    # page numbers
    show_page_numbers: bool = True

    @classmethod
    def from_json(cls, filepath: str) -> "Settings":
        with open(filepath, encoding="utf-8") as f:
            return cls(**json.load(f))


def render(*, template_path: str, cv: CV, settings: Settings):
    with open(template_path, encoding="utf-8") as template_file:
        template_str = template_file.read()
    template = ENVIRONMENT.from_string(template_str)
    return template.render(cv=cv, settings=settings)


def to_latex(s: str):
    # Generic filter:
    # - escape special characters
    # - correct quotes
    # - implement markdown syntax for italic, bold, and url

    # preserve escaped asterisks
    s = s.replace("\\*", '{\\char"002A}')

    # escape `_`, '#', `$`, '%', `&`, '^', '~'
    s = re.sub("([_#$%&])", r"\\\1", s)
    s = s.replace("^", "\\^{}")
    s = s.replace("~", "\\textasciitilde{}")

    # correct quotes
    s = re.sub(r'(^|\s)"', r"\1``", s)
    s = re.sub(r"(^|\s)'", r"\1`", s)

    # bold and italic
    passes = 0
    while s.count("*") and passes < 3:
        s = re.sub(r"\*\*([^*]+?)\*\*", r"\\textbf{\1}", s)
        s = re.sub(r"\*([^*]+?)\*", r"\\emph{\1}", s)
        passes += 1

    # url
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r"\\href{\2}{\1}", s)

    return s


ENVIRONMENT.filters["to_latex"] = to_latex


def null_or_prefixed(s: str, prefix: str) -> str:
    if s:
        return f"{prefix}{s}"
    else:
        return ""


ENVIRONMENT.filters["null_or_prefixed"] = null_or_prefixed


def format_date(
    date1: SmartDate | None,
    style: str,
    date2: SmartDate | None = None,
) -> str:
    # date2, if given, should be a later date than date1
    # but the function will not check if this is the case
    str1 = format_single_date(date1, style)
    str2 = format_single_date(date2, style)

    # If date2 is None or has the same str repr as date1
    if not date2 or (str1 == str2):
        return str1
    # If date1 is None but date1 is not:
    if not date1:
        return str2

    # Else we have two repr-different SmartDates, and
    # no consolidation is required if any of the following is true:
    # - at least one SmartDate isn't a real date
    # - the two objects have different `year` values
    # - the two objects have different resolutions
    # - the style is not one of the consolidatable style
    dash = "\,--\,"
    consolidatable_styles = [
        "american",
        "american long",
        "british",
        "british long",
    ]
    if (
        not date1.is_date
        or not date2.is_date
        or (date1.year != date2.year)
        or (date1.resolution != date2.resolution)
        or style not in consolidatable_styles
    ):
        return f"{str1}{dash}{str2}"

    # Consolidation required if both SmartDates are real dates
    # with identical `year` values and resolutions, and
    # the caller calls for a consolidatable style:
    # - different months without `day` values: May-Jun 2023
    # - different days in the same month: May 22-24, 2023,
    # - different days in different months: May 22 - June 22, 2023
    fulldate1: datetime.date = date1.as_date
    fulldate2: datetime.date = date2.as_date
    year = date1.year
    m1 = fulldate1.strftime("%b")
    m2 = fulldate2.strftime("%b")
    mm1 = fulldate1.strftime("%B")
    mm2 = fulldate2.strftime("%B")
    # NOTE the hash sign is windows specific
    d1 = fulldate1.strftime("%#d")
    d2 = fulldate2.strftime("%#d")

    day_dash = "--"  # between days

    # Different months without `day` values
    if date1.day is None and style in ["american", "british"]:
        return f"{m1}{dash}{m2} {year}"
    elif date1.day is None:
        return f"{mm1}{dash}{mm2} {year}"

    # Different days in the same month
    elif date1.month == date2.month:
        if style == "american":
            return f"{m1} {d1}{day_dash}{d2}, {year}"
        if style == "american long":
            return f"{mm1} {d1}{day_dash}{d2}, {year}"
        if style == "british":
            return f"{d1}{day_dash}{d2} {m1} {year}"
        if style == "british long":
            return f"{d1}{day_dash}{d2} {mm1} {year}"

    # Different days in different months
    elif style == "american":
        return f"{m1} {d1}{dash}{m2}{d2}, {year}"
    elif style == "american long":
        return f"{mm1} {d1}{dash}{mm2}{d2}, {year}"
    elif style == "british":
        return f"{d1} {m1}{dash}{d2}{m2} {year}"
    elif style == "british long":
        return f"{d1} {mm1}{dash}{d2}{mm2} {year}"

    else:
        raise ValueError((date1, date2, style))


def format_single_date(d: SmartDate | None, style: str) -> str:
    if d is None:
        return ""
    if not d.is_date:
        return d.fallback
    if d.month is None:
        return str(d.year)

    # (style, d.day is not None) -> formatter
    style_map = {
        ("american", True): "%b %#d, %Y",
        ("american", False): "%b %Y",
        ("american long", True): "%B %#d, %Y",
        ("american long", False): "%B %Y",
        ("american slash", True): "%m/%d/%Y",
        ("american slash", False): "%m/%Y",
        ("british", True): "%#d %b %Y",
        ("british", False): "%b %Y",
        ("british long", True): "%#d %B %Y",
        ("british long", False): "%B %Y",
        ("british slash", True): "%d/%m/%Y",
        ("british slash", False): "%m/%Y",
        ("iso", True): "%Y-%m-%d",
        ("iso", False): "%Y-%m",
        ("yyyy/mm/dd", True): "%Y/%m/%d",
        ("yyyy/mm/dd", False): "%Y/%m",
    }
    date = datetime.date(year=d.year, month=d.month, day=d.day or 1)
    format_str = style_map[style, d.day is not None]
    return date.strftime(format_str)


ENVIRONMENT.filters["format_date"] = format_date


def format_commitment(hours_per_week: str, weeks_per_year: str, per="/"):
    if hours_per_week == "1":
        hpw = f"1 hour{per}week"
    elif hours_per_week:
        hpw = f"{hours_per_week} hours{per}week"
    else:
        hpw = ""

    if weeks_per_year == "1":
        wpy = f"1 week{per}year"
    elif weeks_per_year:
        wpy = f"{weeks_per_year} weeks{per}year"
    else:
        wpy = ""

    if hpw and wpy:
        return f"{hpw}, {wpy}"
    else:
        return hpw or wpy


ENVIRONMENT.filters["format_commitment"] = format_commitment

# regex pattern for sentences with ending periods:
# ending with '.' and not with '..' (probably an ellipsis)
_HAS_PERIOD = re.compile(r"(?<!\.)\.$")

# regex pattern for sentences missing ending punctuations
_NEEDS_PERIOD = re.compile(r"[^.!?](?:[)'\"])?$")


def handle_ending_period(line: str, policy: str):
    if policy.lower() == "add" and _NEEDS_PERIOD.search(line):
        return f"{line}."
    if policy.lower() == "remove" and _HAS_PERIOD.search(line):
        return line[:-1]
    else:
        return line


ENVIRONMENT.filters["handle_ending_period"] = handle_ending_period
