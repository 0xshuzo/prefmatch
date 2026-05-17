#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


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
        self.binary_var = tk.StringVar(value=str(self.find_binary()))

        self.person_name_vars: list[tk.StringVar] = []
        self.group_name_vars: list[tk.StringVar] = []
        self.preference_widgets: list[list[ttk.Combobox]] = []
        self.active_scroll_canvas: tk.Canvas | None = None

        self.configure_style()
        self.build_layout()
        self.bind_global_scroll()
        self.rebuild_forms()

    def configure_style(self) -> None:
        available_themes = set(self.style.theme_names())
        if sys.platform == "darwin" and "aqua" in available_themes:
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
        self.style.configure("TEntry", padding=8)
        self.style.configure("TCombobox", padding=6)
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

        config_frame = ttk.LabelFrame(self.root, text="Parameter", padding=16, style="Card.TLabelframe")
        config_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        config_frame.columnconfigure(1, weight=1)

        self.add_labeled_entry(config_frame, 0, "Personen", self.person_count_var)
        self.add_labeled_entry(config_frame, 1, "Gruppen", self.group_count_var)
        self.add_labeled_entry(config_frame, 2, "Personen pro Gruppe", self.persons_per_group_var)
        self.add_labeled_entry(config_frame, 3, "Präferenzen pro Person", self.preference_count_var)
        self.add_labeled_entry(config_frame, 4, "Binary", self.binary_var)

        rebuild_button = ttk.Button(
            config_frame,
            text="Formulare aktualisieren",
            command=self.rebuild_forms,
            style="Accent.TButton",
        )
        rebuild_button.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        content_frame = ttk.Frame(self.root, padding=(12, 6, 12, 6))
        content_frame.grid(row=1, column=0, sticky="nsew")
        content_frame.columnconfigure(0, weight=0, minsize=340)
        content_frame.columnconfigure(1, weight=1, minsize=520)
        content_frame.rowconfigure(0, weight=1)

        names_frame = ttk.LabelFrame(content_frame, text="Namen", padding=16, style="Card.TLabelframe")
        names_frame.grid(row=0, column=0, sticky="ns", padx=(0, 6))
        names_frame.columnconfigure(0, weight=1)
        names_frame.rowconfigure(0, weight=1)

        self.names_canvas = tk.Canvas(names_frame, highlightthickness=0, bg="#ffffff")
        self.names_canvas.grid(row=0, column=0, sticky="nsew")
        names_scrollbar = ttk.Scrollbar(names_frame, orient="vertical", command=self.names_canvas.yview)
        names_scrollbar.grid(row=0, column=1, sticky="ns")
        self.names_canvas.configure(yscrollcommand=names_scrollbar.set)

        self.names_container = ttk.Frame(self.names_canvas, style="Surface.TFrame")
        self.names_container.bind("<Configure>", self.update_names_scroll_region)
        self.names_canvas.bind("<Configure>", self.resize_names_canvas_window)
        self.names_canvas_window = self.names_canvas.create_window((0, 0), window=self.names_container, anchor="nw")
        self.bind_scroll_area(names_frame, self.names_canvas)

        preferences_frame = ttk.LabelFrame(content_frame, text="Präferenzen", padding=16, style="Card.TLabelframe")
        preferences_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        preferences_frame.columnconfigure(0, weight=1)
        preferences_frame.rowconfigure(0, weight=1)

        self.preferences_canvas = tk.Canvas(preferences_frame, highlightthickness=0, bg="#ffffff")
        self.preferences_canvas.grid(row=0, column=0, sticky="nsew")
        preferences_scrollbar = ttk.Scrollbar(preferences_frame, orient="vertical", command=self.preferences_canvas.yview)
        preferences_scrollbar.grid(row=0, column=1, sticky="ns")
        self.preferences_canvas.configure(yscrollcommand=preferences_scrollbar.set)

        self.preference_container = ttk.Frame(self.preferences_canvas, style="Surface.TFrame")
        self.preference_container.bind("<Configure>", self.update_preferences_scroll_region)
        self.preferences_canvas.bind("<Configure>", self.resize_preferences_canvas_window)
        self.preferences_canvas_window = self.preferences_canvas.create_window((0, 0), window=self.preference_container, anchor="nw")
        self.bind_scroll_area(preferences_frame, self.preferences_canvas)

        run_frame = ttk.Frame(self.root, padding=(12, 6, 12, 12))
        run_frame.grid(row=2, column=0, sticky="ew")
        run_frame.columnconfigure(0, weight=1)

        self.command_label = ttk.Label(run_frame, text="", wraplength=840)
        self.command_label.grid(row=0, column=0, sticky="w")

        run_button = ttk.Button(run_frame, text="C++-Programm ausführen", command=self.run_program, style="Accent.TButton")
        run_button.grid(row=0, column=1, sticky="e", padx=(12, 0))

    def add_labeled_entry(self, parent: ttk.Widget, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=2)

    def bind_scroll_area(self, widget: tk.Widget, canvas: tk.Canvas) -> None:
        widget.bind("<Enter>", lambda _event: self.set_active_scroll_canvas(canvas), add="+")
        widget.bind("<Leave>", lambda _event: self.clear_active_scroll_canvas(canvas), add="+")
        for child in widget.winfo_children():
            self.bind_scroll_area(child, canvas)

    def set_active_scroll_canvas(self, canvas: tk.Canvas) -> None:
        self.active_scroll_canvas = canvas

    def clear_active_scroll_canvas(self, canvas: tk.Canvas) -> None:
        if self.active_scroll_canvas is canvas:
            self.active_scroll_canvas = None

    def bind_global_scroll(self) -> None:
        self.root.bind_all("<MouseWheel>", self.on_mousewheel, add="+")
        self.root.bind_all("<Button-4>", self.on_mousewheel, add="+")
        self.root.bind_all("<Button-5>", self.on_mousewheel, add="+")

    def on_mousewheel(self, event: tk.Event) -> str | None:
        if self.active_scroll_canvas is None:
            return None

        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            raw_delta = getattr(event, "delta", 0)
            if raw_delta == 0:
                return None

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

        self.active_scroll_canvas.yview_scroll(delta, "units")
        return "break"

    def update_names_scroll_region(self, _event: tk.Event) -> None:
        self.names_canvas.configure(scrollregion=self.names_canvas.bbox("all"))

    def resize_names_canvas_window(self, event: tk.Event) -> None:
        self.names_canvas.itemconfigure(self.names_canvas_window, width=event.width)

    def update_preferences_scroll_region(self, _event: tk.Event) -> None:
        self.preferences_canvas.configure(scrollregion=self.preferences_canvas.bbox("all"))

    def resize_preferences_canvas_window(self, event: tk.Event) -> None:
        self.preferences_canvas.itemconfigure(self.preferences_canvas_window, width=event.width)

    def parse_positive_int(self, value: str, field_name: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} muss eine ganze Zahl sein.") from exc

        if parsed <= 0:
            raise ValueError(f"{field_name} muss größer als 0 sein.")

        return parsed

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
        names_person_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        names_person_frame.columnconfigure(1, weight=1)

        for person in range(person_count):
            ttk.Label(names_person_frame, text=f"Person {person}", style="Section.TLabel").grid(row=person, column=0, sticky="w", pady=4)
            default_name = old_person_names[person] if person < len(old_person_names) else f"Person {person + 1}"
            var = tk.StringVar(value=default_name)
            var.trace_add("write", self.on_names_changed)
            self.person_name_vars.append(var)
            ttk.Entry(names_person_frame, textvariable=var).grid(row=person, column=1, sticky="ew", pady=2)

        names_group_frame = ttk.LabelFrame(self.names_container, text="Gruppennamen", padding=10, style="Card.TLabelframe")
        names_group_frame.grid(row=1, column=0, sticky="ew")
        names_group_frame.columnconfigure(1, weight=1)

        for group in range(group_count):
            ttk.Label(names_group_frame, text=f"Gruppe {group}", style="Section.TLabel").grid(row=group, column=0, sticky="w", pady=4)
            default_name = old_group_names[group] if group < len(old_group_names) else f"Gruppe {group + 1}"
            var = tk.StringVar(value=default_name)
            var.trace_add("write", self.on_names_changed)
            self.group_name_vars.append(var)
            ttk.Entry(names_group_frame, textvariable=var).grid(row=group, column=1, sticky="ew", pady=2)

        self.bind_scroll_area(names_person_frame, self.names_canvas)
        self.bind_scroll_area(names_group_frame, self.names_canvas)
        self.rebuild_preferences(preference_count)

    def on_names_changed(self, *_args: object) -> None:
        try:
            _person_count, _group_count, _persons_per_group, preference_count = self.read_dimensions()
        except ValueError:
            return
        self.rebuild_preferences(preference_count)

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

    def rebuild_preferences(self, preference_count: int) -> None:
        old_values = [[combo.get() for combo in row] for row in self.preference_widgets]

        for child in self.preference_container.winfo_children():
            child.destroy()

        self.preference_widgets = []

        try:
            person_names = self.collect_person_names()
            group_names = self.collect_group_names()
        except ValueError:
            self.update_command_preview()
            return

        group_display_values = [f"{index}: {name}" for index, name in enumerate(group_names)]

        self.preference_container.columnconfigure(0, weight=1, minsize=180)
        ttk.Label(self.preference_container, text="Person", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 8)
        )
        for pref in range(preference_count):
            self.preference_container.columnconfigure(pref + 1, weight=0, minsize=210)
            ttk.Label(self.preference_container, text=f"Präferenz {pref + 1}", style="Header.TLabel").grid(
                row=0, column=pref + 1, sticky="w", padx=6, pady=(0, 8)
            )

        for person, person_name in enumerate(person_names):
            ttk.Label(self.preference_container, text=person_name, style="Surface.TLabel").grid(
                row=person + 1, column=0, sticky="w", padx=(0, 10), pady=4
            )

            row_widgets: list[ttk.Combobox] = []
            for pref in range(preference_count):
                combo = ttk.Combobox(
                    self.preference_container,
                    values=group_display_values,
                    state="readonly",
                    width=26,
                )
                combo.grid(row=person + 1, column=pref + 1, sticky="ew", padx=6, pady=4)
                if person < len(old_values) and pref < len(old_values[person]) and old_values[person][pref] in group_display_values:
                    combo.set(old_values[person][pref])
                elif pref < len(group_display_values):
                    combo.set(group_display_values[pref])
                row_widgets.append(combo)

            self.preference_widgets.append(row_widgets)

        self.bind_scroll_area(self.preference_container, self.preferences_canvas)
        self.update_command_preview()

    def encode_preferences(self) -> str:
        group_names = self.collect_group_names()
        group_name_to_id = {name: index for index, name in enumerate(group_names)}
        encoded_rows: list[str] = []

        for person, row_widgets in enumerate(self.preference_widgets):
            seen: set[int] = set()
            entries: list[str] = []

            for pref, combo in enumerate(row_widgets):
                value = combo.get().strip()
                if not value:
                    raise ValueError(f"Präferenz {pref + 1} für {self.person_name_vars[person].get().strip()} ist leer.")

                _sep, _space, group_name = value.partition(": ")
                if not group_name:
                    raise ValueError(f"Ungültiger Gruppenwert in {self.person_name_vars[person].get().strip()}: {value}")

                group_id = group_name_to_id.get(group_name)
                if group_id is None:
                    raise ValueError(f"Unbekannte Gruppe in Präferenz von {self.person_name_vars[person].get().strip()}: {group_name}")
                if group_id in seen:
                    raise ValueError(f"{self.person_name_vars[person].get().strip()} enthält die Gruppe {group_name} doppelt.")

                seen.add(group_id)
                entries.append(str(group_id))

            encoded_rows.append(",".join(entries))

        return ";".join(encoded_rows)

    def find_binary(self) -> Path:
        project_root = Path(__file__).resolve().parent
        candidates = [
            project_root / "build" / "debug" / "prefmatch",
            project_root / "build" / "release" / "prefmatch",
            project_root / "build" / "prefmatch",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return candidates[0]

    def update_command_preview(self) -> None:
        try:
            person_count, group_count, persons_per_group, preference_count = self.read_dimensions()
            preferences = self.encode_preferences()
            command = (
                f"{self.binary_var.get()} {person_count} {group_count} "
                f"{persons_per_group} {preference_count} \"{preferences}\""
            )
            self.command_label.configure(text=command)
        except ValueError:
            self.command_label.configure(text="")

    def run_program(self) -> None:
        try:
            person_count, group_count, persons_per_group, preference_count = self.read_dimensions()
            self.collect_person_names()
            self.collect_group_names()
            preferences = self.encode_preferences()
        except ValueError as exc:
            messagebox.showerror("Ungültige Eingabe", str(exc))
            return

        binary = Path(self.binary_var.get())
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
                max_flow = int(output)
            except ValueError:
                messagebox.showinfo("Erfolg", output)
                return

            if max_flow == person_count:
                message = (
                    "Es existiert eine vollständige Zuordnung.\n\n"
                    f"Zugeordnete Personen: {max_flow} von {person_count}"
                )
            else:
                message = (
                    "Es existiert keine vollständige Zuordnung.\n\n"
                    f"Zugeordnete Personen: {max_flow} von {person_count}"
                )

            messagebox.showinfo("Ergebnis", message)
        else:
            error_text = result.stderr.strip() or result.stdout.strip() or "Unbekannter Fehler."
            messagebox.showerror("Fehler beim Ausführen", error_text)


def main() -> None:
    root = tk.Tk()
    app = PrefmatchUI(root)
    for variable in (
        app.person_count_var,
        app.group_count_var,
        app.persons_per_group_var,
        app.preference_count_var,
        app.binary_var,
    ):
        variable.trace_add("write", lambda *_args: app.update_command_preview())
    root.mainloop()


if __name__ == "__main__":
    main()
