from txtparse import parse
from render import Settings, render
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


TEST_SETTINGS = Settings(
    show_activity_locations=True,
    show_time_commitments=True,
    main_font="Crimson Pro",
    heading_font="Open Sans",
    title_font="Crimson Pro",
    old_style_numbers=True,
    line_spread=1.05,
    paragraph_skip_in_pt=0,
    entry_skip_in_pt=6,
    bold_headings=True,
    bullet_text="\u2020",
    bullet_item_sep_in_em=1.0,
    date_style="american",
    color_links=True,
    url_color="blue",
)


def test_json_read_write():
    TEST_SETTINGS.to_json("tests/test_output.json", indent=2)
    new_settings = Settings.from_json("tests/test_output.json")
    assert new_settings == TEST_SETTINGS


def test_render():
    with open(TXT_PATH, encoding="utf-8") as f:
        cv = parse(f.read())
    with open(TEX_PATH, "w", encoding="utf-8") as f:
        f.write(render(template_path=TEMPLATE_PATH, settings=TEST_SETTINGS, cv=cv))
    run_lualatex(TEX_PATH, dest_path="tests/test_output.pdf")


if __name__ == "__main__":
    # test_parse()
    test_json_read_write()
    test_render()
