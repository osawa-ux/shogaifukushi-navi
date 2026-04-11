"""
WAM NET 障害福祉サービス等情報公表オープンデータ CSV一括ダウンロード

データソース: https://www.wam.go.jp/content/wamnet/pcpub/top/sfkopendata/
ライセンス: 営利・非営利問わず利用可能（利用報告推奨）
更新頻度: 年2回（3月末・9月末時点）

使い方:
  python scripts/download_wam_csv.py          # 全ファイルダウンロード
  python scripts/download_wam_csv.py --mvp    # MVP対象（放デイ・児発）のみ
  python scripts/download_wam_csv.py --force  # 既存ファイル上書き
"""

import csv
import hashlib
import io
import json
import os
import sys
import zipfile
from datetime import datetime

import requests

# === 設定 ===
BASE_URL = "https://www.wam.go.jp/content/files/pcpub/top/sfkopendata/202509"
DATA_PERIOD = "202509"  # 2025年9月末時点

# サービス種別とNN番号の対応表
SERVICE_FILES = {
    11: "居宅介護",
    12: "重度訪問介護",
    13: "行動援護",
    14: "重度障害者等包括支援",
    15: "同行援護",
    21: "療養介護",
    22: "生活介護",
    32: "施設入所支援",
    33: "共同生活援助",
    41: "自立訓練（機能訓練）",
    42: "自立訓練（生活訓練）",
    45: "就労継続支援A型",
    46: "就労継続支援B型",
    52: "計画相談支援",
    53: "地域相談支援（地域移行支援）",
    54: "地域相談支援（地域定着支援）",
    60: "就労移行支援",
    61: "自立生活援助",
    62: "就労定着支援",
    63: "児童発達支援",
    64: "医療型児童発達支援",
    65: "放課後等デイサービス",
    66: "居宅訪問型児童発達支援",
    67: "保育所等訪問支援",
    68: "福祉型障害児入所施設",
    69: "医療型障害児入所施設",
    70: "障害児相談支援",
}

MVP_NNS = [63, 65]  # 児童発達支援、放課後等デイサービス

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "data_sources", "wam_net")
REPORT_DIR = os.path.join(BASE_DIR, "data_sources", "reports")


def download_and_extract(nn: int, service_name: str, force: bool = False) -> dict:
    """ZIPをダウンロードしてCSVを展開。結果情報を返す。"""
    zip_filename = f"sfkopendata_{DATA_PERIOD}_{nn:02d}.zip"
    zip_url = f"{BASE_URL}/{zip_filename}"
    csv_filename = f"csvdownload0{nn:02d}.csv"
    csv_path = os.path.join(OUTPUT_DIR, csv_filename)

    result = {
        "nn": nn,
        "service_name": service_name,
        "zip_url": zip_url,
        "zip_filename": zip_filename,
        "csv_filename": csv_filename,
        "csv_path": csv_path,
        "status": "unknown",
        "zip_size": None,
        "csv_size": None,
        "row_count": None,
        "error": None,
        "downloaded_at": datetime.now().isoformat(),
    }

    # 既存ファイルチェック
    if os.path.exists(csv_path) and not force:
        csv_size = os.path.getsize(csv_path)
        result["csv_size"] = csv_size
        result["status"] = "skipped"
        print(f"  [{nn:02d}] {service_name}: 既存ファイル使用 ({csv_size/1024:.0f}KB)")
        return result

    print(f"  [{nn:02d}] {service_name}: ダウンロード中... {zip_url}")
    try:
        r = requests.get(zip_url, timeout=120)
        r.raise_for_status()
    except requests.RequestException as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"  [{nn:02d}] {service_name}: [ERROR] {e}")
        return result

    zip_size = len(r.content)
    result["zip_size"] = zip_size

    # ZIP展開
    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            names = zf.namelist()
            # CSVファイルを探す（ZIPの中にZIPが入っている場合もある）
            csv_names = [n for n in names if n.endswith(".csv")]
            zip_names = [n for n in names if n.endswith(".zip")]

            if csv_names:
                # 通常パターン: ZIPの中にCSVが直接入っている
                target = csv_names[0]
                content = zf.read(target)
                with open(csv_path, "wb") as f:
                    f.write(content)
            elif zip_names:
                # ネストZIPパターン: ZIPの中にZIPが入っている
                inner_zip_content = zf.read(zip_names[0])
                with zipfile.ZipFile(io.BytesIO(inner_zip_content)) as inner_zf:
                    inner_csv = [n for n in inner_zf.namelist() if n.endswith(".csv")]
                    if inner_csv:
                        content = inner_zf.read(inner_csv[0])
                        with open(csv_path, "wb") as f:
                            f.write(content)
                    else:
                        result["status"] = "error"
                        result["error"] = f"内側ZIPにCSVなし: {inner_zf.namelist()}"
                        print(f"  [{nn:02d}] {service_name}: [ERROR] {result['error']}")
                        return result
            else:
                result["status"] = "error"
                result["error"] = f"ZIPにCSVなし: {names}"
                print(f"  [{nn:02d}] {service_name}: [ERROR] {result['error']}")
                return result
    except zipfile.BadZipFile as e:
        result["status"] = "error"
        result["error"] = f"不正なZIP: {e}"
        print(f"  [{nn:02d}] {service_name}: [ERROR] {result['error']}")
        return result

    csv_size = os.path.getsize(csv_path)
    result["csv_size"] = csv_size
    result["status"] = "success"
    print(f"  [{nn:02d}] {service_name}: OK ({zip_size/1024:.0f}KB ZIP → {csv_size/1024:.0f}KB CSV)")
    return result


