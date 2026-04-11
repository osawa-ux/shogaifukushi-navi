# 障害福祉サービスナビ — 調査・設計・初期実装方針

調査日: 2026-04-12

---

## 結論: **Go**

### 判定理由

1. **データ取得が現実的** — WAM NETオープンデータでCSV一括取得可能。既存パイプライン（fetch → normalize → convert → build_site.py）をほぼそのまま転用できる
2. **市場規模が大きい** — 全国約16万件の障害福祉サービス事業所。訪問看護（1.8万件）・居宅介護支援（3.6万件）よりはるかに大きい
3. **競合に決定的な穴がある** — 「全種別×詳細情報×使いやすいUI」を持つポータルが存在しない。LITALICOは児童系と就労系で分断、WAM NETはUI劣悪
4. **検索需要が確立** — 「放課後等デイサービス ○○市」「就労移行支援 ○○区」のロングテールキーワードが大量に存在
5. **既存アーキテクチャで構築可能** — build_site.py + site_config.json のマルチポータル構造に乗せるだけ。新規インフラ不要

---

## 1. データ取得調査

### 1-1. 最優先: WAM NET 障害福祉サービス等情報公表オープンデータ

| 項目 | 内容 |
|------|------|
| URL | https://www.wam.go.jp/content/wamnet/pcpub/top/sfkopendata/ |
| 形式 | ZIP圧縮CSV |
| 全国一括 | 可能 |
| 更新頻度 | 年2回（3月末・9月末時点） |
| ライセンス | 営利・非営利問わず利用可能（利用報告推奨） |
| 全国件数 | 約159,000件（全サービス種別合計） |
| 認証 | 不要（直接ダウンロード） |

**ファイルURL構造:**
```
https://www.wam.go.jp/content/files/pcpub/top/sfkopendata/202509/sfkopendata_202509_XX.zip
```

**ファイル命名規則:**
```
https://www.wam.go.jp/content/files/pcpub/top/sfkopendata/{YYYYMM}/sfkopendata_{YYYYMM}_{NN}.zip
```
ZIP内に `csvdownload0{NN}.csv` が1ファイル入っている。

**CSVカラム構造（全27種類のCSVで完全統一）:**

| 列番号 | カラム名 | 用途 |
|--------|---------|------|
| 0 | 都道府県コード又は市区町村コード | 地域分類 |
| 1 | NO | システム内固有番号 |
| 2 | 指定機関名 | — |
| 3 | 法人の名称 | 法人名 |
| 4 | 法人の名称_かな | — |
| 5 | 法人番号 | 13桁法人番号 |
| 6 | 法人住所（市区町村） | — |
| 7 | 法人住所（番地以降） | — |
| 8 | 法人電話番号 | — |
| 9 | 法人FAX番号 | — |
| 10 | 法人URL | — |
| 11 | サービス種別 | **サービス分類キー** |
| 12 | 事業所の名称 | **事業所名** |
| 13 | 事業所の名称_かな | 読み仮名 |
| 14 | 事業所番号 | **10桁ユニークキー** |
| 15 | 事業所住所（市区町村） | **住所（市区町村）** |
| 16 | 事業所住所（番地以降） | **住所（番地）** |
| 17 | 事業所電話番号 | **電話番号** |
| 18 | 事業所FAX番号 | FAX |
| 19 | 事業所URL | **公式URL** |
| 20 | 事業所緯度 | **緯度（WGS84）** |
| 21 | 事業所経度 | **経度（WGS84）** |
| 22 | 利用可能な時間帯（平日） | 営業時間 |
| 23 | 利用可能な時間帯（土曜） | 営業時間 |
| 24 | 利用可能な時間帯（日曜） | 営業時間 |
| 25 | 利用可能な時間帯（祝日） | 営業時間 |
| 26 | 定休日 | 定休日 |
| 27 | 利用可能曜日特記事項（留意事項） | 備考 |
| 28 | 定員 | **定員数** |

**CSVファイル一覧（2025年9月末時点・全27種類）:**

| NN | サービス種別 | 件数 | MVPフェーズ |
|----|------------|------|-----------|
| 11 | 居宅介護 | 24,813 | Phase 3 |
| 12 | 重度訪問介護 | 20,804 | Phase 3 |
| 13 | 行動援護 | 3,020 | Phase 3 |
| 14 | 重度障害者等包括支援 | 20 | Phase 3 |
| 15 | 同行援護 | 7,641 | Phase 3 |
| 21 | 療養介護 | 268 | Phase 3 |
| 22 | 生活介護 | 13,050 | Phase 3 |
| 32 | 施設入所支援 | 2,555 | Phase 3 |
| 33 | 共同生活援助（グループホーム） | 15,538 | Phase 2 |
| 41 | 自立訓練（機能訓練） | 286 | Phase 3 |
| 42 | 自立訓練（生活訓練） | 1,627 | Phase 3 |
| 45 | 就労継続支援A型 | 4,634 | Phase 2 |
| 46 | 就労継続支援B型 | 19,910 | Phase 2 |
| 52 | 計画相談支援 | 12,797 | Phase 3 |
| 53 | 地域相談支援（地域移行支援） | 3,708 | Phase 3 |
| 54 | 地域相談支援（地域定着支援） | 3,570 | Phase 3 |
| 60 | 就労移行支援 | 3,390 | Phase 2 |
| 61 | 自立生活援助 | 503 | Phase 3 |
| 62 | 就労定着支援 | 1,936 | Phase 2 |
| **63** | **児童発達支援** | **16,248** | **MVP** |
| 64 | 医療型児童発達支援 | 40 | Phase 3 |
| **65** | **放課後等デイサービス** | **24,157** | **MVP** |
| 66 | 居宅訪問型児童発達支援 | 347 | Phase 3 |
| 67 | 保育所等訪問支援 | 3,712 | Phase 3 |
| 68 | 福祉型障害児入所施設 | 244 | Phase 3 |
| 69 | 医療型障害児入所施設 | 228 | Phase 3 |
| 70 | 障害児相談支援 | 9,510 | Phase 3 |

**合計: 27種類、約194,000件（ヘッダー行除く）**

**注意点:**
- 情報公表ベースのため、一部事業所で詳細情報が未登録（公表率約81.7%）
- 基本情報（事業所名・住所・電話・サービス種別）はほぼ100%充填
- **緯度経度がCSVに含まれている（列20・21）** → ジオコーディング不要！
- 全CSVでカラム構造が完全統一 → パーサーが1つで全種別対応可能

