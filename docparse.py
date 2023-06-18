import docx
from docx.text.paragraph import Paragraph, Run
from docx.oxml.shared import qn


def parse(path: str) -> str:
    doc = docx.Document(path)
    results = [_process_para(para) for para in doc.paragraphs]
    return "\n".join(results)


def _process_para(para: Paragraph):
    results = []
    if para.style.name == "List Paragraph":
        results.append("- ")
    for run in _get_runs(para):
        if run.bold and run.italic:
            text = f"***{run.text}***"
        elif run.bold:
            text = f"**{run.text}**"
        elif run.italic:
            text = f"*{run.text}*"
        else:
            text = run.text
        if run.font.small_caps:
            text = f"\\textsc{{{text}}}"
        results.append(text)

    return "".join(results)


# Workaround taken from
# https://github.com/python-openxml/python-docx/issues/85#issuecomment-1010150776
def _get_runs(para: Paragraph):
    def _get(node, parent):
        for child in node:
            if child.tag == qn("w:r"):
                yield Run(child, parent)
            elif child.tag == qn("w:hyperlink"):
                yield from _get(child, parent)

    return list(_get(para._element, para))
