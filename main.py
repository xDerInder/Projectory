import flet as ft
from functools import partial
import json
import subprocess
import os
import re
from pathlib import Path
from datei_scanner import looks_like_project_by_files, IGNORED_FOLDERS

APPDATA_DIR = Path(os.getenv("APPDATA")) / "ProgrammierExplorer"
APPDATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = APPDATA_DIR / "config.json"
FAVORITES_FILE = APPDATA_DIR / "favorites.json"

state = {}

LANG_ICONS = {
    ".py": ft.Icons.PEST_CONTROL,
    ".js": ft.Icons.JAVASCRIPT,
    ".ts": ft.Icons.DEVELOPER_MODE,
    ".rs": ft.Icons.BUG_REPORT,
    ".java": ft.Icons.COFFEE,
    ".cpp": ft.Icons.DEVICE_HUB,
    ".cs": ft.Icons.WINDOW,
    ".html": ft.Icons.HTML,
    ".css": ft.Icons.PALETTE,
    ".json": ft.Icons.DATASET,
    ".go": ft.Icons.SPORTS_MOTORSPORTS,
}
LANG_COLORS = {
    ".py": ft.Colors.GREEN_ACCENT,
    ".ts": ft.Colors.LIGHT_BLUE,
    ".rs": ft.Colors.RED_ACCENT,
    ".java": ft.Colors.DEEP_ORANGE,
    ".cpp": ft.Colors.INDIGO,
    ".cs": ft.Colors.BLUE,
    ".html": ft.Colors.ORANGE,
    ".css": ft.Colors.PINK,
    ".json": ft.Colors.CYAN,
    ".go": ft.Colors.LIGHT_GREEN_ACCENT,
}


def add_new_path():
    new_path = state["new_path_field"].value.strip()
    if new_path and os.path.exists(new_path):
        if new_path not in state["config"]["scan_paths"]:
            state["config"]["scan_paths"].append(new_path)
            save_config(state["config"])
            state["new_path_field"].value = ""
            refresh()
    else:
        dlg = ft.AlertDialog(
            title=ft.Text("Fehler"),
            content=ft.Text("Pfad existiert nicht oder ist leer."),
            actions=[ft.TextButton("OK", on_click=lambda e: dlg.close())]
        )
        state["page"].dialog = dlg
        dlg.open = True
        state["page"].update()


def create_new_folder(e=None):
    folder_name = state["create_folder_field"].value.strip()
    if not folder_name:
        return "kein Name"

    base_dir = Path.home()
    new_folder = base_dir / folder_name

    if new_folder.exists():
        dlg = ft.AlertDialog(
            title=ft.Text("Fehler"),
            content=ft.Text("Ordner existiert bereits."),
            actions=[ft.TextButton("OK", on_click=lambda e: dlg.close())]
        )
        state["page"].dialog = dlg
        dlg.open = True
        state["page"].update()
        return

    try:
        new_folder.mkdir(parents=True)
        if str(new_folder) not in state["config"]["scan_paths"]:
            state["config"]["scan_paths"].append(str(new_folder))
            save_config(state["config"])
        state["create_folder_field"].value = ""
        refresh()
    except Exception as e:
        dlg = ft.AlertDialog(
            title=ft.Text("Fehler beim Erstellen"),
            content=ft.Text(str(e)),
            actions=[ft.TextButton("OK", on_click=lambda e: dlg.close())]
        )
        state["page"].dialog = dlg
        dlg.open = True
        state["page"].update()


def create_subfolder_from_dropdown(e):
    parent = state["subfolder_dropdown"].value
    name = state["subfolder_name_field"].value.strip()

    if not parent or not name:
        return

    new_path = Path(parent) / name
    if new_path.exists():
        dlg = ft.AlertDialog(
            title=ft.Text("Fehler"),
            content=ft.Text("Der Unterordner existiert bereits."),
            actions=[ft.TextButton("OK", on_click=lambda e: close_dialog())]
        )
        state["page"].dialog = dlg
        dlg.open = True
        state["page"].update()
        return

    try:
        new_path.mkdir(parents=True)
        refresh()
        state["subfolder_name_field"].value = ""
    except Exception as ex:
        dlg = ft.AlertDialog(
            title=ft.Text("Fehler beim Erstellen"),
            content=ft.Text(str(ex)),
            actions=[ft.TextButton("OK", on_click=lambda e: close_dialog())]
        )
        state["page"].dialog = dlg
        dlg.open = True
        state["page"].update()


