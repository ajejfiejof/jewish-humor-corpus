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


# --- COMMAND 8: ANECDOTE EXTRACTOR ---

CURATED_ANECDOTES = [
    {
        "title": "The Moon in the Barrel",
        "category": "Wise Men of Chełm (Folk Folly)",
        "anecdote": "One night, the elders of Chełm looked into a water barrel and saw the moon reflecting in the water. Terrified that the moon had fallen from the heavens, they hastily hammered a lid onto the barrel to preserve the town's light. The next morning, when they eagerly pried off the lid, the moon was gone. 'Alas!' cried the town sage. 'Someone has broken in and stolen our moon!'",
        "analysis": "Exemplifies Chełmite hyper-literalism and pseudo-deductive reasoning: attempting to solve a non-existent dilemma through meticulous logic that results in absolute absurdity."
    },
    {
        "title": "The Soup and the Coat",
        "category": "Hershele of Ostropol (Trickster Satire)",
        "anecdote": "Hershele arrived at a wealthy man's banquet in threadbare rags, and the servants turned him away into the street. Hershele went home, borrowed an opulent velvet coat, and returned. This time, the host bowed and seated him at the head of the table. When the rich chicken soup was served, Hershele dipped the embroidered sleeve of his coat into the bowl. 'Hershele, what are you doing?' gasped the host. Hershele smiled: 'I am feeding my coat! When I came as myself, you shut the door. It was the coat you invited to dinner, so the coat shall eat.'",
        "analysis": "Classic anti-establishment subversive wit: the trickster uses absurd literalism to expose superficial social hierarchy and unearned wealth."
    },
    {
        "title": "The Two Men Down the Chimney",
        "category": "Talmudic & Rabbinic Paradox",
        "anecdote": "A student asks a rabbi to test his logical acumen. The rabbi asks: 'Two men fall down a chimney. One comes out with a clean face; the other comes out with soot on his face. Which one washes his face?'\nThe student answers: 'The dirty one, of course!'\n'Wrong,' says the rabbi. 'The dirty one looks at the clean one and assumes his own face is clean. The clean one looks at the dirty one, assumes his face is dirty, and washes.'\nThe student says: 'Ah! So the clean one washes!'\n'Wrong again,' sighs the rabbi. 'How can two men fall down the same chimney and one be clean while the other is dirty? Your whole question is flawed.'",
        "analysis": "Illustrates Talmudic pilpul deconstruction: challenging the implicit premise of a query rather than accepting a false dichotomy."
    },
    {
        "title": "Rabinovich and the Leaflets",
        "category": "Soviet Dissident Anekdoty",
        "anecdote": "During the height of Soviet repression, Rabinovich is arrested in Red Square handing out leaflets to passersby. At the KGB headquarters, the interrogator confiscates the leaflets and discovers they are completely blank sheets of paper. 'What is the meaning of this?' yells the officer. 'Why are these blank?' Rabinovich shrugs: 'What is there to write? Everyone already knows.'",
        "analysis": "Subversive political irony: weaponizing silence and universal shared despair against a totalitarian censorship apparatus."
    },
    {
        "title": "The Telegram from Paris",
        "category": "Assimilation & Code-Switching",
        "anecdote": "A young immigrant who made a fortune in New York travels to Paris and sends a one-word telegram to his traditional mother back in Brooklyn: 'START!'\nThe mother panics, calls the entire family, and weeps. The rabbi comes over and asks, 'Why are you weeping?'\nThe mother sobs: 'He writes START! That means: Start worrying!'",
        "analysis": "Reflects the quintessential cultural reflex of fatalistic anticipation: assuming that any change of status or departure portends inevitable misfortune."
    }
]

def cmd_anecdote(topic=None):
    import random
    candidates = CURATED_ANECDOTES
    if topic:
        t_clean = topic.lower()
        candidates = [a for a in CURATED_ANECDOTES if t_clean in a['title'].lower() or t_clean in a['category'].lower()]
        if not candidates:
            candidates = CURATED_ANECDOTES
            
    chosen = random.choice(candidates)
    
    out = Text()
    out.append(f"CATEGORY: {chosen['category']}\n\n", style="bold cyan")
    out.append(f"\"{chosen['anecdote']}\"\n\n", style="white")
    out.append(f"FOLKLORIC & COMEDIC ANALYSIS:\n", style="bold yellow")
    out.append(f"• {chosen['analysis']}\n", style="dim white")
    
    console.print(Panel(out, title=f"[bold green]Corpus Anecdote: {chosen['title']}[/bold green]", box=box.ROUNDED))

