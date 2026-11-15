"""Fetch and cache the open fonts used by the CV."""

import hashlib
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


FONT_COMMIT = "cc39c4c2c304bc368c9b7c311ea2bcc6013299fe"
GIT_URL = "https://github.com/google/fonts.git"
RAW_URL = f"https://raw.githubusercontent.com/google/fonts/{FONT_COMMIT}/"
FONTS = {
    "carlito/Carlito-Regular.ttf": "f6418f708baede9789daef5d458c0f53d2a888af9820e8062934e504fedc6595",
    "carlito/Carlito-Bold.ttf": "bb5d20f79b82599ec72983597437373a80f2d2085fa91fc144fd74e876a594db",
    "notosanssc/NotoSansSC[wght].ttf": "a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da",
}


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def read_upstream(files, temporary):
    try:
        results = {}
        for filename in files:
            url = RAW_URL + quote(f"ofl/{filename}")
            with urlopen(url, timeout=20) as response:
                results[filename] = response.read()
        return results
    except (URLError, OSError):
        # Git offers a second transport when a network blocks GitHub's raw host.
        checkout = temporary / "google-fonts"
        checkout.mkdir()
        environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        commands = (
            ("init", "--quiet"),
            ("remote", "add", "origin", GIT_URL),
            ("config", "remote.origin.promisor", "true"),
            ("config", "remote.origin.partialclonefilter", "blob:none"),
            ("fetch", "--quiet", "--depth=1", "--filter=blob:none", "origin", FONT_COMMIT),
            ("sparse-checkout", "set", "ofl/carlito", "ofl/notosanssc"),
            ("checkout", "--quiet", "--detach", "FETCH_HEAD"),
        )
        for command in commands:
            subprocess.run(["git", *command], cwd=checkout, env=environment, check=True)
        return {filename: (checkout / "ofl" / filename).read_bytes() for filename in files}


def ensure_fonts(cache):
    cache.mkdir(parents=True, exist_ok=True)
    sources = {filename: cache / Path(filename).name for filename in FONTS}
    missing = [
        filename for filename, path in sources.items()
        if not path.is_file() or digest(path.read_bytes()) != FONTS[filename]
    ]
    with TemporaryDirectory(dir=cache) as work:
        temporary = Path(work)
        if missing:
            blobs = read_upstream(missing, temporary)
            for filename, blob in blobs.items():
                if digest(blob) != FONTS[filename]:
                    raise RuntimeError(f"Unexpected SHA-256 for {filename}")
                staged = temporary / Path(filename).name
                staged.write_bytes(blob)
                staged.replace(sources[filename])

        variable_font = sources["notosanssc/NotoSansSC[wght].ttf"]
        regular_font = cache / "NotoSansSC-Regular.ttf"
        if missing or not regular_font.is_file():
            staged = temporary / regular_font.name
            with TTFont(variable_font, recalcTimestamp=False) as font:
                instantiateVariableFont(font, {"wght": 400}, inplace=True, updateFontNames=True)
                font.save(staged)
            staged.replace(regular_font)
    return cache
