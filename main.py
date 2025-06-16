import tkinter as tk
from tkinter import filedialog, messagebox
import json
import requests
import os
import shutil
import tempfile
import py7zr

def open_game_folder():
    path = dir_var.get()
    if not os.path.isdir(path):
        messagebox.showerror("Error", "The selected game folder does not exist. Try setting the game directory somewhere else.")
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
        messagebox.showerror("Error", "Failed to load manifest, try again later. Please report this to the Github if there are still issues after around 2 days of trying again.")
    except json.JSONDecodeError:
        messagebox.showerror("Error", "manifest.json is incorrectly formatted.\nPlease report this issue to the GitHub!")
    return []

def install_selected_mods():
    game_dir = dir_var.get()
    if not os.path.isdir(game_dir):
        messagebox.showerror("Error", "Invalid game directory.")
        return

    plugins_dir = os.path.join(game_dir, "BepInEx", "plugins")
    os.makedirs(plugins_dir, exist_ok=True)

    selected_mods = [mod for mod in manifest if mod_vars[mod["title"]].get() == 1]

    if not selected_mods:
        messagebox.showinfo("No Mods Selected", "Please select at least one mod to install.")
        return

    try:
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
                    if chunk:
                        f.write(chunk)

            if title == "BepInEx" and file_name.endswith(".7z"):
                with py7zr.SevenZipFile(temp_path, mode='r') as archive:
                    archive.extractall(path=game_dir)
            else:
                if file_name.endswith(".dll"):
                    shutil.copy(temp_path, os.path.join(plugins_dir, file_name))
                elif file_name.endswith(".7z"):
                    with py7zr.SevenZipFile(temp_path, mode='r') as archive:
                        archive.extractall(path=plugins_dir)
                else:
                    shutil.copy(temp_path, os.path.join(plugins_dir, file_name))

            os.remove(temp_path)

        messagebox.showinfo("Success", "Selected mods have been installed or updated.")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to install mods:\n{e}")


app = tk.Tk()
app.title("Capu Mod Manager")
app.geometry("450x280")
app.resizable(False, False)

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

for index, mod in enumerate(manifest):
    title = mod.get("title", "Unknown Mod")
    version = mod.get("version", "")
    author = mod.get("author", "Unknown Author")
    requires_caputilla = mod.get("requirescaputilla", "false").lower() == "true"
    default_checked = 1 if title == "BepInEx" else 0

    var = tk.IntVar(value=default_checked)

    row_frame = tk.Frame(scrollable_frame, bg="#f0f0f0" if index % 2 == 0 else "#ffffff")
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

update_caputilla_requirement()

bottom_frame = tk.Frame(app)
bottom_frame.pack(pady=(0, 10))

install_button = tk.Button(bottom_frame, text="Install / Update", width=20, command=install_selected_mods)
install_button.pack(side="left", padx=5)

open_folder_button = tk.Button(bottom_frame, text="Open Game Folder", width=20, command=open_game_folder)
open_folder_button.pack(side="left", padx=5)

app.mainloop()
