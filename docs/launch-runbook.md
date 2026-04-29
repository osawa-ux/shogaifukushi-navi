# shogaifukushi-navi ローンチ Runbook

`https://welfare.zaitaku-navi.com/` を公開するための手順書。

## 前提状態（2026-04-24 確認）

| 項目 | 状態 |
|---|---|
| GitHub repo | `osawa-ux/shogaifukushi-navi`（**private**、master branch） |
| 対象コンテンツ | `site_shogaifukushi/` 配下（Phase 1 テストビルド 40,100 ページ生成済み） |
| CNAME ファイル | `site_shogaifukushi/CNAME = welfare.zaitaku-navi.com` ✓ |
| site_config 反映 | `site_base_url` / `cname_domain` = `welfare.zaitaku-navi.com` 全 41,638 箇所反映済み（[docs/domain_switch_welfare_report.md](domain_switch_welfare_report.md) 参照） |
| GitHub Pages | **未有効化** |
| DNS (Cloudflare) | **welfare サブドメイン未設定** |
| 既存パターン参照 | `houmonshinsatsu-navi` / `kyotaku-navi`（両方 public, gh-pages branch） |

## アーキテクチャ

```
GitHub repo (shogaifukushi-navi, gh-pages branch)
      ↓ GitHub Pages 配信 (osawa-ux.github.io)
      ↓
Cloudflare DNS (zaitaku-navi.com zone)
      CNAME: welfare → osawa-ux.github.io (DNS only)
      ↓
https://welfare.zaitaku-navi.com/
      ↑ SSL: GitHub Pages 側で Let's Encrypt 自動発行
```

## ローンチ手順

### Step 1: repo を public にする

```bash
gh repo edit osawa-ux/shogaifukushi-navi --visibility public --accept-visibility-change-consequences
```

**事前確認事項**:
- commit 履歴に秘密情報を含んでいないか
- data/ に含まれる WAM NET オープンデータ（公開データ）のみであること

### Step 2: `gh-pages` branch を作成し、`site_shogaifukushi/` 内容を配置

```bash
cd ~/projects/shogaifukushi-navi

# 現在の branch 状況確認
git status -sb
# master が clean であることを確認

# site_shogaifukushi/ の中身のみ含む gh-pages branch を作成
git checkout --orphan gh-pages
git rm -rf . 2>/dev/null
git checkout master -- site_shogaifukushi
# site_shogaifukushi の中身を root に移動
git mv site_shogaifukushi/* .
rmdir site_shogaifukushi

# 確認
cat CNAME       # welfare.zaitaku-navi.com
ls index.html   # トップページ
ls pref/        # 都道府県ページ

# commit + push
git add -A
git commit -m "publish: initial gh-pages from site_shogaifukushi/ (Phase 1 放デイ・児発 40,100ページ)"
git push -u origin gh-pages

# master に戻る
git checkout master
```

### Step 3: GitHub Pages を有効化

```bash
gh api -X POST repos/osawa-ux/shogaifukushi-navi/pages \
  -f 'source[branch]=gh-pages' \
  -f 'source[path]=/' \
  --header 'Accept: application/vnd.github+json'

gh api repos/osawa-ux/shogaifukushi-navi/pages --jq '{url:.html_url, branch:.source.branch, path:.source.path, cname:.cname}'
```

期待値:
```json
{
  "url": "https://welfare.zaitaku-navi.com/",
  "branch": "gh-pages",
  "path": "/",
  "cname": "welfare.zaitaku-navi.com"
}
```

### Step 4: Cloudflare DNS に CNAME 追加

```
Type   : CNAME
Name   : welfare
Target : osawa-ux.github.io
Proxy  : DNS only (グレー雲)
TTL    : Auto
```

または API:

```bash
export CF_API_TOKEN='<token>'
ZONE_ID=$(curl -s "https://api.cloudflare.com/client/v4/zones?name=zaitaku-navi.com" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  | jq -r '.result[0].id')

curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"CNAME","name":"welfare","content":"osawa-ux.github.io","ttl":1,"proxied":false}'
```

### Step 5: DNS 伝播確認 + HTTPS 強制化

```bash
nslookup welfare.zaitaku-navi.com 8.8.8.8
# → osawa-ux.github.io に解決されれば OK

# Let's Encrypt 発行待ち (Pages 側で自動、数分〜1時間)
curl -sI "https://welfare.zaitaku-navi.com/" | head -5

# HTTPS 強制
gh api -X PUT repos/osawa-ux/shogaifukushi-navi/pages \
  -f 'https_enforced=true' \
  --header 'Accept: application/vnd.github+json'
```

### Step 6: Data Integrity Check（必須）

```bash
# Phase 1 で 40,100 ページ生成済み
# 代表ページ確認
curl -s "https://welfare.zaitaku-navi.com/" | grep -o "放課後\|児童発達" | head -3
curl -s "https://welfare.zaitaku-navi.com/pref/hokkaido.html" | head -20

# sitemap の件数確認
curl -s "https://welfare.zaitaku-navi.com/sitemap.xml" | grep -c '<url>'
# 期待値: 40,100+ URL
```

### Step 7: SEO 登録

- Google Search Console: `https://welfare.zaitaku-navi.com` プロパティ追加
- sitemap 送信: `https://welfare.zaitaku-navi.com/sitemap.xml`
- 親ハブ `zaitaku-navi.com` 関連サブドメインとして紐付け

### Step 8: alldomain-check の config 更新

```bash
# ~/.claude/skills/alldomain-check/config.json
# { "host": "welfare.zaitaku-navi.com", "expected": "not-launched" }
# ↓
# { "host": "welfare.zaitaku-navi.com", "expected": "200" }
```

## ロールバック

同 shika と同じ（DNS削除 → Pages無効化 → repo private化）。

## 判断ポイント（人間確認）

- [ ] repo を public にして問題ない（WAM NETオープンデータのみ、秘密情報なし）
- [ ] Phase 1（放課後等デイ・児童発達支援）で先行公開してよい（Phase 2 は後続で追加？）
- [ ] `site_shogaifukushi/` を `gh-pages` branch に移す方式でよい
- [ ] Cloudflare Proxy: DNS only で OK

## 特記事項

- 「障害福祉サービスナビ」の旧ドメイン `shogaifukushi-navi.com` は既に放棄（docs/domain_switch_welfare_report.md 参照）
- 新ドメイン `welfare.zaitaku-navi.com` は 41,638 箇所で反映済み
- 本 Runbook は [domain_switch_welfare_report.md](domain_switch_welfare_report.md) の「手動作業が必要な項目」セクションに対応する実行手順

## 参考: 既存成功例の設定

| 項目 | houmonshinsatsu-navi | kyotaku-navi |
|---|---|---|
| visibility | public | public |
| Pages source | gh-pages branch, / | gh-pages branch, / |
| CNAME | zaitakuclinic-navi.com | care.zaitaku-navi.com |
