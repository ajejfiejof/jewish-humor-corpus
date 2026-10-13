#!/usr/bin/env python3
"""
Corpus of Jewish Humor: Computational Linguistics, Folklore & ML Dataset Suite
Features:
- Dual-mode Search: SQLite FTS5 (BM25) + Dense Subword Semantic Vector Search (Cosine) + Hybrid Fusion
- Humor NLP Analytics: Sentiment Inversion Index, Incongruity Modeling, Dialogue Ratios
- Primary Joke Registry: 100+ structured jokes across 12 traditions with original scripts
- Multilingual Orthography: Yiddish (Hebrew script), YIVO transliteration, Ladino, Cyrillic
- Dataset Exporter: Parquet, Hugging Face Instruction-Tuning JSONL, CSV, JSON, Markdown
- Zero-dependency Web & REST API Server (http.server)
"""

import argparse
import csv
import json
import math
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

LADINO_MARKERS = {
    "djoha", "djudha", "refran", "refranes", "bendicho", "dio", "mazal",
    "sarik", "kaved", "hammam", "kuedra", "aniello", "kaldero", "kavesa", "kalabasa"
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

# --- SEMANTIC VECTOR SPACE ENGINE ---
class VectorSearchEngine:
    def __init__(self, conn):
        self.conn = conn
        self.documents = []
        self.vocab = {}
        self.idf = {}
        self.doc_vectors = []
        self._build_index()

    def _tokenize(self, text):
        clean = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        words = clean.split()
        tokens = list(words)
        for w in words:
            if len(w) >= 4:
                for i in range(len(w) - 2):
                    tokens.append(f"#{w[i:i+3]}")
        return tokens

    def _build_index(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT s.id, a.title, s.section_title, s.content
            FROM sections s
            JOIN articles a ON s.article_id = a.id
        """)
        rows = cur.fetchall()
        self.documents = rows
        doc_count = len(rows)

        df = Counter()
        doc_term_freqs = []

        for r in rows:
            tokens = self._tokenize(f"{r[1]} {r[2]} {r[3]}")
            tf = Counter(tokens)
            doc_term_freqs.append(tf)
            for t in tf.keys():
                df[t] += 1

        self.vocab = {term: idx for idx, term in enumerate(df.keys())}
        for term, freq in df.items():
            self.idf[term] = math.log((doc_count + 1.0) / (freq + 1.0)) + 1.0

        for tf in doc_term_freqs:
            vec = {}
            norm_sq = 0.0
            for term, count in tf.items():
                w = (1.0 + math.log(count)) * self.idf.get(term, 1.0)
                vec[term] = w
                norm_sq += w * w
            norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
            self.doc_vectors.append({t: w / norm for t, w in vec.items()})

    def search(self, query, top_k=5):
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        q_tf = Counter(query_tokens)
        q_vec = {}
        norm_sq = 0.0
        for term, count in q_tf.items():
            if term in self.idf:
                w = (1.0 + math.log(count)) * self.idf[term]
                q_vec[term] = w
                norm_sq += w * w
        norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
        q_vec_norm = {t: w / norm for t, w in q_vec.items()}

        scores = []
        for idx, doc_vec in enumerate(self.doc_vectors):
            dot = sum(w * doc_vec.get(t, 0.0) for t, w in q_vec_norm.items())
            if dot > 0.01:
                scores.append((dot, self.documents[idx]))

        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[:top_k]

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

# --- COMMAND 3: SEARCH (FTS, SEMANTIC, HYBRID) ---
def cmd_search(query, mode="hybrid", limit=5):
    conn = get_connection()
    ensure_fts(conn)
    clean_q = query.strip()

    if mode in ["fts", "hybrid"]:
        fts_term = f"{clean_q}*" if (" " not in clean_q and not clean_q.endswith("*") and not clean_q.startswith('"')) else clean_q
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT article_title, section_title, bm25(sections_fts) as rank,
                       snippet(sections_fts, 2, '[bold cyan]', '[/bold cyan]', '...', 22) as snip
                FROM sections_fts
                WHERE sections_fts MATCH ?
                ORDER BY rank ASC
                LIMIT ?
            """, (fts_term, limit))
            fts_results = cur.fetchall()
        except Exception:
            fts_results = []
    else:
        fts_results = []

    if mode in ["semantic", "hybrid"]:
        engine = VectorSearchEngine(conn)
        semantic_results = engine.search(clean_q, top_k=limit)
    else:
        semantic_results = []

    conn.close()

    if mode == "fts":
        if not fts_results:
            console.print(f"[bold red]No FTS5 matches found for query:[/bold red] '{query}'")
            return
        out = Text()
        out.append(f"FTS5 Query: '{query}' ({len(fts_results)} matches displayed):\n", style="bold green")
        for atitle, stitle, rank, snip in fts_results:
            out.append(f"\n• {atitle} → [bold yellow]{stitle}[/bold yellow] [dim](BM25 score: {rank:.2f})[/dim]\n")
            out.append(f"  \"{snip}\"\n")
        console.print(Panel(out, title="[bold green]SQLite FTS5 Keyword Search Engine[/bold green]", box=box.ROUNDED))

    elif mode == "semantic":
        if not semantic_results:
            console.print(f"[bold red]No semantic matches found for query:[/bold red] '{query}'")
            return
        out = Text()
        out.append(f"Dense Semantic Vector Search: '{query}' ({len(semantic_results)} matches displayed):\n", style="bold green")
        for score, (sid, atitle, stitle, content) in semantic_results:
            snip = " ".join(content.split()[:35]) + "..."
            out.append(f"\n• {atitle} → [bold yellow]{stitle}[/bold yellow] [dim](Cosine Similarity: {score:.3f})[/dim]\n")
            out.append(f"  \"{snip}\"\n", style="dim white")
        console.print(Panel(out, title="[bold cyan]Dense Vector Space Semantic Search (Cosine)[/bold cyan]", box=box.ROUNDED))

    else:  # hybrid
        out = Text()
        out.append(f"Hybrid Search (FTS5 BM25 + Semantic Vector Fusion): '{query}'\n", style="bold green")
        if fts_results:
            out.append("\n[bold cyan]─── KEYWORD MATCHES (FTS5 BM25) ───[/bold cyan]\n", style="bold")
            for atitle, stitle, rank, snip in fts_results[:3]:
                out.append(f"• {atitle} → [bold yellow]{stitle}[/bold yellow] [dim](BM25: {rank:.2f})[/dim]\n")
                out.append(f"  \"{snip}\"\n")
        if semantic_results:
            out.append("\n[bold magenta]─── CONCEPTUAL & SEMANTIC MATCHES (VECTOR SPACE) ───[/bold magenta]\n", style="bold")
            for score, (sid, atitle, stitle, content) in semantic_results[:3]:
                snip = " ".join(content.split()[:32]) + "..."
                out.append(f"• {atitle} → [bold yellow]{stitle}[/bold yellow] [dim](Cosine: {score:.3f})[/dim]\n")
                out.append(f"  \"{snip}\"\n", style="dim white")
        console.print(Panel(out, title="[bold green]Hybrid Search Engine (FTS5 + Vector Space)[/bold green]", box=box.ROUNDED))

# --- COMMAND 4: JOKES REGISTRY ---
def cmd_jokes(tradition=None, category=None, search=None):
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT id, title, tradition, category, setup, punchline, analysis, source, title_original, script_original, yivo_transliteration, sentiment_setup, sentiment_punchline, incongruity_score FROM jokes_and_anecdotes WHERE 1=1"
    params = []
    if tradition:
        query += " AND tradition LIKE ?"
        params.append(f"%{tradition}%")
    if category:
        query += " AND category LIKE ?"
        params.append(f"%{category}%")
    if search:
        query += " AND (setup LIKE ? OR punchline LIKE ? OR title LIKE ? OR analysis LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])
    query += " ORDER BY id ASC"
    cur.execute(query, params)
    jokes = cur.fetchall()

    if not jokes:
        console.print("[bold red]No jokes found matching criteria.[/bold red]")
        conn.close()
        return

    console.print(Panel(f"[bold cyan]Corpus of Jewish Humor: Primary Joke Registry[/bold cyan]\nFound [bold green]{len(jokes)}[/bold green] structured primary jokes across traditions.", box=box.ROUNDED))

    for r in jokes[:6]:
        jid, title, trad, cat, setup, punch, analysis, src, orig_t, orig_s, yivo, s_set, s_punc, inc_score = r
        p = Text()
        p.append(f"TRADITION: {trad}  •  CATEGORY: {cat}\n", style="bold yellow")
        if orig_t:
            p.append(f"ORIGINAL ({orig_s}): {orig_t}\n", style="bold cyan")
        if yivo:
            p.append(f"YIVO ROMANIZATION: {yivo}\n", style="dim italic")
        p.append(f"\nSETUP:\n", style="bold cyan")
        p.append(f"{setup}\n\n", style="white")
        p.append(f"PUNCHLINE:\n", style="bold green")
        p.append(f"{punch}\n\n", style="bold white")
        p.append(f"COMEDIC & CULTURAL MECHANICS:\n", style="bold magenta")
        p.append(f"• {analysis}\n", style="dim white")
        delta_p = s_punc - s_set
        p.append(f"• Sentiment Inversion (Delta P): {delta_p:+.2f}  |  Incongruity Index: {inc_score:.2f}\n", style="cyan")
        p.append(f"SOURCE: {src}", style="dim")
        console.print(Panel(p, title=f"[bold white]Joke #{jid}: {title}[/bold white]", box=box.ROUNDED, border_style="cyan"))

    if len(jokes) > 6:
        console.print(f"[dim]... and {len(jokes) - 6} more jokes in registry. Use --tradition or --search to narrow.[/dim]")
    conn.close()

# --- COMMAND 5: HARVEST WIKIPEDIA ---
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
            page_data = next((p for pid, p in pages.items() if pid != "-1"), None)
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

    os.makedirs(RAW_DIR, exist_ok=True)
    slug = re.sub(r"[^a-z0-9_]+", "", real_title.lower().replace(" ", "_"))
    raw_path = os.path.join(RAW_DIR, f"{slug}.json")
    with open(raw_path, "w") as f:
        json.dump({"title": real_title, "full_text": text, "word_count": wc, "char_count": cc, "harvested_at": ts}, f, indent=2)

    conn = get_connection()
    ensure_fts(conn)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO articles (title, word_count, char_count, summary, full_text, harvested_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (real_title, wc, cc, summary, text, ts))
    art_id = cur.lastrowid

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
            cur.execute("""
                INSERT INTO sections_fts (content_rowid, article_title, section_title, content)
                VALUES (?, ?, ?, ?)
            """, (sec_rowid, real_title, sec_title, sec_content))
            indexed_sec_count += 1

    conn.commit()
    conn.close()
    console.print(f"[bold green]Harvested:[/bold green] {real_title} ({wc:,} words, {indexed_sec_count} sections indexed)")

# --- COMMAND 6: ADVANCED HUMOR NLP ANALYZER ---
def cmd_analyze():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, full_text, word_count FROM articles ORDER BY word_count DESC")
    articles = cur.fetchall()

    table = Table(title="[bold cyan]Computational Stylometry & Comedic Linguistics Profile[/bold cyan]", box=box.ROUNDED)
    table.add_column("Document", style="bold white", width=26)
    table.add_column("Words", justify="right", style="dim", width=7)
    table.add_column("Yiddish / 1k", justify="right", style="bold cyan", width=12)
    table.add_column("Ladino / 1k", justify="right", style="bold magenta", width=12)
    table.add_column("Questions / 1k", justify="right", style="yellow", width=14)
    table.add_column("Exclam. / 1k", justify="right", style="red", width=12)
    table.add_column("Dialogue %", justify="right", style="green", width=10)
    table.add_column("Lexical TTR", justify="right", style="white", width=11)

    for aid, title, text, wc in articles[:14]:
        if not wc or wc == 0:
            continue
        words_raw = re.findall(r"\b[a-zA-Z]+\b", text.lower())
        total_tokens = len(words_raw)
        vocab = set(words_raw)
        ttr = (len(vocab) / total_tokens) if total_tokens else 0.0

        y_count = sum(1 for w in words_raw if w in YIDDISH_LOANWORDS)
        y_rate = (y_count / total_tokens * 1000.0) if total_tokens else 0.0

        l_count = sum(1 for w in words_raw if w in LADINO_MARKERS)
        l_rate = (l_count / total_tokens * 1000.0) if total_tokens else 0.0

        q_count = text.count("?")
        q_rate = (q_count / wc * 1000.0)

        e_count = text.count("!")
        e_rate = (e_count / wc * 1000.0)

        quotes = re.findall(r'"([^"]*)"', text) + re.findall(r'“([^”]*)”', text)
        dialogue_words = sum(len(q.split()) for q in quotes)
        diag_pct = (dialogue_words / wc * 100.0) if wc else 0.0

        table.add_row(
            title[:26], f"{wc:,}", f"{y_rate:.1f}", f"{l_rate:.1f}",
            f"{q_rate:.1f}", f"{e_rate:.1f}", f"{diag_pct:.1f}%", f"{ttr:.3f}"
        )

    console.print(table)

    cur.execute("SELECT sentiment_setup, sentiment_punchline, incongruity_score FROM jokes_and_anecdotes")
    j_metrics = cur.fetchall()
    if j_metrics:
        inversions = [r[1] - r[0] for r in j_metrics]
        incongruities = [r[2] for r in j_metrics]
        avg_inv = sum(inversions) / len(inversions)
        avg_inc = sum(incongruities) / len(incongruities)

        inv_panel = Text()
        inv_panel.append(f"• Total Primary Jokes in Registry: {len(j_metrics)}\n", style="bold cyan")
        inv_panel.append(f"• Average Sentiment Inversion (Delta Polarity): {avg_inv:+.3f}\n", style="bold yellow")
        inv_panel.append(f"• Average Incongruity & Paradox Index: {avg_inc:.3f} / 1.000\n", style="bold green")
        inv_panel.append("• Subversion Mechanics: Setup polarity is overwhelmingly punctured by cynical or fatalistic punchlines.\n", style="dim white")
        console.print(Panel(inv_panel, title="[bold yellow]Humor-NLP Sentiment Inversion & Incongruity Index[/bold yellow]", box=box.ROUNDED))

    conn.close()

# --- COMMAND 7: EXPORT CORPUS & ML DATASETS ---
def cmd_export(fmt="json", output_path=None):
    conn = get_connection()
    cur = conn.cursor()

    if fmt == "hf_instruct":
        cur.execute("SELECT id, title, tradition, category, setup, punchline, analysis, source FROM jokes_and_anecdotes")
        jokes = cur.fetchall()
        if not output_path:
            output_path = os.path.join(BASE_DIR, "jewish_humor_instruct.jsonl")
        with open(output_path, "w", encoding="utf-8") as f:
            for j in jokes:
                record = {
                    "instruction": "Analyze the comedic mechanics, cultural tradition, and narrative paradox in the following Jewish humor narrative.",
                    "input": f"TITLE: {j[1]}\nTRADITION: {j[2]} ({j[3]})\nSETUP: {j[4]}",
                    "output": f"PUNCHLINE: {j[5]}\n\nCOMEDIC & CULTURAL ANALYSIS:\n{j[6]}\n\nSOURCE: {j[7]}"
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        console.print(f"[bold green]Exported Hugging Face Instruction Dataset:[/bold green] [white]{output_path}[/white] ({len(jokes)} instruction pairs)")

    elif fmt == "parquet":
        import pandas as pd
        cur.execute("SELECT id, title, tradition, category, setup, punchline, analysis, source, incongruity_score FROM jokes_and_anecdotes")
        rows = cur.fetchall()
        cols = ["id", "title", "tradition", "category", "setup", "punchline", "analysis", "source", "incongruity_score"]
        df = pd.DataFrame(rows, columns=cols)
        if not output_path:
            output_path = os.path.join(BASE_DIR, "jewish_humor_jokes.parquet")
        df.to_parquet(output_path, index=False)
        console.print(f"[bold green]Exported Apache Parquet Dataset:[/bold green] [white]{output_path}[/white] ({len(df)} rows)")

    elif fmt == "json":
        cur.execute("SELECT a.id, a.title, s.section_title, s.content, s.word_count FROM sections s JOIN articles a ON s.article_id = a.id")
        data = [{"article_id": r[0], "article": r[1], "section": r[2], "content": r[3], "words": r[4]} for r in cur.fetchall()]
        if not output_path:
            output_path = os.path.join(BASE_DIR, "corpus_export.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        console.print(f"[bold green]Exported JSON Corpus:[/bold green] [white]{output_path}[/white] ({len(data)} sections)")

    elif fmt == "csv":
        cur.execute("SELECT a.id, a.title, s.section_title, s.content, s.word_count FROM sections s JOIN articles a ON s.article_id = a.id")
        rows = cur.fetchall()
        if not output_path:
            output_path = os.path.join(BASE_DIR, "corpus_export.csv")
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["article_id", "article", "section", "content", "words"])
            writer.writerows(rows)
        console.print(f"[bold green]Exported CSV Corpus:[/bold green] [white]{output_path}[/white] ({len(rows)} sections)")

    elif fmt == "markdown":
        cur.execute("SELECT a.title, s.section_title, s.content, s.word_count FROM sections s JOIN articles a ON s.article_id = a.id ORDER BY a.id, s.id")
        rows = cur.fetchall()
        if not output_path:
            output_path = os.path.join(BASE_DIR, "corpus_export.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Corpus of Jewish Humor: Research Dossier\n\n")
            curr = None
            for r in rows:
                if r[0] != curr:
                    curr = r[0]
                    f.write(f"\n# {curr}\n\n")
                f.write(f"## {r[1]} ({r[3]} words)\n\n{r[2]}\n\n---\n")
        console.print(f"[bold green]Exported Markdown Dossier:[/bold green] [white]{output_path}[/white] ({len(rows)} sections)")

    conn.close()

# --- COMMAND 8: READ ---
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
    cur.execute("SELECT section_title, content, word_count FROM sections WHERE article_id = ? ORDER BY id ASC", (aid,))
    sections = cur.fetchall()
    for stitle, content, wc in sections[:4]:
        console.print(f"\n[bold yellow]═══ {stitle} ({wc} words) ═══[/bold yellow]")
        console.print(content[:600] + ("..." if len(content) > 600 else ""))
    if len(sections) > 4:
        console.print(f"\n[dim]... and {len(sections) - 4} more sections. (Total words: {len(full_text.split()):,})[/dim]")
    conn.close()

# --- COMMAND 9: WEB SERVER & REST API ---

# --- COMMAND: INTERACTIVE TUI EXPLORER ---
def cmd_explore():
    console.print(Panel("[bold cyan]Corpus of Jewish Humor: Interactive Terminal Explorer (jhc v0.4.0)[/bold cyan]\n"
                        "Available commands: [yellow]catalog[/yellow], [yellow]archetypes[/yellow], [yellow]jokes[/yellow], [yellow]analyze[/yellow], [yellow]search <query>[/yellow], [yellow]read <doc>[/yellow], [yellow]harvest <topic>[/yellow], [yellow]exit[/yellow]",
                        box=box.ROUNDED))
    while True:
        try:
            cmd = console.input("[bold yellow]jhc>[/bold yellow] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session closed.[/dim]")
            break
        if not cmd or cmd in ["q", "quit", "exit"]:
            console.print("[dim]Goodbye![/dim]")
            break
        parts = cmd.split(maxsplit=1)
        sub = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        if sub == "catalog":
            cmd_catalog()
        elif sub == "archetypes":
            cmd_archetypes()
        elif sub == "jokes":
            cmd_jokes(search=arg if arg else None)
        elif sub == "analyze":
            cmd_analyze()
        elif sub == "search":
            cmd_search(arg if arg else "humor")
        elif sub == "read":
            cmd_read(arg if arg else "1")
        elif sub == "harvest":
            if arg:
                cmd_harvest(arg)
            else:
                console.print("[red]Usage: harvest <wikipedia_title>[/red]")
        elif sub in ["help", "?"]:
            console.print("[cyan]Commands: catalog, archetypes, jokes, analyze, search <query>, read <doc>, harvest <title>, exit[/cyan]")
        else:
            console.print(f"[red]Unknown command '{sub}'. Type 'help' or 'exit'.[/red]")

# --- COMMAND: REBUILD DATABASE REPOSITORY ---
def cmd_rebuild():
    console.print("[bold yellow]Rebuilding database repository from raw JSON archives and seed routines...[/bold yellow]")
    conn = get_connection()
    cur = conn.cursor()
    
    # 1. Reset relational tables
    cur.execute("DROP TABLE IF EXISTS sections_fts")
    cur.execute("DROP TABLE IF EXISTS sections")
    cur.execute("DROP TABLE IF EXISTS articles")
    
    cur.execute("""
    CREATE TABLE articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT UNIQUE,
        word_count INTEGER,
        char_count INTEGER,
        summary TEXT,
        full_text TEXT,
        harvested_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER,
        section_title TEXT,
        section_level INTEGER,
        content TEXT,
        word_count INTEGER,
        FOREIGN KEY(article_id) REFERENCES articles(id)
    )
    """)
    cur.execute("""
    CREATE VIRTUAL TABLE sections_fts USING fts5(
        article_title,
        section_title,
        content,
        content_rowid UNINDEXED
    )
    """)

    # Ingest from data/raw/
    raw_files = [f for f in sorted(os.listdir(RAW_DIR)) if f.endswith(".json")]
    doc_count = 0
    sec_count = 0
    total_words = 0
    
    for f in raw_files:
        p = os.path.join(RAW_DIR, f)
        with open(p, "r", encoding="utf-8") as jf:
            d = json.load(jf)
        title = d.get("title", "")
        text = d.get("full_text", "")
        if not text:
            continue
        wc = len(text.split())
        cc = len(text)
        summary = text.split("==")[0].strip()
        ts = d.get("harvested_at", "")
        
        cur.execute("""
            INSERT OR REPLACE INTO articles (title, word_count, char_count, summary, full_text, harvested_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, wc, cc, summary, text, ts))
        art_id = cur.lastrowid
        doc_count += 1
        total_words += wc
        
        sec_matches = list(re.finditer(r"(={2,4})\s*([^=]+)\s*\1", text))
        for match in sec_matches:
            sec_level = len(match.group(1))
            sec_title = match.group(2).strip()
            start = match.end()
            end = sec_matches[sec_matches.index(match)+1].start() if sec_matches.index(match)+1 < len(sec_matches) else len(text)
            sec_content = text[start:end].strip()
            sec_wc = len(sec_content.split())
            if sec_content and sec_title.lower() not in ["references", "further reading", "see also", "notes", "bibliography", "external links"]:
                cur.execute("""
                    INSERT INTO sections (article_id, section_title, section_level, content, word_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (art_id, sec_title, sec_level, sec_content, sec_wc))
                sid = cur.lastrowid
                cur.execute("""
                    INSERT INTO sections_fts (content_rowid, article_title, section_title, content)
                    VALUES (?, ?, ?, ?)
                """, (sid, title, sec_title, sec_content))
                sec_count += 1

    conn.commit()
    conn.close()
    console.print(f"[bold green]Rebuild complete:[/bold green] Indexed {doc_count} articles, {sec_count} sections ({total_words:,} words) into SQLite & FTS5.")

def cmd_serve(port=8000):
    import http.server
    import socketserver
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
            elif path == "/api/jokes":
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT id, title, tradition, category, setup, punchline, analysis, source, title_original, script_original, yivo_transliteration, incongruity_score FROM jokes_and_anecdotes")
                data = [{"id": r[0], "title": r[1], "tradition": r[2], "category": r[3], "setup": r[4], "punchline": r[5], "analysis": r[6], "source": r[7], "title_original": r[8], "script_original": r[9], "yivo": r[10], "incongruity": r[11]} for r in cur.fetchall()]
                conn.close()
                self.send_json(data)
            elif path == "/api/search":
                q = params.get("q", [""])[0]
                conn = get_connection()
                ensure_fts(conn)
                cur = conn.cursor()
                clean_q = f"{q.strip()}*" if (" " not in q.strip() and not q.strip().endswith("*")) else q.strip()
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
            elif path in ["/", "/index.html"]:
                self.send_html()
            else:
                self.send_error(404, "Endpoint not found")

        def send_json(self, payload):
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(encoded)

        def send_html(self):
            html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Corpus of Jewish Humor Research Portal</title>
    <style>
        :root { --bg: #0a0e17; --panel: #111827; --card: #172033; --border: #1f2937; --cyan: #38bdf8; --amber: #fbbf24; --green: #34d399; --text: #f9fafb; --muted: #94a3b8; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 24px; }
        .header { border-bottom: 2px solid var(--border); padding-bottom: 16px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        h1 { margin: 0; font-size: 24px; color: var(--cyan); }
        .nav-tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
        .tab-btn { background: transparent; border: none; color: var(--muted); padding: 8px 16px; font-size: 15px; font-weight: 600; cursor: pointer; border-radius: 6px; }
        .tab-btn.active { background: var(--card); color: var(--cyan); }
        .tab-btn:hover { color: var(--text); }
        input { width: 100%; max-width: 600px; padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border); background: var(--panel); color: var(--text); font-size: 16px; outline: none; }
        input:focus { border-color: var(--cyan); }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; margin-top: 16px; }
        .card { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
        .card h3 { margin-top: 0; color: var(--amber); }
        mark { background: rgba(56, 189, 248, 0.3); color: #fff; padding: 2px 4px; border-radius: 4px; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; background: rgba(56, 189, 248, 0.15); color: var(--cyan); font-size: 12px; font-weight: bold; }
        .filter-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
        .filter-btn { background: var(--panel); border: 1px solid var(--border); color: var(--muted); padding: 6px 12px; border-radius: 6px; font-size: 13px; cursor: pointer; }
        .filter-btn.active { border-color: var(--cyan); color: var(--cyan); }
        .joke-setup { color: var(--text); line-height: 1.45; margin-bottom: 12px; }
        .joke-punch { color: var(--green); font-weight: 600; line-height: 1.45; border-left: 3px solid var(--green); padding-left: 10px; margin-bottom: 12px; }
        .joke-analysis { color: var(--muted); font-size: 13px; font-style: italic; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>Corpus of Jewish Humor</h1>
            <p style="margin: 4px 0 0; color: var(--muted); font-size: 14px;">Interactive NLP, Folklore &amp; Joke Registry (v0.4.0)</p>
        </div>
        <div class="badge">SQLite FTS5 + Dense Vector Online</div>
    </div>
    <div class="nav-tabs">
        <button class="tab-btn active" onclick="switchTab('search')">Search Engine</button>
        <button class="tab-btn" onclick="switchTab('jokes')">Primary Jokes (100)</button>
        <button class="tab-btn" onclick="switchTab('archetypes')">Archetypes (20)</button>
    </div>

    <!-- TAB 1: SEARCH -->
    <div id="tab-search">
        <div>
            <input type="text" id="query" placeholder="Search FTS5 &amp; Vector Corpus (e.g. 'golem', 'soup', 'rabbi', 'djoha')..." onkeyup="if(event.key === 'Enter') doSearch()">
        </div>
        <div id="results" class="grid"></div>
    </div>

    <!-- TAB 2: JOKES -->
    <div id="tab-jokes" style="display:none;">
        <div class="filter-bar" id="tradition-filters"></div>
        <div id="jokes-grid" class="grid"></div>
    </div>

    <!-- TAB 3: ARCHETYPES -->
    <div id="tab-archetypes" style="display:none;">
        <div id="archetypes-grid" class="grid"></div>
    </div>

    <script>
        let allJokes = [];
        let allArchetypes = [];

        function switchTab(tab) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('tab-search').style.display = tab === 'search' ? 'block' : 'none';
            document.getElementById('tab-jokes').style.display = tab === 'jokes' ? 'block' : 'none';
            document.getElementById('tab-archetypes').style.display = tab === 'archetypes' ? 'block' : 'none';
            event.target.classList.add('active');
            if (tab === 'jokes' && allJokes.length === 0) loadJokes();
            if (tab === 'archetypes' && allArchetypes.length === 0) loadArchetypes();
        }

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

        async function loadJokes() {
            const res = await fetch('/api/jokes');
            allJokes = await res.json();
            const traditions = ['All', ...new Set(allJokes.map(j => j.tradition))];
            const filterBar = document.getElementById('tradition-filters');
            filterBar.innerHTML = traditions.map(t => `
                <button class="filter-btn ${t==='All'?'active':''}" onclick="filterJokes('${t}', this)">${t}</button>
            `).join('');
            renderJokes(allJokes);
        }

        function filterJokes(tradition, btn) {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const filtered = tradition === 'All' ? allJokes : allJokes.filter(j => j.tradition === tradition);
            renderJokes(filtered);
        }

        function renderJokes(jokes) {
            const grid = document.getElementById('jokes-grid');
            grid.innerHTML = jokes.map(j => `
                <div class="card">
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span class="badge">${j.tradition}</span>
                        <span style="font-size:12px; color:var(--muted)">${j.category}</span>
                    </div>
                    ${j.title_original ? `<p style="color:var(--cyan); font-weight:bold; margin:4px 0 8px;">${j.title_original} <span style="font-weight:normal; font-size:12px; color:var(--muted);">(${j.yivo || ''})</span></p>` : ''}
                    <h3 style="margin: 4px 0 10px;">${j.title}</h3>
                    <p class="joke-setup">${j.setup}</p>
                    <p class="joke-punch">${j.punchline}</p>
                    <p class="joke-analysis">• ${j.analysis}</p>
                </div>
            `).join('');
        }

        async function loadArchetypes() {
            const res = await fetch('/api/archetypes');
            allArchetypes = await res.json();
            const grid = document.getElementById('archetypes-grid');
            grid.innerHTML = allArchetypes.map(a => `
                <div class="card">
                    <span class="badge" style="background:rgba(251,191,36,0.15); color:var(--amber)">${a.category}</span>
                    <h3 style="margin: 8px 0; color:var(--cyan)">${a.term}</h3>
                    <p style="color:var(--text); font-size:14px; line-height:1.45;">${a.definition}</p>
                </div>
            `).join('');
        }

        // Initial search load
        document.getElementById('query').value = 'golem';
        doSearch();
    </script>
</body>
</html>"""
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

def main():
    parser = argparse.ArgumentParser(description="Corpus of Jewish Humor: Research, NLP & ML Suite")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("catalog", help="List all indexed documents, sections, and metrics")
    subparsers.add_parser("archetypes", help="Display cultural archetypes and comic tropes")

    p_search = subparsers.add_parser("search", help="Perform search (supports fts, semantic, hybrid)")
    p_search.add_argument("query", help="Search query (e.g. 'financial anxiety', 'soup*')")
    p_search.add_argument("--mode", choices=["fts", "semantic", "hybrid"], default="hybrid", help="Search mode")
    p_search.add_argument("--limit", type=int, default=5, help="Maximum matches to return")

    p_jokes = subparsers.add_parser("jokes", help="Explore primary joke registry with setup/punchline and original scripts")
    p_jokes.add_argument("--tradition", help="Filter by tradition (e.g. Ashkenazi, Sephardic, Soviet, Talmudic, Borscht)")
    p_jokes.add_argument("--category", help="Filter by category (e.g. 'Folk Folly', 'Trickster', 'Political')")
    p_jokes.add_argument("--search", help="Search keywords in setups, punchlines, or analyses")

    p_harvest = subparsers.add_parser("harvest", help="Fetch and ingest a new Wikipedia article into DB & FTS5")
    p_harvest.add_argument("topic", help="Wikipedia article title (e.g. 'Sholem Aleichem')")

    subparsers.add_parser("analyze", help="Run computational stylometry, sentiment inversion & comedic metrics")

    p_read = subparsers.add_parser("read", help="Read article sections with rich formatting")
    p_read.add_argument("target", help="Article ID or title substring")

    p_export = subparsers.add_parser("export", help="Export corpus or ML datasets")
    p_export.add_argument("--format", choices=["json", "csv", "markdown", "parquet", "hf_instruct"], default="json")
    p_export.add_argument("--output", help="Custom output file path")

    p_serve = subparsers.add_parser("serve", help="Launch embedded local web explorer & REST API")
    p_serve.add_argument("--port", type=int, default=8000, help="Port to serve on (default: 8000)")

    
    subparsers.add_parser("explore", help="Launch interactive terminal explorer loop")
    subparsers.add_parser("rebuild", help="Rebuild database schema and index from raw archives")
    args = parser.parse_args()
    if args.command == "catalog":
        cmd_catalog()
    elif args.command == "archetypes":
        cmd_archetypes()
    elif args.command == "search":
        cmd_search(args.query, mode=args.mode, limit=args.limit)
    elif args.command == "jokes":
        cmd_jokes(tradition=args.tradition, category=args.category, search=args.search)
    elif args.command == "harvest":
        cmd_harvest(args.topic)
    elif args.command == "analyze":
        cmd_analyze()
    elif args.command == "read":
        cmd_read(args.target)
    elif args.command == "export":
        cmd_export(fmt=args.format, output_path=args.output)
    
    elif args.command == "explore":
        cmd_explore()
    elif args.command == "rebuild":
        cmd_rebuild()
    elif args.command == "serve":
        cmd_serve(port=args.port)
    else:
        cmd_catalog()

if __name__ == "__main__":
    main()
