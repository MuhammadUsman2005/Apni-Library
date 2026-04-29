import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os

# ─────────────────────────────────────────────
#  Database path – place library.db in the SAME
#  folder as this script, or edit DB_PATH below.
# ─────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library.db")

# ══════════════════════════════════════════════
#  COLOUR / FONT PALETTE
# ══════════════════════════════════════════════
CLR = {
    "bg":           "#F7F8FA",
    "sidebar":      "#1E2A3A",
    "sidebar_hover":"#2E3D52",
    "accent":       "#3A7BD5",
    "accent2":      "#00C9A7",
    "card":         "#FFFFFF",
    "text":         "#1A2130",
    "muted":        "#6B7A99",
    "border":       "#DDE3EE",
    "row_odd":      "#EEF2FA",
    "row_even":     "#FFFFFF",
    "danger":       "#E74C3C",
    "success":      "#27AE60",
}
FF = "Segoe UI" if os.name == "nt" else "Helvetica"
FONTS = {
    "title":    (FF, 20, "bold"),
    "subtitle": (FF, 11),
    "heading":  (FF, 13, "bold"),
    "body":     (FF, 10),
    "small":    (FF,  9),
    "btn":      (FF, 10, "bold"),
    "nav":      (FF, 10, "bold"),
}


# ══════════════════════════════════════════════
#  DATABASE HELPER
# ══════════════════════════════════════════════
class Database:
    def __init__(self, path: str):
        self.path = path

    def _conn(self):
        c = sqlite3.connect(self.path)
        c.execute("PRAGMA foreign_keys = ON")
        return c

    def query(self, sql, params=()):
        try:
            with self._conn() as c:
                return c.execute(sql, params).fetchall()
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", str(e))
            return []

    def execute(self, sql, params=()):
        try:
            with self._conn() as c:
                c.execute(sql, params)
                c.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", str(e))
            return False


# ══════════════════════════════════════════════
#  REUSABLE WIDGETS
# ══════════════════════════════════════════════
class StyledButton(tk.Button):
    def __init__(self, parent, text, command=None, color=None, fg="#FFFFFF", **kw):
        bg = color or CLR["accent"]
        super().__init__(parent, text=text, command=command,
                         font=FONTS["btn"], bg=bg, fg=fg,
                         activebackground=CLR["sidebar_hover"],
                         activeforeground="#FFFFFF",
                         relief="flat", cursor="hand2",
                         padx=14, pady=7, **kw)
        self.bind("<Enter>", lambda e: self.config(bg=_darken(bg)))
        self.bind("<Leave>", lambda e: self.config(bg=bg))


def _darken(hex_color):
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    f = 0.82
    return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"


class SearchBar(tk.Frame):
    """Search entry with placeholder text."""
    PLACEHOLDER = "Search…"

    def __init__(self, parent, placeholder="Search…", on_change=None, **kw):
        super().__init__(parent, bg=CLR["card"],
                         highlightbackground=CLR["border"],
                         highlightthickness=1, **kw)
        self.PLACEHOLDER = placeholder
        self._on_change = on_change
        self._var = tk.StringVar()
        self._var.trace_add("write", self._on_write)
        tk.Label(self, text="🔍", bg=CLR["card"],
                 fg=CLR["muted"], font=FONTS["body"]).pack(side="left", padx=(8, 2))
        self._e = tk.Entry(self, textvariable=self._var,
                           font=FONTS["body"], bg=CLR["card"],
                           fg=CLR["muted"], relief="flat", bd=0,
                           insertbackground=CLR["text"], width=32)
        self._e.pack(side="left", ipady=6, padx=(0, 8))
        self._e.insert(0, placeholder)
        self._e.bind("<FocusIn>",  self._clr)
        self._e.bind("<FocusOut>", self._set)
        self._ready = False  # set True by caller once tree is built

    def _on_write(self, *_):
        if self._ready and self._on_change:
            self._on_change(self._var.get())

    def _clr(self, _):
        if self._e.get() == self.PLACEHOLDER:
            self._e.delete(0, "end")
            self._e.config(fg=CLR["text"])

    def _set(self, _):
        if not self._e.get():
            self._e.insert(0, self.PLACEHOLDER)
            self._e.config(fg=CLR["muted"])

    def get(self):
        v = self._var.get()
        return "" if v == self.PLACEHOLDER else v


