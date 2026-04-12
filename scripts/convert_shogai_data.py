"""
WAM NET 障害福祉サービスCSV → build_site.py 用JSON変換スクリプト

全27種別のCSVを共通ロジックで読み込み、正規化済みJSONを出力する。
Phase 1 は放課後等デイサービス＋児童発達支援。

使い方:
  python scripts/convert_shogai_data.py                          # 全件変換
  python scripts/convert_shogai_data.py --phase1-only             # Phase1(放デイ+児発)のみ
  python scripts/convert_shogai_data.py --input-dir path/to/csvs  # 入力ディレクトリ指定
  python scripts/convert_shogai_data.py --output data/out.json    # 出力パス指定
  python scripts/convert_shogai_data.py --stats-only              # 集計のみ(JSON出力なし)
  python scripts/convert_shogai_data.py --service after_school_day_service  # 特定サービスのみ

出力:
  data/shogaifukushi.json                  — 全件正規化JSON
  data/shogaifukushi_children.json         — Phase1対象のみ (--phase1-only時)
  data/shogaifukushi_service_counts.json   — サービス別件数
  data/shogaifukushi_pref_counts.json      — 都道府県別件数
  data/shogaifukushi_multifunction.json    — 多機能型横断情報
  data/shogaifukushi_build.json            — build_site.py互換フラット形式

データソース: https://www.wam.go.jp/content/wamnet/pcpub/top/sfkopendata/
ライセンス: 営利・非営利問わず利用可能
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

# Windows環境でのUnicode出力対策
sys.stdout.reconfigure(encoding="utf-8")

# === パス設定 ===
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_DIR = BASE_DIR / "data_sources" / "wam_net"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data"

# === サービス種別マッピング ===
# NN番号 → CSV内ファイル名の対応
NN_TO_CSVFILE = {nn: f"csvdownload0{nn:02d}.csv" for nn in [
    11, 12, 13, 14, 15, 21, 22, 32, 33, 41, 42, 45, 46,
    52, 53, 54, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70,
]}

# CSVの生サービス名 → 正規化キー
SERVICE_TYPE_MAP = {
    "放課後等デイサービス":       "after_school_day_service",
    "児童発達支援":             "child_development_support",
    "医療型児童発達支援":         "medical_child_development",
    "居宅訪問型児童発達支援":      "home_visit_child_development",
    "保育所等訪問支援":          "nursery_visit_support",
    "福祉型障害児入所施設":       "welfare_child_residential",
    "医療型障害児入所施設":       "medical_child_residential",
    "障害児相談支援":           "child_consultation_support",
    "就労移行支援":            "employment_transition",
    "就労継続支援Ａ型":          "employment_continuation_a",
    "就労継続支援A型":          "employment_continuation_a",
    "就労継続支援Ｂ型":          "employment_continuation_b",
    "就労継続支援B型":          "employment_continuation_b",
    "就労定着支援":            "employment_retention",
    "共同生活援助":            "group_home",
    "自立生活援助":            "independent_living",
    "生活介護":              "daily_life_care",
    "自立訓練（機能訓練）":       "functional_training",
    "自立訓練（生活訓練）":       "life_training",
    "療養介護":              "medical_long_term_care",
    "施設入所支援":            "residential_support",
    "居宅介護":              "home_care",
    "重度訪問介護":            "severe_home_visit_care",
    "同行援護":              "accompaniment_support",
    "行動援護":              "behavioral_support",
    "重度障害者等包括支援":       "comprehensive_severe_support",
    "計画相談支援":            "plan_consultation",
    "地域相談支援（地域移行支援）":   "community_transition",
    "地域相談支援（地域定着支援）":   "community_settlement",
}

# 正規化キー → サービスグループ
SERVICE_GROUP_MAP = {
    "after_school_day_service":     "children",
    "child_development_support":    "children",
    "medical_child_development":    "children",
    "home_visit_child_development": "children",
    "nursery_visit_support":        "children",
    "welfare_child_residential":    "children",
    "medical_child_residential":    "children",
    "child_consultation_support":   "children",
    "employment_transition":        "employment",
    "employment_continuation_a":    "employment",
    "employment_continuation_b":    "employment",
    "employment_retention":         "employment",
    "group_home":                   "housing",
    "independent_living":           "housing",
    "daily_life_care":              "day_support",
    "functional_training":          "day_support",
    "life_training":                "day_support",
    "medical_long_term_care":       "day_support",
    "residential_support":          "day_support",
    "home_care":                    "home_support",
    "severe_home_visit_care":       "home_support",
    "accompaniment_support":        "home_support",
    "behavioral_support":           "home_support",
    "comprehensive_severe_support": "home_support",
    "plan_consultation":            "consultation",
    "community_transition":         "consultation",
    "community_settlement":         "consultation",
}

# 正規化キー → 日本語表示名
SERVICE_DISPLAY_NAME = {
    "after_school_day_service":     "放課後等デイサービス",
    "child_development_support":    "児童発達支援",
    "medical_child_development":    "医療型児童発達支援",
    "home_visit_child_development": "居宅訪問型児童発達支援",
    "nursery_visit_support":        "保育所等訪問支援",
    "welfare_child_residential":    "福祉型障害児入所施設",
    "medical_child_residential":    "医療型障害児入所施設",
    "child_consultation_support":   "障害児相談支援",
    "employment_transition":        "就労移行支援",
    "employment_continuation_a":    "就労継続支援A型",
    "employment_continuation_b":    "就労継続支援B型",
    "employment_retention":         "就労定着支援",
    "group_home":                   "グループホーム（共同生活援助）",
    "independent_living":           "自立生活援助",
    "daily_life_care":              "生活介護",
    "functional_training":          "自立訓練（機能訓練）",
    "life_training":                "自立訓練（生活訓練）",
    "medical_long_term_care":       "療養介護",
    "residential_support":          "施設入所支援",
    "home_care":                    "居宅介護",
    "severe_home_visit_care":       "重度訪問介護",
    "accompaniment_support":        "同行援護",
    "behavioral_support":           "行動援護",
    "comprehensive_severe_support": "重度障害者等包括支援",
    "plan_consultation":            "計画相談支援",
    "community_transition":         "地域移行支援",
    "community_settlement":         "地域定着支援",
}

# Phase 1 対象
PHASE1_SERVICES = {"after_school_day_service", "child_development_support"}

# 正規化キー → URL slug
SERVICE_SLUG_MAP = {
    "after_school_day_service":     "after-school-day-service",
    "child_development_support":    "child-development-support",
    "medical_child_development":    "medical-child-development",
    "home_visit_child_development": "home-visit-child-development",
    "nursery_visit_support":        "nursery-visit-support",
    "welfare_child_residential":    "welfare-child-residential",
    "medical_child_residential":    "medical-child-residential",
    "child_consultation_support":   "child-consultation-support",
    "employment_transition":        "employment-transition",
    "employment_continuation_a":    "employment-continuation-a",
    "employment_continuation_b":    "employment-continuation-b",
    "employment_retention":         "employment-retention",
    "group_home":                   "group-home",
    "independent_living":           "independent-living",
    "daily_life_care":              "daily-life-care",
    "functional_training":          "functional-training",
    "life_training":                "life-training",
    "medical_long_term_care":       "medical-long-term-care",
    "residential_support":          "residential-support",
    "home_care":                    "home-care",
    "severe_home_visit_care":       "severe-home-visit-care",
    "accompaniment_support":        "accompaniment-support",
    "behavioral_support":           "behavioral-support",
    "comprehensive_severe_support": "comprehensive-severe-support",
    "plan_consultation":            "plan-consultation",
    "community_transition":         "community-transition",
    "community_settlement":         "community-settlement",
}

# === 都道府県マッピング（build_site.py 互換） ===
PREF_CODE_TO_NAME = {
    "01": "北海道", "02": "青森県", "03": "岩手県", "04": "宮城県", "05": "秋田県",
    "06": "山形県", "07": "福島県", "08": "茨城県", "09": "栃木県", "10": "群馬県",
    "11": "埼玉県", "12": "千葉県", "13": "東京都", "14": "神奈川県", "15": "新潟県",
    "16": "富山県", "17": "石川県", "18": "福井県", "19": "山梨県", "20": "長野県",
    "21": "岐阜県", "22": "静岡県", "23": "愛知県", "24": "三重県", "25": "滋賀県",
    "26": "京都府", "27": "大阪府", "28": "兵庫県", "29": "奈良県", "30": "和歌山県",
    "31": "鳥取県", "32": "島根県", "33": "岡山県", "34": "広島県", "35": "山口県",
    "36": "徳島県", "37": "香川県", "38": "愛媛県", "39": "高知県", "40": "福岡県",
    "41": "佐賀県", "42": "長崎県", "43": "熊本県", "44": "大分県", "45": "宮崎県",
    "46": "鹿児島県", "47": "沖縄県",
}

PREF_SLUG = {
    "01": "hokkaido", "02": "aomori", "03": "iwate", "04": "miyagi", "05": "akita",
    "06": "yamagata", "07": "fukushima", "08": "ibaraki", "09": "tochigi", "10": "gunma",
    "11": "saitama", "12": "chiba", "13": "tokyo", "14": "kanagawa", "15": "niigata",
    "16": "toyama", "17": "ishikawa", "18": "fukui", "19": "yamanashi", "20": "nagano",
    "21": "gifu", "22": "shizuoka", "23": "aichi", "24": "mie", "25": "shiga",
    "26": "kyoto", "27": "osaka", "28": "hyogo", "29": "nara", "30": "wakayama",
    "31": "tottori", "32": "shimane", "33": "okayama", "34": "hiroshima", "35": "yamaguchi",
    "36": "tokushima", "37": "kagawa", "38": "ehime", "39": "kochi", "40": "fukuoka",
    "41": "saga", "42": "nagasaki", "43": "kumamoto", "44": "oita", "45": "miyazaki",
    "46": "kagoshima", "47": "okinawa",
}

# === 欠損値判定 ===
MISSING_VALUES = frozenset([
    "", "-", "ー", "−", "—", "―", "なし", "不明", "未設定",
    "N/A", "n/a", "na", "NA", "NULL", "null", "None", "none",
])


def is_missing(val):
    """値が実質的に欠損かどうか判定する。"""
    if val is None:
        return True
    s = str(val).strip()
    return s in MISSING_VALUES


def clean(val):
    """文字列を前後空白除去し、欠損なら None を返す。"""
    if val is None:
        return None
    s = str(val).strip()
    return None if s in MISSING_VALUES else s


# === 正規化関数 ===

# 全角→半角変換テーブル
_ZEN2HAN = str.maketrans(
    "０１２３４５６７８９ー（）　ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ",
    "0123456789-() ABCDEFGHIJKLMNOPQRSTUVWXYZ",
)


def normalize_tel(raw):
    """電話番号を正規化。無効なら None。"""
    if is_missing(raw):
        return None
    tel = str(raw).strip().translate(_ZEN2HAN)
    # 数字とハイフンだけ残す（妥当性判定用）
    digits = re.sub(r"[^\d]", "", tel)
    if len(digits) < 9 or len(digits) > 11:
        return None
    return tel


def normalize_url(raw):
    """URLを正規化。無効なら None。"""
    if is_missing(raw):
        return None
    url = str(raw).strip()
    # メールアドレスを除外
    if "@" in url and "://" not in url:
        return None
    # プロトコルなしの場合は補完
    if url and not url.startswith(("http://", "https://")):
        if "." in url and " " not in url:
            url = "https://" + url
        else:
            return None
    return url if url.startswith(("http://", "https://")) else None


def normalize_latlng(lat_raw, lng_raw):
    """緯度経度をfloat化し、日本国内の妥当性をチェック。"""
    try:
        lat = float(lat_raw)
        lng = float(lng_raw)
    except (ValueError, TypeError):
        return None, None
    # 0座標または範囲外
    if lat == 0.0 or lng == 0.0:
        return None, None
    if not (20.0 <= lat <= 50.0 and 120.0 <= lng <= 155.0):
        return None, None
    return round(lat, 8), round(lng, 8)


def normalize_capacity(raw):
    """定員を整数化。0や空は None。"""
    if is_missing(raw):
        return None
    try:
        cap = int(str(raw).strip().translate(_ZEN2HAN))
        return cap if cap > 0 else None
    except (ValueError, TypeError):
        return None


def normalize_holidays(raw):
    """定休日テキストを曜日リストに分解（ベストエフォート）。"""
    if is_missing(raw):
        return None
    text = str(raw).strip()
    days = []
    for d in ["月", "火", "水", "木", "金", "土", "日", "祝"]:
        if d in text:
            days.append(d)
    return days if days else [text]


def extract_city_name(address_city_field):
    """WAM CSV の「事業所住所（市区町村）」から都道府県名を除去し、市区町村名を抽出。"""
    if is_missing(address_city_field):
        return ""
    addr = str(address_city_field).strip()
    # 先頭の都道府県名を除去
    for pref_name in PREF_CODE_TO_NAME.values():
        if addr.startswith(pref_name):
            return addr[len(pref_name):]
    return addr


def make_city_slug(city_name):
    """市区町村名をslug化（build_site.py互換: 日本語テキストのまま）。"""
    safe = re.sub(r'[:*?"<>|]', "", city_name)
    return safe


# === CSVカラムインデックス（全27CSV共通・29列） ===
COL_CITY_CODE       = 0   # 都道府県コード又は市区町村コード
COL_NO              = 1   # NO（システム連番）
COL_DESIGNATOR      = 2   # 指定機関名
COL_CORP_NAME       = 3   # 法人の名称
COL_CORP_NAME_KANA  = 4   # 法人の名称_かな
COL_CORP_NUMBER     = 5   # 法人番号
COL_CORP_CITY       = 6   # 法人住所（市区町村）
COL_CORP_ADDR       = 7   # 法人住所（番地以降）
COL_CORP_TEL        = 8   # 法人電話番号
COL_CORP_FAX        = 9   # 法人FAX番号
COL_CORP_URL        = 10  # 法人URL
COL_SERVICE_TYPE    = 11  # サービス種別
COL_OFFICE_NAME     = 12  # 事業所の名称
COL_OFFICE_KANA     = 13  # 事業所の名称_かな
COL_OFFICE_NUMBER   = 14  # 事業所番号
COL_OFFICE_CITY     = 15  # 事業所住所（市区町村）
COL_OFFICE_ADDR     = 16  # 事業所住所（番地以降）
COL_OFFICE_TEL      = 17  # 事業所電話番号
COL_OFFICE_FAX      = 18  # 事業所FAX番号
COL_OFFICE_URL      = 19  # 事業所URL
COL_LAT             = 20  # 事業所緯度
COL_LNG             = 21  # 事業所経度
COL_HOURS_WEEKDAY   = 22  # 利用可能な時間帯（平日）
COL_HOURS_SATURDAY  = 23  # 利用可能な時間帯（土曜）
COL_HOURS_SUNDAY    = 24  # 利用可能な時間帯（日曜）
COL_HOURS_HOLIDAY   = 25  # 利用可能な時間帯（祝日）
COL_CLOSED_DAYS     = 26  # 定休日
COL_HOURS_NOTE      = 27  # 利用可能曜日特記事項（留意事項）
COL_CAPACITY        = 28  # 定員


def convert_row(row, csv_filename):
    """WAM CSV 1行を正規化レコードに変換する。"""
    # 列数チェック
    if len(row) < 29:
        return None

    # サービス種別の正規化
    service_type_raw = clean(row[COL_SERVICE_TYPE]) or ""
    service_type = SERVICE_TYPE_MAP.get(service_type_raw)
    if not service_type:
        # 全角→半角にしてリトライ
        normalized_raw = service_type_raw.translate(_ZEN2HAN)
        service_type = SERVICE_TYPE_MAP.get(normalized_raw)
    if not service_type:
        return None  # 未知のサービス種別はスキップ

    service_group = SERVICE_GROUP_MAP.get(service_type, "unknown")
    display_name = SERVICE_DISPLAY_NAME.get(service_type, service_type_raw)

    # 事業所番号
    office_number = clean(row[COL_OFFICE_NUMBER]) or ""
    if not office_number:
        return None  # 事業所番号なしはスキップ

    # ID生成
    record_id = f"wam:{service_type}:{office_number}"

    # 都道府県
    city_code_raw = clean(row[COL_CITY_CODE]) or ""
    pref_code = city_code_raw[:2] if len(city_code_raw) >= 2 else ""
    pref_name = PREF_CODE_TO_NAME.get(pref_code, "")

    # 住所
    office_city = clean(row[COL_OFFICE_CITY]) or ""
    office_addr_detail = clean(row[COL_OFFICE_ADDR]) or ""
    full_address = f"{office_city}{office_addr_detail}"
    city_name = extract_city_name(office_city)

    # 緯度経度
    lat, lng = normalize_latlng(row[COL_LAT], row[COL_LNG])

    # slug生成
    pref_slug = PREF_SLUG.get(pref_code, pref_code)
    city_slug = make_city_slug(city_name) if city_name else ""
    service_slug = SERVICE_SLUG_MAP.get(service_type, service_type)
    canonical_slug = f"{pref_slug}/{city_slug}/{service_slug}/{office_number}"

    return {
        "id": record_id,
        "source": {
            "system": "wam_shogaifukushi",
            "file_name": csv_filename,
            "snapshot_date": None,
            "retrieved_at": str(date.today()),
        },
        "provider": {
            "name": clean(row[COL_CORP_NAME]),
            "name_kana": clean(row[COL_CORP_NAME_KANA]),
            "corporate_number": clean(row[COL_CORP_NUMBER]),
            "address": f"{clean(row[COL_CORP_CITY]) or ''}{clean(row[COL_CORP_ADDR]) or ''}".strip() or None,
            "tel": normalize_tel(row[COL_CORP_TEL]),
            "fax": normalize_tel(row[COL_CORP_FAX]),
            "url": normalize_url(row[COL_CORP_URL]),
        },
        "office": {
            "name": clean(row[COL_OFFICE_NAME]),
            "name_kana": clean(row[COL_OFFICE_KANA]),
            "office_number": office_number,
            "pref_code": pref_code,
            "pref_name": pref_name,
            "city_code": city_code_raw,
            "city_name": city_name,
            "address": full_address,
            "tel": normalize_tel(row[COL_OFFICE_TEL]),
            "fax": normalize_tel(row[COL_OFFICE_FAX]),
            "url": normalize_url(row[COL_OFFICE_URL]),
            "lat": lat,
            "lng": lng,
        },
        "service": {
            "service_type_raw": service_type_raw,
            "service_type": service_type,
            "service_group": service_group,
            "display_name": display_name,
            "capacity": normalize_capacity(row[COL_CAPACITY]),
        },
        "availability": {
            "weekday_hours": clean(row[COL_HOURS_WEEKDAY]),
            "saturday_hours": clean(row[COL_HOURS_SATURDAY]),
            "sunday_hours": clean(row[COL_HOURS_SUNDAY]),
            "holiday_hours": clean(row[COL_HOURS_HOLIDAY]),
            "regular_holidays": normalize_holidays(row[COL_CLOSED_DAYS]),
            "notes": clean(row[COL_HOURS_NOTE]),
        },
        "relationships": {
            "has_multi_function": False,  # 後段で付与
            "coexisting_service_types": [],
            "coexisting_service_display_names": [],
        },
        "meta": {
            "canonical_slug": canonical_slug,
            "is_phase1_target": service_type in PHASE1_SERVICES,
            "status": "active",
        },
    }


def to_build_site_format(rec):
    """正規化レコードを build_site.py 互換フラットJSONに変換する。

    build_site.py が期待するフィールド:
      kikan_cd, name, address, pref, pref_code, tel, url, lat, lng,
      kikan_kbn, business_status, corporation_name, source, ...
    """
    svc = rec["service"]
    ofc = rec["office"]
    service_slug = SERVICE_SLUG_MAP.get(svc["service_type"], svc["service_type"])

    # kikan_cd: 多機能型で同一office_numberが複数サービスに出現するため、
    # service_slugを付加して一意にする
    kikan_cd = f"{ofc['office_number']}-{service_slug}"

    return {
        "kikan_cd": kikan_cd,
        "name": ofc["name"] or "",
        "address": ofc["address"] or "",
        "postal": "",
        "tel": ofc["tel"] or "",
        "fax": ofc.get("fax") or "",
        "url": ofc["url"] or "",
        "pref": ofc["pref_name"] or "",
        "pref_code": ofc["pref_code"] or "",
        "lat": ofc["lat"],
        "lng": ofc["lng"],
        "kikan_kbn": "2",  # build_site.pyはkikan_kbn='2'のみ処理する
        "business_status": "OPERATIONAL",
        "specialties": [svc["display_name"]],
        "emergency": {},
        "rating": None,
        "review_count": None,
        "photo_url": "",
        "image_url": "",
        "place_id": "",
        "corporation_name": rec["provider"]["name"] or "",
        "source": "wam_shogai_opendata",
        # 障害福祉拡張フィールド
        "service_type": svc["service_type"],
        "service_type_raw": svc["service_type_raw"],
        "service_group": svc["service_group"],
        "service_display_name": svc["display_name"],
        "capacity": svc["capacity"],
        "hours_weekday": rec["availability"]["weekday_hours"],
        "hours_saturday": rec["availability"]["saturday_hours"],
        "closed_days": rec["availability"]["regular_holidays"],
        "multi_function": rec["relationships"]["has_multi_function"],
        "coexisting_services": rec["relationships"]["coexisting_service_display_names"],
    }


def load_all_csvs(input_dir, service_filter=None):
    """全CSVを読み込んで正規化レコードのリストを返す。"""
    input_dir = Path(input_dir)
    all_records = []
    file_stats = {}  # csv_filename -> {"total": N, "converted": M, "errors": E}

    for nn, csv_filename in sorted(NN_TO_CSVFILE.items()):
        csv_path = input_dir / csv_filename
        if not csv_path.exists():
            print(f"  [WARN] ファイルなし: {csv_path}")
            continue

        converted = 0
        errors = 0
        total = 0

        try:
            with open(csv_path, encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    print(f"  [WARN] ヘッダーなし: {csv_filename}")
                    continue

                for row_num, row in enumerate(reader, start=2):
                    total += 1
                    try:
                        rec = convert_row(row, csv_filename)
                        if rec is None:
                            errors += 1
                            continue

                        # サービスフィルタ
                        if service_filter and rec["service"]["service_type"] not in service_filter:
                            continue

                        all_records.append(rec)
                        converted += 1
                    except Exception as e:
                        errors += 1
                        if errors <= 3:
                            print(f"  [ERROR] {csv_filename} 行{row_num}: {e}")

        except Exception as e:
            print(f"  [ERROR] ファイル読込失敗 {csv_filename}: {e}")
            continue

        file_stats[csv_filename] = {
            "nn": nn,
            "total": total,
            "converted": converted,
            "errors": errors,
        }
        print(f"  [{nn:02d}] {csv_filename}: {total:>7,} 行 -> {converted:>7,} 件変換 ({errors} エラー)")

    return all_records, file_stats


def attach_multifunction_info(records):
    """多機能型情報を付与する（全件読込後の二段階処理）。

    同一office_numberに複数service_typeが紐づく場合、
    各レコードにcoexisting情報を付与する。
    """
    # office_number -> set of (service_type, display_name)
    office_services = defaultdict(set)
    for rec in records:
        on = rec["office"]["office_number"]
        st = rec["service"]["service_type"]
        dn = rec["service"]["display_name"]
        office_services[on].add((st, dn))

    multi_count = 0
    for rec in records:
        on = rec["office"]["office_number"]
        services = office_services[on]
        if len(services) > 1:
            current_st = rec["service"]["service_type"]
            coexisting = [(st, dn) for st, dn in services if st != current_st]
            rec["relationships"]["has_multi_function"] = True
            rec["relationships"]["coexisting_service_types"] = sorted(st for st, dn in coexisting)
            rec["relationships"]["coexisting_service_display_names"] = sorted(dn for st, dn in coexisting)
            multi_count += 1

    # 多機能型の事業所数（ユニーク）
    multi_offices = sum(1 for on, svcs in office_services.items() if len(svcs) > 1)
    return multi_count, multi_offices, office_services


def generate_stats(records, file_stats, multi_count, multi_offices):
    """集計情報を生成する。"""

    # サービス別件数
    service_counts = Counter(rec["service"]["service_type"] for rec in records)
    service_counts_detail = {}
    for svc_type, count in sorted(service_counts.items(), key=lambda x: -x[1]):
        service_counts_detail[svc_type] = {
            "count": count,
            "display_name": SERVICE_DISPLAY_NAME.get(svc_type, svc_type),
            "service_group": SERVICE_GROUP_MAP.get(svc_type, "unknown"),
            "is_phase1": svc_type in PHASE1_SERVICES,
        }

    # 都道府県別件数
    pref_counts = Counter(rec["office"]["pref_code"] for rec in records)
    pref_counts_detail = {}
    for pc in sorted(pref_counts.keys()):
        pref_counts_detail[pc] = {
            "pref_name": PREF_CODE_TO_NAME.get(pc, "不明"),
            "count": pref_counts[pc],
        }

    # Phase 1件数
    phase1_records = [r for r in records if r["meta"]["is_phase1_target"]]
    phase1_count = len(phase1_records)
    phase1_pref = Counter(r["office"]["pref_code"] for r in phase1_records)

    # ユニーク事業所番号
    unique_offices = len(set(r["office"]["office_number"] for r in records))

    return {
        "total_records": len(records),
        "unique_office_numbers": unique_offices,
        "multi_function_records": multi_count,
        "multi_function_offices": multi_offices,
        "phase1_records": phase1_count,
        "service_counts": service_counts_detail,
        "pref_counts": pref_counts_detail,
        "phase1_pref_counts": {
            pc: {"pref_name": PREF_CODE_TO_NAME.get(pc, ""), "count": c}
            for pc, c in sorted(phase1_pref.items())
        },
        "file_stats": file_stats,
    }


def main():
    parser = argparse.ArgumentParser(
        description="WAM NET 障害福祉サービスCSV → 正規化JSON変換"
    )
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR),
                        help="CSVファイルのディレクトリ")
    parser.add_argument("--output", default=None,
                        help="メイン出力JSONパス")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR),
                        help="出力ディレクトリ")
    parser.add_argument("--phase1-only", action="store_true",
                        help="Phase1対象（放デイ+児発）のみ出力")
    parser.add_argument("--stats-only", action="store_true",
                        help="集計のみ出力（JSONファイルは生成しない）")
    parser.add_argument("--service", default=None,
                        help="特定サービスのみ (例: after_school_day_service)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # サービスフィルタ
    service_filter = None
    if args.phase1_only:
        service_filter = PHASE1_SERVICES
        print("Phase 1 モード: 放課後等デイサービス + 児童発達支援 のみ")
    elif args.service:
        service_filter = {args.service}
        print(f"サービスフィルタ: {args.service}")

    print("=" * 70)
    print("  WAM NET 障害福祉サービス CSV -> JSON 変換")
    print("=" * 70)
    print(f"  入力: {args.input_dir}")
    print(f"  出力: {output_dir}")
    print()

    # === Step 1: 全CSV読み込み・正規化 ===
    records, file_stats = load_all_csvs(args.input_dir, service_filter)
    print(f"\n変換完了: {len(records):,} 件")

    if not records:
        print("[ERROR] 変換レコードが0件です。入力ディレクトリとCSVを確認してください。")
        sys.exit(1)

    # === Step 2: 多機能型検出 ===
    multi_count, multi_offices, office_services = attach_multifunction_info(records)
    print(f"多機能型: {multi_count:,} レコード / {multi_offices:,} 事業所")

    # === Step 3: 集計 ===
    stats = generate_stats(records, file_stats, multi_count, multi_offices)

    # コンソール出力
    print(f"\n--- サービス別件数 ---")
    for svc_type, info in sorted(stats["service_counts"].items(), key=lambda x: -x[1]["count"]):
        phase_mark = " *P1*" if info["is_phase1"] else ""
        print(f"  {info['display_name']:<30} {info['count']:>8,}{phase_mark}")

    print(f"\n--- 都道府県別件数（上位10） ---")
    sorted_prefs = sorted(stats["pref_counts"].items(), key=lambda x: -x[1]["count"])
    for pc, info in sorted_prefs[:10]:
        print(f"  {pc} {info['pref_name']:<8} {info['count']:>8,}")
    print(f"  ... 合計 {len(stats['pref_counts'])} 都道府県")

    print(f"\n--- Phase 1 サマリー ---")
    print(f"  Phase 1 総件数: {stats['phase1_records']:,}")
    print(f"  ユニーク事業所番号: {stats['unique_office_numbers']:,}")
    print(f"  多機能型事業所: {multi_offices:,}")

    if args.stats_only:
        print("\n(--stats-only: JSON出力スキップ)")
    else:
        # === Step 4: JSON出力 ===

        # 4a: 全件正規化JSON
        main_output = Path(args.output) if args.output else output_dir / "shogaifukushi.json"
        main_output.parent.mkdir(parents=True, exist_ok=True)
        with open(main_output, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=1)
        print(f"\n出力: {len(records):,} 件 -> {main_output}")

        # 4b: Phase 1 のみ
        phase1 = [r for r in records if r["meta"]["is_phase1_target"]]
        if phase1:
            p1_path = output_dir / "shogaifukushi_children.json"
            with open(p1_path, "w", encoding="utf-8") as f:
                json.dump(phase1, f, ensure_ascii=False, indent=1)
            print(f"Phase 1: {len(phase1):,} 件 -> {p1_path}")

        # 4c: build_site.py 互換フラットJSON
        build_records = [to_build_site_format(r) for r in phase1 or records]
        build_path = output_dir / "shogaifukushi_build.json"
        with open(build_path, "w", encoding="utf-8") as f:
            json.dump(build_records, f, ensure_ascii=False, indent=1)
        print(f"build_site互換: {len(build_records):,} 件 -> {build_path}")

        # 4d: 多機能型横断情報
        multi_index = {}
        for on, svcs in office_services.items():
            if len(svcs) > 1:
                multi_index[on] = {
                    "service_types": sorted(st for st, dn in svcs),
                    "display_names": sorted(dn for st, dn in svcs),
                }
        multi_path = output_dir / "shogaifukushi_multifunction.json"
        with open(multi_path, "w", encoding="utf-8") as f:
            json.dump(multi_index, f, ensure_ascii=False, indent=1)
        print(f"多機能型: {len(multi_index):,} 事業所 -> {multi_path}")

    # === Step 5: 集計ファイル出力（常に出力） ===
    svc_counts_path = output_dir / "shogaifukushi_service_counts.json"
    with open(svc_counts_path, "w", encoding="utf-8") as f:
        json.dump(stats["service_counts"], f, ensure_ascii=False, indent=2)
    print(f"サービス別集計: {svc_counts_path}")

    pref_counts_path = output_dir / "shogaifukushi_pref_counts.json"
    with open(pref_counts_path, "w", encoding="utf-8") as f:
        json.dump(stats["pref_counts"], f, ensure_ascii=False, indent=2)
    print(f"都道府県別集計: {pref_counts_path}")

    # 全統計
    all_stats_path = output_dir / "shogaifukushi_stats.json"
    with open(all_stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"全統計: {all_stats_path}")

    print("\n" + "=" * 70)
    print("  変換完了")
    print("=" * 70)


if __name__ == "__main__":
    main()
