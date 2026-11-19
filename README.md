# Academic CV template

Mingyu Bian’s official English and Simplified Chinese CVs use the detailed desktop layout. The PDFs in this repository are copies of the files served on the homepage.

- English [homepage PDF](https://mybian.cn/mingyu-bian-cv.pdf) · [repository PDF](pdf/mingyu-bian-cv-en.pdf)
- 简体中文 [主页 PDF](https://mybian.cn/mingyu-bian-cv-zh.pdf) · [仓库 PDF](pdf/mingyu-bian-cv-zh.pdf)

## Build the reusable template

The optional JSON renderer produces a compact template for reuse. It uses Python 3.11 and the versions in [requirements.txt](requirements.txt).

**Windows PowerShell**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe generate_cv.py --language en --expected-pages 2 --output build/mingyu-bian-cv-en.pdf
.\.venv\Scripts\python.exe generate_cv.py --language zh --expected-pages 2 --output build/mingyu-bian-cv-zh.pdf
```

**macOS and Linux**

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python generate_cv.py --language en --expected-pages 2 --output build/mingyu-bian-cv-en.pdf
.venv/bin/python generate_cv.py --language zh --expected-pages 2 --output build/mingyu-bian-cv-zh.pdf
```

The first build downloads and verifies the fonts and caches them in `build/fonts/`. If the raw download host is unavailable, the generator uses Git on your PATH to fetch the same pinned source. The cached fonts support later builds offline.

## Edit the content

Update [cv.json](cv.json) and rebuild both PDFs. Fields such as `title_zh` and `status_zh` supply Chinese versions of `title` and `status`. Dates, author lists, paper titles, and URLs can be shared by both languages. The `sections` and each section’s `items` render in file order. Use the `entries` layout for dated entries, `publications` for research outputs, and `awards` for competition names and results. An entry can include a URL and one or more detail lines. Set `new_page` to start a section on the next page or `entry_spacing` to adjust the space after each item in points. The optional `alternate_name` adds a second name alongside the primary name.

`profile.biography` contains paragraphs and optional headings. Use either a plain `text` string or a list of labeled text segments with optional URLs.

The optional `wechat_accounts` list adds official account names, descriptions, and QR codes at the end. Set `qr_image` relative to the JSON file and specify `"language": "zh"` for a Chinese account name.

To use different content or an output path, run `python generate_cv.py --data path/to/cv.json --output path/to/cv.pdf` with the virtual environment’s Python. Use `--expected-pages` when you want the build to reject a layout that exceeds or falls short of a chosen page count.

## GitHub downloads

The [workflow](.github/workflows/build.yml) packages the checked-in official PDFs on pushes and pull requests to `main` and supports manual runs. Open **Actions → Package official CV PDFs → a successful run → Artifacts → academic-cv** to download both PDFs from that run.

## Fonts

The renderer uses [Carlito](https://github.com/googlefonts/carlito) and [Noto Sans SC](https://github.com/google/fonts/tree/cc39c4c2c304bc368c9b7c311ea2bcc6013299fe/ofl/notosanssc). The first build verifies the SHA-256 hashes in [fonts.py](fonts.py) and creates the Noto Sans SC weights needed by each language. The [Carlito](fonts/Carlito-OFL.txt) and [Noto Sans SC](fonts/NotoSansSC-OFL.txt) license notices contain their SIL Open Font License terms.
