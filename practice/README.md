# Laptop practice harness

Practise the PySpark lessons on your laptop with a local SparkSession and Delta Lake.

## Set up

1. Install Java 17 or 21. Check with `java -version`.
2. From the repository root:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e . --group spark
   ```

   The first test run downloads the Delta Lake JAR from Maven Central.

   Use a separate virtual environment from the main `dev` one. PySpark 4.0.4 fails with pandas 3.x (`ImportError: cannot import name '_builtin_table'`), so the `spark` group pins pandas 2.x.

## Use

- Write your answers in `practice/exercises/`. Each file matches a lesson id.
- Run your answers: `pytest practice`
- Run the reference answers: `pytest practice --solutions`

A failing test names the behaviour your code misses. Read the test before you look at the solution.
