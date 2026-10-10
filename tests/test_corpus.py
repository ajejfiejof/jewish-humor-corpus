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

    def test_articles_volume(self):
        cur = self.conn.cursor()
        cur.execute("SELECT count(*), sum(word_count) FROM articles")
        count, words = cur.fetchone()
        self.assertGreaterEqual(count, 10, "Corpus must have at least 10 articles")
        self.assertGreater(words, 25000, "Corpus must exceed 25,000 words")

    def test_fts5_search(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT article_title, section_title, snippet(sections_fts, 2, '<b>', '</b>', '...', 15)
            FROM sections_fts
            WHERE sections_fts MATCH 'soup*'
        """)
        results = cur.fetchall()
        self.assertGreaterEqual(len(results), 2, "FTS5 query for 'soup*' must return matches")

    def test_archetypes_seeded(self):
        cur = self.conn.cursor()
        cur.execute("SELECT count(*) FROM archetypes_and_terms")
        count = cur.fetchone()[0]
        self.assertGreaterEqual(count, 8, "Must contain standard archetypes")

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

        # 3. analyze
        res_analyze = subprocess.run([sys.executable, cli_path, "analyze"], capture_output=True, text=True)
        self.assertEqual(res_analyze.returncode, 0)
        self.assertIn("Stylometry", res_analyze.stdout)

        # 4. anecdote
        res_anecdote = subprocess.run([sys.executable, cli_path, "anecdote"], capture_output=True, text=True)
        self.assertEqual(res_anecdote.returncode, 0)
        self.assertIn("Corpus Anecdote", res_anecdote.stdout)

        # 5. read
        res_read = subprocess.run([sys.executable, cli_path, "read", "Chelm"], capture_output=True, text=True)
        self.assertEqual(res_read.returncode, 0)
        self.assertIn("Wise Men of Chelm", res_read.stdout)

if __name__ == "__main__":
    unittest.main()
