# 障害福祉サービスナビ (welfare.zaitaku-navi.com)

全国の障害福祉サービス事業所（Phase 1: 放課後等デイサービス・児童発達支援）を検索できるポータルサイト。
WAM NET オープンデータを基に静的HTMLを生成する。

- 公開先: `https://welfare.zaitaku-navi.com`（DNS未設定・技術的には公開可能状態）
- 親ハブ: `zaitaku-navi.com` 配下のサブドメイン群の一員（kango / shika / care / welfare / ...）

---

## 現在のステータス

| フェーズ | 状態 |
|---------|------|
| Phase 0: データ調査 | 完了（全27種別・194,529件取得済み） |
| Phase 1: MVP実装 | 完了（放デイ24,156件 + 児発16,247件） |
| Phase 1.1: 医療残骸除去 | 完了（build_site.py config駆動化） |
| Phase 1.2: ドメイン切替 | 完了（welfare.zaitaku-navi.com） |
| **次: DNS・ホスティング設定** | **手動作業待ち** |

### ビルド結果（2026-04-12 時点）
- 詳細ページ: **40,100枚** (`office/*.html`)
- 都道府県ページ: 47枚
- 市区町村ページ: 1,510枚
- sitemap.xml: 41,570 URL
- 横浜市都筑区 放デイ: 72件（ベンチマーク一致）

---

## リポジトリ構成

```
shogaifukushi-navi/
├── README.md                         ← 本ファイル
├── .gitignore
├── config/
│   └── site_config_shogaifukushi.json  # build_site.py 用設定（マスターコピー）
├── scripts/
│   ├── download_wam_csv.py             # WAM NET CSV 一括ダウンロード
│   ├── analyze_csv.py                  # CSV構造解析・充填率分析
│   └── convert_shogai_data.py          # CSV → build_site.py 用JSON変換
├── data_sources/
│   ├── wam_net/                        # ダウンロードCSV（gitignore）
│   └── reports/                        # 分析レポートJSON
│       ├── download_manifest.json
│       ├── column_schema.json
│       ├── column_fill_rate.csv
│       ├── service_type_counts.csv
│       └── analysis_detail.json
├── data/                               # 変換後JSON（gitignore）
│   ├── shogaifukushi.json              # 全件正規化
│   ├── shogaifukushi_children.json     # Phase 1 対象のみ
│   ├── shogaifukushi_build.json        # build_site.py 互換形式
│   ├── shogaifukushi_service_counts.json
│   ├── shogaifukushi_pref_counts.json
│   ├── shogaifukushi_multifunction.json
│   └── shogaifukushi_stats.json
├── site_shogaifukushi/                 # ビルド成果物（gitignore）
└── docs/
    ├── research-and-design.md          # Phase 0: 調査・設計
    ├── raw_files_manifest.md           # CSV取得一覧
    ├── column_schema_summary.md        # カラム構造
    ├── mvp_field_policy.md             # MVPフィールド判定
    ├── normalization_notes.md          # 正規化方針
    ├── analysis_summary.md             # 分析結論
    ├── sample_normalized_record.json
    ├── service_type_mapping_draft.json
    ├── phase1_build_report.md          # Phase 1 テストビルド完了
    ├── phase1_1_cleanup_report.md      # Phase 1.1 医療残骸除去
    └── domain_switch_welfare_report.md # ドメイン切替完了
```

### リポジトリ外の依存

build_site.py 本体とテキストテンプレートは `~/projects/MyPython/` 配下にある:

```
MyPython/
├── build_site.py                       # 静的サイトジェネレータ本体（共通）
├── site_config_shogaifukushi.json      # コピー版（build実行時にこちらを参照）
├── region_texts_shogaifukushi.json     # 都道府県ページ用テキスト
└── page_texts_shogaifukushi.json       # 固定ページテキスト
```

`site_config_shogaifukushi.json` は本リポジトリの `config/` とMyPython の両方に存在する。マスターは `shogaifukushi-navi/config/`、同期が必要。

---

## データソース

