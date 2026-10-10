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

    def test_jokes_volume_and_orthography(self):
        cur = self.conn.cursor()
        cur.execute("SELECT count(*), count(DISTINCT tradition) FROM jokes_and_anecdotes")
        count, traditions = cur.fetchone()
        self.assertGreaterEqual(count, 100, "Must contain at least 100 curated jokes")
        self.assertGreaterEqual(traditions, 6, "Must span at least 6 traditions")

        cur.execute("SELECT count(*) FROM jokes_and_anecdotes WHERE script_original IS NOT NULL")
        with_script = cur.fetchone()[0]
        self.assertGreater(with_script, 20, "Must contain original language scripts")

    def test_fts5_and_vector_search(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT article_title, section_title
            FROM sections_fts
            WHERE sections_fts MATCH 'golem*'
        """)
        results = cur.fetchall()
        self.assertGreaterEqual(len(results), 1, "FTS5 query for 'golem*' must return matches")

    def test_cli_execution_suite(self):
        cli_path = os.path.join(BASE_DIR, "cli.py")
        
        # 1. catalog
        res = subprocess.run([sys.executable, cli_path, "catalog"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Corpus Document Catalog", res.stdout)

        # 2. hybrid search
        res_search = subprocess.run([sys.executable, cli_path, "search", "golem", "--mode", "hybrid"], capture_output=True, text=True)
        self.assertEqual(res_search.returncode, 0)
        self.assertIn("Hybrid Search Engine", res_search.stdout)

        # 3. analyze
        res_analyze = subprocess.run([sys.executable, cli_path, "analyze"], capture_output=True, text=True)
        self.assertEqual(res_analyze.returncode, 0)
        self.assertIn("Sentiment Inversion", res_analyze.stdout)

        # 4. jokes
        res_jokes = subprocess.run([sys.executable, cli_path, "jokes", "--tradition", "Sephardic"], capture_output=True, text=True)
        self.assertEqual(res_jokes.returncode, 0)
        self.assertIn("Djohá", res_jokes.stdout)

    def test_ml_dataset_exports(self):
        cli_path = os.path.join(BASE_DIR, "cli.py")
        
        # Hugging Face Instruction JSONL export
        jsonl_path = os.path.join(BASE_DIR, "test_instruct.jsonl")
        res_hf = subprocess.run([sys.executable, cli_path, "export", "--format", "hf_instruct", "--output", jsonl_path], capture_output=True, text=True)
        self.assertEqual(res_hf.returncode, 0)
        self.assertTrue(os.path.exists(jsonl_path))
        with open(jsonl_path) as f:
            lines = f.readlines()
        self.assertGreaterEqual(len(lines), 100)
        if os.path.exists(jsonl_path):
            os.remove(jsonl_path)

        # Parquet export
        parquet_path = os.path.join(BASE_DIR, "test_export.parquet")
        res_pq = subprocess.run([sys.executable, cli_path, "export", "--format", "parquet", "--output", parquet_path], capture_output=True, text=True)
        self.assertEqual(res_pq.returncode, 0)
        self.assertTrue(os.path.exists(parquet_path))
        if os.path.exists(parquet_path):
            os.remove(parquet_path)

if __name__ == "__main__":
    unittest.main()
