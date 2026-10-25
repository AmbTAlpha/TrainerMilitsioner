import csv
import json
import re
import time
import os
import ctypes
import uuid
from collections import deque
import unicodedata
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
try:
    import customtkinter as ctk
    from PIL import Image, ImageDraw
except ImportError:
    import tkinter as _tk
    from tkinter import messagebox as _mb
    _root = _tk.Tk()
    _root.withdraw()
    _mb.showerror("Militsioner Trainer", "Modules Python manquants (customtkinter, pillow).\n\nDouble-clique sur install_requirements.bat, puis appuie de nouveau sur la touche du trainer en jeu.")
    raise SystemExit
import sys
import socket

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
BG, PANEL, EDGE, TEXT, MUTED, ACCENT = "#0A0E14", "#121923", "#243246", "#EEF3FB", "#8FA1BA", "#2EC4B6"
CARD, GOOD, WARN, BAD = "#1A2433", "#3FBF7F", "#E6A23C", "#D9534F"
import math
import tempfile


def draw_logo(size=256):
    big = 512
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((16, 16, big - 16, big - 16), radius=108, fill="#0F1722", outline=ACCENT, width=24)
    star = []
    for k in range(10):
        radius = 64 if k % 2 == 0 else 27
        angle = math.radians(-90 + k * 36)
        star.append((256 + radius * math.cos(angle), 146 + radius * math.sin(angle)))
    d.polygon(star, fill=ACCENT)
    d.polygon([(118, 412), (118, 216), (172, 216), (256, 332), (340, 216), (394, 216), (394, 412), (342, 412), (342, 298), (274, 390), (238, 390), (170, 298), (170, 412)], fill=TEXT)
    return img.resize((size, size), Image.LANCZOS)


def save_logo_ico(path):
    draw_logo(256).save(path, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if "--make-icon" in sys.argv:
    save_logo_ico(sys.argv[sys.argv.index("--make-icon") + 1])
    raise SystemExit

if os.name == "nt":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Militsioner.Trainer.Menu")
    except (AttributeError, OSError):
        pass

HOME = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
CONFIG = HOME / "trainer_preferences.json"
APP_TITLE = "Militsioner Trainer"

def detect_scripts():
    for candidate in (HOME / "scripts", HOME):
        if (candidate / "items_catalog.tsv").is_file() or (candidate / "main.lua").is_file():
            return candidate
    return HOME / "scripts"

DEFAULT = str(detect_scripts())

# Une seule fenetre de menu : si elle existe deja, on la ramene devant.
_instance_lock = socket.socket()
try:
    _instance_lock.bind(("127.0.0.1", 47931))
except OSError:
    if os.name == "nt":
        try:
            user32_ = ctypes.WinDLL("user32")
            hwnd_ = user32_.FindWindowW(None, APP_TITLE)
            if hwnd_:
                user32_.ShowWindow(hwnd_, 9)
                user32_.SetForegroundWindow(hwnd_)
        except OSError:
            pass
    sys.exit(0)

try:
    prefs = json.loads(CONFIG.read_text(encoding="utf-8"))
except (OSError, ValueError):
    prefs = {}
favorites = set(prefs.get("favorites", []))
root = ctk.CTk()
root.title(APP_TITLE)
root.geometry("1220x820")

def apply_icon():
    ico_path = Path(tempfile.gettempdir()) / "militsioner_trainer.ico"
    try:
        save_logo_ico(ico_path)
        root.iconbitmap(str(ico_path))
        return
    except (OSError, tk.TclError):
        pass
    try:
        from PIL import ImageTk
        root._logo_photo = ImageTk.PhotoImage(draw_logo(64))
        root.iconphoto(True, root._logo_photo)
    except (ImportError, tk.TclError):
        pass

apply_icon()
root.after(300, apply_icon)
root.minsize(1050, 690)
root.configure(fg_color=BG)
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(1, weight=1)
saved_scripts = prefs.get("scripts")
scripts_var = ctk.StringVar(value=saved_scripts if (saved_scripts and prefs.get("scripts_manual") and Path(saved_scripts).is_dir()) else DEFAULT)
status_var = ctk.StringVar(value="Charge ta partie avant d’envoyer une commande.")
category_var = ctk.StringVar(value="Toutes les catégories")
search_var = ctk.StringVar(value="")
experimental_var = ctk.BooleanVar(value=False)
favorite_filter = ctk.BooleanVar(value=False)
flight_var = ctk.BooleanVar(value=False)
quantity_var = ctk.StringVar(value="1")
hotkey_var = ctk.StringVar(value=prefs.get("spawn_key", "F6"))
hotkey_enabled = ctk.BooleanVar(value=bool(prefs.get("spawn_enabled", True)))
topmost_var = ctk.BooleanVar(value=bool(prefs.get("topmost", True)))
toggle_key_var = ctk.StringVar(value="F7")
SHORTCUT_CHOICES = ["Aucun"] + ["F%d" % n for n in range(1, 13)] + ["Maj+F%d" % n for n in range(1, 13)]
DEFAULT_SHORTCUTS = {"god": "Maj+F1", "giant_safe": "Maj+F2", "npc_invisible": "Maj+F3", "stealth_test": "Maj+F4", "noclip": "Maj+F5", "speed": "Maj+F8"}
saved_shortcuts = prefs.get("shortcuts") if isinstance(prefs.get("shortcuts"), dict) else {}
shortcut_vars = {}
for _key, _default in DEFAULT_SHORTCUTS.items():
    _value = saved_shortcuts.get(_key, _default)
    shortcut_vars[_key] = ctk.StringVar(value=_value if _value in SHORTCUT_CHOICES else _default)
spawn_history = deque(maxlen=100)
last_selected_spawn = None
last_recreate_id = None
last_snapshot_request = None
last_state_mtime = None
hotkey_down = False
items, visible, selected, log_offset, log_path = {}, [], None, 0, None
states = {key: False for key in ("god", "noclip", "giant_safe", "npc_invisible", "stealth_test")}
flight_sent = {"up": False, "down": False}
last_spawn_time = 0.0

def save_prefs():
    try:
        CONFIG.write_text(json.dumps({"scripts": scripts_var.get(), "scripts_manual": bool(prefs.get("scripts_manual")), "favorites": sorted(favorites), "spawn_key": hotkey_var.get(), "spawn_enabled": bool(hotkey_enabled.get()), "topmost": bool(topmost_var.get()), "shortcuts": {k: v.get() for k, v in shortcut_vars.items()}}, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as error:
        status_var.set("Préférences non enregistrées : " + str(error))

def scripts_dir():
    return Path(scripts_var.get().strip())

def send(command):
    try:
        folder = scripts_dir()
        if not folder.is_dir():
            raise OSError("Dossier scripts introuvable : vérifie Réglages")
        with (folder / "commands.txt").open("a", encoding="utf-8") as file:
            file.write(command + "\n")
        status_var.set("Commande envoyée : " + command + " — résultat à vérifier dans le journal.")
        return True
    except OSError as error:
        status_var.set("Échec d’envoi : " + str(error))
        return False

def normalized(text):
    return " ".join("".join(c for c in unicodedata.normalize("NFD", text.casefold()) if not unicodedata.combining(c)).replace("_", " ").split())

header = ctk.CTkFrame(root, fg_color=PANEL, corner_radius=0, height=66)
header.grid(row=0, column=0, columnspan=2, sticky="ew")
header.grid_propagate(False)
header_logo = ctk.CTkImage(light_image=draw_logo(128), dark_image=draw_logo(128), size=(38, 38))
ctk.CTkLabel(header, text="", image=header_logo).pack(side="left", padx=(20, 0), pady=14)
ctk.CTkLabel(header, text="MILITSIONER", font=("Segoe UI", 22, "bold"), text_color=TEXT).pack(side="left", padx=(10, 8), pady=16)
ctk.CTkLabel(header, text="TRAINER", font=("Segoe UI", 22, "bold"), text_color=ACCENT).pack(side="left")
status_chip = ctk.CTkLabel(header, text="●  Jeu non détecté", corner_radius=14, fg_color=EDGE, text_color=TEXT, font=("Segoe UI", 12, "bold"), height=30)
status_chip.pack(side="right", padx=24)
chip_hint = ctk.CTkLabel(header, text="", text_color=MUTED, font=("Segoe UI", 12))
chip_hint.pack(side="right", padx=4)
sidebar = ctk.CTkFrame(root, width=185, fg_color=PANEL, corner_radius=0)
sidebar.grid(row=1, column=0, sticky="ns")
sidebar.grid_propagate(False)
workspace = ctk.CTkFrame(root, fg_color=BG, corner_radius=0)
workspace.grid(row=1, column=1, sticky="nsew", padx=20, pady=18)
workspace.grid_columnconfigure(0, weight=1)
workspace.grid_rowconfigure(0, weight=1)
pages = {}
nav_buttons = {}

active_page = "Objets"

def show_page(name):
    global active_page
    active_page = name
    for key, page in pages.items():
        if key == name:
            page.grid(row=0, column=0, sticky="nsew")
        else:
            page.grid_remove()
        nav_buttons[key].configure(fg_color=ACCENT if key == name else "transparent", text_color=BG if key == name else TEXT, image=ICON_ACTIVE[key] if key == name else ICON_NORMAL[key])

from PIL import Image, ImageDraw
import math

def draw_icon(name, color):
    size = 96
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = 8
    if name == "Objets":
        for x, y in ((10, 10), (54, 10), (10, 54), (54, 54)):
            d.rounded_rectangle((x, y, x + 32, y + 32), radius=8, outline=color, width=w)
    elif name == "Personnage":
        d.ellipse((30, 8, 66, 44), outline=color, width=w)
        d.arc((10, 52, 86, 128), 180, 360, fill=color, width=w)
    elif name == "Utilitaires":
        for y, knob in ((24, 34), (48, 66), (72, 42)):
            d.line((10, y, 86, y), fill=color, width=6)
            d.ellipse((knob - 11, y - 11, knob + 11, y + 11), fill=color)
    elif name == "Journal":
        d.rounded_rectangle((18, 8, 78, 88), radius=9, outline=color, width=w)
        for y in (30, 48, 66):
            d.line((32, y, 64, y), fill=color, width=6)
    elif name == "Réglages":
        cx = cy = 48
        d.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), outline=color, width=w)
        d.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill=color)
        for k in range(8):
            a = math.radians(k * 45)
            d.line((cx + 30 * math.cos(a), cy + 30 * math.sin(a), cx + 42 * math.cos(a), cy + 42 * math.sin(a)), fill=color, width=w + 2)
    img = img.resize((66, 66), Image.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(22, 22))

