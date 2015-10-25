#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
ZetCode PyQt5 tutorial

This example shows a tooltip on
a window and a button.

author: Jan Bodnar
website: zetcode.com
last edited: January 2015
"""
import sys
import functools
import types
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from itertools import zip_longest, count
import re

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
from PyQt5.QtCore import Qt

def _el(name, text):
    el = ET.Element(name)
    el.text = text
    return el

## TODO: introduce a decent common interface for all four classes
## (kind of done)

class AutoProperty:
    "Intended to be subclasses by a class that has an `attrNames` property and deref() method."
    def getProperty(self, name):
        # print(self, name)
        if name in self.attrNames:
            return getattr(self, name)
        else:
            return getattr(self.deref(), name)
    def setProperty(self, name, value):
        if name in self.attrNames:
            setattr(self, name, value)
        else:
            setattr(self.deref(), name, value)

class NPCItem(QTreeWidgetItem, AutoProperty):
    "Corresponds a single <part>...</part> element, contains `AnswerItem` items as children."
    attrNames = set(['portrait', 'speakerName', 'text', 'script', 'UID'])
    def __init__(self, UID, text='', portrait='', speakerName='', script=''):
        super().__init__()
        self.UID = int(UID)
        self.portrait = portrait
        self.speakerName = speakerName
        self.text = text
        self.script = script
    def getAnswers(self):
        return self.answers
    def data(self, column, role):
        if role == Qt.ForegroundRole:
            return QBrush(QColor(0, 0, 255))
        elif role == Qt.DisplayRole and column == 0:
            return re.sub('\s+', ' ', self.text)
        elif role == Qt.ToolTipRole and column == 0:
            # visual = self.treeWidget().visualRect(self.treeWidget().currentIndex())
            # index = self.treeWidget().currentIndex()
            # sizeHint = self.treeWidget().itemDelegate(index).sizeHint(self.treeWidget().viewOptions(), index)
            # print('tooltip requested')
            return self.text
        else:
            return super().data(column, role)
    def dataModel(self):
        return self.attrNames
    def deref(self):
        return self
    def toXmlPart(self, children):
        dlgPart = ET.Element('dlgPart')
        def sub(name, eltName=None):
            tosave = getattr(self, name)
            if tosave is not None:
                tosave = str(tosave)
            ET.SubElement(dlgPart, eltName or name).text = tosave
        # immediate children
        sub('portrait')
        sub('speakerName', 'speaker_name')
        sub('text', 'npc_text')
        script = ET.SubElement(dlgPart, 'onLoadScripts')
        for line in filter(None, self.script.split('\n')):
            ET.SubElement(script, 'string').text = line
        # answers
        answers = ET.SubElement(dlgPart, 'answers')
        for answer in children:
            dlgAnsw = ET.SubElement(answers, 'dlgAnsw')
            ET.SubElement(dlgAnsw, 'text').text = answer.text
            # find the default link
            # FIXME: we're looking for the first link with no condition
            # FIXME: check to see that only one child is like that
            defaultLinkUID = None
            linkConditions = []
            linkUIDs = []
            for i in range(answer.childCount()):
                child = answer.child(i)
                if isinstance(child, ReferenceItem):
                    child = child.ref
                assert(isinstance(child, AnswerLink))
                # print('child.text:', child.link.text)
                # print('child:', child)
                # print('child.condition:', child.condition)
                # print('child.link.UID:', child.link.UID)
                if not child.getProperty('condition'):
                    if defaultLinkUID:
                        raise BaseException('More than one default link from answer "%s" (parent node: "%s")' %
                                            (answer.getProperty('text'), answer.parent().getProperty('text')))
                    defaultLinkUID = child.deref().UID
                    # print("default link for '%s': %s" % (answer.text, defaultLinkUID))
                else: # non-default
                    # print(child.deref().UID)
                    linkConditions.append(child.condition)
                    linkUIDs.append(str(child.deref().UID))
            if defaultLinkUID is None:
                raise BaseException("No default answer link from answer '%s' (its parent node is: '%s')" %
                                    (answer.text, answer.parent().getProperty('text')))
            ET.SubElement(dlgAnsw, 'def_link').text = str(defaultLinkUID)
            ET.SubElement(dlgAnsw, 'checkOnAppear').text = answer.condition

            checksOnClick = ET.SubElement(dlgAnsw, 'checksOnClick')
            # print('linkConditions:', linkConditions)
            for cond in filter(None, linkConditions):
                ET.SubElement(checksOnClick, 'string').text = cond

            linksOnClick = ET.SubElement(dlgAnsw, 'linksOnClick')
            for link in filter(None, linkUIDs):
                ET.SubElement(linksOnClick, 'int').text = link

            answerScripts = answer.script.split('\n')
            # answerScripts.append(child.script)
            scriptsOnClick = ET.SubElement(dlgAnsw, 'scriptsOnClick')
            for script in filter(None, answerScripts):
                ET.SubElement(scriptsOnClick, 'string').text = script

        sub('UID')

        return dlgPart

class AnswerItem(QTreeWidgetItem, AutoProperty):
    attrNames = set(['text', 'condition', 'script'])
    def __init__(self, text='', condition='', script='', links=None):
        super().__init__()
        self.text = text
        self.condition = condition
        self.links = links or []
        self.script = script
    def warning(self):
        if self.childCount() == 0:
            return 'Link this answer to at least one node.'
        return None
    def data(self, column, role):
        if role == Qt.ForegroundRole:
            return QBrush(QColor(255, 0, 0))
        elif role == Qt.DisplayRole and column == 0:
            return self.text
        elif role == Qt.ToolTipRole and column == 0:
            # visual = self.treeWidget().visualRect(self.treeWidget().currentIndex())
            # index = self.treeWidget().currentIndex()
            # sizeHint = self.treeWidget().itemDelegate(index).sizeHint(self.treeWidget().viewOptions(), index)
            # print('tooltip requested')
            if self.warning():
                return self.warning()
            else:
                return self.text
        elif role == Qt.DecorationRole and column == 0 and self.warning():
            return QIcon("icons/Warning.png")
        else:
            return super().data(column, role)
    def dataModel(self):
        return self.attrNames
    def deref(self):
        return self

class ReferenceItem(QTreeWidgetItem, AutoProperty):
    "A reference to some other item.  Delegates all relevant methods to that item."
    def __init__(self, ref):
        super().__init__()
        self.ref = ref
        self.attrNames = ref.attrNames
    def data(self, column, role):
        # if role == Qt.DisplayRole and column == 0:
        #     return '<ref> %s' % self.ref.data(column, role)
        # el
        if role == Qt.ForegroundRole:
            return QBrush(QColor(70, 70, 70))
        return self.ref.data(column, role)
    def dataModel(self):
        return self.ref.dataModel() - {'script', 'UID', 'speakerName', 'portrait', 'text'}
    def deref(self):
        return self.ref.deref()
    def setProperty(self, name, value):
        self.ref.setProperty(name, value)
    def getProperty(self, name):
        return self.ref.getProperty(name)

class AnswerLink(QTreeWidgetItem, AutoProperty):
    """A link from an `AnswerItem` object to a conditional NPCItem result.  Corresponds to conditionals like:

          <checksOnClick>
            <string>ownsSmallDagger() == true &amp;&amp; aod.critical_strike &gt;= 2</string>
          </checksOnClick>
          <linksOnClick>
            <int>5001</int>
          </linksOnClick>
