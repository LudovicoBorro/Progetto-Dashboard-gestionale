import flet as ft

class ErrorAlert(ft.AlertDialog):
    def __init__(self, error_message: str, title: str, actions: list[ft.TextButton]):
        """
        Pop-up customizzato ereditato da AlertDialog.
        
        :param error_message: Messaggio da mostrare.
        :param title: Titolo del pop-up.
        :param actions: Lista di TextButton da mostrare come azioni.
        """ 
        super().__init__(
            title=ft.Text(title),
            content=ft.Text(error_message),
            actions=[
                action for action in actions
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )