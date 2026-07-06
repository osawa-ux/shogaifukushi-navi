#!/usr/bin/env python3
"""validate_data.py — shogaifukushi-navi（welfare）データ整合性チェック（lightweight, 標準ライブラリのみ）

CLAUDE.md「Data Integrity Check」を機械化したもの。deploy ゲートに組み込める形
（exit code 0 = green / 非0 = fail）。

## ビルド入力の裏取り

`~/projects/MyPython/site_config_shogaifukushi.json` の `data_file` は
`../shogaifukushi-navi/data/shogaifukushi_build.json`（= このrepoの
data/shogaifukushi_build.json）。data/shogaifukushi.json とレコード数は
同一（40,403件・2026-07-06実測）だが、ビルドの正式な入力は build.json 側。

## 件数の関係式（実測で裏取り済み・FAIL 対象・303件差の要因特定済み）

data/shogaifukushi_build.json の生 40,403 件に対し、
site_shogaifukushi/office/*.html は 40,100 件で **303 件差**があった
（brief 証跡ブロック時点）。

MyPython/build_site.py の生成ロジック（6797行目〜「重複排除」節、
6808行目〜「休業・閉業を除外」節、6816行目〜「kikan_kbn==2 のみ残す」節）を
Read し、同一ロジックで実データを再計算したところ 40,100 件に一致した:

  1. 重複排除: 同一 kikan_cd を持つレコードは 1 件目のみ残す
     （2026-07-06実測: 284種の kikan_cd が重複し、延べ 303 件が重複分）
  2. business_status が CLOSED_TEMPORARILY / CLOSED_PERMANENTLY のものを除外
     （実測: 40,403件全件が OPERATIONAL のため今回は 0 件除外）
  3. kikan_kbn == '2' のみ残す（実測: 40,403件全件が '2' のため今回は 0 件除外）

上記 3 ステップを適用した期待 detail 件数 == 40,100 で実測と完全一致。
よって「303件差」は不整合ではなく **build_site.py の意図した重複排除ロジックの
既知の挙動** と特定できた。この関係式を FAIL 条件として実装する
（build_site.py 側は Read only・本 script はロジックを複製するのみで、
build_site.py 自体は変更しない）。

  - detail_html_count (site_shogaifukushi/office/*.html) == expected_detail_count
        （= dedup(kikan_cd) + 休業閉業除外 + kikan_kbn=='2' 適用後の件数）
  - search_json_total (site_shogaifukushi/data/search/*.json 合計) == expected_detail_count

## WARN 止まりの項目（関係式が未確定）

  - sitemap.xml の <loc> 数、site_shogaifukushi 内 HTML 総数: pref/city ページ・
    static ページ等 detail 以外の URL も含むため、厳密な関係式が未確定。
    回帰検知の目的で baseline には記録するが、単独では FAIL 条件にしない。

## baseline ファイル

scripts/validation_baseline.json（このrepo内・PHI なし・件数と実行時刻のみ）。
git 管理は人間判断。初回実行時は記録のみ、2 回目以降は前回との差分が 5% 超の
減少で FAIL、5% 以下の減少で WARN。

Usage:
    python scripts/validate_data.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Windows のデフォルト stdout エンコーディング（cp932）だと日本語ログが文字化けする
# 環境があるため、UTF-8 に固定する（CI の Ubuntu ランナー等では no-op）。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "shogaifukushi_build.json"
SITE_DIR = REPO_ROOT / "site_shogaifukushi"
DETAIL_DIR = SITE_DIR / "office"
SEARCH_DIR = SITE_DIR / "data" / "search"
SITEMAP_FILE = SITE_DIR / "sitemap.xml"
BASELINE_FILE = REPO_ROOT / "scripts" / "validation_baseline.json"

# schema.yaml がこの repo に存在しないため、実データ構造から rendering・識別に
# 必須と判断したフィールドを直接指定する。
REQUIRED_FIELDS = ["kikan_cd", "name", "address", "pref"]

CLOSED_STATUSES = {"CLOSED_TEMPORARILY", "CLOSED_PERMANENTLY"}
BASELINE_DROP_FAIL_RATIO = 0.05  # 5% 超の減少で FAIL

results: list[tuple[str, str]] = []


def log(level: str, message: str) -> None:
    results.append((level, message))
    print(f"[{level}] {message}")


def load_data() -> list[dict]:
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def expected_detail_count(records: list[dict]) -> int:
    """build_site.py の重複排除ロジック（kikan_cd 一次採用 + 休業閉業除外 +
    kikan_kbn=='2' フィルタ）を複製して期待 detail 件数を算出する。"""
    seen: set[str] = set()
    count = 0
    for r in records:
        if r.get("business_status") in CLOSED_STATUSES:
            continue
        if r.get("kikan_kbn") != "2":
            continue
        kcd = r.get("kikan_cd")
        if kcd in seen:
            continue
        seen.add(kcd)
        count += 1
    return count


def count_html_files(directory: Path, exclude_names: set[str] = frozenset()) -> int:
    if not directory.exists():
        return 0
    n = 0
    for entry in directory.iterdir():
        if entry.is_file() and entry.suffix == ".html" and entry.name not in exclude_names:
            n += 1
    return n


def count_html_files_recursive(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for p in directory.rglob("*.html") if p.is_file())


def sum_search_json(directory: Path) -> int:
    if not directory.exists():
        return 0
    total = 0
    for f in sorted(directory.glob("*.json")):
        with open(f, encoding="utf-8") as fh:
            total += len(json.load(fh))
    return total


def count_sitemap_locs(sitemap_file: Path) -> int:
    if not sitemap_file.exists():
        return 0
    return len(re.findall(r"<loc>", sitemap_file.read_text(encoding="utf-8")))


def check_required_fields(records: list[dict]) -> None:
    missing_total = 0
    per_field: dict[str, int] = {}
    for field in REQUIRED_FIELDS:
        missing = sum(1 for r in records if not r.get(field) and r.get(field) != 0 and r.get(field) is not False)
        if missing:
            per_field[field] = missing
            missing_total += missing
    if missing_total == 0:
        log("OK", f"必須フィールド欠落チェック: 欠落なし（{len(REQUIRED_FIELDS)} フィールド確認）")
    else:
        detail = ", ".join(f"{k}={v}件" for k, v in per_field.items())
        log("WARN", f"必須フィールド欠落あり（新規チェックにつき FAIL 条件にはしない・要人手確認）: {detail}")


def check_internal_link_spot(site_dir: Path) -> None:
    """代表ページ数件の href（サイトルート相対 '/...'）が生成物内に実在するか軽量確認。全ページ走査はしない。"""
    if not site_dir.exists():
        log("WARN", "internal link spot check: site_shogaifukushi/ が存在しないためスキップ")
        return

    candidates: list[Path] = []
    top = site_dir / "index.html"
    if top.exists():
        candidates.append(top)
    pref_dir = site_dir / "pref"
    if pref_dir.exists():
        for p in sorted(pref_dir.glob("*.html"))[:1]:
            candidates.append(p)
    if DETAIL_DIR.exists():
        for entry in DETAIL_DIR.iterdir():
            if entry.is_file() and entry.suffix == ".html":
                candidates.append(entry)
                break

    if not candidates:
        log("WARN", "internal link spot check: 代表ページが見つからずスキップ")
        return

    from urllib.parse import unquote

    def href_resolves(href: str) -> bool:
        path_part = href.split("?")[0]
        for rel in (path_part.lstrip("/"), unquote(path_part).lstrip("/")):
            if rel == "":
                rel = "index.html"
            elif rel.endswith("/"):
                rel = rel + "index.html"
            if (site_dir / rel).exists():
                return True
        return False

    checked = 0
    broken: list[str] = []
    for page in candidates:
        html = page.read_text(encoding="utf-8", errors="replace")
        hrefs = [h for h in re.findall(r'href="(/[^"#]*)"', html) if not h.startswith("//")]
        for href in hrefs[:10]:
            checked += 1
            if not href_resolves(href):
                broken.append(f"{page.relative_to(site_dir)} -> {href}")

    if broken:
        log("WARN", f"internal link spot check: {checked} 件中 {len(broken)} 件のリンク切れ疑い: {broken[:5]}")
    else:
        log("OK", f"internal link spot check: {len(candidates)} 代表ページ・{checked} href を確認、リンク切れなし")


def check_baseline(metrics: dict[str, int]) -> None:
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    previous = None
    if BASELINE_FILE.exists():
        try:
            previous = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            previous = None

    if previous is None:
        log("OK", f"baseline: 初回記録（{BASELINE_FILE.name} に保存）")
    else:
        prev_metrics = previous.get("metrics", {})
        for key, current_value in metrics.items():
            prev_value = prev_metrics.get(key)
            if prev_value is None or prev_value == 0:
                continue
            if current_value >= prev_value:
                continue
            drop_ratio = (prev_value - current_value) / prev_value
            if drop_ratio > BASELINE_DROP_FAIL_RATIO:
                log("FAIL", f"baseline 差分: {key} が {prev_value} → {current_value}（{drop_ratio:.1%} 減少・5%超）")
            else:
                log("WARN", f"baseline 差分: {key} が {prev_value} → {current_value}（{drop_ratio:.1%} 減少）")

    # ラチェットガード（reviewer 指摘 2026-07-06）: FAIL 検出時は baseline を上書きしない。
    # 上書きすると件数減少 FAIL が naive リトライで緑化し「件数減少=停止」の警報が消えるため、
    # FAIL ゼロのときのみ現在値を新 baseline として記録する。
    if any(level == "FAIL" for level, _ in results):
        log("WARN", "baseline: FAIL 検出のため更新せず（解消後の実行で更新される）")
        return
    import datetime
    BASELINE_FILE.write_text(
        json.dumps({"last_run": datetime.datetime.now().isoformat(), "metrics": metrics}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    if not DATA_FILE.exists():
        print(f"ERROR: {DATA_FILE} が存在しません。")
        return 1

    records = load_data()
    data_count = len(records)
    expected_detail = expected_detail_count(records)
    log("OK", f"データ件数（実測・生データ）: {data_count}件")
    log("OK", f"期待 detail 件数（重複排除+休業閉業除外+kikan_kbn=='2' 適用後）: {expected_detail}件")

    if not SITE_DIR.exists():
        log("OK", "site_shogaifukushi/ が存在しません（未ビルド）。件数整合チェックは skip します。")
        check_baseline({"data_record_count": data_count, "expected_detail_count": expected_detail})
        return 0

    detail_count = count_html_files(DETAIL_DIR)
    search_total = sum_search_json(SEARCH_DIR)
    sitemap_locs = count_sitemap_locs(SITEMAP_FILE)
    total_html = count_html_files_recursive(SITE_DIR)

    log("OK", f"detail HTML 件数: {detail_count}件")
    log("OK", f"search JSON 合計件数: {search_total}件")
    log("OK", f"sitemap <loc> 数: {sitemap_locs}件 / site_shogaifukushi 全 HTML: {total_html}件（関係式未確定・参考値）")

    if detail_count == expected_detail:
        log("OK", f"件数整合: detail_html({detail_count}) == expected_detail_count({expected_detail})")
    else:
        log("FAIL", f"件数整合 NG: detail_html({detail_count}) != expected_detail_count({expected_detail})")

    if search_total == expected_detail:
        log("OK", f"件数整合: search_json_total({search_total}) == expected_detail_count({expected_detail})")
    else:
        log("FAIL", f"件数整合 NG: search_json_total({search_total}) != expected_detail_count({expected_detail})")

    check_required_fields(records)
    check_internal_link_spot(SITE_DIR)

    metrics = {
        "data_record_count": data_count,
        "expected_detail_count": expected_detail,
        "detail_html_count": detail_count,
        "search_json_total": search_total,
        "sitemap_loc_count": sitemap_locs,
        "total_html_count": total_html,
    }
    check_baseline(metrics)

    fail_count = sum(1 for level, _ in results if level == "FAIL")
    warn_count = sum(1 for level, _ in results if level == "WARN")
    print(f"\n=== summary: FAIL={fail_count} WARN={warn_count} OK={len(results) - fail_count - warn_count} ===")
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
