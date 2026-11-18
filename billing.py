"""
साधं ऑफलाईन बिलिंग सॉफ्टवेअर (Desktop)
- Python 3 + Tkinter + SQLite (काहीही extra install नको)
- Run: python billing.py
"""
import os
import sqlite3
import webbrowser
import html
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# ---------- सेटिंग्ज (इथे बदला) ----------
SHOP_NAME = "माझे दुकान"
SHOP_ADDRESS = "नागपूर"
SHOP_PHONE = ""
FONT = ("Nirmala UI", 11)
# -----------------------------------------

import sys
if getattr(sys, "frozen", False):      # .exe म्हणून चालत असल्यास exe च्या शेजारी डेटा ठेवा
    BASE = os.path.dirname(sys.executable)
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "billing.db")
BILLS_DIR = os.path.join(BASE, "bills")
os.makedirs(BILLS_DIR, exist_ok=True)


def db():
    return sqlite3.connect(DB_PATH)


def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            price REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS bills(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            customer TEXT,
            total REAL, discount REAL, grand REAL);
        CREATE TABLE IF NOT EXISTS bill_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL,
            name TEXT, price REAL, qty REAL, amount REAL);
        """)


def fmt(x):
    return f"{x:,.2f}"


def build_bill_html(bill_id):
    with db() as c:
        b = c.execute("SELECT id,date,customer,total,discount,grand FROM bills WHERE id=?",
                      (bill_id,)).fetchone()
        items = c.execute("SELECT name,price,qty,amount FROM bill_items WHERE bill_id=?",
                          (bill_id,)).fetchall()
    rows = "".join(
        f"<tr><td>{i}</td><td>{html.escape(n)}</td><td class=r>{fmt(p)}</td>"
        f"<td class=r>{q:g}</td><td class=r>{fmt(a)}</td></tr>"
        for i, (n, p, q, a) in enumerate(items, 1))
    page = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>बिल #{b[0]}</title>
<style>
body{{font-family:'Nirmala UI',Arial,sans-serif;max-width:380px;margin:10px auto;font-size:14px}}
h2,p{{text-align:center;margin:2px}} table{{width:100%;border-collapse:collapse;margin-top:8px}}
th,td{{border-bottom:1px dashed #888;padding:4px;text-align:left}} .r{{text-align:right}}
.tot td{{font-weight:bold;border-bottom:none}}
</style></head><body onload="window.print()">
<h2>{html.escape(SHOP_NAME)}</h2><p>{html.escape(SHOP_ADDRESS)} {html.escape(SHOP_PHONE)}</p><hr>
<p style="text-align:left">बिल क्र.: <b>{b[0]}</b><br>दिनांक: {b[1]}<br>ग्राहक: {html.escape(b[2] or '-')}</p>
<table><tr><th>#</th><th>वस्तू</th><th class=r>दर</th><th class=r>नग</th><th class=r>रक्कम</th></tr>
{rows}
<tr class=tot><td colspan=4 class=r>एकूण</td><td class=r>{fmt(b[3])}</td></tr>
<tr class=tot><td colspan=4 class=r>सूट</td><td class=r>{fmt(b[4])}</td></tr>
<tr class=tot><td colspan=4 class=r>देय रक्कम</td><td class=r>{fmt(b[5])}</td></tr>
</table><p>धन्यवाद! पुन्हा भेट द्या.</p></body></html>"""
    path = os.path.join(BILLS_DIR, f"bill_{bill_id}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return path


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("बिलिंग सॉफ्टवेअर")
        self.geometry("900x620")
        self.option_add("*Font", FONT)
        ttk.Style(self).configure("Treeview", font=FONT, rowheight=26)
        ttk.Style(self).configure("Treeview.Heading", font=(FONT[0], 11, "bold"))

        self.items = []          # (name, price, qty, amount)
        self.prices = {}

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_bill = ttk.Frame(nb)
        self.tab_prod = ttk.Frame(nb)
        self.tab_hist = ttk.Frame(nb)
        nb.add(self.tab_bill, text="  नवीन बिल  ")
        nb.add(self.tab_prod, text="  वस्तू / दर  ")
        nb.add(self.tab_hist, text="  जुनी बिले  ")
        nb.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())

        self.build_bill_tab()
        self.build_prod_tab()
        self.build_hist_tab()
        self.refresh_all()

    # ---------------- नवीन बिल ----------------
    def build_bill_tab(self):
        t = self.tab_bill
        top = ttk.Frame(t); top.pack(fill="x", padx=10, pady=8)
        ttk.Label(top, text="ग्राहकाचे नाव:").grid(row=0, column=0, sticky="w")
        self.customer = ttk.Entry(top, width=30)
        self.customer.grid(row=0, column=1, padx=6, sticky="w")

        add = ttk.LabelFrame(t, text="वस्तू जोडा"); add.pack(fill="x", padx=10, pady=4)
        ttk.Label(add, text="वस्तू").grid(row=0, column=0, padx=6, pady=6)
        self.cb_name = ttk.Combobox(add, width=30)
        self.cb_name.grid(row=0, column=1)
        self.cb_name.bind("<<ComboboxSelected>>", self.on_pick)
        ttk.Label(add, text="दर").grid(row=0, column=2, padx=6)
        self.e_price = ttk.Entry(add, width=10); self.e_price.grid(row=0, column=3)
        ttk.Label(add, text="नग").grid(row=0, column=4, padx=6)
        self.e_qty = ttk.Entry(add, width=8); self.e_qty.insert(0, "1"); self.e_qty.grid(row=0, column=5)
        ttk.Button(add, text="जोडा", command=self.add_item).grid(row=0, column=6, padx=8)
        self.e_qty.bind("<Return>", lambda e: self.add_item())

        cols = ("no", "name", "price", "qty", "amount")
        self.tree = ttk.Treeview(t, columns=cols, show="headings", height=12)
        for c, txt, w in zip(cols, ("#", "वस्तू", "दर", "नग", "रक्कम"), (40, 350, 100, 80, 120)):
            self.tree.heading(c, text=txt)
            self.tree.column(c, width=w, anchor="w" if c == "name" else "e")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)

        bot = ttk.Frame(t); bot.pack(fill="x", padx=10, pady=8)
        ttk.Button(bot, text="निवडलेली ओळ काढा", command=self.remove_item).pack(side="left")
        ttk.Button(bot, text="बिल साफ करा", command=self.clear_bill).pack(side="left", padx=6)

        right = ttk.Frame(bot); right.pack(side="right")
        ttk.Label(right, text="सूट (₹):").grid(row=0, column=0, sticky="e")
        self.e_disc = ttk.Entry(right, width=10); self.e_disc.insert(0, "0")
        self.e_disc.grid(row=0, column=1, padx=6)
        self.e_disc.bind("<KeyRelease>", lambda e: self.update_totals())
        self.lbl_total = ttk.Label(right, text="एकूण: ₹0.00")
        self.lbl_total.grid(row=1, column=0, columnspan=2, sticky="e")
        self.lbl_grand = ttk.Label(right, text="देय: ₹0.00", font=(FONT[0], 14, "bold"))
        self.lbl_grand.grid(row=2, column=0, columnspan=2, sticky="e")
        ttk.Button(right, text="बिल सेव्ह करा व प्रिंट", command=self.save_bill)\
            .grid(row=3, column=0, columnspan=2, pady=6, sticky="e")

    def on_pick(self, _=None):
        p = self.prices.get(self.cb_name.get())
        if p is not None:
            self.e_price.delete(0, "end"); self.e_price.insert(0, f"{p:g}")
            self.e_qty.focus_set(); self.e_qty.select_range(0, "end")

    def add_item(self):
        name = self.cb_name.get().strip()
        try:
            price = float(self.e_price.get())
            qty = float(self.e_qty.get())
        except ValueError:
            return messagebox.showwarning("चूक", "दर आणि नग अचूक संख्या टाका.")
        if not name or qty <= 0 or price < 0:
            return messagebox.showwarning("चूक", "वस्तूचे नाव, दर व नग तपासा.")
        self.items.append((name, price, qty, price * qty))
        self.cb_name.set(""); self.e_price.delete(0, "end")
        self.e_qty.delete(0, "end"); self.e_qty.insert(0, "1")
        self.refresh_items()
        self.cb_name.focus_set()

    def remove_item(self):
        sel = self.tree.selection()
        if sel:
            del self.items[self.tree.index(sel[0])]
            self.refresh_items()

    def clear_bill(self):
        self.items.clear(); self.customer.delete(0, "end")
        self.e_disc.delete(0, "end"); self.e_disc.insert(0, "0")
        self.refresh_items()

    def refresh_items(self):
        self.tree.delete(*self.tree.get_children())
        for i, (n, p, q, a) in enumerate(self.items, 1):
            self.tree.insert("", "end", values=(i, n, fmt(p), f"{q:g}", fmt(a)))
        self.update_totals()

    def totals(self):
        total = sum(i[3] for i in self.items)
        try:
            disc = float(self.e_disc.get() or 0)
        except ValueError:
            disc = 0
        disc = max(0, min(disc, total))
        return total, disc, total - disc

    def update_totals(self):
        total, disc, grand = self.totals()
        self.lbl_total.config(text=f"एकूण: ₹{fmt(total)}")
        self.lbl_grand.config(text=f"देय: ₹{fmt(grand)}")

    def save_bill(self):
        if not self.items:
            return messagebox.showinfo("माहिती", "बिलात एकही वस्तू नाही.")
        total, disc, grand = self.totals()
        with db() as c:
            cur = c.execute(
                "INSERT INTO bills(date,customer,total,discount,grand) VALUES(?,?,?,?,?)",
                (datetime.now().strftime("%d-%m-%Y %H:%M"), self.customer.get().strip(),
                 total, disc, grand))
            bid = cur.lastrowid
            c.executemany(
                "INSERT INTO bill_items(bill_id,name,price,qty,amount) VALUES(?,?,?,?,?)",
                [(bid, *i) for i in self.items])
        webbrowser.open("file://" + build_bill_html(bid))
        self.clear_bill()
        self.refresh_hist()

    # ---------------- वस्तू / दर ----------------
    def build_prod_tab(self):
        t = self.tab_prod
        f = ttk.Frame(t); f.pack(fill="x", padx=10, pady=10)
        ttk.Label(f, text="वस्तूचे नाव").grid(row=0, column=0)
        self.p_name = ttk.Entry(f, width=35); self.p_name.grid(row=0, column=1, padx=6)
        ttk.Label(f, text="दर (₹)").grid(row=0, column=2)
        self.p_price = ttk.Entry(f, width=10); self.p_price.grid(row=0, column=3, padx=6)
        ttk.Button(f, text="सेव्ह / अपडेट", command=self.save_product).grid(row=0, column=4, padx=4)
        ttk.Button(f, text="डिलीट", command=self.delete_product).grid(row=0, column=5)

        self.ptree = ttk.Treeview(t, columns=("name", "price"), show="headings")
        self.ptree.heading("name", text="वस्तू"); self.ptree.heading("price", text="दर")
        self.ptree.column("name", width=500); self.ptree.column("price", width=120, anchor="e")
        self.ptree.pack(fill="both", expand=True, padx=10, pady=6)
        self.ptree.bind("<<TreeviewSelect>>", self.on_prod_select)

    def on_prod_select(self, _=None):
        sel = self.ptree.selection()
        if sel:
            n, p = self.ptree.item(sel[0])["values"]
            self.p_name.delete(0, "end"); self.p_name.insert(0, n)
            self.p_price.delete(0, "end"); self.p_price.insert(0, str(p).replace(",", ""))

    def save_product(self):
        name = self.p_name.get().strip()
        try:
            price = float(self.p_price.get())
        except ValueError:
            return messagebox.showwarning("चूक", "दर अचूक टाका.")
        if not name:
            return messagebox.showwarning("चूक", "वस्तूचे नाव टाका.")
        with db() as c:
            c.execute("INSERT INTO products(name,price) VALUES(?,?) "
                      "ON CONFLICT(name) DO UPDATE SET price=excluded.price", (name, price))
        self.p_name.delete(0, "end"); self.p_price.delete(0, "end")
        self.refresh_all()

    def delete_product(self):
        name = self.p_name.get().strip()
        if name and messagebox.askyesno("खात्री", f"'{name}' डिलीट करायची?"):
            with db() as c:
                c.execute("DELETE FROM products WHERE name=?", (name,))
            self.p_name.delete(0, "end"); self.p_price.delete(0, "end")
            self.refresh_all()

    # ---------------- जुनी बिले ----------------
    def build_hist_tab(self):
        t = self.tab_hist
        self.lbl_today = ttk.Label(t, text="", font=(FONT[0], 12, "bold"))
        self.lbl_today.pack(anchor="w", padx=10, pady=8)
        cols = ("id", "date", "customer", "grand")
        self.htree = ttk.Treeview(t, columns=cols, show="headings")
        for c, txt, w in zip(cols, ("बिल क्र.", "दिनांक", "ग्राहक", "रक्कम"), (80, 160, 300, 120)):
            self.htree.heading(c, text=txt)
            self.htree.column(c, width=w, anchor="e" if c in ("id", "grand") else "w")
        self.htree.pack(fill="both", expand=True, padx=10, pady=4)
        self.htree.bind("<Double-1>", self.open_old_bill)
        ttk.Label(t, text="बिल पुन्हा उघडण्यासाठी त्यावर डबल क्लिक करा.").pack(pady=4)

    def open_old_bill(self, _=None):
        sel = self.htree.selection()
        if sel:
            webbrowser.open("file://" + build_bill_html(self.htree.item(sel[0])["values"][0]))

    # ---------------- Refresh ----------------
    def refresh_all(self):
        self.refresh_products()
        self.refresh_hist()

    def refresh_products(self):
        with db() as c:
            rows = c.execute("SELECT name,price FROM products ORDER BY name").fetchall()
        self.prices = dict(rows)
        self.cb_name["values"] = [r[0] for r in rows]
        self.ptree.delete(*self.ptree.get_children())
        for n, p in rows:
            self.ptree.insert("", "end", values=(n, f"{p:g}"))

    def refresh_hist(self):
        with db() as c:
            rows = c.execute("SELECT id,date,customer,grand FROM bills ORDER BY id DESC LIMIT 500").fetchall()
            today = datetime.now().strftime("%d-%m-%Y")
            s = c.execute("SELECT COALESCE(SUM(grand),0), COUNT(*) FROM bills WHERE date LIKE ?",
                          (today + "%",)).fetchone()
        self.htree.delete(*self.htree.get_children())
        for r in rows:
            self.htree.insert("", "end", values=(r[0], r[1], r[2] or "-", fmt(r[3])))
        self.lbl_today.config(text=f"आजची विक्री: ₹{fmt(s[0])}   ({s[1]} बिले)")


if __name__ == "__main__":
    init_db()
    App().mainloop()