"""
    attrNames = set(['condition'])
    def __init__(self, link, condition=''):
        super().__init__()
        self.link = link
        self.condition = condition
    def data(self, column, role):
        if role == Qt.ForegroundRole:
            return QBrush(QColor(0, 0, 255))
        elif role == Qt.DisplayRole and column == 0:
            if self.condition:
                return '<%s> %s' % (self.condition, self.link.data(column, role))
            else: # if self.parent().childCount() > 1
                return '<%s> %s' % ('default', self.link.data(column, role))
        return self.link.data(column, role)
    def getAnswers(self):
        return self.link.answers
    def dataModel(self):
        return self.attrNames | self.deref().dataModel()
    def deref(self):
        return self.link.deref()

class ConditionalLink(QTreeWidgetItem, AutoProperty):
    "Displayed in the links widget inside the header settings box."
    # TODO: make this an item for the roots of the main dialogue tree, used analogous to `AnswerLink`.
    attrNames = {'condition', 'link'}
    def __init__(self, condition=None, link=None):
        super().__init__()
        self.condition = condition
        self.link = link
        self.setFlags(self.flags() | Qt.ItemIsEditable)
    def data(self, column, role):
        assert(column <= 1)
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if column == 0:
                return self.condition
            elif column == 1:
                return self.link
        return super().data(column, role)
    def setData(self, column, role, value):
        # print('setData', column, role)
        if role == Qt.EditRole:
            assert(column <= 1)
            if column == 0:
                self.condition = value
            if column == 1:
                self.link = value
        super().setData(column, role, value)

class BadXmlException(BaseException):
    pass

# class MalformedDialogue(BaseException):
#     def __init__(self):
#         super().__init__()

def subtext(element, xpath):
    "`element.find(xpath).text`, or '' if no such xpath"
    subelement = element.find(xpath)
    if subelement is None:
        return ""
    else:
        return subelement.text

class NodeSelectDialog(QDialog):
    "Selects NPCItem nodes from the current tree."
    def __init__(self):
        super().__init__()
        uic.loadUi('select_node.ui', self)
    def exec(self):
        if super().exec():
            return self.nodes.currentItem().node
        else:
            return None
    @staticmethod
    def selectNode(editor, defaultNode=None):
        dialog = NodeSelectDialog()
        for node in editor.findAllNpcNodes():
            item = QListWidgetItem(dialog.nodes)
            item.setData(Qt.DisplayRole, node.data(0, Qt.DisplayRole))
            item.node = node
            if node == defaultNode:
                dialog.nodes.setCurrentItem(item)
        return dialog.exec()

class EditorMainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class Header(AutoProperty):
    attrNames = ['defaultLink', 'dialogueName', 'defaultSpeakerName', 'defaultPortrait']
    def deref(self):
        return self
    def __init__(self):
        super().__init__()
        self.conditionalLinks = []
        for attrName in self.attrNames:
            setattr(self, attrName, '')
    def toXmlHeader(self, conditionsWidget):
        header = ET.Element('header')

        conditions = ET.SubElement(header, 'conditions')
        links = ET.SubElement(header, 'links')
        it = QTreeWidgetItemIterator(conditionsWidget, QTreeWidgetItemIterator.All)
        while it.value():
            item = it.value()
            ET.SubElement(links, "int").text = item.link
            ET.SubElement(conditions, "string").text = item.condition
            it += 1

        ET.SubElement(header, 'dlg_name').text = self.dialogueName
        ET.SubElement(header, 'def_link').text = self.defaultLink
        ET.SubElement(header, 'def_speaker_name').text = self.defaultSpeakerName
        ET.SubElement(header, 'def_portrait').text = self.defaultPortrait

        return header

class Editor:
    def __init__(self, filename=None):
        self.header = Header()
        self.ui = uic.loadUi('main.ui', EditorMainWindow())
        self.ui.splitter.setSizes([500, 1])
        self.currentFile = None
        # self.ui.splitter.splitterMoved.connect(lambda *x: print(*x))
        def onSelect():
            item = self.ui.tree.currentItem()
            if item:
                self.rebindAll()
        self.ui.tree.itemSelectionChanged.connect(onSelect)
        self.wireUpDialogueTree()
        self.wireUpActions()
        self.bindHeader()
        if filename:
            xml = ET.parse(filename)
            self.populateTree(xml.getroot())
            self.fillHeader(xml.getroot())
            self.currentFile = filename

    def rebindAll(self):
        allFields = set(['portrait', 'speakerName', 'text', 'script', 'condition', 'UID'])
        fields = self.ui.tree.currentItem().dataModel()
        print(fields)
        for f in allFields:
            widget = getattr(self.ui, f)
            widget.setEnabled(f in fields)
            if f in fields:
                self.bind(widget, self.ui.tree.currentItem(), f)
            else:
                # clear when disabled
                self.unbind(widget)
                widget.clear()
            try:
                label = getattr(self.ui, f + 'Label')
                label.setEnabled(f in fields)
            except AttributeError:
                pass

    def bindHeader(self):
        def bindHeader(name):
            self.bind(getattr(self.ui, name), self.header, name)
        self.bind(self.ui.defaultPortrait, self.header, 'defaultPortrait')
        self.bind(self.ui.dialogueName, self.header, 'dialogueName')
        self.bind(self.ui.defaultSpeakerName, self.header, 'defaultSpeakerName')
        self.bind(self.ui.defaultLink, self.header, 'defaultLink')

    def fillHeader(self, xml):
        header = xml.find('./header')
        self.header.defaultPortrait = header.find('./def_portrait').text
        self.header.defaultLink = header.find('./def_link').text
        self.header.defaultSpeakerName = header.find('./def_speaker_name').text
        self.header.dialogueName = header.find('./dlg_name').text
        self.bindHeader()
        conditions = [e.text for e in header.find('./conditions')]
        links = [e.text for e in header.find('./links')]
        # self.ui.headerConditions.setRowCount(max(len(conditions), len(links)))
        self.ui.headerConditions.clear()
        for (cond, link) in zip_longest(conditions, links):
            print(cond, link)
            item = ConditionalLink(cond, link)
            self.ui.headerConditions.addTopLevelItem(item)
        self.ui.headerConditions.resizeColumnToContents(0)

    def UI_ChangeReference(self, reference):
        node = NodeSelectDialog.selectNode(self, self.ui.tree.currentItem().deref())
        if node:
            reference.ref = AnswerLink(node,
                                       condition=reference.getProperty('condition'))
            reference.emitDataChanged()
            self.rebindAll()

    def UI_AddAnswer(self, parent):
        answer = AnswerItem('<text>')
        parent.addChild(answer)
        self.ui.tree.setCurrentItem(answer)
        self.ui.text.setFocus()
        self.ui.text.selectAll()

    def UI_AddAnswerLink(self, parent):
        npcItem = NPCItem(9999, '<text>')
        link = AnswerLink(npcItem)
        parent.addChild(link)
        self.ui.tree.setCurrentItem(link)
        self.ui.text.setFocus()
        self.ui.text.selectAll()

    def UI_RemoveNode(self, node):
        "UI action 'remove this node'"
        parent = node.parent()
        parent.removeChild(node)

    def UI_AddReference(self, node):
        target = NodeSelectDialog.selectNode(self)
        if target:
            reference = ReferenceItem(AnswerLink(target))
            node.addChild(reference)
            self.ui.tree.setCurrentItem(reference)

    def UI_FollowReference(self, reference):
        canonical = self.findCanonical(reference.deref())
        self.ui.tree.setCurrentItem(canonical)

    def askSaveIfNecessary(self):
        return QMessageBox.question(self.ui,
                                    'Save?',
                                    'You have unsaved changes. Save them?',
                                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

    def UI_New(self):
        "UI action 'New file'"
        self.currentFile = None
        self.ui.tree.clear()
        self.ui.headerConditions.clear()
        print(self.ui.children())
        for child in self.ui.findChildren((QLineEdit, QPlainTextEdit)):
            child.clear()
        self.header = Header()
        self.bindHeader()

    def UI_Open(self, *args):
        "UI action 'Open'"
        filename, _ = QFileDialog.getOpenFileName(self.ui, "File...", "", "AoD Dialogue Files (*.xml)")
        if filename:
            xml = ET.parse(filename)
            self.populateTree(xml.getroot())
            self.fillHeader(xml.getroot())
            self.currentFile = filename

    def UI_Save(self):
        "UI action 'Save'"
        if self.currentFile:
            self.saveFile(self.currentFile)
        else:
            self.UI_SaveAs()

    def UI_SaveAs(self):
        "UI action 'Save as'"
        filename, _ = QFileDialog.getSaveFileName(self.ui, 'Save...', '', 'AoD Dialogue Files (*.xml)')
        if filename:
            self.saveFile(filename)
            self.currentFile = filename

    def UI_AddHeaderCondition(self):
        "UI action 'add new header condition'"
        item = ConditionalLink()
        self.ui.headerConditions.addTopLevelItem(item)
        self.ui.headerConditions.setCurrentItem(item)
        self.ui.headerConditions.editItem(item)

    def UI_RemoveHeaderCondition(self):
        "UI action 'remove selected header condition'"
        index = self.ui.headerConditions.indexOfTopLevelItem(self.ui.headerConditions.currentItem())
        if index != -1:
            self.ui.headerConditions.takeTopLevelItem(index)

    def UI_CopyUID(self):
        "UI action 'copy current node UID to clipboard'"
        app.clipboard().setText(str(self.ui.tree.currentItem().getProperty('UID')))

    def saveFile(self, filename):
        "Serialize the current data into xml dialogue format and write it to `filename`"
        try:
            uglyXml = ET.tostring(self.toXml(), encoding='unicode')
        except BaseException as e:
            QMessageBox.information(self.ui, 'Error!', str(e))
            return
        prettyXml = minidom.parseString(uglyXml).toprettyxml(indent = ' '*2)
        f = open(filename, 'wb')
        f.write(prettyXml.encode('utf-8'))
        f.close()
        del f
        return prettyXml

    def wireUpActions(self):
        "Connect various actions to relevant signals."
        self.ui.actionNew    .triggered.connect(self.UI_New)
        self.ui.actionOpen   .triggered.connect(self.UI_Open)
        self.ui.actionSave   .triggered.connect(self.UI_Save)
        self.ui.actionSaveAs .triggered.connect(self.UI_SaveAs)
        self.ui.uidCopyButton.clicked  .connect(self.UI_CopyUID)

        # context menu for the dialogue tree widget
        refItemMenu = QMenu()
        refItemMenu.addAction('Edit reference...', lambda *_: self.UI_ChangeReference(self.ui.tree.currentItem()))
        refItemMenu.addAction('Follow reference', lambda *_: self.UI_FollowReference(self.ui.tree.currentItem()))
        refItemMenu.addAction('Delete reference', lambda *_: self.UI_RemoveNode(self.ui.tree.currentItem()))

        npcItemMenu = QMenu()
        npcItemMenu.addAction('Add player answer', lambda *_: self.UI_AddAnswer(self.ui.tree.currentItem()))
        # npcItemMenu.addAction('Remove', lambda *_: self.UI_RemoveNode(self.ui.tree.currentItem()))

        answerLinkMenu = QMenu()
        answerLinkMenu.addAction('Add player answer', lambda *_: self.UI_AddAnswer(self.ui.tree.currentItem()))

        answerItemMenu = QMenu()
        answerItemMenu.addAction('Add NPC node', lambda *_: self.UI_AddAnswerLink(self.ui.tree.currentItem()))
        answerItemMenu.addAction('Add reference', lambda *_: self.UI_AddReference(self.ui.tree.currentItem()))

        menuByClass = {ReferenceItem: refItemMenu,
                       NPCItem: npcItemMenu,
                       AnswerLink: answerLinkMenu,
                       AnswerItem: answerItemMenu}
        def UI_TreeContextMenu(position):
            currentItem = self.ui.tree.currentItem()
            if currentItem:
                globalPosition = self.ui.tree.mapToGlobal(position)
                menu = menuByClass.get(currentItem.__class__, None)
                if menu:
                    menu.exec(globalPosition)
        self.ui.tree.customContextMenuRequested.connect(UI_TreeContextMenu)

        # header group height persistence across show/hide
        class Cell:
            def __init__(self, value):
                self.value = value
        oldHeaderBoxHeight = Cell(self.ui.splitter.sizes()[2])
        def setSplitterSize(splitter, cellNo, newSize):
            sizes = splitter.sizes().copy()
            sizediff = (newSize - sizes[cellNo]) / (len(sizes)-1)
            for i in range(len(sizes)):
                if i == cellNo:
                    sizes[i] = newSize
                else:
                    sizes[i] = sizes[i] - sizediff
            splitter.setSizes(sizes)
        def showHideGroupBoxItems(visibility):
            self.ui.headerFrame.setVisible(visibility)
            if visibility is False:
                oldHeaderBoxHeight.value = self.ui.splitter.sizes()[2]
                setSplitterSize(self.ui.splitter, 2, 0)
            else:
                setSplitterSize(self.ui.splitter, 2, oldHeaderBoxHeight.value)
        self.ui.headerGroup.toggled.connect(showHideGroupBoxItems)

        # header conditional links add/remove buttons
        self.ui.addCondition.clicked.connect(self.UI_AddHeaderCondition)
        self.ui.removeCondition.clicked.connect(self.UI_RemoveHeaderCondition)

        # fix tab movement while editing (first across, then down)
        def moveCursor(this, cursorAction, modifiers):
            if cursorAction == QAbstractItemView.MoveNext or cursorAction == QAbstractItemView.MovePrevious:
                index = this.currentIndex()
                number = this.columnCount()*index.row() + index.column()
                direction = 1 if cursorAction == QAbstractItemView.MoveNext else -1
                if number+direction < this.columnCount()*(this.topLevelItemCount()) and \
                   number+direction >= 0:
                    return this.model().index((number+direction) // this.columnCount(),
                                              (number+direction)  % this.columnCount(),
                                              index.parent())
            return QTreeWidget.moveCursor(this, cursorAction, modifiers)
        # monkey patch the instance
        self.ui.headerConditions.moveCursor = types.MethodType(moveCursor, self.ui.headerConditions)

    def bind(self, editWidget, obj, attributeName):
        """Bind a text editing widget `editWidget` to the property
