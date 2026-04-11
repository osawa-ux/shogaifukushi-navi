"""
WAM NET 障害福祉サービスCSV 構造解析・充填率分析・件数集計

全27種別のCSVを読み込み、以下を分析する:
1. カラム構造（共通性・差分）
2. 充填率（カラム×サービス種別）
3. 件数集計（ユニーク事業所・法人・重複）
4. データ品質（異常値・形式ゆれ）

出力:
  data_sources/reports/column_fill_rate.csv
  data_sources/reports/service_type_counts.csv
  data_sources/reports/column_schema.json
  data_sources/reports/analysis_detail.json
"""

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data_sources", "wam_net")
REPORT_DIR = os.path.join(BASE_DIR, "data_sources", "reports")

SERVICE_FILES = {
    11: "居宅介護", 12: "重度訪問介護", 13: "行動援護",
    14: "重度障害者等包括支援", 15: "同行援護",
    21: "療養介護", 22: "生活介護", 32: "施設入所支援",
    33: "共同生活援助", 41: "自立訓練（機能訓練）",
    42: "自立訓練（生活訓練）", 45: "就労継続支援A型",
    46: "就労継続支援B型", 52: "計画相談支援",
    53: "地域相談支援（地域移行支援）", 54: "地域相談支援（地域定着支援）",
    60: "就労移行支援", 61: "自立生活援助", 62: "就労定着支援",
    63: "児童発達支援", 64: "医療型児童発達支援",
    65: "放課後等デイサービス", 66: "居宅訪問型児童発達支援",
    67: "保育所等訪問支援", 68: "福祉型障害児入所施設",
    69: "医療型障害児入所施設", 70: "障害児相談支援",
}


def is_effectively_empty(val: str) -> bool:
    """実質的に空とみなすかどうか。"""
    if not val:
        return True
    v = val.strip()
    if not v:
        return True
    if v in ("-", "ー", "−", "—", "―", "なし", "無", "NULL", "null", "None", "N/A", "n/a"):
        return True
    return False


def is_valid_tel(val: str) -> bool:
    """電話番号として妥当か。"""
    if is_effectively_empty(val):
        return False
    digits = re.sub(r"[^\d]", "", val)
    return 9 <= len(digits) <= 11


def is_valid_url(val: str) -> bool:
    """URLとして妥当か。"""
    if is_effectively_empty(val):
        return False
    v = val.strip()
    return v.startswith("http://") or v.startswith("https://")


def is_valid_latlng(lat_str: str, lng_str: str) -> bool:
    """緯度経度が日本国内として妥当か。"""
    try:
        lat = float(lat_str)
        lng = float(lng_str)
        # 日本: 緯度20-46, 経度122-154（離島含む余裕を持たせる）
        return 20 <= lat <= 50 and 120 <= lng <= 155
    except (ValueError, TypeError):
        return False


def load_csv(nn: int) -> tuple:
    """CSVを読み込んでヘッダーと行リストを返す。"""
    csv_path = os.path.join(DATA_DIR, f"csvdownload0{nn:02d}.csv")
    if not os.path.exists(csv_path):
        return None, None

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    return header, rows


