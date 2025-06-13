import threading
from datetime import datetime
import os
import csv
from ServerConnection import UploadFiles
import shutil
from PyQt6.QtWidgets import QApplication, QMessageBox
import sys
from PyQt6.QtCore import QThread, QTimer

from ProcessingThread import ProcessingWorker

class Processing:
    def __init__(self, wavelengths, data, output_folder_path, ui):
        # Initialise variables for processing thread and thread events
        self.start_process_data_event = threading.Event()
        self.stop_process_data_event = threading.Event()
        self.processing_thread = None
        self.processing_worker = None

        # Initialise dictionaries of queues for holding the spectra obtained form each spectrometers as well as the acquisition times and measurement wavelengths
        self.wavelengths = wavelengths
        self.data = data
        self.output_folder_base = output_folder_path
        self.current_output_folder = None
        self.file_path = None

        self.processing_timer = QTimer(ui)
        self.processing_timer.timeout.connect(self.start_process_data_event.set)

    def start_acquisition(self, finished_function, settings, patient_name, study_name):
        self.create_output_path(patient_name, study_name)
        self.save_settings(settings, patient_name, study_name)
        self.start_process_data_event.clear()
        self.stop_process_data_event.clear()
        self.processing_worker = ProcessingWorker(self.start_process_data_event, self.stop_process_data_event, self.data, self.wavelengths, settings)
        self.processing_thread = QThread()
        self.processing_worker.moveToThread(self.processing_thread)
        self.processing_worker.signal_processed.connect(finished_function)
        self.processing_thread.started.connect(self.processing_worker.run)
        self.processing_thread.start()
        self.processing_timer.start(settings.processing_interval)

    def stop_acquisition(self):
        self.processing_timer.stop()
        self.stop_process_data_event.set()
        self.start_process_data_event.set()
        if self.processing_thread:
            self.processing_thread.quit()
            self.processing_thread.wait()
        
    def create_output_path(self, patient_name, study_name):
        if not patient_name:
            self.file_path = None
            return
            # Store patient and study name in class attributes
        self.patient_name = patient_name
        self.study_name = study_name
        if not self.current_output_folder or not f"\\{patient_name}\\" in self.current_output_folder:
            patient_folder_path = f"{self.output_folder_base}\\{study_name}\\{patient_name}"
            if not os.path.exists(patient_folder_path):
                os.makedirs(patient_folder_path)
            session_number = len(next(os.walk(patient_folder_path))[1]) + 1
            self.current_output_folder = f"{patient_folder_path}\\Session {session_number}"
            os.makedirs(self.current_output_folder)
        start_time = datetime.now()
        formatted_time = start_time.strftime("%Y-%m-%d %H-%M-%S")
        self.file_path = f"{self.current_output_folder}\\{formatted_time} Spectrometer SPEC_NUM Raw bNIRS.csv"

    def save_settings(self, settings, patient_name, study_name):
        if not self.file_path:
            return
        settings_file_path = self.file_path.replace("Spectrometer SPEC_NUM Raw bNIRS.csv", "Settings.txt")
        with open(settings_file_path, 'w') as f:
            f.write(f"Subject Number: {patient_name}\n")
            f.write(f"Study Code: {study_name}\n\n")
            for key, value in settings._get_current_settings().items():  
                f.write(f"{key}: {value}\n")

    def save_results(self, results):

        def upload_success_popup():
            # Check if a QApplication already exists
            app = QApplication.instance()
            if app is None:  # If no instance exists, create one
                app = QApplication(sys.argv)

            msg = QMessageBox()
            msg.setWindowTitle("Upload Status")
            msg.setText("File Upload Successfully!")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)

            msg.exec()  # Show the popup window without closing the main app

        if not self.file_path:
            return
        for spec_num in results["ucln"]:
            processed_file_path = self.file_path.replace("SPEC_NUM Raw", str(spec_num+1) + " Processed")
            with open(processed_file_path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows([["Date and Time", "Elapsed Time", "Temperature", "HbO2", "HHb", "CCO"]] + results["ucln"][spec_num]["conc_changes"])

        zip_file = self.current_output_folder  
        session_folder = os.path.dirname(zip_file) 
        last_folder_name = os.path.basename(session_folder)
        folder = os.path.dirname(session_folder)
        last_folder = os.path.basename(folder)

        #Compress the folder into a ZIP file
        shutil.make_archive(zip_file, 'zip', zip_file)
        print(f"Folder compressed: {zip_file}.zip")

        # Upload the ZIP file
        print("Starting folder upload...")
        SaveFolder2 = f"Patient {last_folder_name}"
        Savefolder = f"Test {last_folder}"

        UploadFiles(session_folder, "nikoleta.medphys.ucl.ac.uk", "uclh", "\"Hh2jaKe29", SaveFolder2, Savefolder)
        print("Folder upload completed successfully!")
        upload_success_popup()