ICON_NORMAL = {n: draw_icon(n, TEXT) for n in ("Objets", "Personnage", "Utilitaires", "Journal", "Réglages")}
ICON_ACTIVE = {n: draw_icon(n, BG) for n in ICON_NORMAL}
for name in ("Objets", "Personnage", "Utilitaires", "Journal", "Réglages"):
    page = ctk.CTkFrame(workspace, fg_color=BG, corner_radius=0)
    pages[name] = page
    button = ctk.CTkButton(sidebar, text="  " + name, image=ICON_NORMAL[name], compound="left", height=46, anchor="w", corner_radius=10, fg_color="transparent", hover_color=EDGE, text_color=TEXT, font=("Segoe UI", 14, "bold"), command=lambda n=name: show_page(n))
    button.pack(fill="x", padx=12, pady=(16 if name == "Objets" else 4, 4))
    nav_buttons[name] = button
ctk.CTkLabel(sidebar, text="Militsioner Demo\nSolo • hors ligne", text_color=MUTED, justify="left").pack(side="bottom", padx=16, pady=20)
footer = ctk.CTkFrame(root, fg_color=PANEL, corner_radius=0)
footer.grid(row=2, column=0, columnspan=2, sticky="ew")
ctk.CTkLabel(footer, textvariable=status_var, anchor="w", wraplength=1000, text_color=TEXT).pack(fill="x", padx=20, pady=10)

