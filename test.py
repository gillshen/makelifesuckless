from txtparse import parse
from render import render, Settings


def test_parse():
    with open("tests/test_src.txt", encoding="utf-8") as f:
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
    with open("tests/test_src.txt", encoding="utf-8") as f:
        cv = parse(f.read())
    with open("tests/test_result.tex", "w", encoding="utf-8") as f:
        f.write(render("templates/classic.tex", settings=settings, cv=cv))


if __name__ == "__main__":
    # test_parse()
    # test_render()
    test_parse_and_render()
