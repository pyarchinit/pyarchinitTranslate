import sys

import deepl
import googletrans
import requests
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPixmap
from PyQt5.QtMultimedia import QMediaContent,QMediaPlayer
from PyQt5.QtWidgets import *
from googletrans import Translator
import difflib
import time
#import deepl
from deepl import Translator as tr_d
import os
import sqlite3
import threading
import shutil
import csv
from pg_connection import Postgresconnection


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
        self.translator_deepl = None
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

        apri_action_menu = QtWidgets.QMenu('Open', self)
        file_menu.addMenu(apri_action_menu)

        apri_action_db = QtWidgets.QAction('Open db sqlite', self)
        apri_action_db.triggered.connect(self.apri_database)
        apri_action_menu.addAction(apri_action_db)

        apri_action_pg = QtWidgets.QAction('Open db postgres', self)
        apri_action_pg.triggered.connect(self.apri_database_pg)
        apri_action_menu.addAction(apri_action_pg)

        # Creare l'azione Salva
        salva_menu = QtWidgets.QMenu('Save', self)
        file_menu.addMenu(salva_menu)
        # crea sottogruppo
        salva_action = QtWidgets.QAction('Save', self)
        salva_action.triggered.connect(self.salva_database)
        salva_menu.addAction(salva_action)

        salva_come = QtWidgets.QAction('Save a copy of the db sqlite', self)
        salva_come.triggered.connect(self.salva_come)
        salva_menu.addAction(salva_come)


        # crea importa menu
        importa = QtWidgets.QAction('Import CSV', self)
        importa.triggered.connect(self.importa)
        file_menu.addAction(importa)

        esporta = QtWidgets.QAction('Export CSV', self)
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

        valida_menu = menubar.addMenu("Validation")
        valida_traduzione_action = QtWidgets.QAction("Translate", self)
        valida_traduzione_action.triggered.connect(self.action_verifica_traduzione)
        valida_menu.addAction(valida_traduzione_action)

        self.btn_traduci = QtWidgets.QPushButton('Translate', self)
        self.btn_seleziona_tutti = QtWidgets.QPushButton('Select all', self)
        self.btn_deseleziona_tutti = QtWidgets.QPushButton('Deselect all', self)

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
        self.traduzione_groupbox = QtWidgets.QGroupBox("Options for translation")
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
        self.setWindowTitle('Data Translation Tool')

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
            self.lbl_validazione.setText("The translation is valid.")
            self.lbl_validazione.setStyleSheet("color: green")
        else:
            valid = False
            self.lbl_validazione.setText("The translation is not valid.")
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
            self.show_error('Connection error')
            #db_pg.close()
    def apri_database(self):
        """
        Apre una finestra di dialogo file per consentire all'utente di selezionare un file sqlite, quindi si
        connette al database e recupera i nomi delle tabelle.
        :return:
        """
        # Open file dialog to select the database file
        nome_file, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open database', '',
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
        name_csv, _= QtWidgets.QFileDialog.getOpenFileName(self, 'Open csv', '',
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
        self.btn_seleziona_tabella = QtWidgets.QPushButton('Select', self)
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

    def get_db_type(self, connessione):
        try:
            # Tentativo per PostgreSQL con Psycopg2
            if hasattr(connessione, 'dsn'):
                return 'postgresql'
            # Tentativo per SQLite
            elif hasattr(connessione, 'execute'):
                return 'sqlite'
        except AttributeError:
            pass
        # Aggiungi qui altri DBMS se necessario
        return 'unknown'

    def get_primary_key_column_name(self, connessione, table_name):
        db_type = self.get_db_type(connessione)
        print(db_type)
        if db_type == 'sqlite':
            query = f"PRAGMA table_info({table_name})"
            self.cursor.execute(query)

            columns_info = self.cursor.fetchall()
            print(columns_info)  # Stampa per debug
            for col in columns_info:
                print(col)  # Stampa ogni colonna per debug
                if col[5] == 1:
                    return col[1]

        elif db_type == 'postgresql':
            query = f"""
            SELECT a.attname
            FROM   pg_index i
            JOIN   pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE  i.indrelid = '{table_name}'::regclass
            AND    i.indisprimary;
            """
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            if result:
                return result[0]
        else:
            raise Exception(f"DBMS non supportato: {db_type}")

        raise Exception(f"Non è stato possibile trovare la colonna indice per la tabella {table_name}")

    def salva_database(self):
        if self.connessione is not None:
            self.cursor = self.connessione.cursor()
            table_name = self.lista_tabelle.currentText()

            # Ottieni il nome della colonna indice per la tabella corrente
            id_column_name = self.get_primary_key_column_name(self.connessione, table_name)

            for row_num in range(self.tabella.rowCount()):
                row_data = []
                for col_num in range(self.tabella.columnCount()):
                    item = self.tabella.item(row_num, col_num)
                    if item is not None:
                        row_data.append(item.text())
                    else:
                        row_data.append(None)

                id_value = row_data[self.colonne.index(id_column_name)]

                # Costruisci la parte SET della query
                set_query_parts = [f"{self.colonne[i]}=?" for i in range(len(self.colonne)) if
                                   self.colonne[i] != id_column_name]
                query_values = [row_data[i] for i in range(len(row_data)) if self.colonne[i] != id_column_name]

                # Adatta la query per il tipo di database
                db_type = self.get_db_type(self.connessione)
                if db_type == "postgresql":
                    set_query_parts = [f"{self.colonne[i]}=%s" for i in range(len(self.colonne)) if
                                       self.colonne[i] != id_column_name]

                set_query = ', '.join(set_query_parts)
                query = f"UPDATE {table_name} SET {set_query} WHERE {id_column_name}=?"
                if db_type == "postgresql":
                    query = f"UPDATE {table_name} SET {set_query} WHERE {id_column_name}=%s"

                try:
                    # Esegui la query
                    self.cursor.execute(query, query_values + [id_value])
                    self.connessione.commit()
                except Exception as e:
                    self.connessione.rollback()
                    print(f"Errore nell'aggiornamento del record con {id_column_name}={id_value}: {e}")

            self.show_info('Saved')


        # Gestione del salvataggio CSV omessa per brevità

        elif self.connessione is None and self.lista_tabelle.currentText().endswith('.csv'):
            # Salva le modifiche nel file CSV
            with open(self.name_csv, 'w', newline='') as file:
                writer = csv.writer(file)
                for i in range(self.tabella.rowCount()):
                    row = [self.tabella.item(i, j).text() if self.tabella.item(i, j) is not None else '' for j in
                           range(self.tabella.columnCount())]
                    writer.writerow(row)
            self.show_info('CSV file saved')

        else:
            self.show_info('No changed data')

    def salva_come(self):
        """
        Fa una copia del db.
        :return:
        """
        self.show_info(f"This function is used to make a copy of the sqlite db." 
                       f"So it only works if you have loaded a sqlite db. " 
                       f"'\n' to save the csv table use the 'Export' function, or if you need to save a postgres db "
                       f"use the save function")
        if self.connessione is not None:
            # Selezione del file di output tramite QFileDialog
            new_db_path, _ = QFileDialog.getSaveFileName(None, "Salva copia come", "", "Database SQLite (*.sqlite)")

            # Copia del file del database originale nel nuovo percorso
            shutil.copy2(self.nome_file, new_db_path)
        else:
            self.show_info(f"This function saves only if you have loaded a sqlite db, " 
                           f"'\n' to save the csv table use the 'Export' function")
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
            output_file, _ = QFileDialog.getSaveFileName(None, "Export in CSV", "", "CSV (*.csv)")

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
            output_file, _ = QFileDialog.getSaveFileName(None, "Export in CSV", "", "CSV (*.csv)")

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

    def translate_google(self, item, translator, in_l, out_l):

        if item is not None and item.text() != '':
            testo = item.text()
            try:
                traduzione = translator.translate(testo, src=in_l, dest=out_l).text

                item.setText(traduzione)
            except Exception as e:
                print(f"Errore durante la traduzione con Google Translate: {e}")
                # Qui puoi decidere di loggare l'errore, mostrare un messaggio all'utente, o altro.

    def translate_deepl(self,item,auth_key,out_l):

        if item is not None and item.text() != '':
            testoq = item.text()
            translator_td = tr_d(auth_key)
            trad = translator_td.translate_text(testoq, target_lang=out_l).text


            item.setText(trad)

    import time

    def translate_libretranslate(self, item, source_lang, target_lang):
        if item is not None and item.text() != '':
            try:
                #time.sleep(1)  # Introduce un ritardo di 1 secondo prima della richiesta
                url = "https://libretranslate.de/translate"
                payload = {"q": item.text(), "source": source_lang, "target": target_lang, "format": "text"}
                headers = {"Content-Type": "application/json"}
                response = requests.post(url, json=payload, headers=headers)
                if response.ok:
                    traduzione = response.json().get("translatedText")
                    item.setText(traduzione)
                else:
                    print(f"Translation failed with LibreTranslate, status code: {response.status_code}")
            except Exception as e:
                print(f"Errore durante la traduzione con LibreTranslate: {e}")

    def traduci_dati(self):
        """
        Traduce i dati nelle colonne selezionate e visualizza l'avanzamento utilizzando la barra di avanzamento.
        :return:
        """
        #global language_options, selected_item, selected_item2, t
        try:
            start_time = time.time()

            translator_options = ['libretranslate', 'google', 'deepl']

            selected_l, ok = QInputDialog.getItem(None,
                                                  'Translator type',
                                                  'Select a translator:',
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
                                                         'Input language',
                                                         'Select an input language:',
                                                         list(language_options.values()),
                                                         0,
                                                         False)
                print(list(language_options.values()))
                if not ok:
                    print('No item selected')
                    return

                selected_item2, ok = QInputDialog.getItem(None,
                                                          'Output language',
                                                          'Select an output language:',
                                                          list(language_options.values()),
                                                          0,
                                                          False)
                print(list(language_options.values()))
                if not ok:
                    print('No item selected')
                    return

            if selected_l == 'libretranslate':
                language_options = {'it': 'Italian', 'en': 'English', 'fr': 'French', 'ar': 'Arabic', 'de': 'German',
                                    'es': 'Spanish'}

                selected_item, ok = QInputDialog.getItem(None,
                                                         'Input language',
                                                         'Select an input language:',
                                                         list(language_options.values()),
                                                         0,
                                                         False)
                print(list(language_options.values()))
                if not ok:
                    print('No item selected')
                    return

                selected_item2, ok = QInputDialog.getItem(None,
                                                          'Output language',
                                                          'Select an output language:',
                                                          list(language_options.values()),
                                                          0,
                                                          False)
                print(list(language_options.values()))
                if not ok:
                    print('No item selected')

            if selected_l == 'deepl':
                #self.show_info('By choosing deepl as your translator you just have to choose which language you want to translate into')
                self.translator_deepl = self.apikey_deepl()
                language_options = {'EN-GB': 'English British','EN-US': 'English US', 'IT': 'Italian', 'FR': 'French', 'DE': 'German',
                                    'ES': 'Spanish', 'AR': 'Arabic'}
                # translator_deepl = deepl.Translator(self.apikey_deepl())


                #self.show_info.close()
                selected_item2, ok = QInputDialog.getItem(None,
                                                          'Output language',
                                                          'Select an output language:',
                                                          list(language_options.values()),
                                                          0,
                                                          False)
                print(list(language_options.values()))
                if not ok:
                    print('No item selected')
                    return
            #try:
            in_l = list(language_options.keys())[list(language_options.values()).index(selected_item)]
            #except:
                #pass
            out_l = list(language_options.keys())[list(language_options.values()).index(selected_item2)]
            #print(in_l, out_l)
            self.progress_bar.setRange(0, self.tabella.rowCount())
            self.progress_bar.setValue(0)

            thread_list = []

            translated_columns = []
            #t= None
            # Identifica le colonne selezionate per la traduzione
            colonne_da_tradurre = [j for j, _ in enumerate(
                self.tabella.horizontalHeaderItem(j).text() for j in range(self.tabella.columnCount())) if
                                   self.opzioni_traduzione[self.tabella.horizontalHeaderItem(j).text()].isChecked()]

            for j in colonne_da_tradurre:

                translated_columns.append(self.tabella.horizontalHeaderItem(j).text())
                for i in range(self.tabella.rowCount()):
                    item = self.tabella.item(i, j)

                    # Seleziona il traduttore in base all'opzione scelta dall'utente
                    if selected_l == 'libretranslate':
                        # Chiama direttamente la funzione di traduzione senza usare thread
                        self.translate_libretranslate(item, in_l, out_l)
                        time.sleep(1)  # Introduce una pausa per rispettare i limiti di rate dell'API

                        # Aggiorna la progress bar qui, se necessario
                        self.progress_bar.setValue(i + 1)
                        pct = (i + 1) / self.tabella.rowCount()
                        elapsed_time = time.time() - start_time
                        estimated_time = (elapsed_time * self.tabella.rowCount()) / (i + 1) - elapsed_time
                        self.progress_bar.setTextVisible(True)
                        self.progress_bar.setFormat(
                            f"Line translation {i + 1}/{self.tabella.rowCount()} - column {j + 1}/"
                            f"{self.tabella.columnCount()}\nTime passed: {elapsed_time:.1f}s /"
                            f"Estimated time {estimated_time:.1f}s ({pct:.0%})")
                        self.progress_bar.setAlignment(Qt.AlignCenter)

                    elif selected_l == 'google':
                        tr_google = googletrans.Translator()
                        #tr_google.raise_Exception = False
                        t = threading.Thread(target=self.translate_google, args=(item, tr_google, in_l, out_l))
                        time.sleep(1)
                        thread_list.append(t)
                        # time.sleep(1)
                        t.start()
                    elif selected_l == 'deepl':
                        t = threading.Thread(target=self.translate_deepl, args=(item, self.translator_deepl, out_l))

                        thread_list.append(t)
                        #time.sleep(1)
                        t.start()

                    self.progress_bar.setValue(i + 1)
                    pct = (i + 1) / self.tabella.rowCount()
                    elapsed_time = time.time() - start_time
                    estimated_time = (elapsed_time * self.tabella.rowCount()) / (i + 1) - elapsed_time
                    self.progress_bar.setTextVisible(True)
                    self.progress_bar.setFormat(
                        f"Line translation {i + 1}/{self.tabella.rowCount()} - column {j + 1}/"
                        f"{self.tabella.columnCount()}\nTime passed: {elapsed_time:.1f}s /"
                        f"Estimated time {estimated_time:.1f}s ({pct:.0%})")
                    self.progress_bar.setAlignment(Qt.AlignCenter)

            for t in thread_list:
                t.join()

            self.show_info(
                f"The translation was completed successfully. \n"
                f"They have been translated {i + 1} rows \n"
                f"in the column: {', '.join(translated_columns)}.")

        except Exception as e:
            print(f"Error during translation: {e}")
            self.show_error(f"Error during translation: {str(e)}")
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
                                                     +'Click OK to enter the key', QMessageBox.Ok|QMessageBox.Cancel)
                    if reply==QMessageBox.Ok:

                        api_key, ok = QInputDialog.getText(None, 'Apikey deepl', 'Enter valid apikey:')
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

            api_key, ok = QInputDialog.getText(None, 'Apikey deepl', 'Insert apikey:')
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
        is_valid = self.check_translation(testo_originale, testo_tradotto)
        self.set_validazione_status(is_valid)

    def set_validazione_status(self, is_valid):
        if is_valid:
            self.lbl_validazione.setText("The translation is valid.")
            self.lbl_validazione.setStyleSheet("color: green")
        else:
            self.lbl_validazione.setText("The translation is not valid.")
            self.lbl_validazione.setStyleSheet("color: red")

    def check_translation(self, testo_originale, testo_tradotto):
        # Arbitrary check of translation validity.
        # In a real scenario, this would likely involve more complex logic.
        return testo_originale == testo_tradotto
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
        self.lbl_cerca = QtWidgets.QLabel('Find:')
        self.txt_cerca = QtWidgets.QLineEdit()
        self.lbl_sostituisci = QtWidgets.QLabel('Replace with:')
        self.txt_sostituisci = QtWidgets.QLineEdit()
        self.btn_avvia = QtWidgets.QPushButton('Start')
        self.btn_annulla = QtWidgets.QPushButton('Abort')

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
