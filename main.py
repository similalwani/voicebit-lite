from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List
from datetime import datetime
from groq import Groq
import json
import sqlite3

app = FastAPI()

def init_db():
    conn = sqlite3.connect("orders.db")
    conn.execute("""
            CREATE TABLE IF NOT EXISTS orders(
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 items TEXT,
                 total REAL,
                 status TEXT,
                 created_at TEXT
            )
        """)
    conn.commit()
    conn.close()

init_db()


# ---------------------------------------------------------------------------
# Data Models
# A "model" is just a blueprint that describes the shape of data.
# Pydantic makes sure the data we receive matches that shape.
# ---------------------------------------------------------------------------

class ParseRequest(BaseModel):
    text: str

class OrderItem(BaseModel):
    item_id: int       # which menu item
    quantity: int      # how many

class OrderRequest(BaseModel):
    items: List[OrderItem]   # a list of OrderItems

class StatusUpdate(BaseModel):
    status: str   # the new status we want to set

#-----------
# ---------------------------------------------------------------------------
# In-memory store
# Think of this as a dictionary/notepad where we keep all orders.
# Key = order ID (a number), Value = the order dict.
# This resets every time the server restarts — no database yet.
# ---------------------------------------------------------------------------

#orders = {}           # our notepad
#order_counter = 1     # auto-incrementing ID, like a ticket number
#-----------


#UPDATE:Autoincrement replaces order_counter now as sqlite is our store now.


# This is our restaurant menu — just a list of items
menu = [
    {"id": 1, "name": "Pepperoni Pizza", "size": "large", "price": 14.99},
    {"id": 2, "name": "Margherita Pizza", "size": "large", "price": 12.99},
    {"id": 3, "name": "Garlic Bread", "size": "regular", "price": 5.99},
    {"id": 4, "name": "Coca Cola", "size": "medium", "price": 2.49},
    {"id": 5, "name": "Caesar Salad", "size": "regular", "price": 8.99},
]

system_prompt = f"""You are a restaurant ordering assistant.
Here is the menu: {menu}

Return ONLY a JSON array like: [{{"item_id": 1, "quantity": 2}}]
If nothing matches, return: [] 
"""
@app.get("/")
def home():
    return {"message": "VoiceBit Lite is running"}

@app.get("/menu")
def get_menu():
    return {"Menu" : menu}

# ---------------------------------------------------------------------------
# CREATE — POST /order
# The client sends a list of items. We validate them against the menu,
# calculate the total, save the order, and return a confirmation.
# ---------------------------------------------------------------------------

@app.post("/order")
def create_order(order_request: OrderRequest):

    # Build a lookup dict from the menu so we can find items by ID quickly.
    # e.g. { 1: {"id": 1, "name": "Pepperoni Pizza", ...}, 2: {...} }
    menu_lookup = {item["id"]: item for item in menu}

    order_items = []
    total = 0.0

    for entry in order_request.items:
        # Check that the requested item actually exists on the menu
        if entry.item_id not in menu_lookup:
            raise HTTPException(
                status_code=404,
                detail=f"Menu item with id {entry.item_id} not found"
            )
        menu_item = menu_lookup[entry.item_id]
        line_total = menu_item["price"] * entry.quantity
        total += line_total
        order_items.append({
            "item_id": entry.item_id,
            "name": menu_item["name"],
            "quantity": entry.quantity,
            "line_total": round(line_total, 2)
        })

    conn = sqlite3.connect("orders.db")
    cursor = conn.execute(
        "INSERT INTO orders (items, total, status, created_at) VALUES (?, ?, ?, ?)",
        (json.dumps(order_items), round(total, 2), "pending", datetime.now().isoformat())
    )
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()

    order = {
        "id": order_id,
        "items": order_items,
        "total": round(total, 2),
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    return {"message": "Order created!", "order": order}



@app.get("/order/{order_id}")
def get_order(order_id: int):
    conn = sqlite3.connect("orders.db")
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return {"order": {"id": row[0], "items": json.loads(row[1]), "total": row[2], "status": row[3], "created_at": row[4]}}


VALID_STATUSES = ["pending", "confirmed", "ready", "done", "paid"]

@app.patch("/order/{order_id}/status")
def update_order_status(order_id: int, update: StatusUpdate):
    conn = sqlite3.connect("orders.db")
    row = conn.execute("SELECT id FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    if update.status not in VALID_STATUSES:
        conn.close()
        raise HTTPException(status_code=400)
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (update.status, order_id))
    conn.commit()
    conn.close()
    return f"Order status: {update.status}"

@app.post("/pay/{order_id}")
def pay_order(order_id: int):
    conn = sqlite3.connect("orders.db")
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    if row[3] == "paid":
        conn.close()
        raise HTTPException(status_code=400, detail="Order already paid")
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", ("paid", order_id))
    conn.commit()
    conn.close()
    return {
        "message": "Payment successful",
        "order_id": order_id,
        "amount_charged": row[2],
        "status": "paid"
    }


@app.post("/parse-order")
def parse_order(request: ParseRequest):

    client = Groq()

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.text}
        ]
    )
    
    raw = response.choices[0].message.content

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="AI returned invalid JSON")
    
    return {"items": parsed}

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    client = Groq()

    contents = await audio.read()

    transcription = client.audio.transcriptions.create(
        file=(audio.filename, contents),
        model='whisper-large-v3'
    )

    return {'transcript': transcription.text}

@app.post("/voice-order")
async def voice_order(audio:UploadFile = File(...)):

    client = Groq()

    #step 1: transcribe
    contents = await audio.read()

    transcription = client.audio.transcriptions.create(
        file=(audio.filename, contents),
        model='whisper-large-v3'
    )

    #step 2 - parse intent
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcription.text}
        ]
    )
    
    raw = response.choices[0].message.content

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="AI returned invalid JSON")

    # step 3 — build and save the order
    menu_lookup = {item["id"]: item for item in menu}
    order_items = []
    total = 0.0

    for entry in parsed:
        if entry['item_id'] not in menu_lookup:
            raise HTTPException(
                status_code=422,
                detail=f"AI returned unknown item ID: {entry['item_id']}"
            )
        menu_item = menu_lookup[entry["item_id"]]
        line_total = menu_item["price"] * entry["quantity"]
        total += line_total
        order_items.append({
            "item_id": entry["item_id"],
            "name": menu_item["name"],
            "quantity": entry["quantity"],
            "line_total": round(line_total, 2)
        })

    conn = sqlite3.connect("orders.db")
    cursor = conn.execute(
        "INSERT INTO orders (items, total, status, created_at) VALUES (?, ?, ?, ?)",
        (json.dumps(order_items), round(total, 2), "pending", datetime.now().isoformat())
    )
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()

    order = {
        "id": order_id,
        "items": order_items,
        "total": round(total, 2),
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    return {"message": "Order created from voice!", "order": order}