page = pages["Objets"]
page.grid_columnconfigure(0, weight=1)
page.grid_columnconfigure(1, weight=0, minsize=275)
page.grid_rowconfigure(3, weight=1)
ctk.CTkLabel(page, text="Catalogue d’objets", font=("Segoe UI", 25, "bold"), anchor="w").grid(row=0, column=0, sticky="w", columnspan=2, pady=(0, 12))
filters = ctk.CTkFrame(page, fg_color=PANEL)
filters.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
filters.grid_columnconfigure(0, weight=1)
ctk.CTkEntry(filters, textvariable=search_var, placeholder_text="Rechercher un objet…", height=42, fg_color=CARD, border_color=EDGE).grid(row=0, column=0, sticky="ew", padx=12, pady=12)
category_select = ctk.CTkOptionMenu(filters, variable=category_var, values=["Toutes les catégories"], width=190, height=42, fg_color=EDGE, button_color=ACCENT, button_hover_color="#26A79B", command=lambda _: refresh())
category_select.grid(row=0, column=1, padx=(0, 12), pady=12)
ctk.CTkCheckBox(filters, text="Favoris seulement", variable=favorite_filter, command=lambda: refresh()).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))
count_label = ctk.CTkLabel(page, text="", text_color=MUTED, anchor="w")
count_label.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
list_frame = ctk.CTkScrollableFrame(page, fg_color=BG, corner_radius=12, scrollbar_button_color=EDGE, scrollbar_button_hover_color=ACCENT)
list_frame.grid(row=3, column=0, rowspan=4, sticky="nsew", padx=(0, 14))
list_frame.grid_columnconfigure(0, weight=1)
list_frame.grid_columnconfigure(1, weight=1)
card_widgets = {}
card_pool = []
PAGE_SIZE = 16
page_index = 0
refresh_job = None
CATEGORY_COLORS = {"Consommables":"#D79B59", "Clés et outils":"#6A9EE9", "Vêtements":"#AC8ED3", "Valeurs":"#CBB15D", "Jardinage":"#74BFA3", "Multimédia":"#D38BAF", "Spéciaux":"#D39A6A", "Divers":"#8FA2B9"}
STATUS_LABELS = {"experimental":"Créé • visibilité à vérifier", "spawn_confirme":"Création confirmée", "signale_fonctionnel":"Fonctionnel signalé", "decouvert":"Trouvé dans le jeu • à tester"}

def draw_cards():
    global page_index
    pages_total = max(1, (len(visible) + PAGE_SIZE - 1) // PAGE_SIZE)
    page_index = min(max(page_index, 0), pages_total - 1)
    shown = visible[page_index * PAGE_SIZE:(page_index + 1) * PAGE_SIZE]
    card_widgets.clear()
    while len(card_pool) < min(PAGE_SIZE, len(shown)):
        slot = {"id": None}
        card = ctk.CTkFrame(list_frame, fg_color=PANEL, corner_radius=14, border_width=2, border_color=PANEL)
        card.grid_columnconfigure(0, weight=1)
        category = ctk.CTkLabel(card, text="", font=("Segoe UI", 10, "bold"), anchor="w")
        category.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 2))
        button = ctk.CTkButton(card, text="", font=("Segoe UI", 13, "bold"), fg_color="transparent", hover_color=EDGE, anchor="w", height=50, corner_radius=8, command=lambda s=slot: choose(s["id"]))
        button.grid(row=1, column=0, sticky="ew", padx=8, pady=2)
        badge = ctk.CTkLabel(card, text="", font=("Segoe UI", 10), anchor="w")
        badge.grid(row=2, column=0, sticky="ew", padx=14, pady=(2, 12))
        card.bind("<Button-1>", lambda e,s=slot: choose(s["id"]))
        slot.update(card=card, category=category, button=button, badge=badge)
        card_pool.append(slot)
    for index, slot in enumerate(card_pool):
        if index >= len(shown):
            slot["id"] = None
            slot["card"].grid_remove()
            continue
        ident = shown[index]
        row = items[ident]
        slot["id"] = ident
        slot["category"].configure(text=row["category"].upper(), text_color=CATEGORY_COLORS.get(row["category"], MUTED))
        slot["button"].configure(text=("★ " if ident in favorites else "") + row["label"])
        slot["badge"].configure(text=STATUS_LABELS.get(row["status"], "À tester"), text_color="#E6B879" if row["status"] == "experimental" else MUTED)
        slot["card"].configure(border_color=ACCENT if ident == selected else PANEL)
        slot["card"].grid(row=index//2, column=index%2, sticky="nsew", padx=5, pady=6)
        card_widgets[ident] = slot["card"]
    empty_label.grid_remove() if shown else empty_label.grid(row=0, column=0, columnspan=2, sticky="ew")
    page_label.configure(text=f"Page {page_index + 1} / {pages_total}")
    prev_button.configure(state="normal" if page_index > 0 else "disabled")
    next_button.configure(state="normal" if page_index < pages_total - 1 else "disabled")

detail = ctk.CTkFrame(page, fg_color=PANEL)
detail.grid(row=3, column=1, rowspan=4, sticky="nsew")
detail.grid_columnconfigure(0, weight=1)
ctk.CTkLabel(detail, text="OBJET SÉLECTIONNÉ", text_color=ACCENT, font=("Segoe UI", 10, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 4))
selected_label = ctk.CTkLabel(detail, text="Sélectionne un objet", font=("Segoe UI", 22, "bold"), anchor="w", justify="left", wraplength=230)
selected_label.grid(row=1, column=0, sticky="ew", padx=18, pady=(4, 4))
internal_label = ctk.CTkLabel(detail, text="", text_color=MUTED, anchor="w", wraplength=230)
internal_label.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 6))

def choose(ident=None):
    global selected, last_selected_spawn
    if ident is not None:
        selected = ident if ident in visible else None
    for item_id, card in card_widgets.items():
        card.configure(border_color=ACCENT if item_id == selected else PANEL)
    if selected and selected in items:
        row = items[selected]
        last_selected_spawn = selected
        selected_label.configure(text=row["label"])
        internal_label.configure(text=row["category"] + "\n\n" + row["id"] + ("\n\nChat : l’acteur est créé, mais son rendu reste à diagnostiquer." if row["status"] == "experimental" else "\n\nUn objet par clic, devant le personnage."))
        favorite_button.configure(text="★ Retirer des favoris" if selected in favorites else "☆ Ajouter aux favoris")
        spawn_button.configure(state="normal")
        reveal_button.configure(state="normal" if selected == "BPA_Cat_C" else "disabled")
    else:
        selected_label.configure(text="Aucun objet sélectionné")
        internal_label.configure(text="")
        spawn_button.configure(state="disabled")
        reveal_button.configure(state="disabled")

def request_spawn(ident):
    global last_spawn_time, last_recreate_id
    if ident not in items:
        status_var.set("Sélectionne un objet avant le spawn.")
        return
    now = time.monotonic()
    if now - last_spawn_time < 1.2:
        status_var.set("Anti-spam : attends 1,2 seconde entre deux lots.")
        return
    count = int(quantity_var.get())
    if send(f"spawn {ident} {count}"):
        last_spawn_time = now
        last_recreate_id = ident