def close_dialog():
    state["page"].dialog.open = False
    state["page"].update()


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"scan_paths": [], "vscode_path": "code", "theme_mode": "dark"}


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_favorites(favs):
    with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(favs)), f, indent=2)


def natural_sort_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(s))]


def detect_language(path: Path):
    try:
        for file in path.iterdir():
            if file.is_file():
                ext = file.suffix.lower()
                if ext in LANG_ICONS:
                    return LANG_ICONS[ext], LANG_COLORS.get(ext)
    except:
        pass
    return ft.Icons.FOLDER, ft.Colors.GREY_400


def open_in_vscode(path: str):
    subprocess.Popen([state["config"]["vscode_path"], path])


def open_in_explorer(path: str):
    subprocess.Popen(["explorer", path])


def toggle_favorite(path: str):
    favs = state["favorites"]
    if path in favs:
        favs.remove(path)
    else:
        favs.add(path)
    save_favorites(favs)
    refresh()


def apply_settings(e=None):
    cfg = state["config"]
    cfg["vscode_path"] = state["vscode_field"].value
    cfg["theme_mode"] = state["theme_toggle"].value and "dark" or "light"
    save_config(cfg)
    page = state["page"]
    page.theme_mode = cfg["theme_mode"] == "dark" and ft.ThemeMode.DARK or ft.ThemeMode.LIGHT
    state["settings_dialog"].open = False
    page.update()


