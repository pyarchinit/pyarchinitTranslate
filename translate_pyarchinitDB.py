import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPixmap
from PyQt5.QtMultimedia import QMediaContent,QMediaPlayer
from PyQt5.QtWidgets import *
from googletrans import Translator
import difflib
import time
from deepl import Translator as tr_d
import os
import sqlite3
import threading
import shutil
import csv
from test import Postgresconnection


class SplashScreen(QSplashScreen):
    def __init__(self, image_path, audio_path):
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            super().__init__(pixmap, Qt.WindowStaysOnTopHint)
            self.player = QMediaPlayer()
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(audio_path)))
            self.player.mediaStatusChanged.connect(self.handleMediaStateChanged)
        else:
            raise FileNotFoundError("Could not find image file")

    def handleMediaStateChanged(self, state):
        if state == QMediaPlayer.LoadedMedia:
            self.show()
            self.player.play()
        elif state == QMediaPlayer.InvalidMedia or state == QMediaPlayer.NoMedia:
            print("Error:", self.player.errorString())
            self.close()

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
        self.grid_layouts = {}  # create a dictionary to store grid layouts for each table
        self.tabella_corrente = None

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

        apri_action_menu = QtWidgets.QMenu('Apri', self)
        file_menu.addMenu(apri_action_menu)

        apri_action_db = QtWidgets.QAction('Apri db sqlite', self)
        apri_action_db.triggered.connect(self.apri_database)
        apri_action_menu.addAction(apri_action_db)

        apri_action_pg = QtWidgets.QAction('Apri db postgres', self)
        apri_action_pg.triggered.connect(self.apri_database_pg)
        apri_action_menu.addAction(apri_action_pg)

        # Creare l'azione Salva
        salva_menu = QtWidgets.QMenu('Salva', self)
        file_menu.addMenu(salva_menu)
        # crea sottogruppo
        salva_action = QtWidgets.QAction('Salva', self)
        salva_action.triggered.connect(self.salva_database)
        salva_menu.addAction(salva_action)

        salva_come = QtWidgets.QAction('Salva copia db sqlite', self)
        salva_come.triggered.connect(self.salva_come)
        salva_menu.addAction(salva_come)


        # crea importa menu
        importa = QtWidgets.QAction('Importa CSV', self)
        importa.triggered.connect(self.importa)
        file_menu.addAction(importa)

        esporta = QtWidgets.QAction('Esporta CSV', self)
        esporta.triggered.connect(self.esporta)
        file_menu.addAction(esporta)

        stop_action = QtWidgets.QAction('Stop process', self)
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

        # Add grid layout for translation options
        self.traduzione_layout = QtWidgets.QGridLayout()
        self.traduzione_groupbox = QtWidgets.QGroupBox("Opzioni traduzione")
        self.traduzione_groupbox.setLayout(self.traduzione_layout)

        # Add widgets to layout
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(menubar)
        vbox.addWidget(self.lbl_validazione)

        vbox.addWidget(self.btn_traduci)
        vbox.addWidget(self.progress_bar)
        vbox.addWidget(self.tabella)
        vbox.addWidget(self.traduzione_groupbox)

        # Add translation options buttons to layout
        hbox.addWidget(self.btn_seleziona_tutti)
        hbox.addWidget(self.btn_deseleziona_tutti)
        vbox.addLayout(hbox)

        self.find_replace_dialog = FindReplaceDialog(self)

        # Set window properties
        self.setLayout(vbox)
        self.setGeometry(50, 50, 950, 600)
        self.setWindowTitle('Traduzione Database')

    def aggiorna_traduzione_layout(self, text):
        """
        Aggiorna il layout delle opzioni di traduzione quando viene selezionata una nuova tabella
        """
        self.seleziona_tabella()
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

    def apri_database_pg(self):

        db_pg = Postgresconnection()
        db_pg.exec_()
        self.connessione = db_pg.get_params()


        self.cursor = self.connessione.cursor()
        print (self.cursor)
        if self.cursor:

            self.cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public'")
            self.tabelle = [tabella[0] for tabella in self.cursor.fetchall()]
            self.visualizza_tabelle()

        else:
            self.show_error('Errore di connessione')
            #db_pg.close()
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

    def importa(self):
        name_csv, _= QtWidgets.QFileDialog.getOpenFileName(self, 'Apri csv', '',
                                                          'CSV (*.csv)')
        self.name_csv = name_csv
        self.tabelle = [name_csv]
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
        if self.lista_tabelle.currentText().endswith('.csv'):
            self.btn_seleziona_tabella.clicked.connect(self.seleziona_tabella_csv)
        else:
            self.btn_seleziona_tabella.clicked.connect(self.seleziona_tabella)

        # Add combo box and button to layout
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.lista_tabelle)
        hbox.addWidget(self.btn_seleziona_tabella)

        # Add layout to widget
        widget = QtWidgets.QWidget()
        widget.setLayout(hbox)
        self.layout().insertWidget(1, widget)


    def seleziona_tabella_csv(self):
        """
        Seleziona una tabella dal csv e ne visualizza i dati nel widget tabella, aggiungendo anche caselle di
        controllo per consentire agli utenti di selezionare le colonne per la traduzione.
        """

        with open(self.name_csv, 'r') as file:
            reader = csv.reader(file)
            #reader = reader.decode('utf-8')
            header = next(reader)  # assume first row contains column names
            rows = list(reader)

        # Clear the translation options layout
        while self.traduzione_layout.count():
            item = self.traduzione_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Remove checkboxes from the previous grid layout
        if self.tabella_corrente in self.grid_layouts:
            old_grid_layout = self.grid_layouts[self.tabella_corrente]
            for row in range(old_grid_layout.rowCount()):
                for column in range(old_grid_layout.columnCount()):
                    item = old_grid_layout.itemAtPosition(row, column)
                    if item is not None and item.widget() is not None:
                        widget = item.widget()
                        old_grid_layout.removeWidget(widget)
                        widget.deleteLater()

        # Set up the table widget
        self.tabella.clearContents()
        self.tabella.setColumnCount(len(header))
        self.tabella.setRowCount(len(rows))
        self.tabella.setHorizontalHeaderLabels(header)
        self.tabella.setColumnWidth(0, 200)

        # Create a grid layout with dynamic number of rows and columns
        n_cols = len(header)
        n_rows = (n_cols + 9) // 10  # assume 10 checkboxes per row
        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setColumnStretch(n_cols, 1)
        self.grid_layouts[self.name_csv] = grid_layout

        # Fill the table with data
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                self.tabella.setItem(i, j, QtWidgets.QTableWidgetItem(value))

        # Add translation options for selected columns
        self.opzioni_traduzione = {}
        for i, colonna in enumerate(header):
            checkbox = QtWidgets.QCheckBox(self)
            checkbox.setText(colonna)
            self.opzioni_traduzione[colonna] = checkbox

            # Add checkbox to grid layout
            row = i // 10
            column = i % 10
            grid_layout.addWidget(checkbox, row, column)

        # Add horizontal stretch to the grid layout
        spacer = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        grid_layout.addItem(spacer, n_rows, 0, 1, -1)

        # Add the grid layout to the translation options layout
        self.traduzione_layout.addLayout(grid_layout, 0, 0, 1, 1, alignment = QtCore.Qt.AlignLeft)

        # Update the current table reference
        self.tabella_corrente = self.name_csv
    def seleziona_tabella(self):
        """
        Seleziona una tabella dal database e ne visualizza i dati nel widget tabella, aggiungendo anche caselle di
        controllo per consentire agli utenti di selezionare le colonne per la traduzione.
        """

        tabella_selezionata = self.lista_tabelle.currentText()

        # Clear the translation options layout
        while self.traduzione_layout.count():
            item = self.traduzione_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Remove checkboxes from the previous grid layout
        if self.tabella_corrente in self.grid_layouts:
            old_grid_layout = self.grid_layouts[self.tabella_corrente]
            for row in range(old_grid_layout.rowCount()):
                for column in range(old_grid_layout.columnCount()):
                    item = old_grid_layout.itemAtPosition(row, column)
                    if item is not None and item.widget() is not None:
                        widget = item.widget()
                        old_grid_layout.removeWidget(widget)
                        widget.deleteLater()

        # Set up the table widget
        self.cursor.execute(f"SELECT * FROM {tabella_selezionata}")
        self.data = self.cursor.fetchall()
        self.colonne = [desc[0] for desc in self.cursor.description]
        print(self.colonne)

        self.tabella.clearContents()
        self.tabella.setColumnCount(len(self.colonne))
        self.tabella.setRowCount(len(self.data))
        self.tabella.setHorizontalHeaderLabels(self.colonne)
        self.tabella.setColumnWidth(0, 200)

        # Create a grid layout with 4 columns
        if tabella_selezionata not in self.grid_layouts:
            grid_layout = QtWidgets.QGridLayout()
            grid_layout.setColumnStretch(3, 1)
            self.grid_layouts[tabella_selezionata] = grid_layout
        else:
            grid_layout = self.grid_layouts[tabella_selezionata]

        # Fill the table with data
        for i, row in enumerate(self.data):
            for j, value in enumerate(row):
                self.tabella.setItem(i, j, QtWidgets.QTableWidgetItem(str(value)))

        # Add translation options for selected columns
        self.opzioni_traduzione = {}
        for i, colonna in enumerate(self.colonne):
            checkbox = QtWidgets.QCheckBox(self)
            checkbox.setText(colonna)
            self.opzioni_traduzione[colonna] = checkbox

            # Add checkbox to grid layout
            row = i // 10
            column = i % 10
            grid_layout.addWidget(checkbox, row, column)

        # Add horizontal stretch to the grid layout
        spacer = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        grid_layout.addItem(spacer, row + 1, 0, 1, -1)

        # Add the grid layout to the translation options layout
        self.traduzione_layout.addLayout(grid_layout, 0, 0, 1, 1, alignment=Qt.AlignLeft)

        # Update the current table reference
        self.tabella_corrente = tabella_selezionata
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
            print(self.connessione)
            self.cursor = self.connessione.cursor()
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
                    print(query)
                    self.cursor.execute(query)

                    self.connessione.commit()
                except Exception as e:
                    self.connessione.rollback()
                    print(e)

            if query:

                self.show_info('Saved')
            else:
                self.show_info('OOPs.. somethig is wrog')

        elif self.connessione is None and self.lista_tabelle.currentText().endswith('.csv'):
            # salva le modifiche nel file CSV
            with open(self.name_csv, 'w', newline = '') as file:
                writer = csv.writer(file)
                for i in range(self.tabella.rowCount()):
                    row = []
                    for j in range(self.tabella.columnCount()):
                        item = self.tabella.item(i, j)
                        if item is not None:
                            row.append(item.text())
                        else:
                            row.append('')
                    writer.writerow(row)

        else:
            self.show_info('No changed data')


    def salva_come(self):
        """
        Fa una copia del db.
        :return:
        """
        self.show_info(f"Questa funzione serve per fare una copia del db sqlite."
                       f"Quindi funziona solo se hai caricato un db sqlite. "
                       f"'\n' per salvare la tabella csv usa la funzione 'Esporta', o se devi salvare un db postgres "
                       f"usa la funzione salva")
        if self.connessione is not None:
            # Selezione del file di output tramite QFileDialog
            new_db_path, _ = QFileDialog.getSaveFileName(None, "Salva copia come", "", "Database SQLite (*.sqlite)")

            # Copia del file del database originale nel nuovo percorso
            shutil.copy2(self.nome_file, new_db_path)
        else:
            self.show_info(f"Questa funzione salva solo se hai caricato un db sqlite, "
                           f"'\n' per salvare la tabella csv usa la funzione 'Esporta'")
    def esporta(self):
        """
        Esporta la tabella selezionata
        :return:
        """
        if self.connessione is not None:
            # Esecuzione della query di selezione dei dati
            self.cursor.execute(f"SELECT * FROM {self.lista_tabelle.currentText()}")

            # Lettura dei dati dalla query
            rows = self.cursor.fetchall()
            # Selezione del file di output tramite QFileDialog
            output_file, _ = QFileDialog.getSaveFileName(None, "Esporta in CSV", "", "CSV (*.csv)")

            # Apertura del file di output in modalità scrittura
            with open(output_file, 'w', newline = '', encoding = 'utf-8') as f:
                # Creazione di un writer CSV
                writer = csv.writer(f)

                # Scrittura dell'header del file CSV
                header = [description[0] for description in self.cursor.description]
                writer.writerow(header)

                # Scrittura dei dati nel file CSV
                for row in rows:
                    writer.writerow(row)

            # Chiusura della connessione al database
            self.connessione.close()
        else:
            # Selezione del file di output tramite QFileDialog
            output_file, _ = QFileDialog.getSaveFileName(None, "Esporta in CSV", "", "CSV (*.csv)")

            # Apertura del file di output in modalità scrittura
            with open(output_file, 'w', newline = '') as file:
                writer = csv.writer(file)
                for i in range(self.tabella.rowCount()):
                    row = []
                    for j in range(self.tabella.columnCount()):
                        item = self.tabella.item(i, j)
                        if item is not None:
                            row.append(item.text())
                        else:
                            row.append('')
                    writer.writerow(row)
    def translate_google(self,item,translator, in_l, out_l):
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

    def translate_deepl(self,item,auth_key,out_l):

        if item is not None and item.text() != '':
            testo = item.text()
            translator = tr_d(auth_key)
            t = translator.translate_text(testo, target_lang=out_l).text


            item.setText(t)

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

            if selected_l == 'google':
                language_options = {'it': 'Italian', 'en': 'English', 'fr': 'French', 'ar': 'Arabic', 'de': 'German',
                                    'es': 'Spanish'}

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
            if selected_l == 'deepl':
                self.show_info('Sciegliendo deepl come traduttore devi solo scegliere in che lingua vuoi tradurre')
                translator_deepl = self.apikey_deepl()
                language_options = {'EN-GB': 'English British','EN-US': 'English US', 'IT': 'Italian', 'FR': 'French', 'DE': 'German',
                                    'ES': 'Spanish'}
                # translator_deepl = deepl.Translator(self.apikey_deepl())



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
            try:
                in_l = list(language_options.keys())[list(language_options.values()).index(selected_item)]
            except:
                pass
            out_l = list(language_options.keys())[list(language_options.values()).index(selected_item2)]
            #print(in_l, out_l)
            self.progress_bar.setRange(0, self.tabella.rowCount())
            self.progress_bar.setValue(0)

            thread_list = []

            translated_columns = []

            for j in [j for j, colonna in
                      enumerate(self.tabella.horizontalHeaderItem(j).text() for j in range(self.tabella.columnCount()))
                      if self.opzioni_traduzione[colonna].isChecked()]:
                translated_columns.append(self.tabella.horizontalHeaderItem(j).text())
                for i in range(self.tabella.rowCount()):
                    item = self.tabella.item(i, j)

                    if selected_l == 'deepl':
                        # translator_deepl=self.apikey_deepl()
                        t = threading.Thread(target = self.translate_deepl,
                                             args = (item, translator_deepl, out_l))
                    if selected_l == 'google':
                        tr_google = Translator()
                        t = threading.Thread(target = self.translate_google, args = (item,tr_google, in_l, out_l))
                    thread_list.append(t)
                    t.start()

                    self.progress_bar.setValue(i + 1)
                    pct = (i + 1) / self.tabella.rowCount()
                    elapsed_time = time.time() - start_time
                    estimated_time = (elapsed_time * self.tabella.rowCount()) / (i + 1) - elapsed_time
                    self.progress_bar.setTextVisible(True)
                    self.progress_bar.setFormat(
                        f"Traduzione riga {i + 1}/{self.tabella.rowCount()} - colonna {j + 1}/"
                        f"{self.tabella.columnCount()}\nTempo trascorso: {elapsed_time:.1f}s /"
                        f"Tempo Stimato {estimated_time:.1f}s ({pct:.0%})")
                    self.progress_bar.setAlignment(Qt.AlignCenter)

            for t in thread_list:
                t.join()

            self.show_info(
                f"La traduzione è stata completata con successo. \n"
                f"Sono state tradotte {i + 1} righe \n"
                f"nelle colonne: <b>{', '.join(translated_columns)}</b>.")

        except Exception as e:
            print(f"Error during translation: {e}")
            self.show_error(f"Errore durante la traduzione: {str(e)}")
    def apikey_deepl(self):
        file_path = "deepl_api_key_.txt"
        api_key = ""
        # Verifica se il file deepl_api_key.txt esiste
        if os.path.exists('deepl_api_key.txt'):
            # Leggi l'API Key dal file
            with open('deepl_api_key.txt', 'r') as f:
                api_key = f.read().strip()
                try:
                    translator = deepl.Translator(api_key)
                    t = translator.translate_text('ciao', target_lang = 'EN-GB')

                    if t:
                        return api_key

                except:
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
                        return api_key


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

    def show_error(self, message):
        """
        Funzione per mostrare i messaggi
        :param message:
        :return:
        """
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Critical)
        dialog.setText(message)
        dialog.setWindowTitle('Error')
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
    app = QApplication(sys.argv)

    # Create and show splash screen
    splash_screen = SplashScreen('OIP.jpg', 'intro.wav')
    splash_screen.show()

    # Create and show main window
    finestra = Finestra()

    # Close splash screen after a delay and show main window
    timer = QtCore.QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(finestra.show)
    timer.timeout.connect(splash_screen.close)
    timer.start(7000)

    sys.exit(app.exec_())
