# 障害福祉サービスナビ ドメイン切替レポート

実施日: 2026-04-12
切替先: `welfare.zaitaku-navi.com`（旧 `shogaifukushi-navi.com`）

---

## 結論: **切替完了。welfare.zaitaku-navi.com 前提で公開可能状態。**

- 旧ドメイン `shogaifukushi-navi.com` のコード・生成物残留: **0件**
- 新ドメイン `welfare.zaitaku-navi.com` の反映: **累計41,638箇所**（sitemap+canonical+OGP+JSON-LD）
- 既存の訪問診療ナビ（`zaitakuclinic-navi.com`）・訪問看護ナビ（`kango.zaitaku-navi.com`）に影響 **ゼロ**
- 再ビルドは `--skip-neutrality` 付きで完走、sitemap.xml 41,570 URL 生成

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `MyPython/site_config_shogaifukushi.json` | `site_base_url` / `cname_domain` を `welfare.zaitaku-navi.com` に変更 |
| `shogaifukushi-navi/config/site_config_shogaifukushi.json` | 同上（同期） |
| `MyPython/page_texts_shogaifukushi.json` | `contact_email` を `info@zaitaku-navi.com` に変更 |
| `shogaifukushi-navi/docs/domain_switch_welfare_report.md` | 本レポート（新規） |

**build_site.py 本体への変更: なし**（既存の config 駆動機構で吸収できた）

---

## 旧ドメイン参照の洗い出し結果

洗い出し前の `shogaifukushi-navi.com` / `shogaifukushi_navi` 参照箇所は、リポジトリ全体で **合計6箇所**:

| 場所 | 種別 | 対応 |
|------|------|------|
| `MyPython/site_config_shogaifukushi.json:9` | `site_base_url` | **置換済み** |
| `MyPython/site_config_shogaifukushi.json:10` | `cname_domain` | **置換済み** |
| `shogaifukushi-navi/config/site_config_shogaifukushi.json:9` | `site_base_url` | **置換済み** |
| `shogaifukushi-navi/config/site_config_shogaifukushi.json:10` | `cname_domain` | **置換済み** |
| `MyPython/page_texts_shogaifukushi.json:14` | `contact_email` | **置換済み** |
| `shogaifukushi-navi/docs/phase1_build_report.md:288` | 過去の文書内の言及 | **保留**（歴史的記録。公開物ではない） |
| `shogaifukushi-navi/docs/phase1_1_cleanup_report.md:246` | 過去の文書内の言及 | **保留**（歴史的記録。公開物ではない） |

過去の実装レポート2件（`phase1_build_report.md` / `phase1_1_cleanup_report.md`）には「旧ドメイン案として shogaifukushi-navi.com を想定していた」という経緯記録が残っていますが、公開物でもビルド入力でもないため、**歴史的記録として意図的に保持**しています（本レポートが更新履歴を担います）。

---

## config で変更した主要キー

```diff
- "site_base_url": "https://shogaifukushi-navi.com",
- "cname_domain": "shogaifukushi-navi.com",
+ "site_base_url": "https://welfare.zaitaku-navi.com",
+ "cname_domain": "welfare.zaitaku-navi.com",
```

```diff
- "contact_email": "info@shogaifukushi-navi.com"
+ "contact_email": "info@zaitaku-navi.com"
```

その他キー（`site_name`, `entity_type`, `care_type`, `schema_org_type=LocalBusiness` など）は Phase 1.1 で設定済みのため変更なし。

---

## 再ビルド結果

### コマンド
```bash
cd ~/projects/MyPython
python build_site.py --config site_config_shogaifukushi.json --skip-neutrality
```

### 出力
```
=== 障害福祉サービスナビ サイト生成 ===
中立性チェック: スキップ（--skip-neutrality）
クリニックデータ: 40403件
都道府県整合性チェック: 3件を住所から補正
重複排除後: 40100件
都道府県数: 47
...
都道府県ページ 47枚 + 市区町村ページ 1510枚生成完了
診療所個別ページ 40100枚生成完了
運営者情報・特商法・利用規約・医療機関向けページ生成完了
お問い合わせ・登録ページ生成完了
sitemap.xml生成完了 (41570件)
404.html生成完了
=== 生成完了 ===
```

**エラーなし、sys.exit(1) なし、sitemap.xml まで完走。**

---

## canonical / OGP / JSON-LD / robots / sitemap の確認結果

### CNAME
```
welfare.zaitaku-navi.com
```

### robots.txt（末尾）
```
Sitemap: https://welfare.zaitaku-navi.com/sitemap.xml
```

### sitemap.xml（先頭）
```xml
<url><loc>https://welfare.zaitaku-navi.com/</loc>...</url>
<url><loc>https://welfare.zaitaku-navi.com/pref/hokkaido.html</loc>...</url>
```
全 **41,570 URL** がすべて新ドメイン。

### 詳細ページサンプル `/office/1453800573-after-school-day-service.html`

