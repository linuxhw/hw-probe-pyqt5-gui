#!/usr/bin/env python3

# Hardware Probe
# Copyright (c) 2020-21, Simon Peter <probono@puredarwin.org>
# Copyright (c) 2021 Linux Hardware Project
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Stethoscope Icon
# https://iconarchive.com/show/pry-system-icons-by-jonas-rask/Stethoscope-icon.html
# Artist: Jonas Rask Design
# Iconset: Pry System Icons (64 icons)
# License: Free for non-commercial use.
# Commercial usage: Not allowed

import sys, os, socket
import tempfile
import shutil

from PyQt5 import QtWidgets, QtGui, QtCore # pkg install py37-qt5-widgets
from PyQt5.QtWidgets import QTreeView, QFileSystemModel, QVBoxLayout, QPlainTextEdit, QMainWindow

# Plenty of TODOs and FIXMEs are sprinkled across this code.
# These are invitations for new contributors to implement or comment on how to best implement.
# These things are not necessarily hard, just no one had the time to do them so far.


# Translate this application using Qt .ts files without the need for compilation
import tstranslator
# FIXME: Do not import translations from outside of the appliction bundle
# which currently is difficult because we have all translations for all applications
# in the whole repository in the same .ts files
tstr = None
def tr(input):
    global tstr
    try:
        if not tstr:
            tstr = tstranslator.TsTranslator(os.path.dirname(__file__) + "/i18n", "")
        return tstr.tr(input)
    except:
        return input

#############################################################################
# Helper functions
#############################################################################

