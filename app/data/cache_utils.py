"""Cache générique à durée de vie (TTL), partagé par les modules macro et
dérivés : évite de marteler des API tierces à chaque changement d'actif.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def connect(cache_path: Path) -> sqlite3.Connection:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cache_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ttl_cache (
            cle TEXT PRIMARY KEY,
            valeur_json TEXT NOT NULL,
            enregistre_le TEXT NOT NULL
        )
        """
    )
    return conn


def lire(conn: sqlite3.Connection, cle: str, ttl_secondes: int) -> Any | None:
    row = conn.execute("SELECT valeur_json, enregistre_le FROM ttl_cache WHERE cle = ?", (cle,)).fetchone()
    if row is None:
        return None
    valeur_json, enregistre_le = row
    age = (datetime.now(tz=timezone.utc) - datetime.fromisoformat(enregistre_le)).total_seconds()
    if age > ttl_secondes:
        return None
    return json.loads(valeur_json)


def ecrire(conn: sqlite3.Connection, cle: str, valeur: Any) -> None:
    conn.execute(
        """
        INSERT INTO ttl_cache (cle, valeur_json, enregistre_le) VALUES (?, ?, ?)
        ON CONFLICT (cle) DO UPDATE SET valeur_json = excluded.valeur_json, enregistre_le = excluded.enregistre_le
        """,
        (cle, json.dumps(valeur), datetime.now(tz=timezone.utc).isoformat()),
    )
    conn.commit()
