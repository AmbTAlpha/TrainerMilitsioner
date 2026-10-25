import ast
import io
import re
import shutil
import subprocess
import sys
import tokenize
import zipfile
from pathlib import Path

VERSION = "1.0"
HERE = Path(__file__).resolve().parent
OUT = HERE / "release"


def strip_python(source):
    lines = source.splitlines(keepends=True)
    comments = [t.start for t in tokenize.generate_tokens(io.StringIO(source).readline) if t.type == tokenize.COMMENT]
    for row, col in reversed(comments):
        kept = lines[row - 1][:col].rstrip()
        lines[row - 1] = (kept + "\n") if kept else None
    text = "".join(line for line in lines if line is not None)
    return re.sub(r"\n{3,}", "\n\n", text)


def strip_lua(source):
    out, i, n = [], 0, len(source)
    while i < n:
        if source.startswith("--", i):
            match = re.match(r"--\[(=*)\[", source[i:])
            if match:
                end = source.find("]" + match.group(1) + "]", i)
                i = n if end < 0 else end + len(match.group(1)) + 2
            else:
                while i < n and source[i] != "\n":
                    i += 1
        elif source[i] in "\"'":
            quote = source[i]
            out.append(source[i])
            i += 1
            while i < n and source[i] != quote:
                if source[i] == "\\":
                    out.append(source[i])
                    i += 1
                out.append(source[i])
                i += 1
            out.append(source[i:i + 1])
            i += 1
        else:
            match = re.match(r"\[(=*)\[", source[i:]) if source[i] == "[" else None
            if match:
                end = source.find("]" + match.group(1) + "]", i)
                end = n if end < 0 else end + len(match.group(1)) + 2
                out.append(source[i:end])
                i = end
            else:
                out.append(source[i])
                i += 1
    text = "".join(out)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def lua_bytecode(source_bytes):
    from lupa.lua54 import LuaRuntime
    lua = LuaRuntime(encoding=None)
    dump = lua.eval(b'function(s) return string.dump(assert(load(s, "=core")), true) end')(source_bytes)
    lua.eval(b'function(b) return assert(load(b, "core", "b")) end')(dump)
    return dump


def build_exe(menu_clean):
    work = HERE / "build_tmp"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()
    (work / "menu.py").write_text(menu_clean, encoding="utf-8", newline="\n")
    icon = work / "trainer.ico"
    subprocess.run([sys.executable, str(work / "menu.py"), "--make-icon", str(icon)], check=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
                    "--icon", str(icon), "--name", "TrainerMilitsioner", "--collect-all", "customtkinter",
                    "--distpath", str(work / "dist"), "--workpath", str(work / "work"),
                    "--specpath", str(work), str(work / "menu.py")], check=True)
    return work / "dist" / "TrainerMilitsioner.exe"


def assemble(name, menu_clean, core_text, bytecode, exe_path):
    root = OUT / name
    mod = root / "Mods" / "TrainerMilitsioner"
    scripts = mod / "scripts"
    scripts.mkdir(parents=True)
    if bytecode:
        (scripts / "core.bin").write_bytes(lua_bytecode(core_text.encode("utf-8")))
    else:
        (scripts / "core.lua").write_text(core_text, encoding="utf-8", newline="\n")
    (scripts / "main.lua").write_text(strip_lua((HERE / "main.lua").read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    shutil.copy(HERE / "items_catalog.tsv", scripts / "items_catalog.tsv")
    (scripts / "trainer_config.ini").write_text("toggle_key=F7\n", encoding="utf-8")
    (mod / "enabled.txt").write_text("", encoding="utf-8")
    if exe_path:
        shutil.copy(exe_path, mod / "TrainerMilitsioner.exe")
        shutil.copy(HERE / "LISEZMOI_EXE.txt", root / "LISEZMOI.txt")
    else:
        (scripts / "menu.py").write_text(menu_clean, encoding="utf-8", newline="\n")
        shutil.copy(HERE / "install_requirements.bat", mod / "install_requirements.bat")
        shutil.copy(HERE / "LISEZMOI_SANS_EXE.txt", root / "LISEZMOI.txt")
    archive = OUT / ("TrainerMilitsioner_v" + VERSION + "_" + name + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(root))
    print("OK :", archive)


def main():
    bytecode = "--bytecode" in sys.argv
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    menu_src = (HERE / "menu.py").read_text(encoding="utf-8")
    menu_clean = strip_python(menu_src)
    assert ast.dump(ast.parse(menu_src)) == ast.dump(ast.parse(menu_clean))
    core_text = strip_lua((HERE / "core.lua").read_text(encoding="utf-8"))

    assemble("SANS_EXE", menu_clean, core_text, bytecode, None)
    if "--exe" in sys.argv:
        assemble("EXE", menu_clean, core_text, bytecode, build_exe(menu_clean))
    else:
        print("Version EXE ignoree (lance BUILD_EXE.bat sous Windows pour la construire)")


if __name__ == "__main__":
    main()