def make_tree(parent, columns: list):
    """Build a styled Treeview.  columns = list of dicts."""
    style = ttk.Style()
    style.theme_use("default")
    style.configure("Lib.Treeview",
                    background=CLR["row_even"], foreground=CLR["text"],
                    rowheight=28, fieldbackground=CLR["row_even"],
                    borderwidth=0, font=FONTS["body"])
    style.configure("Lib.Treeview.Heading",
                    background=CLR["sidebar"], foreground="#FFFFFF",
                    font=FONTS["nav"], relief="flat")
    style.map("Lib.Treeview",
              background=[("selected", CLR["accent"])],
              foreground=[("selected", "#FFFFFF")])

    ids = [c["id"] for c in columns]
    tv  = ttk.Treeview(parent, columns=ids, show="headings",
                        style="Lib.Treeview", selectmode="browse")
    for c in columns:
        tv.heading(c["id"], text=c["label"], anchor=c.get("anchor", "w"))
        tv.column(c["id"], width=c.get("width", 150), minwidth=50,
                  anchor=c.get("anchor", "w"), stretch=c.get("stretch", True))
    tv.tag_configure("odd",  background=CLR["row_odd"])
    tv.tag_configure("even", background=CLR["row_even"])
    return tv


def make_scrollable_tree(parent, columns: list):
    """Create a Treeview already wrapped in a scrollable frame.
    Returns (outer_frame, treeview). Uses grid internally so it never
    conflicts with the page's pack geometry manager."""
    outer = tk.Frame(parent, bg=CLR["bg"])
    tv = make_tree(outer, columns)
    vsb = ttk.Scrollbar(outer, orient="vertical",   command=tv.yview)
    hsb = ttk.Scrollbar(outer, orient="horizontal", command=tv.xview)
    tv.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tv.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    outer.rowconfigure(0, weight=1)
    outer.columnconfigure(0, weight=1)

    # smooth mousewheel scrolling
    def _on_mousewheel(event):
        if event.num == 4:          # Linux scroll up
            tv.yview_scroll(-1, "units")
        elif event.num == 5:        # Linux scroll down
            tv.yview_scroll(1, "units")
        else:                       # Windows / macOS
            tv.yview_scroll(int(-1 * (event.delta / 120)), "units")

    tv.bind("<MouseWheel>", _on_mousewheel)   # Windows & macOS
    tv.bind("<Button-4>",   _on_mousewheel)   # Linux
    tv.bind("<Button-5>",   _on_mousewheel)   # Linux

    return outer, tv


def load_tree(tv, rows):
    tv.delete(*tv.get_children())
    for i, row in enumerate(rows):
        tv.insert("", "end", values=row, tags=("odd" if i % 2 else "even",))


# ══════════════════════════════════════════════
#  ADD-DATA DIALOGS
# ══════════════════════════════════════════════
class _BaseDialog(tk.Toplevel):
    def __init__(self, parent, db: Database, title: str, on_success=None):
        super().__init__(parent)
        self.db = db
        self.on_success = on_success
        self.title(title)
        self.resizable(False, False)
        self.configure(bg=CLR["bg"])
        self.transient(parent)
        self.grab_set()
        self._vars = {}
        self._build()

    def _field_row(self, parent, row, label, key):
        tk.Label(parent, text=label, font=FONTS["body"],
                 bg=CLR["bg"], fg=CLR["muted"]).grid(
                     row=row, column=0, sticky="w", padx=20, pady=5)
        var = tk.StringVar()
        tk.Entry(parent, textvariable=var, font=FONTS["body"],
                 bg=CLR["card"], fg=CLR["text"],
                 insertbackground=CLR["text"],
                 relief="solid", bd=1, width=30).grid(
                     row=row, column=1, sticky="ew", padx=20, pady=5)
        self._vars[key] = var

    def _save(self): pass  # override