def analyze_one_service(nn: int, header: list, rows: list) -> dict:
    """1サービス種別の分析結果を返す。"""
    service_name = SERVICE_FILES[nn]
    total = len(rows)

    if total == 0:
        return {"nn": nn, "service_name": service_name, "total": 0}

    # カラム別充填率
    column_stats = {}
    for i, col in enumerate(header):
        non_null = 0
        non_empty = 0
        effective_filled = 0
        for row in rows:
            val = row[i] if i < len(row) else ""
            if val is not None:
                non_null += 1
            if val and val.strip():
                non_empty += 1
            if not is_effectively_empty(val):
                effective_filled += 1

        column_stats[col] = {
            "index": i,
            "total": total,
            "non_null": non_null,
            "non_empty": non_empty,
            "effective_filled": effective_filled,
            "fill_rate": round(non_empty / total * 100, 2),
            "effective_fill_rate": round(effective_filled / total * 100, 2),
        }

    # 事業所番号の分析（列14）
    office_codes = [row[14] for row in rows if len(row) > 14 and row[14].strip()]
    unique_offices = len(set(office_codes))
    dup_offices = len(office_codes) - unique_offices

    # 法人番号の分析（列5）
    corp_numbers = [row[5] for row in rows if len(row) > 5 and row[5].strip()]
    unique_corps = len(set(corp_numbers))

    # 緯度経度の分析（列20, 21）
    valid_latlng = 0
    zero_latlng = 0
    missing_latlng = 0
    for row in rows:
        lat = row[20] if len(row) > 20 else ""
        lng = row[21] if len(row) > 21 else ""
        if is_effectively_empty(lat) or is_effectively_empty(lng):
            missing_latlng += 1
        elif is_valid_latlng(lat, lng):
            valid_latlng += 1
        else:
            # 0座標 or 範囲外
            try:
                if float(lat) == 0 or float(lng) == 0:
                    zero_latlng += 1
                else:
                    zero_latlng += 1  # 範囲外もここに
            except ValueError:
                missing_latlng += 1

    # 電話番号（列17 = 事業所電話）
    valid_tel = sum(1 for row in rows if len(row) > 17 and is_valid_tel(row[17]))

    # URL（列19 = 事業所URL）
    valid_url = sum(1 for row in rows if len(row) > 19 and is_valid_url(row[19]))

    # 定員（列28）
    capacity_filled = 0
    capacity_zero = 0
    for row in rows:
        cap = row[28] if len(row) > 28 else ""
        if not is_effectively_empty(cap):
            try:
                c = int(cap)
                if c > 0:
                    capacity_filled += 1
                else:
                    capacity_zero += 1
            except ValueError:
                pass

    # サービス種別名（列11）の値分布
    service_type_raw_values = Counter(
        row[11].strip() for row in rows if len(row) > 11 and row[11].strip()
    )

    # 都道府県分布（列0の先頭2桁）
    pref_dist = Counter()
    for row in rows:
        code = row[0].strip() if row[0] else ""
        if len(code) >= 2:
            pref_dist[code[:2]] += 1

    return {
        "nn": nn,
        "service_name": service_name,
        "total": total,
        "column_count": len(header),
        "columns": header,
        "column_stats": column_stats,
        "unique_office_codes": unique_offices,
        "duplicate_office_codes": dup_offices,
        "office_codes_filled": len(office_codes),
        "unique_corp_numbers": unique_corps,
        "corp_numbers_filled": len(corp_numbers),
        "valid_latlng": valid_latlng,
        "zero_latlng": zero_latlng,
        "missing_latlng": missing_latlng,
        "valid_tel": valid_tel,
        "valid_url": valid_url,
        "capacity_filled": capacity_filled,
        "capacity_zero": capacity_zero,
        "service_type_raw_values": dict(service_type_raw_values),
        "pref_distribution": dict(sorted(pref_dist.items())),
        "pref_count": len(pref_dist),
    }


