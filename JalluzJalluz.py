"""JalluzJalluz 2_0_8
Miro Haltia
miro.haltia@tuni.fi
miro.haltia.mh@gmail.com
TG: @JalluzJalluz

Alkuperäisen, Aleksi Sivosen Visual Basicillä tehdyn JalluzJalluz -sovelluksen
itse tehty versio Pythonilla, käyttäen samaan tapaan local SQL-serveriä
tietojen tallentamiseen Formatia -peliä varten.


Tekoälyä on paljon käytetty tämän toteuttamiseen ajan säästämiseksi. Bugeja
ja muita varmasti löytyy. Ohjelma on rakennettu samalle pohjalle kuin alkuperäinen ja tästä
uudistettu moneen kertaan pidemmälle.

Määritettävät polut löytyvät config-tiedostosta. Tarvittavat pip-asennukset:
PySide6, matplotlib, pyodbc

Yhteydenotot
miro.haltia.mh@gmail.com
@JalluzJalluz
"""
from PySide6.QtWidgets import *
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl, QTimer, QDate, Qt, QRegularExpression, QObject, Signal, QRunnable, QThreadPool, QDateTime, QThread
from PySide6.QtGui import QIcon, QRegularExpressionValidator, QPixmap, QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from matplotlib.ticker import MultipleLocator, FuncFormatter
from collections import Counter, defaultdict
import sys
import time
import pyodbc
from datetime import datetime, timedelta, time as dt_time
import xml.etree.ElementTree as ET
import os
import platform
import numpy as np
from dotenv import load_dotenv
import keyboard
import serial



if getattr(sys, 'frozen', False):
    # If the application is frozen (e.g., bundled by PyInstaller)
    JALLUZ_WORKING_DIR = os.path.dirname(sys.executable)
else:
    # If it's a normal Python script
    JALLUZ_WORKING_DIR = os.path.dirname(os.path.abspath(__file__))

# Ladataan .env-tiedosto, joka sijaitsee samassa kansiossa
load_dotenv(os.path.join(JALLUZ_WORKING_DIR, '.env'))


def lataa_config(config_tiedosto=rf"{JALLUZ_WORKING_DIR}\config.xml"):
    tree = ET.parse(config_tiedosto)
    root = tree.getroot()

    db = root.find("database")
    polut = root.find("paths")

    config = {
        "server": db.find("server").text,
        "database_name": db.find("database_name").text,
        "trusted_connection": db.find("trusted_connection").text.lower() == "yes",
        "table_name": db.find("table_name").text,
        "profile_table_name": db.find("profile_table_name").text,
        "icon_path": polut.find("icon").text,
        "game_music": polut.find("game_music").text,
        "interlude_music": polut.find("interlude_music").text,
        "default_table_columns": db.find("default_table_columns").text,
        "rank_olvi": polut.find("rank_olvi").text if polut.find(
            "rank_olvi") is not None else "",
        "rank_pirkka": polut.find("rank_pirkka").text if polut.find(
            "rank_pirkka") is not None else "",
        "rank_coop": polut.find("rank_coop").text if polut.find(
            "rank_coop") is not None else "",
        "rank_sandels": polut.find("rank_sandels").text if polut.find(
            "rank_sandels") is not None else "",
        "bluetooth_com": polut.find("bluetooth_com").text if polut.find(
            "bluetooth_com") is not None else "COM4",
    }
    return config

config = lataa_config()


# SQL-yhteys
server = config['server']
database = config["database_name"]
trusted = "yes" if config["trusted_connection"] else "no"
table = config["table_name"]
profile_table = config["profile_table_name"]
(winner1, winner2, loser1, loser2, game_time, game_date, under_table,
 winner_side, drink1,
 drink2, drink3, drink4, comment) = config["default_table_columns"].split(",")

connection_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={config['server']};"
    f"DATABASE={config['database_name']};"
    f"Trusted_Connection={'yes' if config['trusted_connection'] else 'no'};"
)

print(connection_string)

def muodosta_yhteys(connection_string, splash=None, max_yritykset=5, viive=3):
    for i in range(1, max_yritykset + 1):
        try:
            if splash:
                splash.paivita_tila(f"Odotetaan SQL Serveriä... (Yritys {i}/{max_yritykset})", int((i/max_yritykset)*50))
            
            # Lyhennetään timeouttia (esim. 5 sekuntia), ettei UI jäädy yhdessä yrityksessä ikuisuudeksi
            yhteys = pyodbc.connect(connection_string, timeout=5) 
            
            if splash:
                splash.paivita_tila("Tietokantayhteys muodostettu!", 90)
            return yhteys
            
        except Exception as e:
            if i < max_yritykset:
                if splash:
                    splash.paivita_tila(f"Tietokanta ei ole vielä valmis. Odotetaan {viive} sekuntia...")
                
                # Odotetaan viive, mutta pidetään latausikkunan animaatio pyörimässä
                for _ in range(viive * 10):
                    time.sleep(0.1)
                    if splash:
                        QApplication.processEvents()
            else:
                if splash:
                    splash.paivita_tila("Yhteys epäonnistui lopullisesti.", 100)
                raise

conn = None


def on_windows11():
    if platform.system() != "Windows":
        return False
    version = platform.version()
    build_number = int(version.split('.')[-1])
    # Windows 11 build number on 22000+
    return build_number >= 22000

def aseta_dark_theme(app):
    dark_theme = """
    QWidget {
        background-color: #1e1e1e;
        color: #ffffff;
    }

    QPushButton {
        background-color: #2b2b2b;
        color: #ffffff;
        border: 1px solid #3e3e42;
        padding: 5px;
    }

    QPushButton:hover {
        background-color: #3a3a3a;
    }

    QLineEdit, QSpinBox, QDateEdit {
        background-color: #2b2b2b;
        color: #ffffff;
        border: 1px solid #3e3e42;
    }

    QCheckBox, QRadioButton {
        color: #ffffff;
    }

    QTableWidget {
        background-color: #2b2b2b;
        color: #ffffff;
        gridline-color: #3e3e42;
    }

    QHeaderView::section {
        background-color: #2b2b2b;
        color: #ffffff;
        border: 1px solid #3e3e42;
    }

    QScrollBar:vertical {
        background: #2b2b2b;
        width: 10px;
    }

    QScrollBar::handle:vertical {
        background: #3e3e42;
    }

    QDialog {
        background-color: #1e1e1e;
    }

    QLabel {
        color: #ffffff;
    }
    """
    app.setStyleSheet(dark_theme)

def hae_pelaajat_kannasta():
    """
    Hakee pelaajien nimet ja pelimäärät profiilitaulusta (profile_table),
    järjestää eniten pelanneet ensimmäiseksi ja palauttaa:
        - pelaajat: lista nimistä (lowercase) QCompleteria varten
        - pelaaja_pelit: dict {nimi: pelit}
    """
    try:
        with conn.cursor() as cur:
            sql = f"""
                SELECT
                    LOWER(LTRIM(RTRIM(Nimi))) AS Nimi,
                    Pelit
                FROM {profile_table}
                WHERE Nimi IS NOT NULL AND Nimi <> ''
                ORDER BY Pelit DESC, Nimi ASC;
            """
            cur.execute(sql)
            rows = cur.fetchall()

        pelaajat = [row[0] for row in rows]                  # lista completerille
        pelaaja_pelit = {row[0]: int(row[1]) for row in rows}  # nimi -> pelit

        return pelaajat, pelaaja_pelit

    except Exception as e:
        print("Virhe hae_pelaajat_kannasta():", e)
        return [], {}



def aseta_autocomplete(input_fields, pelaajat, parent=None):
    completer = QCompleter(pelaajat, parent)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchStartsWith)
    completer.setCompletionMode(QCompleter.PopupCompletion)

    for field in input_fields:
        field.setCompleter(completer)

        def update_completion_prefix(text, comp=completer):
            comp.setCompletionPrefix(text)
            comp.complete()

        field.textEdited.connect(update_completion_prefix)


