from fastapi import APIRouter, HTTPException
from database import get_database
from models import DBQueryRequest
import re

router = APIRouter(prefix="/api/db", tags=["database"])


@router.get("/stats")
async def db_stats():
    db = get_database()
    return {"success": True, "stats": db.get_db_stats()}


@router.get("/tables")
async def db_tables():
    db = get_database()
    tables = db.get_table_info()
    return {"success": True, "tables": tables, "count": len(tables)}


@router.get("/table/{table_name}")
async def db_table_data(table_name: str, page: int = 1, per_page: int = 50):
    db = get_database()
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
        raise HTTPException(status_code=400, detail="Invalid table name")
    tables = db.get_table_info()
    valid_names = [t["name"] for t in tables]
    if table_name not in valid_names:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    data = db.get_table_data(table_name, page, per_page)
    return {"success": True, **data}


@router.get("/table/{table_name}/schema")
async def db_table_schema(table_name: str):
    db = get_database()
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
        raise HTTPException(status_code=400, detail="Invalid table name")
    conn = db._get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        columns = [
            {"name": r["name"], "type": r["type"], "not_null": bool(r["notnull"]), "default": r["dflt_value"]}
            for r in cursor.fetchall()
        ]
        return {"success": True, "table": table_name, "columns": columns}
    finally:
        conn.close()


@router.post("/query")
async def db_custom_query(body: DBQueryRequest):
    db = get_database()
    result = db.execute_readonly_query(body.sql)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"success": True, **result}