### 1-2. 厚労省 jigyosho系CSV

**結論: 障害福祉サービス向けのjigyosho_XXX.csv形式は存在しない。**

介護保険系（jigyosho_130, jigyosho_430等）は厚労省が提供するが、障害福祉はWAM NETが一元管轄。この棲み分けは明確。

### 1-3. 補助ソース

| ソース | 形式 | 用途 | 難易度 |
|--------|------|------|--------|
| 各都道府県HP | PDF/Excel | 補完（指定事業所一覧） | 中（個別対応） |
| WAM NET検索UI | HTML | スクレイピング補完 | 高（SPA） |
| e-Stat | CSV | 統計・件数確認のみ | 低 |
| Google Places API | JSON | 口コミ・写真・営業状態 | 低（API課金あり） |

### 1-4. データ取得の優先順位

| 優先度 | ソース | 形式 | 全国一括 | 難易度 | フェーズ |
|--------|--------|------|----------|--------|----------|
| **最優先** | WAM NETオープンデータCSV | ZIP/CSV | 可 | **簡単** | MVP |
| 補助 | ジオコーディング（住所→緯度経度） | API | — | 低 | MVP |
| 補助 | Google Places API | JSON | — | 低（課金） | Phase 2 |
| 後回し | 都道府県別事業所一覧 | PDF/Excel | 都道府県単位 | 中 | Phase 3 |
| 後回し | WAM NET検索UIスクレイピング | HTML/SPA | 不可 | 高 | Phase 3+ |

### 1-5. MVPで十分なデータ vs 追加クロールで補完すべきデータ

**MVPで十分:**
- 事業所名、住所、電話番号、サービス種別、法人名、定員、緯度経度、営業時間
- 上記は**すべてWAM NET CSVで取得可能**（ジオコーディングも不要）

**追加クロールで補完:**
- 口コミ・写真（Google Places API: Phase 2）
- 詳細な運営方針・特色テキスト（WAM NET検索UIスクレイピング: Phase 3）
- 空き状況（事業所からの有料申告: Phase 3+）

---

## 2. サービス分類設計

### 2-1. 障害福祉サービスの公式分類一覧

#### 障害者総合支援法に基づくサービス

**介護給付:**
| サービス名 | 概要 | 全国事業所数 |
|------------|------|-------------|
| 居宅介護 | ホームヘルプ（身体介護・家事援助） | ~26,000 |
| 重度訪問介護 | 重度身体障害者への長時間在宅支援 | （居宅介護と重複登録多） |
| 同行援護 | 視覚障害者の移動支援 | ~7,000 |
| 行動援護 | 知的・精神障害者の行動支援 | ~3,000 |
| 重度障害者等包括支援 | 最重度の包括支援 | ~30 |
| 短期入所（ショートステイ） | 短期間の施設入所 | ~5,000 |
| 療養介護 | 医療+介護の長期入所 | ~250 |
| 生活介護 | 日中活動（入浴・食事・創作・生産） | ~12,000 |

**訓練等給付:**
| サービス名 | 概要 | 全国事業所数 |
|------------|------|-------------|
| 自立訓練（機能訓練） | 身体リハビリ | ~300 |
| 自立訓練（生活訓練） | 生活スキル訓練 | ~1,200 |
| 就労移行支援 | 一般就労への移行訓練（2年上限） | ~3,500 |
| 就労継続支援A型 | 雇用契約ありの就労 | ~4,500 |
| 就労継続支援B型 | 雇用契約なしの就労（工賃） | ~15,000 |
| 就労定着支援 | 就労後のフォローアップ | ~1,500 |
| 自立生活援助 | 一人暮らしの定期巡回支援 | ~500 |
| 共同生活援助（グループホーム） | 共同住居での生活支援 | ~13,000 |

**相談支援:**
| サービス名 | 概要 | 全国事業所数 |
|------------|------|-------------|
| 計画相談支援 | サービス等利用計画の作成 | ~11,000 |
| 地域移行支援 | 施設→地域への移行支援 | ~3,000 |
| 地域定着支援 | 地域生活の緊急対応支援 | ~3,000 |

#### 児童福祉法に基づくサービス

| サービス名 | 概要 | 全国事業所数 |
|------------|------|-------------|
| 児童発達支援 | 未就学児の療育 | ~11,000 |
| 放課後等デイサービス | 就学児の放課後療育 | ~22,000 |
| 保育所等訪問支援 | 保育所等への専門スタッフ派遣 | ~1,500 |
| 居宅訪問型児童発達支援 | 外出困難児への在宅療育 | ~100 |

### 2-2. ユーザー向け再分類（推奨案）

制度上の分類は複雑すぎて、利用者・家族には分かりにくい。
**ユーザーの「探しているもの」に沿った6カテゴリに再分類する。**

| カテゴリ | ユーザーの意図 | 含まれる公式サービス | 件数規模 |
|----------|---------------|---------------------|----------|
| **子ども向け支援** | 子どもの療育・放課後の居場所を探している | 児童発達支援、放課後等デイサービス、保育所等訪問支援、居宅訪問型児発 | ~35,000 |
| **就労支援** | 働きたい・働く場所を探している | 就労移行支援、就労継続支援A型、就労継続支援B型、就労定着支援 | ~24,500 |
| **住まい** | 住む場所を探している | 共同生活援助（グループホーム）、自立生活援助 | ~13,500 |
| **日中活動** | 日中の過ごし方・活動場所を探している | 生活介護、自立訓練（機能・生活）、短期入所、療養介護 | ~19,000 |
| **在宅支援** | 自宅での介護・外出支援を探している | 居宅介護、重度訪問介護、同行援護、行動援護、重度包括 | ~36,000 |
| **相談支援** | まず何をすればいいか相談したい | 計画相談支援、地域移行支援、地域定着支援 | ~17,000 |

**合計: 約145,000件**（重複登録を考慮すると実質は少なくなる）

### 2-3. なぜこの分類か

1. **ユーザーの検索意図に対応** — 制度名を知らなくても「子どもの療育」「働く場所」「住む場所」で辿り着ける
2. **SEO的に有利** — 各カテゴリがH1レベルのキーワード群を形成（「放課後等デイサービス ○○市」「グループホーム 障害者 ○○」）
3. **ページ量のバランス** — 各カテゴリ1万〜3.5万件で、薄すぎず多すぎない
4. **1サービスが1カテゴリに収まる** — 重複割り当てがなく、ナビゲーションが明快