def format_seconds(seconds):
    """Muuntaa sekunnit muotoon mm:ss."""
    if seconds is None: return "--:--"
    mm = int(seconds // 60)
    ss = int(seconds % 60)
    return f"{mm:02d}:{ss:02d}"


class WorkerSignals(QObject):
    """Signaalit, joilla Worker kommunikoi UI-säikeen kanssa."""
    results = Signal(list)
    error = Signal(str)

class DatabaseWorker(QRunnable):
    """Työntekijä, joka suorittaa SQL-kyselyn taustalla."""
    def __init__(self, query, params):
        super().__init__()
        self.query = query
        self.params = params
        self.signals = WorkerSignals()

    def run(self):
        try:
            # Luodaan uusi yhteys worker-säikeeseen (pyodbc vaatii oman yhteyden per säie)
            worker_conn = pyodbc.connect(connection_string, timeout=10)
            worker_cursor = worker_conn.cursor()
            worker_cursor.execute(self.query, self.params)
            results = worker_cursor.fetchall()
            # Muutetaan tulokset listoiksi, jotta ne ovat helpommin käsiteltävissä
            data = [list(r) for r in results]
            worker_conn.close()
            self.signals.results.emit(data)
        except Exception as e:
            self.signals.error.emit(str(e))

class HotkeySignal(QObject):
    """Signaali, jolla keyboard-kirjaston taustasäie keskustelee PySide6:n kanssa turvallisesti."""
    pressed = Signal()

class SerialWorker(QThread):
    """Taustasäie, joka kuuntelee Bluetooth-sarjaporttia jäätämättä käyttöliittymää."""
    nappi_painettu = Signal()

    def __init__(self, portti="COM4", baudrate=9600):
        super().__init__()
        self.portti = portti
        self.baudrate = baudrate
        self.running = True

    def run(self):
        try:
            with serial.Serial(self.portti, self.baudrate, timeout=1) as ser:
                while self.running:
                    # Jos sarjaportissa on luettavaa dataa
                    if ser.in_waiting > 0:
                        rivi = ser.readline().decode('utf-8', errors='ignore').strip()
                        if rivi == "JALLUZ_PAINETTU":
                            self.nappi_painettu.emit()
        except Exception as e:
            print(f"Sarjaporttia {self.portti} ei saatu auki tai yhteys katkesi: {e}")

    def stop(self):
        self.running = False
        self.wait()

class Latausikkuna(QWidget):
    """Photoshop-tyylinen latausikkuna, joka näytetään ohjelman käynnistyessä."""
    def __init__(self, kuva_polku):
        super().__init__()
        # Kehyksetön ikkuna, pysyy päällimmäisenä ja toimii splash-ikkunana
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Kuva
        self.kuva_label = QLabel()
        self.kuva_label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(kuva_polku)
        if not pixmap.isNull():
            # Skaalataan hieman isommaksi, jos käytät pientä ikonia
            self.kuva_label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        # Tilateksti
        self.info_label = QLabel("Käynnistetään ohjelmaa...")
        self.info_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        self.info_label.setAlignment(Qt.AlignCenter)
        
        # Edistymispalkki
        self.progress = QProgressBar()
        self.progress.setRange(0, 0) # 0,0 tekee palkista sahaavan latausanimoinnin
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        
        layout.addWidget(self.kuva_label)
        layout.addSpacing(10)
        layout.addWidget(self.info_label)
        layout.addWidget(self.progress)
        self.setLayout(layout)
        
        # Tumma teema latausikkunaan
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 2px solid #3e3e42;
            }
            QProgressBar {
                background-color: #2b2b2b;
                border: 1px solid #3e3e42;
            }
            QProgressBar::chunk {
                background-color: #007acc;
            }
        """)

    def paivita_tila(self, teksti, edistys=None):
        """Päivittää tekstiä ja pakottaa ikkunan piirtämään itsensä uudelleen."""
        self.info_label.setText(teksti)
        if edistys is not None:
            self.progress.setRange(0, 100)
            self.progress.setValue(edistys)
        QApplication.processEvents() # Tämä on tärkeä: pakottaa käyttöliittymän päivittymään!


class AjanottoGUI(QWidget):
    """Pääohjelma, joka aukeaa ensimmäisenä. Mahdollisuus ajanottoon,
    pysäyttämiseen, jatkamiseen, pelaajien nimien kirjoittamiseen,
    voittajajoukkueen valitsemiseen, häviäjien pöydän alle merkitsemiseen.
    Lisäksi napit tilastoihin, valintojen resetoimiseen, pelin tallentamiseen,
    halutun pelinimen tarkastamiseen, sekä napit välimusiikin soittamiseen
    (vain kun mitään tietoja ei ole vielä syötetty / reset nappia painettu),
    sekä help-nappi ja profiilien tarkastelunappi.
    """

    def __init__(self):
        """Luodaan aloitusikkuna"""

        super().__init__()
        self.setWindowTitle("JalluzJalluz 2.0.8")

        # Ikkunan leveys ja korkeus
        self.resize(330, 600)

        # Alussa alkuaika pois, peli pois päältä ja kulunut peliaika 0
        self.start_time = None
        self.running = False
        self.total_elapsed = 0
        self.result = QLabel("Peliä ei ole vielä tallennettu")
        empty_label = QLabel("")

        # Sallitut merkit
        regex = QRegularExpression(r"^[a-öA-Ö0-9@ .?!()\-]{0,20}$")
        validator = QRegularExpressionValidator(regex)

        # Pelaaja -kentät
        self.a1_input = QLineEdit()
        self.a1_input.setPlaceholderText("Ikkunaseinä - Pelaaja 1")
        self.a1_input.textChanged.connect(self.tarkista_voiko_tallentaa)
        self.a1_input.setValidator(validator)
        self.a2_input = QLineEdit()
        self.a2_input.setPlaceholderText("Ikkunaseinä - Pelaaja 2")
        self.a2_input.textChanged.connect(self.tarkista_voiko_tallentaa)
        self.a2_input.setValidator(validator)
        self.b1_input = QLineEdit()
        self.b1_input.setPlaceholderText("Julisteseinä - Pelaaja 1")
        self.b1_input.textChanged.connect(self.tarkista_voiko_tallentaa)
        self.b1_input.setValidator(validator)
        self.b2_input = QLineEdit()
        self.b2_input.setPlaceholderText("Julisteseinä - Pelaaja 2")
        self.b2_input.textChanged.connect(self.tarkista_voiko_tallentaa)
        self.b2_input.setValidator(validator)

        # Expert-tila checkbox
        self.expert_checkbox = QCheckBox("Ranked-tila")
        self.expert_checkbox.stateChanged.connect(self.toggle_expert)

        # Juomapudotusvalikot (alussa piilotettu)
        self.juoma_options = ["...", "Kalja", "Vichy", "Hard Seltzer", "Siideri", "Lonkero", "Limsa", "Energiajuoma", "Muu"]
        self.a1_juoma = QComboBox();
        self.a1_juoma.addItems(self.juoma_options);
        self.a1_juoma.setVisible(False)
        self.a2_juoma = QComboBox();
        self.a2_juoma.addItems(self.juoma_options);
        self.a2_juoma.setVisible(False)
        self.b1_juoma = QComboBox();
        self.b1_juoma.addItems(self.juoma_options);
        self.b1_juoma.setVisible(False)
        self.b2_juoma = QComboBox();
        self.b2_juoma.addItems(self.juoma_options);
        self.b2_juoma.setVisible(False)

        # Kommentti-kenttä
        self.comment_label = QLabel("Kommentti (max 50 merkkiä):")
        self.comment_label.setMinimumHeight(30)
        self.comment_edit = QLineEdit()
        self.comment_edit.setMaxLength(50)
        self.comment_edit.setFixedHeight(40)
        self.comment_edit.setPlaceholderText(
            "Miten meni?...")
        self.comment_label.setVisible(False)
        self.comment_edit.setVisible(False)

        # Voittajatiimin valinta
        self.winner_label = QLabel("Kumpi tiimi voitti?")
        self.radio_teamA = QRadioButton("Tiimi Ikkunaseinä")
        self.radio_teamA.toggled.connect(self.tarkista_voiko_tallentaa)
        self.radio_teamB = QRadioButton("Tiimi Julisteseinä")
        self.radio_teamB.toggled.connect(self.tarkista_voiko_tallentaa)
        self.winner_group = QButtonGroup()
        self.winner_group.addButton(self.radio_teamA)
        self.winner_group.addButton(self.radio_teamB)

        # Häviäjät pöydän alle -nappi
        self.game_under_table = QCheckBox("Pöydän alla")

        # Aikanäyttö
        self.info = QLabel("Ranked-tila ei käytössä")
        self.label = QLineEdit("00:00")
        self.label.setStyleSheet("QLineEdit { font-size: 18px; }")
        self.label.setReadOnly(False)

        # Pelinvetäjän tarkastuskenttä
        self.gamemaster_input = QLineEdit()
        self.gamemaster_input.setPlaceholderText("Pelinvetäjä")
        self.gamemaster_input.setMaxLength(50)
        self.gamemaster_input.setVisible(False) # Piilotettu oletuksena

        # Pelinimen tarkastuskenttä
        self.pelinimi_label = QLabel("Tarkista kelvollinen pelinimi:")
        self.pelinimi_input = QLineEdit()
        self.pelinimi_tarkistus = QLabel("")

        # Pelin käyttönapit
        self.btn_start = QPushButton("Start")
        self.btn_pause = QPushButton("Stop")
        self.btn_continue = QPushButton("TÖHÖ")
        self.btn_continue.setEnabled(False)
        self.btn_save = QPushButton("Save")
        self.btn_save.setEnabled(False)
        self.btn_stats = QPushButton("Tilastot")
        self.btn_reset = QPushButton("Reset")

        # Nappien yhdistys attribuutteihin
        self.btn_start.clicked.connect(self.start)
        self.btn_pause.clicked.connect(self.stop)
        self.btn_continue.clicked.connect(self.continue_)
        self.btn_save.clicked.connect(self.save)
        self.btn_stats.clicked.connect(self.avaa_tilastot)
        self.btn_reset.clicked.connect(self.reset_toiminto)
        self.pelinimi_input.textChanged.connect(self.tarkista_pelinimi)

        # Ajastin
        self.timer = QTimer()
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.paivita_aika)

        # Mutenappi
        self.mute_button = QPushButton("Välimusiikki 🔇")
        self.mute_button.clicked.connect(self.toggle_mute)

        # help- ja profiilinapit
        help_button = QPushButton("Help")
        help_button.clicked.connect(self.avaa_help)
        profiili_button = QPushButton("Profiilit")
        profiili_button.clicked.connect(self.avaa_profiilit)

        # Layout
        layout = QVBoxLayout()

        # Tiimi Ikkunaseinä
        layout.addWidget(QLabel("Tiimi Ikkunaseinä:"))

        # Pelaaja 1 rivi
        a1_layout = QHBoxLayout()
        a1_layout.addWidget(self.a1_input)
        a1_layout.addWidget(self.a1_juoma)
        layout.addLayout(a1_layout)

        # Pelaaja 2 rivi
        a2_layout = QHBoxLayout()
        a2_layout.addWidget(self.a2_input)
        a2_layout.addWidget(self.a2_juoma)
        layout.addLayout(a2_layout)

        # Tiimi Julisteseinä
        layout.addWidget(QLabel("Tiimi Julisteseinä:"))

        # Pelaaja 1 rivi
        b1_layout = QHBoxLayout()
        b1_layout.addWidget(self.b1_input)
        b1_layout.addWidget(self.b1_juoma)
        layout.addLayout(b1_layout)

        # Pelaaja 2 rivi
        b2_layout = QHBoxLayout()
        b2_layout.addWidget(self.b2_input)
        b2_layout.addWidget(self.b2_juoma)
        layout.addLayout(b2_layout)

        # --- Expert: todennäköisyysnappi ja tuloslabel (näkyy vain expert-tilassa)
        prob_layout = QHBoxLayout()

        self.btn_prob_calc = QPushButton("Laske\nkertoimet")
        self.btn_prob_calc.setToolTip(
            "Laskee Ikkunaseinä vs. Julisteseinä -voittotodennäköisyyden nykyisistä Felo-arvoista"
        )
        self.btn_prob_calc.setFixedHeight(
            40)  # tekee napista 2 rivin korkuisen
        self.btn_prob_calc.setSizePolicy(QSizePolicy.Preferred,
                                         QSizePolicy.Expanding)
        self.btn_prob_calc.clicked.connect(self.laske_todennakoisyys_elosta)

        self.prob_label = QLabel("")
        self.prob_label.setWordWrap(True)
        self.prob_label.setMinimumWidth(50)
        self.prob_label.setMinimumHeight(80)
        self.prob_label.setStyleSheet("color:#ddd; padding-left:8px;")
        self.prob_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # aluksi piilossa (vain expert-tilassa)
        self.btn_prob_calc.setVisible(False)
        self.prob_label.setVisible(False)
        self.btn_prob_calc.setEnabled(False)

        prob_layout.addWidget(self.btn_prob_calc, 0)
        prob_layout.addWidget(self.prob_label,
                              1)  # label nappiin nähden oikealle

        layout.addLayout(prob_layout)

        # päivitys: kun nimiä muokataan, päivitä mahdollisuus laskea
        for w in (self.a1_input, self.a2_input, self.b1_input, self.b2_input):
            w.textChanged.connect(self._paivita_prob_napin_tila)

        # Aika ja kupin kaato
        self.timer_layout = QHBoxLayout()
        self.btn_kuppi_nurin = QPushButton("Kuppi nurin\n (+40s)")
        self.btn_kuppi_nurin.clicked.connect(self.lisaa_aikaa)
        self.btn_kuppi_nurin.setEnabled(False)
        self.kaadetut_kupit = 0
        layout.addWidget(QLabel("Aika:"))
        self.timer_layout.addWidget(self.label)
        self.timer_layout.addWidget(self.btn_kuppi_nurin)
        self.label.setFixedHeight(40)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addLayout(self.timer_layout)
        layout.addWidget(self.info)
        layout.addWidget(self.gamemaster_input)

        # Start / Continue / Stop
        start_continue_stop_layout = QHBoxLayout()
        self.btn_start.setFixedHeight(60)
        self.btn_continue.setFixedHeight(30)
        self.btn_pause.setFixedHeight(60)
        start_continue_stop_layout.addWidget(self.btn_start)
        start_continue_stop_layout.addWidget(self.btn_continue)
        start_continue_stop_layout.addWidget(self.btn_pause)
        layout.addLayout(start_continue_stop_layout)


        # Voittajan valinta ja pöydän alla, kommentti
        winner_comment_layout = QHBoxLayout()

        comment_layout = QVBoxLayout()
        comment_layout.addWidget(self.comment_label)
        comment_layout.addWidget(self.comment_edit)

        winner_layout = QVBoxLayout()
        winner_layout.addWidget(self.winner_label)
        winner_layout.addWidget(self.radio_teamA)
        winner_layout.addWidget(self.radio_teamB)
        winner_layout.addWidget(self.game_under_table)
        winner_layout.setSpacing(6)
        winner_layout.setContentsMargins(0, 0, 0, 6)

        winner_comment_layout.addLayout(winner_layout)
        winner_comment_layout.addLayout(comment_layout)

        layout.addLayout(winner_comment_layout)

        # Save, Reset ja tuloslabel
        self.btn_save.setFixedHeight(40)
        layout.addWidget(self.btn_save)
        layout.addWidget(self.result)
        self.btn_reset.setFixedHeight(30)
        layout.addWidget(self.btn_reset)
        layout.addWidget(empty_label)

        # Pelinimi ja tarkistus
        layout.addWidget(self.pelinimi_label)
        layout.addWidget(self.pelinimi_input)
        layout.addWidget(self.pelinimi_tarkistus)

        # Mutenappi
        layout.addWidget(self.mute_button)

        # Tilasto- ja profiilinapit
        stats_layout = QHBoxLayout()
        stats_layout.addWidget(self.btn_stats)
        stats_layout.addWidget(profiili_button)
        layout.addLayout(stats_layout)

        #Help- ja Expert-nappi
        last_layout = QHBoxLayout()
        last_layout.addWidget(help_button)
        last_layout.addWidget(self.expert_checkbox)
        layout.addLayout(last_layout)

        self.setLayout(layout)

        # Pelimusiikki
        self.pelimusiikki_player = QMediaPlayer()
        self.pelimusiikki_audio = QAudioOutput()
        self.pelimusiikki_player.setAudioOutput(self.pelimusiikki_audio)
        self.pelimusiikki_player.setLoops(-1)
        self.pelimusiikki_player.setSource(
            QUrl.fromLocalFile(config["game_music"]))

        # Välimusiikki
        self.valimusiikki_player = QMediaPlayer()
        self.valimusiikki_audio = QAudioOutput()
        self.valimusiikki_player.setAudioOutput(self.valimusiikki_audio)
        self.valimusiikki_player.setSource(
            QUrl.fromLocalFile(config["interlude_music"]))
        self.valimusiikki_audio.setMuted(True)
        self.valimusiikki_player.setLoops(-1)
        self.valimusiikki_player.play()

        # Autocomplete
        self.pelaajat, self.pelaaja_pelit = hae_pelaajat_kannasta()
        aseta_autocomplete(
            [self.a1_input, self.a2_input, self.b1_input, self.b2_input, self.gamemaster_input],
            self.pelaajat, self)

        self.juhlapeli_label = QLabel()
        self.juhlapeli_label.setWordWrap(True)
        self.juhlapeli_label.setStyleSheet("color:#bbb; padding:6px 4px;")
        layout.addWidget(self.juhlapeli_label)
        self.paivita_juhlapeli_ilmoitus()

        # Tilasto- ja profiili-ikkunat
        self.kaikki_tilastot = []
        self.aktiiviset_profiili_ikkunat = []
        self.aktiiviset_help_ikkunat = []

        self.expert_checkbox.setChecked(True)

        self.viimeisin_painallus = 0
        self.aikalukko_sekunteina = 0.5  # estää vahingossa useamman painalluksen  

        # USB-näppäimistön (F13) kuuntelu
        self.hotkey_signal = HotkeySignal()
        self.hotkey_signal.pressed.connect(self.nappia_painettu_vastaanotettu)
        keyboard.add_hotkey('f13', self.hotkey_signal.pressed.emit)

        # Bluetooth-sarjaportin kuuntelu taustasäikeessä
        # Voit määrittää COM-portin .env-tiedostossa, esim: BLUETOOTH_COM="COM4"
        com_portti = config.get("bluetooth_com", "COM4")
        self.serial_worker = SerialWorker(portti=com_portti)
        self.serial_worker.nappi_painettu.connect(self.nappia_painettu_vastaanotettu)
        self.serial_worker.start()

    def toggle_expert(self, state):
        """Näytetään tai piilotetaan juomapudotusvalikot + todennäköisyysnappi/label"""
        on = (state == 2)
        self.a1_juoma.setVisible(on)
        self.a2_juoma.setVisible(on)
        self.b1_juoma.setVisible(on)
        self.b2_juoma.setVisible(on)
        # todennäköisyysnapin ja labelin näkyvyys
        self.btn_prob_calc.setVisible(on)
        self.prob_label.setVisible(on)
        # päivitä napin enable-tila jos näkyvissä
        self._paivita_prob_napin_tila()
        # Kommenttikenttä näkyviin
        self.comment_label.setVisible(on)
        self.comment_edit.setVisible(on)
        self.gamemaster_input.setVisible(on)
        if on:
            self.info.setText("Ranked-tila käytössä")
        else:
            self.info.setText("Ranked-tila ei käytössä")
        self.update()

    def _paivita_prob_napin_tila(self):
        """Aktivoi todennäköisyysnapin vain kun kaikki neljä nimeä on annettu."""
        kaikki_nimet = all([
            self.a1_input.text().strip(),
            self.a2_input.text().strip(),
            self.b1_input.text().strip(),
            self.b2_input.text().strip()
        ])
        self.btn_prob_calc.setEnabled(
            bool(kaikki_nimet) and self.btn_prob_calc.isVisible())

    def laske_todennakoisyys_elosta(self):
        """Laskee Ikkunaseinä vs. Julisteseinä voittotodennäköisyydet ja Felo-muutokset."""
        a1 = self.a1_input.text().strip().lower()
        a2 = self.a2_input.text().strip().lower()
        b1 = self.b1_input.text().strip().lower()
        b2 = self.b2_input.text().strip().lower()

        if not all([a1, a2, b1, b2]):
            QMessageBox.warning(self, "Puuttuvia tietoja",
                                "Syötä ensin kaikkien neljän pelaajan nimet.")
            return

        try:
            # Hae Felot kannasta
            names = [a1, a2, b1, b2]
            plhs = ",".join("?" for _ in names)
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT Nimi, Felo FROM {profile_table} WHERE Nimi IN ({plhs})",
                    names)
                felo_map = {(n or "").strip().lower(): float(f or 1500.0) for
                            n, f
                            in cur.fetchall()}

            Ra1 = felo_map.get(a1, 1500.0)
            Ra2 = felo_map.get(a2, 1500.0)
            Rb1 = felo_map.get(b1, 1500.0)
            Rb2 = felo_map.get(b2, 1500.0)

            # Tiimin keskiarvo Eloista
            R_ikkuna = (Ra1 + Ra2) / 2.0
            R_juliste = (Rb1 + Rb2) / 2.0

            # 1. Odotusarvot (Winning Probability)
            diff = (R_juliste - R_ikkuna) / 400.0
            from_pow = pow(10.0, diff)
            p_ikkuna = 1.0 / (1.0 + from_pow)
            p_juliste = 1.0 - p_ikkuna

            # 2. Kertoimet: 1/p
            k_ikkuna = 1.0 / p_ikkuna if p_ikkuna > 0 else float('inf')
            k_juliste = 1.0 / p_juliste if p_juliste > 0 else float('inf')

            # 3. Felo-muutos (Delta)
            K_FACTOR = 10

            # LASKETAAN VOITOT (Nämä ovat positiivisia lukuja)
            # Jos Ikkuna (suosikki) voittaa, (1 - p_ikkuna) on pieni luku -> Pieni voitto
            win_ikkuna_delta = round(K_FACTOR * (1 - p_ikkuna), 2)

            # Jos Juliste (altavastaaja) voittaa, (1 - p_juliste) on iso luku -> Iso voitto
            win_juliste_delta = round(K_FACTOR * (1 - p_juliste), 2)

            # --- KORJAUS TÄSSÄ ---
            # Häviö on nollasummapeliä.
            # Jos Ikkuna häviää, se tarkoittaa että Juliste voitti.
            # Ikkuna menettää tismalleen sen verran pisteitä, kuin Juliste saa.

            lose_ikkuna_delta = -win_juliste_delta  # Suosikki häviää paljon
            lose_juliste_delta = -win_ikkuna_delta  # Altavastaaja häviää vähän

            # Tulostus
            self.prob_label.setText(
                f"<b>Ikkunaseinä:</b> {p_ikkuna * 100:.1f}%  (kerroin {k_ikkuna:.2f})<br>"
                f"Felo Voitolla: <font color='green'>+"
                f"{win_ikkuna_delta:.2f}</font> | "
                f"Häviöllä: <font color='red'>{lose_ikkuna_delta:.2f}</font><br><br>"

                f"<b>Julisteseinä:</b> {p_juliste * 100:.1f}%  (kerroin {k_juliste:.2f})<br>"
                f"Felo Voitolla: <font color='green'>+{
                win_juliste_delta:.2f}</font> | "
                f"Häviöllä: <font color='red'>{lose_juliste_delta:.2f}</font>"
            )

        except Exception as e:
            QMessageBox.critical(self, "Virhe",
                                 f"Todennäköisyyden lasku epäonnistui:\n{e}")

    def start(self):
        """Aloittaa pelin

        """
        # Aloitusaika on painamishetkellä kellonaika sekunnin tarkkuudella
        self.start_time = time.time()

        # Estetään ajan muuttaminen pelin ollessa käynnissä ja start,
        # sekä töhö napin käyttö
        self.label.setReadOnly(True)
        self.btn_start.setEnabled(False)
        self.btn_continue.setEnabled(False)

        # Peli käynnistyy
        self.running = True

        #Kulunut aika alkuun 0
        self.total_elapsed = 0

        #Aloittaa ajastimen
        self.timer.start()
        self.info.setText("Ajanotto käynnissä...")

        # Pysäytetään välimusiikki
        self.valimusiikki_player.stop()
        self.valimusiikki_audio.setMuted(True)
        self.mute_button.setText("Välimusiikki 🔇")
        self.mute_button.setEnabled(False)

        # Aloitetaan pelimusiikki alusta
        self.pelimusiikki_player.setPosition(0)
        self.pelimusiikki_player.play()

    def stop(self):
        """Pysäyttää pelin

        :return:
        """
        if self.running:
            now = time.time()
            self.total_elapsed += now - self.start_time
            self.running = False
            self.timer.stop()
            self.label.setReadOnly(False)
            self.info.setText("Ajanotto pysäytetty. Voit Muokata aikaa.")
            self.pelimusiikki_player.stop()
            self.tarkista_voiko_tallentaa()
            self.stopped_time = time.time()
            self.btn_kuppi_nurin.setEnabled(True)
            self.btn_continue.setEnabled(True)

    def continue_(self):
        """Jatkaa peliä, jos vahingossa pysäytetty liian aikaisin.
        Muokkausehdotus: ota huomioon myös pysäytetty aika.


        """
        # Virheilmoitus, jos ajanotto on jo päällä
        if self.running:
            QMessageBox.information(self, "Tieto", "Ajanotto on jo käynnissä.")
            return

        # Tai peliä ei ole vielä aloitettukkaan
        if self.total_elapsed < 1:
            QMessageBox.warning(self, "Virhe",
            "Aloita peli ensin.")
            return

        # Jatketaan peliä ja lisätään pysähtyneenä ollut aika
        now = time.time()
        self.total_elapsed += now - self.stopped_time
        self.start_time = now
        self.running = True
        self.timer.start()
        self.label.setReadOnly(True)
        self.info.setText("Ajanotto jatkuu...")
        self.pelimusiikki_player.play()
        self.tarkista_voiko_tallentaa()
        self.btn_kuppi_nurin.setEnabled(False)
        self.btn_continue.setEnabled(False)

    def nappia_painettu_vastaanotettu(self):
        """Ottaa vastaan signaalin sekä F13-näppäimestä että Bluetooth-sarjaportista."""
        nykyinen_aika = time.time()
        
        # Tarkistetaan, onko edellisestä kerrasta kulunut yli x sekunttia
        if nykyinen_aika - self.viimeisin_painallus > self.aikalukko_sekunteina:
            self.viimeisin_painallus = nykyinen_aika
            self.start_stop_peli()
        else:
            print("Tuplapainallus estetty aikalukolla (USB ja Bluetooth komento tulivat yhtä aikaa).")

    def start_stop_peli(self):
        """Käsittelee yhden napin logiikan: Start, Stop ja Continue (TÖHÖ)."""
        # Jos peli on jo tallennettu, nappi ei tee enää mitään ennen resettiä
        onko_tallennettu = "tallennettu onnistuneesti" in self.result.text()
        if onko_tallennettu:
            return

        if self.running:
            # Peli on käynnissä -> Pysäytetään (Stop)
            self.stop()
        else:
            if self.total_elapsed == 0:
                # Peliä ei ole vielä aloitettu -> Aloitetaan (Start)
                if self.btn_start.isEnabled():
                    self.start()
            else:
                # Peli on pysäytetty, mutta aikaa on kulunut -> Jatketaan (TÖHÖ)
                if self.btn_continue.isEnabled():
                    self.continue_()

    def save(self):
        """Tallentaa pelin SQL-tietokantaan. Sallittu vain, jos peli ei ole käynnissä."""

        if self.running:
            QMessageBox.warning(self, "Tallennus estetty",
                                "Peli on vielä käynnissä.\n\nPysäytä peli ennen tallentamista.")
            return

        # Pelaajien nimet
        a1 = self.a1_input.text().strip()
        a2 = self.a2_input.text().strip()
        b1 = self.b1_input.text().strip()
        b2 = self.b2_input.text().strip()

        # Voittajatiimin valinta
        voittaja_valittu = self.radio_teamA.isChecked() or self.radio_teamB.isChecked()

        # Save-nappia ei aktivoida, ennekuin nimet ja voittaja syötetty
        if not all([a1, a2, b1, b2]) or not voittaja_valittu:
            QMessageBox.warning(
                self, "Virhe",
                "Tallennus epäonnistui.\n\nVarmista, että:\n"
                "- Kaikki 4 pelaajan nimeä on syötetty\n"
                "- Voittajatiimi on valittu"
            )
            return

        # Ajan muokkaus
        aika_str = self.label.text()
        try:
            m, s = map(int, aika_str.split(":"))
            if s >= 60 or s < 0 or m < 0:
                raise ValueError
            self.total_elapsed = m * 60 + s
        except ValueError:
            QMessageBox.warning(self, "Virhe",
                                "Aika ei ole oikeassa muodossa (mm:ss).")
            return
        self.result.setText(f"Aika: {aika_str}")
        self.info.setText("Ajanotto lopetettu.")

        # Voittaja ja pöydän alla
        winner = "Tiimi Ikkunaseinä" if self.radio_teamA.isChecked() else "Tiimi Julisteseinä"
        peli_tila = 1 if self.game_under_table.isChecked() else 0
        self.btn_kuppi_nurin.setEnabled(False)
        self.btn_start.setEnabled(True)
        self.btn_continue.setEnabled(False)
        self.radio_teamA.setEnabled(False)
        self.radio_teamB.setEnabled(False)
        self.game_under_table.setEnabled(False)

        # Otetaan pelinvetäjä talteen vain, jos Ranked-tila on päällä
        gamemaster_nimi = None
        if self.expert_checkbox.isChecked():
            gamemaster_nimi = self.gamemaster_input.text().strip()
            if not gamemaster_nimi:
                gamemaster_nimi = None # Varmistetaan, että tyhjä kenttä tallentuu NULL-arvona

        # Tulostetaan pelin tulos
        tulos_msg = (
            f"Tiimi Ikkunaseinä: {a1}, {a2}\n"
            f"Tiimi Julisteseinä: {b1}, {b2}\n\n"
            f"Voittaja: {winner}\n"
            f"Kokonaisaika: {aika_str}\n"
            f"Peli tallennettu onnistuneesti!"
        )
        self.result.setText(tulos_msg)

        # Tallennus SQL Serveriin (juomat ja voittajapuoli lisätään myöhemmin)
        self.tallenna_sql_serveriin(a1, a2, b1, b2, winner, peli_tila, gamemaster_nimi)

        # Juhlapeli-ilmon päivitys
        self.paivita_juhlapeli_ilmoitus()

    def lisaa_aikaa(self):

        if not self.running and hasattr(self, 'total_elapsed'):
            try:
                aika_str = self.label.text()
                m, s = map(int, aika_str.split(":"))
                if s >= 60 or s < 0 or m < 0:
                    raise ValueError
                self.total_elapsed = m * 60 + s
                self.total_elapsed += 40
                self.kaadetut_kupit += 1
                self.label.setText(format_seconds(self.total_elapsed))
                self.btn_continue.setEnabled(False)

            except ValueError:
                QMessageBox.warning(self, "Virhe",
                                    "Aika ei ole oikeassa muodossa (mm:ss).")
                return
            self.info.setText(f"Kuppi kaatunut, aikasakko lisätty (x"
                              f"{self.kaadetut_kupit})")

    def tarkista_voiko_tallentaa(self):
        """Tarkistetaan, voidaanko Save-nappia aktivoida


        """
        nimet_ok = all([
            self.a1_input.text().strip(),
            self.a2_input.text().strip(),
            self.b1_input.text().strip(),
            self.b2_input.text().strip()
        ])
        voittaja_valittu = self.radio_teamA.isChecked() or self.radio_teamB.isChecked()

        self.btn_save.setEnabled(nimet_ok and voittaja_valittu and not self.running)

    def paivita_aika(self):
        """Pelin keston päivittäjä

        """
        if self.running:
            nykyhetki = time.time()
            kulunut = self.total_elapsed + (nykyhetki - self.start_time)
            self.label.setText(format_seconds(kulunut))

    def tallenna_sql_serveriin(self, a1, a2, b1, b2, winner, peli_tila, gamemaster_nimi):
        """Tallennetaan peli SQL-serverille, mukaan lukien juomat (vain expert-tilassa) ja voittajapuoli"""

        pelipvm = datetime.now()  # Päivämäärä ja aika
        kulunut_sekunteina = round(self.total_elapsed)
        kesto = timedelta(seconds=kulunut_sekunteina)

        # Määritetään pelaajien järjestys tallennusta varten
        if winner == "Tiimi Ikkunaseinä":
            pelaaja1 = a1.lower()
            pelaaja2 = a2.lower()
            pelaaja3 = b1.lower()
            pelaaja4 = b2.lower()
            juoma1 = self.a1_juoma.currentText() if self.expert_checkbox.isChecked() else None
            juoma2 = self.a2_juoma.currentText() if self.expert_checkbox.isChecked() else None
            juoma3 = self.b1_juoma.currentText() if self.expert_checkbox.isChecked() else None
            juoma4 = self.b2_juoma.currentText() if self.expert_checkbox.isChecked() else None
            voittopuoli = True
        else:
            pelaaja1 = b1.lower()
            pelaaja2 = b2.lower()
            pelaaja3 = a1.lower()
            pelaaja4 = a2.lower()
            juoma1 = self.b1_juoma.currentText() if self.expert_checkbox.isChecked() else None
            juoma2 = self.b2_juoma.currentText() if self.expert_checkbox.isChecked() else None
            juoma3 = self.a1_juoma.currentText() if self.expert_checkbox.isChecked() else None
            juoma4 = self.a2_juoma.currentText() if self.expert_checkbox.isChecked() else None
            voittopuoli = False

        juoma1 = None if juoma1 == "..." else juoma1
        juoma2 = None if juoma2 == "..." else juoma2
        juoma3 = None if juoma3 == "..." else juoma3
        juoma4 = None if juoma4 == "..." else juoma4


        poydan_alle = int(peli_tila)
        kommentti_teksti = self.comment_edit.text()

        # Muutetaan kesto TIME-muotoon
        kesto_aikana = (datetime.min + kesto).time()

        # SQL-komento: lisätään {drink1}–4 ja Voittaja
        with conn.cursor() as cur:
            sql = f"""
            INSERT INTO {table} 
            ({game_date}, {game_time}, {winner1}, {winner2}, {loser1}, {loser2}, 
            {drink1}, 
            {drink2}, 
            {drink3}, {drink4}, {under_table}, {winner_side}, {comment}, gamemaster)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """


            try:
                cur.execute(sql, (
                    pelipvm, kesto_aikana,
                    pelaaja1, pelaaja2, pelaaja3, pelaaja4,
                    juoma1, juoma2, juoma3, juoma4,
                    poydan_alle, voittopuoli, kommentti_teksti, gamemaster_nimi
                ))
                conn.commit()
                self.btn_save.setEnabled(False)
            except Exception as e:
                QMessageBox.critical(self, "Virhe", f"Virhe tallennettaessa: {e}")

    def avaa_tilastot(self):
        """Tilastojen avaus, lisätään listaan aukiolevista tilastot -ikkunoista

        """
        uusi = TilastotIkkuna()
        self.kaikki_tilastot.append(uusi)
        uusi.show()

    def reset_toiminto(self):
        """Palautetaan alkunäkymään kaikki mahdollinen.


        """
        onko_tallennettu = "tallennettu onnistuneesti" in self.result.text()

        if self.running or (self.total_elapsed > 0 and not onko_tallennettu):
            # Luodaan vahvistusikkuna
            vastaus = QMessageBox.question(
                self,
                "Vahvista nollaus",
                "Peli on käynnissä tai edellistä peliä ei ole tallennettu.\n\nHaluatko varmasti nollata tilanteen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            # Jos käyttäjä vastaa "No", poistutaan funktiosta tekemättä mitään
            if vastaus == QMessageBox.StandardButton.No:
                return

        # Tyhjennä pelaajien nimet
        self.a1_input.clear()
        self.a2_input.clear()
        self.b1_input.clear()
        self.b2_input.clear()

        self.a1_juoma.setCurrentIndex(0)
        self.a2_juoma.setCurrentIndex(0)
        self.b1_juoma.setCurrentIndex(0)
        self.b2_juoma.setCurrentIndex(0)

        self.comment_edit.clear()
        self.gamemaster_input.clear()

        # Poista valinta voittajatiimeistä (radiobuttonit)
        self.winner_group.setExclusive(False)
        self.radio_teamA.setChecked(False)
        self.radio_teamB.setChecked(False)
        self.winner_group.setExclusive(True)

        # Aktivoidaan tiimin valinta uudelleen
        self.radio_teamA.setEnabled(True)
        self.radio_teamB.setEnabled(True)

        # Poista checkbox valinta pöydän alla
        self.game_under_table.setChecked(False)
        self.game_under_table.setEnabled(True)

        # Nollaa timer-arvot ja tilat
        self.start_time = None
        self.total_elapsed = 0
        self.running = False
        self.label.setText("00:00")
        self.btn_kuppi_nurin.setEnabled(False)

        # Pysäytä ajastin jos se on käynnissä
        self.timer.stop()

        # Tyhjennä tiedot ja info-labelit
        if self.expert_checkbox.isChecked():
            self.info.setText("Ranked-tila käytössä")
        else:
            self.info.setText("Ranked-tila ei käytössä")
        self.result.setText("Peliä ei ole vielä tallennettu")

        # Poista Save-napin aktiivisuus ja start nappi aktiiviseksi
        self.btn_save.setEnabled(False)
        self.btn_start.setEnabled(True)
        self.btn_continue.setEnabled(False)

        # Nollataan kaadettujen kuppien määrä
        self.kaadetut_kupit = 0

        # Poistetaan lasketut kertoimet
        self.prob_label.setText("")

        # Pysäytä molemmat musiikit
        self.valimusiikki_player.stop()
        self.pelimusiikki_player.stop()

        # Käynnistä välimusiikki uudelleen mutella
        self.valimusiikki_audio.setMuted(True)
        self.valimusiikki_player.setPosition(0)
        self.valimusiikki_player.play()
        self.mute_button.setEnabled(True)

        # Päivitä juhlapelaajat
        self.paivita_juhlapeli_ilmoitus()

        # Nollaa mute-napin teksti
        self.mute_button.setText("Välimusiikki 🔇")

    def onko_pelaajanimi_kaytossa(self, pelinimi):
        """Tarkistaa löytyykö pelaajanimi profiilitaulusta (profile_table)."""

        pelinimi = pelinimi.strip().lower()
        if not pelinimi:
            return False

        with conn.cursor() as cur:
            sql = f"""
                SELECT TOP 1 1
                FROM {profile_table}
                WHERE LOWER(LTRIM(RTRIM(Nimi))) = ?
            """
            cur.execute(sql, (pelinimi.lower(),))
            return cur.fetchone() is not None

    def tarkista_pelinimi(self):
        """Pelinimen tarkastus laatikko

        :return:
        """
        pelinimi = self.pelinimi_input.text().strip()
        if not pelinimi:
            self.pelinimi_tarkistus.setText("")
            self.tarkista_voiko_tallentaa()
            return

        if self.onko_pelaajanimi_kaytossa(pelinimi):
            self.pelinimi_tarkistus.setText(
                f"Pelinimi '{pelinimi}' on jo käytössä!")
            self.pelinimi_tarkistus.setStyleSheet("color: red;")
            self.btn_save.setEnabled(False)
        else:
            self.pelinimi_tarkistus.setText("Pelinimi on vapaa.")
            self.pelinimi_tarkistus.setStyleSheet("color: green;")
            self.tarkista_voiko_tallentaa()

    def toggle_mute(self):
        """Välimusiikin nappi"""
        nykytila = self.valimusiikki_audio.isMuted()
        uusi_tila = not nykytila
        self.valimusiikki_audio.setMuted(uusi_tila)

        if uusi_tila:
            self.mute_button.setText("Välimusiikki 🔇")
        else:
            self.mute_button.setText("Välimusiikki 🔈")

    def paivita_juhlapeli_ilmoitus(self):
        """
        Listaa kaikki tulevat juhlapelaajat:
        - PlayerProfiles.Pelit % 100 >= 95 (enintään 5 peliä rajapyykkiin)
        - Pelaaja on pelannut viimeisen 6 kk aikana (Games-taulusta, missä tahansa slotissa)
        """

        try:
            # Lasketaan NextMilestone dynaamisesti: Nykyiset pelit + (100 - jakojäännös)
            query = f"""
                SELECT p.Nimi, p.Pelit, p.Pelit + (100 - (p.Pelit % 100)) AS NextMilestone
                FROM {profile_table} AS p
                WHERE (p.Pelit % 100) >= 95
                  AND EXISTS (
                      SELECT 1
                      FROM {table} AS g
                      WHERE g.{game_date} >= DATEADD(MONTH, -6, GETDATE())
                        AND (
                             LOWER(LTRIM(RTRIM(g.{winner1}))) = p.Nimi OR
                             LOWER(LTRIM(RTRIM(g.{winner2}))) = p.Nimi OR
                             LOWER(LTRIM(RTRIM(g.{loser1}))) = p.Nimi OR
                             LOWER(LTRIM(RTRIM(g.{loser2}))) = p.Nimi
                            )
                  )
                ORDER BY (100 - (p.Pelit % 100)) ASC, p.Nimi ASC;
            """
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()

            if not rows:
                self.juhlapeli_label.setText("Tulevat juhlapelit: –")
                return

            # Muotoilu: "nimi: nykyiset/seuraava" (esim. "andi: 97/100")
            ilmo = []
            for nimi, pelit, next_m in rows:
                n = (nimi or "").strip().lower()
                m_val = int(next_m) if next_m is not None else 0
                pelit_val = int(pelit) if pelit is not None else 0
                ilmo.append(f"{n}: {pelit_val}/{m_val}")

            self.juhlapeli_label.setText(
                "Tulevat juhlapelit: " + ", ".join(ilmo))

        except Exception as e:
            self.juhlapeli_label.setText(f"Tulevat juhlapelit: virhe: {e}")

    def keyPressEvent(self, event):
        """Käsittelee näppäinpainallukset: Enter toimii kuten välilyönti napeissa."""
        # Tarkistetaan, onko painettu näppäin Enter tai Numpadin Enter
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Haetaan elementti, joka on tällä hetkellä aktiivisena (focus)
            aktiivinen_osa = QApplication.focusWidget()
            
            # Jos aktiivinen elementti on painike, klikataan sitä
            if isinstance(aktiivinen_osa, QPushButton):
                aktiivinen_osa.click()
                event.accept() # Merkitään tapahtuma käsitellyksi
                return
                
        # Jos kyseessä ei ollut Enter napin kohdalla, jatketaan normaalia toimintaa
        super().keyPressEvent(event)

    def avaa_help(self):
        """Help-nappi ja avautuva vieritettävä ikkuna"""
        uusi = HelpIkkuna()
        self.aktiiviset_help_ikkunat.append(uusi)
        uusi.show()

    def avaa_profiilit(self):
        """Profiilit-nappi"""
        uusi = ProfiiliIkkuna()
        self.aktiiviset_profiili_ikkunat.append(uusi)
        uusi.show()

    def closeEvent(self, event):
        """Suljetaan kaikki, jos pääikkuna suljetaan"""

        keyboard.unhook_all() # Vapautetaan F13-näppäinkuuntelu

        if hasattr(self, 'serial_worker'):
            self.serial_worker.stop()

        for ikkuna in self.kaikki_tilastot:
            ikkuna.close()

        for ikkuna in self.aktiiviset_profiili_ikkunat:
            ikkuna.close()

        event.accept()



class HelpIkkuna(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Help")
        self.resize(200, 100)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        help_widget = QWidget()
        help_layout = QHBoxLayout(help_widget)

        help_text = "TG: @PelletinVPJ"

        help_layout.addWidget(QLabel(help_text))

        scroll_area.setWidget(help_widget)
        dialog_layout = QHBoxLayout()
        dialog_layout.addWidget(scroll_area)
        self.setLayout(dialog_layout)

class TilastotIkkuna(QDialog):
    """Tilastojen tarkasteluun käytetty luokka"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pelitilastot")
        self.tilastodata = []

        # leveys , korkeus
        self.resize(1500, 800)

        # --- Hakukenttä ---
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Hae pelaajan nimellä.")
        self.search_input.returnPressed.connect(self.hae_pelit)

        self.search_button = QPushButton("Hae")
        self.search_button.clicked.connect(self.hae_pelit)

        # --- Editor nappi ---
        self.editor_button = QPushButton("Editori")
        self.editor_button.clicked.connect(self.avaa_editori)

        # --- Pudotusvalikot graafeille (oikealle) ---
        self.combo_pelaajagraafit = QComboBox()
        self.combo_pelaajagraafit.addItems([
            "...",
            "Voittoprosentin kehitys",
            "Pelien määrän kehitys",
            "Keskiajan kehitys",
            "Pelimäärän vaikutus voittoprosenttiin",
            "Pelimäärän vaikutus keskiaikaan"
        ])
        self.combo_pelaajagraafit.currentIndexChanged.connect(
            self.kasittele_pelaajagraafi
        )

        self.combo_kaikkigraafit = QComboBox()
        self.combo_kaikkigraafit.addItems([
            "...",
            "Peliajankohta jakauma",
            "Pelikesto jakauma",
            "Kaikkien pelien määrän kehitys",
            "Kaikkien pelien keskiajan muutos",
            "Ikkuna vastaan juliste",
            "Juomajakauma"
        ])
        self.combo_kaikkigraafit.currentIndexChanged.connect(
            self.kasittele_kaikkigraafi
        )

        # --- Pudotusvalikko tilastoille (vasemmalle) ---
        self.combo_tilastot = QComboBox()
        self.combo_tilastot.addItems([
            "...",
            "Ennätykset",
            "Yhteiset ennätykset",
            "Juomien värit",
            "Soolopelit"
        ])
        self.combo_tilastot.currentIndexChanged.connect(
            self.kasittele_tilastovalinta
        )

        # --- Taulukko ---
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(7, 80)
        self.table.setColumnWidth(8, 500)
        self.table.setHorizontalHeaderLabels([
            "ID", "Ajankohta", "Aika", "Voittaja 1", "Voittaja 2",
            "Häviäjä 1", "Häviäjä 2", "Pöydän alla", "Kommentti"
        ])
        self.table.horizontalHeader().sectionClicked.connect(
            self.jarjesta_tilastot_sarakkeen_mukaan
        )
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.keyPressEvent = self.taulukko_keypress
        self.table.setFixedWidth(800)

        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate())
        self.start_date_edit.dateChanged.connect(self.hae_pelit)

        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate().addDays(1))
        self.end_date_edit.dateChanged.connect(self.hae_pelit)

        # --- Koostelabel ---
        self.stats_label = QLabel()
        self.stats_label.setWordWrap(True)
        self.stats_label.setMinimumWidth(150)
        self.stats_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        font = self.stats_label.font()
        font.setPointSize(12)
        self.stats_label.setFont(font)

        self.stats_scroll = QScrollArea()
        self.stats_scroll.setWidgetResizable(True)
        self.stats_scroll.setWidget(self.stats_label)
        self.stats_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        # --- Layoutit ---
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        # --- Graafit combobox layoutit otsikoilla ---
        pelaaja_label = QLabel("Graafit pelaajan tilastoista")
        font_label = pelaaja_label.font()
        font_label.setPointSize(14)
        pelaaja_label.setFont(font_label)
        pelaaja_label.setFixedHeight(30)
        pelaaja_label.setAlignment(Qt.AlignCenter)

        pelaaja_layout = QVBoxLayout()
        pelaaja_layout.addWidget(pelaaja_label)
        pelaaja_layout.addWidget(self.combo_pelaajagraafit)

        kaikki_label = QLabel("Graafit kaikista peleistä")
        kaikki_label.setFont(font_label)
        kaikki_label.setFixedHeight(30)
        kaikki_label.setAlignment(Qt.AlignCenter)

        kaikki_layout = QVBoxLayout()
        kaikki_layout.addWidget(kaikki_label)
        kaikki_layout.addWidget(self.combo_kaikkigraafit)

        graph_combo_layout = QHBoxLayout()
        graph_combo_layout.addLayout(pelaaja_layout)
        graph_combo_layout.addLayout(kaikki_layout)
        right_layout.addLayout(graph_combo_layout)

        # Kontti graafille
        self.graafi_container = QVBoxLayout()
        right_layout.addLayout(self.graafi_container)
        self.graafi_canvas = None

        # Hakukenttä ja nappi
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.search_input)
        input_layout.addWidget(self.search_button)
        input_container = QWidget()
        input_container.setLayout(input_layout)
        input_container.setFixedWidth(800)
        left_layout.addWidget(input_container)

        # Aikavälinappi
        self.date_filter_checkbox = QCheckBox("Käytä aikaväliä")
        self.date_filter_checkbox.stateChanged.connect(self.hae_pelit)

        # Filtterit layout
        filter_layout = QHBoxLayout()
        filter_layout.addStretch()
        filter_layout.addWidget(self.date_filter_checkbox)
        filter_layout.addWidget(QLabel("Alkaen:"))
        filter_layout.addWidget(self.start_date_edit)
        filter_layout.addWidget(QLabel("Päättyen:"))
        filter_layout.addWidget(self.end_date_edit)
        filter_container = QWidget()
        filter_container.setLayout(filter_layout)
        filter_container.setFixedWidth(800)
        left_layout.addWidget(filter_container)

        # Taulukko
        left_layout.addWidget(self.table, 3)

        # Alapalkki: editori + tilastopudotusvalikko allekkain, stats_label vieressä
        bottom_layout = QHBoxLayout()
        self.rank_label = QLabel()
        self.rank_label.setFixedSize(150, 150)
        self.rank_label.setScaledContents(True)
        self.rank_label.setAlignment(Qt.AlignCenter)

        editor_combo_layout = QVBoxLayout()
        editor_combo_layout.addWidget(self.rank_label)
        editor_combo_layout.addWidget(self.combo_tilastot)
        editor_combo_layout.addWidget(self.editor_button)
        self.combo_tilastot.setMaximumWidth(150)
        self.editor_button.setMaximumWidth(150)

        bottom_layout.addLayout(editor_combo_layout)
        bottom_layout.addWidget(self.stats_scroll)
        self.stats_scroll.setFixedHeight(280)
        left_layout.addLayout(bottom_layout)

        # Yhdistä vasen ja oikea
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        main_layout.addStretch() # <-- Tämä työntää taulukon ja graafin kiinni toisiinsa vasemmalle
        self.setLayout(main_layout)

        # Muut muuttujat
        self.sort_column_tilastot = 0
        self.sort_desc_tilastot = True

        # Autocompleteen tarvittavat muuttujat alustetaan tyhjiksi,
        # täytetään vasta vaiheittaisessa latauksessa
        self.pelaajat = []
        # self.tilastodata on jo alustettu listaksi ylhäällä

        # Luo yksi tyhjä graafi aluksi kevyesti
        self.reset_graafi()

        self.threadpool = QThreadPool.globalInstance()
        self.pelaajat, _ = hae_pelaajat_kannasta()
        aseta_autocomplete([self.search_input], self.pelaajat, self)
        self.hae_pelit()
        self.nayta_juomien_varit()


    def kasittele_pelaajagraafi(self, index):
        if index > 0:  # jos ei olla "..." kohdassa
            # resetoi toinen pudotusvalikko
            self.combo_kaikkigraafit.setCurrentIndex(0)
        if index == 1:
            self.nayta_voittoprosentti_graafi()
        elif index == 2:
            self.nayta_pelimaara_graafi()
        elif index == 3:
            self.nayta_keskiajan_kehitys_graafi()
        elif index == 4:
            self.nayta_paivan_pelimaara_voittoprosentti_tiheyksilla()
        elif index == 5:
            self.nayta_pelimaara_vs_paivan_keskiaika()

    def kasittele_kaikkigraafi(self, index):
        if index > 0:  # jos ei olla "..." kohdassa
            # resetoi pelaajagraafit-pudotusvalikko
            self.combo_pelaajagraafit.setCurrentIndex(0)
        if index == 1:
            self.nayta_peliaikojen_barplot()
        elif index == 2:
            self.nayta_pelikestot_barplot()
        elif index == 3:
            self.nayta_kumulatiivinen_pelit()
        elif index == 4:
            self.nayta_keskiaikojen_muutos()
        elif index == 5:
            self.nayta_tiimien_voitto_pie()
        elif index == 6:
            self.nayta_juomat_pie()

    def kasittele_tilastovalinta(self, index):
        if index == 1:
            self.nayta_ennatyskooste()
        elif index == 2:
            self.nayta_yhteiset_ennatykset()
        elif index == 3:
            self.nayta_juomien_varit()
        elif index == 4:
            self.solo_pelit()

    def jarjesta_tilastot_sarakkeen_mukaan(self, index):
        """Järjestetään tilastoja halutun sarakkeen mukaan"""

        # Jos klikataan Pöydän alla -saraketta (indeksi 7)
        if index == 7:
            self.sort_column_tilastot = index
            self.sort_desc_tilastot = True  # True pelit ylimmäksi
        else:
            if self.sort_column_tilastot == index:
                self.sort_desc_tilastot = not self.sort_desc_tilastot
            else:
                self.sort_column_tilastot = index
                self.sort_desc_tilastot = True

        self.paivita_tilastot()

    def paivita_tilastot(self):
        """Asettaa tiedot taulukkoon ja värjää solut juomien perusteella"""
        data = self.tilastodata.copy() if hasattr(self, 'tilastodata') else []

        def sort_key(x):
            value = x[self.sort_column_tilastot]
            if self.sort_column_tilastot == 7:
                # Pöydän alla -sarake: None → False
                return bool(value)
            return value if value is not None else ""

        data.sort(key=sort_key, reverse=self.sort_desc_tilastot)

        self.table.setRowCount(len(data))

        # Määritellään taustavärit juomille (Tummaan teemaan sopivat sävyt)
        juoma_varit = {
            "kalja": QColor("#8B6508"),         # Tummahko ruskeankeltainen
            "vichy": QColor("#36648B"),         # Teräksensininen
            "siideri": QColor("#556B2F"),       # Tumma oliivinvihreä
            "lonkero": QColor("#708090"),       # Siniharmaa
            "hard seltzer": QColor("#8B008B"),  # Tumma magenta
            "limsa": QColor("#CD5C5C"),         # Tumma koralli
            "energiajuoma": QColor("#B8860B")   # Tumma kulta
        }

        for i, row in enumerate(data):
            # Käydään läpi vain näkyvät 9 saraketta (indeksit 0-8)
            for j in range(9):
                sek = None
                # Varmistetaan, ettei ylitetä listan rajoja
                arvo = row[j] if j < len(row) else ""

                if j == 2 and isinstance(arvo, dt_time):  # {game_time} sarake
                    sek = arvo.hour * 3600 + arvo.minute * 60 + arvo.second
                    arvo_str = format_seconds(sek)
                elif j == 7:
                    arvo_str = "True" if arvo else ""
                elif arvo is None:
                    arvo_str = ""
                else:
                    arvo_str = str(arvo)
                    
                item = QTableWidgetItem(arvo_str)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

                if j == 2 and sek is not None:
                    if sek < 60:
                        item.setBackground(QColor("#228B22"))  # Vihreä (< 1 min)
                    elif 60 <= sek <= 180:
                        item.setBackground(QColor("#DAA520"))  # Keltainen (1 - 3 min)
                    else:
                        item.setBackground(QColor("#8B0000"))  # Punainen (> 3 min)


                # --- UUSI LISÄYS: Värjäyslogiikka ---
                # Sarakkeet: 3 = Voittaja 1, 4 = Voittaja 2, 5 = Häviäjä 1, 6 = Häviäjä 2
                if j in (3, 4, 5, 6):
                    # Lasketaan juoman indeksi row-listassa (3 -> 9, 4 -> 10 jne.)
                    juoma_indeksi = j + 6
                    
                    # Tarkistetaan, että SQL-haussa oli juomat mukana
                    if len(row) > juoma_indeksi:
                        juoma_nimi = str(row[juoma_indeksi]).lower().strip() if row[juoma_indeksi] else ""
                        
                        # Jos juoma löytyy sanakirjasta, asetetaan taustaväri
                        if juoma_nimi in juoma_varit:
                            item.setBackground(juoma_varit[juoma_nimi])
                            
                            # VINKKI: Jos taustaväri on liian hallitseva, voit poistaa 
                            # setBackground-rivin ja värjätä vain pelaajan nimen tekstin:
                            # item.setForeground(juoma_varit[juoma_nimi])

                if j == 7 and arvo:
                    item.setBackground(QColor("#8B0000"))  # Tummanpunainen
                

                # Lisätään solu taulukkoon
                self.table.setItem(i, j, item)

    def hae_pelit(self):
        """Käynnistää pelien haun taustasäikeessä."""
        nimi = self.search_input.text().strip()
        kayta_aikavalia = self.date_filter_checkbox.isChecked()

        query = f"SELECT ID, {game_date}, {game_time}, {winner1}, {winner2}, {loser1}, {loser2}, {under_table}, {comment}, {drink1}, {drink2}, {drink3}, {drink4}, gamemaster FROM {table}"
        conditions = []
        params = []

        if nimi:
            if ";" in nimi:
                pelaajat = [n.strip().lower() for n in nimi.split(";")]
                if len(pelaajat) == 2:
                    conditions.append(
                        f"((LOWER({winner1}) = ? AND LOWER({winner2}) = ?) OR (LOWER({winner1}) = ? AND LOWER({winner2}) = ?) OR (LOWER({loser1}) = ? AND LOWER({loser2}) = ?) OR (LOWER({loser1}) = ? AND LOWER({loser2}) = ?))")
                    params.extend(
                        [pelaajat[0], pelaajat[1], pelaajat[1], pelaajat[0],
                         pelaajat[0], pelaajat[1], pelaajat[1], pelaajat[0]])
            else:
                conditions.append(
                    f"(LOWER({winner1}) = ? OR LOWER({winner2}) = ? OR LOWER({loser1}) = ? OR LOWER({loser2}) = ?)")
                params.extend([nimi.lower()] * 4)

        if kayta_aikavalia:
            conditions.append(f"{game_date} BETWEEN ? AND ?")
            params.append(self.start_date_edit.date().toPython())
            params.append(self.end_date_edit.date().toPython())

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY ID DESC"

        # Käynnistetään taustatyö
        self.search_button.setEnabled(False)  # Estetään tuplaklikkaus
        worker = DatabaseWorker(query, params)
        worker.signals.results.connect(self._kasittele_haun_tulokset)
        worker.signals.error.connect(self._kasittele_haun_virhe)
        self.threadpool.start(worker)

    def _kasittele_haun_tulokset(self, results):
        """UI-säie kutsuu tätä kun data on valmis."""
        self.search_button.setEnabled(True)
        self.tilastodata = results
        self.paivita_tilastot()

        nimi = self.search_input.text().strip()
        if nimi:
            pelaajat = [n.strip() for n in nimi.split(";")]
            self.paivita_kooste(pelaajat, results)

    def _kasittele_haun_virhe(self, error_msg):
        self.search_button.setEnabled(True)
        QMessageBox.critical(self, "Virhe",
                             f"Virhe haettaessa pelejä:\n{error_msg}")

    def paivita_kooste(self, pelaajat, results):
        """Päämetodi, joka ohjaa tietojen hakua, laskentaa ja tulostusta.
        
        """
        if hasattr(self, "rank_label"):
            self.rank_label.clear()

        if not results:
            self.stats_label.setText("Ei pelejä valituilla pelaajilla.")
            return

        pelaajat_low = [p.lower().strip() for p in pelaajat]

        # 1. Hae ensimmäisten minuuttipelien ID:t
        eka_minuutti_id = self._hae_ensimmaiset_minuuttipelit()

        # 2. Laske tilastot tuloksista
        tilastot = self._laske_koosteen_tilastot(pelaajat_low, results, eka_minuutti_id)

        # 3. Hae Felo ja pelinvetäjätiedot (vain yhdelle pelaajalle)
        felo_luku, vedetyt_pelit_lkm = self._hae_pelaajan_lisatiedot(pelaajat_low)
        self.paivita_rank_kuvake(felo_luku)

        # 4. Rakenna ja aseta teksti
        koosteteksti = self._muotoile_koosteteksti(
            pelaajat, pelaajat_low, tilastot, felo_luku, vedetyt_pelit_lkm, results
        )
        self.stats_label.setText(koosteteksti)

    def _hae_ensimmaiset_minuuttipelit(self):
        """Hakee pelaajien ensimmäisten minuuttipelien ID:t tietokannasta."""
        sql = f"""
            WITH M AS (
                SELECT LOWER(LTRIM(RTRIM({winner1}))) AS n, ID FROM {table} WHERE DATEDIFF(SECOND, '00:00:00', {game_time}) < 60
                UNION ALL
                SELECT LOWER(LTRIM(RTRIM({winner2}))), ID FROM {table} WHERE DATEDIFF(SECOND, '00:00:00', {game_time}) < 60
                UNION ALL
                SELECT LOWER(LTRIM(RTRIM({loser1}))), ID FROM {table} WHERE DATEDIFF(SECOND, '00:00:00', {game_time}) < 60
                UNION ALL
                SELECT LOWER(LTRIM(RTRIM({loser2}))), ID FROM {table} WHERE DATEDIFF(SECOND, '00:00:00', {game_time}) < 60
            )
            SELECT n, MIN(ID) AS eka_id FROM M GROUP BY n
        """
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                return {r[0]: r[1] for r in cur.fetchall()}
        except Exception as e:
            print(f"Virhe eka_minuutti haussa: {e}")
            return {}

    def _laske_koosteen_tilastot(self, pelaajat_low, results, eka_minuutti_id):
        """Iteroi hakutulokset läpi ja laskee kaikki tarvittavat tilastot sanakirjaan."""
        tilastot = {
            "pelit_sekunteina": [],
            "voitot": 0,
            "havio_poydan_alla": 0,
            "minuuttipelit": 0,
            "kaljat": 0,
            "vichyt": 0,
            "kaikki_juomat": 0,
            "itse_voitolla_klubiin": False,
            "heitetyt": set(),
            "poydan_alle_heitot": 0,
            "poydan_alle_heitetyt_nimet": set()
        }

        for row in results:
            peli_id = row[0]
            kesto = row[2]
            p1, p2, p3, p4 = [(row[i] or "").lower().strip() for i in range(3, 7)]
            poydan_alla = row[7]
            sekunnit = kesto.hour * 3600 + kesto.minute * 60 + kesto.second

            tilastot["pelit_sekunteina"].append(sekunnit)
            winners = {p1, p2}
            losers = {p3, p4}

            if len(pelaajat_low) == 2:
                jos_voitto = (pelaajat_low[0] in winners and pelaajat_low[1] in winners)
                jos_osallistui = jos_voitto or (pelaajat_low[0] in losers and pelaajat_low[1] in losers)
            else:
                sel = pelaajat_low[0]
                jos_voitto = (sel in winners)
                jos_osallistui = (sel in winners or sel in losers)

            if jos_voitto: tilastot["voitot"] += 1
            if poydan_alla:
                if len(pelaajat_low) == 1 and pelaajat_low[0] in losers:
                    tilastot["havio_poydan_alla"] += 1
                elif len(pelaajat_low) == 2 and (pelaajat_low[0] in losers and pelaajat_low[1] in losers):
                    tilastot["havio_poydan_alla"] += 1

                if jos_voitto:
                    tilastot["poydan_alle_heitot"] += 1
                    for vastustaja in losers:
                        if vastustaja:
                            tilastot["poydan_alle_heitetyt_nimet"].add(vastustaja)

            if jos_osallistui and sekunnit < 60:
                tilastot["minuuttipelit"] += 1
                if len(pelaajat_low) == 1:
                    sel = pelaajat_low[0]
                    if peli_id == eka_minuutti_id.get(sel) and jos_voitto:
                        tilastot["itse_voitolla_klubiin"] = True

                    if jos_voitto:
                        for vast in (losers | (winners - {sel})):
                            if vast and eka_minuutti_id.get(vast) == peli_id:
                                tilastot["heitetyt"].add(vast)

            # Juomalaskenta (Expert-tila)
            if len(row) > 12 and len(pelaajat_low) == 1:
                sel = pelaajat_low[0]
                pelaaja_nimet = [p1, p2, p3, p4]
                juomat = [str(row[i]).lower().strip() if row[i] else "" for i in range(9, 13)]
                for i, nimi in enumerate(pelaaja_nimet):
                    if nimi == sel:
                        juoma = juomat[i]
                        if juoma:
                            tilastot["kaikki_juomat"] += 1
                            if juoma == "kalja":
                                tilastot["kaljat"] += 1
                            elif juoma == "vichy":
                                tilastot["vichyt"] += 1

        return tilastot

    def _hae_pelaajan_lisatiedot(self, pelaajat_low):
        """Hakee yhden pelaajan Felo-arvon ja pelinvetäjänä toimittujen pelien määrän."""
        felo_luku = None
        vedetyt_pelit_lkm = 0

        if len(pelaajat_low) == 1:
            pelaaja = pelaajat_low[0]
            try:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT Felo FROM {profile_table} WHERE LOWER(Nimi) = ?", (pelaaja,))
                    r = cur.fetchone()
                    if r:
                        felo_luku = r[0]
            except Exception as e:
                print("Felo-haku epäonnistui:", e)

            try:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE LOWER(LTRIM(RTRIM(gamemaster))) = ?", (pelaaja,))
                    vedetyt_pelit_lkm = cur.fetchone()[0]
            except Exception as e:
                print(f"Pelinvetäjien laskenta epäonnistui: {e}")

        return felo_luku, vedetyt_pelit_lkm

    def _muotoile_koosteteksti(self, pelaajat_orig, pelaajat_low, tilastot, felo_luku, vedetyt_pelit_lkm, results):
        """Kokoaa datan HTML-muotoilluksi merkkijonoksi."""
        pelit_sekunteina = tilastot["pelit_sekunteina"]
        pelien_maara = len(pelit_sekunteina)
        
        keskiarvo = sum(pelit_sekunteina) / pelien_maara if pelien_maara > 0 else 0
        voittoprosentti = (tilastot["voitot"] / pelien_maara * 100) if pelien_maara > 0 else 0
        
        kaljat = tilastot["kaljat"]
        vichyt = tilastot["vichyt"]
        kaikki_juomat = tilastot["kaikki_juomat"]
        kalja_pros = (kaljat / kaikki_juomat * 100) if kaikki_juomat > 0 else 0
        vichy_pros = (vichyt / kaikki_juomat * 100) if kaikki_juomat > 0 else 0
        
        nopein = min(pelit_sekunteina) if pelit_sekunteina else 0
        hitain = max(pelit_sekunteina) if pelit_sekunteina else 0

        pelaajat_str = " ja ".join(pelaajat_orig)
        koosteteksti = (
            f"<b>Kooste pelaajasta {pelaajat_str}:</b><br><br>"
            f"<b>Pelit:</b> {pelien_maara} &nbsp;&nbsp; <b>Voitot:</b> {tilastot['voitot']} ({voittoprosentti:.1f} %)<br>"
            f"<b>Nopein:</b> {format_seconds(nopein)} &nbsp;&nbsp; <b>Hitain:</b> {format_seconds(hitain)} &nbsp;&nbsp; <b>Keskiaika:</b> {format_seconds(keskiarvo)}<br>"
            f"<b>Pöydän alla:</b> {tilastot['havio_poydan_alla']} &nbsp;&nbsp; <b>Minuuttipelit:</b> {tilastot['minuuttipelit']} ({tilastot['minuuttipelit'] / pelien_maara * 100:.1f} %)<br>"
        )

        if len(pelaajat_low) == 1:
            koosteteksti += f"<b>Kaljat:</b> {kaljat} kpl ({kalja_pros:.1f} %) &nbsp;&nbsp; <b>Vichyt:</b> {vichyt} kpl ({vichy_pros:.1f} %) &nbsp;&nbsp; <b>Kaikki:</b> {kaikki_juomat} kpl"
            if kaikki_juomat == 0:
                koosteteksti += " &nbsp; <i>(Ei juomamerkintöjä)</i>"
            koosteteksti += "<br>"

            heitetyt = tilastot["heitetyt"]
            lista = ", ".join(sorted(heitetyt)) if heitetyt else "–"
            koosteteksti += f"<b>Minuuttiklubiin heitetyt:</b> {lista}"
            if tilastot["itse_voitolla_klubiin"]:
                koosteteksti += " &nbsp; <i>(Itse voitolla minuuttiklubiin)</i>"
            koosteteksti += "<br>"

            poydan_alle_heitetyt_nimet = tilastot["poydan_alle_heitetyt_nimet"]
            p_lista = ", ".join(sorted(poydan_alle_heitetyt_nimet)) if poydan_alle_heitetyt_nimet else "–"
            koosteteksti += f"<b>Pöydän alle heitetyt:</b> {p_lista} "
            if tilastot["poydan_alle_heitot"] > 0:
                koosteteksti += f"&nbsp; <i>({len(poydan_alle_heitetyt_nimet)} henkilöä, {tilastot['poydan_alle_heitot']} kerralla)</i>"
            koosteteksti += "<br>"

            kaverit, lkm = self.laske_yleisimmat_pelikaverit(pelaajat_orig[0], results)
            if kaverit:
                koosteteksti += f"<b>Yleisin pelikaveri:</b> {', '.join(kaverit)} ({lkm} peliä)<br>"
            else:
                koosteteksti += f"<b>Yleisin pelikaveri:</b> –<br>"

            koosteteksti += f"<b>Pelinvetäjänä toiminut:</b> {vedetyt_pelit_lkm} peliä<br>"

            if felo_luku is not None:
                koosteteksti += f"<b>Felo:</b> {int(felo_luku)}<br>"
            else:
                koosteteksti += f"<b>Felo:</b> –<br>"

        return koosteteksti

    def laske_yleisimmat_pelikaverit(self, nimi: str, results):
        """Palauta (lista_kavereista, pelimaara) haetulle nimelle.
        Pelikaveri lasketaan vain jos ollaan samalla puolella:
        ({winner1},{winner2}) tai ({loser1},{loser2}).
        """
        target = (nimi or "").strip().lower()
        if not target:
            return [], 0

        counts = Counter()
        canonical = {}  # säilytä siisti esitysmuoto (ensimmäinen nähty)

        for row in results:
            p1, p2, p3, p4 = row[3], row[4], row[5], row[6]
            winners = [p1 or "", p2 or ""]
            losers = [p3 or "", p4 or ""]

            def laske_puolella(side):
                low = [s.strip().lower() for s in side]
                if target in low:
                    i = low.index(target)
                    teammate = (side[1 - i] or "").strip()
                    if teammate:
                        key = teammate.lower()
                        counts[key] += 1
                        canonical.setdefault(key, teammate)

            laske_puolella(winners)
            laske_puolella(losers)

        if not counts:
            return [], 0

        maks = max(counts.values())
        top_keys = [k for k, v in counts.items() if v == maks]
        # Palauta nätissä muodossa, aakkosjärjestys
        top_names = sorted((canonical[k] for k in top_keys),
                           key=lambda s: s.lower())
        return top_names, maks

    def paivita_rank_kuvake(self, felo):
        """Päivittää rank-kuvakkeen Felo-luvun perusteella."""
        if not hasattr(self, "rank_label"):
            return

        if felo is None:
            self.rank_label.clear()
            return

        try:
            felo_val = float(felo)
        except (TypeError, ValueError):
            self.rank_label.clear()
            return

        # Logiikka: Sandels (>1600), Coop (1500-1599), Pirkka (1400-1499), Olvi (<1400)
        if felo_val >= 1600:
            path = config.get("rank_sandels")
        elif 1500 <= felo_val < 1600:
            path = config.get("rank_coop")
        elif 1400 <= felo_val < 1500:
            path = config.get("rank_pirkka")
        else:
            path = config.get("rank_olvi")

        if path and os.path.isfile(path):
            pix = QPixmap(path)
            if not pix.isNull():
                self.rank_label.setPixmap(pix)
            else:
                self.rank_label.clear()
        else:
            self.rank_label.clear()

    def avaa_editori(self):
        password, ok = QInputDialog.getText(
            self, "Salasana",
            "Syötä editorin salasana:",
            QLineEdit.EchoMode.Password
        )
        if not ok:
            return

        oikea_salasana = os.getenv("EDITOR_PASSWORD")
        
        # Ei löydy salasana täältä, sori :)
        if not oikea_salasana or password != oikea_salasana:
            QMessageBox.critical(self, "Virhe", "Väärä salasana!")
            return

        # Valinta mitä halutaan tehdä
        vaihtoehto, ok = QInputDialog.getItem(
            self, "Valitse toiminto",
            "Mitä haluat tehdä?",
            ["Muokkaa peliä ID:llä",
             "Vaihda pelaajan nimeä kaikissa peleissä",
             "Laske Felo uudelleen"],  # Felon uudelleen laskenta
            0, False
        )
        if not ok:
            return

        if vaihtoehto == "Muokkaa peliä ID:llä":
            id_str, ok = QInputDialog.getText(self, "Pelin ID",
                                              "Syötä muokattavan pelin ID:")
            if ok and id_str.isdigit():
                self.muokkaa_pelia(int(id_str))
            else:
                QMessageBox.warning(self, "Virhe", "Virheellinen ID.")

        elif vaihtoehto == "Vaihda pelaajan nimeä kaikissa peleissä":
            self.vaihda_pelaajanimi_globaalisti()

        elif vaihtoehto == "Laske Felo uudelleen":
            self.felo_rebuild()

    def felo_rebuild(self):
        """Ajaa koko historian Felo-laskennan ja päivittää näkymän."""
        try:
            with conn.cursor() as cur:
                cur.execute("EXEC dbo.Felo_RebuildAll;")
                conn.commit()
            # Päivitä UI jos metodi löytyy (toimii sekä profiili- että peli-ikkunassa)
            if hasattr(self, "lataa_data"):
                self.lataa_data()
            elif hasattr(self, "hae_pelit"):
                self.hae_pelit()
            QMessageBox.information(self, "Felo", "Felo-pisteet päivitetty.")
        except Exception as e:
            QMessageBox.critical(self, "Virhe",
                                 f"Felo Rebuild epäonnistui:\n{e}")

    def muokkaa_pelia(self, peli_id: int):
        """Avataan muokkausikkuna, joka näyttää ja sallii muokkauksen aiemmilla arvoilla."""
        try:
            with conn.cursor() as cur:
                # SQL haut
                cur.execute(f"""
                    SELECT ID, {winner1}, {winner2}, {loser1}, {loser2},
                           {under_table}, {game_time}, {winner_side},
                           {drink1}, {drink2}, {drink3}, {drink4},
                           {game_date}, {comment}, gamemaster
                    FROM {table}
                    WHERE ID = ?
                """, (peli_id,))
                rivi = cur.fetchone()
        except Exception as e:
            QMessageBox.critical(self, "Tietokantavirhe",
                                 f"Tietojen haku epäonnistui:\n{e}")
            return

        if not rivi:
            QMessageBox.warning(self, "Ei löytynyt",
                                f"ID {peli_id} ei löytynyt.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Muokkaa peliä (ID: {peli_id})")
        dialog.resize(480,
                      700)  # Kasvatettu korkeutta, jotta uudet kentät mahtuvat

        # Pelaajat
        p1 = QLineEdit((getattr(rivi, winner1) or "").strip())
        p2 = QLineEdit((getattr(rivi, winner2) or "").strip())
        p3 = QLineEdit((getattr(rivi, loser1) or "").strip())
        p4 = QLineEdit((getattr(rivi, loser2) or "").strip())

        # Pöydän alla
        poydan_alla = QCheckBox("Pöydän alla")
        poydan_alla.setChecked(getattr(rivi, under_table))

        # Kommentti (Uusi kenttä)
        kommentti_le = QLineEdit(str(getattr(rivi, comment) or ""))
        kommentti_le.setMaxLength(50)
        kommentti_le.setPlaceholderText("Muokkaa kommenttia...")

        # Pelinvetäjä
        gamemaster_le = QLineEdit(str(getattr(rivi, 'gamemaster', '') or ""))
        gamemaster_le.setMaxLength(50)
        gamemaster_le.setPlaceholderText("Muokkaa pelinvetäjää...")

        # Ajankohta
        ajankohta_edit = QDateTimeEdit()
        ajankohta_edit.setCalendarPopup(True)
        ajankohta_edit.setDisplayFormat("dd.MM.yyyy HH:mm:ss")
        vanha_pvm = getattr(rivi, game_date)
        if vanha_pvm:
            ajankohta_edit.setDateTime(QDateTime(vanha_pvm))
        else:
            ajankohta_edit.setDateTime(QDateTime.currentDateTime())

        # Aika (Kesto)
        aika_le = QLineEdit()
        aika_le.setPlaceholderText("mm:ss")
        try:
            kesto = getattr(rivi, game_time, None)
            if kesto:
                if hasattr(kesto, "hour"):
                    total_sec = kesto.hour * 3600 + kesto.minute * 60 + kesto.second
                else:
                    parts = str(kesto).split(":")
                    total_sec = (
                        int(parts[0]) * 3600 + int(parts[1]) * 60 + int(
                            parts[2]) if len(parts) == 3 else 0)
                aika_le.setText(format_seconds(total_sec))
        except Exception:
            pass

        # Voittopuolen valinta
        nykyinen_voitto_raw = getattr(rivi, winner_side, None)
        # Muunnos loogiseksi arvoksi (käsittelee bit/bool/int)
        nykyinen_voitto = int(
            nykyinen_voitto_raw) if nykyinen_voitto_raw is not None else None

        radio_a = QRadioButton("Tiimi Ikkunaseinä")
        radio_b = QRadioButton("Tiimi Julisteseinä")
        if nykyinen_voitto == 1:
            radio_a.setChecked(True)
        elif nykyinen_voitto == 0:
            radio_b.setChecked(True)

        voittoryhmä_group = QGroupBox("Voittopuoli")
        voitt_layout = QVBoxLayout()
        voitt_layout.addWidget(radio_a)
        voitt_layout.addWidget(radio_b)
        voittoryhmä_group.setLayout(voitt_layout)

        # Juomat
        drink_opts = self._get_drink_options()
        juomat_cb = [QComboBox() for _ in range(4)]
        aiemmat_juomat = [getattr(rivi, drink1, None),
                          getattr(rivi, drink2, None),
                          getattr(rivi, drink3, None),
                          getattr(rivi, drink4, None)]

        for cb, vanha in zip(juomat_cb, aiemmat_juomat):
            cb.addItems(drink_opts)
            if vanha and str(vanha).strip() in drink_opts:
                cb.setCurrentText(str(vanha).strip())
            else:
                cb.setCurrentIndex(0)

        # Napit
        poista_btn = QPushButton("Poista peli")
        poista_btn.setStyleSheet("color: red; font-weight: bold")
        poista_btn.clicked.connect(lambda: self.poista_peli(peli_id, dialog))

        tallenna_btn = QPushButton("Tallenna")
        # Huom: lisätty kommentti_le.text() argumentiksi
        tallenna_btn.clicked.connect(lambda: self.tallenna_muokattu_peli(
            peli_id, p1.text(), p2.text(), p3.text(), p4.text(),
            poydan_alla.isChecked(), aika_le.text(),
            radio_a.isChecked(), radio_b.isChecked(),
            juomat_cb[0].currentText(), juomat_cb[1].currentText(),
            juomat_cb[2].currentText(), juomat_cb[3].currentText(),
            ajankohta_edit.dateTime(),
            kommentti_le.text(),
            gamemaster_le.text(),
            dialog
        ))

        # Layoutin rakennus
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Ajankohta:"))
        layout.addWidget(ajankohta_edit)

        pelaaja_box = QGroupBox("Pelaajat")
        pl = QFormLayout()
        pl.addRow("Voittaja 1:", p1)
        pl.addRow("Voittaja 2:", p2)
        pl.addRow("Häviäjä 1:", p3)
        pl.addRow("Häviäjä 2:", p4)
        pelaaja_box.setLayout(pl)
        layout.addWidget(pelaaja_box)

        layout.addWidget(QLabel("Pelattu aika (mm:ss):"))
        layout.addWidget(aika_le)
        layout.addWidget(voittoryhmä_group)

        juoma_box = QGroupBox("Juomat")
        jb = QFormLayout()
        jb.addRow(f"{winner1}:", juomat_cb[0])
        jb.addRow(f"{winner2}:", juomat_cb[1])
        jb.addRow(f"{loser1}:", juomat_cb[2])
        jb.addRow(f"{loser2}:", juomat_cb[3])
        juoma_box.setLayout(jb)
        layout.addWidget(juoma_box)

        layout.addWidget(QLabel("Kommentti:"))
        layout.addWidget(kommentti_le)
        layout.addWidget(QLabel("Pelinvetäjä:"))
        layout.addWidget(gamemaster_le)
        layout.addWidget(poydan_alla)
        layout.addWidget(tallenna_btn)
        layout.addWidget(poista_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def vaihda_pelaajanimi_globaalisti(self):
        """Kysyy vanhan ja uuden nimen, ja vaihtaa ne kaikissa peleissä."""
        vanha, ok1 = QInputDialog.getText(self, "Vanha nimi",
                                          "Syötä vaihdettava nimi:")
        if not ok1 or not vanha.strip():
            return
        uusi, ok2 = QInputDialog.getText(self, "Uusi nimi", "Syötä uusi nimi:")
        if not ok2 or not uusi.strip():
            return

        vanha = vanha.strip()
        uusi = uusi.strip()

        vastaus = QMessageBox.question(
            self,
            "Vahvista nimenvaihto",
            f"Haluatko varmasti muuttaa kaikki '{vanha}' → '{uusi}'?\n"
            f"Tämä vaikuttaa kaikkiin tämän pelaajan peleihin.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if vastaus != QMessageBox.StandardButton.Yes:
            return

        try:
            with conn.cursor() as cur:
                # Vaihdetaan nimi kaikissa {winner1}–{loser2} kentissä
                for sarake in [f"{winner1}", f"{winner2}", f"{loser1}",
                               f"{loser2}"]:
                    cur.execute(
                        f"UPDATE {table} SET {sarake} = ? WHERE LOWER({sarake}) = LOWER(?)",
                        (uusi, vanha)
                    )
                conn.commit()
            QMessageBox.information(self, "Onnistui",
                                    f"Nimi '{vanha}' vaihdettiin '{uusi}' kaikissa peleissä.")
            self.hae_pelit()  # Päivitä näkymä
        except Exception as e:
            QMessageBox.critical(self, "Virhe",
                                 f"Nimenvaihto epäonnistui:\n{e}")

    def _get_drink_options(self):
        """Palauttaa sallitut juoma-vaihtoehdot."""
        return ["...", "Kalja", "Vichy", "Hard Seltzer", "Siideri", "Limsa",
                "Energiajuoma", "Muu"]

    def tallenna_muokattu_peli(self, peli_id, p1, p2, p3, p4, poydan_alla,
                               aika_text, radio_a_checked, radio_b_checked,
                               juoma1, juoma2, juoma3, juoma4,
                               uusi_ajankohta_qt, kommentti, gamemaster,
                               dialog):
        """Tallentaa muokatun pelin — säilyttää None-arvot oikein."""

        if not all([p1.strip(), p2.strip(), p3.strip(), p4.strip()]):
            QMessageBox.warning(self, "Virhe",
                                "Kaikkien pelaajien nimet on täytettävä.")
            return

        tallennettava_kommentti = kommentti.strip() if kommentti.strip() else None

        tallennettava_gm = gamemaster.strip() if gamemaster.strip() else None
        # Muunnetaan QDateTime Pythonin datetime-objektiksi
        uusi_pvm_python = uusi_ajankohta_qt.toPython()

        # Haetaan aiemmat juomat ja voittopuoli, jotta voidaan säilyttää None-arvot
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {drink1}, {drink2}, {drink3}, {drink4}, {winner_side}, gamemaster "
                f"FROM {table} "
                f"WHERE ID = ?",
                (peli_id,))
            vanhat = cur.fetchone()

        if not vanhat:
            QMessageBox.warning(self, "Virhe", "Peliä ei löytynyt.")
            return

        sallitut_juomat = self._get_drink_options()
        uudet_juomat = [juoma1, juoma2, juoma3, juoma4]
        tallennettavat_juomat = []

        for uusi in uudet_juomat:
            uusi_clean = (uusi or "").strip()
            
            # Jos valittuna on "..." tai kenttä on tyhjä, tallennetaan None (NULL kantaan)
            if uusi_clean == "..." or not uusi_clean:
                tallennettavat_juomat.append(None)
            elif uusi_clean not in sallitut_juomat:
                tallennettavat_juomat.append("Muu")
            else:
                tallennettavat_juomat.append(uusi_clean)

        # Aika (mm:ss)
        kesto_aikana = None
        if aika_text.strip():
            try:
                mm, ss = map(int, aika_text.strip().split(":"))
                if mm < 0 or not (0 <= ss < 60): raise ValueError
                kesto = timedelta(minutes=mm, seconds=ss)
                kesto_aikana = (datetime.min + kesto).time()
            except ValueError:
                QMessageBox.warning(self, "Virhe",
                                    "Aika ei ole oikeassa muodossa (mm:ss).")
                return
        else:
            with conn.cursor() as cur:
                cur.execute(f"SELECT {game_time} FROM {table} WHERE ID = ?",
                            (peli_id,))
                rivi = cur.fetchone()
            kesto_aikana = getattr(rivi, game_time, None) if rivi else None

        # Voittopuoli
        if radio_a_checked:
            nykyinen_voitto = 1
        elif radio_b_checked:
            nykyinen_voitto = 0
        else:
            nykyinen_voitto = getattr(vanhat, winner_side, None)

        # Päivitys tietokantaan
        try:
            with conn.cursor() as cur:
                # MUUTOS: Lisätty {game_date} = ? UPDATE-lauseeseen
                cur.execute(f"""
                    UPDATE {table}
                    SET {winner1} = ?, {winner2} = ?, {loser1} = ?, {loser2} = ?,
                        {under_table} = ?, {game_time} = ?,
                        {drink1} = ?, {drink2} = ?, {drink3} = ?, {drink4} = ?,
                        {winner_side} = ?,
                        {game_date} = ?,
                        {comment} = ?,
                        gamemaster = ?
                    WHERE ID = ?
                """, (
                    p1.strip(), p2.strip(), p3.strip(), p4.strip(),
                    int(poydan_alla),
                    kesto_aikana,
                    *tallennettavat_juomat,
                    nykyinen_voitto,
                    uusi_pvm_python,
                    tallennettava_kommentti,
                    tallennettava_gm,
                    peli_id
                ))
                conn.commit()
            QMessageBox.information(self, "Onnistui",
                                    "Pelin tiedot päivitetty.")
            dialog.accept()
            self.hae_pelit()
        except Exception as e:
            QMessageBox.critical(self, "Virhe", f"Virhe tallennettaessa: {e}")

    def poista_peli(self, peli_id: int, dialog: QDialog):
        """Poistetaan valittu peli

        :param peli_id:
        :param dialog:
        :return:
        """
        vastaus = QMessageBox.question(
            self,
            "Vahvista poisto",
            f"Haluatko varmasti poistaa pelin ID {peli_id}? Toimintoa ei voi perua.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if vastaus == QMessageBox.StandardButton.Yes:
            try:
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM {table} WHERE ID = ?",
                                   (peli_id,))
                    conn.commit()
                QMessageBox.information(self, "Poistettu",
                                        "Peli poistettiin onnistuneesti.")
                dialog.accept()  # Sulje editointi-ikkuna
                self.hae_pelit()  # Päivitä pääikkunan taulukko
            except Exception as e:
                QMessageBox.critical(self, "Virhe",
                                     f"Pelin poistaminen epäonnistui:\n{e}")

    def reset_graafi(self):
        # Poista vanha canvas, jos sellainen on jo lisättynä
        if hasattr(self, 'graafi_canvas') and self.graafi_canvas is not None:
            self.graafi_container.removeWidget(self.graafi_canvas)
            self.graafi_canvas.setParent(None)
            self.graafi_canvas = None

        # Luo uusi figure ja canvas
        self.graafi_fig = Figure(figsize=(7, 4))
        self.graafi_fig.patch.set_facecolor("#2b2b2b")
        self.graafi_canvas = FigureCanvas(self.graafi_fig)
        self.graafi_ax = self.graafi_fig.add_subplot(111)
        self.graafi_ax.set_facecolor("#2b2b2b")
        self.graafi_ax.tick_params(colors='white')
        self.graafi_ax.spines['bottom'].set_color('white')
        self.graafi_ax.spines['left'].set_color('white')

        # Lisää uusi canvas comboboxien ALLE
        self.graafi_container.addWidget(self.graafi_canvas)
        self.graafi_canvas.setMinimumWidth(500)
        self.graafi_fig.tight_layout()
        self.graafi_canvas.draw()

    def kopioi_valitut_solut(self):
        """Kopioi valitut solut leikepöydälle Excel-muodossa (Tab-erottelu, rivinvaihdot)"""
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            return

        copied_text = ""

        for selection in selected_ranges:
            for row in range(selection.topRow(), selection.bottomRow() + 1):
                row_data = []
                for col in range(selection.leftColumn(),
                                 selection.rightColumn() + 1):
                    item = self.table.item(row, col)
                    if item is not None:
                        row_data.append(item.text())
                    else:
                        row_data.append("")
                copied_text += "\t".join(row_data) + "\n"

        clipboard = QApplication.clipboard()
        clipboard.setText(copied_text.strip())

    def taulukko_keypress(self, event):
        """Tarkistaa onko Ctrl+C painettu taulukossa"""
        if event.key() == Qt.Key_C and (
                event.modifiers() & Qt.ControlModifier):
            self.kopioi_valitut_solut()
        else:
            QTableWidget.keyPressEvent(self.table, event)

    def nayta_voittoprosentti_graafi(self):
        self.graafi_fig.clear()
        ax = self.graafi_fig.add_subplot(111)
        self.graafi_fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')

        nimi = self.search_input.text().strip().lower()
        if not nimi:
            QMessageBox.warning(self, "Ei pelaajaa", "Syötä pelaajan nimi.")
            return

        # Haetaan vain ne pelit, joissa pelaaja esiintyy
        query = f"""
            SELECT {game_date},
                   CASE 
                       WHEN LOWER({winner1}) = ? OR LOWER({winner2}) = ? 
                       THEN 1 
                       ELSE 0 
                   END AS Voitto
            FROM {table}
            WHERE LOWER({winner1}) = ? OR LOWER({winner2}) = ? 
                  OR LOWER({loser1}) = ? OR LOWER({loser2}) = ?
            ORDER BY {game_date}
        """
        with conn.cursor() as cur:
            cur.execute(query, (nimi, nimi, nimi, nimi, nimi, nimi))
            rows = cur.fetchall()

        if not rows:
            QMessageBox.information(self, "Ei pelejä",
                                    "Pelaajalla ei ole pelejä.")
            return

        # Lasketaan voittoprosentti kumulatiivisesti ilman isoja välilistoja
        prosentit = []
        voitot = 0
        for i, rivi in enumerate(rows, start=1):
            voitot += rivi.Voitto
            prosentit.append(100 * voitot / i)

        # Piirretään ilman yksittäisiä markkereita (kevyempi muistille)
        ax.plot(range(1, len(prosentit) + 1), prosentit,
                color='white', linewidth=1)

        # Tekstien värit valkoiseksi
        ax.set_title(f"{nimi} – Voittoprosentin kehitys", color='white')
        ax.set_xlabel("Peli nro", color='white')
        ax.set_ylabel("Voittoprosentti (%)", color='white')

        # Akselit ja ruudukko
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')
        ax.grid(color='gray', linestyle='dotted', linewidth=0.5)

        self.graafi_fig.tight_layout()

        self.graafi_canvas.draw()

    def nayta_pelimaara_graafi(self):
        """Piirtää pelaajan kumulatiivisen pelimäärän kehityksen (tehostettu versio)."""

        pelaaja_nimi = self.search_input.text().strip().lower()
        if not pelaaja_nimi:
            QMessageBox.warning(self, "Valitse pelaaja",
                                "Valitse pelaaja pudotusvalikosta.")
            return

        self.graafi_fig.clear()
        ax = self.graafi_fig.add_subplot(111)
        self.graafi_fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')

        # Haetaan pelien määrät valmiiksi ryhmiteltynä päivittäin SQL:ssä
        query = f"""
            SELECT CAST({game_date} AS DATE) AS Paiva, COUNT(*) AS Pelit
            FROM {table}
            WHERE (LOWER({winner1}) = ? OR LOWER({winner2}) = ? 
                   OR LOWER({loser1}) = ? OR LOWER({loser2}) = ?)
              AND {game_date} IS NOT NULL
            GROUP BY CAST({game_date} AS DATE)
            ORDER BY Paiva
        """
        try:
            with conn.cursor() as cur:
                cur.execute(query, (pelaaja_nimi, pelaaja_nimi, pelaaja_nimi,
                                       pelaaja_nimi))
                rows = cur.fetchall()
        except Exception as e:
            QMessageBox.critical(self, "Tietokantavirhe",
                                 f"Virhe haettaessa pelejä:\n{e}")
            return

        if not rows:
            QMessageBox.information(self, "Ei pelejä",
                                    "Valitulla pelaajalla ei ole pelejä.")
            return

        # Lasketaan kumulatiivinen summa
        dates = [r.Paiva for r in rows]
        counts = [r.Pelit for r in rows]

        cum_counts = np.cumsum(counts)

        # Piirretään vain viiva (ei markkereita → kevyempi muistille)
        ax.plot(dates, cum_counts, color='white', linewidth=1.5)

        # Otsikot ja ulkoasu
        ax.set_title(f"{pelaaja_nimi} – Pelien määrän kehitys", color='white')
        ax.set_xlabel("Päivämäärä", color='white')
        ax.set_ylabel("Kumulatiivinen pelien määrä", color='white')

        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')
        ax.grid(color='gray', linestyle='dotted', linewidth=0.5)

        # Päivämäärien muotoilu x-akselilla
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        for label in ax.get_xticklabels():
            label.set_rotation(90)
            label.set_horizontalalignment('center')

        self.graafi_fig.tight_layout()
        self.graafi_canvas.draw()

    def nayta_keskiajan_kehitys_graafi(self):
        self.graafi_fig.clear()
        ax = self.graafi_fig.add_subplot(111)
        self.graafi_fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')

        nimi = self.search_input.text().strip().lower()
        if not nimi:
            QMessageBox.warning(self, "Ei pelaajaa", "Syötä pelaajan nimi.")
            return

        # Haetaan vain ne pelit, joissa pelaaja esiintyy
        query = f"""
            SELECT {game_date}, {game_time}
            FROM {table}
            WHERE LOWER({winner1}) = ? OR LOWER({winner2}) = ? 
                  OR LOWER({loser1}) = ? OR LOWER({loser2}) = ?
            ORDER BY {game_date}
        """
        with conn.cursor() as cur:
            cur.execute(query, (nimi, nimi, nimi, nimi))
            rows = cur.fetchall()

        if not rows:
            QMessageBox.information(self, "Ei pelejä",
                                    "Pelaajalla ei ole pelejä.")
            return

        keskiajat = []
        kesto_summa = 0

        for i, (pvm, kesto) in enumerate(rows, start=1):
            # Muutetaan time -> sekunnit
            sek = kesto.hour * 3600 + kesto.minute * 60 + kesto.second
            kesto_summa += sek
            keskiajat.append(kesto_summa / i)

        # Piirretään ilman yksittäisiä markkereita (kevyempi muistille)
        ax.plot(range(1, len(keskiajat) + 1), keskiajat,
                color='white', linewidth=1)

        # Tekstit ja ulkoasu
        ax.set_title(f"{nimi} – Keskiajan kehitys", color='white')
        ax.set_xlabel("Peli nro", color='white')
        ax.set_ylabel("Keskiaika (sek)", color='white')

        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')
        ax.grid(color='gray', linestyle='dotted', linewidth=0.5)

        self.graafi_fig.tight_layout()

        self.graafi_canvas.draw()

    def nayta_paivan_pelimaara_voittoprosentti_tiheyksilla(self):
        """
        Piirtää päivän pelimäärän ja voittoprosentin välisen riippuvuuden
        (tehostettu versio).
        """
        self.graafi_fig.clear()
        ax = self.graafi_fig.add_subplot(111)
        self.graafi_fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')

        nimi = self.search_input.text().strip().lower()
        if not nimi:
            QMessageBox.warning(self, "Ei pelaajaa", "Syötä pelaajan nimi.")
            return

        # Haetaan vain rivit, joissa pelaaja on mukana
        query = f"""
            SELECT {game_date},
                   CASE 
                       WHEN LOWER({winner1}) = ? OR LOWER({winner2}) = ? THEN 1
                       ELSE 0
                   END AS Voitto
            FROM {table}
            WHERE LOWER({winner1}) = ? OR LOWER({winner2}) = ? 
                  OR LOWER({loser1}) = ? OR LOWER({loser2}) = ?
            ORDER BY {game_date}
        """
        with conn.cursor() as cur:
            cur.execute(query, (nimi, nimi, nimi, nimi, nimi, nimi))
            rows = cur.fetchall()

        if not rows:
            QMessageBox.information(self, "Ei pelejä",
                                    "Pelaajalla ei ole pelejä.")
            return

        paiva_stats = defaultdict(lambda: [0, 0])  # {päivä: [pelit, voitot]}
        for pvm, voitto in rows:
            # Päivän laskenta 03:00 cutoffilla
            if pvm.time() < datetime.strptime("03:00:00", "%H:%M:%S").time():
                oikea_pvm = (pvm - timedelta(days=1)).date()
            else:
                oikea_pvm = pvm.date()

            paiva_stats[oikea_pvm][0] += 1  # pelit
            paiva_stats[oikea_pvm][1] += voitto  # voitot

        # Rakennetaan pistetiheys
        pistetiheys = Counter()
        for (pelit, voitot) in paiva_stats.values():
            if pelit > 0:
                vp = 100 * voitot / pelit
                pistetiheys[(pelit, vp)] += 1

        if not pistetiheys:
            QMessageBox.information(self, "Ei dataa",
                                    "Pelaajalle ei löytynyt tarpeeksi pelattuja päiviä.")
            return

        # Scatter vektoroituna
        x_vals, y_vals, counts = zip(
            *[(x, y, c) for (x, y), c in pistetiheys.items()])
        sc = ax.scatter(x_vals, y_vals, c="white", edgecolors="white", s=20)

        # Lisää xN -tekstit toistuville pisteille
        for x, y, c in zip(x_vals, y_vals, counts):
            if c > 1:
                ax.text(x + 0.1, y + 0.1, f"x{c}", fontsize=8, color='white')

        # Sovite (2. aste)
        x_arr = np.array(x_vals)
        y_arr = np.array(y_vals)
        coeffs = np.polyfit(x_arr, y_arr, deg=2)
        poly = np.poly1d(coeffs)
        x_fit = np.linspace(min(x_arr), max(x_arr), 200)
        y_fit = poly(x_fit)
        ax.plot(x_fit, y_fit, color='white', linewidth=2,
                label="2. asteen sovite")
        ax.legend(facecolor='#2b2b2b', edgecolor='white', labelcolor='white')

        # Ulkoasu
        ax.set_title(f"{nimi} – Päivän pelimäärän vaikutus voittoprosenttiin",
                     color='white')
        ax.set_xlabel("Pelien määrä päivän aikana", color='white')
        ax.set_ylabel("Voittoprosentti (%)", color='white')
        ax.set_xlim(0.5, max(x_arr) + 0.5)
        ax.set_ylim(-5, 105)
        ax.xaxis.set_major_locator(MultipleLocator(1))
        ax.yaxis.set_major_locator(MultipleLocator(10))
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')
        ax.grid(color='gray', linestyle='dotted', linewidth=0.5)

        self.graafi_fig.tight_layout()

        self.graafi_canvas.draw()

    def nayta_ennatyskooste(self):
        """Näytetään pelien ennätykset kooste-labeliin."""

        try:
            with conn.cursor() as cur:
                # --- MUUTOS: Haetaan sekä Pelit että PoydanAlla samalla kertaa ---
                # Tämä on todella nopea kysely verrattuna aiempaan
                cur.execute(f"""
                    SELECT LOWER(LTRIM(RTRIM(Nimi))), Pelit, PoydanAlla 
                    FROM {profile_table} 
                    WHERE Pelit > 0 OR PoydanAlla > 0
                """)
                profiilit = cur.fetchall()

            # 1. Lasketaan eniten pelanneet (indeksi 1 = Pelit)
            if profiilit:
                max_pelit = max(r[1] for r in profiilit)
                eniten_pelaajat = [r[0] for r in profiilit if
                                   r[1] == max_pelit]
            else:
                max_pelit = 0
                eniten_pelaajat = ["-"]

            # 2. Lasketaan eniten pöydän alla (indeksi 2 = PoydanAlla)
            # Suodatetaan ensin ne, joilla on pöydän alla -merkintöjä (>0)
            poydan_alla_lista = [r for r in profiilit if r[2] > 0]

            if poydan_alla_lista:
                max_poydan_alla = max(r[2] for r in poydan_alla_lista)
                poydan_alla_pelaajat = [r[0] for r in poydan_alla_lista if
                                        r[2] == max_poydan_alla]
            else:
                max_poydan_alla = 0
                poydan_alla_pelaajat = ["-"]

            # --- Nopein ja hitain peli (Tämä vaatii edelleen pelihistorian hakua) ---
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT TOP 1 {game_time}, {game_date}, {winner1}, {winner2}, {loser1}, {loser2}
                    FROM {table} ORDER BY {game_time} ASC
                """)
                nopein_peli = cur.fetchone()

                cur.execute(f"""
                    SELECT TOP 1 {game_time}, {game_date}, {winner1}, {winner2}, {loser1}, {loser2}
                    FROM {table} ORDER BY {game_time} DESC
                """)
                hitain_peli = cur.fetchone()

            def muotoile_peli(rivi):
                if not rivi: return "-", "-", []

                # Käsitellään aika (voi olla datetime.time tai timedelta tai string riippuen ajurista)
                raw_time = rivi[0]
                if hasattr(raw_time, 'hour'):
                    sekunnit = raw_time.hour * 3600 + raw_time.minute * 60 + raw_time.second
                    aika = format_seconds(sekunnit)
                else:
                    aika = str(raw_time)

                pvm = rivi[1].strftime("%d.%m.%Y")
                pelaajat = [p for p in rivi[2:] if p]
                return aika, pvm, pelaajat

            nopein_aika, nopein_pvm, nopein_pelaajat = muotoile_peli(
                nopein_peli)
            hitain_aika, hitain_pvm, hitain_pelaajat = muotoile_peli(
                hitain_peli)

            # --- Haetaan kaikki päivämäärä + pelaajat aikajaksoennätyksiä varten ---
            # Tätä ei voi ottaa profiilitaulusta, koska tarvitsemme tarkat päivämäärät
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT {game_date}, {winner1}, {winner2}, {loser1}, {loser2}
                    FROM {table}
                """)
                rows = cur.fetchall()

            paiva_laskuri, viikko_laskuri, kuukausi_laskuri, lukuvuosi_laskuri = {}, {}, {}, {}

            for pelipvm, p1, p2, p3, p4 in rows:
                # Jos peli ennen klo 03:00, lasketaan edelliseen päivään
                if pelipvm.time() < dt_time(3, 0):
                    paiva = (pelipvm - timedelta(days=1)).date()
                else:
                    paiva = pelipvm.date()

                pelaajat = set(p.lower() for p in (p1, p2, p3, p4) if p)

                # Päivä
                for p in pelaajat:
                    paiva_laskuri[(paiva, p)] = paiva_laskuri.get((paiva, p),
                                                                  0) + 1

                # Viikko (maanantai–sunnuntai)
                viikon_alku = paiva - timedelta(days=paiva.weekday())
                viikon_loppu = viikon_alku + timedelta(days=6)
                viikon_alku_dt = datetime.combine(viikon_alku, dt_time.min)
                viikon_loppu_dt = datetime.combine(viikon_loppu, dt_time.max)
                for p in pelaajat:
                    viikko_laskuri[(viikon_alku_dt, viikon_loppu_dt,
                                    p)] = viikko_laskuri.get(
                        (viikon_alku_dt, viikon_loppu_dt, p), 0
                    ) + 1

                # Kuukausi
                for p in pelaajat:
                    kuukausi_laskuri[
                        (paiva.year, paiva.month, p)] = kuukausi_laskuri.get(
                        (paiva.year, paiva.month, p), 0
                    ) + 1

                # Lukuvuosi
                lukuvuosi = paiva.year - 1 if paiva.month < 7 else paiva.year
                for p in pelaajat:
                    lukuvuosi_laskuri[(lukuvuosi, p)] = lukuvuosi_laskuri.get(
                        (lukuvuosi, p), 0
                    ) + 1

            # --- Etsitään maksimit aikajaksoille ---
            def etsi_maksimit_ja_formatointi(laskuri, tyyppi):
                if not laskuri: return [], 0, []
                maksimi = max(laskuri.values())
                parhaat = [key for key, n in laskuri.items() if n == maksimi]
                return parhaat, maksimi

            paivapelien_pelaajat, max_paivapelimaara = etsi_maksimit_ja_formatointi(
                paiva_laskuri, "paiva")
            viikkopelien_pelaajat, max_viikkopelit = etsi_maksimit_ja_formatointi(
                viikko_laskuri, "viikko")
            kuukausipelien_pelaajat, max_kuukausipelit = etsi_maksimit_ja_formatointi(
                kuukausi_laskuri, "kuukausi")
            lukuvuoden_pelaajat, max_lukuvuosipelit = etsi_maksimit_ja_formatointi(
                lukuvuosi_laskuri, "lukuvuosi")

            # --- Koosteen teksti ---
            teksti = f"""
            <b>Ennätykset</b><br><br>
            <b>Nopein peli:</b> {nopein_aika} ({', '.join(nopein_pelaajat)})  
                <i>({nopein_pvm})</i><br>
            <b>Hitain peli:</b> {hitain_aika} ({', '.join(hitain_pelaajat)})  
                <i>({hitain_pvm})</i><br>
            <b>Eniten pelejä päivän aikana:</b> {', '.join([p for d, p in paivapelien_pelaajat])} ({max_paivapelimaara})&nbsp;&nbsp;&nbsp;&nbsp;{', '.join([d.strftime('%d.%m.%Y') for d, p in paivapelien_pelaajat])}<br>
            <b>Eniten pelejä viikon aikana:</b> {', '.join([p for a, l, p in viikkopelien_pelaajat])} ({max_viikkopelit})&nbsp;&nbsp;&nbsp;&nbsp;{', '.join([f"{a.strftime('%d.%m.%Y')} – {l.strftime('%d.%m.%Y')}" for a, l, p in viikkopelien_pelaajat])}<br>
            <b>Eniten pelejä kuukauden aikana:</b> {', '.join([p for (y, m, p) in kuukausipelien_pelaajat])} ({max_kuukausipelit})&nbsp;&nbsp;&nbsp;&nbsp;{', '.join([f"{y}-{m:02d}" for (y, m, p) in kuukausipelien_pelaajat])}<br>
            <b>Eniten pelejä lukuvuoden aikana:</b> {', '.join([p for v, p in lukuvuoden_pelaajat])} ({max_lukuvuosipelit})&nbsp;&nbsp;&nbsp;&nbsp;{', '.join([f"Lukuvuosi {v}-{v + 1}" for v, p in lukuvuoden_pelaajat])}<br>
            <b>Eniten pöydän alla:</b> {', '.join(poydan_alla_pelaajat)} ({max_poydan_alla})<br>
            <b>Eniten pelejä koskaan:</b> {', '.join(eniten_pelaajat)} ({max_pelit})<br>
            """
            self.stats_label.setText(teksti)

        except Exception as e:
            QMessageBox.critical(self, "Virhe",
                                 f"Virhe ennätyskoostetta haettaessa:\n{e}")

    def nayta_yhteiset_ennatykset(self):
        """Näytä yhteiset pelien ennätykset: päivä, viikko, kuukausi, lukuvuosi (cut-off 30.6.)."""
        try:
            # Haetaan vain ajat
            with conn.cursor() as cur:
                cur.execute(f"SELECT {game_date} FROM {table}")
                rows = cur.fetchall()
            if not rows:
                self.stats_label.setText("Ei pelejä.")
                return

            # Kertymät
            paiva_total = {}  # date -> count
            viikko_total = {}  # (start_date, end_date) -> count
            kuukausi_total = {}  # (year, month) -> count
            lukuvuosi_total = {}  # school_year_start_year -> count

            for (pelipvm,) in rows:
                # 03:00 leikkuri
                if pelipvm.time() < dt_time(3, 0):
                    paiva = (pelipvm - timedelta(days=1)).date()
                else:
                    paiva = pelipvm.date()

                # Päivä
                paiva_total[paiva] = paiva_total.get(paiva, 0) + 1

                # Viikko (ma–su)
                viikon_alku = paiva - timedelta(days=paiva.weekday())
                viikon_loppu = viikon_alku + timedelta(days=6)
                viikko_total[(viikon_alku, viikon_loppu)] = viikko_total.get(
                    (viikon_alku, viikon_loppu), 0) + 1

                # Kuukausi
                kuukausi_total[(paiva.year, paiva.month)] = kuukausi_total.get(
                    (paiva.year, paiva.month), 0) + 1

                # Lukuvuosi: 1.7.–30.6., cut-off 30.6.
                # Jos kuukausi < 7, peli kuuluu edellisen vuoden lukuvuoteen
                lv = paiva.year - 1 if paiva.month < 7 else paiva.year
                lukuvuosi_total[lv] = lukuvuosi_total.get(lv, 0) + 1

            # Maksimit ja ajankohdat
            max_pv = max(paiva_total.values())
            pv_ajat = sorted(
                [d for d, n in paiva_total.items() if n == max_pv])

            max_vk = max(viikko_total.values())
            vk_ajat = sorted(
                [rng for rng, n in viikko_total.items() if n == max_vk],
                key=lambda x: x[0])

            max_kk = max(kuukausi_total.values())
            kk_ajat = sorted(
                [ym for ym, n in kuukausi_total.items() if n == max_kk])

            max_lv = max(lukuvuosi_total.values())
            lv_ajat = sorted(
                [v for v, n in lukuvuosi_total.items() if n == max_lv])

            # Muotoilu
            pv_str = f"{max_pv} — " + ", ".join(
                d.strftime("%d.%m.%Y") for d in pv_ajat)
            vk_str = f"{max_vk} — " + ", ".join(
                f"{a.strftime('%d.%m.%Y')} – {l.strftime('%d.%m.%Y')}" for a, l
                in vk_ajat)
            kk_str = f"{max_kk} — " + ", ".join(
                f"{y}-{m:02d}" for y, m in kk_ajat)
            lv_str = f"{max_lv} — " + ", ".join(
                f"Lukuvuosi {v}-{v + 1}" for v in lv_ajat)

            teksti = (
                "<b>Yhteiset ennätykset</b><br><br>"
                f"<b>Eniten pelejä päivässä:</b> {pv_str}<br>"
                f"<b>Eniten pelejä viikossa:</b> {vk_str}<br>"
                f"<b>Eniten pelejä kuukaudessa:</b> {kk_str}<br>"
                f"<b>Eniten pelejä lukuvuodessa:</b> {lv_str}<br>"
            )
            self.stats_label.setText(teksti)

        except Exception as e:
            self.stats_label.setText(f"Virhe: {e}")

    def nayta_juomien_varit(self):
        """Näyttää pelkästään juomien värikoodit koosteessa."""
        variselite = (
            "<b>Juomien värikoodit:</b><br><br>"
            "<span style='background-color:#8B6508; color:white;'>&nbsp;Kalja&nbsp;</span><br><br>"
            "<span style='background-color:#36648B; color:white;'>&nbsp;Vichy&nbsp;</span><br><br>"
            "<span style='background-color:#556B2F; color:white;'>&nbsp;Siideri&nbsp;</span><br><br>"
            "<span style='background-color:#708090; color:white;'>&nbsp;Lonkero&nbsp;</span><br><br>"
            "<span style='background-color:#8B008B; color:white;'>&nbsp;Hard Seltzer&nbsp;</span><br><br>"
            "<span style='background-color:#CD5C5C; color:white;'>&nbsp;Limsa&nbsp;</span><br><br>"
            "<span style='background-color:#B8860B; color:white;'>&nbsp;Energiajuoma&nbsp;</span>"
        )
        self.stats_label.setText(variselite)

    def solo_pelit(self):
        """Näyttää vain ne pelit, joissa {winner1}, {winner2}, {loser1} ja
        {loser2} ovat sama pelaaja (soolopelit)

        """
        query = f"""
                SELECT ID, {game_date}, {game_time}, {winner1}, {winner2}, {loser1}, {loser2}, {under_table}
                FROM {table}
                WHERE LOWER({winner1}) = LOWER({winner2})
                  AND LOWER({winner1}) = LOWER({loser1})
                  AND LOWER({winner1}) = LOWER({loser2})
                ORDER BY ID DESC
            """
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                results = cur.fetchall()
        except Exception as e:
            QMessageBox.critical(self, "Virhe",
                                 f"Virhe haettaessa soolopelejä:\n{e}")
            return

        self.tilastodata = [list(r) for r in results]
        self.paivita_tilastot()
        self.stats_label.setText(f"Soolopelejä löytyi {len(results)} kpl.")

    def nayta_peliaikojen_barplot(self):
        self.reset_graafi()

        query = f"""
            SELECT {game_date}
            FROM {table}
        """

        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
        except Exception as e:
            QMessageBox.critical(self, "Virhe", f"Virhe haettaessa dataa: {e}")
            return

        if not rows:
            QMessageBox.information(self, "Ei dataa", "Ei pelattuja pelejä.")
            return

        # Lasketaan pelimäärät tunneittain
        tuntien_laskuri = [0] * 24

        for rivi in rows:
            pvm = rivi[0]
            if pvm.time() < datetime.strptime("03:00:00", "%H:%M:%S").time():
                oikea_pvm = pvm - timedelta(days=1)
            else:
                oikea_pvm = pvm
            tunti = oikea_pvm.hour
            tuntien_laskuri[tunti] += 1

        # Piirretään pylväsdiagrammi
        self.graafi_fig.clear()
        ax = self.graafi_fig.add_subplot(111)
        self.graafi_fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')

        bars = ax.bar(range(24), tuntien_laskuri, color='gray',
                      edgecolor='white',
                      align='edge')

        ax.bar_label(bars, fmt='%d', color='white', padding=3)

        ax.set_title("Peliaikojen jakauma (tunnit)", color='white')
        ax.set_xlabel("Tunti", color='white')
        ax.set_ylabel("Pelien määrä", color='white')

        ax.set_xticks(range(24))
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.grid(color='gray', linestyle='dotted', linewidth=0.5, axis='y')

        self.graafi_fig.tight_layout()

        self.graafi_canvas.draw()

    def nayta_pelikestot_barplot(self):
        self.reset_graafi()

        query = f"""
            SELECT {game_time}
            FROM {table}
        """

        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
        except Exception as e:
            QMessageBox.critical(self, "Virhe", f"Virhe haettaessa dataa: {e}")
            return

        if not rows:
            QMessageBox.information(self, "Ei dataa", "Ei pelattuja pelejä.")
            return

        # Kerätään kestot sekunteina ja suodatetaan 20s-400s väliin
        kesto_sekunnit = []
        for rivi in rows:
            kesto = rivi[0]
            sekunnit = kesto.hour * 3600 + kesto.minute * 60 + kesto.second
            if sekunnit >= 20:
                # Niputetaan kaikki yli 400s kestävät pelit viimeiseen palkkiin
                if sekunnit >= 400:
                    sekunnit = 405
                kesto_sekunnit.append(sekunnit)

        if not kesto_sekunnit:
            QMessageBox.information(self, "Ei dataa",
                                    "Ei pelejä valitulla kestovälillä.")
            return

        # Histogrammi 10 sekunnin välein 20-410s
        bins = list(range(20, 411, 10))

        counts, edges = np.histogram(kesto_sekunnit, bins=bins)

        self.graafi_fig.clear()
        ax = self.graafi_fig.add_subplot(111)
        self.graafi_fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')

        # Piirretään histogrammi pylväinä ja otetaan ne talteen 'bars'-muuttujaan
        bars = ax.bar(edges[:-1], counts, width=np.diff(edges), align='edge',
                      color='gray', edgecolor='white')
        
        # Lisätään määrät pylväiden päälle ---
        # Käytetään listakomprehensiota, jotta nollia (0) ei tulosteta turhaan tyhjiin väleihin
        labels = [str(int(v)) if v > 0 else "" for v in counts]
        ax.bar_label(bars, labels=labels, color='white', padding=3)

        # xtickit binien reunoihin (20, 30, 40, ... 400)
        ax.set_xticks(edges)
        ax.set_xlim(20, 410)
        ax.set_xticklabels(ax.get_xticklabels(),
                           rotation=90)  # 90 astetta = pystyyn

        xticks = edges[:-1].copy()
        xticklabels = [str(int(e)) for e in edges[:-1]]
        xticklabels[-1] = "400+"

        ax.set_xticks(xticks)
        ax.set_xticklabels(xticklabels, rotation=90, color='white')

        ax.set_title("Pelien keston jakauma (20-400s)", color='white')
        ax.set_xlabel("Kesto (s)", color='white')
        ax.set_ylabel("Pelien määrä", color='white')

        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.grid(color='gray', linestyle='dotted', linewidth=0.5, axis='y')
        ax.set_ylim(top=ax.get_ylim()[1] * 1.10)

        self.graafi_fig.tight_layout()
        self.graafi_canvas.draw()

    def nayta_kumulatiivinen_pelit(self):
        self.reset_graafi()

        query = f"""
            SELECT {game_date}
            FROM {table}
            ORDER BY {game_date} ASC
        """

        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
        except Exception as e:
            QMessageBox.critical(self, "Virhe", f"Virhe haettaessa dataa: {e}")
            return

        if not rows:
            QMessageBox.information(self, "Ei dataa", "Ei pelattuja pelejä.")
            return

        # Lasketaan kumulatiivinen määrä
        ajat = [rivi[0] for rivi in rows]
        kumulatiivinen = list(range(1, len(ajat) + 1))

        # Piirretään viivadiagrammi
        self.graafi_fig.clear()
        ax = self.graafi_fig.add_subplot(111)
        self.graafi_fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')

        ax.plot(ajat, kumulatiivinen, color='white', linewidth=2)

        ax.set_title("Kumulatiivinen pelimäärä", color='white')
        ax.set_xlabel("Aika", color='white')
        ax.set_ylabel("Pelien määrä", color='white')

        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.grid(color='gray', linestyle='dotted', linewidth=0.5, axis='both')

        self.graafi_fig.tight_layout()
        self.graafi_canvas.draw()

    def nayta_keskiaikojen_muutos(self):
        self.reset_graafi()

        query = f"""
            SELECT {game_date}, {game_time}
            FROM {table}
            ORDER BY {game_date} ASC
        """

        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
        except Exception as e:
            QMessageBox.critical(self, "Virhe", f"Virhe haettaessa dataa: {e}")
            return

        if not rows:
            QMessageBox.information(self, "Ei dataa", "Ei pelattuja pelejä.")
            return

        ajat = []
        keskiajat = []
        kum_summa = 0

        for i, rivi in enumerate(rows, start=1):
            pvm, kesto = rivi
            sekunnit = kesto.hour * 3600 + kesto.minute * 60 + kesto.second
            kum_summa += sekunnit
            keskiaika = kum_summa / i
            ajat.append(pvm)
            keskiajat.append(keskiaika)

        # Piirretään viivadiagrammi
        self.graafi_fig.clear()
        ax = self.graafi_fig.add_subplot(111)
        self.graafi_fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')

        ax.plot(ajat, keskiajat, color='white', linewidth=2)

        ax.set_title("Keskiaikojen muutos", color='white')
        ax.set_xlabel("Aika", color='white')
        ax.set_ylabel("Keskiaika (s)", color='white')

        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.grid(color='gray', linestyle='dotted', linewidth=0.5, axis='both')

        self.graafi_fig.tight_layout()
        self.graafi_canvas.draw()

    def nayta_tiimien_voitto_pie(self):
        """Piirakkagraafi: Ikkunaseinä vs. Julisteseinä. Ohittaa NULL/None-voitot."""
        self.graafi_fig.clear()
        ax = self.graafi_fig.add_subplot(111)
        self.graafi_fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')

        query = f"""
            SELECT
                SUM(CASE WHEN {winner_side} = 1 THEN 1 ELSE 0 END) AS 
                Ikkunaseina,
                SUM(CASE WHEN {winner_side} = 0 THEN 1 ELSE 0 END) AS 
                Julisteseina
            FROM {table}
            WHERE CAST({game_date} AS DATE) >= '2025-09-15'
              AND {winner_side} IS NOT NULL
        """
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                row = cur.fetchone()
        except Exception as e:
            QMessageBox.critical(self, "Tietokantavirhe",
                                 f"Virhe haettaessa tiimien voittoja:\n{e}")
            return

        if not row:
            QMessageBox.information(self, "Ei tietoja",
                                    "Tietokannassa ei ole pelejä.")
            return

        ikk = int(row.Ikkunaseina or 0)
        jul = int(row.Julisteseina or 0)
        total = ikk + jul
        if total == 0:
            QMessageBox.information(self, "Ei tietoja",
                                    "Ei voittoja valitulla aikavälillä (vain NULL-merkintöjä).")
            return

        values = [ikk, jul]
        labels = ["Ikkunaseinä", "Julisteseinä"]

        # Piirakka
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            autopct=lambda
                p: f"{p:.1f}%\n({int(round(p * total / 100))})" if p > 0 else "",
            startangle=90,
            textprops={'color': 'white'},
            wedgeprops={'edgecolor': 'white', 'linewidth': 1.0}
        )
        ax.axis('equal')  # ympyrä

        ax.set_title("Tiimien voitot (15.9.2025 →)", color='white')
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')

        self.graafi_fig.tight_layout()
        self.graafi_canvas.draw()

    def nayta_pelimaara_vs_paivan_keskiaika(self):
        """Päivän pelimäärä vs. päivän keskiaika. Leikkaus 3:00 ja leikatut pisteet merkitään."""
        # Ulkoasu kuten muissa
        self.graafi_fig.clear()
        ax = self.graafi_fig.add_subplot(111)
        self.graafi_fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')

        nimi_raw = self.search_input.text().strip()
        if not nimi_raw:
            QMessageBox.warning(self, "Ei pelaajaa", "Syötä pelaajan nimi.")
            return
        nimi = nimi_raw.lower()

        # Haku: vain pelit joissa pelaaja mukana
        query = f"""
            SELECT {game_date}, {game_time}
            FROM {table}
            WHERE LOWER({winner1})=? OR LOWER({winner2})=?
               OR LOWER({loser1})=? OR LOWER({loser2})=?
            ORDER BY {game_date}
        """
        with conn.cursor() as cur:
            cur.execute(query, (nimi, nimi, nimi, nimi))
            rows = cur.fetchall()
        if not rows:
            QMessageBox.information(self, "Ei pelejä",
                                    "Pelaajalla ei ole pelejä.")
            return

        # Päiväkohtaiset kestot 03:00 cutoffilla
        paiva_kestot = defaultdict(list)
        cutoff = datetime.strptime("03:00:00", "%H:%M:%S").time()
        for pvm, kesto in rows:
            sek = kesto.hour * 3600 + kesto.minute * 60 + kesto.second
            oikea_pvm = (pvm - timedelta(
                days=1)).date() if pvm.time() < cutoff else pvm.date()
            paiva_kestot[oikea_pvm].append(sek)

        # Jokaisesta päivästä piste: (pelien määrä sinä päivänä, päivän keskiaika sekunteina)
        xs, ys = [], []
        for sek_list in paiva_kestot.values():
            n = len(sek_list)
            if n:
                xs.append(n)
                ys.append(float(np.mean(sek_list)))

        if not xs:
            QMessageBox.information(self, "Ei dataa", "Ei kelvollisia päiviä.")
            return

        xs_arr = np.asarray(xs, dtype=float)
        ys_arr = np.asarray(ys, dtype=float)

        # Leikkaus 3:00. Leikatut merkitään kolmioina yläreunan alle.
        cap_sec = 180.0
        pad = 5.0
        mask_clip = ys_arr > cap_sec

        # Ei-leikatut pisteet
        ax.scatter(xs_arr[~mask_clip], ys_arr[~mask_clip],
                   c="white", edgecolors="white", s=20)

        # Leikatut pisteet kolmioina
        if mask_clip.any():
            ax.scatter(xs_arr[mask_clip],
                       np.full(mask_clip.sum(), cap_sec - 0.5),
                       marker='^', facecolors='none', edgecolors='white', s=30,
                       label="> 03:00")

        # Sovite: käytä leikatun datan arvoja
        if xs_arr.size >= 3:
            ys_fit = np.minimum(ys_arr, cap_sec)
            coeffs = np.polyfit(xs_arr, ys_fit, deg=2)
            poly = np.poly1d(coeffs)
            x_fit = np.linspace(xs_arr.min(), xs_arr.max(), 200)
            y_fit = poly(x_fit)
            ax.plot(x_fit, y_fit, color='white', linewidth=2,
                    label="2. asteen sovite")
            ax.legend(facecolor='#2b2b2b', edgecolor='white',
                      labelcolor='white')

        # Akselit
        ax.set_title(f"{nimi_raw} – Päivän pelimäärän vaikutus keskiaikaan",
                     color='white')
        ax.set_xlabel("Pelien määrä päivän aikana", color='white')
        ax.set_ylabel("Keskiaika (mm:ss)", color='white')

        ax.set_xlim(0.5, float(xs_arr.max()) + 0.5)
        y_lower = max(0.0, min(ys_arr.min(), cap_sec) - pad)
        y_upper = cap_sec + pad
        if y_upper <= y_lower:
            y_upper = y_lower + 10.0
        ax.set_ylim(y_lower, y_upper)

        ax.xaxis.set_major_locator(MultipleLocator(1))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: format_seconds(v)))

        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')
        ax.grid(color='gray', linestyle='dotted', linewidth=0.5)

        self.graafi_fig.tight_layout()

        self.graafi_canvas.draw()

    def nayta_juomat_pie(self, min_pct=3.0):
        """Piirakka kirjatuista juomista ({drink1}–{drink4}). Ohittaa
        NULL/tyhjät.
        Nippaa pienet 'Muut'."""
        self.graafi_fig.clear()
        ax = self.graafi_fig.add_subplot(111)
        self.graafi_fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')

        query = f"""
            WITH AllDrinks AS (
                SELECT LOWER(LTRIM(RTRIM({drink1}))) AS JuomaNorm FROM {table}
                 WHERE {drink1} IS NOT NULL
                   AND LTRIM(RTRIM({drink1})) <> ''
                   AND CAST({game_date} AS DATE) >= '2025-09-15'
                UNION ALL
                SELECT LOWER(LTRIM(RTRIM({drink2}))) FROM {table}
                 WHERE {drink2} IS NOT NULL
                   AND LTRIM(RTRIM({drink2})) <> ''
                   AND CAST({game_date} AS DATE) >= '2025-09-15'
                UNION ALL
                SELECT LOWER(LTRIM(RTRIM({drink3}))) FROM {table}
                 WHERE {drink3} IS NOT NULL
                   AND LTRIM(RTRIM({drink3})) <> ''
                   AND CAST({game_date} AS DATE) >= '2025-09-15'
                UNION ALL
                SELECT LOWER(LTRIM(RTRIM({drink4}))) FROM {table}
                 WHERE {drink4} IS NOT NULL
                   AND LTRIM(RTRIM({drink4})) <> ''
                   AND CAST({game_date} AS DATE) >= '2025-09-15'
            )
            SELECT JuomaNorm, COUNT(*) AS Cnt
            FROM AllDrinks
            GROUP BY JuomaNorm
            ORDER BY COUNT(*) DESC;
        """
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
        except Exception as e:
            QMessageBox.critical(self, "Tietokantavirhe",
                                 f"Virhe haettaessa juomia:\n{e}")
            return

        if not rows:
            QMessageBox.information(self, "Ei tietoja",
                                    "Ei kirjattuja juomia.")
            return

        labels = [(r.JuomaNorm or "").capitalize() for r in rows]
        values = [int(r.Cnt or 0) for r in rows]
        total = sum(values)
        if total == 0:
            QMessageBox.information(self, "Ei tietoja",
                                    "Ei kirjattuja juomia.")
            return

        # Nippaa pienet osuudet "Muut"
        big_labels, big_values, small_sum = [], [], 0
        for lab, val in zip(labels, values):
            if 100.0 * val / total >= min_pct:
                big_labels.append(lab)
                big_values.append(val)
            else:
                small_sum += val
        if small_sum > 0:
            big_labels.append("Muut")
            big_values.append(small_sum)

        wedges, texts, autotexts = ax.pie(
            big_values,
            labels=big_labels,
            autopct=lambda
                p: f"{p:.1f}%\n({int(round(p * total / 100))})" if p > 0 else "",
            startangle=90,
            textprops={'color': 'white'},
            wedgeprops={'edgecolor': 'white', 'linewidth': 1.0}
        )
        ax.axis('equal')
        ax.set_title("Kirjatut juomat (15.9.2025 →)", color='white')

        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')

        self.graafi_fig.tight_layout()
        self.graafi_canvas.draw()