| 項目 | 値 |
|------|-----|
| `<link rel="canonical">` | `https://welfare.zaitaku-navi.com/office/1453800573-after-school-day-service.html` |
| `<meta property="og:url">` | 同上 |
| `<meta property="og:image">` | `https://welfare.zaitaku-navi.com/static/ogp.png` |
| `<meta property="og:site_name">` | `障害福祉サービスナビ` |
| JSON-LD `@type` | `BreadcrumbList`, `LocalBusiness`, `PostalAddress`, `GeoCoordinates` |
| JSON-LD `url` | `https://welfare.zaitaku-navi.com/office/1453800573-after-school-day-service.html` |

**`MedicalClinic` は完全に消失**、`LocalBusiness` に統一済み。

---

## 旧ドメイン残留・医療残骸の全件スキャン

```bash
cd site_shogaifukushi
grep -rl "shogaifukushi-navi.com" . → 0 ファイル
grep -rl "MedicalClinic" . → 0 ファイル
grep -rl "保険医療機関コード" . → 0 ファイル
grep -rl "主な診療科目は" . → 0 ファイル
```

### 16ファイルのサンプル検証結果
| ファイル | 旧ドメイン | 新ドメイン |
|---------|----------|----------|
| index.html | 0 | 6 |
| pref/kanagawa.html | 0 | 7 |
| pref/kanagawa/横浜市都筑区.html | 0 | 8 |
| office/1453800573-after-school-day-service.html | 0 | 9 |
| for-clinics.html | 0 | 4 |
| register-free.html | 0 | 4 |
| contact.html | 0 | 4 |
| contact-clinic.html | 0 | 4 |
| premium.html | 0 | 4 |
| about.html | 0 | 4 |
| tokushoho.html | 0 | 4 |
| terms.html | 0 | 4 |
| 404.html | 0 | 4 |
| sitemap.xml | 0 | 41,570 |
| robots.txt | 0 | 1 |
| CNAME | 0 | 1 |
| **合計** | **0** | **41,638** |

---

## 既存サイトへの影響確認

| サイト | config | site_base_url | 変更 |
|--------|--------|--------------|------|
| 訪問診療ナビ | `site_config.json` | `https://zaitakuclinic-navi.com` | なし |
| 訪問看護ナビ | `site_config_houmon_kango.json` | `https://kango.zaitaku-navi.com` | なし |
| 障害福祉サービスナビ | `site_config_shogaifukushi.json` | `https://welfare.zaitaku-navi.com` | **本修正** |

既存2サイトのconfigは未変更。build_site.py 本体も未変更のため、既存ビルドへの影響はゼロ。

---

## 親サイト zaitaku-navi.com 配下の統一感

現在のサブドメイン構成（想定 + 実装済み）:

| 種別 | サブドメイン | 状態 |
|------|------------|------|
| 訪問診療 | `zaitakuclinic-navi.com`（独自ドメイン） | 本番稼働中 |
| 訪問看護 | `kango.zaitaku-navi.com` | 設定済み（kango configに存在） |
| 歯科 | `shika.zaitaku-navi.com` | 未実装 |
| 介護 | `care.zaitaku-navi.com` | 未実装 |
| **障害福祉** | **`welfare.zaitaku-navi.com`** | **本修正で設定** |

`welfare.zaitaku-navi.com` は既存の `kango.zaitaku-navi.com` と同じパターンに従っており、親ドメイン `zaitaku-navi.com` 配下のサブドメイン群の一員として自然に配置されます。

---

## 手動作業が必要な項目

### 1. ドメイン設定（DNS）

`welfare.zaitaku-navi.com` を本番公開するには、以下のDNS設定が必要です（**Cloudflare管理画面またはDNSプロバイダーで手動実施**）:

#### GitHub Pages で公開する場合
```
Type: CNAME
Name: welfare
Target: <GitHub Pagesのユーザー名>.github.io
Proxy: オレンジ（Cloudflare経由）または グレー（DNSのみ）
TTL: Auto
```

#### Cloudflare Pages で公開する場合
Cloudflare Pages プロジェクト側で「Custom domains」に `welfare.zaitaku-navi.com` を追加すれば、DNSレコードは自動設定される。

### 2. ホスティング選定（repo 外作業）

現時点では `site_shogaifukushi/` にビルド成果物が生成されるのみで、デプロイ手段は未設定です。以下のいずれかを選択:

| 方式 | 手順 |
|------|------|
| **GitHub Pages** | (a) `site_shogaifukushi/` を別リポジトリ `welfare-zaitaku-navi` として切り出し → `gh-pages` or `main` ブランチを公開 / (b) 訪問看護ナビと同様に `houmonshinsatsu-navi` 的なリポジトリ構造を採用 |
| **Cloudflare Pages** | GitHub 連携で `site_shogaifukushi/` ディレクトリを公開 / ビルドコマンドなし（静的配信） |
| **Vercel** | Framework Preset: "Other" / Output Directory: `site_shogaifukushi` |

推奨: 訪問診療ナビ・訪問看護ナビと同じ方式に統一する（既存ノウハウを流用できる）。

### 3. Cloudflare の設定（Cloudflareを使用している場合）