### 2-4. サイト構造: 1サイト統合 vs サービス群分割

| 観点 | 1サイト統合 | サービス群ごとに分割（例: 放デイナビ、就労ナビ） |
|------|------------|------------------------------------------------|
| **SEO** | ドメインパワーが集約される。内部リンクが強い | 各サイトのドメインパワーが弱い。リンク分散 |
| **運用負荷** | 1つのbuild_site.pyで管理。設定切替で対応 | 複数サイト × 設定 × デプロイの管理が倍増 |
| **UX** | カテゴリ切替で回遊できる | サイト横断が必要で離脱リスク |
| **将来拡張** | カテゴリ追加がURL追加だけで済む | 新サイト立ち上げが毎回必要 |
| **ブランド認知** | 「障害福祉サービスナビ」で統一的に覚えてもらえる | 認知が分散する |
| **ページ数** | 10万ページ超になりうる → sitemap分割・noindex戦略が必要 | 各サイト1〜3万ページ |
| **競合差別化** | 全種別カバーが最大の強み | LITALICOと同じ分割戦略になり差別化できない |

### **推奨: 1サイト統合**

理由:
- **最大の差別化ポイントが「全種別を1箇所で探せること」** — これは既存競合がどこもやっていない
- 運用負荷が個人開発体制で現実的（build_site.pyのconfig切替で対応可能）
- ドメインパワー集約でSEO効率が高い
- ただし **MVP段階では全種別を作る必要はない** — URLの名前空間だけ確保して、フェーズごとにカテゴリを増やす

---

## 3. データ構造設計

### 3-1. 共通コア（OfficeMaster — 全ポータル共通）

既存の kyotaku-navi の `OfficeMaster` をベースに、ポータル横断で使えるコア。

```json
{
  "office_id": "wam_shogai:{office_code}:{service_code}",
  "portal_type": "shogaifukushi",
  "service_code": "放課後等デイサービス",
  "service_name": "放課後等デイサービス",

  "name": "○○放課後等デイサービス",
  "name_kana": null,

  "prefecture": "神奈川県",
  "pref_code": "14",
  "city": "横浜市都筑区",
  "city_code": "141180",
  "address": "神奈川県横浜市都筑区○○1-2-3",
  "address_building": "○○ビル2F",
  "postal_code": "224-0003",

  "tel": "045-123-4567",
  "fax": "045-123-4568",

  "corporation_name": "株式会社○○",
  "corporation_number": "1234567890123",

  "office_code": "1450000001",

  "latitude": 35.5505,
  "longitude": 139.5622,

  "website_url": "https://example.com",

  "source_primary": "wam_shogai_open_data",
  "source_url": "https://www.wam.go.jp/content/wamnet/pcpub/top/sfkopendata/",
  "source_updated_at": "2025-09-30",
  "retrieved_at": "2026-04-12T10:00:00+09:00",

  "is_active": true
}
```

**フィールド分類:**

| フィールド | 必須/任意 | 説明 |
|-----------|----------|------|
| office_id | **必須** | 一意識別子 |
| portal_type | **必須** | ポータル種別 |
| service_code | **必須** | WAM NETサービス種別コード |
| service_name | **必須** | サービス種別名称 |
| name | **必須** | 事業所名 |
| name_kana | 任意 | 事業所名カナ |
| prefecture | **必須** | 都道府県 |
| pref_code | **必須** | 都道府県コード（2桁） |
| city | **必須** | 市区町村 |
| city_code | 任意 | 市区町村コード（6桁） |
| address | **必須** | 全住所 |
| address_building | 任意 | 方書 |
| postal_code | 任意 | 郵便番号 |
| tel | **必須** | 電話番号 |
| fax | 任意 | FAX |
| corporation_name | 任意 | 法人名 |
| corporation_number | 任意 | 法人番号（13桁） |
| office_code | **必須** | 事業所番号（10桁）= ユニークキー |
| latitude | 任意（MVP後必須化） | 緯度 |
| longitude | 任意（MVP後必須化） | 経度 |
| website_url | 任意 | 公式URL |
| source_primary | **必須** | データソース名 |
| source_url | 任意 | 取得元URL |
| source_updated_at | 任意 | ソース更新日 |
| retrieved_at | 任意 | 取得日時 |
| is_active | **必須** | 稼働フラグ |

### 3-2. 障害福祉サービス拡張（ShogaiFukushiFeatures）

```json
{
  "office_id": "wam_shogai:1450000001:放課後等デイサービス",

  "service_type": "放課後等デイサービス",
  "service_group": "子ども向け支援",

  "target_disabilities": ["知的障害", "発達障害", "身体障害"],
  "target_age_group": "就学児（6〜18歳）",

  "capacity": 10,
  "current_users": null,

  "multi_function": true,
  "coexisting_services": ["児童発達支援"],

  "support_features": {
    "has_pickup": true,
    "has_meals": false,
    "has_bathing": false,
    "has_medical_care": false,
    "has_night_support": false,
    "has_weekend": true,
    "has_holiday": true,
    "specialties": ["運動療育", "学習支援", "SST"]
  },

  "business_days_text": "月〜土 10:00〜18:00",
  "business_days_note": "日曜・祝日休み",
  "established_date": "2020-04-01",

  "remarks_raw": null,

  "source": "wam_shogai_open_data"
}
```

**フィールド分類:**

| フィールド | 必須/任意 | 説明 |
|-----------|----------|------|
| office_id | **必須** | OfficeMasterへの外部キー |
| service_type | **必須** | 公式サービス種別名 |
| service_group | **必須** | ユーザー向けカテゴリ（6分類） |
| target_disabilities | 任意 | 対象障害種別（配列） |
| target_age_group | 任意 | 対象年齢区分 |
| capacity | 任意 | 定員 |
| current_users | 任意 | 現在利用者数 |
| multi_function | 任意 | 多機能型事業所か |
| coexisting_services | 任意 | 併設サービス（配列） |
| support_features | 任意 | 提供特徴（送迎・食事等） |
| business_days_text | 任意 | 営業曜日テキスト |
| business_days_note | 任意 | 営業特記事項 |
| established_date | 任意 | 開所日 |
| remarks_raw | 任意 | 備考 |
| source | **必須** | データソース名 |

### 3-3. サービス別追加拡張の切り方

