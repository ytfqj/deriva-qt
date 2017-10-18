from PyQt5.QtWidgets import QTableWidget


class TableWidget(QTableWidget):

    def __init__(self, parent):
        super(QTableWidget, self).__init__(parent)

    def getCurrentTableRow(self):
        row = self.currentRow()
        if row == -1 and self.rowCount() > 0:
            row = 0

        return row

    def getCurrentTableItemTextByName(self, column_name):
        row = self.getCurrentTableRow()
        return self.getTableItemTextByName(row, column_name)

    def getTableItemTextByName(self, row, column_name):
        item = self.getTableItemByName(row, column_name)
        return item.text() if item else ""

    def getTableItemByName(self, row, column_name):
        column = None
        header_count = self.columnCount()
        # noinspection PyTypeChecker
        for column in range(header_count):
            header_text = self.horizontalHeaderItem(column).text()
            if column_name == header_text:
                break
        if row is None or column is None:
            return None

        return self.item(row, column)
