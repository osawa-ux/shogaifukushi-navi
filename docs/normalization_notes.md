# 正規化方針・実装ノート

分析日: 2026-04-12

---

## 1. 主キー設計

### 結論: `office_code` + `service_type` の複合キー

- `office_code`（事業所番号、10桁）は同一サービス種別内でほぼユニーク
- ただし以下のケースで重複が発生:
  - 同一事業所番号で複数拠点（放デイ: 175件の重複 = 約0.7%）
  - 放デイと児発の多機能型（12,793件の共通事業所番号）
- **ページ生成の単位**: `office_code:service_type` の複合キー → 1ページ
- **slug例**: `/office/1450000001-houkago-day.html`

### 同一事業所番号で複数レコードがある場合

原因: 同一法人が同じ事業所番号で複数施設を運営（事業所名末尾に枝番）
例: 「ハッピークローバー5」「ハッピークローバー6」→ 事業所番号が同じ

**対策:**
- `office_code + name` のハッシュを付加して一意化
- 例: `0150102242-a1b2c3.html`（MD5の先頭6桁）
- または行番号（NO列）を補助キーに使用

---

## 2. service_type の正規化

### CSV上の生値（列11）

各CSVで `サービス種別` の値は完全に統一されている（表記ゆれなし）:
- `放課後等デイサービス`
- `児童発達支援`
- `就労継続支援Ｂ型`（全角Ｂ）
- `就労継続支援Ａ型`（全角Ａ）

### 正規化ルール

```python
SERVICE_TYPE_NORMALIZE = {
    "放課後等デイサービス": "放課後等デイサービス",  # そのまま
    "児童発達支援": "児童発達支援",
    "就労継続支援Ａ型": "就労継続支援A型",  # 全角→半角
    "就労継続支援Ｂ型": "就労継続支援B型",
    # 他のサービスはそのまま使用可能
}
```

- 全角英数字 → 半角に統一（A型/B型のみ）
- 括弧内の表記: `（機能訓練）` `（生活訓練）` → そのまま使用（全角括弧で統一されている）

---

## 3. service_group への束ね方

```python
SERVICE_GROUP_MAP = {
    "放課後等デイサービス": "kodomo",
    "児童発達支援": "kodomo",
    "医療型児童発達支援": "kodomo",
    "居宅訪問型児童発達支援": "kodomo",
    "保育所等訪問支援": "kodomo",
    "福祉型障害児入所施設": "kodomo",
    "医療型障害児入所施設": "kodomo",
    "障害児相談支援": "kodomo",
    "就労移行支援": "shuro",
    "就労継続支援A型": "shuro",
    "就労継続支援B型": "shuro",
    "就労定着支援": "shuro",
    "共同生活援助": "sumai",
    "自立生活援助": "sumai",
    "生活介護": "nicchu",
    "自立訓練（機能訓練）": "nicchu",
    "自立訓練（生活訓練）": "nicchu",
    "療養介護": "nicchu",
    "施設入所支援": "nicchu",
    "居宅介護": "zaitaku",
    "重度訪問介護": "zaitaku",
    "同行援護": "zaitaku",
    "行動援護": "zaitaku",
    "重度障害者等包括支援": "zaitaku",
    "計画相談支援": "soudan",
    "地域相談支援（地域移行支援）": "soudan",
    "地域相談支援（地域定着支援）": "soudan",
}
```

---

## 4. 電話番号の正規化ルール

### 現状
- 形式: ハイフン付き（例: `045-912-0733`）
- 充填率: 99.9%以上
- 異常値: ほぼなし

### 正規化ルール
```python
def normalize_tel(raw: str) -> str | None:
    """電話番号を正規化。無効なら None を返す。"""
    if not raw or not raw.strip():
        return None
    # 全角→半角
    tel = raw.translate(str.maketrans('０１２３４５６７８９ー（）', '0123456789-()'))
    # 数字とハイフンのみ残す
    digits = re.sub(r'[^\d]', '', tel)
    if len(digits) < 9 or len(digits) > 11:
        return None
    return tel.strip()
```

---

## 5. URL正規化ルール

### 現状
- 充填率: 放デイ67.4%、児発69.0%
- `http://` と `https://` が混在
- 末尾スラッシュの有無が不統一

### 正規化ルール
```python
def normalize_url(raw: str) -> str | None:
    """URLを正規化。無効なら None を返す。"""
    if not raw or not raw.strip():
        return None
    url = raw.strip()
    if not url.startswith(('http://', 'https://')):
        return None
    # メールアドレスを除外
    if '@' in url:
        return None
    return url
```

- `http://` → そのまま保持（httpsへの強制書き換えはしない）
- 事業所URL未登録の場合、法人URL（列10）をフォールバック候補とする

