import os
import subprocess

import txtparse
import docparse
from tex import Settings, render


TXT_PATH = "tests/sample1.txt"
DOC_PATH = "tests/sample2.docx"
TEX_PATH = "output.tex"
TEMPLATE_PATH = "templates/classic.tex"


def test_txt_parse():
    with open(TXT_PATH, encoding="utf-8") as f:
        cv, unparsed = txtparse.parse(f.read())
    _print_parsed(cv, unparsed)


def test_doc_parse():
    cv, unparsed = txtparse.parse(docparse.parse(DOC_PATH))
    _print_parsed(cv, unparsed)


def _print_parsed(cv: txtparse.CV, unparsed: list):
    print(cv.to_json())
    print(f"Unparsed lines: {len(unparsed)}")
    print(*unparsed, sep="\n")


TEST_SETTINGS = Settings(
    show_activity_locations=True,
    show_time_commitments=True,
    main_font="Crimson Pro",
    heading_font="Crimson Pro",
    title_font="Crimson Pro",
    old_style_numbers=True,
    before_sectitle_skip_in_pt=9,
    paragraph_skip_in_pt=0,
    entry_skip_in_pt=6,
    bold_headings=True,
    bullet_item_sep_in_em=1.0,
    bullet_indent_in_em=1.0,
    date_style="american",
    contact_divider="\u2022",
    color_links=True,
    url_color="cyan",
)


def test_json_read_write():
    TEST_SETTINGS.to_json("output.json", indent=2)
    new_settings = Settings.from_json("output.json")
    assert new_settings == TEST_SETTINGS


def test_render():
    with open(TXT_PATH, encoding="utf-8") as f:
        cv, _ = txtparse.parse(f.read())
    with open(TEX_PATH, "w", encoding="utf-8") as f:
        f.write(render(template_path=TEMPLATE_PATH, settings=TEST_SETTINGS, cv=cv))
    run_lualatex(TEX_PATH, dest_path="output.pdf")


def run_lualatex(
    src_path,
    *,
    dest_path="",
    stdout=None,
    stderr=None,
    capture_output=False,
    open_when_done=True,
):
    proc = subprocess.run(
        ["lualatex", "-interaction=nonstopmode", src_path],
        check=True,
        stdout=stdout,
        stderr=stderr,
        capture_output=capture_output,
    )
    # move the resultant pdf
    base_name, _ = os.path.splitext(os.path.split(src_path)[-1])
    base_path = f"{base_name}.pdf"
    if dest_path:
        os.replace(base_path, dest_path)
    if open_when_done:
        os.startfile(os.path.join(*os.path.split(dest_path or base_path)))
    # clean up
    os.remove(f"{base_name}.aux")
    os.remove(f"{base_name}.log")
    os.remove(f"{base_name}.out")

    return proc


if __name__ == "__main__":
    test_txt_parse()
    test_doc_parse()
    test_json_read_write()
    test_render()
