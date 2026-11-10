#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
储能科学与技术 (energystorage-journal.com) -> RSS 生成器
数据来源：站点 sitemap-articles-*.xml（文章 URL + lastmod）+ 每篇文章的 citation_* 元信息
输出：feed.xml（RSS 2.0，最新 N 篇，按 online_date 倒序）
"""
import re, sys, gzip, time, html
import urllib.request
from datetime import datetime, timezone, timedelta
from xml.sax.saxutils import escape

SITE = "https://www.energystorage-journal.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CST = timezone(timedelta(hours=8))


def get(url, tries=3, timeout=30):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


def sitemap_urls():
    idx = get(f"{SITE}/sitemap.xml")
    return re.findall(r"<loc>([^<]*sitemap-articles-[0-9]+\.xml)</loc>", idx)


def collect_articles():
    """返回 [(url, lastmod_dt)]，只保留中文版文章页"""
    out = []
    for sm in sitemap_urls():
        xml = get(sm)
        for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
            loc = re.search(r"<loc>(.*?)</loc>", block)
            lm = re.search(r"<lastmod>(.*?)</lastmod>", block)
            if not loc:
                continue
            u = html.unescape(loc.group(1))
            if "/zh/article/doi/" not in u:
                continue
            dt = None
            if lm:
                try:
                    dt = datetime.fromisoformat(lm.group(1))
                except ValueError:
                    dt = None
            out.append((u, dt))
    out.sort(key=lambda t: (t[1] or datetime.min.replace(tzinfo=CST)), reverse=True)
    return out


META = lambda name, page: (re.search(
    r'<meta[^>]*name="%s"[^>]*content="([^"]*)"' % name, page) or [None, ""])[1]


def clean(text):
    """元信息里的标题常被转义成 Li/CF&lt;sub&gt;x&lt;/sub&gt;，这里还原为纯文本"""
    if not text:
        return ""
    t = html.unescape(text)          # &lt;sub&gt; -> <sub>
    t = re.sub(r"<[^>]+>", "", t)    # 去掉 <sub>/<sup>/<italic> 等标签
    t = html.unescape(t)             # 处理二次转义的实体
    return re.sub(r"\s+", " ", t).strip()


def parse_article(url):
    page = get(url)
    title = clean(META("citation_title", page)) or clean(
        (re.search(r"<title>([^<]*)</title>", page) or [None, ""])[1])
    desc = clean(META("description", page))
    doi = clean(META("citation_doi", page))
    online = clean(META("citation_online_date", page))
    authors = [clean(a) for a in
               re.findall(r'<meta[^>]*name="citation_author"[^>]*content="([^"]*)"', page)]
    vol, iss = clean(META("citation_volume", page)), clean(META("citation_issue", page))
    pages = clean(META("citation_firstpage", page)), clean(META("citation_lastpage", page))
    dt = None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m"):
        try:
            dt = datetime.strptime(online.strip(), fmt).replace(tzinfo=CST)
            break
        except Exception:
            pass
    return dict(title=(title or "").strip() or "（无标题）", link=url, doi=doi,
                desc=desc.strip(), authors=authors, online=online, dt=dt,
                vol=vol, issue=iss, pages=pages)


def build(items, out="feed.xml", limit=30, self_url=""):
    now = datetime.now(CST)
    buf = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" '
           'xmlns:dc="http://purl.org/dc/elements/1.1/" '
           'xmlns:content="http://purl.org/rss/1.0/modules/content/">',
           "<channel>",
           f"<title>储能科学与技术 — 最新发布</title>",
           f"<link>{SITE}/zh/issues/</link>",
           f"<description>《储能科学与技术》最新在线发布文章（标题、作者、摘要、DOI），"
           f"由站点 sitemap 与文章页元信息生成，共 {len(items)} 条。</description>",
           "<language>zh-cn</language>",
           f"<lastBuildDate>{now.strftime('%a, %d %b %Y %H:%M:%S %z')}</lastBuildDate>",
           "<ttl>360</ttl>",
           "<generator>energystorage-rss</generator>"]
    if self_url:
        buf.append(f'<atom:link href="{escape(self_url)}" rel="self" type="application/rss+xml" />')
    for it in items[:limit]:
        dt = it["dt"] or now
        info = []
        if it["authors"]:
            info.append("作者：" + "、".join(it["authors"][:8]) + ("等" if len(it["authors"]) > 8 else ""))
        if it["doi"]:
            info.append(f"DOI：{it['doi']}")
        if it["online"]:
            info.append(f"在线日期：{it['online']}")
        body = escape(it["desc"]) + ("\n\n" + escape(" | ".join(info)) if info else "")
        buf += ["<item>",
                f"<title>{escape(it['title'])}</title>",
                f"<link>{escape(it['link'])}</link>",
                f"<guid isPermaLink=\"true\">{escape(it['link'])}</guid>",
                f"<description>{body}</description>",
                f"<pubDate>{dt.strftime('%a, %d %b %Y %H:%M:%S %z')}</pubDate>"]
        if it["authors"]:
            buf.append(f"<dc:creator>{escape(it['authors'][0])}</dc:creator>")
        if it["doi"]:
            buf.append(f"<category>{escape(it['doi'])}</category>")
        buf.append("</item>")
    buf += ["</channel>", "</rss>"]
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(buf))
    return out


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    arts = collect_articles()
    print(f"sitemap 中中文文章 URL 共 {len(arts)} 条，开始抓取前 {limit} 篇元信息…", file=sys.stderr)
    items = []
    for u, _ in arts[:limit]:
        try:
            items.append(parse_article(u))
        except Exception as e:
            print("跳过", u, e, file=sys.stderr)
    # 按在线日期重排（sitemap lastmod 有时批量刷新，不代表真实发布时间）
    items.sort(key=lambda x: (x["dt"] or datetime.min.replace(tzinfo=CST)), reverse=True)
    print(build(items, "feed.xml", limit=limit), "已生成，条目数", len(items), file=sys.stderr)