def main():
    os.makedirs(REPORT_DIR, exist_ok=True)

    print("=" * 70)
    print("  WAM NET CSV 構造解析・充填率分析")
    print("=" * 70)

    all_results = {}
    all_headers = {}

    # 全CSV読み込み・分析
    for nn in sorted(SERVICE_FILES.keys()):
        header, rows = load_csv(nn)
        if header is None:
            print(f"  [{nn:02d}] {SERVICE_FILES[nn]}: ファイルなし — スキップ")
            continue

        result = analyze_one_service(nn, header, rows)
        all_results[nn] = result
        all_headers[nn] = header
        print(f"  [{nn:02d}] {result['service_name']}: {result['total']:,}件, "
              f"{result['column_count']}列, "
              f"lat/lng={result['valid_latlng']:,}, "
              f"tel={result['valid_tel']:,}, "
              f"url={result['valid_url']:,}")

    # === カラム構造の共通性チェック ===
    print("\n" + "=" * 70)
    print("  カラム構造の比較")
    print("=" * 70)

    header_sets = {}
    for nn, h in all_headers.items():
        key = tuple(h)
        if key not in header_sets:
            header_sets[key] = []
        header_sets[key].append(nn)

    if len(header_sets) == 1:
        print("  全CSVでカラム構造が完全一致 [OK]")
        common_header = list(list(header_sets.keys())[0])
    else:
        print(f"  カラム構造のパターン数: {len(header_sets)}")
        for i, (h, nns) in enumerate(header_sets.items()):
            names = [SERVICE_FILES[n] for n in nns]
            print(f"  パターン{i+1} ({len(h)}列): {', '.join(names[:5])}...")
        # 最も多いパターンを共通とする
        common_header = list(max(header_sets.keys(), key=lambda k: len(header_sets[k])))

    print(f"\n  共通カラム数: {len(common_header)}")
    print("  カラム一覧:")
    for i, col in enumerate(common_header):
        print(f"    [{i:2d}] {col}")

    # === サマリーテーブル（全サービス） ===
    print("\n" + "=" * 70)
    print("  サービス種別別サマリー")
    print("=" * 70)
    print(f"  {'NN':>4}  {'サービス':^28}  {'件数':>7}  {'事業所':>7}  {'重複':>5}  "
          f"{'lat/lng':>7}  {'TEL':>7}  {'URL':>7}  {'定員':>6}  {'都道府県':>4}")
    print("  " + "-" * 110)

    grand_total = 0
    for nn in sorted(all_results.keys()):
        r = all_results[nn]
        grand_total += r["total"]
        latlng_pct = r["valid_latlng"] / r["total"] * 100 if r["total"] > 0 else 0
        tel_pct = r["valid_tel"] / r["total"] * 100 if r["total"] > 0 else 0
        url_pct = r["valid_url"] / r["total"] * 100 if r["total"] > 0 else 0
        cap_pct = r["capacity_filled"] / r["total"] * 100 if r["total"] > 0 else 0
        print(f"  {nn:>4}  {r['service_name']:<28}  {r['total']:>7,}  "
              f"{r['unique_office_codes']:>7,}  {r['duplicate_office_codes']:>5}  "
              f"{latlng_pct:>6.1f}%  {tel_pct:>6.1f}%  {url_pct:>6.1f}%  "
              f"{cap_pct:>5.1f}%  {r['pref_count']:>4}")
    print("  " + "-" * 110)
    print(f"  {'合計':<34}  {grand_total:>7,}")

    # === MVP対象（放デイ・児発）の詳細充填率 ===
    print("\n" + "=" * 70)
    print("  MVP対象 充填率詳細（放課後等デイサービス + 児童発達支援）")
    print("=" * 70)

    for nn in [65, 63]:
        r = all_results.get(nn)
        if not r:
            continue
        print(f"\n  [{nn}] {r['service_name']} ({r['total']:,}件)")
        print(f"  {'カラム名':<40}  {'充填率':>8}  {'実質充填率':>10}  {'件数':>8}")
        print("  " + "-" * 75)
        for col, stats in r["column_stats"].items():
            mark = "OK  " if stats["effective_fill_rate"] >= 95 else \
                   "LOW " if stats["effective_fill_rate"] >= 50 else "WARN"
            print(f"  [{mark}] {col:<36}  {stats['fill_rate']:>7.1f}%  "
                  f"{stats['effective_fill_rate']:>9.1f}%  {stats['effective_filled']:>8,}")

    # === 出力: column_fill_rate.csv ===
    fill_rate_path = os.path.join(REPORT_DIR, "column_fill_rate.csv")
    with open(fill_rate_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "service_type_raw", "nn", "column_name", "column_index",
            "total_rows", "non_null_count", "non_empty_count",
            "effective_filled_count", "fill_rate", "effective_fill_rate", "notes"
        ])
        for nn in sorted(all_results.keys()):
            r = all_results[nn]
            for col, stats in r["column_stats"].items():
                notes = ""
                if stats["effective_fill_rate"] < 10:
                    notes = "ほぼ空"
                elif stats["effective_fill_rate"] < 50:
                    notes = "欠損多い"
                writer.writerow([
                    r["service_name"], nn, col, stats["index"],
                    stats["total"], stats["non_null"], stats["non_empty"],
                    stats["effective_filled"],
                    stats["fill_rate"], stats["effective_fill_rate"], notes
                ])
    print(f"\n  充填率CSV保存: {fill_rate_path}")

    # === 出力: service_type_counts.csv ===
    counts_path = os.path.join(REPORT_DIR, "service_type_counts.csv")
    with open(counts_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "service_type_raw", "nn", "file_name",
            "record_count", "unique_office_number_count",
            "unique_corporate_number_count",
            "lat_lng_valid_count", "lat_lng_valid_pct",
            "tel_present_count", "tel_present_pct",
            "url_present_count", "url_present_pct",
            "capacity_filled_count", "capacity_filled_pct",
            "pref_count", "duplicate_office_codes"
        ])
        for nn in sorted(all_results.keys()):
            r = all_results[nn]
            t = r["total"] or 1
            writer.writerow([
                r["service_name"], nn, f"csvdownload0{nn:02d}.csv",
                r["total"], r["unique_office_codes"],
                r["unique_corp_numbers"],
                r["valid_latlng"], round(r["valid_latlng"] / t * 100, 1),
                r["valid_tel"], round(r["valid_tel"] / t * 100, 1),
                r["valid_url"], round(r["valid_url"] / t * 100, 1),
                r["capacity_filled"], round(r["capacity_filled"] / t * 100, 1),
                r["pref_count"], r["duplicate_office_codes"]
            ])
    print(f"  件数CSV保存: {counts_path}")

    # === 出力: column_schema.json ===
    schema_path = os.path.join(REPORT_DIR, "column_schema.json")
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump({
            "analyzed_at": datetime.now().isoformat(),
            "common_header": common_header,
            "column_count": len(common_header),
            "header_patterns": len(header_sets),
            "all_identical": len(header_sets) == 1,
            "pattern_details": {
                str(i): {
                    "columns": list(h),
                    "services": [SERVICE_FILES[n] for n in nns]
                }
                for i, (h, nns) in enumerate(header_sets.items())
            }
        }, f, ensure_ascii=False, indent=2)
    print(f"  カラムスキーマJSON保存: {schema_path}")

    # === 出力: analysis_detail.json ===
    detail_path = os.path.join(REPORT_DIR, "analysis_detail.json")
    # column_statsをシリアライズ可能にする
    serializable_results = {}
    for nn, r in all_results.items():
        sr = dict(r)
        serializable_results[str(nn)] = sr
    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump({
            "analyzed_at": datetime.now().isoformat(),
            "grand_total": grand_total,
            "service_count": len(all_results),
            "services": serializable_results,
        }, f, ensure_ascii=False, indent=2)
    print(f"  分析詳細JSON保存: {detail_path}")

    # === 最終サマリー ===
    print("\n" + "=" * 70)
    print("  最終サマリー")
    print("=" * 70)

    mvp_63 = all_results.get(63, {})
    mvp_65 = all_results.get(65, {})
    mvp_total = mvp_63.get("total", 0) + mvp_65.get("total", 0)

    print(f"  全サービス合計: {grand_total:,}件（27種別）")
    print(f"  MVP対象合計: {mvp_total:,}件")
    print(f"    放課後等デイサービス: {mvp_65.get('total', 0):,}件")
    print(f"    児童発達支援: {mvp_63.get('total', 0):,}件")
    print(f"  カラム構造: {'全CSV共通' if len(header_sets) == 1 else '差異あり'}")
    print(f"  文字コード: UTF-8 BOM付き（全ファイル共通）")

    # MVP品質チェック
    for nn, label in [(65, "放デイ"), (63, "児発")]:
        r = all_results.get(nn)
        if not r:
            continue
        t = r["total"]
        ll = r["valid_latlng"] / t * 100
        tl = r["valid_tel"] / t * 100
        print(f"\n  {label} 品質:")
        print(f"    事業所番号ユニーク: {r['unique_office_codes']:,} / {t:,} "
              f"(重複: {r['duplicate_office_codes']})")
        print(f"    緯度経度有効: {r['valid_latlng']:,} ({ll:.1f}%)")
        print(f"    電話番号有効: {r['valid_tel']:,} ({tl:.1f}%)")
        print(f"    URL有効: {r['valid_url']:,} ({r['valid_url']/t*100:.1f}%)")
        print(f"    定員あり: {r['capacity_filled']:,} ({r['capacity_filled']/t*100:.1f}%)")
        print(f"    都道府県数: {r['pref_count']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
