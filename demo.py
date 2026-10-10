#!/usr/bin/env python3
"""
Corpus of Jewish Humor: Terminal Capabilities Demo
Demonstrates real-time querying, metadata inspection, and semantic extraction
against the local SQLite database (data/corpus_jewish_humor/jewish_humor.db).
"""

import sqlite3
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

def main():
    console = Console(width=110)
    db_path = "data/corpus_jewish_humor/jewish_humor.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
    except Exception as e:
        console.print(f"[bold red]Error connecting to {db_path}:[/bold red] {e}")
        sys.exit(1)

    cur.execute("SELECT count(*), sum(word_count), sum(char_count) FROM articles")
    doc_count, total_words, total_chars = cur.fetchone()

    cur.execute("SELECT count(*) FROM sections")
    total_sections = cur.fetchone()[0]

    header_text = Text()
    header_text.append("CORPUS OF JEWISH HUMOR", style="bold cyan")
    header_text.append(" | Linguistic, Cultural & Folklore Analytics Suite\n", style="bold white")
    header_text.append(f"Database: {db_path}  •  Articles: {doc_count}  •  Sections: {total_sections}  •  Words: {total_words:,}  •  Chars: {total_chars:,}", style="dim")
    console.print(Panel(header_text, box=box.ROUNDED, border_style="cyan"))

    table_docs = Table(title="[bold yellow]Harvested Document Index & Corpus Composition[/bold yellow]", box=box.SIMPLE_HEAVY)
    table_docs.add_column("ID", justify="center", style="dim", width=4)
    table_docs.add_column("Document Title", style="bold white")
    table_docs.add_column("Sections", justify="right", style="cyan")
    table_docs.add_column("Words", justify="right", style="green")
    table_docs.add_column("Chars", justify="right", style="dim")
    table_docs.add_column("Summary Preview", style="italic")

    cur.execute("""
        SELECT a.id, a.title, count(s.id) as num_sec, a.word_count, a.char_count, a.summary
        FROM articles a
        LEFT JOIN sections s ON a.id = s.article_id
        GROUP BY a.id
        ORDER BY a.word_count DESC
    """)

    for row in cur.fetchall():
        aid, title, num_sec, wc, cc, summary = row
        preview = summary[:60] + "..." if summary else ""
        table_docs.add_row(str(aid), title, str(num_sec), f"{wc:,}", f"{cc:,}", preview)

    console.print(table_docs)
    console.print()

    table_arch = Table(title="[bold magenta]Core Cultural Archetypes & Folkloric Entities[/bold magenta]", box=box.ROUNDED)
    table_arch.add_column("Term / Persona", style="bold cyan", width=22)
    table_arch.add_column("Category", style="yellow", width=18)
    table_arch.add_column("Definition & Cultural Mechanics", style="white")

    cur.execute("SELECT term, category, definition FROM archetypes_and_terms ORDER BY id ASC")
    for term, cat, defn in cur.fetchall():
        table_arch.add_row(term, cat, defn)

    console.print(table_arch)
    console.print()

    search_kw = "logic"
    cur.execute("""
        SELECT a.title, s.section_title, s.content
        FROM sections s
        JOIN articles a ON s.article_id = a.id
        WHERE s.content LIKE ? OR s.section_title LIKE ?
        LIMIT 2
    """, (f"%{search_kw}%", f"%{search_kw}%"))

    search_results = cur.fetchall()
    demo_text = Text()
    demo_text.append(f"Semantic Query: '{search_kw}' across 74 indexed sections:\n", style="bold green")
    for title, sec, content in search_results:
        demo_text.append(f"\n[•] {title} → Section: '{sec}'\n", style="bold yellow")
        clean_snippet = " ".join(content.split()[:45]) + "..."
        demo_text.append(f"    \"{clean_snippet}\"\n", style="dim white")

    console.print(Panel(demo_text, title="[bold green]Live NLP & Substring Extraction Engine[/bold green]", box=box.ROUNDED, border_style="green"))
    conn.close()

if __name__ == "__main__":
    main()
