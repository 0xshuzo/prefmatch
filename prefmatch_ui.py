#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from xml.sax.saxutils import escape


class PrefmatchUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Prefmatch UI")
        self.root.minsize(900, 620)
        self.style = ttk.Style()

        self.person_count_var = tk.StringVar(value="3")
        self.group_count_var = tk.StringVar(value="2")
        self.persons_per_group_var = tk.StringVar(value="2")
        self.preference_count_var = tk.StringVar(value="2")

        self.person_name_vars: list[tk.StringVar] = []
        self.group_name_vars: list[tk.StringVar] = []
        self.preference_rows: list[list[int]] = []
        self.preference_widgets: list[ttk.Combobox] = []
        self.preference_listbox: tk.Listbox | None = None
        self.person_name_listbox: tk.Listbox | None = None
        self.group_name_listbox: tk.Listbox | None = None
        self.person_name_editor_var = tk.StringVar()
        self.group_name_editor_var = tk.StringVar()
        self.selected_person_index = 0
        self.selected_person_name_index = 0
        self.selected_group_name_index = 0
        self.autosave_after_id: str | None = None
        self.autosave_status_var = tk.StringVar(value="Gespeichert")
        self.autosave_spinner: ttk.Progressbar | None = None
        self.autosave_check_label: ttk.Label | None = None
        self.preference_editor_canvas: tk.Canvas | None = None
        self.preference_editor_canvas_window: int | None = None

        self.configure_style()
        self.build_layout()
        self.bind_autosave()
        self.rebuild_forms()

    def configure_style(self) -> None:
        available_themes = set(self.style.theme_names())
        is_macos = sys.platform == "darwin"
        if is_macos and "aqua" in available_themes:
            self.style.theme_use("aqua")
        elif "clam" in available_themes:
            self.style.theme_use("clam")

        background = "#f5f7fb"
        card_background = "#ffffff"
        border = "#d8deea"
        accent = "#0f766e"
        text = "#172033"
        muted = "#5b6474"

        self.root.configure(bg=background)
        self.style.configure(".", font=("SF Pro Text", 13))
        self.style.configure("TFrame", background=background)
        self.style.configure("Card.TLabelframe", background=card_background, bordercolor=border, relief="solid")
        self.style.configure("Card.TLabelframe.Label", background=card_background, foreground=text, font=("SF Pro Display", 14, "bold"))
        self.style.configure("TLabel", background=background, foreground=text)
        self.style.configure("Surface.TFrame", background=card_background)
        self.style.configure("Surface.TLabel", background=card_background, foreground=text)
        self.style.configure("Section.TLabel", background=card_background, foreground=muted, font=("SF Pro Text", 11, "bold"))
        self.style.configure("Header.TLabel", background=card_background, foreground=muted, font=("SF Pro Text", 11, "bold"))
        self.style.configure("Saved.TLabel", background=background, foreground="#15803d", font=("SF Pro Text", 12, "bold"))
        self.style.configure("Saving.TLabel", background=background, foreground=muted, font=("SF Pro Text", 12))
        self.style.configure("TEntry", padding=8)
        self.style.configure("TCombobox", padding=6)
        self.style.configure("TButton", padding=(12, 8))

        if is_macos:
            # Aqua buttons render more reliably when native colors are left alone.
            self.style.configure("Accent.TButton", padding=(16, 10), font=("SF Pro Text", 13, "bold"))
        else:
            self.style.configure(
                "Accent.TButton",
                padding=(14, 10),
                foreground="#ffffff",
                background=accent,
                borderwidth=0,
                focusthickness=0,
            )
            self.style.map(
                "Accent.TButton",
                background=[("active", "#115e59"), ("pressed", "#134e4a")],
                foreground=[("disabled", "#d1d5db")],
            )

    def build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        config_frame = ttk.LabelFrame(self.root, text="Parameter", padding=12, style="Card.TLabelframe")
        config_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        config_frame.columnconfigure(1, weight=1)
        config_frame.columnconfigure(3, weight=1)

        self.add_labeled_entry(config_frame, 0, 0, "Personen", self.person_count_var)
        self.add_labeled_entry(config_frame, 0, 2, "Gruppen", self.group_count_var)
        self.add_labeled_entry(config_frame, 1, 0, "Personen pro Gruppe", self.persons_per_group_var)
        self.add_labeled_entry(config_frame, 1, 2, "Präferenzen pro Person", self.preference_count_var)

        rebuild_button = ttk.Button(
            config_frame,
            text="Formulare aktualisieren",
            command=self.rebuild_forms,
            style="Accent.TButton",
        )
        rebuild_button.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(8, 0))

        config_buttons = ttk.Frame(config_frame)
        config_buttons.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        config_buttons.columnconfigure(0, weight=1)
        config_buttons.columnconfigure(1, weight=1)

        export_config_button = ttk.Button(
            config_buttons,
            text="Konfiguration exportieren",
            command=self.export_configuration,
        )
        export_config_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        import_config_button = ttk.Button(
            config_buttons,
            text="Konfiguration importieren",
            command=self.import_configuration,
        )
        import_config_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        content_frame = ttk.Frame(self.root, padding=(12, 4, 12, 8))
        content_frame.grid(row=1, column=0, sticky="nsew")
        content_frame.columnconfigure(0, weight=2, minsize=360)
        content_frame.columnconfigure(1, weight=3, minsize=540)
        content_frame.rowconfigure(0, weight=1)

        names_frame = ttk.LabelFrame(content_frame, text="Namen", padding=16, style="Card.TLabelframe")
        names_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        names_frame.columnconfigure(0, weight=1)
        names_frame.rowconfigure(0, weight=1)

        self.names_container = ttk.Frame(names_frame, style="Surface.TFrame")
        self.names_container.grid(row=0, column=0, sticky="nsew")

        preferences_frame = ttk.LabelFrame(content_frame, text="Präferenzen", padding=16, style="Card.TLabelframe")
        preferences_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        preferences_frame.columnconfigure(0, weight=1)
        preferences_frame.rowconfigure(0, weight=1)

        self.preference_container = ttk.Frame(preferences_frame, style="Surface.TFrame")
        self.preference_container.grid(row=0, column=0, sticky="nsew")

        run_frame = ttk.Frame(self.root, padding=(12, 6, 12, 12))
        run_frame.grid(row=2, column=0, sticky="ew")
        run_frame.columnconfigure(0, weight=1)

        status_frame = ttk.Frame(run_frame)
        status_frame.grid(row=0, column=0, sticky="w")

        self.autosave_spinner = ttk.Progressbar(status_frame, mode="indeterminate", length=18)
        self.autosave_check_label = ttk.Label(status_frame, text="✓", style="Saved.TLabel")
        self.autosave_check_label.grid(row=0, column=0, sticky="w")

        self.autosave_label = ttk.Label(
            status_frame,
            textvariable=self.autosave_status_var,
            style="Saved.TLabel",
        )
        self.autosave_label.grid(row=0, column=1, sticky="w", padx=(8, 0))

        run_button = ttk.Button(run_frame, text="Zuordnung finden", command=self.run_program, style="Accent.TButton")
        run_button.grid(row=0, column=1, sticky="e")

    def add_labeled_entry(
        self, parent: ttk.Widget, row: int, column: int, label: str, variable: tk.StringVar
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", pady=2)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=column + 1, sticky="ew", pady=2, padx=(8, 16 if column == 0 else 0))

    def bind_autosave(self) -> None:
        for variable in (
            self.person_count_var,
            self.group_count_var,
            self.persons_per_group_var,
            self.preference_count_var,
            self.person_name_editor_var,
            self.group_name_editor_var,
        ):
            variable.trace_add("write", self.on_autosave_change)

    def on_autosave_change(self, *_args: object) -> None:
        self.schedule_autosave()

    def autosave_path(self) -> Path:
        return Path(__file__).resolve().parent / ".prefmatch_ui_autosave.json"

    def build_autosave_state(self) -> dict[str, object]:
        return {
            "person_count": self.person_count_var.get(),
            "group_count": self.group_count_var.get(),
            "persons_per_group": self.persons_per_group_var.get(),
            "preference_count": self.preference_count_var.get(),
            "person_names": [var.get() for var in self.person_name_vars],
            "group_names": [var.get() for var in self.group_name_vars],
            "preferences": [list(row) for row in self.preference_rows],
        }

    def schedule_autosave(self) -> None:
        if self.autosave_after_id is not None:
            self.root.after_cancel(self.autosave_after_id)
        self.autosave_after_id = self.root.after(250, self.write_autosave)

    def set_autosave_status(self, saved: bool) -> None:
        if self.autosave_spinner is None or self.autosave_check_label is None:
            return

        if saved:
            self.autosave_spinner.stop()
            self.autosave_spinner.grid_remove()
            self.autosave_check_label.grid()
            self.autosave_status_var.set("Gespeichert")
            self.autosave_label.configure(style="Saved.TLabel")
        else:
            self.autosave_check_label.grid_remove()
            self.autosave_spinner.grid(row=0, column=0, sticky="w")
            self.autosave_spinner.start(10)
            self.autosave_status_var.set("Wird gespeichert…")
            self.autosave_label.configure(style="Saving.TLabel")

    def write_autosave(self) -> None:
        self.autosave_after_id = None
        self.set_autosave_status(saved=False)
        self.root.update_idletasks()
        try:
            self.autosave_path().write_text(
                json.dumps(self.build_autosave_state(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass
        self.set_autosave_status(saved=True)

    def parse_positive_int(self, value: str, field_name: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} muss eine ganze Zahl sein.") from exc

        if parsed <= 0:
            raise ValueError(f"{field_name} muss größer als 0 sein.")

        return parsed

    def update_preference_editor_scroll_region(self, _event: tk.Event) -> None:
        if self.preference_editor_canvas is not None:
            self.preference_editor_canvas.configure(scrollregion=self.preference_editor_canvas.bbox("all"))

    def resize_preference_editor_canvas_window(self, event: tk.Event) -> None:
        if self.preference_editor_canvas is not None and self.preference_editor_canvas_window is not None:
            self.preference_editor_canvas.itemconfigure(self.preference_editor_canvas_window, width=event.width)

    def on_preference_editor_mousewheel(self, event: tk.Event) -> str:
        if self.preference_editor_canvas is None:
            return "break"

        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            raw_delta = getattr(event, "delta", 0)
            if raw_delta == 0:
                return "break"

            if sys.platform == "darwin":
                delta = -int(raw_delta)
                if delta == 0:
                    delta = -1 if raw_delta > 0 else 1
            elif sys.platform.startswith("win"):
                delta = -int(raw_delta / 120)
                if delta == 0:
                    delta = -1 if raw_delta > 0 else 1
            else:
                delta = -1 if raw_delta > 0 else 1

        self.preference_editor_canvas.yview_scroll(delta, "units")
        return "break"

    def read_dimensions(self) -> tuple[int, int, int, int]:
        person_count = self.parse_positive_int(self.person_count_var.get(), "Personen")
        group_count = self.parse_positive_int(self.group_count_var.get(), "Gruppen")
        persons_per_group = self.parse_positive_int(self.persons_per_group_var.get(), "Personen pro Gruppe")
        preference_count = self.parse_positive_int(self.preference_count_var.get(), "Präferenzen pro Person")

        if preference_count > group_count:
            raise ValueError("Präferenzen pro Person dürfen nicht größer als die Anzahl der Gruppen sein.")

        if person_count > group_count * persons_per_group:
            raise ValueError("Die Gruppenkapazität reicht nicht für alle Personen.")

        return person_count, group_count, persons_per_group, preference_count

    def rebuild_forms(self) -> None:
        try:
            person_count, group_count, _persons_per_group, preference_count = self.read_dimensions()
        except ValueError as exc:
            messagebox.showerror("Ungültige Eingabe", str(exc))
            return

        old_person_names = [var.get() for var in self.person_name_vars]
        old_group_names = [var.get() for var in self.group_name_vars]

        self.person_name_vars = []
        self.group_name_vars = []

        for child in self.names_container.winfo_children():
            child.destroy()

        names_person_frame = ttk.LabelFrame(self.names_container, text="Personennamen", padding=10, style="Card.TLabelframe")
        names_person_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        names_person_frame.columnconfigure(0, weight=1)
        names_person_frame.rowconfigure(1, weight=1)

        for person in range(person_count):
            default_name = old_person_names[person] if person < len(old_person_names) else f"Person {person + 1}"
            var = tk.StringVar(value=default_name)
            self.person_name_vars.append(var)

        ttk.Label(names_person_frame, text="Personen", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        person_list_frame = ttk.Frame(names_person_frame, style="Surface.TFrame")
        person_list_frame.grid(row=1, column=0, sticky="nsew")
        person_list_frame.columnconfigure(0, weight=1)
        person_list_frame.rowconfigure(0, weight=1)

        self.person_name_listbox = tk.Listbox(
            person_list_frame,
            height=14,
            exportselection=False,
            activestyle="none",
            font=("SF Pro Text", 12),
        )
        self.person_name_listbox.grid(row=0, column=0, sticky="nsew")
        person_scrollbar = ttk.Scrollbar(person_list_frame, orient="vertical", command=self.person_name_listbox.yview)
        person_scrollbar.grid(row=0, column=1, sticky="ns")
        self.person_name_listbox.configure(yscrollcommand=person_scrollbar.set)
        self.person_name_listbox.bind("<<ListboxSelect>>", self.on_person_name_selected)

        ttk.Label(names_person_frame, text="Ausgewählte Person", style="Header.TLabel").grid(row=2, column=0, sticky="w", pady=(10, 4))
        person_editor = ttk.Entry(names_person_frame, textvariable=self.person_name_editor_var)
        person_editor.grid(row=3, column=0, sticky="ew")
        person_editor.bind("<FocusOut>", self.on_person_name_editor_commit)
        person_editor.bind("<Return>", self.on_person_name_editor_commit)

        names_group_frame = ttk.LabelFrame(self.names_container, text="Gruppennamen", padding=10, style="Card.TLabelframe")
        names_group_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        names_group_frame.columnconfigure(0, weight=1)
        names_group_frame.rowconfigure(1, weight=1)

        for group in range(group_count):
            default_name = old_group_names[group] if group < len(old_group_names) else f"Gruppe {group + 1}"
            var = tk.StringVar(value=default_name)
            self.group_name_vars.append(var)

        ttk.Label(names_group_frame, text="Gruppen", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        group_list_frame = ttk.Frame(names_group_frame, style="Surface.TFrame")
        group_list_frame.grid(row=1, column=0, sticky="nsew")
        group_list_frame.columnconfigure(0, weight=1)
        group_list_frame.rowconfigure(0, weight=1)

        self.group_name_listbox = tk.Listbox(
            group_list_frame,
            height=10,
            exportselection=False,
            activestyle="none",
            font=("SF Pro Text", 12),
        )
        self.group_name_listbox.grid(row=0, column=0, sticky="nsew")
        group_scrollbar = ttk.Scrollbar(group_list_frame, orient="vertical", command=self.group_name_listbox.yview)
        group_scrollbar.grid(row=0, column=1, sticky="ns")
        self.group_name_listbox.configure(yscrollcommand=group_scrollbar.set)
        self.group_name_listbox.bind("<<ListboxSelect>>", self.on_group_name_selected)

        ttk.Label(names_group_frame, text="Ausgewählte Gruppe", style="Header.TLabel").grid(row=2, column=0, sticky="w", pady=(10, 4))
        group_editor = ttk.Entry(names_group_frame, textvariable=self.group_name_editor_var)
        group_editor.grid(row=3, column=0, sticky="ew")
        group_editor.bind("<FocusOut>", self.on_group_name_editor_commit)
        group_editor.bind("<Return>", self.on_group_name_editor_commit)

        self.names_container.columnconfigure(0, weight=1)
        self.names_container.columnconfigure(1, weight=1)
        self.names_container.rowconfigure(0, weight=1)
        self.preference_rows = self.normalize_preference_rows(
            person_count, group_count, preference_count, self.preference_rows
        )
        self.refresh_name_views()
        self.rebuild_preferences(preference_count)
        self.schedule_autosave()

    def on_names_changed(self, *_args: object) -> None:
        self.refresh_preference_views()
        self.schedule_autosave()

    def refresh_name_listbox(self, listbox: tk.Listbox | None, names: list[str], selected_index: int) -> None:
        if listbox is None:
            return

        listbox.delete(0, tk.END)
        for name in names:
            listbox.insert(tk.END, name)

        if not names:
            return

        selected_index = max(0, min(selected_index, len(names) - 1))
        listbox.selection_set(selected_index)
        listbox.activate(selected_index)
        listbox.see(selected_index)

    def refresh_name_views(self) -> None:
        person_names = [var.get() for var in self.person_name_vars]
        group_names = [var.get() for var in self.group_name_vars]

        self.selected_person_name_index = min(self.selected_person_name_index, max(0, len(person_names) - 1))
        self.selected_group_name_index = min(self.selected_group_name_index, max(0, len(group_names) - 1))

        self.refresh_name_listbox(self.person_name_listbox, person_names, self.selected_person_name_index)
        self.refresh_name_listbox(self.group_name_listbox, group_names, self.selected_group_name_index)

        self.person_name_editor_var.set(person_names[self.selected_person_name_index] if person_names else "")
        self.group_name_editor_var.set(group_names[self.selected_group_name_index] if group_names else "")

    def commit_person_name_editor(self) -> None:
        if not self.person_name_vars:
            return

        index = max(0, min(self.selected_person_name_index, len(self.person_name_vars) - 1))
        self.person_name_vars[index].set(self.person_name_editor_var.get().strip())
        self.refresh_name_views()
        self.on_names_changed()

    def commit_group_name_editor(self) -> None:
        if not self.group_name_vars:
            return

        index = max(0, min(self.selected_group_name_index, len(self.group_name_vars) - 1))
        self.group_name_vars[index].set(self.group_name_editor_var.get().strip())
        self.refresh_name_views()
        self.on_names_changed()

    def on_person_name_selected(self, _event: tk.Event | None = None) -> None:
        if self.person_name_listbox is None:
            return

        selection = self.person_name_listbox.curselection()
        if not selection:
            return

        self.commit_person_name_editor()
        self.selected_person_name_index = int(selection[0])
        self.refresh_name_views()

    def on_group_name_selected(self, _event: tk.Event | None = None) -> None:
        if self.group_name_listbox is None:
            return

        selection = self.group_name_listbox.curselection()
        if not selection:
            return

        self.commit_group_name_editor()
        self.selected_group_name_index = int(selection[0])
        self.refresh_name_views()

    def on_person_name_editor_commit(self, _event: tk.Event | None = None) -> str | None:
        self.commit_person_name_editor()
        return "break"

    def on_group_name_editor_commit(self, _event: tk.Event | None = None) -> str | None:
        self.commit_group_name_editor()
        return "break"

    def collect_person_names(self) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()

        for index, var in enumerate(self.person_name_vars):
            name = var.get().strip()
            if not name:
                raise ValueError(f"Name für Person {index} fehlt.")
            if name in seen:
                raise ValueError(f"Personenname doppelt vergeben: {name}")
            seen.add(name)
            names.append(name)

        return names

    def collect_group_names(self) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()

        for index, var in enumerate(self.group_name_vars):
            name = var.get().strip()
            if not name:
                raise ValueError(f"Name für Gruppe {index} fehlt.")
            if name in seen:
                raise ValueError(f"Gruppenname doppelt vergeben: {name}")
            seen.add(name)
            names.append(name)

        return names

    def normalize_preference_rows(
        self,
        person_count: int,
        group_count: int,
        preference_count: int,
        old_rows: list[list[int]],
    ) -> list[list[int]]:
        rows: list[list[int]] = []
        default_row = list(range(preference_count))

        for person in range(person_count):
            source_row = old_rows[person] if person < len(old_rows) else []
            normalized_row: list[int] = []
            seen: set[int] = set()

            for group_index in source_row:
                if 0 <= group_index < group_count and group_index not in seen:
                    normalized_row.append(group_index)
                    seen.add(group_index)
                if len(normalized_row) == preference_count:
                    break

            for group_index in default_row:
                if group_index not in seen:
                    normalized_row.append(group_index)
                    seen.add(group_index)
                if len(normalized_row) == preference_count:
                    break

            rows.append(normalized_row)

        return rows

    def group_display_values(self, group_names: list[str]) -> list[str]:
        return list(group_names)

    def parse_group_display_value(
        self,
        value: str,
        group_name_to_index: dict[str, int],
        person_name: str,
        pref: int,
    ) -> int:
        if not value:
            raise ValueError(f"Präferenz {pref + 1} für {person_name} ist leer.")

        group_index = group_name_to_index.get(value)
        if group_index is None:
            raise ValueError(f"Unbekannte Gruppe in Präferenz von {person_name}: {value}")

        return group_index

    def sync_current_preferences_from_editor(self) -> None:
        if not self.preference_widgets:
            return

        try:
            person_names = self.collect_person_names()
            group_names = self.collect_group_names()
        except ValueError:
            return

        if self.selected_person_index < 0 or self.selected_person_index >= len(self.preference_rows):
            return

        person_name = person_names[self.selected_person_index]
        group_name_to_index = {group_name: index for index, group_name in enumerate(group_names)}
        seen: set[int] = set()
        updated_row: list[int] = []

        for pref, combo in enumerate(self.preference_widgets):
            group_index = self.parse_group_display_value(
                combo.get().strip(), group_name_to_index, person_name, pref
            )
            if group_index in seen:
                raise ValueError(f"{person_name} enthält die Gruppe {group_names[group_index]} doppelt.")
            seen.add(group_index)
            updated_row.append(group_index)

        self.preference_rows[self.selected_person_index] = updated_row

    def populate_preference_editor(self) -> None:
        if not self.preference_widgets:
            return

        try:
            person_names = self.collect_person_names()
            group_names = self.collect_group_names()
        except ValueError:
            for combo in self.preference_widgets:
                combo.configure(values=())
                combo.set("")
            return

        if not person_names:
            return

        self.selected_person_index = max(0, min(self.selected_person_index, len(person_names) - 1))
        if self.preference_listbox is not None:
            self.preference_listbox.selection_clear(0, tk.END)
            self.preference_listbox.selection_set(self.selected_person_index)
            self.preference_listbox.activate(self.selected_person_index)
            self.preference_listbox.see(self.selected_person_index)

        group_display_values = self.group_display_values(group_names)
        current_row = self.preference_rows[self.selected_person_index]
        for pref, combo in enumerate(self.preference_widgets):
            combo.configure(values=group_display_values)
            if pref < len(current_row) and current_row[pref] < len(group_display_values):
                combo.set(group_display_values[current_row[pref]])
            else:
                combo.set("")

    def on_person_selected(self, _event: tk.Event | None = None) -> None:
        if self.preference_listbox is None:
            return

        selection = self.preference_listbox.curselection()
        if not selection:
            return

        try:
            self.sync_current_preferences_from_editor()
        except ValueError as exc:
            messagebox.showerror("Ungültige Eingabe", str(exc))
            if self.preference_listbox is not None:
                self.preference_listbox.selection_clear(0, tk.END)
                self.preference_listbox.selection_set(self.selected_person_index)
                self.preference_listbox.activate(self.selected_person_index)
            return

        self.selected_person_index = int(selection[0])
        self.populate_preference_editor()
        self.schedule_autosave()

    def on_preference_changed(self, _event: tk.Event | None = None) -> None:
        try:
            self.sync_current_preferences_from_editor()
        except ValueError as exc:
            messagebox.showerror("Ungültige Eingabe", str(exc))
            self.populate_preference_editor()
            return
        self.schedule_autosave()

    def refresh_preference_views(self) -> None:
        if self.preference_listbox is None:
            return

        try:
            person_names = self.collect_person_names()
        except ValueError:
            return

        self.preference_listbox.delete(0, tk.END)
        for person_name in person_names:
            self.preference_listbox.insert(tk.END, person_name)

        self.populate_preference_editor()

    def rebuild_preferences(self, preference_count: int) -> None:
        for child in self.preference_container.winfo_children():
            child.destroy()

        try:
            person_names = self.collect_person_names()
            group_names = self.collect_group_names()
        except ValueError:
            return

        self.preference_rows = self.normalize_preference_rows(
            len(person_names), len(group_names), preference_count, self.preference_rows
        )

        self.preference_container.columnconfigure(0, weight=0, minsize=220)
        self.preference_container.columnconfigure(1, weight=1)
        self.preference_container.rowconfigure(1, weight=1)

        ttk.Label(
            self.preference_container,
            text="Wähle links eine Person aus und bearbeite rechts ihre Präferenzen.",
            style="Header.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        person_frame = ttk.Frame(self.preference_container, style="Surface.TFrame")
        person_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 16))
        person_frame.columnconfigure(0, weight=1)
        person_frame.rowconfigure(1, weight=1)

        ttk.Label(person_frame, text="Personen", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.preference_listbox = tk.Listbox(
            person_frame,
            height=18,
            exportselection=False,
            activestyle="none",
            font=("SF Pro Text", 12),
        )
        self.preference_listbox.grid(row=1, column=0, sticky="nsew")
        person_scrollbar = ttk.Scrollbar(person_frame, orient="vertical", command=self.preference_listbox.yview)
        person_scrollbar.grid(row=1, column=1, sticky="ns")
        self.preference_listbox.configure(yscrollcommand=person_scrollbar.set)
        self.preference_listbox.bind("<<ListboxSelect>>", self.on_person_selected)

        editor_frame = ttk.Frame(self.preference_container, style="Surface.TFrame")
        editor_frame.grid(row=1, column=1, sticky="nsew")
        editor_frame.columnconfigure(0, weight=1)
        editor_frame.rowconfigure(1, weight=1)

        ttk.Label(editor_frame, text="Präferenzen", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.preference_editor_canvas = tk.Canvas(editor_frame, highlightthickness=0, bg="#ffffff")
        self.preference_editor_canvas.grid(row=1, column=0, sticky="nsew")
        editor_scrollbar = ttk.Scrollbar(
            editor_frame,
            orient="vertical",
            command=self.preference_editor_canvas.yview,
        )
        editor_scrollbar.grid(row=1, column=1, sticky="ns")
        self.preference_editor_canvas.configure(yscrollcommand=editor_scrollbar.set)

        editor_content = ttk.Frame(self.preference_editor_canvas, style="Surface.TFrame")
        editor_content.columnconfigure(1, weight=1)
        editor_content.bind("<Configure>", self.update_preference_editor_scroll_region)
        self.preference_editor_canvas.bind("<Configure>", self.resize_preference_editor_canvas_window)
        self.preference_editor_canvas_window = self.preference_editor_canvas.create_window(
            (0, 0), window=editor_content, anchor="nw"
        )

        self.preference_widgets = []
        group_display_values = self.group_display_values(group_names)
        for pref in range(preference_count):
            ttk.Label(editor_content, text=f"Präferenz {pref + 1}", style="Header.TLabel").grid(
                row=pref + 1, column=0, sticky="w", padx=(0, 12), pady=6
            )
            combo = ttk.Combobox(
                editor_content,
                values=group_display_values,
                state="readonly",
                width=30,
            )
            combo.grid(row=pref + 1, column=1, sticky="ew", pady=6)
            combo.bind("<<ComboboxSelected>>", self.on_preference_changed)
            combo.bind("<MouseWheel>", self.on_preference_editor_mousewheel)
            combo.bind("<Button-4>", self.on_preference_editor_mousewheel)
            combo.bind("<Button-5>", self.on_preference_editor_mousewheel)
            self.preference_widgets.append(combo)

        self.selected_person_index = min(self.selected_person_index, max(0, len(person_names) - 1))
        self.refresh_preference_views()

    def encode_preferences(self) -> str:
        self.sync_current_preferences_from_editor()
        person_names = self.collect_person_names()
        group_names = self.collect_group_names()
        encoded_rows: list[str] = []

        for person, row in enumerate(self.preference_rows):
            seen: set[int] = set()
            entries: list[str] = []

            if len(row) == 0:
                raise ValueError(f"Für {person_names[person]} wurden keine Präferenzen angegeben.")

            for pref, group_id in enumerate(row):
                if group_id < 0 or group_id >= len(group_names):
                    raise ValueError(f"Ungültige Gruppen-ID in Präferenz von {person_names[person]}: {group_id}")
                if group_id in seen:
                    raise ValueError(f"{person_names[person]} enthält die Gruppe {group_names[group_id]} doppelt.")

                seen.add(group_id)
                entries.append(str(group_id))

            encoded_rows.append(",".join(entries))

        return ";".join(encoded_rows)

    def collect_preference_sets(self) -> list[set[int]]:
        self.sync_current_preferences_from_editor()
        person_names = self.collect_person_names()
        group_names = self.collect_group_names()
        preference_sets: list[set[int]] = []

        for person, row in enumerate(self.preference_rows):
            person_preferences: set[int] = set()
            for group_id in row:
                if group_id < 0 or group_id >= len(group_names):
                    raise ValueError(
                        f"Ungültige Gruppen-ID in Präferenz von {person_names[person]}: {group_id}"
                    )
                person_preferences.add(group_id)

            preference_sets.append(person_preferences)

        return preference_sets

    def collect_preference_rows(self) -> list[list[int]]:
        self.sync_current_preferences_from_editor()
        person_names = self.collect_person_names()
        group_names = self.collect_group_names()
        preference_rows: list[list[int]] = []

        for person, row in enumerate(self.preference_rows):
            if len(row) == 0:
                raise ValueError(f"Für {person_names[person]} wurden keine Präferenzen angegeben.")
            for group_id in row:
                if group_id < 0 or group_id >= len(group_names):
                    raise ValueError(
                        f"Ungültige Gruppen-ID in Präferenz von {person_names[person]}: {group_id}"
                    )
            preference_rows.append(list(row))

        return preference_rows

    def build_configuration(self) -> dict[str, object]:
        person_count, group_count, persons_per_group, preference_count = self.read_dimensions()
        return {
            "person_count": person_count,
            "group_count": group_count,
            "persons_per_group": persons_per_group,
            "preference_count": preference_count,
            "person_names": self.collect_person_names(),
            "group_names": self.collect_group_names(),
            "preferences": self.collect_preference_rows(),
        }

    def export_configuration(self) -> None:
        try:
            config = self.build_configuration()
        except ValueError as exc:
            messagebox.showerror("Ungültige Eingabe", str(exc))
            return

        target = filedialog.asksaveasfilename(
            parent=self.root,
            title="Konfiguration exportieren",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Alle Dateien", "*.*")],
        )
        if not target:
            return

        Path(target).write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        messagebox.showinfo("Export", f"Konfiguration gespeichert:\n{target}")

    def import_configuration(self) -> None:
        source = filedialog.askopenfilename(
            parent=self.root,
            title="Konfiguration importieren",
            filetypes=[("JSON", "*.json"), ("Alle Dateien", "*.*")],
        )
        if not source:
            return

        try:
            config = json.loads(Path(source).read_text(encoding="utf-8"))
            self.apply_configuration(config)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            messagebox.showerror("Import fehlgeschlagen", str(exc))
            return

        messagebox.showinfo("Import", f"Konfiguration geladen:\n{source}")

    def apply_configuration(self, config: dict[str, object]) -> None:
        required_keys = {
            "person_count",
            "group_count",
            "persons_per_group",
            "preference_count",
            "person_names",
            "group_names",
            "preferences",
        }
        missing = required_keys.difference(config)
        if missing:
            raise ValueError(f"Konfiguration unvollständig: {', '.join(sorted(missing))}")

        person_count = int(config["person_count"])
        group_count = int(config["group_count"])
        persons_per_group = int(config["persons_per_group"])
        preference_count = int(config["preference_count"])
        person_names = [str(name) for name in config["person_names"]]
        group_names = [str(name) for name in config["group_names"]]
        preference_rows = [[int(group) for group in row] for row in config["preferences"]]

        if len(person_names) != person_count:
            raise ValueError("Anzahl der Personennamen passt nicht zur Personenanzahl.")
        if len(group_names) != group_count:
            raise ValueError("Anzahl der Gruppennamen passt nicht zur Gruppenanzahl.")
        if len(preference_rows) != person_count:
            raise ValueError("Anzahl der Präferenzzeilen passt nicht zur Personenanzahl.")
        for row in preference_rows:
            if len(row) != preference_count:
                raise ValueError("Eine Präferenzzeile hat nicht die erwartete Länge.")

        self.person_count_var.set(str(person_count))
        self.group_count_var.set(str(group_count))
        self.persons_per_group_var.set(str(persons_per_group))
        self.preference_count_var.set(str(preference_count))

        self.rebuild_forms()

        for index, name in enumerate(person_names):
            self.person_name_vars[index].set(name)
        for index, name in enumerate(group_names):
            self.group_name_vars[index].set(name)

        self.preference_rows = self.normalize_preference_rows(
            person_count, group_count, preference_count, preference_rows
        )
        self.rebuild_preferences(preference_count)
        self.schedule_autosave()
    def binary_path(self) -> Path:
        return Path(__file__).resolve().parent / "prefmatch"

    def run_program(self) -> None:
        try:
            person_count, group_count, persons_per_group, preference_count = self.read_dimensions()
            person_names = self.collect_person_names()
            group_names = self.collect_group_names()
            preferences = self.encode_preferences()
            preference_sets = self.collect_preference_sets()
        except ValueError as exc:
            messagebox.showerror("Ungültige Eingabe", str(exc))
            return

        binary = self.binary_path()
        if not binary.exists():
            messagebox.showerror("Binary fehlt", f"Binary nicht gefunden: {binary}")
            return

        command = [
            str(binary),
            str(person_count),
            str(group_count),
            str(persons_per_group),
            str(preference_count),
            preferences,
        ]

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout.strip()
            if output == "":
                messagebox.showinfo("Erfolg", "Programm erfolgreich ausgeführt.")
                return

            try:
                parsed = self.parse_program_output(output)
            except ValueError:
                messagebox.showinfo("Erfolg", output)
                return

            max_flow = parsed["max_flow"]
            assignments = parsed["assignments"]

            assigned_count = len(assignments)

            if max_flow == person_count:
                summary = (
                    "Es existiert eine vollständige Zuordnung.\n\n"
                    f"Zugeordnete Personen über Präferenzen: {max_flow} von {person_count}"
                )
            else:
                if assigned_count == person_count:
                    summary = (
                        "Nicht alle Präferenzen können perfekt berücksichtigt werden.\n\n"
                        f"Über reine Präferenzen zuordenbar: {max_flow} von {person_count}\n"
                        "Die möglichst beste vollständige Zuordnung ist die nachfolgende."
                    )
                else:
                    summary = (
                        "Es existiert insgesamt keine vollständige Zuordnung.\n\n"
                        f"Über reine Präferenzen zuordenbar: {max_flow} von {person_count}\n"
                        f"Tatsächlich zugeordnet: {assigned_count} von {person_count}"
                    )

            assignment_rows: list[tuple[str, str, bool]] = []
            for person_index in sorted(assignments):
                group_index = assignments[person_index]
                assignment_rows.append(
                    (
                        person_names[person_index],
                        group_names[group_index],
                        group_index not in preference_sets[person_index],
                    )
                )

            self.show_result_window(summary, assignment_rows)
        else:
            error_text = result.stderr.strip() or result.stdout.strip() or "Unbekannter Fehler."
            messagebox.showerror("Fehler beim Ausführen", error_text)

    def show_result_window(
        self, summary: str, assignment_rows: list[tuple[str, str, bool]]
    ) -> None:
        window = tk.Toplevel(self.root)
        window.title("Ergebnis")
        window.geometry("760x520")
        window.configure(bg="#f5f7fb")
        window.transient(self.root)

        container = ttk.Frame(window, padding=16)
        container.grid(row=0, column=0, sticky="nsew")
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        summary_label = ttk.Label(container, text=summary, justify="left", wraplength=700)
        summary_label.grid(row=0, column=0, sticky="w", pady=(0, 12))

        table_frame = ttk.Frame(container, style="Surface.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        tree = ttk.Treeview(table_frame, columns=("person", "group"), show="headings", height=12)
        tree.heading("person", text="Person")
        tree.heading("group", text="Gruppe")
        tree.column("person", width=280, anchor="w")
        tree.column("group", width=280, anchor="w")
        tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)
        tree.tag_configure("warning", foreground="#b42318")

        for person_name, group_name, is_fallback in assignment_rows:
            tag = "warning" if is_fallback else ""
            tree.insert("", "end", values=(person_name, group_name), tags=(tag,))

        explanation = ttk.Label(
            container,
            text="Rot markierte Personen wurden einer Gruppe zugeordnet, für die sie keine Präferenz abgegeben hatten.",
            justify="left",
            wraplength=700,
            style="Section.TLabel",
        )
        explanation.grid(row=2, column=0, sticky="w", pady=(12, 0))

        button_row = ttk.Frame(container)
        button_row.grid(row=3, column=0, sticky="e", pady=(12, 0))

        export_button = ttk.Button(
            button_row,
            text="Als Excel-Datei exportieren",
            command=lambda: self.export_assignment_excel(assignment_rows),
        )
        export_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        close_button = ttk.Button(button_row, text="Schließen", command=window.destroy, style="Accent.TButton")
        close_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def export_assignment_excel(self, assignment_rows: list[tuple[str, str, bool]]) -> None:
        target = filedialog.asksaveasfilename(
            parent=self.root,
            title="Zuordnung exportieren",
            defaultextension=".xlsx",
            filetypes=[("Excel-Arbeitsmappe", "*.xlsx"), ("Alle Dateien", "*.*")],
        )
        if not target:
            return

        rows = [("Person", "Gruppe")]
        rows.extend((person_name, group_name) for person_name, group_name, _is_fallback in assignment_rows)
        self.write_xlsx(Path(target), rows)
        messagebox.showinfo("Export", f"Zuordnung exportiert:\n{target}")

    def write_xlsx(self, target: Path, rows: list[tuple[str, str]]) -> None:
        sheet_rows: list[str] = []
        for row_index, (person_name, group_name) in enumerate(rows, start=1):
            sheet_rows.append(
                "<row r=\"{row}\">"
                "<c r=\"A{row}\" t=\"inlineStr\"><is><t>{person}</t></is></c>"
                "<c r=\"B{row}\" t=\"inlineStr\"><is><t>{group}</t></is></c>"
                "</row>".format(
                    row=row_index,
                    person=escape(person_name),
                    group=escape(group_name),
                )
            )

        sheet_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">"
            "<sheetData>"
            f"{''.join(sheet_rows)}"
            "</sheetData>"
            "</worksheet>"
        )

        workbook_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" "
            "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">"
            "<sheets><sheet name=\"Zuordnung\" sheetId=\"1\" r:id=\"rId1\"/></sheets>"
            "</workbook>"
        )

        workbook_rels_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
            "<Relationship Id=\"rId1\" "
            "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" "
            "Target=\"worksheets/sheet1.xml\"/>"
            "<Relationship Id=\"rId2\" "
            "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" "
            "Target=\"styles.xml\"/>"
            "</Relationships>"
        )

        root_rels_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
            "<Relationship Id=\"rId1\" "
            "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" "
            "Target=\"xl/workbook.xml\"/>"
            "</Relationships>"
        )

        content_types_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
            "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
            "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
            "<Override PartName=\"/xl/workbook.xml\" "
            "ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>"
            "<Override PartName=\"/xl/worksheets/sheet1.xml\" "
            "ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>"
            "<Override PartName=\"/xl/styles.xml\" "
            "ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml\"/>"
            "</Types>"
        )

        styles_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<styleSheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">"
            "<fonts count=\"1\"><font><sz val=\"11\"/><name val=\"Calibri\"/></font></fonts>"
            "<fills count=\"2\">"
            "<fill><patternFill patternType=\"none\"/></fill>"
            "<fill><patternFill patternType=\"gray125\"/></fill>"
            "</fills>"
            "<borders count=\"1\"><border><left/><right/><top/><bottom/><diagonal/></border></borders>"
            "<cellStyleXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\"/></cellStyleXfs>"
            "<cellXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\"/></cellXfs>"
            "<cellStyles count=\"1\"><cellStyle name=\"Normal\" xfId=\"0\" builtinId=\"0\"/></cellStyles>"
            "</styleSheet>"
        )

        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", content_types_xml)
            archive.writestr("_rels/.rels", root_rels_xml)
            archive.writestr("xl/workbook.xml", workbook_xml)
            archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
            archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
            archive.writestr("xl/styles.xml", styles_xml)

    def parse_program_output(self, output: str) -> dict[str, object]:
        max_flow: int | None = None
        assignments: dict[int, int] = {}

        for line in output.splitlines():
            if line.startswith("MAX_FLOW "):
                max_flow = int(line.split()[1])
            elif line.startswith("ASSIGNMENT "):
                _label, person, group = line.split()
                assignments[int(person)] = int(group)

        if max_flow is None:
            raise ValueError("MAX_FLOW fehlt")

        return {
            "max_flow": max_flow,
            "assignments": assignments,
        }


def main() -> None:
    root = tk.Tk()
    PrefmatchUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
