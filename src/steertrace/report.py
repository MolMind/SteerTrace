"""Human-readable, offline HTML reviews; evidence identifiers stay in JSON."""
from __future__ import annotations

from html import escape
from importlib.resources import files
from pathlib import Path

from .storage import TraceError
from .validation import load_run, validate

OWNERSHIP = {
    "human_proposed": "你提出的要求或判断",
    "ai_proposed_human_selected": "AI 提议，你作了选择",
    "authorization_only": "你同意继续",
    "unknown": "暂时无法判断是谁提出的",
}
KINDS = {"goal": "确定目标", "question": "提出疑问", "critique": "纠正方案",
         "constraint": "划定范围", "tradeoff": "明确取舍", "selection": "选择方案",
         "authorization": "同意继续", "stop": "叫停工作"}


def h(value: str) -> str:
    return escape(value, quote=True)


def icon(name: str) -> str:
    # Only bundled Tabler assets are used; analysis strings never select markup.
    svg = files("steertrace").joinpath(f"assets/tabler-{name}.svg").read_text(encoding="utf-8")
    return svg.replace('<svg', '<svg class="icon-tabler" aria-hidden="true" focusable="false"', 1)


def paragraph(value: str, cls: str = "") -> str:
    return f'<p class="{cls}">{h(value)}</p>'


def quotes(refs: list[dict]) -> str:
    return "".join(f'<blockquote>{h(ref["quote"])}</blockquote>' for ref in refs)


