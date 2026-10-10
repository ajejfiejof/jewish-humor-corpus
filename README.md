# Corpus of Jewish Humor 🎭
> A comprehensive computational and cultural NLP corpus documenting the history, archetypes, linguistic mechanisms, and narrative structures of Jewish humor across Ashkenazi, Sephardic, Talmudic, Soviet, and Modern traditions.

![Corpus Dashboard](assets/demo_screenshot.png)

---

## Overview

The **Corpus of Jewish Humor** is an open research database and natural language processing suite initialized from foundational scholarly, historical, and folkloric texts. It indexes the historical progression of Jewish humor from ancient Talmudic wit to the modern Borscht Belt, Soviet political *anekdoty*, Sephardic *Djohá* trickster tales, and contemporary satire.

- **Primary Database:** SQLite 3 with **FTS5 Full-Text Search** (`data/jewish_humor.db`)
- **Indexed Volume:** **56,872 words** across **21 foundational texts** and **196 categorized sections** (355k+ characters).
- **Primary Joke Registry:** Dedicated `jokes_and_anecdotes` table indexing classic jokes with setup, punchline, and comedic/cultural analysis across 7 traditions.
- **Cultural Entities:** 20 pre-indexed archetypes spanning Ashkenazi, Sephardic, Mythic, Rabbinic, and Modern Israeli lore.
- **Stylometric Engine:** Pre-compiled lexicon of Yiddish and Ladino markers, question/exclamation density metrics, and Type-Token Ratio (TTR) analysis.
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

### 3. Running Automated Tests
Verify database integrity, FTS5 index, and CLI suite:
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

### 1. Primary Joke Registry (`jokes`)
Explore and filter curated primary jokes with setup, punchline, and cultural analysis:
```bash
# Browse all jokes
python3 cli.py jokes

# Filter by tradition (e.g. Sephardic, Ashkenazi, Soviet, Talmudic, Borscht)
python3 cli.py jokes --tradition Sephardic
python3 cli.py jokes --tradition Soviet
python3 cli.py jokes --tradition Talmudic

# Search jokes by keyword in setup or punchline
python3 cli.py jokes --search "soup"
```

### 2. Full-Text Search with BM25 Ranking (`search`)
Leverages SQLite's native **FTS5** full-text search engine with BM25 relevance scoring and colored snippet highlighting:
```bash
# Search for keywords or prefix wildcards across 196 sections
python3 cli.py search "golem*"
python3 cli.py search "donkey*"
python3 cli.py search "theatre"
```

### 3. Folk Anecdotes & Parable Extractor (`anecdote`)
Serves classic curated folk jokes and parables with background comedic and cultural analysis:
```bash
# Random folk joke with analysis
python3 cli.py anecdote

# Filter anecdotes by topic (e.g. Chelm, Hershele, Talmudic, Soviet)
python3 cli.py anecdote --topic Chelm
python3 cli.py anecdote --topic Soviet
```

### 4. Computational Stylometry & Linguistics (`analyze`)
Analyzes subconscious stylistic markers and comedic language traits across every document in the corpus:
```bash
python3 cli.py analyze
```
- **Yiddish Loanword Density:** Measures Yiddish comedic loanwords per 1,000 words.
- **Rhetorical Question Rate:** Quantifies Talmudic dialectic counter-questioning habits (*"Why do you answer a question with a question?"* — peaks at **12.2 / 1k words** in the core text).
- **Emotional Exclamation Rate:** Measures hyperbolic emphasis.
- **Lexical Diversity (TTR):** Evaluates vocabulary breadth across historical periods.

### 5. Automated Wikipedia Harvester (`harvest`)
Dynamically fetches and ingests new Wikipedia articles into both the relational schema and the FTS5 search index on demand:
```bash
# Ingest new articles into the corpus
python3 cli.py harvest "Sholem Aleichem"
python3 cli.py harvest "Leo Rosten"
python3 cli.py harvest "Badchen"
```

