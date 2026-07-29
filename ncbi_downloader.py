#!/usr/bin/env python3

from pathlib import Path
import os
import argparse
import sqlite3 
import hashlib

from tqdm import tqdm
import pandas as pd
import requests


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-s", "--summary", 
        type=str, 
        required=True, 
        help="NCBI summary tsv (e.g. path/to/assembly_summary.txt)"
    )
    parser.add_argument(
        "-q", "--query",
        type=str, 
        required=True,
        help="SQL query to select data for download"
    )
    parser.add_argument(
        "-p", "--preview", 
        action="store_true", 
        help="Preview query results without downloading"
    )
    parser.add_argument(
        "-o", "--outdir", 
        type=Path, 
        default=Path.cwd(), 
        help="Path to output dir"
    )
    parser.add_argument(
        "-t", "--file_type", 
        type=str, 
        default="_genomic.fna.gz", 
        help="FTP suffix (i.e. '_genomic.fna.gz)"
    )
    return parser.parse_args()


def parse_summary(summary: Path) -> pd.DataFrame:
    return pd.read_csv(summary, sep='\t', skiprows=1)


def validate_file(ftp: str, reference: str, md5local: str) -> bool:
    source = requests.get(f"{ftp}/md5checksums.txt")

    with open("tmp.txt", "wb") as tmp:
        tmp.write(source.content)
    
    df = pd.read_csv("tmp.txt", sep=r'\s+', header=None)
    filtered_df = df[df[1] == f"./{reference}"]
    return filtered_df[0].values[0] == md5local


def main():
    args = parse_args()
    outdir = args.outdir
    outdir.mkdir(exist_ok=True, parents=True)

    summary_db = Path.cwd() / "summary.db"

    if not summary_db.exists():
        print("\nCreating summary.db\n")
        df = parse_summary(args.summary)
        conn = sqlite3.connect(summary_db)
        df.to_sql("summary", conn, if_exists="replace", index=False)
    else:
        conn = sqlite3.connect(summary_db)

    result = pd.read_sql_query(args.query, conn)

    if args.preview:
        print(f"\nQuery will return {len(result)} items:\n")
        print(result[["#assembly_accession", "species_taxid", "organism_name", "infraspecific_name", "assembly_level", "gc_percent", "contig_count"]])
        return

    data = outdir / "data"
    data.mkdir(exist_ok=True, parents=True)

    print(f"Fetching {len(result)} items")
    for _, row in tqdm(result.iterrows(), total=len(result), desc="Progress"):
        ftp = row["ftp_path"]
        target = ftp.split("/")[-2]
        link = f"{ftp}{target}{args.file_type}"
        outfile = data / f"{target}{args.file_type}"

        try:
            response = requests.get(link, timeout=120)
        except Exception as e:
            print(f"{ftp} failed to download: {e}, skipping...")
            with open("failed_links.txt", "a") as fail:
                fail.write(f"{ftp}")
            continue

        md5local = hashlib.md5(response.content).hexdigest()

        if validate_file(ftp, f"{target}{args.file_type}", md5local):
            with open(outfile, "wb") as out_f:
                out_f.write(response.content)
        else:
            print(f"{ftp} md5 mismatch, skipping...")

    os.remove("tmp.txt")


if __name__ == "__main__":
    main()
