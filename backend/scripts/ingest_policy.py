"""
售后政策 Chroma 向量化脚本。
可重复运行：每次会先清空旧 collection，再重新写入。

用法:
    python scripts/ingest_policy.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from app.rag.embeddings import get_embeddings
from app.rag.vectorstore import get_vectorstore


POLICY_FILE = ROOT / "knowledge" / "after_sales_policy.md"


def split_policy(text: str):
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "title"),
            ("##", "chapter"),
            ("###", "section"),
        ]
    )
    header_splits = header_splitter.split_text(text)

    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        length_function=len,
    )
    final_splits = char_splitter.split_documents(header_splits)
    return final_splits


def main():
    if not POLICY_FILE.exists():
        print(f"ERROR: policy file not found: {POLICY_FILE}")
        sys.exit(1)

    print(f"Reading policy file: {POLICY_FILE}")
    with open(POLICY_FILE, "r", encoding="utf-8") as f:
        policy_text = f.read()

    print(f"Splitting policy document...")
    chunks = split_policy(policy_text)
    print(f"  -> {len(chunks)} chunks generated")

    print(f"Loading embeddings model...")
    embeddings = get_embeddings()

    vectorstore = get_vectorstore()

    existing = vectorstore.get()
    existing_count = len(existing.get("ids", [])) if existing else 0
    if existing_count > 0:
        print(f"Clearing {existing_count} existing vectors...")
        vectorstore.delete(ids=existing["ids"])

    print(f"Adding {len(chunks)} chunks to Chroma...")
    vectorstore.add_documents(documents=chunks)

    verify = vectorstore.get()
    print(f"\nDone. Total vectors in collection: {len(verify.get('ids', []))}")

    print(f"\n--- Quick verification ---")
    test_queries = ["耳机保修多久", "食品变质怎么退", "换货需要审核吗"]
    for q in test_queries:
        results = vectorstore.similarity_search(q, k=2)
        print(f"\nQuery: '{q}'")
        for d in results:
            meta = d.metadata
            label = meta.get("section") or meta.get("chapter") or meta.get("title", "")
            preview = d.page_content[:80].replace("\n", " ")
            print(f"  [{label}] {preview}...")


if __name__ == "__main__":
    main()