### 6. Embedded Web Explorer & REST API (`serve`)
Launches a zero-dependency local web server and search portal at `http://localhost:8000`:
```bash
python3 cli.py serve --port 8000
```
**API Endpoints:**
- `GET /api/search?q=golem`: FTS5 BM25 search results with highlighted snippets.
- `GET /api/jokes`: Curated primary jokes with setup/punchline segmentation.
- `GET /api/catalog`: Complete document list with word and section counts.
- `GET /api/archetypes`: Cultural archetypes, roles, and definitions.
- `GET /api/anecdote`: Random curated folk joke and analytical breakdown.

### 7. Interactive TUI Explorer (`explore`)
Launches an interactive terminal loop to query, read, and browse without restarting the CLI:
```bash
python3 cli.py explore
```

### 8. Structured Article Reader (`read`)
Reads formatted, readable section chunks from any indexed article by ID or title substring:
```bash
python3 cli.py read "Chelm"
python3 cli.py read "Sholem Aleichem"
python3 cli.py read 1
```

### 9. Data Export Engine (`export`)
Exports the entire corpus or query sets into structured formats for external analysis in Pandas, R, or Jupyter:
```bash
python3 cli.py export --format json --output corpus.json
python3 cli.py export --format csv --output corpus.csv
python3 cli.py export --format markdown --output corpus.md
```

---

## Corpus Taxonomy: The 6 Knowledge Domains

### 1. Folk Anthologies & The Primary Joke Canon
- **Chełm Folly Cycles:** Parables of pseudo-intellectualism and hyper-literal deduction.
- **Hershele of Ostropol:** 18th-century court jester satirizing aristocratic greed.
- **Freud's Humor Theory (*Jokes and Their Relation to the Unconscious*):** Psychoanalytic models of displacement, aggression, and relief in Jewish humor.
- **Soviet Anekdoty:** Dissident political irony starring *Rabinovich*.

### 2. Mythic Archetypes & Folklore
- **The Golem of Prague:** Animated clay defender representing artificial life and protective power turning catastrophic.
- **The Dybbuk:** Displaced soul possessing the living, reflecting shtetl anxieties and broken oaths.
- **Tzadikim Nistarim (The 36 Hidden Righteous):** Unrecognized individuals sustaining humanity's existence.
- **Elijah the Prophet:** Ethical trickster-judge testing generosity in the guise of a beggar.
- **Luftmensch & Gimpel the Fool:** The impractical dreamer and the holy fool.

### 3. Talmudic Dialectics & Rabbinic Parables
- **The Oven of Akhnai (*Lo BaShamayim Hi*):** Intellectual consensus and reason defeating divine miracles.
- **Talmudic Counter-Questioning:** Inverting passive questions into active assertions.
- **Pilpul Parodies:** Scholastic hair-splitting humor.

### 4. Sephardic & Judeo-Spanish (Ladino) Traditions
- **Djohá (Djudha):** The Mediterranean and Ottoman Sephardic trickster counterpart to Hershele.
- **Ladino Refranes:** Ironical, fatalistic proverbs from Salonica, Istanbul, and Sarajevo.

### 5. Classic Yiddish & Hebrew Literary Satirists
- **Mendele Mocher Sforim:** *The Travels of Benjamin the Third* (The Jewish Don Quixote).
- **Sholem Aleichem:** Monologues of *Tevye* and *Menachem-Mendl*.
- **Ephraim Kishon:** Satirist of Israeli statehood and bureaucracy (*The Blaumilch Canal*).

### 6. The Borscht Belt & American Stand-Up Pipeline
- **Catskills Tummlers:** Rapid-fire one-liner rhythm (Henny Youngman).
- **Subversive Counter-Culture:** Lenny Bruce's sociological deconstruction of language and identity.
- **The Modern Television Dialectic:** Transition from Talmudic social dissection to *Seinfeld* and *Curb Your Enthusiasm*.

---

## Database Architecture

The SQLite database (`data/jewish_humor.db`) is structured into five normalized tables:
- `articles`: Master table for ingested source documents (21 documents, 56k+ words).
- `sections`: Hierarchical content sections parsed from source text (196 sections).
- `sections_fts`: SQLite **FTS5** virtual table indexing all section content for BM25 ranking.
- `jokes_and_anecdotes`: Structured primary joke archive with setup, punchline, and comedic analysis across 7 traditions.
- `archetypes_and_terms`: Seeded catalog of 20 archetypes, roles, and cultural concepts.

---

## License

This project is licensed under the [MIT License](LICENSE).