| サービスグループ | 追加で必要になるフィールド |
|----------------|--------------------------|
| 子ども向け支援 | 療育プログラム内容、対象学齢、保護者支援有無 |
| 就労支援 | 工賃/賃金実績、就職率、訓練内容、業種 |
| 住まい | 居室タイプ（個室/共同）、世話人配置比率、入居条件 |
| 日中活動 | 活動内容、医療的ケア対応、重心対応 |
| 在宅支援 | 対応時間帯、対応地域、緊急対応可否 |
| 相談支援 | 対応障害種別、オンライン相談可否 |

**方針: MVP段階ではShogaiFukushiFeaturesのみ。サービス別拡張はPhase 2以降。**

### 3-4. build_site.py向け変換後フォーマット

build_site.pyに投入するデータ形式（既存のclinic/stationフォーマット互換）:

```json
{
  "kikan_cd": "1450000001",
  "name": "○○放課後等デイサービス",
  "address": "神奈川県横浜市都筑区○○1-2-3",
  "postal": "224-0003",
  "tel": "045-123-4567",
  "fax": "045-123-4568",
  "url": "https://example.com",
  "pref": "神奈川県",
  "pref_code": "14",
  "lat": 35.5505,
  "lng": 139.5622,
  "kikan_kbn": "2",
  "business_status": "OPERATIONAL",
  "specialties": ["放課後等デイサービス"],
  "emergency": {},
  "rating": null,
  "review_count": null,
  "photo_url": "",
  "image_url": "",
  "place_id": "",
  "corporation_name": "株式会社○○",
  "source": "wam_shogai_opendata",

  "service_type": "放課後等デイサービス",
  "service_group": "子ども向け支援",
  "capacity": 10,
  "target_age_group": "就学児",
  "has_pickup": true,
  "coexisting_services": ["児童発達支援"]
}
```

---

## 4. MVP設計

### 4-1. 最初に扱うべきサービスの比較

| サービス | 検索需要 | 件数 | データ取得 | SEOチャンス | 競合強度 | 比較のしやすさ | 推奨度 |
|----------|---------|------|-----------|------------|---------|-------------|--------|
| **放課後等デイサービス** | 非常に高い | ~22,000 | 容易 | 高い | LITALICO強い | 高い | **◎ MVP第一候補** |
| **児童発達支援** | 高い | ~11,000 | 容易 | 高い | LITALICO強い | 高い | **◎ 放デイと同時** |
| 就労継続支援B型 | 中〜高 | ~15,000 | 容易 | 中 | LITALICO仕事ナビ | 中 | ○ Phase 2 |
| 就労移行支援 | 高い | ~3,500 | 容易 | 中 | LITALICO仕事ナビ | 中 | ○ Phase 2 |
| グループホーム | 高（増加中） | ~13,000 | 容易 | 高い | 弱い | 低い | ○ Phase 2-3 |
| 相談支援 | 低〜中 | ~11,000 | 容易 | 低い | 弱い | 低い | △ Phase 3 |
| 生活介護 | 中 | ~12,000 | 容易 | 低い | 弱い | 低い | △ Phase 3 |
| 居宅介護 | 低 | ~26,000 | 容易 | 低い | なし | 低い | △ Phase 3+ |

### 4-2. 推奨MVP: 放課後等デイサービス＋児童発達支援

**なぜこの2つか:**

1. **検索需要が最大** — 保護者（主に母親）が「自分で積極的に調べる」行動をとる。在宅クリニックナビと同じ構造
2. **同時に扱うのが自然** — 多くの事業所が放デイと児発の両方を提供（多機能型）。ユーザーも両方を比較する
3. **件数規模が適切** — 合計約33,000件。訪問診療ナビ（15,759件）より大きいが、16万件全部に比べれば管理可能
4. **比較軸が明確** — 送迎有無、対象年齢、療育プログラム、土日対応、定員 → 比較表が作りやすい
5. **収益化しやすい** — 事業所側も集客に積極的。月額3,000〜10,000円の有料掲載が現実的

**LITALICOとの競合は問題にならないか:**
- LITALICOは掲載事業所からの有料申込ベースで情報を充実させるモデル
- 当ナビはWAM NETの公開データで全事業所を網羅するモデル → LITALICOに掲載されていない事業所も載る
- 特に地方都市・中小都市ではLITALICOの掲載が薄い → そこがSEOの隙間

### 4-3. 地域範囲: 最初から全国

理由:
- WAM NET CSVで全国一括取得できるため、データ面のコストは同じ
- build_site.pyは全国47都道府県対応済み
- SEOは都道府県×市区町村のロングテール → 全国分生成しないと機会損失
- 特定地域だけだと「一部地域しかない」という印象でユーザーが離脱する

### 4-4. MVP最低限フィールド

| フィールド | ソース | 表示用途 |
|-----------|--------|---------|
| 事業所名 | WAM NET CSV | タイトル |
| 住所 | WAM NET CSV | 地域ページ振り分け + 表示 |
| 電話番号 | WAM NET CSV | 連絡先 |
| サービス種別 | WAM NET CSV | カテゴリ分類 |
| 法人名 | WAM NET CSV | 運営元表示 |
| 定員 | WAM NET CSV | 比較情報 |
| 開所日 | WAM NET CSV | 参考情報 |

### 4-5. MVPとして不要な項目

- 緯度経度（地図表示はPhase 2。住所テキストだけで十分）
- Google口コミ・写真（Phase 2）
- 詳細な運営方針テキスト（Phase 3: WAM NETスクレイピング）
- 空き状況（Phase 3+: 事業所申告）
- 療育プログラム詳細（有料プランで事業所が入力）
- 工賃実績（就労系Phase 2）

### 4-6. 最初からやらない方がよい機能

- 口コミ投稿機能（モデレーション負荷が高い）
- 予約・問い合わせフォーム（MVP不要。有料プランで後付け）
- 事業所ログイン・管理画面（バックエンド不要の方針）
- 地図検索（ジオコーディングコスト + 実装コスト）
- AI推薦・マッチング（過剰）

### 4-7. フェーズ計画

| Phase | スコープ | 件数 | 期間目安 |
|-------|---------|------|---------|
| **MVP** | 放デイ＋児発（全国） | ~40,400 | 2-3週間 |
| **Phase 2** | 就労系4種＋グループホーム追加 | +~36,000 | 2-3週間 |
| **Phase 3** | 残り全種別追加 | +~90,000 | 3-4週間 |
| **Phase 4** | Google Places連携・地図・有料プラン | — | 継続 |

