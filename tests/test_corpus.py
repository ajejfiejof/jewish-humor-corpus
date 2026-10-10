import os
import sqlite3
import unittest
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "jewish_humor.db")

class TestJewishHumorCorpus(unittest.TestCase):
    def setUp(self):
        self.assertTrue(os.path.exists(DB_PATH), "Database file must exist")
        self.conn = sqlite3.connect(DB_PATH)

    def tearDown(self):
        self.conn.close()

    def test_database_tables_exist(self):
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        self.assertIn("articles", tables)
        self.assertIn("sections", tables)
        self.assertIn("archetypes_and_terms", tables)
        self.assertIn("sections_fts", tables)
        self.assertIn("jokes_and_anecdotes", tables)

    def test_articles_volume(self):
        cur = self.conn.cursor()
        cur.execute("SELECT count(*), sum(word_count) FROM articles")
        count, words = cur.fetchone()
        self.assertGreaterEqual(count, 20, "Corpus must have at least 20 articles")
        self.assertGreater(words, 50000, "Corpus must exceed 50,000 words")

    def test_jokes_table(self):
        cur = self.conn.cursor()
        cur.execute("SELECT count(*), count(DISTINCT tradition) FROM jokes_and_anecdotes")
        count, traditions = cur.fetchone()
        self.assertGreaterEqual(count, 12, "Must contain at least 12 curated jokes")
        self.assertGreaterEqual(traditions, 6, "Must span at least 6 distinct traditions")

    def test_fts5_search(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT article_title, section_title, snippet(sections_fts, 2, '<b>', '</b>', '...', 15)
            FROM sections_fts
            WHERE sections_fts MATCH 'golem*'
        """)
        results = cur.fetchall()
        self.assertGreaterEqual(len(results), 1, "FTS5 query for 'golem*' must return matches")

    def test_archetypes_seeded(self):
        cur = self.conn.cursor()
        cur.execute("SELECT count(*) FROM archetypes_and_terms")
        count = cur.fetchone()[0]
        self.assertGreaterEqual(count, 20, "Must contain at least 20 archetypes")

    def test_cli_execution_suite(self):
        cli_path = os.path.join(BASE_DIR, "cli.py")
        
        # 1. catalog
        res = subprocess.run([sys.executable, cli_path, "catalog"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"catalog failed: {res.stderr}")
        self.assertIn("Corpus Document Catalog", res.stdout)

        # 2. search
        res_search = subprocess.run([sys.executable, cli_path, "search", "rabbi"], capture_output=True, text=True)
        self.assertEqual(res_search.returncode, 0)
        self.assertIn("FTS5 Query", res_search.stdout)

        # 3. jokes
        res_jokes = subprocess.run([sys.executable, cli_path, "jokes", "--tradition", "Sephardic"], capture_output=True, text=True)
        self.assertEqual(res_jokes.returncode, 0)
        self.assertIn("Djohá", res_jokes.stdout)

if __name__ == "__main__":
    unittest.main()