def spawn_selected():
    if selected in visible:
        request_spawn(selected)

def toggle_favorite():
    if selected is None:
        return
    if selected in favorites:
        favorites.remove(selected)
    else:
        favorites.add(selected)
    save_prefs()
    refresh()

spawn_button = ctk.CTkButton(detail, text="SPAWNER DEVANT MOI", height=44, width=215, command=spawn_selected, state="disabled", fg_color=ACCENT)
spawn_button.grid(row=3, column=0, sticky="ew", padx=16, pady=(4, 6))
favorite_button = ctk.CTkButton(detail, text="Ajouter aux favoris", height=30, fg_color=EDGE, command=toggle_favorite)
favorite_button.grid(row=4, column=0, sticky="ew", padx=16, pady=3)
def scan_for_items():
    if send("scan_items"):
        status_var.set("Scan en cours dans le jeu…")
        root.after(2500, load_catalog)
        root.after(5000, load_catalog)

scan_button = ctk.CTkButton(detail, text="Chercher plus d’objets dans le jeu", height=30, fg_color=EDGE, command=scan_for_items)
scan_button.grid(row=5, column=0, sticky="ew", padx=16, pady=3)
reveal_button = ctk.CTkButton(detail, text="Essai visibilité du dernier chat", fg_color=EDGE, hover_color="#3B4A5C", height=36, state="disabled", command=lambda: send("cat_reveal"))
ctk.CTkLabel(detail, text="Quantité par lot", text_color=MUTED).grid(row=7, column=0, sticky="w", padx=18, pady=(4, 2))
ctk.CTkSegmentedButton(detail, values=["1", "2", "3"], variable=quantity_var, selected_color=ACCENT, selected_hover_color="#26A79B", unselected_color=EDGE, unselected_hover_color="#33465E", text_color=TEXT).grid(row=8, column=0, sticky="ew", padx=16, pady=(0, 12))
ctk.CTkLabel(page, text="Molette sur les cartes • noms FR descriptifs • clic pour sélectionner", text_color=MUTED, anchor="w").grid(row=8, column=0, columnspan=2, sticky="ew", pady=(8, 0))

empty_label = ctk.CTkLabel(list_frame, text="Aucun résultat\nEssaie une autre recherche ou catégorie.", text_color=MUTED, height=130)
pager = ctk.CTkFrame(page, fg_color="transparent")
pager.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(10, 0))
pager.grid_columnconfigure(1, weight=1)

def turn_page(delta):
    global page_index, selected
    total = max(1, (len(visible) + PAGE_SIZE - 1) // PAGE_SIZE)
    page_index = min(max(page_index + delta, 0), total - 1)
    current_ids = visible[page_index * PAGE_SIZE:(page_index + 1) * PAGE_SIZE]
    if selected not in current_ids:
        selected = current_ids[0] if current_ids else None
    draw_cards()
    choose()

prev_button = ctk.CTkButton(pager, text="← Précédent", width=135, height=32, fg_color=EDGE, command=lambda: turn_page(-1))
prev_button.grid(row=0, column=0)
page_label = ctk.CTkLabel(pager, text="", text_color=MUTED)
page_label.grid(row=0, column=1)
next_button = ctk.CTkButton(pager, text="Suivant →", width=135, height=32, fg_color=EDGE, command=lambda: turn_page(1))
next_button.grid(row=0, column=2)

def matches(row, query):
    return not query or any(name.startswith(query) for name in row.get("_search_names", ()))

def refresh(*args):
    global visible, selected, page_index, refresh_job
    if refresh_job is not None:
        root.after_cancel(refresh_job)
        refresh_job = None
    page_index = 0
    previous = selected
    query = normalized(search_var.get())
    visible = sorted((ident for ident, row in items.items()
        if matches(row, query)
        and (category_var.get() == "Toutes les catégories" or row["category"] == category_var.get())
        and (experimental_var.get() or row["status"] != "experimental")
        and (not favorite_filter.get() or ident in favorites)), key=lambda ident: (ident not in favorites, normalized(items[ident]["label"])))
    selected = previous if previous in visible[:PAGE_SIZE] else (visible[0] if visible else None)
    draw_cards()
    choose()
    count_label.configure(text=f"{len(visible)} résultats  •  {len(items)} objets au catalogue  •  {len(favorites)} favoris")

WORDS_FR = {"chair": "Chaise", "table": "Table", "lamp": "Lampe", "door": "Porte", "window": "Fenêtre", "box": "Boîte", "bottle": "Bouteille", "phone": "Téléphone", "key": "Clé", "book": "Livre", "books": "Livres", "bed": "Lit", "sofa": "Canapé", "tv": "Télé", "radio": "Radio", "guitar": "Guitare", "piano": "Piano", "fan": "Ventilateur", "wheel": "Roue", "car": "Voiture", "tire": "Pneu", "tires": "Pneus", "chest": "Coffre", "locked": "Verrouillé", "vase": "Vase", "breakable": "Cassable", "planks": "Planches", "wooden": "En bois", "small": "Petit", "big": "Grand", "large": "Grand", "long": "Long", "wall": "Mur", "floor": "Sol", "cable": "Câble", "ladder": "Échelle", "lever": "Levier", "button": "Bouton", "switch": "Interrupteur", "coin": "Pièce", "money": "Argent", "food": "Nourriture", "drink": "Boisson", "fruit": "Fruit", "fish": "Poisson", "flower": "Fleur", "plant": "Plante", "suit": "Costume", "shoes": "Chaussures", "watch": "Montre", "wrist": "Poignet", "paper": "Papier", "papers": "Papiers", "notepad": "Bloc-notes", "sink": "Évier", "kettle": "Bouilloire", "keyboard": "Clavier", "mouse": "Souris", "pc": "Ordinateur", "case": "Valise", "battery": "Batterie", "puddle": "Flaque", "water": "Eau", "tree": "Arbre", "lock": "Serrure", "padlock": "Cadenas", "hanging": "Suspendu", "street": "Rue", "boss": "Patron", "garden": "Jardin", "kitchen": "Cuisine", "office": "Bureau", "library": "Bibliothèque", "shelf": "Étagère", "bookshelf": "Bibliothèque", "cupboard": "Placard", "junk": "Bric-à-brac", "set": "Ensemble", "item": "Objet", "child": "Enfant", "bench": "Banc", "stove": "Cuisinière", "fridge": "Frigo", "cab": "Meuble", "cabinet": "Meuble", "top": "Haut", "bottom": "Bas", "alarm": "Alarme", "light": "Lumière", "flashlight": "Lampe torche", "train": "Train", "cargo": "Cargo", "carriage": "Wagon", "lift": "Ascenseur", "elevator": "Ascenseur", "vending": "Distributeur", "machine": "Machine", "passport": "Passeport", "hand": "Main", "golden": "Doré", "figure": "Figurine", "cat": "Chat", "rat": "Rat", "bird": "Oiseau", "birds": "Oiseaux"}

def pretty_label(internal):
    name = re.sub(r"^(?:BPP|BPA|BPC|BP|DEV)_", "", internal)
    name = re.sub(r"_C$", "", name)
    parts = [p for p in re.split(r"[_\s]+", re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)) if p]
    words = [WORDS_FR.get(p.lower(), p) for p in parts]
    return " ".join(words) if words else internal