---

## 5. 実装・SEO設計

### 5-1. ページ構造

```
/                                    → トップ（全サービスカテゴリ一覧）
/service/{service_group}/            → サービスグループトップ
  例: /service/kodomo/               → 子ども向け支援トップ
      /service/shuro/                → 就労支援トップ
      /service/sumai/                → 住まいトップ
/pref/{pref_slug}.html               → 都道府県ページ
  例: /pref/kanagawa.html
/pref/{pref_slug}/{city_slug}.html   → 市区町村ページ
  例: /pref/kanagawa/横浜市都筑区.html
/office/{office_code}.html           → 事業所詳細ページ
  例: /office/1450000001.html
/data/search/{01-47}.json            → 都道府県別検索JSON
/data/area_master.json               → エリアマスター
/sitemap_index.xml                   → サイトマップインデックス
/sitemap_{pref_code}.xml             → 都道府県別サイトマップ
```

### 5-2. URL設計の判断

**「サービス種別」をURLに含めるか問題:**

```
案A: /pref/kanagawa.html（全種別混合）
案B: /service/kodomo/pref/kanagawa.html（種別でネスト）
案C: /houkago-day/pref/kanagawa.html（サービス名でネスト）
```

**推奨: 案A（全種別混合） + フィルター**

理由:
- MVP段階は放デイ＋児発のみなので、種別ネストは過剰
- Phase 2以降でカテゴリが増えたら `/service/{group}/pref/...` に段階的に分岐
- build_site.pyの既存構造と互換（pref → city → detail の3層構造）

**Phase 2以降の拡張:**
```
/kodomo/pref/kanagawa.html            → 子ども向け×神奈川
/shuro/pref/tokyo.html                → 就労支援×東京
/sumai/pref/osaka.html                → 住まい×大阪
```

### 5-3. ページ数概算

**MVP（放デイ＋児発）:**
| ページ種別 | 計算 | ページ数 |
|-----------|------|---------|
| トップ | 1 | 1 |
| 都道府県ページ | 47 | 47 |
| 市区町村ページ | ~1,500市区町村 | ~1,500 |
| 事業所詳細 | ~40,400（放デイ24,157+児発16,248） | ~40,400 |
| 検索JSON | 47 | 47 |
| 静的ページ | ~10 | ~10 |
| **合計** | | **~42,000** |

**全種別展開後:**
| ページ種別 | ページ数 |
|-----------|---------|
| サービスグループトップ | 6 |
| 都道府県 × サービスグループ | 47 × 6 = 282 |
| 市区町村 × サービスグループ | ~1,500 × 6 = ~9,000 |
| 事業所詳細 | ~120,000（重複除外後） |
| **合計** | **~130,000** |

### 5-4. 薄いページ対策

**リスク:**
- 過疎地域の市区町村ページが事業所1〜2件になる
- 全種別展開すると空のカテゴリ×市区町村ページが大量発生

**対策:**
- `noindex, follow` — 事業所1件以下の市区町村ページ（既存build_site.pyと同じ）
- **サービスグループ×市区町村ページは件数3件以上でのみ生成** — 少なすぎるページは親（都道府県）に集約
- テンプレートバリエーション — 都道府県ページのテキストを7パターンで回す（既存と同じ）
- 各詳細ページに十分なコンテンツ — 基本情報 + 近隣事業所リスト + 同法人の他事業所 + FAQセクション

### 5-5. sitemap/canonical方針

- **sitemap_index.xml** — 都道府県別に47分割（既存と同じ）
- Phase 2以降: サービスグループ別にも分割 → `sitemap_kodomo.xml`, `sitemap_shuro.xml` 等
- **canonical** — 全ページに自己参照canonical
- 1事業所が複数サービスを持つ場合 → 各サービスで別ページ（別URL）を生成し、各ページにcanonicalを設定
- robots.txt — 検索JSON・内部APIパスをDisallow

---

## 6. リスク評価

### 6-1. リスク一覧と回避策

| # | リスク | 影響度 | 回避策 |
|---|--------|--------|--------|
| 1 | **WAM NET CSVのカラム構造が未確認** — 実際のCSVを開くまでフィールドの充填率・粒度が不明 | 高 | 最初にCSVをダウンロードしてカラム分析（download_csv.pyパターン）。異常があればMVPスコープを調整 |
| 2 | ~~緯度経度がCSVに含まれない~~ **解消: CSV列20・21に緯度経度が含まれる** | — | ジオコーディング不要。地図機能もMVPから検討可能 |
| 3 | **1事業所で複数サービスを提供** — データの重複・ページ分割の判断が複雑 | 中 | office_code + service_type の複合キーでユニーク化。1事業所×1サービス = 1詳細ページ。事業所一覧では「多機能型」バッジで表示 |
| 4 | **サービス分類が多すぎてUXが悪化** — 20種類以上のサービスをどう見せるか | 中 | ユーザー向け6カテゴリに再分類。トップページは6カテゴリのみ表示。詳細は各カテゴリ内で |
| 5 | **薄いページが量産される** — 過疎地域×マイナーサービスの組み合わせ | 中 | noindex戦略 + 件数閾値（3件未満は生成しない）で制御 |
| 6 | **LITALICOとの直接競合** — 児童系はLITALICOが圧倒的に強い | 低〜中 | 全事業所網羅（LITALICO未掲載事業所も載る）で差別化。地方都市に注力。最終的には全種別カバーが差別化の核 |
| 7 | **データ更新頻度が年2回** — 情報の鮮度が低い | 低 | 有料プランで事業所自身が情報更新できる仕組みをPhase 3で追加。無料分はWAM NET更新に追従 |
| 8 | **CSV形式変更** — WAM NETがフォーマットを変更する可能性 | 低 | カラムマッピングを設定ファイルで管理。変更検知スクリプトを用意 |

### 6-2. 訪問診療ナビ・訪問看護ナビとの比較

| 観点 | 訪問診療ナビ | 訪問看護ナビ | 障害福祉サービスナビ |
|------|------------|------------|-------------------|
| データソース | 厚労省CSV + Google Places | 厚労省 jigyosho_130.csv | WAM NETオープンデータCSV |
| 全国件数 | ~15,800 | ~18,000 | **~40,400（MVP）/ ~160,000（全種別）** |
| サービス分類 | 1種類 | 1種類 | **20種類以上 → 6カテゴリに再分類** |
| データ取得難易度 | 低 | 低 | **低（CSVダウンロード）** |
| 設計の複雑さ | 低 | 低 | **中（多サービス対応が必要）** |
| SEO難易度 | 中 | 中 | **中〜高（競合LITALICOが強い）** |
| 運用負荷 | 低 | 低 | **低〜中（データ更新は同じパターン）** |

