#!/usr/bin/env python3
"""
Corpus of Jewish Humor: Interactive CLI & Search Engine
Provides querying, archetype discovery, and full-text semantic inspection.
"""

import argparse
import os
import sqlite3
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "jewish_humor.db")

def get_connection():
    if not os.path.exists(DB_PATH):
        console.print(f"[bold red]Error: Database file not found at {DB_PATH}[/bold red]")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def cmd_catalog():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.title, count(s.id) as num_sec, a.word_count, a.char_count
        FROM articles a
        LEFT JOIN sections s ON a.id = s.article_id
        GROUP BY a.id
        ORDER BY a.word_count DESC
    """)
    
    table = Table(title="[bold yellow]Corpus Document Catalog[/bold yellow]", box=box.ROUNDED)
    table.add_column("ID", justify="center", style="dim", width=4)
    table.add_column("Article Title", style="bold white")
    table.add_column("Sections", justify="right", style="cyan")
    table.add_column("Words", justify="right", style="green")
    table.add_column("Characters", justify="right", style="dim")
    
    total_w = 0
    for aid, title, nsec, wc, cc in cur.fetchall():
        table.add_row(str(aid), title, str(nsec), f"{wc:,}", f"{cc:,}")
        total_w += wc
        
    console.print(table)
    console.print(f"[dim]Total indexed volume: [bold green]{total_w:,}[/bold green] words across 74 sections.[/dim]\n")
    conn.close()

def cmd_archetypes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT term, category, definition FROM archetypes_and_terms ORDER BY id ASC")
    
    table = Table(title="[bold magenta]Core Cultural Archetypes & Comic Roles[/bold magenta]", box=box.ROUNDED)
    table.add_column("Archetype / Concept", style="bold cyan", width=22)
    table.add_column("Classification", style="yellow", width=18)
    table.add_column("Cultural Mechanics & Function", style="white")
    
    for term, cat, defn in cur.fetchall():
        table.add_row(term, cat, defn)
        
    console.print(table)
    conn.close()

def cmd_search(query):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.title, s.section_title, s.content
        FROM sections s
        JOIN articles a ON s.article_id = a.id
        WHERE s.content LIKE ? OR s.section_title LIKE ?
        LIMIT 5
    """, (f"%{query}%", f"%{query}%"))
    
    results = cur.fetchall()
    if not results:
        console.print(f"[bold red]No matches found for query:[/bold red] '{query}'")
        conn.close()
        return
        
    out = Text()
    out.append(f"Search Results for '{query}' ({len(results)} matches displayed):\n", style="bold green")
    for title, sec, content in results:
        out.append(f"\n• {title} → [bold yellow]{sec}[/bold yellow]\n")
        snippet = " ".join(content.split()[:45]) + "..."
        out.append(f"  \"{snippet}\"\n", style="dim white")
        
    console.print(Panel(out, title="[bold green]Semantic Extraction Results[/bold green]", box=box.ROUNDED))
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Corpus of Jewish Humor: Research & NLP CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("catalog", help="List all indexed documents and metrics")
    subparsers.add_parser("archetypes", help="Display core cultural archetypes and comic tropes")
    
    search_parser = subparsers.add_parser("search", help="Perform full-text search across sections")
    search_parser.add_argument("query", help="Keyword or phrase to search")
    
    args = parser.parse_args()
    if args.command == "catalog":
        cmd_catalog()
    elif args.command == "archetypes":
        cmd_archetypes()
    elif args.command == "search":
        cmd_search(args.query)
    else:
        # Default: show catalog and archetypes
        cmd_catalog()
        cmd_archetypes()

if __name__ == "__main__":
    main()