def load_catalog():
    global items
    try:
        with (scripts_dir() / "items_catalog.tsv").open(encoding="utf-8", newline="") as file:
            items = {row["id"]: row for row in csv.DictReader(file, delimiter="\t")}
        discovered_file = scripts_dir() / "items_discovered.tsv"
        if discovered_file.is_file():
            with discovered_file.open(encoding="utf-8", newline="") as file:
                for row in csv.DictReader(file, delimiter="\t"):
                    if row.get("id") and row["id"] not in items:
                        row["label"] = pretty_label(row.get("internal") or row["id"])
                        items[row["id"]] = row
        for row in items.values():
            row.setdefault("category", "Divers")
            if row["id"] == "BP_Key_PC06_Painter_C":
                row["status"] = "signale_fonctionnel"
            if row["id"] == "BPA_Cat_C":
                row["status"] = "experimental"
        for row in items.values():
            names = [normalized(row["label"]), normalized(row.get("internal", row["id"].removesuffix("_C")))]
            names += [re.sub(r"^(?:bpa|bp)\s+", "", name.lstrip()) for name in names[:]]
            if row["id"] == "Lockpick_C":
                names += ["crochetage", "lockpick"]
            row["_search_names"] = tuple(names)
        categories = ["Toutes les catégories"] + sorted({row["category"] for row in items.values()})
        category_select.configure(values=categories)
        category_var.set(categories[0])
        refresh()
        status_var.set(f"Catalogue chargé : {len(items)} classes. Charge ta partie avant le spawn.")
    except (OSError, KeyError) as error:
        items = {}
        refresh()
        status_var.set("Catalogue introuvable ou invalide : " + str(error))

def schedule_refresh(*args):
    global refresh_job
    if refresh_job is not None:
        root.after_cancel(refresh_job)
    refresh_job = root.after(160, refresh)

search_var.trace_add("write", schedule_refresh)

character_content = ctk.CTkScrollableFrame(pages["Personnage"], fg_color=BG)
character_content.pack(fill="both", expand=True)
page = character_content
ctk.CTkLabel(page, text="Personnage & discrétion", font=("Segoe UI", 25, "bold")).pack(anchor="w", pady=(0, 14))
ctk.CTkLabel(page, text="Active d’abord le trainer en jeu avec la touche d’activation. Chaque option a un raccourci clavier qui marche directement dans le jeu, tu peux le changer ici.", text_color=MUTED, wraplength=730, justify="left", anchor="w").pack(anchor="w", pady=(0, 12))
FEATURES = (
    ("god", "God mode", "Vie, air et chutes sans dégâts."),
    ("giant_safe", "Protection contre le géant", "Capture impossible, main du géant bloquée."),
    ("npc_invisible", "Discrétion face aux PNJ", "Réduit la réaction des PNJ (effet limité)."),
    ("stealth_test", "Furtivité du joueur", "Le géant ne te voit plus et n’entend plus tes pas."),
    ("noclip", "Noclip + vol", "ESPACE = monter, C ou CTRL = descendre. Lâche la touche pour t’arrêter."),
    ("speed", "Vitesse rapide", "Augmente la vitesse de déplacement du joueur (×2 par rapport à la normale)."),
)
toggle_vars = {}
trainer_armed = {"value": None}
pending_toggles = {}

def toggle(key):
    var = toggle_vars[key]
    if trainer_armed["value"] is False:
        var.set(False)
        status_var.set("Trainer désactivé : appuie sur la touche d’activation dans le jeu.")
        return
    desired = bool(var.get())
    command = key if key != "speed" else ("speed2" if desired else "speed1")
    if send(command):
        pending_toggles[key] = (desired, time.monotonic())
    else:
        var.set(not desired)

def shortcut_conflict(key):
    chosen = shortcut_vars[key].get()
    if chosen == "Aucun":
        return None
    for other, var in shortcut_vars.items():
        if other != key and var.get() == chosen:
            return "Ce raccourci est déjà utilisé par une autre option."
    if chosen in (hotkey_var.get(), toggle_key_var.get()):
        return "Ce raccourci est déjà pris par le spawn rapide ou par la touche d’activation."
    return None

def on_shortcut_change(key):
    problem = shortcut_conflict(key)
    status_var.set(problem if problem else "Raccourci enregistré : " + shortcut_vars[key].get())
    save_prefs()

for key, title, description in FEATURES:
    card = ctk.CTkFrame(page, fg_color=CARD, corner_radius=14)
    card.pack(fill="x", pady=5)
    card.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(card, text=title, font=("Segoe UI", 15, "bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=18, pady=(12, 0))
    ctk.CTkLabel(card, text=description, text_color=MUTED, anchor="w", justify="left", wraplength=470).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))
    ctk.CTkLabel(card, text="Raccourci", text_color=MUTED, font=("Segoe UI", 11)).grid(row=0, column=1, sticky="s", padx=8, pady=(10, 0))
    ctk.CTkOptionMenu(card, variable=shortcut_vars[key], values=SHORTCUT_CHOICES, width=110, height=28, fg_color=EDGE, button_color=ACCENT, button_hover_color="#26A79B", command=lambda _, k=key: on_shortcut_change(k)).grid(row=1, column=1, padx=8, pady=(0, 12))
    var = ctk.BooleanVar(value=False)
    toggle_vars[key] = var
    ctk.CTkSwitch(card, text="", variable=var, width=52, progress_color=ACCENT, command=lambda k=key: toggle(k)).grid(row=0, column=2, rowspan=2, padx=(10, 18))

