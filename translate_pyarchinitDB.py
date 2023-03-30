import sqlite3
import threading
from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from googletrans import Translator
import difflib

class Finestra(QtWidgets.QWidget):
    def __init__(self):
        """
        Inizializza una nuova istanza della classe `Finestra`.
        """
        super().__init__()
        self.connessione = None
        self.cursor = None
        self.tabelle = []
        self.opzioni_traduzione = {}
        self.init_ui()

    def init_ui(self):
        """
        Inizializza l'interfaccia utente (UI) creando oggetti di layout, aggiungendo widget, collegando segnali e slot e
        impostando le proprietà della finestra.
        """
        # Create buttons
        hbox = QtWidgets.QHBoxLayout()
        # Add a menu bar
        menubar = QtWidgets.QMenuBar()

        # Create a File menu with an Open action and a Save action
        file_menu = menubar.addMenu('File')

        apri_action = QtWidgets.QAction('Apri', self)
        apri_action.triggered.connect(self.apri_database)
        file_menu.addAction(apri_action)

        salva_action = QtWidgets.QAction('Salva', self)
        salva_action.triggered.connect(self.salva_database)
        file_menu.addAction(salva_action)

        stop_action = QtWidgets.QAction('Stop', self)
        stop_action.triggered.connect(self.stop_process)
        file_menu.addAction(stop_action)

        # Create an Edit menu with a Find/Replace action
        edit_menu = menubar.addMenu('Edit')

        find_replace_action = QtWidgets.QAction('Find/Replace', self)
        find_replace_action.triggered.connect(self.show_find_replace_dialog)
        edit_menu.addAction(find_replace_action)

        valida_menu = menubar.addMenu("Valida")
        valida_traduzione_action = QtWidgets.QAction("Traduzione", self)
        valida_traduzione_action.triggered.connect(self.action_verifica_traduzione)
        valida_menu.addAction(valida_traduzione_action)

        self.btn_apri = QtWidgets.QPushButton('Apri database', self)
        self.btn_salva = QtWidgets.QPushButton('Salva database', self)
        self.btn_stop = QtWidgets.QPushButton('Stop processo', self)
        self.btn_traduci = QtWidgets.QPushButton('Traduci', self)
        self.btn_seleziona_tutti = QtWidgets.QPushButton('Seleziona tutti', self)
        self.btn_deseleziona_tutti = QtWidgets.QPushButton('Deseleziona tutti', self)

        # Connect button signals to slots
        self.btn_apri.clicked.connect(self.apri_database)
        self.btn_salva.clicked.connect(self.salva_database)
        self.btn_stop.clicked.connect(self.stop_process)
        self.btn_traduci.clicked.connect(self.traduci_dati)

        # Add progress bar and table widgets
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.tabella = QtWidgets.QTableWidget(self)

        # Set widget properties
        self.progress_bar.setGeometry(20, 100, 500, 20)
        self.tabella.setGeometry(20, 140, 900, 590)
        self.tabella.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.tabella.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.btn_seleziona_tutti.clicked.connect(lambda _: self.select_all_checkboxes(True))
        self.btn_deseleziona_tutti.clicked.connect(lambda _: self.select_all_checkboxes(False))
        # Add label for validation messages
        self.lbl_validazione = QtWidgets.QLabel(self)

        # Add widgets to layout
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(menubar)
        vbox.addWidget(self.lbl_validazione)
        self.btn_apri.setHidden(True)
        self.btn_salva.setHidden(True)
        self.btn_stop.setHidden(True)
        vbox.addWidget(self.btn_traduci)
        vbox.addWidget(self.progress_bar)
        vbox.addWidget(self.tabella)

        hbox.addWidget(self.btn_seleziona_tutti)
        hbox.addWidget(self.btn_deseleziona_tutti)
        vbox.addLayout(hbox)
        self.find_replace_dialog = FindReplaceDialog(self)




        # Set window properties
        self.setLayout(vbox)
        self.setGeometry(50, 50, 950, 600)
        self.setWindowTitle('Traduzione Database')

    def action_verifica_traduzione(self):
        """
        Verifica la validità di una traduzione confrontando il testo originale con il testo tradotto.
        :return:
        """
        # Inserisci qui il testo originale e tradotto per la verifica
        testo_originale = "Ciao mondo!"
        testo_tradotto = "Hello world!"

        # Verifica la validità della traduzione

        s = difflib.SequenceMatcher(None, testo_originale, testo_tradotto)
        ratio = s.ratio()
        if ratio > 0.9:
            valid = True
            self.lbl_validazione.setText("La traduzione è valida.")
            self.lbl_validazione.setStyleSheet("color: green")
        else:
            valid = False
            self.lbl_validazione.setText("La traduzione non è valida.")
            self.lbl_validazione.setStyleSheet("color: red")
    def show_find_replace_dialog(self):
        """
        Visualizza una finestra di dialogo che consente agli utenti di cercare e sostituire il testo all'interno dei
        dati visualizzati nel widget tabella
        :return: text
        """
        # Show the find/replace dialog
        if self.find_replace_dialog.exec_() == QtWidgets.QDialog.Accepted:
            # Get text to find and replace
            cerca = self.find_replace_dialog.txt_cerca.text()
            sostituisci = self.find_replace_dialog.txt_sostituisci.text()

            # Find and replace text in table widget
            for row in range(self.tabella.rowCount()):
                for column in range(self.tabella.columnCount()):
                    item = self.tabella.item(row, column)
                    if item is not None and cerca in item.text():
                        item.setText(item.text().replace(cerca, sostituisci))
    def apri_database(self):
        """
        Apre una finestra di dialogo file per consentire all'utente di selezionare un file sqlite, quindi si
        connette al database e recupera i nomi delle tabelle.
        :return:
        """
        # Open file dialog to select the database file
        nome_file, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Apri database', '',
                                                             'Database (*.db *.sqlite)')
        if nome_file:
            self.connessione = sqlite3.connect(nome_file)
            self.cursor = self.connessione.cursor()

            # Get table names from database
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            self.tabelle = [tabella[0] for tabella in self.cursor.fetchall()]
            print(self.tabelle)
            self.visualizza_tabelle()

    def visualizza_tabelle(self):
        """
        Crea un widget casella combinata per mostrare le tabelle nel database e aggiunge un pulsante per consentire
        all'utente di selezionare la tabella scelta
        """
        # Create combo box to show tables in the database
        self.lista_tabelle = QtWidgets.QComboBox(self)
        for tabella in self.tabelle:
            self.lista_tabelle.addItem(tabella)

        # Add button to select table
        self.btn_seleziona_tabella = QtWidgets.QPushButton('Seleziona', self)
        self.btn_seleziona_tabella.clicked.connect(self.seleziona_tabella)

        # Add combo box and button to layout
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.lista_tabelle)
        hbox.addWidget(self.btn_seleziona_tabella)

        # Add layout to widget
        widget = QtWidgets.QWidget()
        widget.setLayout(hbox)
        self.layout().insertWidget(1, widget)

    def seleziona_tabella(self):
        """
        Seleziona una tabella dal database e ne visualizza i dati nel widget tabella, aggiungendo anche caselle di
        controllo per consentire agli utenti di selezionare le colonne per la traduzione
        """
        tabella_selezionata = self.lista_tabelle.currentText()
        self.cursor.execute(f"SELECT * FROM {tabella_selezionata}")
        data = self.cursor.fetchall()
        colonne = [desc[0] for desc in self.cursor.description]
        self.tabella.setColumnCount(len(colonne))
        self.tabella.setRowCount(len(data))
        self.tabella.setHorizontalHeaderLabels(colonne)
        self.tabella.setColumnWidth(0, 200)

        # Fill the table with data
        for i, row in enumerate(data):
            for j, value in enumerate(row):
                self.tabella.setItem(i, j, QtWidgets.QTableWidgetItem(str(value)))

        # Add translation options for selected columns
        for i, colonna in enumerate(colonne):
            checkbox = QtWidgets.QCheckBox(self)
            checkbox.setText(colonna)
            self.opzioni_traduzione[colonna] = checkbox

            # Add checkbox to layout
            hbox = QtWidgets.QHBoxLayout()
            hbox.addWidget(checkbox)
            self.layout().insertLayout(2 + i, hbox)

    def select_all_checkboxes(self, state):
        """
        Seleziona o deseleziona tutte le caselle di spunta per le opzioni di traduzione.
        :param state:
        :return:
        """
        for checkbox in self.opzioni_traduzione.values():
            checkbox.setChecked(state)

    def salva_database(self):
        """
        Salva tutte le modifiche apportate al database e chiude la connessione al database.
        :return:
        """
        if self.connessione is not None:
            self.connessione.commit()
            self.connessione.close()

    def traduci_dati(self):
        """
        Traduce i dati nelle colonne selezionate e visualizza l'avanzamento utilizzando la barra di avanzamento.
        :return:
        """
        try:
            translator = Translator()

            for i in range(self.tabella.rowCount()):
                thread_list = []

                for j in range(self.tabella.columnCount()):
                    colonna = self.tabella.horizontalHeaderItem(j).text()

                    if self.opzioni_traduzione[colonna].isChecked():
                        item = self.tabella.item(i, j)
                        t = threading.Thread(target = self.translate_item, args = (item, translator))
                        thread_list.append(t)
                        t.start()

                for t in thread_list:
                    t.join()

                progress = int(((i + 1) / self.tabella.rowCount()) * 100)
                self.progress_bar.setValue(progress)



            QtWidgets.QApplication.processEvents()
            self.show_info('Finished')

            self.progress_bar.setValue(0)
        except Exception as e:
            print(str(e))

    def translate_item(self, item, translator):
        """
        Funzione di supporto che traduce una singola cella della tabella in base al testo originale
        :param item:
        :param translator:
        :return:
        """
        if item is not None and item.text() != '':
            testo = item.text()
            traduzione = translator.translate(testo, dest = 'en').text
            item.setText(traduzione)

    def verifica_traduzione(self, testo_originale, testo_tradotto):
        """
        Funzione di supporto che verifica se la traduzione è valida confrontando il testo originale e il testo tradotto.
        :param testo_originale:
        :param testo_tradotto:
        :return:
        """
        if valid:
            self.lbl_validazione.setText("La traduzione è valida.")
            self.lbl_validazione.setStyleSheet("color: green")
        else:
            self.lbl_validazione.setText("La traduzione non è valida.")
            self.lbl_validazione.setStyleSheet("color: red")

    def stop_process(self):
        """
        Funzione segnaposto per arrestare un processo o un thread, ma attualmente non implementata nel codice
        :return:
        """
        # To stop a running process/thread
        # Not implemented in the current code
        pass

    def btn_seleziona_tutti(self):
        """
        Seleziona tutte le caselle di controllo per le opzioni di traduzione.
        :return:
        """
        for checkbox in self.opzioni_traduzione.values():
            checkbox.setChecked(True)

    def btn_deseleziona_tutti(self):
        """
        Deseleziona tutte le caselle di controllo per le opzioni di traduzione.
        :return:
        """
        for checkbox in self.opzioni_traduzione.values():
            checkbox.setChecked(False)

    def show_info(self, message):
        """
        Funzione per mostrare i messaggi
        :param message:
        :return:
        """
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Information)
        dialog.setText(message)
        dialog.setWindowTitle('Info')
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.show()