def count_rows(csv_path: str) -> int:
    """CSVの行数をカウント（ヘッダー除く）。"""
    encodings = ["utf-8-sig", "utf-8", "cp932", "shift_jis"]
    for enc in encodings:
        try:
            with open(csv_path, encoding=enc) as f:
                reader = csv.reader(f)
                header = next(reader, None)
                count = sum(1 for _ in reader)
                return count
        except (UnicodeDecodeError, UnicodeError):
            continue
    return -1


def detect_encoding(csv_path: str) -> str:
    """CSVの文字コードを検出。"""
    encodings = ["utf-8-sig", "utf-8", "cp932", "shift_jis"]
    for enc in encodings:
        try:
            with open(csv_path, encoding=enc) as f:
                f.read(4096)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "unknown"


def main():
    mvp_only = "--mvp" in sys.argv
    force = "--force" in sys.argv

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

    target_nns = MVP_NNS if mvp_only else sorted(SERVICE_FILES.keys())

    print("=" * 70)
    print(f"  WAM NET 障害福祉サービスオープンデータ CSV取得")
    print(f"  データ時点: {DATA_PERIOD}")
    print(f"  対象: {'MVP（放デイ・児発）' if mvp_only else f'全{len(target_nns)}種別'}")
    print("=" * 70)

    results = []
    success_count = 0
    error_count = 0

    for nn in target_nns:
        service_name = SERVICE_FILES[nn]
        result = download_and_extract(nn, service_name, force=force)

        # 行数カウント
        if result["status"] in ("success", "skipped") and os.path.exists(result["csv_path"]):
            row_count = count_rows(result["csv_path"])
            result["row_count"] = row_count
            result["encoding"] = detect_encoding(result["csv_path"])

        if result["status"] == "error":
            error_count += 1
        else:
            success_count += 1

        results.append(result)

    # サマリー表示
    print("\n" + "=" * 70)
    print("  ダウンロード結果サマリー")
    print("=" * 70)
    print(f"  成功/スキップ: {success_count}件")
    print(f"  エラー: {error_count}件")

    total_rows = 0
    print(f"\n  {'NN':>4}  {'サービス種別':<30}  {'件数':>8}  {'CSVサイズ':>10}  {'文字コード':<12}")
    print("  " + "-" * 80)
    for r in results:
        if r["status"] != "error":
            rows = r.get("row_count", 0) or 0
            total_rows += rows
            size_kb = (r.get("csv_size", 0) or 0) / 1024
            enc = r.get("encoding", "?")
            print(f"  {r['nn']:>4}  {r['service_name']:<30}  {rows:>8,}  {size_kb:>8.0f}KB  {enc}")
        else:
            print(f"  {r['nn']:>4}  {r['service_name']:<30}  [ERROR] {r['error']}")

    print("  " + "-" * 80)
    print(f"  {'合計':<36}  {total_rows:>8,}")

    # 結果をJSONに保存
    report_path = os.path.join(REPORT_DIR, "download_manifest.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "downloaded_at": datetime.now().isoformat(),
            "data_period": DATA_PERIOD,
            "total_files": len(results),
            "success_count": success_count,
            "error_count": error_count,
            "total_rows": total_rows,
            "files": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\nマニフェスト保存: {report_path}")


if __name__ == "__main__":
    main()
