import hashlib
import os
from datetime import date
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import psycopg2.extras

from .db import connect
from .schema import SCHEMA_SQL


load_dotenv()

app = FastAPI(title="CaloTrack API", version="0.1.0")

cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


@app.on_event("startup")
def _startup() -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        conn.commit()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class AuthBody(BaseModel):
    group_id: str = Field(min_length=1)
    password: str = Field(min_length=1)


@app.post("/auth/register")
def register(body: AuthBody) -> dict[str, Any]:
    gid = body.group_id.strip()
    pw_hash = hash_pw(body.password)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT group_id FROM accounts WHERE group_id=%s", (gid,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Group already exists")
            cur.execute("INSERT INTO accounts (group_id, password) VALUES (%s, %s)", (gid, pw_hash))
        conn.commit()
    return {"group_id": gid}


@app.post("/auth/login")
def login(body: AuthBody) -> dict[str, Any]:
    gid = body.group_id.strip()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password FROM accounts WHERE group_id=%s", (gid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Group not found")
            if row[0] != hash_pw(body.password):
                raise HTTPException(status_code=401, detail="Invalid credentials")
    # Pas de session serveur pour l’instant : le front renverra group_id + password à chaque call.
    return {"group_id": gid}


class UserBody(BaseModel):
    name: str = Field(min_length=1)


def _auth_group(conn, gid: str, password: str) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT password FROM accounts WHERE group_id=%s", (gid,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Group not found")
        if row[0] != hash_pw(password):
            raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/groups/{group_id}/users")
def list_users(group_id: str, password: str) -> dict[str, Any]:
    with connect() as conn:
        _auth_group(conn, group_id, password)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT name FROM users WHERE group_id=%s ORDER BY name ASC", (group_id,))
            rows = cur.fetchall()
    return {"users": [r["name"] for r in rows]}


@app.post("/groups/{group_id}/users")
def add_user(group_id: str, password: str, body: UserBody) -> dict[str, Any]:
    name = body.name.strip()
    with connect() as conn:
        _auth_group(conn, group_id, password)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (name, group_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (name, group_id),
            )
        conn.commit()
    return {"ok": True}


@app.delete("/groups/{group_id}/users/{name}")
def delete_user(group_id: str, name: str, password: str) -> dict[str, Any]:
    with connect() as conn:
        _auth_group(conn, group_id, password)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE name=%s AND group_id=%s", (name, group_id))
        conn.commit()
    return {"ok": True}


class FoodBody(BaseModel):
    name: str = Field(min_length=1)
    cal_100g: float = Field(ge=0)


@app.get("/foods")
def list_foods() -> dict[str, Any]:
    with connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT name, cal_100g FROM foods ORDER BY name ASC")
            rows = cur.fetchall()
    return {"foods": rows}


@app.put("/foods")
def upsert_food(body: FoodBody) -> dict[str, Any]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO foods (name, cal_100g) VALUES (%s, %s) "
                "ON CONFLICT (name) DO UPDATE SET cal_100g = EXCLUDED.cal_100g",
                (body.name.strip(), body.cal_100g),
            )
        conn.commit()
    return {"ok": True}


class MealBody(BaseModel):
    date: date
    label: str = Field(min_length=1)
    user: str = Field(min_length=1)
    calories: float = Field(ge=0)


@app.get("/groups/{group_id}/meals")
def list_meals(group_id: str, password: str, day: date | None = None) -> dict[str, Any]:
    with connect() as conn:
        _auth_group(conn, group_id, password)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if day is None:
                cur.execute(
                    'SELECT id, date, "user", label, calories FROM meal_logs WHERE group_id=%s ORDER BY date DESC, id DESC',
                    (group_id,),
                )
            else:
                cur.execute(
                    'SELECT id, date, "user", label, calories FROM meal_logs WHERE group_id=%s AND date=%s ORDER BY id ASC',
                    (group_id, day),
                )
            rows = cur.fetchall()
    return {"meals": rows}


@app.post("/groups/{group_id}/meals")
def add_meal(group_id: str, password: str, body: MealBody) -> dict[str, Any]:
    with connect() as conn:
        _auth_group(conn, group_id, password)
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO meal_logs (date, label, "user", calories, group_id) VALUES (%s, %s, %s, %s, %s) RETURNING id',
                (body.date, body.label.strip(), body.user.strip(), body.calories, group_id),
            )
            meal_id = cur.fetchone()[0]
        conn.commit()
    return {"id": meal_id}


@app.delete("/groups/{group_id}/meals/{meal_id}")
def delete_meal(group_id: str, meal_id: int, password: str) -> dict[str, Any]:
    with connect() as conn:
        _auth_group(conn, group_id, password)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM meal_logs WHERE id=%s AND group_id=%s", (meal_id, group_id))
        conn.commit()
    return {"ok": True}