# --- COMMAND 9: INTERACTIVE EXPLORER ---
def cmd_explore():
    console.print(Panel("[bold cyan]Corpus of Jewish Humor: Interactive Explorer TUI[/bold cyan]\nType 'catalog', 'archetypes', 'analyze', 'anecdote', 'search <kw>', 'read <title>', or 'quit'", box=box.ROUNDED))
    while True:
        try:
            cmd_input = console.input("[bold yellow]jhc>[/bold yellow] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting explorer.[/dim]")
            break
            
        if not cmd_input or cmd_input in ["exit", "quit", "q"]:
            console.print("[dim]Goodbye![/dim]")
            break
            
        parts = cmd_input.split(maxsplit=1)
        sub = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        if sub == "catalog":
            cmd_catalog()
        elif sub == "archetypes":
            cmd_archetypes()
        elif sub == "analyze":
            cmd_analyze()
        elif sub == "anecdote":
            cmd_anecdote(arg)
        elif sub == "search":
            if arg:
                cmd_search(arg)
            else:
                console.print("[red]Usage: search <query>[/red]")
        elif sub == "read":
            if arg:
                cmd_read(arg)
            else:
                console.print("[red]Usage: read <article_title_or_id>[/red]")
        elif sub == "harvest":
            if arg:
                cmd_harvest(arg)
            else:
                console.print("[red]Usage: harvest <wikipedia_title>[/red]")
        else:
            console.print(f"[red]Unknown command: '{sub}'. Try: catalog, archetypes, search, analyze, anecdote, read, harvest, quit[/red]")

