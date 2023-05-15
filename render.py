import dataclasses
import json

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

    # heading appearance
    bold_headings: bool = True
    all_cap_headings: bool = True
    default_activities_section_title: str = "Activities"
    awards_section_title: str = "Awards"
    skills_section_title: str = "Skills"

    # date formatting
    date_style: str = "american"

    # url appearance
    url_font_follows_text: bool = True
    color_links: bool = False
    url_color: str = "black"

    @classmethod
    def from_json(cls, filepath: str) -> "Settings":
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def to_json(self, filepath: str, indent=4):
        data = dataclasses.asdict(self)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)


def render(*, template_path: str, cv: CV, settings: Settings):
    with open(template_path, encoding="utf-8") as template_file:
        template_str = template_file.read()
    template = ENVIRONMENT.from_string(template_str)
    return template.render(cv=cv, settings=settings)
