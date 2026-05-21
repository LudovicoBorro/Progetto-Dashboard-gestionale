from UI.controllers.base_controller import BaseController
from UI.services.project_service import ProjectService
from UI.widgets.error_alert import ErrorAlert
import flet as ft
from datetime import datetime

class ProjectCreationController(BaseController):
    def __init__(self, view):
        super().__init__(view)

    def save_project(self, name: str, description: str, start_date: datetime, end_date: datetime,
                     initial_budget_str: str, resources: list[dict]):
        """
        Valida i dati del progetto e delle risorse, poi li salva nel database.
        """
        page = self.view.page or self.view._page_ref

        # 1. Validazione Nome Progetto
        if not name or not name.strip():
            self._show_error("Il nome del progetto è obbligatorio.")
            return

        # 2. Validazione Date
        if not start_date:
            self._show_error("La data di inizio progetto è obbligatoria.")
            return

        if not end_date:
            self._show_error("La data di fine progetto è obbligatoria.")
            return

        if start_date >= end_date:
            self._show_error("La data di inizio deve essere antecedente alla data di fine.")
            return

        # 3. Validazione Budget
        try:
            initial_budget = float(initial_budget_str) if initial_budget_str else 0.0
            if initial_budget < 0:
                raise ValueError()
        except ValueError:
            self._show_error("Il budget iniziale deve essere un numero reale non negativo.")
            return

        # 4. Validazione Risorse
        if not resources:
            self._show_error("Devi inserire almeno una risorsa per creare il progetto.")
            return

        for idx, res in enumerate(resources):
            res_name = res.get("name", "").strip()
            if not res_name:
                self._show_error(f"La risorsa al punto {idx+1} deve avere un nome.")
                return
            
            try:
                cap_min = int(res.get("capacity_min", 0))
                if cap_min < 0:
                    raise ValueError()
            except ValueError:
                self._show_error(f"La capacità minima per la risorsa '{res_name}' deve essere un numero intero non negativo.")
                return

            cap_max_val = res.get("capacity_max")
            if cap_max_val is not None:
                try:
                    cap_max = int(cap_max_val)
                    if cap_max < cap_min:
                        self._show_error(f"La capacità massima per la risorsa '{res_name}' non può essere inferiore alla minima ({cap_min}).")
                        return
                except ValueError:
                    self._show_error(f"La capacità massima per la risorsa '{res_name}' deve essere un numero intero valido.")
                    return

        # 5. Salvataggio
        try:
            # Creazione del progetto nel db tramite il service
            new_project = ProjectService.create_project(
                name=name.strip(),
                description=description.strip() if description else None,
                start_date=start_date,
                end_date=end_date,
                initial_budget=initial_budget,
                resources=resources
            )

            # Successo: snackbar e navigazione
            self._show_snackbar("Progetto creato con successo!")
            
            # Navighiamo alla pagina dei dettagli per consentire l'importazione excel
            page.go(f"/project_details?id={new_project.id}")

        except Exception as ex:
            import traceback
            traceback.print_exc()
            self._show_error(f"Errore durante la creazione del progetto: {ex}")

    def _show_error(self, message: str):
        page = self.view.page or self.view._page_ref
        if not page:
            print(f"[ERRORE] {message}")
            return

        def close_dialog(e):
            err_alert.open = False
            if hasattr(page, 'close'):
                page.close(err_alert)
            else:
                page.update()

        err_alert = ErrorAlert(
            error_message=message,
            title="Errore di Validazione",
            actions=[
                ft.TextButton("OK", on_click=close_dialog)
            ]
        )

        if hasattr(page, 'open'):
            page.open(err_alert)
        else:
            err_alert.open = True
            if err_alert not in page.overlay:
                page.overlay.append(err_alert)
            page.update()

    def _show_snackbar(self, message: str):
        page = self.view.page or self.view._page_ref
        if page:
            page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=ft.Colors.GREEN_700)
            page.snack_bar.open = True
            page.update()
        else:
            print(f"[Snackbar] {message}")