**WAM NET 障害福祉サービス等情報公表オープンデータ**
- URL: https://www.wam.go.jp/content/wamnet/pcpub/top/sfkopendata/
- 形式: ZIP → CSV (UTF-8 BOM付き, 29列)
- 更新頻度: 年2回（3月末・9月末）
- ライセンス: 営利・非営利問わず利用可能（利用報告推奨）
- 全27種別・約194,529件
- 全件に緯度経度を含む（ジオコーディング不要）

---

## ビルド手順

### 初回セットアップ

```bash
# 1. WAM NET CSV 全27種別ダウンロード
cd ~/projects/shogaifukushi-navi
python scripts/download_wam_csv.py

# 2. CSV構造解析（初回のみ・品質確認用）
python scripts/analyze_csv.py

# 3. build_site 互換 JSON に変換（Phase 1 対象のみ）
python scripts/convert_shogai_data.py --phase1-only
```

### 日常のビルド

```bash
# データ更新後、再生成
cd ~/projects/shogaifukushi-navi
python scripts/convert_shogai_data.py --phase1-only

# 静的サイト生成
cd ~/projects/MyPython
python build_site.py --config site_config_shogaifukushi.json --skip-neutrality
```

### ローカルプレビュー

```bash
cd ~/projects/shogaifukushi-navi/site_shogaifukushi
python -m http.server 8000
# http://localhost:8000/
```

---

## Phase 1 対象サービス

| コード | サービス種別 | 件数 | URL slug |
|--------|------------|------|----------|
| 65 | 放課後等デイサービス | 24,156 | `after-school-day-service` |
| 63 | 児童発達支援 | 16,247 | `child-development-support` |

- 多機能型（両サービスを提供）: 12,793事業所
- ユニーク事業所番号: 27,307
- 対象: 全国47都道府県

---

## アーキテクチャ方針

1. **build_site.py は既存資産を流用**
   - 訪問診療ナビ・訪問看護ナビと同じ共通エンジンを使用
   - 本体への変更はゼロ（Phase 1）→ config駆動の最小追加（Phase 1.1）
2. **データはアダプター方式で吸収**
   - convert_shogai_data.py が WAM CSV を build_site.py 互換フラット JSON に変換
   - 多機能型検出は変換時の二段階処理で付与
3. **サービス単位ページ**
   - 詳細ページは office_number + service_type の複合キー
   - 多機能型は各サービスで別ページを生成し、併設情報を相互にリンク

---

## 残タスク（公開前）

### リポジトリ内で対応可能
- [ ] Phase 2: サービス種別バッジ・営業時間・定員表示
- [ ] 就労支援・住まい・相談支援の追加
- [ ] `/guide/` 配下のガイド記事作成

### 手動作業（公開時に必要）
- [ ] `welfare.zaitaku-navi.com` の DNS設定 (CNAME)
- [ ] ホスティング選定（GitHub Pages / Cloudflare Pages / Vercel）
- [ ] Cloudflare SSL/TLS 設定
- [ ] Search Console 登録 + sitemap送信
- [ ] GA4 プロパティ作成・測定ID設定
- [ ] 特商法・運営者情報の実値更新
- [ ] OGP画像の品質確認

詳細は [docs/domain_switch_welfare_report.md](docs/domain_switch_welfare_report.md) の「手動作業が必要な項目」を参照。

---

## 関連ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [docs/research-and-design.md](docs/research-and-design.md) | 初期調査・設計判断（Phase 0） |
| [docs/analysis_summary.md](docs/analysis_summary.md) | CSV品質分析結論 |
| [docs/mvp_field_policy.md](docs/mvp_field_policy.md) | MVPフィールド判定 |
| [docs/normalization_notes.md](docs/normalization_notes.md) | 正規化ルール |
| [docs/phase1_build_report.md](docs/phase1_build_report.md) | Phase 1 テストビルド完了 |
| [docs/phase1_1_cleanup_report.md](docs/phase1_1_cleanup_report.md) | Phase 1.1 医療残骸除去 |
| [docs/domain_switch_welfare_report.md](docs/domain_switch_welfare_report.md) | Phase 1.2 ドメイン切替 |

---

## ライセンス・帰属

- データ: WAM NET 障害福祉サービス等情報公表オープンデータ（独立行政法人福祉医療機構）
- 運営: MDX株式会社
- 姉妹サイト: 在宅クリニックナビ / 訪問看護ナビ