page = pages["Journal"]
ctk.CTkLabel(page, text="Journal UE4SS", font=("Segoe UI", 25, "bold")).pack(anchor="w", pady=(0, 12))
ctk.CTkLabel(page, text="Nouvelles lignes [SPAWN], [FURTIVITE] et erreurs. Le succès signifie acteur créé, pas forcément ramassable.", text_color=MUTED, wraplength=730).pack(anchor="w", pady=(0, 12))
journal = ctk.CTkTextbox(page, fg_color=PANEL, font=("Consolas", 12), wrap="word")
journal.pack(fill="both", expand=True)
journal.configure(state="disabled")

def append_log(text):
    journal.configure(state="normal")
    journal.insert("end", text + "\n")
    if int(journal.index("end-1c").split(".")[0]) > 600:
        journal.delete("1.0", "100.0")
    journal.see("end")
    journal.configure(state="disabled")

def poll_log():
    global log_offset, log_path
    path = scripts_dir().parent.parent.parent / "UE4SS.log"
    try:
        size = path.stat().st_size
        if log_path != path:
            log_path, log_offset = path, size
        if size < log_offset:
            log_offset = 0
        with path.open("rb") as file:
            file.seek(log_offset)
            data = file.read(65536)
        end = data.rfind(b"\n")
        if end >= 0:
            data = data[:end+1]
            log_offset += len(data)
            for line in data.decode("utf-8", errors="replace").splitlines():
                if any(token in line for token in ("[SPAWN", "[CHAT", "[TRAINER", "[GEANT", "[RESULTAT", "[FURTIVITE", "get_function_ref", "Error:")):
                    append_log(line)
                    record_spawn_event(line)
                    if "[SPAWN ERREUR]" in line:
                        status_var.set("Échec du spawn : consulte Journal pour la cause et l’étape.")
                    elif "[SPAWN] Cree" in line:
                        status_var.set("UE4SS confirme la création d’un acteur. Vérifie son apparition et son interaction.")
    except OSError:
        pass
    root.after(1200, poll_log)

settings_content = ctk.CTkScrollableFrame(pages["Réglages"], fg_color=BG)
settings_content.pack(fill="both", expand=True)
page = settings_content
ctk.CTkLabel(page, text="Réglages", font=("Segoe UI", 25, "bold")).pack(anchor="w", pady=(0, 16))

def trainer_ini_path():
    return scripts_dir() / "trainer_config.ini"

def read_toggle_key():
    try:
        match = re.search(r"toggle_key\s*=\s*(\S+)", trainer_ini_path().read_text(encoding="utf-8"))
        return match.group(1) if match else "F7"
    except OSError:
        return "F7"

def write_toggle_key(value):
    try:
        trainer_ini_path().write_text("toggle_key=" + value + "\n", encoding="utf-8")
        toggle_key_var.set(value)
        status_var.set("Touche d’activation enregistrée : " + value + " — redémarre le jeu pour l’appliquer.")
    except OSError as error:
        status_var.set("Impossible d’écrire trainer_config.ini : " + str(error))

toggle_key_var.set(read_toggle_key())
keys_card = ctk.CTkFrame(page, fg_color=CARD, corner_radius=14)
keys_card.pack(fill="x", pady=6)
ctk.CTkLabel(keys_card, text="Touche d’activation (dans le jeu)", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=18, pady=(14, 2))
ctk.CTkLabel(keys_card, text="Appuie dessus en jeu pour activer le trainer et ouvrir ce menu. Une deuxième pression désactive tout et remet les valeurs par défaut. Redémarre le jeu après un changement.", text_color=MUTED, wraplength=640, justify="left").pack(anchor="w", padx=18)
ctk.CTkOptionMenu(keys_card, variable=toggle_key_var, values=["F5", "F6", "F7", "F8", "F9", "F11", "F12"], fg_color=EDGE, button_color=ACCENT, command=write_toggle_key).pack(anchor="w", padx=18, pady=14)

window_card = ctk.CTkFrame(page, fg_color=CARD, corner_radius=14)
window_card.pack(fill="x", pady=6)
ctk.CTkLabel(window_card, text="Fenêtre", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=18, pady=(14, 2))
ctk.CTkCheckBox(window_card, text="Toujours au premier plan (utile en jeu plein écran fenêtré)", variable=topmost_var, fg_color=ACCENT, command=lambda: (root.attributes("-topmost", bool(topmost_var.get())), save_prefs())).pack(anchor="w", padx=18, pady=(6, 14))

if not (scripts_dir() / "items_catalog.tsv").is_file():
    path_card = ctk.CTkFrame(page, fg_color=CARD, corner_radius=14)
    path_card.pack(fill="x", pady=6)
    ctk.CTkLabel(path_card, text="Dossier scripts du trainer", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=18, pady=(14, 2))
    ctk.CTkLabel(path_card, text="Détecté automatiquement. À changer seulement si le menu ne trouve pas le jeu.", text_color=MUTED).pack(anchor="w", padx=18)
    ctk.CTkEntry(path_card, textvariable=scripts_var, height=38).pack(fill="x", padx=18, pady=10)

    def select_folder():
        value = filedialog.askdirectory(title="Sélectionne le dossier TrainerMilitsioner/scripts")
        if value:
            scripts_var.set(value)
            prefs["scripts_manual"] = True
            save_prefs()
            load_catalog()

    ctk.CTkButton(path_card, text="Choisir le dossier", fg_color=EDGE, command=select_folder).pack(anchor="w", padx=18, pady=(0, 14))

ctk.CTkLabel(page, text="Les noms d’objets sont des traductions descriptives déduites des noms internes, pas les textes officiels du jeu.", text_color=MUTED, wraplength=700, justify="left").pack(anchor="w", pady=14)

# --- Vol : l'etat des touches est ecrit en continu dans trainer_input.tsv.
# Si le menu s'arrete, le fichier n'est plus mis a jour et le Lua lache les touches tout seul.
flight_seq = 0