def build_folder_tree(entry: Path, level: int = 0, search_term: str = "", favorites=None):
    items = []
    try:
        children = sorted(
            [p for p in entry.iterdir() if p.is_dir()
             and p.name not in IGNORED_FOLDERS],
            key=lambda p: natural_sort_key(p.name)
        )
    except PermissionError:
        return []

    for sub in children:
        sub_items = build_folder_tree(sub, level+1, search_term, favorites)
        if search_term and search_term.lower() not in sub.name.lower() and not sub_items:
            continue
        is_proj = looks_like_project_by_files(sub)
        icon, color = detect_language(sub) if is_proj else (
            ft.Icons.FOLDER, ft.Colors.GREY_400)
        fav_icon = ft.Icons.STAR if str(
            sub) in favorites else ft.Icons.STAR_BORDER
        actions = [
            ft.IconButton(ft.Icons.CODE, icon_color=color, tooltip="VS Code",
                          on_click=lambda e, p=sub: open_in_vscode(str(p))),
            ft.IconButton(ft.Icons.FOLDER_OPEN, icon_color=color, tooltip="Explorer",
                          on_click=lambda e, p=sub: open_in_explorer(str(p))),
            ft.IconButton(fav_icon, icon_color=ft.Colors.AMBER, tooltip="Favorit",
                          on_click=lambda e, p=str(sub): toggle_favorite(p)),
        ]
        exp = ft.ExpansionTile(
            leading=ft.Icon(icon, color=color, size=20),
            title=ft.Row([
                ft.Text(sub.name, color=ft.Colors.WHITE,
                        size=14, no_wrap=True, expand=True),
                *actions
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            dense=True,
            tile_padding=ft.padding.symmetric(horizontal=16, vertical=6),
            controls_padding=ft.padding.only(left=(level+1)*16),
            controls=sub_items
        )
        items.append(
            ft.Container(
                exp,
                padding=ft.padding.only(left=level*16),
                margin=ft.margin.only(bottom=4),
                border_radius=8,
                gradient=ft.LinearGradient(
                    colors=[ft.Colors.GREY_900, ft.Colors.GREY_800]),
                shadow=ft.BoxShadow(
                    spread_radius=1, blur_radius=4, color=ft.Colors.BLACK12, offset=ft.Offset(1, 2))
            )
        )
    return items


def refresh(e=None):
    search = state["search_box"].value
    col = state["tree_list"]
    col.controls.clear()

    valid_paths = []
    for bp in state["config"]["scan_paths"]:
        root = Path(bp)
        if not root.exists():
            continue
        valid_paths.append(bp)
        tiles = build_folder_tree(root, 0, search, state["favorites"])
        is_proj = looks_like_project_by_files(root)
        icon, color = detect_language(root) if is_proj else (
            ft.Icons.FOLDER, ft.Colors.GREY_400)
        fav_icon = ft.Icons.STAR if str(
            root) in state["favorites"] else ft.Icons.STAR_BORDER

        actions = [
            ft.IconButton(ft.Icons.CODE, icon_color=color, tooltip="VS Code",
                          on_click=lambda e, p=root: open_in_vscode(str(p))),
            ft.IconButton(ft.Icons.FOLDER_OPEN, icon_color=color, tooltip="Explorer",
                          on_click=lambda e, p=root: open_in_explorer(str(p))),
            ft.IconButton(fav_icon, icon_color=ft.Colors.AMBER, tooltip="Favorit",
                          on_click=lambda e, p=str(root): toggle_favorite(p)),
        ]

        exp = ft.ExpansionTile(
            leading=ft.Icon(icon, color=color, size=20),
            title=ft.Row([
                ft.Text(root.name, color=ft.Colors.WHITE, size=16,
                        weight=ft.FontWeight.BOLD, no_wrap=True, expand=True),
                *actions
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER),
            dense=False,
            tile_padding=ft.padding.symmetric(horizontal=16, vertical=8),
            controls_padding=ft.padding.only(left=16),
            controls=tiles
        )

        col.controls.append(
            ft.Container(
                exp,
                padding=ft.padding.all(10),
                margin=ft.margin.only(bottom=8),
                border_radius=12,
                gradient=ft.LinearGradient(
                    colors=[ft.Colors.GREY_900, ft.Colors.GREY_800]),
                shadow=ft.BoxShadow(
                    spread_radius=1, blur_radius=6, color=ft.Colors.BLACK12, offset=ft.Offset(2, 3))
            )
        )

    if valid_paths != state["config"]["scan_paths"]:
        state["config"]["scan_paths"] = valid_paths
        save_config(state["config"])

    state["page"].update()


def open_settings_dialog(e=None):
    state["settings_dialog"].open = True
    state["page"].dialog = state["settings_dialog"]
    state["page"].update()


def close_settings_dialog(e=None):
    state["settings_dialog"].open = False
    state["page"].update()


def main(page: ft.Page):
    cfg = load_config()
    state.update({
        "config": cfg,
        "favorites": load_favorites(),
        "page": page
    })

    page.title = "📂 Programmier - Explorer"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.Colors.BLACK87

    state["search_box"] = ft.TextField(
        hint_text="🔍 Projekt suchen...", expand=True, on_change=lambda e: refresh())
    state["vscode_field"] = ft.TextField(
        label="VS Code Pfad", value=cfg.get("vscode_path", "code"))
    state["theme_toggle"] = ft.Switch(label="Dark Mode", value=True)
    state["new_path_field"] = ft.TextField(label="Neuen Ordnerpfad hinzufügen")
    add_path_btn = ft.TextButton("Hinzufügen", on_click=add_new_path)

    state["create_folder_field"] = ft.TextField(
        label="Neuen Ordnernamen erstellen")
    create_folder_btn = ft.TextButton(
        "Ordner erstellen", on_click=create_new_folder)

    state["subfolder_dropdown"] = ft.Dropdown(label="Oberordner auswählen", options=[
                                              ft.dropdown.Option(p) for p in cfg.get("scan_paths", [])])
    state["subfolder_name_field"] = ft.TextField(label="Neuer Unterordnername")
    create_subfolder_btn = ft.TextButton(
        "Unterordner erstellen", on_click=create_subfolder_from_dropdown)

    state["settings_dialog"] = ft.AlertDialog(
        title=ft.Text("Einstellungen"),
        content=ft.Container(
            content=ft.Column([
                state["vscode_field"],
                state["theme_toggle"],
                state["new_path_field"],
                add_path_btn,
                state["create_folder_field"],
                create_folder_btn,
                ft.Divider(),
                state["subfolder_dropdown"],
                state["subfolder_name_field"],
                create_subfolder_btn
            ], tight=True, scroll=ft.ScrollMode.AUTO),
            width=500,
            height=500,
            padding=20
        ),
        actions=[
            ft.TextButton("Speichern", on_click=apply_settings),
            ft.TextButton("Abbrechen", on_click=close_settings_dialog)
        ]
    )

    state["tree_list"] = ft.Column(expand=True, spacing=0)

    page.add(
        ft.Row([
            ft.Text("Programmier - Explorer", size=24,
                    weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            state["search_box"],
            ft.IconButton(icon=ft.Icons.REFRESH,
                          tooltip="Neu laden", on_click=refresh),
            ft.IconButton(ft.Icons.SETTINGS, tooltip="Einstellungen",
                          on_click=open_settings_dialog)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(thickness=1),
        ft.Column(controls=[state["tree_list"]],
                  expand=True, scroll=ft.ScrollMode.AUTO),
        state["settings_dialog"]
    )

    refresh()


ft.app(target=main)
