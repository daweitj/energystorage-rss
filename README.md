# 储能科学与技术 —— 自动更新的 RSS 订阅源

把期刊站 [energystorage-journal.com](https://www.energystorage-journal.com/homeNav?lang=zh) 的最新在线发布文章，变成一个每天自动更新的 RSS 地址，订阅进任意阅读器。

> 这个站**没有官方 RSS**（`/rss`、`/feed`、`/atom.xml` 均 404）。本仓库用它的 `sitemap-articles-*.xml` 探测新文章，再读文章页 `<meta name="citation_*">` 拿到标题、作者、摘要、DOI、在线日期，生成标准 RSS 2.0。

## 订阅地址

```
https://daweitj.github.io/energystorage-rss/feed.xml
```

## 部署步骤

### 1. 建仓库
- Public 仓库（Private 用 Pages 需付费）

### 2. 上传文件
- `energystorage_rss.py`、`feed.xml`、`README.md`、`.github/workflows/update-feed.yml`

### 3. 开 Pages
- **Settings → Pages** → Source 选 **Deploy from a branch** → Branch `main`、Folder **/ (root)** → Save

### 4. 给 Action 写权限（关键，不然推送会失败）
- **Settings → Actions → General → Workflow permissions** → 选 **Read and write permissions** → Save

### 5. 手动跑一次验证
- **Actions** → `Update RSS feed` → **Run workflow**，日志应出现 `feed 校验通过，条目数 30，最新标题：…`

### 6. 之后自动运行
每天北京时间约 10:00 自动跑一次，有新文章才提交。改时间就编辑 `update-feed.yml` 的 `cron`，注意是 **UTC 时间**。

## 本地手动跑

```bash
python3 energystorage_rss.py 30      # 参数是条目数，默认 25
```

只依赖标准库，不需要 pip 装任何东西。

## 两个已知的坑

1. **GitHub 会自动停掉定时任务**：仓库连续 60 天无活动时，scheduled workflow 会被禁用。本仓库每次运行都会提交 `feed.xml`（算活动），正常不会触发；万一停了，去 Actions 点一次 `Run workflow` 即可恢复。
2. **`github.io` 在国内直连偏慢/不稳**：境外阅读器（Feedly、Inoreader 等）抓取不受影响；用国内阅读器直连才可能超时。

## 数据口径

- 条目顺序按 `citation_online_date` 倒序，**不是** sitemap 的 `lastmod`——站点批量重建时 lastmod 会被统一刷新，把旧文章顶成"最新"。
- `guid` 用文章永久 URL（`.../zh/article/doi/<DOI>/`），阅读器不会重复推送。
- `description` 内是完整中文摘要 + 作者 + DOI + 在线日期。
- 题录里的上下标在源站被转义了两次（`Li/CF&lt;sub&gt;x&lt;/sub&gt;`），脚本会还原成 `Li/CFx` 这类纯文本。