### 6-3. 難易度総評

| 項目 | 難易度 | 理由 |
|------|--------|------|
| データ取得 | **低** | WAM NET CSVで一括取得。認証不要 |
| データ正規化 | **中** | 多サービス対応、1事業所複数サービスの扱い |
| 設計 | **中** | サービス分類設計、URL設計の判断が必要 |
| 実装 | **低** | build_site.py + site_config.json の既存パターン |
| SEO | **中〜高** | LITALICOが児童系で強い。地方ロングテールで勝負 |
| 運用 | **低** | 年2回のCSV更新 + build |

**総合: 中（訪問診療ナビより少し難しいが、十分に個人開発で回せる）**

---

## 7. 優先順位

### すぐ作れる領域

| 領域 | 理由 |
|------|------|
| **放課後等デイサービス（全国一覧）** | データ取得容易、検索需要最大、比較軸明確 |
| **児童発達支援（全国一覧）** | 放デイと同時取得・同時生成。多機能型で併設多い |
| **都道府県×市区町村の一覧ページ** | build_site.pyの既存パターンそのまま |
| **基本情報の詳細ページ** | WAM NET CSVのフィールドだけで成立 |

### 後回しにした方がいい領域

| 領域 | 理由 |
|------|------|
| 在宅支援系（居宅介護・重度訪問等） | 検索需要が低い。利用者が自分で探すケースが少ない |
| 地図検索 | ジオコーディングコストが発生。MVPには不要 |
| 口コミ・写真 | Google Places API課金 + モデレーション負荷 |
| 有料プラン・課金機能 | ユーザー獲得後でよい |
| 事業所管理画面 | バックエンド構築が必要。Phase 4以降 |

### やると強いが難しい領域

| 領域 | 強さ | 難しさ |
|------|------|--------|
| **全種別カバー（16万件）** | 唯一の全種別ポータルになれる | ページ数10万超の管理、薄いページ対策 |
| **空き状況のリアルタイム表示** | 圧倒的な差別化。利用者の最大ニーズ | 事業所側の更新の仕組みが必要（バックエンド） |
| **療育プログラム・就労実績の詳細比較** | 比較サイトとしての価値が飛躍的に向上 | データが公開情報にない。事業所からの情報提供が必要 |
| **相談支援事業所との連携機能** | ケアマネ→事業所の紹介フローを取れる | BtoB機能の設計が複雑 |

---

## 最終提案

### 構築順序

```
Phase 0: データ取得・検証（1〜2日）
  ↓
Phase 1/MVP: 放デイ＋児発 全国ポータル（2〜3週間）
  ↓
Phase 2: 就労系＋グループホーム追加（2〜3週間）
  ↓
Phase 3: 残り全種別＋Google Places連携
  ↓
Phase 4: 有料プラン・問い合わせ機能
```

### 初手の推奨アクション3つ

1. **WAM NETオープンデータCSVをダウンロードしてカラム分析する**
   - 放課後等デイサービス: `https://www.wam.go.jp/content/files/pcpub/top/sfkopendata/202509/sfkopendata_202509_65.zip`
   - 児童発達支援: `https://www.wam.go.jp/content/files/pcpub/top/sfkopendata/202509/sfkopendata_202509_63.zip`
   - download_csv.py パターンでカラム充填率・件数・都道府県分布を分析
   - CSVカラム構造は確認済み（29列、緯度経度含む）。充填率の実測がこのステップのゴール

2. **site_config_shogaifukushi.json を作成する**
   - 既存の site_config_houmon_kango.json をコピーして設定を書き換え
   - entity_detail_prefix = "office"
   - entity_type = "障害福祉サービス事業所"
   - care_type = "障害福祉サービス"

3. **convert_shogai_data.py を実装する**
   - WAM NET CSV → build_site.py用JSONへの変換スクリプト
   - 既存の convert_kango_data.py パターンを流用
   - 放デイ＋児発のフィルタリングを含む

---

## 補助成果物

### A. 初期実装タスク分解

```
[ ] Phase 0: データ取得・検証
  [ ] WAM NETオープンデータページからCSVファイルのURL特定
  [ ] download_csv.py 作成（shogaifukushi版）
  [ ] CSV構造分析（カラム名、充填率、件数、都道府県分布）
  [ ] 放課後等デイサービス + 児童発達支援 のフィルタリング確認

[ ] Phase 1: 正規化・変換
  [ ] normalize_offices.py 作成（住所正規化、法人名正規化）
  [ ] service_type_mapping.json 作成
  [ ] convert_shogai_data.py 作成（CSV → build_site.py用JSON）
  [ ] データ品質レポート出力

[ ] Phase 1: サイト生成
  [ ] site_config_shogaifukushi.json 作成
  [ ] region_texts_shogaifukushi.json 作成
  [ ] page_texts_shogaifukushi.json 作成
  [ ] build_site.py で生成テスト
  [ ] HTML出力確認（都道府県・市区町村・詳細ページ）
  [ ] sitemap生成確認

[ ] Phase 1: デプロイ
  [ ] GitHub Pages or Cloudflare Pages セットアップ
  [ ] ドメイン取得・DNS設定
  [ ] GA4・Search Console設置
  [ ] データ品質最終確認
  [ ] 公開
```

### B. service_type 正規化マッピング案

