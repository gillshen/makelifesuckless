import dataclasses
import jinja2

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
    main_font: str
    heading_font: str
    title_font: str
    proportional_numbers: bool = True
    old_style_numbers: bool = False
    paper: str = "a4paper"
    font_size_in_point: int = 11
    heading_relative_size: str = "large"
    title_relative_size: str = "LARGE"
    bold_headings: bool = True
    all_cap_headings: bool = True
    top_margin_in_inch: int = 0.8
    bottom_margin_in_inch: int = 1
    left_margin_in_inch: int = 1
    right_margin_in_inch: int = 1
    color_links: bool = False
    url_style: str = "rm"
    date_style: str = "american"


def render(template_filename, **args):
    with open(template_filename, encoding="utf-8") as template_file:
        template_str = template_file.read()
    template = ENVIRONMENT.from_string(template_str)
    return template.render(**args)