class TestoNonVuotoValidator(QtGui.QValidator):
    """
    Funzione di convalida che controlla se il testo di input è vuoto o meno.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def validate(self, testo, posizione):
        if testo == '' or testo.isspace():
            return QtGui.QValidator.Invalid, testo, posizione
        else:
            return QtGui.QValidator.Acceptable, testo, posizione


class FindReplaceDialog(QtWidgets.QDialog):
    """
    Crea una finestra di dialogo con i widget find/replace.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Find and replace')

        # Create widgets
        self.lbl_cerca = QtWidgets.QLabel('Cerca:')
        self.txt_cerca = QtWidgets.QLineEdit()
        self.lbl_sostituisci = QtWidgets.QLabel('Sostituisci con:')
        self.txt_sostituisci = QtWidgets.QLineEdit()
        self.btn_avvia = QtWidgets.QPushButton('Avvia')
        self.btn_annulla = QtWidgets.QPushButton('Annulla')

        # Connect button signals to slots
        self.btn_avvia.clicked.connect(self.avvia_find_replace)
        self.btn_annulla.clicked.connect(self.reject)

        # Add widgets to layout
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.lbl_cerca, 0, 0)
        layout.addWidget(self.txt_cerca, 0, 1)
        layout.addWidget(self.lbl_sostituisci, 1, 0)
        layout.addWidget(self.txt_sostituisci, 1, 1)
        layout.addWidget(self.btn_avvia, 2, 0)
        layout.addWidget(self.btn_annulla, 2, 1)

        # Set layout and dialog properties
        self.setLayout(layout)
        self.setModal(True)

    def avvia_find_replace(self):
        """
        Avvia la funzione di find/replace
        :return:
        """
        self.accept()


