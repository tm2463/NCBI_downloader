# NCBI Downloader

Python script to download test data from the NCBI FTP server

## Setup
```bash
# install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# download the ncbi summary file
curl -O https://ftp.ncbi.nlm.nih.gov/genomes/refseq/bacteria/assembly_summary.txt
```

## Usage

The script loads the NCBI assembly summary file into a local SQLite database (`summary.db`), so you can select exactly which genomes to download using standard SQL against the `summary` table. Column names match the headers in `assembly_summary.txt` (e.g. `organism_name`, `assembly_level`, `taxid`, `ftp_path`, etc).

```bash
python ncbi_downloader.py -s assembly_summary.txt -q "SQL_QUERY" -o output_dir
```

> **Note:** On first run, the script builds `output_dir/summary.db` from your summary TSV. On subsequent runs, if `summary.db` already exists in your current dir, it is reused as-is and the `-s/--summary` file is **not** re-read. If you update `assembly_summary.txt` and want the database rebuilt, delete `summary.db` first.

> **Note:** The first query will take longer than any subsequent runs due to the needs to build summary.db first.

### Arguments

| Flag | Description |
|------|-------------|
| `-s`, `--summary` | Path to the NCBI summary TSV (e.g. `assembly_summary.txt`). Only used if `summary.db` doesn't already exist in `outdir` |
| `-q`, `--query` | SQL query to select rows from the `summary` table |
| `-p`, `--preview` | Preview the number of matching results without downloading |
| `-o`, `--outdir` | Output directory (default: current directory) |
| `-t`, `--file_type` | FTP file suffix to download (default: `_genomic.fna.gz`) |

### Previewing a query

Before downloading, use `--preview` to check how many assemblies match:

```bash
python ncbi_downloader.py \
  -s assembly_summary.txt \
  -q "SELECT * FROM summary WHERE organism_name LIKE '%Escherichia coli%'" \
  --preview
```

### Example queries

**Download all complete genomes for a species**
```sql
SELECT * FROM summary
WHERE organism_name LIKE '%Escherichia coli%'
AND assembly_level = 'Complete Genome'
```

**Download reference genomes only**
```sql
SELECT * FROM summary
WHERE refseq_category = 'reference genome'
```

**Download a random subset of 50 genomes for a genus**
```sql
SELECT * FROM summary
WHERE organism_name LIKE '%Salmonella%'
ORDER BY RANDOM()
LIMIT 50
```

**Download by specific taxid**
```sql
SELECT * FROM summary
WHERE taxid = 562
```

**Exclude genomes flagged by RefSeq**
```sql
SELECT * FROM summary
WHERE organism_name LIKE '%Klebsiella pneumoniae%'
AND excluded_from_refseq IS NULL
```

**Download genomes released after a given date**
```sql
SELECT * FROM summary
WHERE seq_rel_date >= '2022-01-01'
```

### Running multiple queries against the same summary

Since `summary.db` is reused once created, you can run several queries back-to-back without re-parsing the TSV each time — just point them at the same `-o outdir`:

```bash
python ncbi_downloader.py -s assembly_summary.txt -q "SELECT * FROM summary WHERE taxid = 562" -o output_dir
python ncbi_downloader.py -s assembly_summary.txt -q "SELECT * FROM summary WHERE taxid = 573" -o output_dir
```

### Downloading protein FASTA instead of genomic FASTA

Use `-t` to change the file suffix:

```bash
python ncbi_downloader.py \
  -s assembly_summary.txt \
  -q "SELECT * FROM summary WHERE assembly_level = 'Complete Genome' LIMIT 10" \
  -t "_protein.faa.gz" \
  -o output_dir
```

Downloaded files are written to `output_dir/data/`, and each file's MD5 checksum is validated against `md5checksums.txt` on the NCBI FTP server before saving.