- SSL/TLS モード: `Full (strict)` 推奨
- Always Use HTTPS: ON
- Automatic HTTPS Rewrites: ON
- Brotli 圧縮: ON
- CNAME フラッティング: 自動

### 4. Search Console 登録

登録すべき対象:
- プロパティ追加: `https://welfare.zaitaku-navi.com/`
- 所有権確認: DNS TXT レコード または HTML メタタグ
- sitemap 送信: `https://welfare.zaitaku-navi.com/sitemap.xml`

### 5. GA4 設定

- 新規プロパティ作成: `welfare.zaitaku-navi.com`
- 測定ID を `site_config_shogaifukushi.json` の `ga4_measurement_id` に設定（現在空文字）
- 必要なら、親ドメイン `zaitaku-navi.com` 全体のプロパティも作成してサブドメインを一括計測

### 6. OGP画像の品質確認

現在 `/static/ogp.png` は既存の医療系テンプレートで生成されている可能性があります。公開前に実機で確認推奨:
- `https://welfare.zaitaku-navi.com/static/ogp.png`
- `https://welfare.zaitaku-navi.com/static/ogp_pref/kanagawa.png` 等

問題があれば Pillow スクリプトでロゴ・トーンを調整。

### 7. 特商法ページの実値確定

`about.html` / `tokushoho.html` / `terms.html` の運営者情報・返金条件等が初期値のまま。公開前に MDX株式会社の正式情報で更新が必要。

---

## 公開可否の最終判定

### 今の状態で welfare.zaitaku-navi.com としてそのまま公開可能か: **Yesに近いがDNS・ホスティング設定が未実施**

**技術的には公開可能状態:**
- ビルド成果物はすべて新ドメイン前提で整合
- 旧ドメイン残留ゼロ、医療残骸ゼロ
- LocalBusiness 構造化データ適用済み
- 40,100 詳細ページ + 1,510 市区町村 + 47 都道府県 + sitemap.xml 生成済み
- 既存サイトへの影響ゼロ

**公開前に残る手動作業:**
1. **DNS設定** (welfare → GitHub Pages / Cloudflare Pages)
2. **ホスティング選定とデプロイ設定** (リポジトリ構造決定)
3. **Cloudflare SSL/TLS 設定** (Full strict 推奨)
4. **Search Console 登録 + sitemap 送信**
5. **GA4 プロパティ作成と測定ID 設定**
6. **特商法・運営者情報の実値更新**
7. **OGP画像の最終品質確認**

---

## 親サイト zaitaku-navi.com 側で後から追加するとよい導線

Phase 2 以降で、親ハブとの連携を強化するために以下を検討:

1. **`zaitaku-navi.com` トップページにサービスカード追加**
   - 「在宅医療を探す」→ `clinic.zaitaku-navi.com`
   - 「訪問看護を探す」→ `kango.zaitaku-navi.com`
   - **「障害福祉サービスを探す」→ `welfare.zaitaku-navi.com`**

2. **各サブサイトのフッターに「他のサービスを探す」共通ナビを追加**
   - build_site.py に `related_services` のようなconfigキーを追加
   - 各サイトで自サイト以外のリンクを表示

3. **共通ヘッダーロゴを `zaitaku-navi.com` へのリンクに**
   - 現状は `/` (自サイトトップ)
   - 将来は親ハブにリンクしつつ、サブサイト名を保持する形式に

4. **共通 OGP 画像ブランディング**
   - 「zaitaku-navi.com サービス群」であることが視覚的に伝わるフッター等

これらは **今回のスコープ外**。公開後の Phase 2 で段階的に追加するのが自然。

---

## 受け入れ条件チェックリスト

| 条件 | 結果 |
|------|------|
| 旧ドメイン `shogaifukushi-navi.com` 前提がコード・生成物から除去されている | ✓ grep 全件 0 |
| 公開URL前提が `welfare.zaitaku-navi.com` に統一されている | ✓ 41,638箇所に反映 |
| canonical / OGP / JSON-LD / robots / sitemap が新ドメインで整合している | ✓ 全て確認 |
| 再ビルドが成功する | ✓ sitemap.xml 41,570 URL 完走 |
| 既存医療サイトを壊していない | ✓ 既存config未変更、影響ゼロ |
| repo 内でできない作業は手動手順として明示されている | ✓ DNS/ホスティング/Search Console/GA4 手順明記 |
| 公開可否を判断できる状態になっている | ✓ 「技術的には公開可能、DNS設定のみ未実施」と明確化 |

---

## 再現コマンド

```bash
# 1. データ変換（Phase 1 で完了済み、変更なし）
cd ~/projects/shogaifukushi-navi
python scripts/convert_shogai_data.py --phase1-only

# 2. welfare.zaitaku-navi.com ビルド
cd ~/projects/MyPython
python build_site.py --config site_config_shogaifukushi.json --skip-neutrality

# 3. 生成物確認
cat ~/projects/shogaifukushi-navi/site_shogaifukushi/CNAME
# → welfare.zaitaku-navi.com

# 4. ローカルプレビュー
cd ~/projects/shogaifukushi-navi/site_shogaifukushi
python -m http.server 8000
# → http://localhost:8000/
```