class ProfiiliIkkuna(QDialog):
    """Profiilien haku luokka

    """
    def __init__(self):
        """Luodaan ikkuna

        """
        super().__init__()
        self.setWindowTitle("Pelaajaprofiilit")

        # Ikkunan koko
        self.resize(880, 600)

        self.profiilit = []
        self.sort_column = 0
        self.sort_descending = True

        # Vähimmäispelimäärä
        self.min_games_spinbox = QSpinBox()
        self.min_games_spinbox.setMinimum(0)
        self.min_games_spinbox.setMaximum(10000)
        self.min_games_spinbox.setValue(0)
        self.min_games_spinbox.valueChanged.connect(self.paivita_taulukko)


        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate())
        self.start_date_edit.dateChanged.connect(self.lataa_data)

        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate().addDays(1))
        self.end_date_edit.dateChanged.connect(self.lataa_data)

        # Taulukko
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Nimi", "Pelien määrä", "Voitot", "Voittoprosentti",
            "Keskiaika", "Minuuttipelit", "Pöydän alla", "Felo"])
        self.table.horizontalHeader().sectionClicked.connect(self.jarjesta_sarakkeen_mukaan)

        # Layout
        # Pienet layoutit päivämääräpareille
        alkaen_layout = QHBoxLayout()
        alkaen_layout.addStretch()
        alkaen_layout.addSpacing(20)
        self.date_filter_checkbox = QCheckBox("Käytä aikaväliä")
        alkaen_layout.addWidget(self.date_filter_checkbox)
        self.date_filter_checkbox.stateChanged.connect(self.lataa_data)
        alkaen_layout.addWidget(QLabel("Alkaen:"))
        alkaen_layout.addWidget(self.start_date_edit)


        alkaen_layout.addWidget(QLabel("Päättyen:"))
        alkaen_layout.addWidget(self.end_date_edit)

        # Päälayout
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Vähimmäispelimäärä:"))
        settings_layout.addWidget(self.min_games_spinbox)
        settings_layout.addSpacing(10)

        # Lisää päivämääräparit yhtenä "blokkeina"
        settings_layout.addLayout(alkaen_layout)
        settings_layout.addSpacing(10)

        layout = QVBoxLayout()
        layout.addLayout(settings_layout)
        layout.addWidget(QLabel("Klikkaa sarakeotsikkoa järjestääksesi:"))
        layout.addWidget(self.table)


        self.setLayout(layout)

        self.lataa_data()

    def lataa_data(self):
        """Datan haku serveriltä:
        - ilman aikaväliä -> uudet profiilit dbo.profile_table_name
        - aikavälillä     -> vanha Games-union-laskenta
        """
        try:
            if not self.date_filter_checkbox.isChecked():
                # --- UUSI NOPEA REITTI: suoraan profiilinäkymästä ---
                # dbo.v_PlayerProfiles kentät:
                # Nimi (lower), Pelit, Voitot, Voittoprosentti (DECIMAL), AverageSeconds (INT), Minuuttipelit, PoydanAlla
                query = f"""
                    SELECT Nimi, Pelit, Voitot, AverageSeconds, Minuuttipelit, PoydanAlla, Felo
                    FROM {profile_table}
                """
                with conn.cursor() as cur:
                    cur.execute(query)
                    rows = cur.fetchall()

                self.profiilit = []
                for r in rows:
                    nimi = (r[0] or "").lower()
                    pelit = int(r[1] or 0)
                    voitot = int(r[2] or 0)
                    average_seconds = int(r[3] or 0)
                    minuuttipelit = int(r[4] or 0)
                    poydan_alla = int(r[5] or 0)
                    felo = float(r[6] or 1500)

                    prosentti = (voitot / pelit) * 100 if pelit else 0.0

                    keskiaika_str = format_seconds(average_seconds)

                    self.profiilit.append([
                        nimi, pelit, voitot, prosentti,
                        keskiaika_str, minuuttipelit, poydan_alla, felo
                    ])



            else:

                # --- VANHA REITTI AIKAVÄLILLÄ: lasketaan Games-taulusta ---

                params = []

                aikavali = f"WHERE {game_date} BETWEEN ? AND ?"

                alku = self.start_date_edit.date().toPython()

                loppu = self.end_date_edit.date().toPython()

                params.extend([alku, loppu])

                # Koska aikaväli tulee joka UNION-haaraan, kerrotaan parametrit 4 kertaa

                final_params = params * 4

                query = f"""

                    WITH Base AS (

                        SELECT ID AS PeliID, LOWER(LTRIM(RTRIM({winner1}))) AS 
                Pelaaja,

                               1 AS Voitto, 0 AS PoydanAllaHavio,

                               DATEDIFF(SECOND, CAST('00:00:00' AS TIME), {game_time}) AS {
                game_time}Sek

                        FROM {table} {aikavali}

                        UNION ALL

                        SELECT ID, LOWER(LTRIM(RTRIM({winner2}))),

                               1, 0,

                               DATEDIFF(SECOND, CAST('00:00:00' AS TIME), {game_time})

                        FROM {table} {aikavali}

                        UNION ALL

                        SELECT ID, LOWER(LTRIM(RTRIM({loser1}))),

                               0, CASE WHEN {under_table} = 1 THEN 1 ELSE 0 
                               END,

                               DATEDIFF(SECOND, CAST('00:00:00' AS TIME), {game_time})

                        FROM {table} {aikavali}

                        UNION ALL

                        SELECT ID, LOWER(LTRIM(RTRIM({loser2}))),

                               0, CASE WHEN {under_table} = 1 THEN 1 ELSE 0 
                               END,

                               DATEDIFF(SECOND, CAST('00:00:00' AS TIME), {game_time})

                        FROM {table} {aikavali}

                    ),

                    -- Deduplikoidaan per (PeliID, Pelaaja), mutta sallitaan sekä Voitto=1 että PoydanAllaHavio=1

                    PerGamePlayer AS (

                        SELECT

                            PeliID,

                            Pelaaja,

                            MAX(Voitto)          AS Voitto,

                            MAX(PoydanAllaHavio) AS PoydanAllaHavio,

                            MAX({game_time}Sek)        AS {game_time}Sek

                        FROM Base

                        WHERE Pelaaja IS NOT NULL AND Pelaaja <> ''

                        GROUP BY PeliID, Pelaaja

                    )

                    SELECT

                        Pelaaja,

                        COUNT(*) AS Pelit,                                -- 1/peli/pelaaja

                        SUM(Voitto) AS Voitot,                            -- voi olla 1 vaikka olisi myös pöydän alla

                        SUM(PoydanAllaHavio) AS PoydanAllaHaviot,         -- voi olla 1 samaan aikaan kuin Voitto

                        AVG(CAST({game_time}Sek AS FLOAT)) AS KeskiaikaSek,

                        SUM(CASE WHEN {game_time}Sek < 60 THEN 1 ELSE 0 END) AS 
                        Minuuttipelit

                    FROM PerGamePlayer

                    GROUP BY Pelaaja

                """

                with conn.cursor() as cur:
                    cur.execute(query, final_params)
                    rows = cur.fetchall()

                # --- HAE FELO-ARVOT NYKYTILASTA (ei aikasuodatusta) ---

                names = [(r[0] or "").strip().lower() for r in rows]

                names = sorted(
                    set([n for n in names if n]))  # dedup & poista tyhjät

                # --- HAE KAIKKI FELO-ARVOT SANAKIRJAAN ---
                felo_map = {}
                try:
                    with conn.cursor() as cur:
                        # Haetaan kaikki profiilit kerralla, jotta vältetään IN-lauseen parametriraja
                        cur.execute(
                            f"SELECT LOWER(LTRIM(RTRIM(Nimi))), Felo FROM {profile_table}")
                        felo_map = {str(n).strip(): float(f or 1500.0) for n, f
                                    in cur.fetchall()}
                except Exception as e:
                    print(f"Felo-haku epäonnistui: {e}")

                # --- RAKENNA PROFIILIT, LISÄÄ FELO LOPPUUN ---

                self.profiilit = []

                for rivi in rows:
                    nimi = (rivi[0] or "").lower()

                    pelit = int(rivi[1] or 0)

                    voitot = int(rivi[2] or 0)

                    poydan_alla = int(rivi[3] or 0)

                    keskiaika_sek = int(rivi[4] or 0)

                    minuuttipelit = int(rivi[5] or 0)

                    prosentti = (voitot / pelit) * 100 if pelit else 0.0

                    keskiaika_str = format_seconds(keskiaika_sek)

                    felo = felo_map.get(nimi, 1500.0)

                    self.profiilit.append([

                        nimi, pelit, voitot, prosentti,

                        keskiaika_str, minuuttipelit, poydan_alla, felo

                    ])

            # Päivitä taulukko näkymään
            self.paivita_taulukko()

        except Exception as e:
            QMessageBox.critical(self, "Virhe",
                                 f"Virhe haettaessa profiilitietoja:\n{e}")
            return

    def paivita_taulukko(self):
        """Taulukon päivitys

        :return:
        """
        min_pelit = self.min_games_spinbox.value()

        # Suodatus vähimmäispelimäärän perusteella
        suodatetut = [r for r in self.profiilit if r[1] >= min_pelit]

        # Järjestä nykyisen sarakkeen ja suunnan mukaan
        suodatetut.sort(key=lambda x: x[self.sort_column], reverse=self.sort_descending)

        self.table.setRowCount(len(suodatetut))
        for i, (nimi, pelit, voitot, prosentti, keskiaika_str, minuuttipelit,
                poydan_alla, felo) in enumerate(suodatetut):
            solut = [
                QTableWidgetItem(nimi),
                QTableWidgetItem(str(pelit)),
                QTableWidgetItem(str(voitot)),
                QTableWidgetItem(f"{prosentti:.1f} %"),
                QTableWidgetItem(keskiaika_str),
                QTableWidgetItem(str(minuuttipelit)),
                QTableWidgetItem(str(poydan_alla)),
                QTableWidgetItem(str(int(felo))),
            ]

            for j, item in enumerate(solut):
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(i, j, item)

    def jarjesta_sarakkeen_mukaan(self, index):
        """Sarakkeen mukaan järjestely

        :param index:
        :return:
        """
        # Jos sama sarake klikataan uudestaan, vaihda järjestyssuuntaa
        if self.sort_column == index:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_column = index
            self.sort_descending = True

        self.paivita_taulukko()


