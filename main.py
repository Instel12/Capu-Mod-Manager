import tkinter as tk
from tkinter import filedialog, messagebox
import json
import requests
import os
import shutil
import tempfile
import py7zr
import webbrowser

app = tk.Tk()
app.title("Capu Mod Manager")
app.geometry("410x287")
app.resizable(False, False)

APPDATA_DIR = os.path.join(os.getenv("APPDATA"), "capumodmanager")
os.makedirs(APPDATA_DIR, exist_ok=True)

INSTALLED_MODS_PATH = os.path.join(APPDATA_DIR, "mods.json")

def load_installed_mods():
    if os.path.exists(INSTALLED_MODS_PATH):
        with open(INSTALLED_MODS_PATH, "r") as f:
            return json.load(f)
    return []

def save_installed_mods(mods):
    with open(INSTALLED_MODS_PATH, "w") as f:
        json.dump(mods, f)

def open_game_folder():
    path = dir_var.get()
    if not os.path.isdir(path):
        messagebox.showerror("Error", "The selected game folder does not exist.")
        return
    os.startfile(path)

def browse_folder():
    folder_selected = filedialog.askdirectory(initialdir=dir_var.get())
    if folder_selected:
        dir_var.set(folder_selected)

def load_manifest():
    url = "https://raw.githubusercontent.com/Instel12/Capu-Mod-Manager/refs/heads/main/manifest.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        messagebox.showerror("Error", "Failed to load manifest.")
    except json.JSONDecodeError:
        messagebox.showerror("Error", "Manifest format error.")
    return []

def install_selected_mods():
    game_dir = dir_var.get()
    if not os.path.isdir(game_dir):
        messagebox.showerror("Error", "Invalid game directory.")
        return

    plugins_dir = os.path.join(game_dir, "BepInEx", "plugins")
    os.makedirs(plugins_dir, exist_ok=True)

    selected_mods = [mod for mod in manifest if mod_vars[mod["title"]].get() == 1]
    selected_titles = [mod["title"] for mod in selected_mods]
    previously_installed = load_installed_mods()

    try:
        for mod in manifest:
            title = mod["title"]
            if title in previously_installed and title not in selected_titles:
                file_name = mod.get("download", "").split("/")[-1]
                if file_name:
                    path = os.path.join(plugins_dir, file_name)
                    if os.path.exists(path):
                        os.remove(path)

        for mod in selected_mods:
            title = mod.get("title", "Unknown")
            url = mod.get("download")
            if not url:
                continue

            response = requests.get(url, stream=True)
            response.raise_for_status()
            file_name = url.split("/")[-1]
            temp_path = os.path.join(tempfile.gettempdir(), file_name)

            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if title == "BepInEx" and file_name.endswith(".7z"):
                with py7zr.SevenZipFile(temp_path, mode='r') as archive:
                    archive.extractall(path=game_dir)
            else:
                if file_name.endswith(".7z"):
                    with py7zr.SevenZipFile(temp_path, mode='r') as archive:
                        archive.extractall(path=plugins_dir)
                else:
                    shutil.copy(temp_path, os.path.join(plugins_dir, file_name))

            os.remove(temp_path)

        save_installed_mods(selected_titles)
        messagebox.showinfo("Success", "Selected mods installed/updated.")

    except Exception as e:
        messagebox.showerror("Error", f"Installation failed:\n{e}")

top_frame = tk.Frame(app)
top_frame.pack(side=tk.TOP, fill=tk.X, padx=4, pady=4)

dir_var = tk.StringVar(value=r"C:\Program Files (x86)\Steam\steamapps\common\Capuchin")
entry = tk.Entry(top_frame, textvariable=dir_var)
entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))

browse_button = tk.Button(top_frame, text="Browse", command=browse_folder)
browse_button.grid(row=0, column=1)
top_frame.columnconfigure(0, weight=1)

mods_frame = tk.Frame(app, highlightbackground="gray", highlightthickness=1, height=200)
mods_frame.pack(fill=tk.X, padx=6, pady=6)
mods_frame.pack_propagate(False)

canvas = tk.Canvas(mods_frame, borderwidth=0)
scrollbar = tk.Scrollbar(mods_frame, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas)

scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

def on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

canvas.bind_all("<MouseWheel>", on_mousewheel)

search_var = tk.StringVar()

search_frame = tk.Frame(app)
search_frame.pack(fill="x", padx=6, pady=(0, 6))

