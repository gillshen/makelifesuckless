from txtparse import parse
from render import render, Settings
from shell import run_lualatex

TXT_PATH = "tests/test_src.txt"
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
    args = {
        "name": "Alice",
        "activities": ["hiking", "rowing", "digging graves"],
        "awards": ["silliest walker", "best mole"],
    }
    print(render("tests/test_template.tex", **args))


def test_parse_and_render():
    settings = Settings(main_font="EB Garamond", secondary_font="EB Garamond")
    with open(TXT_PATH, encoding="utf-8") as f:
        cv = parse(f.read())
    with open(TEX_PATH, "w", encoding="utf-8") as f:
        f.write(render(TEMPLATE_PATH, settings=settings, cv=cv))
    run_lualatex(TEX_PATH, dest_path="tests/test_output.pdf")


if __name__ == "__main__":
    # test_parse()
    # test_render()
    test_parse_and_render()
