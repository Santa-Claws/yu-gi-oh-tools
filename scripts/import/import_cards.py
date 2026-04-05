#!/usr/bin/env python3
"""Standalone script to trigger card import via Celery task.

Usage:
    python scripts/import/import_cards.py [--limit N]
"""
import argparse
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../apps/ai"))

from app.worker.tasks.import_tasks import import_cards_task


def main():
    parser = argparse.ArgumentParser(description="Import Yu-Gi-Oh cards from YGOProDeck API")
    parser.add_argument("--limit", type=int, default=None, help="Max cards to import (default: all)")
    parser.add_argument("--sync", action="store_true", help="Run synchronously instead of via Celery")
    args = parser.parse_args()

    if args.sync:
        import asyncio
        from app.worker.tasks.import_tasks import _run_import
        result = asyncio.run(_run_import(args.limit))
        print(f"Import complete: {result}")
    else:
        task = import_cards_task.delay(limit=args.limit)
        print(f"Import task queued: {task.id}")


if __name__ == "__main__":
    main()