class AddBookDialog(_BaseDialog):
    def __init__(self, parent, db, on_success=None):
        super().__init__(parent, db, "Add New Book", on_success)

    def _build(self):
        tk.Label(self, text="Add New Book", font=FONTS["heading"],
                 bg=CLR["bg"], fg=CLR["text"]).grid(
                     row=0, column=0, columnspan=2,
                     padx=20, pady=(20, 10), sticky="w")
        for i, (lbl, key) in enumerate(
            [("Title *", "title"), ("Genre", "genre"),
             ("Publisher", "publisher"), ("Year", "year")], 1):
            self._field_row(self, i, lbl, key)
        bf = tk.Frame(self, bg=CLR["bg"])
        bf.grid(row=5, column=0, columnspan=2, pady=(10, 20), padx=20)
        StyledButton(bf, "Save", command=self._save,
                     color=CLR["accent"]).pack(side="left", padx=4)
        StyledButton(bf, "Cancel", command=self.destroy,
                     color=CLR["muted"]).pack(side="left", padx=4)

    def _save(self):
        t = self._vars["title"].get().strip()
        if not t:
            messagebox.showwarning("Validation", "Title is required.", parent=self)
            return
        yr = self._vars["year"].get().strip()
        try:
            yr = int(yr) if yr else None
        except ValueError:
            messagebox.showwarning("Validation", "Year must be a number.", parent=self)
            return
        if self.db.execute(
            "INSERT INTO Books(title,genre,publisher,year) VALUES(?,?,?,?)",
            (t, self._vars["genre"].get().strip() or None,
             self._vars["publisher"].get().strip() or None, yr)):
            messagebox.showinfo("Success", f'Book "{t}" added.', parent=self)
            if self.on_success:
                self.on_success()
            self.destroy()


class AddMemberDialog(_BaseDialog):
    def __init__(self, parent, db, on_success=None):
        super().__init__(parent, db, "Add New Member", on_success)

    def _build(self):
        tk.Label(self, text="Add New Member", font=FONTS["heading"],
                 bg=CLR["bg"], fg=CLR["text"]).grid(
                     row=0, column=0, columnspan=2,
                     padx=20, pady=(20, 10), sticky="w")
        for i, (lbl, key) in enumerate(
            [("Name *", "name"), ("Email", "email"),
             ("Phone", "phone"), ("Address", "address")], 1):
            self._field_row(self, i, lbl, key)
        bf = tk.Frame(self, bg=CLR["bg"])
        bf.grid(row=5, column=0, columnspan=2, pady=(10, 20), padx=20)
        StyledButton(bf, "Save", command=self._save,
                     color=CLR["accent2"], fg=CLR["text"]).pack(side="left", padx=4)
        StyledButton(bf, "Cancel", command=self.destroy,
                     color=CLR["muted"]).pack(side="left", padx=4)

    def _save(self):
        n = self._vars["name"].get().strip()
        if not n:
            messagebox.showwarning("Validation", "Name is required.", parent=self)
            return
        if self.db.execute(
            "INSERT INTO Members(name,email,phone,address) VALUES(?,?,?,?)",
            (n, self._vars["email"].get().strip() or None,
             self._vars["phone"].get().strip() or None,
             self._vars["address"].get().strip() or None)):
            messagebox.showinfo("Success", f'Member "{n}" added.', parent=self)
            if self.on_success:
                self.on_success()
            self.destroy()