if __name__ == '__main__':
    """
    Questo è il punto di ingresso principale del programma in cui vengono creati e visualizzati all'utente l'oggetto 
    dell'applicazione e la finestra principale.
    """
    app = QtWidgets.QApplication([])
    finestra = Finestra()
    finestra.show()
    app.exec_()

 # La classe `Finestra` contiene tre pulsanti - `btn_apri`, `btn_traduci` e `btn_seleziona_tabella` - e una tabella `tabella` per la visualizzazione dei dati. Quando l'utente fa clic sul pulsante `btn_apri`, viene mostrata una finestra di dialogo per selezionare il file del database. Se il file viene selezionato, la lista delle tabelle contenute nel database viene visualizzata nella casella di selezione `lista_tabelle` e il pulsante `btn_seleziona_tabella` viene mostrato. Quando l'utente fa clic sul pulsante `btn_seleziona_tabella`, la tabella selezionata viene visualizzata nella finestra e le opzioni di traduzione per le colonne selezionate vengono visualizzate sotto forma di checkbox.
 # Quando l'utente fa clic sul pulsante `btn_traduci`, gli elementi selezionati nella tabella vengono tradotti in inglese utilizzando l'API di Google Translate. La traduzione viene applicata solo ai campi selezionati dall'utente. I risultati della traduzione vengono visualizzati nella tabella.
 # Per aggiungere una funzione di validazione, potresti ad esempio includere una casella di selezione per specificare la lingua di origine dei dati nel database. La casella di selezione potrebbe essere utilizzata per filtrare solo i campi validi per la traduzione in inglese.