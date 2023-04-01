from PyQt5 import QtGui,QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from googletrans import Translator
import difflib
import time
import requests
import deepl
import os
import sqlite3
import threading
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
        self.apikey=''

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

        # Creare l'azione Salva
        salva_menu = QtWidgets.QMenu('Salva', self)
        file_menu.addMenu(salva_menu)
        salva_action = QtWidgets.QAction('Salva', self)
        salva_action.triggered.connect(self.salva_database)
        salva_menu.addAction(salva_action)

        salva_come = QtWidgets.QAction('Salva come...', self)
        salva_come.triggered.connect(self.salva_database)
        salva_menu.addAction(salva_come)

        rollback = QtWidgets.QAction('Rollback', self)
        rollback.triggered.connect(self.salva_database)
        salva_menu.addAction(rollback)


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

        self.btn_traduci = QtWidgets.QPushButton('Traduci', self)
        self.btn_seleziona_tutti = QtWidgets.QPushButton('Seleziona tutti', self)
        self.btn_deseleziona_tutti = QtWidgets.QPushButton('Deseleziona tutti', self)

        # Connect button signals to slots
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
        self.nome_file = nome_file
        if nome_file:
            self.connessione = sqlite3.connect(nome_file)
            self.connessione.isolation_level = None
            self.cursor = self.connessione.cursor()

            # Get table names from database
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%'"
                        "AND name NOT LIKE 'idx_%'"
                        "AND name NOT LIKE 'views_%'"
                        "AND name NOT LIKE 'virts_%'"
                        "AND name NOT LIKE 'geometry_%'"
                        "AND name NOT LIKE 'raster_%'"
                        "AND name NOT LIKE 'spatialite%'"
                        "AND name NOT LIKE 'sqlite%'"
                        "AND name NOT LIKE 'ISO%'"
                        "AND name NOT LIKE 'spatial_%'"
                        "AND name NOT LIKE 'rl2map%'"
                        "AND name NOT LIKE 'coverage%'"
                        "AND name NOT LIKE 'wms%'"
                        "AND name NOT LIKE 'vector%'"
                        "AND name NOT LIKE 'SE_%'"
                        "AND name NOT LIKE 'stored%'"
                        "AND name NOT LIKE 'sql_%'"
                        ";")
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
        for tabella in sorted(self.tabelle):
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
        self.data = self.cursor.fetchall()
        self.colonne = [desc[0] for desc in self.cursor.description]
        self.tabella.setColumnCount(len(self.colonne))
        self.tabella.setRowCount(len(self.data))
        self.tabella.setHorizontalHeaderLabels(self.colonne)
        self.tabella.setColumnWidth(0, 200)

        # Fill the table with data
        for i, row in enumerate(self.data):
            for j, value in enumerate(row):
                self.tabella.setItem(i, j, QtWidgets.QTableWidgetItem(str(value)))

        # Add translation options for selected columns
        for i, colonna in enumerate(self.colonne):
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

            for row_num in range(self.tabella.rowCount()):
                row_data = []
                for col_num in range(self.tabella.columnCount()):
                    item = self.tabella.item(row_num, col_num)
                    if item is not None:
                        row_data.append(item.text())
                    else:
                        row_data.append('')
                id_column_name = self.colonne[0]
                set_query = ', '.join([f"{self.colonne[i]}='{row_data[i]}'" for i in range(len(self.colonne))])
                try:
                    query = f"UPDATE {self.lista_tabelle.currentText()} SET {set_query} WHERE {id_column_name}={row_num +1 }"
                    self.cursor.execute(query)
                    self.connessione.commit()
                except Exception as e:
                    self.connessione.rollback()
            if query:

                self.show_info('Saved')
            else:
                self.show_info('OOPs.. somethig is wrog')


        elif self.connessione is None:
            self.show_info('You need connect the database')
        else:
            self.show_info('No changed data')

    def translate_google(self,item, translator, in_l, out_l):
        """
        Funzione di supporto che traduce una singola cella della tabella in base al testo originale
        :param item:
        :param translator:
        :return:
        """
        if item is not None and item.text() != '':
            testo = item.text()
            traduzione = translator.translate(testo, src = in_l, dest = out_l).text
            item.setText(traduzione)

    def translate_deepl(self,item,auth_key, in_l, out_l):

        if item is not None and item.text() != '':
            testo = item.text()
            translator = deepl.Translator(auth_key)
            t = translator.translate_text(testo,in_l, out_l)


            item.setText(traduzione)

    def traduci_dati(self):
        """
        Traduce i dati nelle colonne selezionate e visualizza l'avanzamento utilizzando la barra di avanzamento.
        :return:
        """
        try:
            start_time = time.time()




            translator_options = ['google', 'deepl']

            selected_l, ok = QInputDialog.getItem(None,
                                                  'Tipo di traduttore',
                                                  'Seleziona un traduttore:',
                                                  translator_options,
                                                  0,
                                                  False)
            if not ok:
                print('No item selected')
                return

            if selected_l=='google':
                language_options = {'it': 'Italian', 'en': 'English', 'fr': 'French', 'ar': 'Arabic', 'de': 'German',
                                    'es': 'Spanish'}
                translator = Translator()

            elif selected_l=='deepl':

                translator_deepl = self.apikey_deepl()
                language_options = {'it': 'Italian', 'en': 'English', 'fr': 'French', 'ar': 'Arabic', 'de': 'German',
                                    'es': 'Spanish'}
                #translator_deepl = deepl.Translator(self.apikey_deepl())


            selected_item, ok = QInputDialog.getItem(None,
                                                     'Lingua di input',
                                                     'Seleziona una lingua di input:',
                                                     list(language_options.values()),
                                                     0,
                                                     False)
            print(list(language_options.values()))
            if not ok:
                print('No item selected')
                return

            selected_item2, ok = QInputDialog.getItem(None,
                                                      'Lingua di output',
                                                      'Seleziona una lingua di output:',
                                                      list(language_options.values()),
                                                      0,
                                                      False)
            print(list(language_options.values()))
            if not ok:
                print('No item selected')
                return

            in_l = list(language_options.keys())[list(language_options.values()).index(selected_item)]
            out_l = list(language_options.keys())[list(language_options.values()).index(selected_item2)]
            print(in_l,out_l)
            self.progress_bar.setRange(0, self.tabella.rowCount())
            self.progress_bar.setValue(0)

            thread_list = []

            for j in [j for j, colonna in
                      enumerate(self.tabella.horizontalHeaderItem(j).text() for j in range(self.tabella.columnCount()))
                      if self.opzioni_traduzione[colonna].isChecked()]:
                for i in range(self.tabella.rowCount()):
                    item = self.tabella.item(i, j)

                    if selected_l == 'deepl':
                        #translator_deepl=self.apikey_deepl()
                        t = threading.Thread(target = self.translate_deepl, args = (item, translator_deepl,in_l, out_l))
                    if selected_l =='google':
                        translator= Translator()
                        t = threading.Thread(target = self.translate_google, args = (item, translator, in_l, out_l))
                    thread_list.append(t)
                    t.start()

                    self.progress_bar.setValue(i + 1)
                    pct = (i + 1) / self.tabella.rowCount()
                    elapsed_time = time.time() - start_time
                    estimated_time = (elapsed_time * self.tabella.rowCount()) / (i + 1) - elapsed_time
                    self.progress_bar.setTextVisible(True)
                    self.progress_bar.setFormat(f"Traduzione riga {i + 1}/{self.tabella.rowCount()} - colonna {j + 1}/"
                                                f"{self.tabella.columnCount()}\nTempo trascorso: {elapsed_time:.1f}s /"
                                                f"Tempo Stimato {estimated_time:.1f}s ({pct:.0%})")
                    self.progress_bar.setAlignment(Qt.AlignCenter)

            for t in thread_list:
                t.join()
            self.show_info('Finished')

            self.progress_bar.setValue(0)
        except Exception as e:
            print(str(e))



    def apikey_deepl(self):
        # Verifica se il file deepl_api_key.txt esiste
        if os.path.exists('deepl_api_key.txt'):
            # Leggi l'API Key dal file
            with open('deepl_api_key.txt', 'r') as f:
                api_key = f.read().strip()
                headers = {"Authorization": f"DeepL-Auth-Key {api_key}"}
                response = requests.post("https://api.deepl.com/v2/auth", headers = headers)

                if response.status_code == 200:
                    print('apikey valida')# L'API key è valida
                else:
                    reply = QMessageBox.question(self, 'Warning', 'Apikey non valida'+'\n'
                                                 +'Clicca ok per inserire la chiave', QMessageBox.Ok|QMessageBox.Cancel)
                    if reply==QMessageBox.Ok:

                        api_key, ok = QInputDialog.getText(None, 'Apikey deepl', 'Inserisci apikey valida:')
                        if ok:
                            # Salva la nuova API Key nel file
                            with open('deepl_api_key.txt', 'w') as f:
                                f.write(api_key)
                                f.close()
                            with open('deepl_api_key.txt', 'r') as f:
                                api_key = f.read().strip()
                    else:
                        return
        else:
            # Chiedi all'utente di inserire una nuova API Key

            api_key, ok = QInputDialog.getText(None, 'Apikey deepl', 'Inserisci apikey:')
            if ok:
                # Salva la nuova API Key nel file
                with open('deepl_api_key.txt', 'w') as f:
                    f.write(api_key)
                    f.close()
                with open('deepl_api_key.txt', 'r') as f:
                    api_key = f.read().strip()

        return api_key


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
    def show_warning(self, message):
        """
        Funzione per mostrare i messaggi
        :param message:
        :return:
        """
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Information)
        dialog.setText(message)
        dialog.setWindowTitle('Warning')
        dialog.setStandardButtons(QMessageBox.Cancel|QMessageBox.Ok)
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