# ══════════════════════════════════════════════
#  PAGE BASE
# ══════════════════════════════════════════════
class BasePage(tk.Frame):
    def __init__(self, parent, db: Database, **kw):
        super().__init__(parent, bg=CLR["bg"], **kw)
        self.db = db

    def reload(self): pass

    # ── common header helper ──────────────────
    def _header(self, icon_title: str, btn_label=None,
                btn_color=None, btn_fg="#fff", btn_cmd=None):
        f = tk.Frame(self, bg=CLR["bg"])
        f.pack(fill="x", padx=26, pady=(22, 6))
        tk.Label(f, text=icon_title, font=FONTS["title"],
                 bg=CLR["bg"], fg=CLR["text"]).pack(side="left")
        if btn_label:
            StyledButton(f, btn_label, command=btn_cmd,
                         color=btn_color or CLR["accent"],
                         fg=btn_fg).pack(side="right")
        return f

    def _status_bar(self):
        lbl = tk.Label(self, text="", font=FONTS["small"],
                       bg=CLR["bg"], fg=CLR["muted"])
        lbl.pack(anchor="w", padx=26, pady=(0, 6))
        return lbl


# ══════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════
class DashboardPage(BasePage):
    def __init__(self, parent, db, navigate, **kw):
        super().__init__(parent, db, **kw)
        self.navigate = navigate
        self._build()

    def _build(self):
        # ── header ──
        hdr = tk.Frame(self, bg=CLR["bg"])
        hdr.pack(fill="x", padx=36, pady=(36, 4))
        tk.Label(hdr, text="📚  Library Management System",
                 font=FONTS["title"], bg=CLR["bg"], fg=CLR["text"]).pack(side="left")
        # no subtitle line

        # ── stat cards row 1 ──
        sf = tk.Frame(self, bg=CLR["bg"])
        sf.pack(fill="x", padx=36, pady=(18, 6))
        stats_row1 = [
            ("📖", "Books",        "SELECT COUNT(*) FROM Books",        CLR["accent"]),
            ("👤", "Members",      "SELECT COUNT(*) FROM Members",      CLR["accent2"]),
            ("📋", "Transactions", "SELECT COUNT(*) FROM Transactions", "#F39C12"),
            ("🗂️", "Copies",       "SELECT COUNT(*) FROM Copies",       "#9B59B6"),
        ]
        for i, (ico, lbl, sql, clr) in enumerate(stats_row1):
            val  = self.db.query(sql)
            n    = val[0][0] if val else "–"
            card = tk.Frame(sf, bg=clr, padx=22, pady=14)
            card.grid(row=0, column=i, padx=8, sticky="ew")
            sf.columnconfigure(i, weight=1)
            tk.Label(card, text=ico,    font=(FF, 20), bg=clr, fg="#fff").pack(anchor="w")
            tk.Label(card, text=str(n), font=(FF, 24, "bold"), bg=clr, fg="#fff").pack(anchor="w")
            tk.Label(card, text=lbl,    font=FONTS["body"], bg=clr, fg="#fff").pack(anchor="w")

        # ── stat cards row 2 ──
        sf2 = tk.Frame(self, bg=CLR["bg"])
        sf2.pack(fill="x", padx=36, pady=(0, 6))
        stats_row2 = [
            ("📅", "Reservations", "SELECT COUNT(*) FROM Reservations", "#E67E22"),
            ("💰", "Fines",        "SELECT COUNT(*) FROM Fines",        "#C0392B"),
            ("💰", "Unpaid Fines", "SELECT COUNT(*) FROM Fines WHERE status='Unpaid'", "#922B21"),
            ("✅", "Paid Fines",   "SELECT COUNT(*) FROM Fines WHERE status='Paid'",   CLR["success"]),
        ]
        for i, (ico, lbl, sql, clr) in enumerate(stats_row2):
            val  = self.db.query(sql)
            n    = val[0][0] if val else "–"
            card = tk.Frame(sf2, bg=clr, padx=22, pady=14)
            card.grid(row=0, column=i, padx=8, sticky="ew")
            sf2.columnconfigure(i, weight=1)
            tk.Label(card, text=ico,    font=(FF, 20), bg=clr, fg="#fff").pack(anchor="w")
            tk.Label(card, text=str(n), font=(FF, 24, "bold"), bg=clr, fg="#fff").pack(anchor="w")
            tk.Label(card, text=lbl,    font=FONTS["body"], bg=clr, fg="#fff").pack(anchor="w")

        # ── separator ──
        tk.Frame(self, bg=CLR["border"], height=1).pack(
            fill="x", padx=36, pady=(4, 14))

        # ── nav buttons ──
        tk.Label(self, text="Quick Navigation", font=FONTS["heading"],
                 bg=CLR["bg"], fg=CLR["text"]).pack(anchor="w", padx=36, pady=(0, 10))
        nf = tk.Frame(self, bg=CLR["bg"])
        nf.pack(fill="x", padx=36)
        navs = [
            ("📖  Books",        "books",        CLR["accent"]),
            ("👤  Members",      "members",      CLR["accent2"]),
            ("📋  Transactions", "transactions", "#F39C12"),
            ("🗂️  Copies",       "copies",       "#9B59B6"),
            ("📅  Reservations", "reservations", "#E67E22"),
            ("💰  Fines",        "fines",        "#C0392B"),
        ]
        for i, (lbl, page, clr) in enumerate(navs):
            b = tk.Button(nf, text=lbl, font=(FF, 11, "bold"),
                          bg=clr, fg="#fff", relief="flat",
                          cursor="hand2", padx=14, pady=14,
                          command=lambda p=page: self.navigate(p))
            b.grid(row=i // 3, column=i % 3, padx=6, pady=4, sticky="ew")
        for col in range(3):
            nf.columnconfigure(col, weight=1)

        # ── add data ──
        tk.Label(self, text="Add Data", font=FONTS["heading"],
                 bg=CLR["bg"], fg=CLR["text"]).pack(anchor="w", padx=36, pady=(26, 10))
        af = tk.Frame(self, bg=CLR["bg"])
        af.pack(anchor="w", padx=36)
        StyledButton(af, "＋  Add Book",
                     command=lambda: AddBookDialog(self, self.db),
                     color=CLR["accent"]).pack(side="left", padx=(0, 10))
        StyledButton(af, "＋  Add Member",
                     command=lambda: AddMemberDialog(self, self.db),
                     color=CLR["accent2"], fg=CLR["text"]).pack(side="left")


# ══════════════════════════════════════════════
#  BOOKS PAGE
# ══════════════════════════════════════════════
class BooksPage(BasePage):
    def __init__(self, parent, db, **kw):
        super().__init__(parent, db, **kw)
        self._all = []
        self._build()

    def _build(self):
        self._header("📖  Books",
                     btn_label="＋  Add Book",
                     btn_cmd=lambda: AddBookDialog(self, self.db,
                                                   on_success=self.reload))
        # search
        sf = tk.Frame(self, bg=CLR["bg"])
        sf.pack(fill="x", padx=26, pady=(0, 8))
        self._search = SearchBar(sf, "Search by title…",
                                 on_change=self._filter)
        self._search.pack(side="left")

        cols = [
            {"id": "title",     "label": "Title",     "width": 280},
            {"id": "genre",     "label": "Genre",     "width": 110},
            {"id": "publisher", "label": "Publisher", "width": 140},
            {"id": "year",      "label": "Year",      "width": 70,
             "anchor": "center", "stretch": False},
        ]
        outer, self._tv = make_scrollable_tree(self, cols)
        outer.pack(fill="both", expand=True, padx=26, pady=(0, 6))
        self._sb = self._status_bar()
        self._search._ready = True  # treeview is now ready

    def reload(self):
        self._all = self.db.query(
            "SELECT title,genre,publisher,year FROM Books ORDER BY title")
        self._filter(self._search.get())
        self._sb.config(text=f"{len(self._all)} books in database")

    def _filter(self, text):
        q = text.strip().lower()
        rows = [r for r in self._all if q in r[0].lower()] if q else self._all
        load_tree(self._tv, rows)
        self._sb.config(text=f"Showing {len(rows)} of {len(self._all)} books")


# ══════════════════════════════════════════════
#  MEMBERS PAGE
# ══════════════════════════════════════════════
class MembersPage(BasePage):
    def __init__(self, parent, db, **kw):
        super().__init__(parent, db, **kw)
        self._build()

    def _build(self):
        self._header("👤  Members",
                     btn_label="＋  Add Member",
                     btn_color=CLR["accent2"], btn_fg=CLR["text"],
                     btn_cmd=lambda: AddMemberDialog(self, self.db,
                                                     on_success=self.reload))
        cols = [
            {"id": "name",  "label": "Name",  "width": 200},
            {"id": "email", "label": "Email", "width": 250},
            {"id": "phone", "label": "Phone", "width": 140},
        ]
        outer, self._tv = make_scrollable_tree(self, cols)
        outer.pack(fill="both", expand=True, padx=26, pady=(8, 6))
        self._sb = self._status_bar()

    def reload(self):
        rows = self.db.query(
            "SELECT name,email,phone FROM Members ORDER BY name")
        load_tree(self._tv, rows)
        self._sb.config(text=f"{len(rows)} members")


# ══════════════════════════════════════════════
#  TRANSACTIONS PAGE
# ══════════════════════════════════════════════
class TransactionsPage(BasePage):
    def __init__(self, parent, db, **kw):
        super().__init__(parent, db, **kw)
        self._build()

    def _build(self):
        self._header("📋  Transactions",
                     btn_label="↻  Refresh",
                     btn_color=CLR["muted"],
                     btn_cmd=self.reload)
        cols = [
            {"id": "member",  "label": "Member Name", "width": 190},
            {"id": "book",    "label": "Book Title",  "width": 260},
            {"id": "issue",   "label": "Issue Date",  "width": 120,
             "anchor": "center"},
            {"id": "return_", "label": "Return Date", "width": 120,
             "anchor": "center"},
        ]
        outer, self._tv = make_scrollable_tree(self, cols)
        outer.pack(fill="both", expand=True, padx=26, pady=(8, 6))
        self._sb = self._status_bar()

    def reload(self):
        rows = self.db.query("""
            SELECT m.name, b.title, t.issue_date, t.return_date
            FROM   Transactions t
            JOIN   Members m ON t.member_id = m.member_id
            JOIN   Copies  c ON t.copy_id   = c.copy_id
            JOIN   Books   b ON c.book_id   = b.book_id
            ORDER  BY t.issue_date DESC
        """)
        load_tree(self._tv, rows)
        self._sb.config(text=f"{len(rows)} transactions")


# ══════════════════════════════════════════════
#  COPIES PAGE
# ══════════════════════════════════════════════
class CopiesPage(BasePage):
    def __init__(self, parent, db, **kw):
        super().__init__(parent, db, **kw)
        self._all = []
        self._build()

    def _build(self):
        self._header("🗂️  Copies")

        # filter radios
        ff = tk.Frame(self, bg=CLR["bg"])
        ff.pack(fill="x", padx=26, pady=(0, 8))
        self._fv = tk.StringVar(value="All")
        for lbl in ("All", "Available", "Issued"):
            tk.Radiobutton(ff, text=lbl, variable=self._fv,
                           value=lbl, command=self._apply,
                           bg=CLR["bg"], fg=CLR["text"],
                           selectcolor=CLR["card"],
                           font=FONTS["body"], cursor="hand2").pack(
                               side="left", padx=8)

        cols = [
            {"id": "title",   "label": "Book Title", "width": 280},
            {"id": "copy_id", "label": "Copy #",     "width": 70,
             "anchor": "center", "stretch": False},
            {"id": "status",  "label": "Status",     "width": 110,
             "anchor": "center"},
        ]
        outer, self._tv = make_scrollable_tree(self, cols)
        self._tv.tag_configure("available", foreground=CLR["success"])
        self._tv.tag_configure("issued",    foreground=CLR["danger"])
        outer.pack(fill="both", expand=True, padx=26, pady=(0, 6))
        self._sb = self._status_bar()

    def reload(self):
        self._all = self.db.query("""
            SELECT b.title, c.copy_id, c.status
            FROM   Copies c
            JOIN   Books  b ON c.book_id = b.book_id
            ORDER  BY b.title, c.copy_id
        """)
        self._apply()

    def _apply(self):
        f    = self._fv.get()
        rows = [r for r in self._all if f == "All" or r[2] == f]
        self._tv.delete(*self._tv.get_children())
        for i, row in enumerate(rows):
            row_tag    = "odd" if i % 2 else "even"
            status_tag = "available" if row[2] == "Available" else "issued"
            self._tv.insert("", "end", values=row,
                            tags=(row_tag, status_tag))
        self._sb.config(
            text=f"Showing {len(rows)} of {len(self._all)} copies")


# ══════════════════════════════════════════════
#  RESERVATIONS PAGE
# ══════════════════════════════════════════════
class ReservationsPage(BasePage):
    def __init__(self, parent, db, **kw):
        super().__init__(parent, db, **kw)
        self._build()

    def _build(self):
        self._header("📅  Reservations",
                     btn_label="↻  Refresh",
                     btn_color=CLR["muted"],
                     btn_cmd=self.reload)
        cols = [
            {"id": "member",  "label": "Member Name",       "width": 200},
            {"id": "book",    "label": "Book Title",         "width": 280},
            {"id": "date",    "label": "Reservation Date",   "width": 140,
             "anchor": "center"},
        ]
        outer, self._tv = make_scrollable_tree(self, cols)
        outer.pack(fill="both", expand=True, padx=26, pady=(8, 6))
        self._sb = self._status_bar()

    def reload(self):
        rows = self.db.query("""
            SELECT m.name, b.title, r.reservation_date
            FROM   Reservations r
            JOIN   Members m ON r.member_id = m.member_id
            JOIN   Books   b ON r.book_id   = b.book_id
            ORDER  BY r.reservation_date DESC
        """)
        load_tree(self._tv, rows)
        self._sb.config(text=f"{len(rows)} reservations")


# ══════════════════════════════════════════════
#  FINES PAGE
# ══════════════════════════════════════════════
class FinesPage(BasePage):
    def __init__(self, parent, db, **kw):
        super().__init__(parent, db, **kw)
        self._all = []
        self._build()

    def _build(self):
        self._header("💰  Fines")

        # filter radios
        ff = tk.Frame(self, bg=CLR["bg"])
        ff.pack(fill="x", padx=26, pady=(0, 8))
        self._fv = tk.StringVar(value="All")
        for lbl in ("All", "Paid", "Unpaid"):
            tk.Radiobutton(ff, text=lbl, variable=self._fv,
                           value=lbl, command=self._apply,
                           bg=CLR["bg"], fg=CLR["text"],
                           selectcolor=CLR["card"],
                           font=FONTS["body"], cursor="hand2").pack(
                               side="left", padx=8)

        cols = [
            {"id": "member", "label": "Member Name", "width": 200},
            {"id": "book",   "label": "Book Title",  "width": 240},
            {"id": "amount", "label": "Amount (Rs)", "width": 110,
             "anchor": "center"},
            {"id": "status", "label": "Status",      "width": 100,
             "anchor": "center"},
        ]
        outer, self._tv = make_scrollable_tree(self, cols)
        self._tv.tag_configure("paid",   foreground=CLR["success"])
        self._tv.tag_configure("unpaid", foreground=CLR["danger"])
        outer.pack(fill="both", expand=True, padx=26, pady=(0, 6))
        self._sb = self._status_bar()

    def reload(self):
        self._all = self.db.query("""
            SELECT m.name, b.title, f.amount, f.status
            FROM   Fines f
            JOIN   Transactions t ON f.transaction_id = t.transaction_id
            JOIN   Members m      ON t.member_id      = m.member_id
            JOIN   Copies  c      ON t.copy_id        = c.copy_id
            JOIN   Books   b      ON c.book_id        = b.book_id
            ORDER  BY f.status, m.name
        """)
        self._apply()

    def _apply(self):
        f    = self._fv.get()
        rows = [r for r in self._all if f == "All" or r[3] == f]
        self._tv.delete(*self._tv.get_children())
        for i, row in enumerate(rows):
            row_tag    = "odd" if i % 2 else "even"
            status_tag = "paid" if row[3] == "Paid" else "unpaid"
            self._tv.insert("", "end", values=row,
                            tags=(row_tag, status_tag))
        self._sb.config(
            text=f"Showing {len(rows)} of {len(self._all)} fines")


class LibraryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Library Management System")
        self.geometry("1120x700")
        self.minsize(900, 580)
        self.configure(bg=CLR["bg"])

        self.db = Database(DB_PATH)
        self._pages: dict[str, BasePage] = {}
        self._nav_btns: dict[str, tk.Button] = {}
        self._current = None

        self._build_layout()
        self._show("dashboard")

    # ── build sidebar + content ──────────────
    def _build_layout(self):
        # ── sidebar ──
        sb = tk.Frame(self, bg=CLR["sidebar"], width=210)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        tk.Label(sb, text="📚", font=(FF, 26),
                 bg=CLR["sidebar"], fg="#FFFFFF").pack(pady=(26, 2))
        tk.Label(sb, text="Welcome to\nApni Library",
                 font=(FF, 11, "bold"),
                 bg=CLR["sidebar"], fg="#FFFFFF",
                 justify="center").pack()
        tk.Frame(sb, bg="#FFFFFF", height=1).pack(
            fill="x", padx=18, pady=14)

        nav_items = [
            ("dashboard",    "🏠  Dashboard"),
            ("books",        "📖  Books"),
            ("members",      "👤  Members"),
            ("transactions", "📋  Transactions"),
            ("copies",       "🗂️  Copies"),
            ("reservations", "📅  Reservations"),
            ("fines",        "💰  Fines"),
        ]
        for key, label in nav_items:
            btn = tk.Button(sb, text=label, font=FONTS["nav"],
                            bg=CLR["sidebar"], fg="#CBD5E1",
                            activebackground=CLR["sidebar_hover"],
                            activeforeground="#FFFFFF",
                            relief="flat", cursor="hand2",
                            anchor="w", padx=22, pady=10,
                            command=lambda k=key: self._show(k))
            btn.pack(fill="x")
            self._nav_btns[key] = btn

        tk.Frame(sb, bg=CLR["sidebar"]).pack(fill="both", expand=True)
        tk.Label(sb, text="v1.0  •  SQLite",
                 font=FONTS["small"],
                 bg=CLR["sidebar"], fg="#4A5568").pack(pady=14)

        # ── content ──
        self._content = tk.Frame(self, bg=CLR["bg"])
        self._content.pack(side="left", fill="both", expand=True)

        # instantiate all pages
        self._pages["dashboard"]    = DashboardPage(
            self._content, self.db, navigate=self._show)
        self._pages["books"]        = BooksPage(self._content, self.db)
        self._pages["members"]      = MembersPage(self._content, self.db)
        self._pages["transactions"] = TransactionsPage(self._content, self.db)
        self._pages["copies"]       = CopiesPage(self._content, self.db)
        self._pages["reservations"] = ReservationsPage(self._content, self.db)
        self._pages["fines"]        = FinesPage(self._content, self.db)

    def _show(self, name: str):
        if self._current:
            self._pages[self._current].pack_forget()
            self._nav_btns[self._current].config(
                bg=CLR["sidebar"], fg="#CBD5E1")

        page = self._pages[name]
        page.pack(fill="both", expand=True)
        page.reload()
        self._nav_btns[name].config(
            bg=CLR["sidebar_hover"], fg="#FFFFFF")
        self._current = name


# ══════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════
if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Database Not Found",
            f"library.db not found at:\n{DB_PATH}\n\n"
            "Place library.db in the same folder as library_app.py and try again."
        )
        root.destroy()
    else:
        app = LibraryApp()
        app.mainloop()