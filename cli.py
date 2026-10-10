#!/usr/bin/env python3
"""
Corpus of Jewish Humor: Advanced CLI & Computational Linguistics Suite
Provides full-text FTS5 search, automated MediaWiki harvesting, stylometric
analysis, interactive article reading, and data export.
"""

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich import box

console = Console()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "jewish_humor.db")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")

YIDDISH_LOANWORDS = {
    "alrightnik", "baleboste", "balabusta", "blintz", "boychik", "briss", "bubbe", "bubbeh",
    "bupkis", "bobske", "challah", "cholent", "chutzpah", "daven", "dreidel", "feh",
    "farklempt", "fleishig", "gelt", "glezel", "gonif", "goy", "goyishe", "golem",
    "hamantasch", "kaddish", "kashrut", "kibbitz", "kibitz", "kichel", "kishkes", "klutz",
    "knish", "kosher", "kreplach", "kugel", "kvell", "kvetch", "latke", "litvak",
    "lox", "macher", "mame", "mamzer", "maven", "mazel", "mensch", "meshugge",
    "meshuggener", "milchig", "minyan", "mishmash", "mispocheh", "mishpocha", "mitzvah",
    "naches", "narr", "narishkeit", "nebbish", "nebish", "nosh", "nu", "nudnik",
    "oy", "oyvey", "pareve", "plotz", "poper", "pupik", "putz", "rebbe",
    "schlub", "schlock", "schlep", "schlepper", "schmaltz", "schmaltzy", "schmeer",
    "schmo", "schmooze", "schmuck", "schmutz", "schnorrer", "schnoz", "schtick",
    "shtick", "schlemiel", "shlemiel", "schlimazel", "shlimazel", "shadchan", "shanda",
    "shnorrer", "shabbat", "sheitel", "shiksa", "shmutz", "shnorrer", "shtetl",
    "tchotchke", "traif", "tref", "tsuris", "tummler", "tzaddik", "verklempt",
    "yenta", "yarmulke", "yeshiva", "yid", "yiddish", "yiddishe", "zaftig"
}

