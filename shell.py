import os
import subprocess


def run_lualatex(src_path, dest_path="", open_when_done=True):
    subprocess.call(["lualatex", "-interaction=nonstopmode", src_path])
    base_name, _ = os.path.splitext(os.path.split(src_path)[-1])
    base_path = f"{base_name}.pdf"
    if dest_path:
        os.replace(base_path, dest_path)
    if open_when_done:
        os.startfile(os.path.join(*os.path.split(dest_path or base_path)))
    # clean up
    os.remove(f"{base_name}.aux")
    os.remove(f"{base_name}.log")
