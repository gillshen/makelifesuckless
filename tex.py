import dataclasses
import json
import re

import jinja2

from txtparse import CV

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

    # bullet appearance
    bullet_text: str = "•"  # U+2022
    bullet_indent_in_em: float = 0.0
    bullet_item_sep_in_em: float = 1.0

    # awards & skills appearance
    bold_award_names: bool = False
    bold_skillset_names: bool = True

    # date formatting
    date_style: str = "american"

    # contact divider
    contact_divider: str = "|"

    # url appearance
    url_font_follows_text: bool = True
    color_links: bool = False
    url_color: str = "black"

    @classmethod
    def from_json(cls, filepath: str) -> "Settings":
        with open(filepath, encoding="utf-8") as f:
            return cls(**json.load(f))

    def to_json(self, filepath: str, indent=4):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(dataclasses.asdict(self), f, indent=indent)

    def __setattr__(self, attr, value):
        if attr in [
            "default_activities_section_title",
            "awards_section_title",
            "skills_section_title",
        ]:
            value = sanitize_headings(value)
        super().__setattr__(attr, value)


def render(*, template_path: str, cv: CV, settings: Settings):
    with open(template_path, encoding="utf-8") as template_file:
        template_str = template_file.read()
    template = ENVIRONMENT.from_string(template_str)
    return template.render(cv=cv, settings=settings)


# An abridged version of txtparse._preprocess
def sanitize_headings(s: str):
    # escape special characters `_`, `$`, '%', and `&`
    s = re.sub("([_$%&])", r"\\\1", s)

    # preserve `^` and escaped `*`
    s = s.replace("^", "\\^{}")
    s = s.replace("\\*", '{\\char"002A}')

    return s