def get_connection():
    if not os.path.exists(DB_PATH):
        console.print(f"[bold red]Error: Database file not found at {DB_PATH}[/bold red]")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def ensure_fts(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sections_fts'")
    if not cur.fetchone():
        cur.execute("""
            CREATE VIRTUAL TABLE sections_fts USING fts5(
                article_title,
                section_title,
                content,
                content_rowid UNINDEXED
            )
        """)
        cur.execute("""
            SELECT s.id, a.title, s.section_title, s.content
            FROM sections s
            JOIN articles a ON s.article_id = a.id
        """)
        for sid, atitle, stitle, content in cur.fetchall():
            cur.execute("""
                INSERT INTO sections_fts (content_rowid, article_title, section_title, content)
                VALUES (?, ?, ?, ?)
            """, (sid, atitle, stitle, content))
        conn.commit()

# --- COMMAND 1: CATALOG ---
def cmd_catalog():
    conn = get_connection()
    ensure_fts(conn)
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.title, count(s.id) as num_sec, a.word_count, a.char_count, a.harvested_at
        FROM articles a
        LEFT JOIN sections s ON a.id = s.article_id
        GROUP BY a.id
        ORDER BY a.word_count DESC
    """)
    
    table = Table(title="[bold yellow]Corpus Document Catalog & Storage Index[/bold yellow]", box=box.ROUNDED)
    table.add_column("ID", justify="center", style="dim", width=4)
    table.add_column("Article Title", style="bold white", width=32)
    table.add_column("Sections", justify="right", style="cyan", width=10)
    table.add_column("Words", justify="right", style="green", width=10)
    table.add_column("Characters", justify="right", style="dim", width=12)
    table.add_column("Harvest Date", style="dim", width=20)
    
    total_w, total_c = 0, 0
    for aid, title, nsec, wc, cc, ts in cur.fetchall():
        ts_str = ts.replace("T", " ").replace("Z", "") if ts else "N/A"
        table.add_row(str(aid), title, str(nsec), f"{wc:,}", f"{cc:,}", ts_str)
        total_w += wc
        total_c += cc
        
    console.print(table)
    console.print(f"[dim]Total indexed volume: [bold green]{total_w:,}[/bold green] words ({total_c:,} characters) across {len(table.rows)} documents.[/dim]\n")
    conn.close()

# --- COMMAND 2: ARCHETYPES ---
def cmd_archetypes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT term, category, definition, source_article FROM archetypes_and_terms ORDER BY id ASC")
    
    table = Table(title="[bold magenta]Core Cultural Archetypes & Comic Roles[/bold magenta]", box=box.ROUNDED)
    table.add_column("Archetype / Concept", style="bold cyan", width=22)
    table.add_column("Classification", style="yellow", width=18)
    table.add_column("Cultural Mechanics & Function", style="white")
    table.add_column("Source", style="dim", width=18)
    
    for term, cat, defn, src in cur.fetchall():
        table.add_row(term, cat, defn, src)
        
    console.print(table)
    conn.close()

# --- COMMAND 3: FULL-TEXT SEARCH (FTS5 + BM25) ---
def cmd_search(query, limit=5):
    conn = get_connection()
    ensure_fts(conn)
    cur = conn.cursor()
    
    clean_q = query.strip()
    # Support prefix wildcard if single word without quotes
    if " " not in clean_q and not clean_q.endswith("*") and not clean_q.startswith('"'):
        fts_query = f"{clean_q}*"
    else:
        fts_query = clean_q
        
    try:
        cur.execute("""
            SELECT article_title, section_title, bm25(sections_fts) as rank,
                   snippet(sections_fts, 2, '[bold cyan]', '[/bold cyan]', '...', 22) as snip
            FROM sections_fts
            WHERE sections_fts MATCH ?
            ORDER BY rank ASC
            LIMIT ?
        """, (fts_query, limit))
        results = cur.fetchall()
    except Exception as e:
        # Fallback to standard LIKE if FTS syntax fails
        cur.execute("""
            SELECT a.title, s.section_title, 0.0 as rank, s.content
            FROM sections s
            JOIN articles a ON s.article_id = a.id
            WHERE s.content LIKE ? OR s.section_title LIKE ?
            LIMIT ?
        """, (f"%{clean_q}%", f"%{clean_q}%", limit))
        results = [(r[0], r[1], r[2], " ".join(r[3].split()[:40]) + "...") for r in cur.fetchall()]

    if not results:
        console.print(f"[bold red]No matches found for query:[/bold red] '{query}'")
        conn.close()
        return

    out = Text()
    out.append(f"FTS5 Query: '{query}' ({len(results)} relevant sections matched):\n", style="bold green")
    for atitle, stitle, rank, snip in results:
        out.append(f"\n• {atitle} → [bold yellow]{stitle}[/bold yellow] [dim](BM25 score: {rank:.2f})[/dim]\n")
        out.append(f"  \"{snip}\"\n")

    console.print(Panel(out, title="[bold green]SQLite FTS5 Semantic Search Engine[/bold green]", box=box.ROUNDED, border_style="green"))
    conn.close()

# --- COMMAND 4: AUTOMATED MEDIAWIKI HARVESTER ---
def cmd_harvest(topic):
    headers = {'User-Agent': 'JewishHumorCorpusResearchBot/1.0 (academic; https://github.com/ajejfiejof)'}
    console.print(f"[cyan]Harvesting Wikipedia article:[/cyan] [bold white]{topic}[/bold white]...")
    
    params = {"action": "query", "prop": "extracts", "titles": topic, "explaintext": "1", "format": "json"}
    url = f"https://en.wikipedia.org/w/api.php?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            pages = data.get("query", {}).get("pages", {})
            page_data = None
            for pid, pdata in pages.items():
                if pid != "-1":
                    page_data = pdata
                    break
    except Exception as e:
        console.print(f"[bold red]Network error fetching {topic}:[/bold red] {e}")
        return

    if not page_data or not page_data.get("extract"):
        console.print(f"[bold red]Could not find or extract article for:[/bold red] '{topic}'")
        return

    real_title = page_data.get("title", topic)
    text = page_data.get("extract", "")
    wc = len(text.split())
    cc = len(text)
    summary = text.split("==")[0].strip()
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Save raw JSON
    os.makedirs(RAW_DIR, exist_ok=True)
    slug = re.sub(r"[^a-z0-9_]+", "", real_title.lower().replace(" ", "_"))
    raw_path = os.path.join(RAW_DIR, f"{slug}.json")
    with open(raw_path, "w") as f:
        json.dump({
            "title": real_title,
            "full_text": text,
            "word_count": wc,
            "char_count": cc,
            "harvested_at": ts
        }, f, indent=2)

    # Ingest into SQLite
    conn = get_connection()
    ensure_fts(conn)
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO articles (title, word_count, char_count, summary, full_text, harvested_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (real_title, wc, cc, summary, text, ts))
    art_id = cur.lastrowid

    # Parse sections
    sec_matches = list(re.finditer(r"(={2,4})\s*([^=]+)\s*\1", text))
    indexed_sec_count = 0
    for i, match in enumerate(sec_matches):
        sec_level = len(match.group(1))
        sec_title = match.group(2).strip()
        start = match.end()
        end = sec_matches[i+1].start() if i + 1 < len(sec_matches) else len(text)
        sec_content = text[start:end].strip()
        sec_wc = len(sec_content.split())
        
        if sec_content and sec_title.lower() not in ["references", "further reading", "see also", "notes", "bibliography", "external links"]:
            cur.execute("""
                INSERT INTO sections (article_id, section_title, section_level, content, word_count)
                VALUES (?, ?, ?, ?, ?)
            """, (art_id, sec_title, sec_level, sec_content, sec_wc))
            sec_rowid = cur.lastrowid
            
            # Index into FTS5
            cur.execute("""
                INSERT INTO sections_fts (content_rowid, article_title, section_title, content)
                VALUES (?, ?, ?, ?)
            """, (sec_rowid, real_title, sec_title, sec_content))
            indexed_sec_count += 1

    conn.commit()
    conn.close()

    panel_text = Text()
    panel_text.append(f"Article: [bold white]{real_title}[/bold white]\n", style="green")
    panel_text.append(f"Word Count: [bold green]{wc:,}[/bold green] words ({cc:,} chars)\n")
    panel_text.append(f"Sections Indexed into FTS5: [bold cyan]{indexed_sec_count}[/bold cyan]\n")
    panel_text.append(f"Raw Archive: [dim]{raw_path}[/dim]\n")
    console.print(Panel(panel_text, title="[bold green]Harvest & Ingest Successful[/bold green]", box=box.ROUNDED))

# --- COMMAND 5: COMPUTATIONAL STYLOMETRY & LEXICAL ANALYSIS ---
def cmd_analyze():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, full_text, word_count FROM articles ORDER BY word_count DESC")
    articles = cur.fetchall()
    
    table = Table(title="[bold cyan]Computational Stylometry & Comedic Linguistics Profile[/bold cyan]", box=box.ROUNDED)
    table.add_column("Document", style="bold white", width=28)
    table.add_column("Words", justify="right", style="dim", width=8)
    table.add_column("Yiddish Terms", justify="right", style="cyan", width=14)
    table.add_column("Yiddish / 1k", justify="right", style="bold cyan", width=13)
    table.add_column("Questions / 1k", justify="right", style="yellow", width=15)
    table.add_column("Exclam. / 1k", justify="right", style="magenta", width=13)
    table.add_column("Lexical TTR", justify="right", style="green", width=12)
    
    total_yiddish_found = Counter()
    
    for aid, title, text, wc in articles:
        if not wc or wc == 0:
            continue
        words_raw = re.findall(r"\b[a-zA-Z]+\b", text.lower())
        total_tokens = len(words_raw)
        vocab = set(words_raw)
        ttr = (len(vocab) / total_tokens) if total_tokens else 0.0
        
        # Count Yiddish terms
        y_count = sum(1 for w in words_raw if w in YIDDISH_LOANWORDS)
        y_rate = (y_count / total_tokens * 1000.0) if total_tokens else 0.0
        
        # Punctuation counts
        q_count = text.count("?")
        q_rate = (q_count / wc * 1000.0)
        
        e_count = text.count("!")
        e_rate = (e_count / wc * 1000.0)
        
        for w in words_raw:
            if w in YIDDISH_LOANWORDS:
                total_yiddish_found[w] += 1
                
        table.add_row(
            title, f"{wc:,}", str(y_count), f"{y_rate:.1f}",
            f"{q_rate:.1f}", f"{e_rate:.1f}", f"{ttr:.3f}"
        )
        
    console.print(table)
    
    # Top loanwords breakdown
    top_y = total_yiddish_found.most_common(12)
    top_str = ", ".join([f"[bold cyan]{w}[/bold cyan] ({c})" for w, c in top_y])
    
    insights = Text()
    insights.append("LINGUISTIC & STYLOMETRIC HIGHLIGHTS:\n", style="bold yellow")
    insights.append(f"• Top Yiddish Comedic Vocabulary in Corpus: {top_str}\n")
    insights.append("• Rhetorical Question Rate: High question rates reflect Talmudic dialectic syntax and counter-questioning habits.\n")
    insights.append("• Type-Token Ratio (TTR): Measures lexical diversity across historical and folkloric source texts.\n")
    console.print(Panel(insights, title="[bold yellow]Corpus Insights[/bold yellow]", box=box.ROUNDED))
    conn.close()

# --- COMMAND 6: READ ARTICLE ---
def cmd_read(target):
    conn = get_connection()
    cur = conn.cursor()
    if target.isdigit():
        cur.execute("SELECT id, title, full_text FROM articles WHERE id = ?", (int(target),))
    else:
        cur.execute("SELECT id, title, full_text FROM articles WHERE title LIKE ? LIMIT 1", (f"%{target}%",))
        
    row = cur.fetchone()
    if not row:
        console.print(f"[bold red]Article not found matching:[/bold red] '{target}'")
        conn.close()
        return
        
    aid, title, full_text = row
    console.print(Panel(f"[bold cyan]{title}[/bold cyan] (Document ID #{aid})", box=box.HEAVY))
    
    # Display sections
    cur.execute("SELECT section_title, content, word_count FROM sections WHERE article_id = ? ORDER BY id ASC", (aid,))
    sections = cur.fetchall()
    
    for stitle, content, wc in sections[:4]:
        console.print(f"\n[bold yellow]═══ {stitle} ({wc} words) ═══[/bold yellow]")
        console.print(content[:600] + ("..." if len(content) > 600 else ""))
        
    if len(sections) > 4:
        console.print(f"\n[dim]... and {len(sections) - 4} more sections. (Total words: {len(full_text.split()):,})[/dim]")
    conn.close()

# --- COMMAND 7: EXPORT CORPUS ---
def cmd_export(fmt="json", output_path=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.title, s.section_title, s.section_level, s.word_count, s.content
        FROM sections s
        JOIN articles a ON s.article_id = a.id
        ORDER BY a.id, s.id
    """)
    rows = cur.fetchall()
    
    if not output_path:
        output_path = os.path.join(BASE_DIR, f"corpus_export.{fmt}")
        
    if fmt == "json":
        data = [
            {"article_id": r[0], "article": r[1], "section": r[2], "level": r[3], "words": r[4], "content": r[5]}
            for r in rows
        ]
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
    elif fmt == "csv":
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["article_id", "article", "section", "level", "words", "content"])
            writer.writerows(rows)
    elif fmt == "markdown":
        with open(output_path, "w") as f:
            f.write("# Corpus of Jewish Humor: Full Export Dossier\n\n")
            current_art = None
            for r in rows:
                if r[1] != current_art:
                    current_art = r[1]
                    f.write(f"\n# {current_art}\n\n")
                f.write(f"## {r[2]} ({r[4]} words)\n\n{r[5]}\n\n---\n")

    console.print(f"[bold green]Corpus successfully exported:[/bold green] [white]{output_path}[/white] ({len(rows)} sections in {fmt.upper()})")
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Corpus of Jewish Humor: Research & NLP Suite")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("catalog", help="List all indexed documents, sections, and metrics")
    subparsers.add_parser("archetypes", help="Display cultural archetypes and comic tropes")
    
    p_search = subparsers.add_parser("search", help="Perform FTS5 full-text search with BM25 ranking")
    p_search.add_argument("query", help="Search query (supports wildcards, e.g. 'soup*', 'logic*')")
    p_search.add_argument("--limit", type=int, default=5, help="Maximum matches to return")
    
    p_harvest = subparsers.add_parser("harvest", help="Fetch and ingest a new Wikipedia article into DB & FTS5")
    p_harvest.add_argument("topic", help="Wikipedia article title (e.g. 'Sholem Aleichem')")
    
    subparsers.add_parser("analyze", help="Run computational stylometry & comedic linguistics analysis")
    
    p_read = subparsers.add_parser("read", help="Read article sections with rich formatting")
    p_read.add_argument("target", help="Article ID or title substring")
    
    p_export = subparsers.add_parser("export", help="Export corpus to JSON, CSV, or Markdown")
    p_export.add_argument("--format", choices=["json", "csv", "markdown"], default="json")
    p_export.add_argument("--output", help="Custom output file path")

    args = parser.parse_args()
    if args.command == "catalog":
        cmd_catalog()
    elif args.command == "archetypes":
        cmd_archetypes()
    elif args.command == "search":
        cmd_search(args.query, limit=args.limit)
    elif args.command == "harvest":
        cmd_harvest(args.topic)
    elif args.command == "analyze":
        cmd_analyze()
    elif args.command == "read":
        cmd_read(args.target)
    elif args.command == "export":
        cmd_export(fmt=args.format, output_path=args.output)
    else:
        cmd_catalog()

if __name__ == "__main__":
    main()