```json
{
  "service_type_mapping": {
    "放課後等デイサービス": {
      "nn": 65,
      "csv_file": "sfkopendata_202509_65.zip",
      "records": 24157,
      "group": "kodomo",
      "group_name": "子ども向け支援",
      "age_group": "就学児（6〜18歳）",
      "slug": "houkago-day",
      "search_keywords": ["放課後等デイサービス", "放デイ", "放課後デイ", "障害児 放課後"]
    },
    "児童発達支援": {
      "nn": 63,
      "csv_file": "sfkopendata_202509_63.zip",
      "records": 16248,
      "group": "kodomo",
      "group_name": "子ども向け支援",
      "age_group": "未就学児（0〜6歳）",
      "slug": "jidou-hattatsu",
      "search_keywords": ["児童発達支援", "療育", "発達支援", "児発"]
    },
    "就労移行支援": {
      "group": "shuro",
      "group_name": "就労支援",
      "age_group": "18〜65歳",
      "slug": "shuro-ikou",
      "search_keywords": ["就労移行支援", "障害者 就職", "就労移行"]
    },
    "就労継続支援A型": {
      "group": "shuro",
      "group_name": "就労支援",
      "age_group": "18〜65歳",
      "slug": "shuro-a",
      "search_keywords": ["就労継続支援A型", "A型事業所", "障害者 雇用"]
    },
    "就労継続支援B型": {
      "group": "shuro",
      "group_name": "就労支援",
      "age_group": "18歳以上",
      "slug": "shuro-b",
      "search_keywords": ["就労継続支援B型", "B型事業所", "作業所", "障害者 工賃"]
    },
    "就労定着支援": {
      "group": "shuro",
      "group_name": "就労支援",
      "age_group": "18歳以上",
      "slug": "shuro-teichaku",
      "search_keywords": ["就労定着支援"]
    },
    "共同生活援助": {
      "group": "sumai",
      "group_name": "住まい",
      "age_group": "18歳以上",
      "slug": "group-home",
      "search_keywords": ["グループホーム", "障害者 グループホーム", "共同生活援助", "GH"]
    },
    "自立生活援助": {
      "group": "sumai",
      "group_name": "住まい",
      "age_group": "18歳以上",
      "slug": "jiritsu-seikatsu",
      "search_keywords": ["自立生活援助"]
    },
    "生活介護": {
      "group": "nicchu",
      "group_name": "日中活動",
      "age_group": "18歳以上",
      "slug": "seikatsu-kaigo",
      "search_keywords": ["生活介護", "障害者 日中活動"]
    },
    "自立訓練（機能訓練）": {
      "group": "nicchu",
      "group_name": "日中活動",
      "age_group": "18歳以上",
      "slug": "kinou-kunren",
      "search_keywords": ["自立訓練", "機能訓練"]
    },
    "自立訓練（生活訓練）": {
      "group": "nicchu",
      "group_name": "日中活動",
      "age_group": "18歳以上",
      "slug": "seikatsu-kunren",
      "search_keywords": ["自立訓練", "生活訓練"]
    },
    "短期入所": {
      "group": "nicchu",
      "group_name": "日中活動",
      "age_group": "全年齢",
      "slug": "short-stay",
      "search_keywords": ["短期入所", "ショートステイ", "障害者 ショートステイ"]
    },
    "療養介護": {
      "group": "nicchu",
      "group_name": "日中活動",
      "age_group": "18歳以上",
      "slug": "ryouyou-kaigo",
      "search_keywords": ["療養介護"]
    },
    "居宅介護": {
      "group": "zaitaku",
      "group_name": "在宅支援",
      "age_group": "全年齢",
      "slug": "kyotaku-kaigo",
      "search_keywords": ["居宅介護", "ホームヘルプ", "障害者 ヘルパー"]
    },
    "重度訪問介護": {
      "group": "zaitaku",
      "group_name": "在宅支援",
      "age_group": "18歳以上",
      "slug": "judo-houmon",
      "search_keywords": ["重度訪問介護"]
    },
    "同行援護": {
      "group": "zaitaku",
      "group_name": "在宅支援",
      "age_group": "全年齢",
      "slug": "doukou-engo",
      "search_keywords": ["同行援護", "視覚障害 移動支援"]
    },
    "行動援護": {
      "group": "zaitaku",
      "group_name": "在宅支援",
      "age_group": "全年齢",
      "slug": "koudou-engo",
      "search_keywords": ["行動援護"]
    },
    "重度障害者等包括支援": {
      "group": "zaitaku",
      "group_name": "在宅支援",
      "age_group": "全年齢",
      "slug": "judo-houkatsu",
      "search_keywords": ["重度障害者等包括支援"]
    },
    "計画相談支援": {
      "group": "soudan",
      "group_name": "相談支援",
      "age_group": "全年齢",
      "slug": "keikaku-soudan",
      "search_keywords": ["計画相談支援", "相談支援事業所", "障害 相談"]
    },
    "地域移行支援": {
      "group": "soudan",
      "group_name": "相談支援",
      "age_group": "18歳以上",
      "slug": "chiiki-ikou",
      "search_keywords": ["地域移行支援"]
    },
    "地域定着支援": {
      "group": "soudan",
      "group_name": "相談支援",
      "age_group": "18歳以上",
      "slug": "chiiki-teichaku",
      "search_keywords": ["地域定着支援"]
    },
    "保育所等訪問支援": {
      "group": "kodomo",
      "group_name": "子ども向け支援",
      "age_group": "未就学〜就学児",
      "slug": "hoikusho-houmon",
      "search_keywords": ["保育所等訪問支援"]
    },
    "居宅訪問型児童発達支援": {
      "group": "kodomo",
      "group_name": "子ども向け支援",
      "age_group": "未就学〜就学児",
      "slug": "kyotaku-jidou",
      "search_keywords": ["居宅訪問型児童発達支援"]
    }
  },

  "service_groups": {
    "kodomo": {
      "name": "子ども向け支援",
      "slug": "kodomo",
      "description": "お子さまの療育・発達支援・放課後の居場所",
      "icon": "child",
      "priority": 1,
      "mvp": true
    },
    "shuro": {
      "name": "就労支援",
      "slug": "shuro",
      "description": "働きたい方の就職支援・作業所・職場定着",
      "icon": "briefcase",
      "priority": 2,
      "mvp": false
    },
    "sumai": {
      "name": "住まい",
      "slug": "sumai",
      "description": "グループホーム・一人暮らし支援",
      "icon": "home",
      "priority": 3,
      "mvp": false
    },
    "nicchu": {
      "name": "日中活動",
      "slug": "nicchu",
      "description": "日中の活動・リハビリ・ショートステイ",
      "icon": "sun",
      "priority": 4,
      "mvp": false
    },
    "zaitaku": {
      "name": "在宅支援",
      "slug": "zaitaku",
      "description": "自宅での介護・外出支援・移動支援",
      "icon": "house-medical",
      "priority": 5,
      "mvp": false
    },
    "soudan": {
      "name": "相談支援",
      "slug": "soudan",
      "description": "サービス利用の計画作成・地域生活の相談",
      "icon": "comments",
      "priority": 6,
      "mvp": false
    }
  }
}
```