obj.attributeName.  One-way binding from widget to object (widget won't be updated if property changes)."""
        signal = editWidget.textChanged if not isinstance(editWidget, QLineEdit) else editWidget.textEdited
        setter = None
        if isinstance(editWidget, QLineEdit):
            setter = editWidget.setText
        elif isinstance(editWidget, QPlainTextEdit):
            setter = editWidget.setPlainText
        getText = None
        if isinstance(editWidget, QLineEdit):
            getText = editWidget.text
        elif isinstance(editWidget, QPlainTextEdit):
            getText = editWidget.toPlainText
        try:
            # throws up if nothing is connected
            signal.disconnect()
        except:
            pass
        setter('' if obj.getProperty(attributeName) is None else str(obj.getProperty(attributeName)))
        # print('binding: %s.%s, %s' % (obj, attributeName, obj.getProperty(attributeName)))
        def notify(*args):
            obj.setProperty(attributeName, getText())
            for ref in self.findAllReferences(obj.deref()):
                ref.emitDataChanged()
        signal.connect(notify)

    def unbind(self, editWidget):
        "Unbind the given widget from all 'change' signals."
        signal = editWidget.textChanged if not isinstance(editWidget, QLineEdit) else editWidget.textEdited
        try:
            signal.disconnect()
        except:
            pass

    def appendItems(self, added, root):
        "Auxiliary: append nodes to given root."
        answers = None
        for answer in root.getAnswers():
            root.addChild(answer)
            for link in answer.links:
                assert(isinstance(link.link, NPCItem))
                if link.link in added:
                    # print('ALREADY ADDED: [%s]' % link.link.text)
                    answer.addChild(ReferenceItem(link))
                else:
                    added.append(link.link)
                    answer.addChild(link)
                    self.appendItems(added, link)

    def populateTree(self, xmlroot):
        "Populate the UI dialogue tree from given xml root."
        self.ui.tree.clear()
        added = []
        allItems = []
        uid_to_npc_item = {}
        xParts = xmlroot.find('./parts')
        print(xParts, bool(xParts))
        if xParts is None:
            raise BadXmlException()
        xDlgParts = xParts.findall('./dlgPart')
        # print('xDlgParts: %s, xParts', xDlgParts, xParts)
        if xDlgParts:
            for part in xDlgParts:
                item = NPCItem(subtext(part, './UID'),
                               subtext(part, './npc_text'),
                               subtext(part, './portrait'),
                               subtext(part, './speaker_name'),
                               '\n'.join(map(lambda x: x.text,
                                             part.findall('./onLoadScripts/string'))))
                allItems.append(item)
                # print('saving %s' % item.UID)
                uid_to_npc_item[item.UID] = item
                item.answers = []
                for xAnswer in part.findall('./answers/dlgAnsw'):
                    defaultLink = AnswerLink(subtext(xAnswer, './def_link'),
                                             None)
                    answer = AnswerItem(subtext(xAnswer, './text'),
                                        subtext(xAnswer, './checkOnAppear'),
                                        '\n'.join(map(lambda x: x.text,
                                                      xAnswer.findall('./scriptsOnClick/string'))),
                                        [defaultLink])
                    checksOnClick = xAnswer.findall('./checksOnClick/string')
                    linksOnClick = xAnswer.findall('./linksOnClick/int')
                    #scriptsOnClick = xAnswer.findall('./scriptsOnClick/string')

                    for (check, link) in zip_longest(checksOnClick, linksOnClick):
                        print('appending links, %s, %s' % (link, check))
                        answer.links.append(AnswerLink(int(link.text),
                                                       check.text))
                    item.answers.append(answer)
        # print('before resolving, allItems: %s', allItems)
        # resolve answer links
        for item in allItems:
            for answer in item.answers:
                for link in answer.links:
                    if link.link is not int:
                        link.link = uid_to_npc_item[int(link.link)]

        # actually populate the tree
        def_link = subtext(xmlroot, './header/def_link')
        roots = []
        if def_link:
            roots.append(def_link)
        roots.extend([x.text for x in xmlroot.findall('./header/links/int')])
        roots = [int(x) for x in roots]
        for rootItem in [item for item in allItems if item.UID in roots]:
            # print('rootItem', rootItem)
            self.ui.tree.addTopLevelItem(rootItem)
            added.append(rootItem)
            self.appendItems(added, rootItem)
        if self.ui.tree.topLevelItemCount() > 0:
            self.ui.tree.setCurrentItem(self.ui.tree.topLevelItem(0))
            self.expandAllItems(self.ui.tree.currentItem())

    def toXml(self):
        "Convert current dialogue data to ElementTree xml data."
        rootItem = self.ui.tree.invisibleRootItem()
        rootElement = ET.Element('dlgData')
        rootElement.append(self.header.toXmlHeader(self.ui.headerConditions))
        uids_processed = []
        parts = ET.SubElement(rootElement, 'parts')
        items = [item for item in self.iterateTreeItems(self.ui.tree) if isinstance(item.deref(), NPCItem)]
        for item in sorted(items, key=lambda x: x.deref().UID):
            # item = item.deref()
            # print('item:', item)
            if isinstance(item.deref(), NPCItem) and not item.deref().UID in uids_processed:
                answerItems = []
                answerItemsCount = item.childCount()
                # print('answerItemsCount', answerItemsCount, item.deref().UID)
                # ET.SubElement('dlgPart')
                for i in range(answerItemsCount):
                    answerItems.append(item.child(i))
                parts.append(item.deref().toXmlPart(answerItems))
                uids_processed.append(item.deref().UID)
        return rootElement

    def findCanonical(self, npcItem):
        "Find the canonical item representing `npcItem`."
        assert(self.ui.tree)
        for item in self.iterateTreeItems(self.ui.tree):
            if item.deref() == npcItem and not isinstance(item, ReferenceItem):
                return item
        return None

    def findAllReferences(self, item):
        "Find all items in current tree that link/refer to the given item.."
        assert(self.ui.tree)
        return [i for i in self.iterateTreeItems(self.ui.tree) if i.deref() == item]

    def findAllNpcNodes(self):
        "Find all NPCItem nodes."
        assert(self.ui.tree)
        rv = {}
        for item in self.iterateTreeItems(self.ui.tree):
            value = item.deref()
            if isinstance(value, NPCItem):
                rv[value.UID] = value
        return list(rv.values())

    def wireUpDialogueTree(self):
        "Wire up the dialogue tree signals."
        def onItemDoubleClicked(item, column):
            if isinstance(item, ReferenceItem):
                self.UI_FollowReference(item)
        self.ui.tree.itemDoubleClicked.connect(lambda *args: onItemDoubleClicked(*args))

    def expandAllItems(self, expand):
        "Expand all items in the dialogue tree."
        for item in self.iterateTreeItems(self.ui.tree):
            if expand:
                self.ui.tree.expandItem(item)
            else:
                self.ui.tree.collapseItem(item)

    def iterateTreeItems(self, tree):
        "Iterate over all items in the current dialogue tree, non-dereferenced."
        it = QTreeWidgetItemIterator(tree, QTreeWidgetItemIterator.All)
        while it.value():
            yield it.value()
            it += 1
        raise StopIteration()

if __name__ == '__main__':
    global app
    app = QApplication(sys.argv)
    # ui = main()
    # ui.show()
    editor = Editor(sys.argv[1] if len(sys.argv) > 1 else None)
    editor.ui.showMaximized()
    sys.exit(app.exec_())