def internetCheckConnected(host="8.8.8.8", port=53, timeout=3):
    """
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        print(ex)
        print("Trying ping")
        for host in ['ya.ru', 'google.com', 'linux-hardware.org']:
            if os.system("ping -c 1 %s >/dev/null" % host) == 0:
                return True
        return False


#############################################################################
# Initialization
# https://doc.qt.io/qt-5/qwizard.html
#############################################################################
app = QtWidgets.QApplication(sys.argv)

class Wizard(QtWidgets.QWizard, object):
    Page_Intro   = 1
    Page_Filer   = 2
    Page_Privacy = 3
    Page_Upload  = 4
    Page_Success = 5

    def __init__(self):
        app.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor)) # It can take some time before we show the initial page, because hw-probe runs there

        print("Preparing wizard")
        super().__init__()

        self.should_show_last_page = False
        self.skip_raw_view = True
        self.error_message_nice = tr("An unknown error occured.")

        self.setWizardStyle(QtWidgets.QWizard.MacStyle)
        self.setPixmap(QtWidgets.QWizard.BackgroundPixmap, QtGui.QPixmap(os.path.dirname(__file__) + '/Stethoscope-icon.png'))
        self.setOption(QtWidgets.QWizard.ExtendedWatermarkPixmap, True) # Extend WatermarkPixmap all the way down to the window's edge; https://doc.qt.io/qt-5/qwizard.html#wizard-look-and-feel

        self.hw_probe_tool = 'hw-probe'
        if os.environ.get('HW_PROBE_FLATPAK'):
            self.hw_probe_output = tempfile.mkdtemp(dir = os.environ.get('XDG_DATA_HOME'))
        elif os.environ.get('HW_PROBE_SNAP'):
            self.hw_probe_output = tempfile.mkdtemp(dir = os.environ.get('SNAP_USER_COMMON'))
        else:
            self.hw_probe_output = tempfile.mkdtemp()

        self.hw_probe_done = False
        self.server_probe_url = None

        self.setWindowTitle(tr("Hardware Probe"))
        self.setFixedSize(600, 400)

        self.setSubTitleFormat(QtCore.Qt.RichText) # Allow HTML; Qt 5.14+ also have an option for Markdown

        # Translate the widgets in the UI objects in the Wizard
        self.setWindowTitle(tr(self.windowTitle()))
        for e in self.findChildren(QtCore.QObject, None, QtCore.Qt.FindChildrenRecursively):
            if hasattr(e, 'text') and hasattr(e, 'setText'):
                e.setText(tr(e.text()))

    def showErrorPage(self, message):
        print("Show error page")
        self.addPage(ErrorPage())
        # It is not possible jo directly jump to the last page from here, so we need to take a workaround
        self.should_show_last_page = True
        self.error_message_nice = message
        self.next()

    # When we are about to go to the next page, we need to check whether we have to show the error page instead
    def nextId(self):
        if self.should_show_last_page == True:
            return max(wizard.pageIds())
        elif self.skip_raw_view and self.currentId() == self.Page_Intro:
            return self.Page_Privacy
        else:
            return self.currentId() + 1

wizard = Wizard()

#############################################################################
# Privacy Information
#############################################################################

class PrivacyPage(QtWidgets.QWizardPage, object):
    def __init__(self):

        print("Privacy Information")
        super().__init__()

        self.setTitle(tr('Privacy Information'))
        self.setSubTitle(tr('Uploading a Hardware Probe is subject to the following Privacy Terms.'))
        privacy_label = QtWidgets.QTextBrowser()
        privacy_layout = QtWidgets.QVBoxLayout(self)
        
        text = ""
        text += tr("This will upload the anonymized hardware probe to the Linux hardware database. The probe will be published publicly under a permanent URL to view the probe.") + "\n\n"
        text += tr("Private information (including the username, hostname, IP addresses, MAC addresses, UUIDs and serial numbers) is not uploaded to the database.") + "\n\n"
        text += tr("The tool uploads 32-byte prefix of salted SHA512 hash of MAC addresses/UUIDs and serial numbers to properly distinguish between different computers and hard drives. All the data is uploaded securely via HTTPS.") + "\n\n"
        text += tr("DISCLAIMER: BY USING THIS UTILITY, YOU AGREE THAT INFORMATION ABOUT YOUR HARDWARE WILL BE UPLOADED TO A PUBLICLY VISIBLE DATABASE. DO NOT USE THIS UTILITY IF YOU DO NOT AGREE WITH THIS.") + "\n\n"
        text += tr("Please contact https://linux-hardware.org/?view=contacts in case of questions and in case you wish accidentally submitted probes to be removed from the database.")
        
        privacy_label.setText(text)
        font = wizard.font()
        font.setPointSize(9)
        privacy_label.setFont(font)

        privacy_layout.addWidget(privacy_label)

        additional_privacy_label = QtWidgets.QLabel()
        additional_privacy_label.setWordWrap(True)
        additional_privacy_label.setText(tr('Please see %s for more information.') % '<a href="https://linux-hardware.org">https://Linux-Hardware.org</a>')
        privacy_layout.addWidget(additional_privacy_label)

#############################################################################
# Filer page
#############################################################################
class Filer(QtWidgets.QWizardPage, object):
    def __init__(self):

        print("Preparing probe raw viewer")
        super().__init__()

        self.setTitle(tr("Raw Collected Info"))

        self.model = QFileSystemModel()
        self.model.setRootPath(wizard.hw_probe_output)
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(wizard.hw_probe_output))
        self.tree.setColumnWidth(0, 250)
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.contextMenu)

        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        self.setLayout(layout)

    def contextMenu(self):
        menu = QtWidgets.QMenu()
        open = menu.addAction(tr("Open file"))
        open.triggered.connect(self.openFile)
        cursor = QtGui.QCursor()
        menu.exec_(cursor.pos())

    def openFile(self):
        index = self.tree.currentIndex()
        filePath = self.model.filePath(index)

        if not os.path.isfile(filePath):
            return

        text = open(filePath).read()

        viewer = Viewer(wizard)
        viewer.setup(os.path.basename(filePath), text)
        viewer.show()

class Viewer(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(Viewer, self).__init__(*args, **kwargs)
        self.editor = QPlainTextEdit()
        self.setCentralWidget(self.editor)
        self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.resize(640, 480)

    def setup(self, title, text):
        self.setWindowTitle(title)
        self.editor.setPlainText(text)

#############################################################################
# Intro page
#############################################################################

class IntroPage(QtWidgets.QWizardPage, object):
    def __init__(self):

        print("Preparing IntroPage")
        super().__init__()

        self.setTitle(tr('Hardware Probe'))
        self.setSubTitle(tr("""<p>This utility collects anonymized hardware details of your computer and can upload them to a public database.</p>
        <p>This can help users and developers to collaboratively debug hardware related issues, check for hardware compatibility and find drivers.</p>
        <p>You will get a permanent probe URL to view and share collected information.</p><br><br><br>"""))

        layout = QtWidgets.QVBoxLayout(self)
        # layout.addWidget(center_widget, True) # True = add stretch vertically

        wizard.showHardwareProbeButton = QtWidgets.QPushButton(tr('Collecting hardware info ...'), self)
        wizard.showHardwareProbeButton.clicked.connect(self.showHardwareProbeButtonClicked)
        wizard.showHardwareProbeButton.setDisabled(True)
        self.hw_probe_done = False
        layout.addWidget(wizard.showHardwareProbeButton)

    def showHardwareProbeButtonClicked(self):
        print("showHardwareProbeButtonClicked")
        print("hw_probe_output: %s" % wizard.hw_probe_output)
        wizard.skip_raw_view = False
        wizard.next()

    def initializePage(self):
        print("Displaying IntroPage")

        # Without this, the window does not get shown before run_probe_locally is done; why?
        workaroundtimer = QtCore.QTimer()
        workaroundtimer.singleShot(200, self.run_probe_locally)

    def run_probe_locally(self):
        proc = QtCore.QProcess()

        if os.environ.get('HW_PROBE_FLATPAK') or os.environ.get('HW_PROBE_SNAP'):
            command = self.wizard().hw_probe_tool
            args = ["-all", "-output", self.wizard().hw_probe_output]
        else:
            command = 'sudo'
            args = ["-A", "-E", self.wizard().hw_probe_tool, "-all", "-output", self.wizard().hw_probe_output]

        try:
            print("Starting %s %s" % (command, args))
            proc.start(command, args)
        except:
            wizard.showErrorPage(tr("Failed to collect info.")) # This does not catch most cases of errors; hence see below
            return

        proc.waitForFinished()

        output_lines = proc.readAllStandardOutput().split("\n")

        done_properly = None
        for line in output_lines:
            line = str(line, encoding='utf-8')
            print(line)
            if "Local probe path:" in line:
                done_properly = True

        if not done_properly:
            wizard.showErrorPage(tr("Failed to collect info.")) # This catches most cases if something goes wrong
            return

        wizard.showHardwareProbeButton.setText(tr('Show raw collected info'))
        wizard.showHardwareProbeButton.setDisabled(False)
        app.setOverrideCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

        wizard.hw_probe_done = True
        wizard.currentPage().completeChanged.emit()

    def isComplete(self):
        return wizard.hw_probe_done

#############################################################################
# Installation page
#############################################################################

class UploadPage(QtWidgets.QWizardPage, object):
    def __init__(self):

        print("Preparing InstallationPage")
        super().__init__()

        self.setTitle(tr('Uploading Hardware Probe'))
        self.setSubTitle(tr('The Hardware Probe is being uploaded to the public database'))

        self.layout = QtWidgets.QVBoxLayout(self)
        wizard.progress = QtWidgets.QProgressBar(self)
        # Set the minimum, maximum and current values to get an indeterminate progress bar
        wizard.progress.setMaximum(0)
        wizard.progress.setMinimum(0)
        wizard.progress.setValue(0)
        self.layout.addWidget(wizard.progress, True)

    def initializePage(self):
        print("Displaying InstallationPage")
        wizard.setButtonLayout(
            [QtWidgets.QWizard.Stretch])

        if internetCheckConnected() == False:
            print("Offline?")
            wizard.showErrorPage(tr("You need an active internet connection in order to upload."))
            return

        # Without this, the progress bar does not get shown at all; why?
        workaroundtimer = QtCore.QTimer()
        workaroundtimer.singleShot(200, self.upload)

    def upload(self):
        print("Starting Upload")

        proc = QtCore.QProcess()

        command = wizard.hw_probe_tool

        args = ["-from-gui", "-upload", "-output", self.wizard().hw_probe_output]

        try:
            print("Starting %s %s" % (command, args))
            proc.start(command, args)
        except:
            wizard.showErrorPage(tr("Failed to upload data.")) # This does not catch most cases of errors; hence see below
            return

        proc.waitForFinished()
        # FIXME: What can we do so that the progress bar stays animated without the need for threading?
        output_lines = proc.readAllStandardOutput().split("\n")
        err_lines = proc.readAllStandardError().split("\n")
        if err_lines[0] != "":
            wizard.showErrorPage(str(err_lines[0], encoding='utf-8'))
            return
        else:
            for line in output_lines:
                line = str(line, encoding='utf-8')
                print(line)
                if "Probe URL:" in line:
                    wizard.server_probe_url = line.replace("Probe URL:","").strip()  # Probe URL: https://linux-hardware.org/?probe=...
                    print("wizard.server_probe_url: %s" % wizard.server_probe_url)

        if not wizard.server_probe_url:
            wizard.showErrorPage(tr("Failed to upload the probe."))
            return

        wizard.next()

#############################################################################
# Success page
#############################################################################

class SuccessPage(QtWidgets.QWizardPage, object):
    def __init__(self):

        print("Preparing SuccessPage")
        super().__init__()
        self.timer = QtCore.QTimer()  # Used to periodically check the available disks

    def initializePage(self):
        print("Displaying SuccessPage")
        wizard.setButtonLayout(
            [QtWidgets.QWizard.Stretch, QtWidgets.QWizard.CancelButton])

        self.setTitle(tr('Hardware Probe Uploaded'))
        # self.setSubTitle(tr('Thank you for uploading your Hardware Probe.'))

        logo_pixmap = QtGui.QPixmap(os.path.dirname(__file__) + '/check.png').scaledToHeight(160, QtCore.Qt.SmoothTransformation)
        logo_label = QtWidgets.QLabel()
        logo_label.setPixmap(logo_pixmap)

        center_layout = QtWidgets.QHBoxLayout(self)
        center_layout.addStretch()
        center_layout.addWidget(logo_label)
        center_layout.addStretch()

        center_widget =  QtWidgets.QWidget()
        center_widget.setLayout(center_layout)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(center_widget, True) # True = add stretch vertically

        label = QtWidgets.QLabel()
        label.setText(tr("Your probe URL is") + "<a href='%s'>%s</a>" % (wizard.server_probe_url, wizard.server_probe_url))
        label.setWordWrap(True)
        layout.addWidget(label)

        wizard.showUploadedProbeButton = QtWidgets.QPushButton(tr("Open probe URL in your browser"), self)
        wizard.showUploadedProbeButton.clicked.connect(self.showUploadedProbeButtonClicked)
        layout.addWidget(wizard.showUploadedProbeButton)

        self.setButtonText(wizard.CancelButton, tr("Quit"))
        wizard.setButtonLayout([QtWidgets.QWizard.Stretch, QtWidgets.QWizard.CancelButton])

    def showUploadedProbeButtonClicked(self):
        print("showHardwareProbeButtonClicked")
        print("wizard.server_probe_url: %s" % wizard.server_probe_url)
        proc = QtCore.QProcess()
        command = 'xdg-open'
        args = [wizard.server_probe_url]
        try:
            print("Starting %s %s" % (command, args))
            proc.startDetached(command, args)
        except:
            wizard.showErrorPage(tr("Failed to open the uploaded hardware probe."))
            return

#############################################################################
# Error page
#############################################################################

class ErrorPage(QtWidgets.QWizardPage, object):
    def __init__(self):

        print("Preparing ErrorPage")
        super().__init__()

        self.setTitle(tr('Error'))
        self.setSubTitle(tr('Hardware Probe was not successful.'))

        logo_pixmap = QtGui.QPixmap(os.path.dirname(__file__) + '/cross.png').scaledToHeight(160, QtCore.Qt.SmoothTransformation)
        logo_label = QtWidgets.QLabel()
        logo_label.setPixmap(logo_pixmap)

        center_layout = QtWidgets.QHBoxLayout(self)
        center_layout.addStretch()
        center_layout.addWidget(logo_label)
        center_layout.addStretch()

        center_widget =  QtWidgets.QWidget()
        center_widget.setLayout(center_layout)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(center_widget, True) # True = add stretch vertically

        self.label = QtWidgets.QLabel()  # Putting it in initializePage would add another one each time the page is displayed when going back and forth
        self.layout.addWidget(self.label)

    def initializePage(self):
        print("Displaying ErrorPage")
        app.setOverrideCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        wizard.showHardwareProbeButton.hide() # FIXME: Why is this needed?
        wizard.progress.hide()  # FIXME: Why is this needed?3
        self.label.setWordWrap(True)
        self.label.clear()
        self.label.setText(wizard.error_message_nice)
        self.setButtonText(wizard.CancelButton, tr("Quit"))
        wizard.setButtonLayout([QtWidgets.QWizard.Stretch, QtWidgets.QWizard.CancelButton])

#############################################################################
# Pages flow in the wizard
#############################################################################

wizard.setPage(wizard.Page_Intro, IntroPage())
wizard.setPage(wizard.Page_Filer, Filer())
wizard.setPage(wizard.Page_Privacy, PrivacyPage())
wizard.setPage(wizard.Page_Upload, UploadPage())
wizard.setPage(wizard.Page_Success, SuccessPage())

wizard.show()

retcode = app.exec_()
if os.path.exists(wizard.hw_probe_output):
    print("Cleanup")
    shutil.rmtree(wizard.hw_probe_output)
sys.exit(retcode)
