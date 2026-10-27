"""English Tkinter interface for converting DXF and KML files."""

from __future__ import annotations

import sys
import threading
import tkinter as tk
import xml.etree.ElementTree as ET
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ezdxf import DXFError
from pyproj.exceptions import ProjError

from dxf2kml import convert_dxf_to_kml, convert_kml_to_dxf

CRS_OPTIONS = {"WGS 84 Geographic (EPSG:4326)": "EPSG:4326"}
CRS_OPTIONS.update(
    {
        label: f"EPSG:{code}"
        for zone in range(1, 61)
        for label, code in (
            (f"UTM Zone {zone} North (EPSG:{32600 + zone})", 32600 + zone),
            (f"UTM Zone {zone} South (EPSG:{32700 + zone})", 32700 + zone),
        )
    }
)

BACKGROUND = "#F2F5F9"
CARD = "#FFFFFF"
NAVY = "#132D46"
TEXT = "#243B53"
MUTED = "#627D98"
ACCENT = "#087E8B"


class ConverterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("DXF to KML Converter")
        root.configure(background=BACKGROUND)
        root.resizable(False, False)
        icon_path = Path(
            getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
        ) / "app.ico"
        if icon_path.is_file():
            root.iconbitmap(default=str(icon_path))

        self.direction = tk.StringVar(value="DXF to KML")
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.crs = tk.StringVar(value="")
        self.status = tk.StringVar(value="Choose files and a coordinate system to begin.")

        self._configure_styles()
        self._build_ui()
        self._update_direction()
        self._center_window()

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background=BACKGROUND)
        style.configure("Card.TFrame", background=CARD)
        style.configure(
            "Title.TLabel",
            background=NAVY,
            foreground="#FFFFFF",
            font=("Segoe UI", 19, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=NAVY,
            foreground="#D9E7F2",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Section.TLabel",
            background=CARD,
            foreground=TEXT,
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "Field.TLabel",
            background=CARD,
            foreground=TEXT,
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Hint.TLabel",
            background=CARD,
            foreground=MUTED,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Status.TLabel",
            background=CARD,
            foreground=ACCENT,
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Footer.TLabel",
            background=BACKGROUND,
            foreground=MUTED,
            font=("Segoe UI", 9),
        )
        style.configure(
            "TCombobox",
            padding=8,
            fieldbackground="#FFFFFF",
            background="#FFFFFF",
            foreground=TEXT,
            arrowcolor=ACCENT,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#FFFFFF")],
            foreground=[("readonly", TEXT)],
        )
        style.configure(
            "Browse.TButton",
            padding=(12, 8),
            background="#E7F2F4",
            foreground=ACCENT,
            font=("Segoe UI", 9, "bold"),
            borderwidth=0,
        )
        style.map(
            "Browse.TButton",
            background=[("active", "#D1E8EB"), ("disabled", "#E8EDF2")],
        )
        style.configure(
            "Convert.TButton",
            padding=(12, 11),
            background=ACCENT,
            foreground="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
        )
        style.map(
            "Convert.TButton",
            background=[("active", "#066773"), ("disabled", "#9BBCC0")],
            foreground=[("disabled", "#F5F7FA")],
        )

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, style="App.TFrame", padding=(24, 20, 24, 12))
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)

        header = tk.Frame(outer, background=NAVY, padx=22, pady=20)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(1, weight=1)

        self.avatar = tk.Canvas(
            header,
            width=72,
            height=72,
            background=NAVY,
            highlightthickness=0,
        )
        self.avatar.grid(row=0, column=0, rowspan=2, padx=(0, 18))
        self._draw_user_avatar()

        ttk.Label(
            header,
            text="DXF  ⇄  KML CONVERTER",
            style="Title.TLabel",
            anchor="w",
        ).grid(row=0, column=1, sticky="sw")
        ttk.Label(
            header,
            text="Convert CAD drawings and map data with accurate coordinates.",
            style="Subtitle.TLabel",
            anchor="w",
        ).grid(row=1, column=1, sticky="nw", pady=(4, 0))

        card = ttk.Frame(outer, style="Card.TFrame", padding=(22, 20, 22, 20))
        card.grid(row=1, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        ttk.Label(
            card, text="Conversion settings", style="Section.TLabel", anchor="w"
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))

        self._field_label(card, "Direction", 1)
        self.direction_box = ttk.Combobox(
            card,
            textvariable=self.direction,
            values=("DXF to KML", "KML to DXF"),
            state="readonly",
            justify="left",
        )
        self.direction_box.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 13))
        self.direction_box.bind("<<ComboboxSelected>>", self._update_direction)

        self._field_label(card, "Input file", 3)
        self.input_entry = ttk.Entry(card, textvariable=self.input_path)
        self.input_entry.grid(row=4, column=0, sticky="ew", pady=(5, 13), padx=(0, 10))
        self.input_button = ttk.Button(
            card, text="Browse...", style="Browse.TButton", command=self._browse_input
        )
        self.input_button.grid(row=4, column=1, sticky="ew", pady=(5, 13))

        self._field_label(card, "Output file", 5)
        self.output_entry = ttk.Entry(card, textvariable=self.output_path)
        self.output_entry.grid(row=6, column=0, sticky="ew", pady=(5, 13), padx=(0, 10))
        self.output_button = ttk.Button(
            card,
            text="Save as...",
            style="Browse.TButton",
            command=self._browse_output,
        )
        self.output_button.grid(row=6, column=1, sticky="ew", pady=(5, 13))

        self.crs_label = ttk.Label(card, style="Field.TLabel", anchor="w")
        self.crs_label.grid(row=7, column=0, columnspan=2, sticky="w")
        self.crs_box = ttk.Combobox(
            card,
            textvariable=self.crs,
            values=tuple(CRS_OPTIONS),
            state="readonly",
            height=15,
            justify="left",
        )
        self.crs_box.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(5, 4))
        ttk.Label(
            card,
            text="For UTM, select the zone and hemisphere used by your drawing.",
            style="Hint.TLabel",
            anchor="w",
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(0, 16))

        self.convert_button = ttk.Button(
            card,
            text="Convert file",
            style="Convert.TButton",
            command=self._start_conversion,
        )
        self.convert_button.grid(row=10, column=0, columnspan=2, sticky="ew")
        ttk.Label(
            card, textvariable=self.status, style="Status.TLabel", anchor="w"
        ).grid(row=11, column=0, columnspan=2, sticky="w", pady=(12, 0))

        ttk.Label(
            outer,
            text="Developer: K1.Adili",
            style="Footer.TLabel",
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(12, 0))

    @staticmethod
    def _field_label(parent: ttk.Frame, text: str, row: int) -> None:
        ttk.Label(parent, text=text, style="Field.TLabel", anchor="w").grid(
            row=row, column=0, columnspan=2, sticky="w"
        )

    def _draw_user_avatar(self) -> None:
        self.avatar.create_oval(
            2, 2, 70, 70, fill="#E4F4F5", outline="#76C7CD", width=2
        )
        self.avatar.create_polygon(
            15, 23, 30, 18, 42, 23, 57, 18, 57, 48, 42, 53, 30, 48, 15, 53,
            fill="#FFFFFF",
            outline=ACCENT,
            width=2,
            joinstyle="round",
        )
        self.avatar.create_line(30, 18, 30, 48, fill=ACCENT, width=2)
        self.avatar.create_line(42, 23, 42, 53, fill=ACCENT, width=2)
        self.avatar.create_line(18, 43, 26, 36, 34, 40, 45, 29, fill="#F2A65A", width=2)
        self.avatar.create_oval(42, 26, 48, 32, fill="#F2A65A", outline="")
        self.avatar.create_arc(
            16, 49, 56, 70, start=205, extent=130, style="arc",
            outline="#D9E7F2", width=2,
        )
        self.avatar.create_arc(
            16, 49, 56, 70, start=25, extent=130, style="arc",
            outline="#D9E7F2", width=2,
        )

    def _center_window(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        x = (self.root.winfo_screenwidth() - width) // 2
        y = (self.root.winfo_screenheight() - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _extensions(self) -> tuple[str, str]:
        if self.direction.get() == "DXF to KML":
            return ".dxf", ".kml"
        return ".kml", ".dxf"

    def _update_direction(self, _event: tk.Event | None = None) -> None:
        input_extension, output_extension = self._extensions()
        self.input_button.configure(text=f"Browse {input_extension[1:].upper()}...")
        self.output_button.configure(text=f"Save {output_extension[1:].upper()} as...")
        self.crs_label.configure(
            text=(
                "Source coordinate system"
                if self.direction.get() == "DXF to KML"
                else "Output coordinate system"
            )
        )
        self.status.set("Choose files and a coordinate system to begin.")

    def _browse_input(self) -> None:
        input_extension, _ = self._extensions()
        selected = filedialog.askopenfilename(
            title="Select input file",
            filetypes=[
                (f"{input_extension[1:].upper()} files", f"*{input_extension}"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self.input_path.set(selected)
            source = Path(selected)
            output_extension = self._extensions()[1]
            self.output_path.set(str(source.with_suffix(output_extension)))

    def _browse_output(self) -> None:
        _, output_extension = self._extensions()
        selected = filedialog.asksaveasfilename(
            title="Choose output file",
            defaultextension=output_extension,
            initialfile=f"converted{output_extension}",
            filetypes=[
                (f"{output_extension[1:].upper()} files", f"*{output_extension}"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self.output_path.set(selected)

    def _start_conversion(self) -> None:
        source = Path(self.input_path.get().strip())
        destination = Path(self.output_path.get().strip())
        crs = CRS_OPTIONS.get(self.crs.get(), "")

        if not source.is_file():
            messagebox.showerror("Error", "Please select a valid input file.")
            return
        if not destination.name:
            messagebox.showerror("Error", "Please specify an output file.")
            return
        if source.resolve() == destination.resolve():
            messagebox.showerror("Error", "The output file must be different from the input file.")
            return
        if not crs:
            messagebox.showerror("Error", "Please select a coordinate system.")
            return
        if not destination.parent.is_dir():
            messagebox.showerror("Error", "The output folder does not exist.")
            return
        if destination.exists() and not messagebox.askyesno(
            "Confirm overwrite",
            f"The output file already exists. Replace it?\n{destination}",
        ):
            return

        self.convert_button.configure(state="disabled")
        self.status.set("Converting...")
        threading.Thread(
            target=self._convert_in_background,
            args=(source, destination, crs, self.direction.get()),
            daemon=True,
        ).start()

    def _convert_in_background(
        self, source: Path, destination: Path, crs: str, direction: str
    ) -> None:
        try:
            if direction == "DXF to KML":
                count = convert_dxf_to_kml(source, destination, crs)
            else:
                count = convert_kml_to_dxf(source, destination, crs)
        except (OSError, ValueError, DXFError, ET.ParseError, ProjError) as error:
            self.root.after(0, self._show_error, str(error))
            return
        self.root.after(0, self._show_success, count, destination)

    def _show_error(self, error: str) -> None:
        self.convert_button.configure(state="normal")
        self.status.set("Conversion failed.")
        messagebox.showerror("Conversion error", error)

    def _show_success(self, count: int, destination: Path) -> None:
        self.convert_button.configure(state="normal")
        self.status.set(f"Conversion complete — {count} geometries saved.")
        messagebox.showinfo(
            "Conversion complete",
            f"{count} geometries were saved to:\n{destination}",
        )


def main() -> None:
    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