# --- COMMAND 10: EMBEDDED WEB SERVER ---
def cmd_serve(port=8000):
    import http.server
    import socketserver
    import urllib.parse
    
    class CorpusHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            params = urllib.parse.parse_qs(parsed.query)
            
            if path == "/api/catalog":
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT id, title, word_count, char_count, summary FROM articles ORDER BY word_count DESC")
                data = [{"id": r[0], "title": r[1], "words": r[2], "chars": r[3], "summary": r[4]} for r in cur.fetchall()]
                conn.close()
                self.send_json(data)
            elif path == "/api/archetypes":
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT term, category, definition FROM archetypes_and_terms")
                data = [{"term": r[0], "category": r[1], "definition": r[2]} for r in cur.fetchall()]
                conn.close()
                self.send_json(data)
            elif path == "/api/search":
                q = params.get("q", [""])[0]
                conn = get_connection()
                ensure_fts(conn)
                cur = conn.cursor()
                clean_q = q.strip()
                if clean_q and " " not in clean_q and not clean_q.endswith("*"):
                    clean_q = f"{clean_q}*"
                try:
                    cur.execute("""
                        SELECT article_title, section_title, bm25(sections_fts) as rank,
                               snippet(sections_fts, 2, '<mark>', '</mark>', '...', 25)
                        FROM sections_fts WHERE sections_fts MATCH ? ORDER BY rank ASC LIMIT 8
                    """, (clean_q,))
                    results = [{"article": r[0], "section": r[1], "rank": r[2], "snippet": r[3]} for r in cur.fetchall()]
                except Exception:
                    results = []
                conn.close()
                self.send_json(results)
            elif path == "/api/jokes":
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT id, title, tradition, category, setup, punchline, analysis, source FROM jokes_and_anecdotes")
                data = [{"id": r[0], "title": r[1], "tradition": r[2], "category": r[3], "setup": r[4], "punchline": r[5], "analysis": r[6], "source": r[7]} for r in cur.fetchall()]
                conn.close()
                self.send_json(data)
            elif path == "/api/anecdote":
                import random
                self.send_json(random.choice(CURATED_ANECDOTES))
            elif path in ["/", "/index.html"]:
                self.send_html()
            else:
                self.send_error(404, "Endpoint not found")
                
        def send_json(self, payload):
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(encoded)
            
        def send_html(self):
            html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Corpus of Jewish Humor Explorer</title>
    <style>
        :root { --bg: #0a0e17; --panel: #111827; --card: #172033; --border: #1f2937; --cyan: #38bdf8; --amber: #fbbf24; --text: #f9fafb; --muted: #9ca3af; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 24px; }
        .header { border-bottom: 2px solid var(--border); padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }
        h1 { margin: 0; font-size: 24px; color: var(--cyan); }
        .search-box { margin-bottom: 24px; }
        input { width: 100%; max-width: 600px; padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border); background: var(--panel); color: var(--text); font-size: 16px; outline: none; }
        input:focus { border-color: var(--cyan); }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
        .card { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
        .card h3 { margin-top: 0; color: var(--amber); }
        mark { background: rgba(56, 189, 248, 0.3); color: #fff; padding: 2px 4px; border-radius: 4px; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; background: rgba(56, 189, 248, 0.15); color: var(--cyan); font-size: 12px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>Corpus of Jewish Humor</h1>
            <p style="margin: 4px 0 0; color: var(--muted); font-size: 14px;">Interactive NLP &amp; Folklore Research Portal</p>
        </div>
        <div class="badge">SQLite FTS5 Online</div>
    </div>
    <div class="search-box">
        <input type="text" id="query" placeholder="Search FTS5 corpus (e.g. 'soup', 'logic', 'rabbi', 'theatre')..." onkeyup="if(event.key === 'Enter') doSearch()">
    </div>
    <div id="results" class="grid"></div>
    <script>
        async function doSearch() {
            const q = document.getElementById('query').value;
            const res = await fetch('/api/search?q=' + encodeURIComponent(q));
            const data = await res.json();
            const container = document.getElementById('results');
            if (data.length === 0) {
                container.innerHTML = '<p style="color:var(--muted)">No matches found.</p>';
                return;
            }
            container.innerHTML = data.map(item => `
                <div class="card">
                    <span class="badge">${item.article}</span>
                    <h3 style="margin: 8px 0;">${item.section}</h3>
                    <p style="color: var(--muted); font-size: 14px; line-height: 1.4;">"...${item.snippet}..."</p>
                </div>
            `).join('');
        }
        // Initial load with popular topic
        document.getElementById('query').value = 'soup';
        doSearch();
    </script>
</body>
</html>'''
            encoded = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    console.print(f"[bold green]Starting Corpus Web Explorer on http://localhost:{port}[/bold green]")
    console.print("[dim]Press Ctrl+C to stop the server.[/dim]")
    with socketserver.TCPServer(("", port), CorpusHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            console.print("\n[dim]Server stopped.[/dim]")


# --- COMMAND: JOKES DATABASE EXPLORER ---
def cmd_jokes(tradition=None, category=None, search=None):
    conn = get_connection()
    cur = conn.cursor()
    
    query = "SELECT id, title, tradition, category, setup, punchline, analysis, source FROM jokes_and_anecdotes WHERE 1=1"
    params = []
    
    if tradition:
        query += " AND tradition LIKE ?"
        params.append(f"%{tradition}%")
    if category:
        query += " AND category LIKE ?"
        params.append(f"%{category}%")
    if search:
        query += " AND (setup LIKE ? OR punchline LIKE ? OR title LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        
    query += " ORDER BY id ASC"
    cur.execute(query, params)
    jokes = cur.fetchall()
    
    if not jokes:
        console.print("[bold red]No jokes found matching the criteria.[/bold red]")
        conn.close()
        return
        
    console.print(Panel(f"[bold cyan]Corpus of Jewish Humor: Primary Joke & Anecdote Registry[/bold cyan]\nDisplaying [bold green]{len(jokes)}[/bold green] curated primary jokes across historical traditions.", box=box.ROUNDED))
    
    for jid, title, trad, cat, setup, punch, analysis, src in jokes:
        p_text = Text()
        p_text.append(f"TRADITION: {trad}  •  CATEGORY: {cat}\n\n", style="bold yellow")
        p_text.append(f"SETUP:\n", style="bold cyan")
        p_text.append(f"{setup}\n\n", style="white")
        p_text.append(f"PUNCHLINE:\n", style="bold green")
        p_text.append(f"{punch}\n\n", style="bold white")
        p_text.append(f"COMEDIC & CULTURAL MECHANICS:\n", style="bold magenta")
        p_text.append(f"• {analysis}\n\n", style="dim white")
        p_text.append(f"SOURCE: {src}", style="italic dim")
        
        console.print(Panel(p_text, title=f"[bold white]Joke #{jid}: {title}[/bold white]", box=box.ROUNDED, border_style="cyan"))
        
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

    
    
    p_jokes = subparsers.add_parser("jokes", help="Browse structured primary jokes and anecdotes with setup/punchline analysis")
    p_jokes.add_argument("--tradition", help="Filter by tradition (e.g. Ashkenazi, Sephardic, Soviet, Talmudic, Borscht)")
    p_jokes.add_argument("--category", help="Filter by category (e.g. 'Folk Folly', 'Trickster', 'Political')")
    p_jokes.add_argument("--search", help="Search text in setups or punchlines")
    p_anecdote = subparsers.add_parser("anecdote", help="Display a curated folk joke, parable, or anecdote")
    p_anecdote.add_argument("--topic", help="Filter anecdotes by keyword or category")
    
    subparsers.add_parser("explore", help="Launch interactive TUI corpus explorer")
    
    p_serve = subparsers.add_parser("serve", help="Launch embedded local web explorer & REST API")
    p_serve.add_argument("--port", type=int, default=8000, help="Port to serve on (default: 8000)")

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
    
    
    elif args.command == "jokes":
        cmd_jokes(tradition=args.tradition, category=args.category, search=args.search)
    elif args.command == "anecdote":
        cmd_anecdote(topic=args.topic)
    elif args.command == "explore":
        cmd_explore()
    elif args.command == "serve":
        cmd_serve(port=args.port)
    else:
        cmd_catalog()

if __name__ == "__main__":
    main()
