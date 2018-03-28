import sys
from deriva.transfer import GenericUploader
from deriva.qt import DerivaUploadGUI


DESC = "Deriva Data Upload Utility"
INFO = "For more information see: https://github.com/informatics-isi-edu/deriva-qt"


def main():
    gui = DerivaUploadGUI(GenericUploader, DESC, INFO)
    return gui.main()


if __name__ == '__main__':
    sys.exit(main())
