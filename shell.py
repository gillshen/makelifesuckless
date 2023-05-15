import os
import subprocess


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
