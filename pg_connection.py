import sys
import psycopg2
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QMessageBox, QLabel, QLineEdit
from PyQt5.QtCore import QCoreApplication
# Classe per la finestra principale dell'applicazione
class Postgresconnection(QDialog):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # Creazione dei widget per i parametri di connessione
        self.dbname_label = QLabel("Database:")
        self.dbname_input = QLineEdit()
        self.port_label = QLabel("Port:")
        self.port = QLineEdit()
        self.user_label = QLabel("User:")
        self.user_input = QLineEdit()
        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.host_label = QLabel("Host:")
        self.host_input = QLineEdit()

        # Creazione dei widget per la visualizzazione dei dati
        self.button = QPushButton("Connect")
        self.button.clicked.connect(self.get_params)

        # Layout orizzontale per i widget dei parametri di connessione
        parameters_layout = QHBoxLayout()
        parameters_layout.addWidget(self.dbname_label)
        parameters_layout.addWidget(self.dbname_input)
        parameters_layout.addWidget(self.port_label)
        parameters_layout.addWidget(self.port)
        parameters_layout.addWidget(self.user_label)
        parameters_layout.addWidget(self.user_input)
        parameters_layout.addWidget(self.password_label)
        parameters_layout.addWidget(self.password_input)
        parameters_layout.addWidget(self.host_label)
        parameters_layout.addWidget(self.host_input)

        # Layout verticale per i widget della finestra principale
        main_layout = QVBoxLayout()
        main_layout.addLayout(parameters_layout)
        main_layout.addWidget(self.button)

        self.setLayout(main_layout)
        self.setWindowTitle("Interface for PostgreSQL")

    # Funzione per recuperare gli utenti dal database
    def get_params(self):
        conn_params = {
            "dbname": self.dbname_input.text(),
            "port" : int(self.port.text()),
            "user": self.user_input.text(),
            "password": self.password_input.text(),
            "host": self.host_input.text()
        }
        self.connessione = psycopg2.connect(**conn_params)

        if self.connessione:
            show_info('con successo')
            return self.connessione
        else:
            QMessageBox.critical(
                None, "Errore", f"Si è verificato un'errore"
            )

    # # Funzione per mostrare gli utenti nella finestra
    # def show_users(self):
    #     users = self.get_users()
    #     self.text_box.clear()
    #     self.text_box.insertPlainText("Gli utenti sono:\n\n")
    #     for user in users:
    #         self.text_box.insertPlainText(f"{user['id']}: {user['name']} ({user['email']})\n")
    #     self.text_box.insertPlainText("\n")

# Funzione per gestire gli errori
def show_info(message):
    QMessageBox.information(
        None, "Excellent", f"connection successful: {message}"
    )
def handle_exception(exc_type, exc_value, exc_traceback):
    QMessageBox.critical(
        None, "Error", f"An error has occurred: {exc_value}"
    )
    #sys.exit(1)

def close(self):
        super().close()
def exec_(self):
    # Implementazione del metodo exec_()
    super().exec_()
# Configurazione dell'handler per le eccezioni
sys.excepthook = handle_exception

# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = Postgresconnection()
#     window.show()
#     sys.exit(app.exec_())