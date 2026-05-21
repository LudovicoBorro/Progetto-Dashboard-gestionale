import flet as ft
from datetime import datetime
from UI.views.base_view import BaseView
from UI.widgets.error_alert import ErrorAlert

class ProjectCreationView(BaseView):
    def __init__(self, page: ft.Page):
        super().__init__(route="/new_project")
        self._page_ref = page
        
        # State variables
        self.selected_start_date = None
        self.selected_end_date = None
        self.resources_list = []
        
        # Color palette options (premium, curated colors)
        self.PREMIUM_COLORS = [
            ("#4F46E5", "Indigo"),
            ("#0D9488", "Teal"),
            ("#10B981", "Emerald"),
            ("#F59E0B", "Amber"),
            ("#EF4444", "Red"),
            ("#EC4899", "Pink"),
            ("#8B5CF6", "Violet"),
            ("#06B6D4", "Cyan"),
            ("#6366F1", "Periwinkle"),
            ("#84CC16", "Lime"),
            ("#F97316", "Orange"),
            ("#64748B", "Slate")
        ]
        self.selected_color = self.PREMIUM_COLORS[0][0] # Default to Indigo
        
        # Initialize Pickers
        self.start_date_picker = ft.DatePicker(
            on_change=self.on_start_date_change,
            first_date=datetime(1900, 1, 1),
            last_date=datetime(2200, 12, 31),
            current_date=datetime.now(),
            cancel_text="Annulla",
            confirm_text="Conferma",
            locale=ft.Locale(country_code='IT', language_code='it'),
            error_format_text='Formato data non valido. Inserisci una data nel formato gg/mm/aaaa.',
            error_invalid_text='Data non valida. Inserisci una data compresa tra il 01/01/1900 e il 31/12/2200.',
        )
        self.end_date_picker = ft.DatePicker(
            on_change=self.on_end_date_change,
            first_date=datetime(1900, 1, 1),
            last_date=datetime(2200, 12, 31),
            current_date=datetime.now(),
            cancel_text="Annulla",
            confirm_text="Conferma",
            locale=ft.Locale(country_code='IT', language_code='it'),
            error_format_text='Formato data non valido. Inserisci una data nel formato gg/mm/aaaa.',
            error_invalid_text='Data non valida. Inserisci una data compresa tra il 01/01/1900 e il 31/12/2200.',
        )

    def on_start_date_change(self, e):
        if e.control.value:
            self.selected_start_date = e.control.value
            self.btn_start_date.content = f"Inizio: {self.selected_start_date.strftime('%d/%m/%Y')}"
            self.btn_start_date.style = ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_GREY_800,
                color=ft.Colors.WHITE,
            )
            self.update()

    def on_end_date_change(self, e):
        if e.control.value:
            self.selected_end_date = e.control.value
            self.btn_end_date.content = f"Fine: {self.selected_end_date.strftime('%d/%m/%Y')}"
            self.btn_end_date.style = ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_GREY_800,
                color=ft.Colors.WHITE,
            )
            self.update()

    def select_palette_color(self, color_hex: str):
        self.selected_color = color_hex
        self.palette_container.content = self._build_color_palette()
        self.palette_container.update()

    def _build_color_palette(self):
        palette_controls = []
        for color_hex, name in self.PREMIUM_COLORS:
            is_selected = self.selected_color == color_hex
            palette_controls.append(
                ft.Container(
                    width=30,
                    height=30,
                    shape=ft.BoxShape.CIRCLE,
                    bgcolor=color_hex,
                    tooltip=name,
                    border=ft.Border.all(3, ft.Colors.WHITE) if is_selected else ft.Border.all(1, ft.Colors.WHITE24),
                    on_click=lambda e, col=color_hex: self.select_palette_color(col),
                    animate=ft.Animation(150, ft.AnimationCurve.DECELERATE),
                    margin=ft.Margin(3, 3, 3, 3)
                )
            )
        return ft.Row(
            controls=palette_controls,
            spacing=5,
            wrap=True
        )

    def add_resource_to_list(self, e):
        name = self.res_name_input.value.strip()
        cap_min_str = self.res_cap_min_input.value.strip()
        cap_max_str = self.res_cap_max_input.value.strip()
        
        # Validation
        if not name:
            self.res_name_input.error_text = "Il nome della risorsa è richiesto"
            self.res_name_input.update()
            return
        else:
            self.res_name_input.error_text = None
            self.res_name_input.update()
            
        try:
            cap_min = int(cap_min_str)
            if cap_min < 0:
                raise ValueError
            self.res_cap_min_input.error_text = None
            self.res_cap_min_input.update()
        except ValueError:
            self.res_cap_min_input.error_text = "Numero intero >= 0 richiesto"
            self.res_cap_min_input.update()
            return
            
        cap_max = None
        if cap_max_str:
            try:
                cap_max = int(cap_max_str)
                if cap_max < cap_min:
                    self.res_cap_max_input.error_text = "Deve essere >= min"
                    self.res_cap_max_input.update()
                    return
                self.res_cap_max_input.error_text = None
                self.res_cap_max_input.update()
            except ValueError:
                self.res_cap_max_input.error_text = "Intero richiesto"
                self.res_cap_max_input.update()
                return

        # Check for duplicates
        if any(r["name"].lower() == name.lower() for r in self.resources_list):
            self.res_name_input.error_text = "Esiste già una risorsa con questo nome"
            self.res_name_input.update()
            return

        # Add to list
        self.resources_list.append({
            "name": name,
            "capacity_min": cap_min,
            "capacity_max": cap_max,
            "color_hex": self.selected_color
        })
        
        # Reset inputs
        self.res_name_input.value = ""
        self.res_cap_min_input.value = "1"
        self.res_cap_max_input.value = ""
        
        self.res_name_input.update()
        self.res_cap_min_input.update()
        self.res_cap_max_input.update()
        
        # Rebuild resources list UI
        self.resources_list_container.content = self._build_resources_list_ui()
        self.resources_list_container.update()

    def remove_resource_from_list(self, resource_dict):
        if resource_dict in self.resources_list:
            self.resources_list.remove(resource_dict)
            self.resources_list_container.content = self._build_resources_list_ui()
            self.resources_list_container.update()

    def _build_resources_list_ui(self):
        if not self.resources_list:
            return ft.Container(
                alignment=ft.MainAxisAlignment.CENTER,
                padding=20,
                content=ft.Text(
                    "Nessuna risorsa aggiunta. Aggiungi almeno una risorsa.",
                    color=ft.Colors.WHITE38,
                    italic=True,
                    size=13
                )
            )

        controls = []
        for r in self.resources_list:
            cap_str = f"Cap: {r['capacity_min']}"
            if r['capacity_max'] is not None:
                cap_str += f" - {r['capacity_max']}"
                
            controls.append(
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
                    border=ft.Border.all(1, ft.Colors.WHITE10),
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=10,
                                controls=[
                                    ft.Container(
                                        width=12,
                                        height=12,
                                        shape=ft.BoxShape.CIRCLE,
                                        bgcolor=r["color_hex"]
                                    ),
                                    ft.Text(r["name"], weight=ft.FontWeight.W_600, size=14),
                                    ft.Text(f"({cap_str})", color=ft.Colors.WHITE50, size=12)
                                ]
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color=ft.Colors.RED_400,
                                icon_size=18,
                                tooltip="Elimina risorsa",
                                on_click=lambda e, res=r: self.remove_resource_from_list(res)
                            )
                        ]
                    )
                )
            )
        return ft.Column(controls=controls, spacing=8)

    def submit_project(self, e):
        name = self.name_input.value.strip()
        description = self.desc_input.value.strip()
        initial_budget = self.budget_input.value.strip()
        
        self.controller.save_project(
            name=name,
            description=description,
            start_date=self.selected_start_date,
            end_date=self.selected_end_date,
            initial_budget_str=initial_budget,
            resources=self.resources_list
        )

    def build_view(self):
        if not self.controller:
            return

        p = self._page_ref
        if p:
            if self.start_date_picker not in p.overlay:
                p.overlay.append(self.start_date_picker)
            if self.end_date_picker not in p.overlay:
                p.overlay.append(self.end_date_picker)

        # Header Row
        header = ft.Container(
            padding=20,
            bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
            border_radius=12,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        spacing=5,
                        controls=[
                            ft.Text("Nuovo Progetto", size=24, weight=ft.FontWeight.BOLD),
                            ft.Text("Crea un nuovo progetto e configura le sue risorse", size=13, color=ft.Colors.WHITE60)
                        ]
                    ),
                    ft.TextButton(
                        "Annulla e Torna",
                        icon=ft.Icons.ARROW_BACK,
                        on_click=self.controller.go_dashboard
                    )
                ]
            )
        )

        # Column 1: Project details card
        self.name_input = ft.TextField(
            label="Nome Progetto *",
            border_radius=8,
            cursor_color=ft.Colors.BLUE_400,
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_400,
        )
        self.desc_input = ft.TextField(
            label="Descrizione (Opzionale)",
            multiline=True,
            min_lines=3,
            max_lines=4,
            border_radius=8,
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_400,
        )
        self.budget_input = ft.TextField(
            label="Budget Iniziale (€) *",
            value="0.0",
            border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_400,
        )
        
        self.btn_start_date = ft.OutlinedButton(
            "Seleziona Data Inizio *",
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=lambda _: self._page_ref.show_dialog(self.start_date_picker),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding.all(15)
            )
        )
        
        self.btn_end_date = ft.OutlinedButton(
            "Seleziona Data Fine *",
            icon=ft.Icons.FLAG,
            on_click=lambda _: self._page_ref.show_dialog(self.end_date_picker),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding.all(15)
            )
        )

        project_details_card = ft.Container(
            bgcolor=ft.Colors.with_opacity(0.02, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.WHITE10),
            border_radius=12,
            padding=24,
            expand=True,
            content=ft.Column(
                spacing=20,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.ASSIGNMENT_OUTLINED, color=ft.Colors.BLUE_400),
                            ft.Text("Informazioni Progetto", size=18, weight=ft.FontWeight.BOLD),
                        ]
                    ),
                    ft.Divider(height=1, color=ft.Colors.WHITE10),
                    self.name_input,
                    self.desc_input,
                    ft.Text("Date del Progetto *", size=14, color=ft.Colors.WHITE70, weight=ft.FontWeight.W_600),
                    ft.Row(
                        controls=[
                            self.btn_start_date,
                            self.btn_end_date
                        ],
                        spacing=15
                    ),
                    self.budget_input,
                    ft.Container(height=10),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.ElevatedButton(
                                "Salva Progetto",
                                icon=ft.Icons.SAVE,
                                bgcolor=ft.Colors.GREEN_700,
                                color=ft.Colors.WHITE,
                                height=48,
                                width=220,
                                on_click=self.submit_project,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8)
                                )
                            )
                        ]
                    )
                ]
            )
        )

        # Column 2: Resources card
        self.res_name_input = ft.TextField(
            label="Nome Risorsa *",
            border_radius=8,
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_400,
        )
        self.res_cap_min_input = ft.TextField(
            label="Capacità Minima *",
            value="1",
            border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_400,
        )
        self.res_cap_max_input = ft.TextField(
            label="Capacità Massima (Opzionale)",
            border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_400,
        )
        
        self.palette_container = ft.Container(
            content=self._build_color_palette()
        )
        
        self.resources_list_container = ft.Container(
            content=self._build_resources_list_ui(),
            height=120,
            border_radius=8,
        )

        resources_card = ft.Container(
            bgcolor=ft.Colors.with_opacity(0.02, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.WHITE10),
            border_radius=12,
            padding=24,
            expand=True,
            content=ft.Column(
                spacing=15,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PEOPLE_OUTLINE, color=ft.Colors.BLUE_400),
                            ft.Text("Risorse associate", size=18, weight=ft.FontWeight.BOLD),
                        ]
                    ),
                    ft.Divider(height=1, color=ft.Colors.WHITE10),
                    
                    # Add Resource Sub-section
                    ft.Text("Nuova Risorsa", size=14, color=ft.Colors.WHITE70, weight=ft.FontWeight.W_600),
                    self.res_name_input,
                    ft.Row(
                        controls=[
                            self.res_cap_min_input,
                            self.res_cap_max_input
                        ],
                        spacing=10
                    ),
                    ft.Text("Seleziona Colore Risorsa:", size=13, color=ft.Colors.WHITE60),
                    self.palette_container,
                    
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.ElevatedButton(
                                "Aggiungi Risorsa",
                                icon=ft.Icons.ADD,
                                bgcolor=ft.Colors.BLUE_800,
                                color=ft.Colors.WHITE,
                                on_click=self.add_resource_to_list,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8)
                                )
                            )
                        ]
                    ),
                    ft.Divider(height=1, color=ft.Colors.WHITE10),
                    
                    # Resources List Sub-section
                    ft.Text("Elenco Risorse Aggiunte", size=14, color=ft.Colors.WHITE70, weight=ft.FontWeight.W_600),
                    self.resources_list_container
                ]
            )
        )

        # Responsive layout for form columns
        form_layout = ft.Row(
            spacing=20,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                project_details_card,
                resources_card
            ]
        )

        # Set main layout
        self.set_content(
            controls=[
                header,
                form_layout
            ]
        )
