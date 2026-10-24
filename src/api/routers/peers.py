"""
Day 40 - Peer Groups API

Endpoint:
    GET /api/v1/peers/{group_name}
"""

import sqlite3

from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/peers",
    tags=["Peers"],
)


DB_PATH = "database/n100.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# GET PEER GROUP
# ============================================================


@router.get("/{group_name}")
def get_peer_group(group_name: str):
    """
    Return all companies belonging to a peer group.

    Includes percentile ranks for the available peer metrics.
    """

    conn = get_connection()

    try:

        # ------------------------------------------------------
        # CHECK PEER GROUP EXISTS
        # ------------------------------------------------------

        group_row = conn.execute(
            """
            SELECT peer_group_name
            FROM peer_groups
            WHERE LOWER(TRIM(peer_group_name))
                  = LOWER(TRIM(?))
            LIMIT 1
            """,
            (group_name,),
        ).fetchone()

        if group_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown peer group: {group_name}",
            )

        canonical_group = group_row["peer_group_name"]

        # ------------------------------------------------------
        # GET PEER COMPANIES
        # ------------------------------------------------------

        companies = conn.execute(
            """
            SELECT
                company_id,
                peer_group_name,
                is_benchmark
            FROM peer_groups
            WHERE LOWER(TRIM(peer_group_name))
                  = LOWER(TRIM(?))
            ORDER BY
                is_benchmark DESC,
                company_id
            """,
            (canonical_group,),
        ).fetchall()

        # ------------------------------------------------------
        # GET PERCENTILE DATA
        # ------------------------------------------------------

        percentile_rows = conn.execute(
            """
            SELECT
                company_id,
                metric,
                value,
                percentile_rank,
                year
            FROM peer_percentiles
            WHERE LOWER(TRIM(peer_group_name))
                  = LOWER(TRIM(?))
            ORDER BY
                company_id,
                metric
            """,
            (canonical_group,),
        ).fetchall()

        # ------------------------------------------------------
        # BUILD PERCENTILE LOOKUP
        # ------------------------------------------------------

        percentile_lookup = {}

        for row in percentile_rows:

            company_id = row["company_id"]
            metric = row["metric"]

            if company_id not in percentile_lookup:
                percentile_lookup[company_id] = {}

            percentile_lookup[company_id][metric] = {
                "value": row["value"],
                "percentile_rank": row["percentile_rank"],
                "year": row["year"],
            }

        # ------------------------------------------------------
        # BUILD COMPANY RESULTS
        # ------------------------------------------------------

        results = []

        for company in companies:

            company_id = company["company_id"]

            metrics = percentile_lookup.get(company_id, {})

            results.append(
                {
                    "company_id": company_id,
                    "is_benchmark": bool(company["is_benchmark"]),
                    "metrics": metrics,
                }
            )

        # ------------------------------------------------------
        # DETERMINE METRIC COUNT
        # ------------------------------------------------------

        metric_names = sorted(
            {row["metric"] for row in percentile_rows if row["metric"] is not None}
        )

        # ------------------------------------------------------
        # RESPONSE
        # ------------------------------------------------------

        return {
            "peer_group": canonical_group,
            "count": len(results),
            "metric_count": len(metric_names),
            "metrics": metric_names,
            "companies": results,
        }

    finally:
        conn.close()


# ============================================================
# OPTIONAL ROOT ENDPOINT
# ============================================================


@router.get("")
def peers_root():
    """
    Return available peer groups.
    """

    conn = get_connection()

    try:

        rows = conn.execute("""
            SELECT
                peer_group_name,
                COUNT(*) AS company_count
            FROM peer_groups
            GROUP BY peer_group_name
            ORDER BY peer_group_name
            """).fetchall()

        return {
            "count": len(rows),
            "peer_groups": [
                {
                    "peer_group_name": row["peer_group_name"],
                    "company_count": row["company_count"],
                }
                for row in rows
            ],
        }

    finally:
        conn.close()
