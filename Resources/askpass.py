#!/usr/bin/env python3


# man sudo(8)
#      -A, --askpass
#                  Normally, if sudo requires a password, it will read it from
#                  the user's terminal.  If the -A (askpass) option is
#                  specified, a (possibly graphical) helper program is executed
#                  to read the user's password and output the password to the
#                  standard output.  If the SUDO_ASKPASS environment variable is
#                  set, it specifies the path to the helper program.  Otherwise,
#                  if sudo.conf(5) contains a line specifying the askpass
#                  program, that value will be used.  For example:
#
#                      # Path to askpass helper program
#                      Path askpass /usr/X11R6/bin/ssh-askpass
#
#                  If no askpass program is available, sudo will exit with an
#                  error.


from PyQt5 import QtWidgets
import tstranslator

tstr = None
def tr(input):
    global tstr
    try:
        if not tstr:
            tstr = tstranslator.TsTranslator(os.path.dirname(__file__) + "/i18n", "")
        return tstr.tr(input)
    except:
        return input

app = QtWidgets.QApplication([])
password, ok = QtWidgets.QInputDialog.getText(None, "sudo", tr("Password"), QtWidgets.QLineEdit.Password)
if ok:
    print(password)
app.exit(0)