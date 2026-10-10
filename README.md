# Corpus of Jewish Humor 🎭
> A structured computational and cultural NLP corpus documenting the history, archetypes, linguistic mechanisms, and narrative structures of Jewish humor.

![Corpus Dashboard](assets/demo_screenshot.png)

---

## Overview

The **Corpus of Jewish Humor** is an open research database and natural language processing suite initialized from foundational scholarly, historical, and folkloric texts. It indexes the historical progression of Jewish humor from ancient Talmudic wit to the modern Borscht Belt, Soviet political *anekdoty*, and contemporary satire.

- **Primary Database:** SQLite 3 with **FTS5 Full-Text Search** (`data/jewish_humor.db`)
- **Indexed Volume:** **26,290 words** across **9 foundational texts** and **86 categorized sections**.
- **Cultural Entities:** Pre-indexed archetypes (*Schlemiel*, *Schlimazel*, *Wise Men of Chełm*, *Hershele Ostropoler*, *Chutzpah*, *Badchen*).
- **Stylometric Engine:** Pre-compiled lexicon of 80+ Yiddish loanwords, question/exclamation density metrics, and Type-Token Ratio (TTR) analysis.

---

## Quickstart

### 1. Installation
Clone the repository and install the lightweight CLI dependency (`rich`):
```bash
git clone https://github.com/ajejfiejof/jewish-humor-corpus.git
cd jewish-humor-corpus
pip install -r requirements.txt
```

### 2. Interactive Terminal Demo
Launch the full terminal visualization suite:
```bash
python3 demo.py
```

### 3. Running Automated Tests
Verify database integrity, FTS5 index, and CLI suite:
```bash
python3 -m unittest discover tests
```

---

## CLI Capabilities & Feature Suite

The included `cli.py` tool provides a complete suite for querying, analyzing, expanding, and exporting the corpus.

### Full-Text Search with BM25 Ranking (`search`)
Leverages SQLite's native **FTS5** full-text search engine with BM25 relevance scoring and colored snippet highlighting:
```bash
# Search for keywords or prefix wildcards
python3 cli.py search "soup*"
python3 cli.py search "rabbi"
python3 cli.py search "theatre"
```

### Computational Stylometry & Linguistics (`analyze`)
Analyzes subconscious stylistic markers and comedic language traits across every document:
```bash
python3 cli.py analyze
```
- **Yiddish Loanword Density:** Measures Yiddish comedic loanwords per 1,000 words.
- **Rhetorical Question Rate:** Captures Talmudic counter-questioning habits (*"Why do you answer a question with a question?"*).
- **Emotional Exclamation Rate:** Quantifies hyperbolic emphasis.
- **Lexical Diversity (TTR):** Evaluates vocabulary breadth across eras.

### Automated Wikipedia Harvester (`harvest`)
Dynamically fetches and ingests new Wikipedia articles into both the relational schema and the FTS5 search index on demand:
```bash
# Ingest new articles into the corpus
python3 cli.py harvest "Sholem Aleichem"
python3 cli.py harvest "Leo Rosten"
python3 cli.py harvest "Badchen"
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

### Document & Archetype Exploration (`catalog`, `archetypes`)
```bash
# List all indexed documents, word counts, and section metrics
python3 cli.py catalog

# Display core cultural archetypes and comic tropes
python3 cli.py archetypes
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
- `articles`: Master table for ingested source documents.
- `sections`: Hierarchical content sections parsed from source text.
- `sections_fts`: SQLite **FTS5** virtual table indexing all section content for BM25 ranking.
- `archetypes_and_terms`: Seeded glossary of archetypes, roles, and cultural concepts.

---

## License

This project is licensed under the [MIT License](LICENSE).
