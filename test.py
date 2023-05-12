from txtparse import parse
from render import render, Settings
from shell import run_lualatex

TXT_PATH = "tests/test_src1.txt"
TEX_PATH = "tests/test_output.tex"
TEMPLATE_PATH = "templates/classic.tex"


def test_parse():
    with open(TXT_PATH, encoding="utf-8") as f:
        cv = parse(f.read())

    print(f"{cv.name=}")
    print(f"{cv.email=}")
    print(f"{cv.address=}")
    print(f"{cv.phone=}")

    for education in cv.education:
        print(education)
    for activity in cv.activities:
        print(activity)
    for award in cv.awards:
        print(award)
    for skillset in cv.skillsets:
        print(skillset)


def test_render():
    settings = Settings(
        main_font="Crimson Pro",
        heading_font="Open Sans",
        title_font="Crimson Pro",
        old_style_numbers=True,
        line_spread=1.05,
        paragraph_skip_in_pt=1,
        entry_skip_in_pt=6,
        bold_headings=False,
        date_style="american slash",
        color_links=True,
        url_color="blue",
    )
    with open(TXT_PATH, encoding="utf-8") as f:
        cv = parse(f.read())
    with open(TEX_PATH, "w", encoding="utf-8") as f:
        f.write(render(template_path=TEMPLATE_PATH, settings=settings, cv=cv))
    run_lualatex(TEX_PATH, dest_path="tests/test_output.pdf")


if __name__ == "__main__":
    # test_parse()
    test_render()