---

## 6. 緯度経度の妥当性チェック

### 現状
- **全レコード100%充填**
- 形式: 小数点以下8桁（例: `35.56536668`, `139.57640325`）
- 異常値: なし（全件が日本国内の座標）

### チェックルール
```python
def is_valid_japan_latlng(lat: float, lng: float) -> bool:
    """日本国内の座標として妥当か。"""
    return 20.0 <= lat <= 50.0 and 120.0 <= lng <= 155.0
```

- 0座標チェック: 実データでは0座標は確認されなかった
- ジオコーディングは**完全に不要**

---

## 7. 住所の正規化

### 現状
- 列15: 事業所住所（市区町村）→ 例: `神奈川県横浜市都筑区`
- 列16: 事業所住所（番地以降）→ 例: `大丸3-3-8 セントラルアベニュー202号室`
- 列0: 市区町村コード（5桁）→ 先頭2桁が都道府県コード

### 正規化ルール
```python
# 都道府県の抽出
PREF_NAMES = ["北海道", "青森県", ..., "沖縄県"]

def extract_prefecture(city_address: str) -> tuple[str, str]:
    """市区町村住所から都道府県を抽出。(都道府県名, 市区町村以下) を返す。"""
    for pref in PREF_NAMES:
        if city_address.startswith(pref):
            return pref, city_address[len(pref):]
    return "", city_address

# 全住所の結合
full_address = f"{row[15]}{row[16]}"
```

---

## 8. 1事業所複数サービスの表現方針

### 発見された事実
- 放デイ24,156件 + 児発16,247件 = 40,403レコード
- しかし事業所番号のユニーク数は **27,307件**
- **12,793件が放デイ・児発の両方を提供する多機能型**

### 表現方針

**方針: サービス単位でページを生成する（事業所単位ではない）**

理由:
1. ユーザーは「放課後等デイサービス ○○市」で検索する → サービス種別ごとのページが必要
2. 同一事業所でもサービスごとに定員・営業時間が異なりうる
3. build_site.pyの既存構造（1レコード=1ページ）と整合

**ただし:**
- 詳細ページに「この事業所が提供する他のサービス」セクションを表示
- 例: 放デイの詳細ページに「※この事業所では児童発達支援も提供しています」

```python
# 多機能型の検出
multi_function = len(services_by_office_code[office_code]) > 1
coexisting_services = [s for s in services_by_office_code[office_code] if s != current_service]
```

---

## 9. slug生成

### 詳細ページのslug
```
/office/{office_code}-{service_slug}.html
```

例:
- `/office/1450000001-houkago-day.html`（放デイ）
- `/office/1450000001-jidou-hattatsu.html`（児発）

同一事業所番号で同一サービスの重複がある場合:
- `/office/0150102242-houkago-day-a1b2c3.html`（ハッシュ付加）

### service_slug 対応表
```python
SERVICE_SLUGS = {
    "放課後等デイサービス": "houkago-day",
    "児童発達支援": "jidou-hattatsu",
    "就労移行支援": "shuro-ikou",
    "就労継続支援A型": "shuro-a",
    "就労継続支援B型": "shuro-b",
    "共同生活援助": "group-home",
    # ... 他のサービス
}
```

---

## 10. 詳細ページの単位: 事業所 vs サービス

### 結論: **サービス単位**

| 観点 | 事業所単位 | サービス単位（推奨） |
|------|----------|------------------|
| URL | `/office/1450000001.html` | `/office/1450000001-houkago-day.html` |
| ページ数 | ~27,307 | ~40,403 |
| SEO | 「放デイ ○○市」で弱い | サービス名がページに紐づくので強い |
| ユーザー体験 | 1ページに複数サービス混在 | 探しているサービスに集中できる |
| build_site.py互換 | 要改修 | 既存パターンそのまま |

---

## 11. convert_shogai_data.py に実装すべき最重要ルール

### 必須実装（Phase 0）
1. WAM NET CSV読み込み（utf-8-sig, 29カラム）
2. 放デイ(NN=65) + 児発(NN=63) のフィルタリング
3. pref_code の抽出（city_code[:2]）
4. 都道府県名の付与
5. 全住所の結合（列15 + 列16）
6. service_type の正規化（全角→半角）
7. service_group の割り当て
8. 多機能型フラグの生成
9. build_site.py用JSON形式への変換
10. 重複行の検出・レポート（削除はしない）
11. 品質サマリーの出力（件数・充填率・都道府県分布）

### 品質チェック（build前に必須）
- 全国47都道府県にレコードがあること
- 事業所名・住所・TELの充填率が99%以上であること
- 緯度経度の充填率が100%であること
- 定員の充填率が80%以上であること