def write_flight(up, down):
    global flight_seq
    flight_seq += 1
    path = scripts_dir() / "trainer_input.tsv"
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(f"{flight_seq}\t{int(up)}\t{int(down)}\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass

def flight_poll():
    active = toggle_vars["noclip"].get() and winapi is not None
    if active:
        up = down = False
        if is_game_foreground():
            user32_ = winapi[0]
            up = bool(user32_.GetAsyncKeyState(0x20) & 0x8000)
            down = bool(user32_.GetAsyncKeyState(0x43) & 0x8000) or bool(user32_.GetAsyncKeyState(0x11) & 0x8000)
        write_flight(up, down)
    root.after(60 if active else 300, flight_poll)

def close():
    save_prefs()
    try:
        (scripts_dir() / "menu_alive.txt").unlink()
    except OSError:
        pass
    root.destroy()


def record_spawn_event(line):
    if "[SPAWN] Cree :" not in line:
        return
    match = re.search(r"\[SPAWN\] Cree :\s+(\S+)", line)
    ident = match.group(1) if match else "inconnu"
    label = items.get(ident, {}).get("label", ident)
    stamp = time.strftime("%H:%M:%S")
    spawn_history.appendleft((ident, f"{stamp}  •  {label}"))
    refresh_history()

util = ctk.CTkScrollableFrame(pages["Utilitaires"], fg_color=BG)
util.pack(fill="both", expand=True)
ctk.CTkLabel(util, text="Gestion des spawns", font=("Segoe UI", 22, "bold")).pack(anchor="w", pady=(0, 12))

ctk.CTkLabel(util, text="Nettoyage de tes créations", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(18, 8))

def clear_spawns(all_spawns):
    text = "Détruire tous les objets suivis, créés par ce trainer dans cette session ?" if all_spawns else "Détruire le dernier objet suivi, créé par ce trainer ?"
    if messagebox.askyesno("Nettoyage des spawns", text + "\nCela peut aussi affecter un objet que tu as ensuite ramassé. Les spawns antérieurs à un redémarrage du Lua ne sont pas suivis.", parent=root):
        send("spawn_clear" if all_spawns else "spawn_delete_last")

cleanup = ctk.CTkFrame(util, fg_color="transparent")
cleanup.pack(fill="x", pady=5)
ctk.CTkButton(cleanup, text="Supprimer le dernier spawn", command=lambda: clear_spawns(False), fg_color="#874641").pack(side="left", padx=4)
ctk.CTkButton(cleanup, text="Nettoyer mes spawns", command=lambda: clear_spawns(True), fg_color="#874641").pack(side="left", padx=4)
ctk.CTkButton(util, text="Refaire le dernier spawn demandé", command=lambda: request_spawn(last_recreate_id)).pack(anchor="w", pady=10)
ctk.CTkLabel(util, text="Historique des créations confirmées dans le journal (session du menu)", text_color=MUTED).pack(anchor="w", pady=(14, 5))
history_box = ctk.CTkTextbox(util, height=150, fg_color=PANEL)
history_box.pack(fill="x", pady=5)
history_box.configure(state="disabled")

def refresh_history():
    history_box.configure(state="normal")
    history_box.delete("1.0", "end")
    history_box.insert("end", "\n".join(entry[1] for entry in spawn_history) or "Aucune création encore reçue.")
    history_box.configure(state="disabled")

ctk.CTkLabel(util, text="Compteurs à la demande", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(18, 8))
counter_label = ctk.CTkLabel(util, text="PNJ / géants / mes spawns : non actualisés", text_color=MUTED, anchor="w")
counter_label.pack(anchor="w")
ctk.CTkButton(util, text="Lire les compteurs", command=lambda: request_snapshot()).pack(anchor="w", pady=6)

movement_panel = ctk.CTkFrame(character_content, fg_color=CARD, corner_radius=14)
movement_panel.pack(fill="x", pady=6)
ctk.CTkLabel(movement_panel, text="Déplacement réglable — appliquer explicitement", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=16, pady=10)
movement_controls = {}
for key, title, minimum, maximum, default, steps in (
    ("speed_factor", "Multiplicateur de vitesse", 0.5, 4, 1, 14),
    ("jump", "Multiplicateur de saut", 0.25, 4, 1, 15),
    ("gravity", "Multiplicateur de gravité", 0.1, 3, 1, 29)):
    frame = ctk.CTkFrame(movement_panel, fg_color="transparent")
    frame.pack(fill="x", padx=12, pady=3)
    value = ctk.DoubleVar(value=default)
    ctk.CTkLabel(frame, text=title, width=190, anchor="w").pack(side="left")
    slider = ctk.CTkSlider(frame, from_=minimum, to=maximum, number_of_steps=steps, variable=value, width=240)
    slider.pack(side="left", padx=8)
    number = ctk.CTkLabel(frame, text=f"{default:g}", width=50)
    number.pack(side="left")
    movement_controls[key] = (value, number)
    slider.configure(command=lambda v,label=number: label.configure(text=f"{v:.2f}"))
    ctk.CTkButton(frame, text="Appliquer", width=90, command=lambda k=key,v=value: send(f"movement {k} {v.get():.4f}")).pack(side="left", padx=4)
def movement_defaults():
    if send("movement restore"):
        status_var.set("Retour par défaut demandé — en attente du Lua. Retourne dans le jeu pour laisser la commande s’exécuter.")

ctk.CTkButton(movement_panel, text="PAR DÉFAUT — vitesse / saut / gravité", command=movement_defaults, fg_color=ACCENT).pack(anchor="w", padx=16, pady=12)

# Compteurs (PNJ / spawns) à la demande.
def request_snapshot():
    global last_snapshot_request
    ident = uuid.uuid4().hex[:10]
    if send("trainer_snapshot " + ident):
        last_snapshot_request = ident
        root.after(900, read_snapshot)
        root.after(1800, read_snapshot)

def read_snapshot():
    try:
        with (scripts_dir() / "trainer_state.tsv").open(encoding="utf-8", newline="") as file:
            values = {row["key"]: row["value"] for row in csv.DictReader(file, delimiter="\t")}
        if values.get("request_id") != last_snapshot_request:
            return
        def fmt(key):
            return values.get(key, "indisponible")
        counter_label.configure(text=f"PNJ (inclut le géant) : {fmt('npcs')}  •  Géants : {fmt('giants')}  •  Mes spawns suivis : {fmt('spawns')}  •  En file : {fmt('queued')}")
    except (OSError, KeyError):
        pass

hotkey_panel = ctk.CTkFrame(settings_content, fg_color=CARD, corner_radius=14)
hotkey_panel.pack(fill="x", pady=6)
ctk.CTkLabel(hotkey_panel, text="Spawn rapide dans le jeu", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=18, pady=(14, 2))
ctk.CTkLabel(hotkey_panel, text="Sélectionne un objet dans le menu, retourne dans le jeu et appuie sur la touche : un appui = un lot. Le menu doit rester ouvert (il peut être réduit).", text_color=MUTED, wraplength=640, justify="left").pack(anchor="w", padx=18)
ctk.CTkCheckBox(hotkey_panel, text="Activer la touche de spawn", variable=hotkey_enabled, fg_color=ACCENT, command=save_prefs).pack(anchor="w", padx=18, pady=8)
ctk.CTkOptionMenu(hotkey_panel, variable=hotkey_var, values=["F6", "F7", "F8", "F9", "F10", "F11", "F12"], fg_color=EDGE, button_color=ACCENT, command=lambda _: save_prefs()).pack(anchor="w", padx=18, pady=(0, 14))

winapi = None
if os.name == "nt":
    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    winapi = (user32,kernel32)
foreground_cache = (None,0.0,False)

def is_game_foreground():
    global foreground_cache
    if winapi is None:
        return False
    user32,kernel32 = winapi
    window = user32.GetForegroundWindow()
    now = time.monotonic()
    if window == foreground_cache[0] and now - foreground_cache[1] < 0.5:
        return foreground_cache[2]
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(window, ctypes.byref(pid))
    handle = kernel32.OpenProcess(0x1000, False, pid.value)
    result = False
    if handle:
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            size = wintypes.DWORD(len(buffer))
            if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                result = Path(buffer.value).name.casefold() == "tallproject-win64-shipping.exe"
        finally:
            kernel32.CloseHandle(handle)
    foreground_cache = (window,now,result)
    return result

def spawn_hotkey_poll():
    global hotkey_down
    enabled = hotkey_enabled.get() and winapi is not None
    pressed = False
    if enabled:
        try:
            vk = 0x70 + int(hotkey_var.get()[1:]) - 1
            pressed = bool(winapi[0].GetAsyncKeyState(vk) & 0x8000)
            if pressed and not hotkey_down and is_game_foreground():
                request_spawn(last_selected_spawn)
        except (ValueError,OSError):
            pass
    hotkey_down = pressed
    root.after(70 if enabled else 350, spawn_hotkey_poll)

shortcut_down = {}

def shortcut_poll():
    delay = 300
    if winapi is not None and trainer_armed["value"]:
        delay = 40
        try:
            user32_ = winapi[0]
            shift = bool(user32_.GetAsyncKeyState(0x10) & 0x8000)
            in_game = is_game_foreground()
            for key, var in shortcut_vars.items():
                choice = var.get()
                if choice == "Aucun":
                    shortcut_down[key] = False
                    continue
                with_shift = choice.startswith("Maj+")
                vk = 0x70 + int(choice.split("F")[-1]) - 1
                pressed = bool(user32_.GetAsyncKeyState(vk) & 0x8000) and shift == with_shift
                if pressed and not shortcut_down.get(key) and in_game:
                    toggle_vars[key].set(not toggle_vars[key].get())
                    toggle(key)
                shortcut_down[key] = pressed
        except (ValueError, OSError):
            pass
    root.after(delay, shortcut_poll)

refresh_history()
root.after(350, spawn_hotkey_poll)
root.after(400, shortcut_poll)


action_start_time = time.time()
last_action_stamp = None

def poll_action_result():
    global last_action_stamp
    path = scripts_dir() / "trainer_action_result.tsv"
    try:
        info = path.stat()
        stamp = (str(path), info.st_mtime_ns, info.st_size)
        if stamp != last_action_stamp and info.st_mtime >= action_start_time:
            with path.open(encoding="utf-8", newline="") as file:
                records = list(csv.DictReader(file, delimiter="\t"))
            if records and all(k in records[0] for k in ("module","status","message")):
                result = records[0]
                last_action_stamp = stamp
                state = result["status"]
                status_var.set("Lua • " + state + " : " + result["message"])
                append_log("[RETOUR LUA] " + result["module"] + " " + state + " " + result["message"])
                if result["module"] == "movement_default" and state == "OK":
                    for value, number in movement_controls.values():
                        value.set(1.0)
                        number.configure(text="1.00")
    except (OSError, ValueError, KeyError):
        pass
    root.after(900, poll_action_result)

root.after(900, poll_action_result)

def read_status():
    try:
        with (scripts_dir() / "trainer_status.tsv").open(encoding="utf-8", newline="") as file:
            return {row["key"]: row["value"] for row in csv.DictReader(file, delimiter="\t")}
    except (OSError, KeyError):
        return None

def apply_chip(text, color):
    status_chip.configure(text="●  " + text, fg_color=color)

def poll_trainer_status():
    data = read_status()
    fresh = False
    if data:
        try:
            fresh = abs(time.time() - int(data["time"])) < 8
        except (KeyError, ValueError):
            fresh = False
    if not fresh:
        apply_chip("Jeu non détecté", EDGE)
        chip_hint.configure(text="Lance le jeu puis appuie sur " + toggle_key_var.get())
        if trainer_armed["value"] is not None:
            trainer_armed["value"] = None
    else:
        armed = data.get("armed") == "1"
        if armed:
            apply_chip("Trainer ACTIF", GOOD)
            chip_hint.configure(text=toggle_key_var.get() + " en jeu = désactiver")
        else:
            apply_chip("Désactivé", WARN)
            chip_hint.configure(text="Appuie sur " + toggle_key_var.get() + " en jeu pour activer")
        for key, var in toggle_vars.items():
            wanted = data.get(key) == "1"
            if key in pending_toggles:
                desired, stamp = pending_toggles[key]
                if wanted == desired or time.monotonic() - stamp > 4:
                    pending_toggles.pop(key, None)
                else:
                    continue
            if bool(var.get()) != wanted:
                var.set(wanted)
        previous = trainer_armed["value"]
        if previous is not None and previous != armed:
            try:
                if armed:
                    root.deiconify()
                    root.lift()
                    root.attributes("-topmost", True)
                    root.after(300, lambda: root.attributes("-topmost", bool(topmost_var.get())))
                else:
                    root.iconify()
            except tk.TclError:
                pass
        trainer_armed["value"] = armed
    root.after(500, poll_trainer_status)

def heartbeat():
    try:
        (scripts_dir() / "menu_alive.txt").write_text(str(int(time.time())), encoding="utf-8")
    except OSError:
        pass
    root.after(1000, heartbeat)

root.attributes("-topmost", bool(topmost_var.get()))
root.after(200, poll_trainer_status)
root.after(100, heartbeat)
root.protocol("WM_DELETE_WINDOW", close)
show_page("Objets")
load_catalog()
root.after(1200, poll_log)
root.after(300, flight_poll)
root.mainloop()