### C. サンプルスキーマ（sample_schema.json）

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ShogaiFukushiOffice",
  "description": "障害福祉サービス事業所 統合データスキーマ（共通コア + 障害福祉拡張）",
  "type": "object",
  "required": ["office_id", "portal_type", "service_code", "service_name", "name", "prefecture", "pref_code", "city", "address", "tel", "office_code", "source_primary", "is_active", "service_type", "service_group"],
  "properties": {
    "office_id": {
      "type": "string",
      "description": "一意識別子。形式: wam_shogai:{office_code}:{service_code}",
      "pattern": "^wam_shogai:\\d{10}:.+"
    },
    "portal_type": {
      "type": "string",
      "const": "shogaifukushi"
    },
    "service_code": {
      "type": "string",
      "description": "WAM NETサービス種別コード"
    },
    "service_name": {
      "type": "string",
      "description": "サービス種別名称"
    },
    "name": {
      "type": "string",
      "description": "事業所名"
    },
    "name_kana": {
      "type": ["string", "null"],
      "description": "事業所名カナ"
    },
    "prefecture": {
      "type": "string",
      "description": "都道府県"
    },
    "pref_code": {
      "type": "string",
      "pattern": "^\\d{2}$",
      "description": "都道府県コード（2桁）"
    },
    "city": {
      "type": "string",
      "description": "市区町村"
    },
    "city_code": {
      "type": ["string", "null"],
      "pattern": "^\\d{6}$",
      "description": "市区町村コード（6桁）"
    },
    "address": {
      "type": "string",
      "description": "住所（都道府県含む全文）"
    },
    "address_building": {
      "type": ["string", "null"]
    },
    "postal_code": {
      "type": ["string", "null"],
      "pattern": "^\\d{3}-\\d{4}$"
    },
    "tel": {
      "type": ["string", "null"]
    },
    "fax": {
      "type": ["string", "null"]
    },
    "corporation_name": {
      "type": ["string", "null"]
    },
    "corporation_number": {
      "type": ["string", "null"],
      "pattern": "^\\d{13}$"
    },
    "office_code": {
      "type": "string",
      "pattern": "^\\d{10}$",
      "description": "事業所番号（10桁）= ユニークキー"
    },
    "latitude": {
      "type": ["number", "null"]
    },
    "longitude": {
      "type": ["number", "null"]
    },
    "website_url": {
      "type": ["string", "null"],
      "format": "uri"
    },
    "source_primary": {
      "type": "string"
    },
    "source_url": {
      "type": ["string", "null"]
    },
    "source_updated_at": {
      "type": ["string", "null"],
      "format": "date"
    },
    "retrieved_at": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "is_active": {
      "type": "boolean",
      "default": true
    },
    "service_type": {
      "type": "string",
      "description": "公式サービス種別名"
    },
    "service_group": {
      "type": "string",
      "enum": ["kodomo", "shuro", "sumai", "nicchu", "zaitaku", "soudan"],
      "description": "ユーザー向けカテゴリ（6分類）"
    },
    "target_disabilities": {
      "type": ["array", "null"],
      "items": { "type": "string" }
    },
    "target_age_group": {
      "type": ["string", "null"]
    },
    "capacity": {
      "type": ["integer", "null"]
    },
    "current_users": {
      "type": ["integer", "null"]
    },
    "multi_function": {
      "type": ["boolean", "null"],
      "description": "多機能型事業所か"
    },
    "coexisting_services": {
      "type": ["array", "null"],
      "items": { "type": "string" }
    },
    "support_features": {
      "type": ["object", "null"],
      "properties": {
        "has_pickup": { "type": ["boolean", "null"] },
        "has_meals": { "type": ["boolean", "null"] },
        "has_bathing": { "type": ["boolean", "null"] },
        "has_medical_care": { "type": ["boolean", "null"] },
        "has_night_support": { "type": ["boolean", "null"] },
        "has_weekend": { "type": ["boolean", "null"] },
        "has_holiday": { "type": ["boolean", "null"] },
        "specialties": {
          "type": ["array", "null"],
          "items": { "type": "string" }
        }
      }
    },
    "business_days_text": {
      "type": ["string", "null"]
    },
    "business_days_note": {
      "type": ["string", "null"]
    },
    "established_date": {
      "type": ["string", "null"],
      "format": "date"
    },
    "remarks_raw": {
      "type": ["string", "null"]
    }
  }
}
```

### D. MVP定義（phase1_scope.md相当）

```
# 障害福祉サービスナビ — Phase 1 MVP定義

## スコープ
- サービス種別: 放課後等デイサービス + 児童発達支援
- 地域: 全国47都道府県
- 想定件数: ~40,400事業所
- ページ数: ~42,000ページ

## データソース
- WAM NETオープンデータCSV（主データ）
- ジオコーディングなし（Phase 2）

## 含む機能
- 都道府県一覧ページ
- 市区町村一覧ページ
- 事業所詳細ページ
- 都道府県別検索JSON
- サイトマップ（都道府県別分割）
- GA4 / Search Console
- noindex制御（1件以下の市区町村ページ）
- レスポンシブデザイン
- OGP画像

## 含まない機能（Phase 2以降）
- 地図表示
- Google口コミ・写真
- 有料プラン
- 問い合わせフォーム
- 事業所管理画面
- 就労系・住まい系等の他カテゴリ
- 口コミ投稿

## 技術スタック
- Python（データパイプライン）
- build_site.py（静的HTML生成）
- GitHub Pages or Cloudflare Pages（ホスティング）
- Cloudflare（DNS / CDN）

## 成功基準
- 全国33,000事業所の詳細ページが正しく生成される
- 都道府県別件数が正常（47都道府県すべてに事業所あり）
- 薄いページにnoindexが設定されている
- Search Consoleでインデックス登録が始まる
- ページ表示速度がモバイルで良好（静的HTMLなので問題なし想定）
```

---

## 参考リンク

- WAM NETオープンデータ: https://www.wam.go.jp/content/wamnet/pcpub/top/sfkopendata/
- WAM NET事業所検索: https://www.wam.go.jp/sfkohyoout/
- 厚労省 障害福祉サービス等情報公表制度: https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000202214_00001.html
- LITALICO発達ナビ: https://h-navi.jp/support_facility
- LITALICO仕事ナビ: https://snabi.jp/
- みんなの障がい: https://www.minnanosyougai.com/
- 障害者ドットコム: https://shohgaisha.com/
- ここくらす: https://cocokurasu.com/
