# Corpus of Jewish Humor 🎭
> A structured computational and cultural NLP corpus documenting the history, archetypes, linguistic mechanisms, and narrative structures of Jewish humor.

![Corpus Dashboard](assets/demo_screenshot.png)

---

## Overview

The **Corpus of Jewish Humor** is an open research database and natural language processing dataset initialized from foundational scholarly, historical, and folkloric texts. It indexes the historical progression of Jewish humor from ancient Talmudic wit to the modern Borscht Belt and contemporary satire.

- **Primary Database:** SQLite 3 (`data/jewish_humor.db`)
- **Indexed Volume:** **22,978 words** across **8 foundational texts** and **74 categorized sections**.
- **Cultural Entities:** Pre-indexed archetypes (*Schlemiel*, *Schlimazel*, *Wise Men of Chełm*, *Hershele Ostropoler*, *Chutzpah*, *Badchen*).

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

### 3. Querying the Corpus via CLI
The included `cli.py` tool provides instant searching, archetype inspection, and catalog exploration:

```bash
# List all indexed documents and section metrics
python3 cli.py catalog

# Display core cultural archetypes and comic tropes
python3 cli.py archetypes

# Search across all 74 indexed sections for a keyword
python3 cli.py search "logic"
python3 cli.py search "soup"
python3 cli.py search "trickster"
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

The SQLite database (`data/jewish_humor.db`) is structured into three normalized tables:

```sql
-- Retrieve all sections detailing folklore and paradoxes
SELECT a.title, s.section_title, s.word_count
FROM sections s
JOIN articles a ON s.article_id = a.id
WHERE s.section_title LIKE '%Chelm%' 
   OR s.section_title LIKE '%Hershel%'
ORDER BY s.word_count DESC;
```

---

## License

This project is licensed under the [MIT License](LICENSE).