def render(run: Path, analysis: dict) -> tuple[str, dict]:
    result = validate(run, analysis)
    if not result["valid"]:
        raise TraceError("Report refused: " + "; ".join(result["errors"]))
    _, conversation, documents = load_run(run)
    order = {m["id"]: i for i, m in enumerate(conversation["messages"])}
    docs = {d["id"]: d for d in documents}
    events = sorted(analysis["events"], key=lambda e: min(order[r["message_id"]] for r in e["user_evidence"]))
    anchors = {e["id"]: f"decision-{i}" for i, e in enumerate(events, 1)}
    numbers = {e["id"]: i for i, e in enumerate(events, 1)}
    criticisms = analysis.get("criticisms", [])
    flagged = {eid for c in criticisms for eid in c["event_ids"]}
    review = analysis.get("review", {})

    def links(ids: list[str]) -> str:
        return '<div class="related">当时的判断：' + " · ".join(
            f'<a href="#{anchors[eid]}">第 {numbers[eid]} 步</a>' for eid in ids) + '</div>'

    blocks = []
    for c in criticisms:
        blocks.append('<article class="criticism"><span class="eyebrow">值得关注的判断</span>'
                      f'<h3>{h(c["title"])}</h3>' +
                      ('<p class="inference">这是基于上下文的推测，需要你核对。</p>' if c["basis"] == "inference" else '') +
                      '<dl>' + ''.join(f'<div><dt>{label}</dt><dd>{h(c[field])}</dd></div>' for label, field in
                                      (("判断偏差", "problem"), ("潜在影响", "consequence"), ("思维强化方向", "better_move"))) +
                      '</dl>' + links(c["event_ids"]) + '</article>')
    criticism_html = ''.join(blocks) or paragraph("当前记录未呈现有充分依据的判断偏差。", "empty")
    strengths = review.get("keep_doing", [])
    strength_html = '<ul class="strengths">' + ''.join(f'<li>{h(s)}</li>' for s in strengths) + '</ul>' if strengths else ''
    cards = []
    for i, e in enumerate(events, 1):
        context = ''
        for label, field in (("AI 当时的提议", "before"), ("AI 随后的回应", "after")):
            if e.get(field):
                context += f'<h4>{label}</h4>' + quotes(e[field])
        document_html = ''
        for link in e.get("document_links", []):
            doc = docs[link["doc_id"]]
            status = "文档中的结果记录，未在本次重新测试" if link["verification"] == "reported_result" else "文档中写下了这些内容"
            document_html += f'<h4>{h(Path(doc["path"]).name)}</h4>' + paragraph(status, "muted") + f'<blockquote>{h(link["quote"])}</blockquote>'
        if document_html:
            context += '<h4>方案里怎么写</h4>' + document_html
        elif context:
            context += paragraph("这一步没有找到可以对应的文档内容。", "muted")
        category = "attention" if e["id"] in flagged else "choice" if e["kind"] in {"tradeoff", "selection"} else "other"
        cards.append(f'<article class="event" id="decision-{i}" data-category="{category}" data-choice="{str(e["kind"] in {"tradeoff", "selection"}).lower()}">'
                     f'<div class="step" aria-hidden="true">{i:02}</div><div class="event-body">'
                     f'<div class="tags"><span>{KINDS[e["kind"]]}</span><span>{OWNERSHIP[e["ownership"]]}</span>' +
                     ('<span class="attention-tag">值得关注</span>' if e["id"] in flagged else '') + '</div>'
                     f'<h3>{h(e["summary"])}</h3><h4>你当时说</h4>' + quotes(e["user_evidence"]) +
                     '<h4>这意味着什么</h4>' + paragraph(e["interpretation"]) +
                     ('<p class="inference">这部分解释包含推测。</p>' if e["evidence_posture"] != "observed_submission" else '') +
                     '<details><summary>' + icon('chevron-right') + '<span>对话与文档</span></summary><div class="evidence-content">' + (context or paragraph("没有更多上下文。")) +
                     '</div></details></div></article>')
    event_html = ''.join(cards) or paragraph("没有记录可支持的关键判断。这不说明你没有思考。", "empty")
    rec_html = ''.join(f'<article class="next-action"><span class="action-number">{i:02}</span><div><h3>{h(r["text"])}</h3>'
                       '<h4>判断中的着力点</h4>' + paragraph(r["next_check"]) + links(r["event_ids"]) + '</div></article>'
                       for i, r in enumerate(analysis["recommendations"], 1)) or paragraph("当前记录未呈现需要额外强化的方向。", "empty")
    headline = review.get("headline", "回看你怎样推动了这次工作")
    summary = review.get("summary", "从你提出的要求、作出的选择和 AI 的回应，回看这次合作里值得保留和需要调整的做法。")
    css = files("steertrace").joinpath("assets/report.css").read_text(encoding="utf-8")
    js = files("steertrace").joinpath("assets/report.js").read_text(encoding="utf-8")
    icon_license = files("steertrace").joinpath("assets/tabler-LICENSE.txt").read_text(encoding="utf-8").replace("--", "—")
    html = f'''<!doctype html>
<!-- {icon_license} -->
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light"><meta name="referrer" content="no-referrer">
<title>SteerTrace — 判断与归因分析</title><style>{css}</style></head>
<body><a class="skip" href="#main">跳到报告正文</a>
<div class="reading-progress" aria-hidden="true"><span></span></div>
<header class="site-nav"><a class="brand" href="#top">Steer<span>Trace</span><small>判断分析</small></a>
<nav aria-label="报告目录"><a href="#guide">阅读导引</a><a href="#criticism">问题与归因</a><a href="#journey">判断过程</a><a href="#next">强化方向</a></nav>
<button id="print" class="quiet" hidden>{icon("file-type-pdf")} 保存为 PDF</button></header>
<main id="main"><header id="top" class="hero">
<div class="watermark" aria-hidden="true">SteerTrace</div>
<div class="eyebrow">HUMAN JUDGMENT / AI COLLABORATION</div>
<p class="hero-kicker">每一次选择，都值得看清。</p>
<h1>{h(headline)}</h1><p class="lead">{h(summary)}</p>
<div class="hero-actions"><a class="button primary" href="#overview">阅读本次分析 {icon("arrow-up-right")}</a><a class="button" href="#guide">如何阅读这份报告 {icon("chevron-down")}</a></div>
<p class="hero-note">基于指定对话与项目文档</p>
<a class="explore" href="#guide">向下探索 {icon("chevron-down")}</a></header>
<section id="guide" class="guide" aria-labelledby="guide-title"><div class="guide-pin">
<div class="section-heading"><span class="section-number">READING GUIDE</span><h2 id="guide-title">从一个判断，看到下一次改变。</h2></div>
<p class="muted guide-intro">沿着三个问题阅读。滚动或点击步骤，了解每一部分关注什么。</p>
<div class="guide-layout"><div class="guide-steps" role="group" aria-label="阅读导引步骤">
<button data-guide="0" aria-pressed="true"><span><strong>判断依据</strong><small>为什么接受，为什么否定？</small></span></button>
<button data-guide="1" aria-pressed="false"><span><strong>错误归因</strong><small>现象与原因之间，还缺什么？</small></span></button>
<button data-guide="2" aria-pressed="false"><span><strong>思维强化</strong><small>哪些思维方式值得强化？</small></span></button></div>
<div class="guide-stage">
<article data-guide-panel="0"><p class="eyebrow">01 / EVIDENCE</p><h3>判断的力量，<br>来自依据。</h3><p>回到当时的目标、原话与上下文，检查一个选择是由证据支撑，还是建立在尚未验证的假设上。</p><div class="thought-line"><span>提出假设</span><span aria-hidden="true">{icon("chevron-right")}</span><span>检查证据</span><span aria-hidden="true">{icon("chevron-right")}</span><span>作出判断</span></div><a href="#journey">查看本次判断过程 {icon("arrow-up-right")}</a></article>
<article data-guide-panel="1"><p class="eyebrow">02 / ATTRIBUTION</p><h3>现象与原因，<br>值得分开看。</h3><p>区分人的决策、AI 的建议与执行条件。检查哪些解释有证据，哪些只是可能；原因尚不明确时，保留不确定性。</p><div class="thought-line"><span>观察到的事实</span><span aria-hidden="true">{icon("arrows-diff")}</span><span>已经证实的原因</span></div><a href="#criticism">查看本次问题分析 {icon("arrow-up-right")}</a></article>
<article data-guide-panel="2"><p class="eyebrow">03 / NEXT DECISION</p><h3>让有效的思维，<br>在判断中延续。</h3><p>从这次选择中提炼值得延续的思维方式，让目标意识、证据意识与验证边界成为判断的支点。</p><div class="thought-line"><span>目标意识</span><span aria-hidden="true">{icon("plus")}</span><span>证据意识</span><span aria-hidden="true">{icon("plus")}</span><span>验证边界</span></div><a href="#next">查看强化方向 {icon("arrow-up-right")}</a></article>
<div class="guide-bottom"><span>阅读方法 · 非本次分析结论</span><span id="guide-count">01 / 03</span></div></div></div></div></section>
<div class="report-content">
<section id="overview"><div class="section-heading"><span class="section-number">01</span><h2>先看结论</h2></div>
<div class="overview-grid"><div class="stat"><strong>{len(events)}</strong><span>个关键判断</span></div><div class="stat"><strong>{len(criticisms)}</strong><span>处关键偏差</span></div><div class="stat"><strong>{len(analysis["recommendations"])}</strong><span>个强化方向</span></div></div>
{('<h3>值得延续的思维</h3>' + strength_html) if strength_html else ''}</section>
<section id="criticism"><div class="section-heading"><span class="section-number">02</span><h2>判断与归因</h2></div>{criticism_html}</section>
<section id="journey"><div class="section-heading"><span class="section-number">03</span><h2>回看判断过程</h2></div><p class="muted">按对话先后排列，顺序不代表前一句一定导致了后面的变化。</p>
<div class="toolbar" id="filters" hidden><label for="search">查找内容<input id="search" type="search" placeholder="输入目标、判断或原话" autocomplete="off"></label>
<div class="filter-buttons" role="group" aria-label="筛选判断"><button data-filter="all" aria-pressed="true">全部</button><button data-filter="attention" aria-pressed="false">值得关注</button><button data-filter="choice" aria-pressed="false">取舍与选择</button></div></div>
<p id="match-count" class="muted" aria-live="polite"></p><div class="timeline">{event_html}</div><p id="no-matches" class="empty" hidden>没有找到符合条件的判断，试试清空搜索或切换分类。</p></section>
<section id="next"><div class="section-heading"><span class="section-number">04</span><h2>思维强化方向</h2></div>{rec_html}</section>
<footer><a class="brand" href="#top">SteerTrace</a><span>看清判断依据，让下一次思考更清楚。</span><a href="#top">返回顶部 {icon("chevron-up")}</a></footer></div></main><script>{js}</script></body></html>'''
    return html, result
