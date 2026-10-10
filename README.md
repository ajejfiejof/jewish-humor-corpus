# Corpus of Jewish Humor 🎭
> A structured computational and cultural NLP corpus documenting the history, archetypes, linguistic mechanisms, and narrative structures of Jewish humor.

![Corpus Dashboard](assets/demo_screenshot.png)

---

## Overview

The **Corpus of Jewish Humor** is an open research database and natural language processing suite initialized from foundational scholarly, historical, and folkloric texts. It indexes the historical progression of Jewish humor from ancient Talmudic wit to the modern Borscht Belt, Soviet political *anekdoty*, and contemporary satire.

- **Primary Database:** SQLite 3 with **FTS5 Full-Text Search** (`data/jewish_humor.db`)
- **Indexed Volume:** **29,050 words** across **11 foundational texts** and **98 categorized sections** (179k+ characters).
- **Cultural Entities:** Pre-indexed archetypes (*Schlemiel*, *Schlimazel*, *Wise Men of Chełm*, *Hershele Ostropoler*, *Chutzpah*, *Badchen*).
- **Stylometric Engine:** Pre-compiled lexicon of 80+ Yiddish loanwords, question/exclamation density metrics, and Type-Token Ratio (TTR) analysis.
- **Embedded Web & API Server:** Zero-dependency local web explorer and REST API server.

---

## Quickstart

### 1. Installation
Clone the repository and install as an editable package (provides the `jhc` command):
```bash
git clone https://github.com/ajejfiejof/jewish-humor-corpus.git
cd jewish-humor-corpus
pip install -e .
```

### 2. Interactive Terminal Demo
Launch the full terminal visualization suite:
```bash
python3 demo.py
```

### 3. Automated Test Suite
Run the automated test suite verifying database integrity, FTS5 search, and CLI tools:
```bash
python3 -m unittest discover tests
```

---

## CLI Capabilities & Feature Suite

The included `cli.py` (or `jhc` command) provides a comprehensive research toolkit:

```bash
# Display help and available commands
python3 cli.py --help
```

### Full-Text Search with BM25 Ranking (`search`)
Leverages SQLite's native **FTS5** full-text search engine with BM25 relevance scoring and colored snippet highlighting:
```bash
python3 cli.py search "soup*"
python3 cli.py search "rabbi"
python3 cli.py search "theatre"
```

### Folk Anecdotes & Parable Extractor (`anecdote`)
Serves classic curated folk jokes and parables with background comedic and cultural analysis:
```bash
# Random folk joke with analysis
python3 cli.py anecdote

# Filter anecdotes by topic (e.g. Chelm, Hershele, Talmudic, Soviet)
python3 cli.py anecdote --topic Chelm
python3 cli.py anecdote --topic Soviet
```

### Computational Stylometry & Linguistics (`analyze`)
Analyzes subconscious stylistic markers and comedic language traits across every document in the corpus:
```bash
python3 cli.py analyze
```
- **Yiddish Loanword Density:** Measures Yiddish comedic loanwords per 1,000 words.
- **Rhetorical Question Rate:** Quantifies Talmudic dialectic counter-questioning habits (*"Why do you answer a question with a question?"* — peaks at **12.2 / 1k words** in the core text).
- **Emotional Exclamation Rate:** Measures hyperbolic emphasis.
- **Lexical Diversity (TTR):** Evaluates vocabulary breadth across historical periods.

### Automated Wikipedia Harvester (`harvest`)
Dynamically fetches and ingests new Wikipedia articles into both the relational schema and the FTS5 search index on demand:
```bash
# Ingest new articles into the corpus
python3 cli.py harvest "Sholem Aleichem"
python3 cli.py harvest "Leo Rosten"
python3 cli.py harvest "Badchen"
```

### Embedded Web Explorer & REST API (`serve`)
Launches a zero-dependency local web server and search portal at `http://localhost:8000`:
```bash
python3 cli.py serve --port 8000
```
**API Endpoints:**
- `GET /api/search?q=soup`: FTS5 BM25 search results with highlighted snippets.
- `GET /api/catalog`: Complete document list with word and section counts.
- `GET /api/archetypes`: Cultural archetypes, roles, and definitions.
- `GET /api/anecdote`: Random curated folk joke and analytical breakdown.

### Interactive TUI Explorer (`explore`)
Launches an interactive terminal loop to query, read, and browse without restarting the CLI:
```bash
python3 cli.py explore
```

### Structured Article Reader (`read`)
Reads formatted, readable section chunks from any indexed article by ID or title substring:
```bash
python3 cli.py read "Chelm"
python3 cli.py read "Sholem Aleichem"
python3 cli.py read 1
```

### Data Export Engine (`export`)
Exports the entire corpus or query sets into structured formats for external analysis in Pandas, R, or Jupyter:
```bash
python3 cli.py export --format json --output corpus.json
python3 cli.py export --format csv --output corpus.csv
python3 cli.py export --format markdown --output corpus.md
```

---

## Corpus Taxonomy

### Historical Eras
1. **Talmudic & Rabbinic Era:** Disputations, midrashic paradoxes, and legalistic *pilpul* argumentation.
2. **The Haskalah (Enlightenment, 18th–19th c.):** Internal satire targeting superstition and provincial insularity.
3. **Eastern European Shtetl Era:** Chełm folktales, Hershele the trickster, wedding *badchen* jesters, and defensive irony amid hardship.
4. **Borscht Belt & American Vaudeville (20th c.):** Catskills resort *tummlers*; the cradle of modern stand-up comedy (Marx Brothers, Milton Berle, Mel Brooks, Seinfeld).
5. **Soviet Dissident Era:** Political *anekdoty* (Rabinovich) using biting irony to navigate authoritarian bureaucracy.
6. **Contemporary Israeli Satire:** Shift from diaspora vulnerability to direct *Sabra* wit (Ephraim Kishon, *Eretz Nehederet*).

### Archetypes & Comic Roles
- **The Schlemiel:** The perpetually clumsy or inept person who habitually spills their soup.
- **The Schlimazel:** The chronically unlucky person upon whom the soup is spilled.
- **The Wise Men of Chełm:** A mythical town of naive fools who apply convoluted, hyper-logical deductions to everyday problems with absurdly flawed results.
- **Hershele of Ostropol:** An 18th-century Ukrainian Jewish folk trickster who defended the impoverished with razor-sharp satirical retorts.
- **Chutzpah:** Brazen audacity, famously illustrated as someone who murders their parents and throws themselves on the mercy of the court as an orphan.

---

## Database Architecture

The SQLite database (`data/jewish_humor.db`) is structured into four normalized tables:
- `articles`: Master table for ingested source documents (11 documents, 29k words).
- `sections`: Hierarchical content sections parsed from source text (98 sections).
- `sections_fts`: SQLite **FTS5** virtual table indexing all section content for BM25 ranking.
- `archetypes_and_terms`: Seeded glossary of archetypes, roles, and cultural concepts.

---

## License

This project is licensed under the [MIT License](LICENSE).