def main():
    app = QApplication([])

    if not on_windows11():
        aseta_dark_theme(app)

    app.setWindowIcon(QIcon(config["icon_path"]))

    # Asetetaan latausosoitin (tiimalasi/pyörivä rengas) koko sovellukselle
    app.setOverrideCursor(Qt.WaitCursor)

    # 1. Luodaan ja näytetään latausikkuna
    # Käytetään configin ikonia kuvana. Voit halutessasi vaihtaa polun muuhun kuvaan.
    splash = Latausikkuna(config["icon_path"]) 
    splash.show()
    app.processEvents() # Piirtää ikkunan ruudulle

    # 2. Yhdistetään tietokantaan nyt, kun latausikkuna on näkyvissä
    global conn
    try:
        conn = muodosta_yhteys(connection_string, splash=splash, max_yritykset=8, viive=5)
    except Exception as e:
        app.restoreOverrideCursor() # Palautetaan hiiri
        QMessageBox.critical(None, "Kriittinen virhe", f"Tietokantayhteys epäonnistui lopullisesti:\n{e}")
        sys.exit(1)

    splash.paivita_tila("Käynnistetään käyttöliittymää...", 100)
    time.sleep(0.5) # Pieni viive, jotta käyttäjä ehtii nähdä 100%
    app.processEvents()

    # 3. Ladataan varsinainen pääikkuna
    window = AjanottoGUI()
    window.show()

    # 4. Suljetaan latausikkuna ja palautetaan normaali hiiri
    splash.close()
    app.restoreOverrideCursor()

    def sulje_tietokanta():
        if conn:
            conn.close()

    app.aboutToQuit.connect(sulje_tietokanta)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()


