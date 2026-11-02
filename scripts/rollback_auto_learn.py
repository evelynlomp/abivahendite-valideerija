"""
AUTO_LEARN impordi tagasivõtmise (rollback) tööriist.

Kasutamine:
1. Konkreetse impordipartii eemaldamine SQL-tasemel (säilitades muud spetsialisti kinnitused):
   .\.venv\Scripts\python.exe scripts\rollback_auto_learn.py --batch-id BATCH_SEPT_15_09_AUTO_LEARN

2. Täielik andmebaasi taastamine impordieelsest varukoopiast:
   .\.venv\Scripts\python.exe scripts\rollback_auto_learn.py --restore-backup
"""

import os
import sys
import argparse
import sqlite3

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from src.knowledge_base import KnowledgeBase


def restore_from_backup(db_path: str, backup_path: str) -> None:
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Varukoopia faili ei leitud: {backup_path}")
    src_conn = sqlite3.connect(backup_path)
    dst_conn = sqlite3.connect(db_path)
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    print(f"Andmebaas edukalt taastatud varukoopiast: {backup_path}")


def main():
    parser = argparse.ArgumentParser(description="Võtab tagasi AUTO_LEARN impordi.")
    parser.add_argument(
        "--batch-id",
        default="BATCH_SEPT_15_09_AUTO_LEARN",
        help="Impordipartii ID (vaikimisi BATCH_SEPT_15_09_AUTO_LEARN)"
    )
    parser.add_argument(
        "--restore-backup",
        action="store_true",
        help="Taasta kogu valideer.db impordieelsest varukoopia failist"
    )
    parser.add_argument(
        "--backup-file",
        default=os.path.join(ROOT_DIR, "data", "backups", "valideer_pre_auto_learn_latest.db"),
        help="Varukoopia faili rada"
    )
    args = parser.parse_args()

    db_path = os.path.join(ROOT_DIR, "data", "valideer.db")

    if args.restore_backup:
        restore_from_backup(db_path, args.backup_file)
    else:
        kb = KnowledgeBase(db_path=db_path)
        res = kb.rollback_import(batch_id=args.batch_id)
        print(
            f"Partii '{args.batch_id}' edukalt tagasi võetud: "
            f"kustutati {res['kustutatud_teadmisi']} teadmist, "
            f"{res['kustutatud_variandireegleid']} variandireeglit ja "
            f"{res['kustutatud_aliaseid']} aliase seost."
        )


if __name__ == "__main__":
    main()
