# Academic CV template

A two-page English academic CV generated from editable JSON. The example contains Mingyu Bian’s public academic CV. The PDF includes a bilingual name, linked institutions and papers, education, research experience, projects, community service, publications and awards.

## Build the PDF

Use Python 3.11. From the repository root, create a virtual environment and install the versions in [requirements.txt](requirements.txt).

**Windows PowerShell**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe generate_cv.py --expected-pages 2
```

**macOS and Linux**

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python generate_cv.py --expected-pages 2
```

Open `build/academic-cv.pdf`. The first build downloads and verifies the fonts and caches them in `build/fonts/`. If the raw download host is unavailable, the generator uses Git on your PATH to fetch the same pinned source. The cached fonts support later builds offline.

## Edit the content

Update [cv.json](cv.json) and rerun the build command. The `sections` and each section’s `items` render in file order. Use the `entries` layout for dated entries, `publications` for research outputs, and `awards` for honors and competition roles. An entry can include a URL and one or more detail lines. Set `new_page` to start a section on the next page or `entry_spacing` to adjust the space after each item in points. The optional `alternate_name` adds a second name alongside the primary name.

The optional `wechat_accounts` list adds official account names, descriptions, and QR codes at the end. Set `qr_image` relative to the JSON file and specify `"language": "zh"` for a Chinese account name.

To use different content or an output path, run `python generate_cv.py --data path/to/cv.json --output path/to/cv.pdf` with the virtual environment’s Python. Use `--expected-pages` when you want the build to reject a layout that exceeds or falls short of a chosen page count.

## Build on GitHub

The [workflow](.github/workflows/build.yml) rebuilds the PDF on pushes and pull requests to `main`, and supports manual runs. Open **Actions → Build academic CV → a successful run → Artifacts → academic-cv** to download that run’s PDF. To refresh the document, edit `cv.json` and push the change. The build uses public dependencies and requires no repository secrets.

## Fonts

The renderer uses [Carlito](https://github.com/googlefonts/carlito) for Latin text and [Noto Sans SC](https://github.com/google/fonts/tree/cc39c4c2c304bc368c9b7c311ea2bcc6013299fe/ofl/notosanssc) for the alternate name. The first build verifies the SHA-256 hashes in [fonts.py](fonts.py) and creates a regular-weight instance of Noto Sans SC. The [Carlito](fonts/Carlito-OFL.txt) and [Noto Sans SC](fonts/NotoSansSC-OFL.txt) license notices contain their SIL Open Font License terms.