search_entry = tk.Entry(search_frame, textvariable=search_var)
search_entry.pack(side="left", fill="x", expand=True, padx=(0, 0))
search_placeholder = "Search mods..."

def on_entry_focus_in(event):
    if search_entry.get() == search_placeholder:
        search_entry.delete(0, tk.END)
        search_entry.config(fg="black")

def on_entry_focus_out(event):
    if search_entry.get() == "":
        search_entry.insert(0, search_placeholder)
        search_entry.config(fg="gray")

search_entry.insert(0, search_placeholder)
search_entry.config(fg="gray")

search_entry.bind("<FocusIn>", on_entry_focus_in)
search_entry.bind("<FocusOut>", on_entry_focus_out)

mod_vars = {}
mod_checkbuttons = {}
manifest = load_manifest()

def update_caputilla_requirement():
    requires_caputilla = any(
        mod.get("requirescaputilla", "false").lower() == "true" and mod_vars.get(mod["title"], tk.IntVar()).get() == 1
        for mod in manifest
    )
    caputilla_var = mod_vars.get("Caputilla")
    caputilla_cb = mod_checkbuttons.get("Caputilla")

    if caputilla_var and caputilla_cb:
        if requires_caputilla:
            caputilla_var.set(1)
            caputilla_cb.config(state="disabled")
        else:
            caputilla_cb.config(state="normal")

def filter_mods(*args):
    search_term = search_var.get().lower()
    visible_rows = []

    for mod in manifest:
        title = mod.get("title", "")
        cb = mod_checkbuttons.get(title)
        row_frame = cb.master if cb else None
        if row_frame:
            if search_term in title.lower():
                visible_rows.append(row_frame)
            else:
                row_frame.pack_forget()

    for row in visible_rows:
        row.pack_forget()
    for i, row in enumerate(visible_rows):
        row.pack(fill="x")

        bg = "#f0f0f0" if i % 2 == 0 else "#ffffff"
        row.configure(bg=bg)
        for widget in row.winfo_children():
            if isinstance(widget, (tk.Checkbutton, tk.Label)):
                widget.configure(bg=bg)

search_var.trace_add("write", filter_mods)

installed = load_installed_mods()
from collections import defaultdict

# Group mods by category
mods_by_category = defaultdict(list)
for mod in manifest:
    category = mod.get("catagory", "Other")
    mods_by_category[category].append(mod)

row_index = 0
installed = load_installed_mods()

for category in sorted(mods_by_category.keys()):
    # Category label
    cat_label = tk.Label(scrollable_frame, text=category, font=("Arial", 10, "bold"), anchor="w")
    cat_label.pack(fill="x", pady=(8, 0), padx=10)
    cat_label.configure(bg="#dcdcdc")

    for mod in mods_by_category[category]:
        title = mod.get("title", "Unknown Mod")
        version = mod.get("version", "")
        author = mod.get("author", "Unknown Author")
        requires_caputilla = mod.get("requirescaputilla", "false").lower() == "true"
        default_checked = 1 if title in installed or title == "BepInEx" else 0

        var = tk.IntVar(value=default_checked)

        row_frame = tk.Frame(scrollable_frame, bg="#f0f0f0" if row_index % 2 == 0 else "#ffffff")
        row_frame.pack(fill="x")

        cb = tk.Checkbutton(
            row_frame,
            text=title,
            variable=var,
            command=update_caputilla_requirement,
            bg=row_frame["bg"],
            anchor="w"
        )
        cb.pack(side="left", padx=(10, 5))

        info_label = tk.Label(
            row_frame,
            text=f"{version} | by {author}",
            bg=row_frame["bg"],
            fg="gray"
        )
        info_label.pack(side="left", padx=5)

        if title == "BepInEx":
            cb.config(state="disabled")

        mod_vars[title] = var
        mod_checkbuttons[title] = cb

        row_index += 1


update_caputilla_requirement()

bottom_frame = tk.Frame(app)
bottom_frame.pack(pady=(0, 10))

install_button = tk.Button(bottom_frame, text="Install / Update", width=20, command=install_selected_mods)
install_button.pack(side="left", padx=5)

open_folder_button = tk.Button(bottom_frame, text="Open Game Folder", width=20, command=open_game_folder)
open_folder_button.pack(side="left", padx=5)

def github():
    webbrowser.open('https://github.com/Instel12/Capu-Mod-Manager/tree/main')

github_button = tk.Button(bottom_frame, text="GitHub", width=10, command=github)
github_button.pack(side="left", padx=5)

menubar = tk.Menu(app)
app.config(menu=menubar)

app.mainloop()
