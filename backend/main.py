from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import os

app = FastAPI(title="Nilaavathy Plastics - GST Billing")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), "invoices.db")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            invoice_date TEXT NOT NULL,
            buyer_name TEXT NOT NULL,
            buyer_address TEXT DEFAULT '',
            buyer_gstin TEXT DEFAULT '',
            vehicle_number TEXT DEFAULT '',
            subtotal REAL NOT NULL DEFAULT 0,
            sgst REAL NOT NULL DEFAULT 0,
            cgst REAL NOT NULL DEFAULT 0,
            grand_total REAL NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            s_no INTEGER NOT NULL,
            description TEXT NOT NULL,
            hsn TEXT DEFAULT '',
            quantity REAL NOT NULL DEFAULT 0,
            rate REAL NOT NULL DEFAULT 0,
            amount REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


init_db()


# ---------- Pydantic Models ----------

class InvoiceItem(BaseModel):
    s_no: int
    description: str
    hsn: Optional[str] = ""
    quantity: float
    rate: float
    amount: float


class InvoiceCreate(BaseModel):
    invoice_number: str
    invoice_date: str
    buyer_name: str
    buyer_address: Optional[str] = ""
    buyer_gstin: Optional[str] = ""
    vehicle_number: Optional[str] = ""
    subtotal: float
    sgst: float
    cgst: float
    grand_total: float
    items: List[InvoiceItem]


# ---------- API Routes ----------

@app.get("/api/next-invoice-number")
def get_next_invoice_number():
    conn = get_db()
    row = conn.execute(
        "SELECT MAX(CAST(invoice_number AS INTEGER)) as max_num FROM invoices"
    ).fetchone()
    conn.close()
    max_num = row["max_num"] or 0
    return {"next_number": str(max_num + 1).zfill(3)}


@app.get("/api/invoices")
def list_invoices():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM invoices ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/invoices")
def create_invoice(invoice: InvoiceCreate):
    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO invoices
               (invoice_number, invoice_date, buyer_name, buyer_address,
                buyer_gstin, vehicle_number, subtotal, sgst, cgst, grand_total)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                invoice.invoice_number, invoice.invoice_date,
                invoice.buyer_name, invoice.buyer_address,
                invoice.buyer_gstin, invoice.vehicle_number,
                invoice.subtotal, invoice.sgst, invoice.cgst, invoice.grand_total,
            ),
        )
        invoice_id = cursor.lastrowid
        for item in invoice.items:
            conn.execute(
                """INSERT INTO invoice_items
                   (invoice_id, s_no, description, hsn, quantity, rate, amount)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (invoice_id, item.s_no, item.description, item.hsn,
                 item.quantity, item.rate, item.amount),
            )
        conn.commit()
        return {"id": invoice_id, "invoice_number": invoice.invoice_number}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Invoice number already exists")
    finally:
        conn.close()


@app.get("/api/invoices/{invoice_id}")
def get_invoice(invoice_id: int):
    conn = get_db()
    invoice = conn.execute(
        "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
    ).fetchone()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    items = conn.execute(
        "SELECT * FROM invoice_items WHERE invoice_id = ? ORDER BY s_no",
        (invoice_id,),
    ).fetchall()
    conn.close()
    result = dict(invoice)
    result["items"] = [dict(i) for i in items]
    return result


@app.delete("/api/invoices/{invoice_id}")
def delete_invoice(invoice_id: int):
    conn = get_db()
    conn.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    conn.commit()
    conn.close()
    return {"message": "Deleted successfully"}


# ---------- Serve Frontend ----------

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/invoices")
def serve_invoices():
    return FileResponse(os.path.join(FRONTEND_DIR, "invoices.html"))


@app.get("/view")
def serve_view():
    return FileResponse(os.path.join(FRONTEND_DIR, "view.html"))


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
