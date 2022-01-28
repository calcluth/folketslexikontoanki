# import the main window object (mw) from aqt
from aqt import mw
from anki import notes
import re
import requests
import json
# import the "show info" tool from utils.py
from aqt.utils import showInfo, qconnect
# import all of the Qt GUI library
from aqt.qt import *
from bs4 import BeautifulSoup
# We're going to add a menu item below. First we want to create a function to
# be called when the menu item is activated.
import pathlib
from . import dialog
import urllib.request

import xml.etree.ElementTree as ET

# tree = ET.parse('dict.xml')
# root = tree.getroot()
 

def testFunction() -> None:
    # get the number of cards in the current collection, which is stored in
    # the main window
    (sheetsurl, model, ok) = ImportSettingsDialog().getDialogResult()

    # sheetsurl, ok = QInputDialog.getText(mw, 'input dialog', 'Enter the URL of the exported Google Translate sheet')
    if ok:
        # showInfo("%s" % sheetsurl)
        # https://docs.google.com/spreadsheets/d/1t2bMQamnldHL_atv0RlNlKasKs5EV1OnI_rLj8DwOCU/export?format=csv&gid=1216286449
        sheetid = str(re.findall('\/d\/(.*?)\/', sheetsurl)[0])
        csvurl = "https://docs.google.com/spreadsheets/d/"+sheetid+"/export?format=csv"
        data = download(csvurl).split("\n")

        # path = QFileDialog.getExistingDirectory(mw, "Import Directory")
        # path = os.path
        # self.mediaDir = path
        # data = str(data)
        # printdata = data[0:1000]

        """Paths to directories get determined based on __file__"""
        asset_dir = os.path.join(pathlib.Path(__file__).parent.absolute(), "assets")
        temp_dir = os.path.join(pathlib.Path(__file__).parent.absolute(), "temp")
        user_files_dir = os.path.join(pathlib.Path(__file__).parent.absolute(), "user_files")
        log_dir = os.path.join(pathlib.Path(__file__).parent.absolute(), "user_files", "logs")

        debug_mode = os.path.isfile(os.path.join(user_files_dir, ".debug"))

        """Ensure directories (create if not existing)"""
        for path in [temp_dir, user_files_dir, log_dir, asset_dir]:
            if not os.path.exists(path):
                os.makedirs(path)


        mw.progress.start(immediate=True, label="Downloading dictionary", max=len(data))
        # Download the dictionary from folkets lexikan
        dict =  temp_dir+'/dict.xml'
        url = 'https://folkets-lexikon.csc.kth.se/folkets/folkets_sv_en_public.xml'
        urllib.request.urlretrieve(url, dict)

        # Get prebiously imported CSV
        if os.path.isfile(user_files_dir+"/previousgoogletranslate.csv"):
            f = open(user_files_dir+"/previousgoogletranslate.csv", "r")
            previousdata = f.read()
            previousdata = previousdata.split("\n")
            f.close()
        else:
            previousdata = []

        # did = mw.col.decks.all()
        # decks =mw.col.decks.byName('Swedish')
        #
        # did = decks['id']
        # # showInfo("%s" % did)
        did = mw.col.decks.id("Swedish")
        # mw.col.decks.select(did)
        # anki defaults to the last note type used in the selected deck
        # m = mw.col.models.byName("Basic")
        # deck = mw.col.decks.get(did)
        # deck['mid'] = m['id']
        # mw.col.decks.save(deck)

        (root, dirs, files) = next(os.walk(path))


        out = ""
        j= 1

        for line in data:
            repeated = False
            for prevline in previousdata:
                if prevline == line:
                    repeated = True
            if not repeated:
                cols = line.split(',')
                fromlang = cols[0]
                tolang = cols[1]
                firstword = cols[2]
                secondword = cols[3]

                if fromlang == "Swedish":
                    word_sv = firstword.replace("'", "&amp;#39;").lower()
                    word_en = secondword.replace("'", "&amp;#39;").lower()
                else:
                    word_sv = secondword.replace("'", "&amp;#39;").lower()
                    word_en = firstword.replace("'", "&amp;#39;").lower()

                    # print(word_sv))
                card = createCard(dict,root, word_sv, word_en);

                if card is not None:
                    note = notes.Note(mw.col, model)
                    note.model()['did'] = did
                    # Update the underlying dictionary to accept more arguments for more customisable cards
                    # n._fmap = defaultdict(str, n._fmap)


                    note['Front'] = card['front']
                    note['Back'] = card['back']
                    if card['soundpath'] is not None:
                        soundfname = mw.col.media.addFile(card['soundpath'])
                        note['Back'] += u'[sound:%s]' % soundfname

                    note.tags.append('importsheets')
                    # n.addTag('ensv')

                    num_cards = mw.col.addNote(note)
                    if num_cards:
                        j+=1
                    # if card['soundpath'] is not None:
                    #     showInfo("%s" % card['soundpath'])
                    # showInfo("%s" % card['front'])

                    mw.progress.update(value=j)

        mw.progress.finish()
        mw.deckBrowser.refresh()
        printdata = out
        # showInfo("%s" % printdata)

        # text_edit = QPlainTextEdit()
        # text = open('~/Library/Application Support/Anki2/info.txt').read()
        # showInfo("%s" % da)
        # text_edit.setPlainText(text)


    cardCount = mw.col.cardCount()
    # show a message box
    showInfo("Card count: %d" % cardCount)

def _parseHtmlPageToAnkiDeck(data, lazyLoadImages=False):

    orgData = _generateOrgListFromHtmlPage(data)

    return orgData

def download(url):

    response = requests.get(url)
    if response.status_code == 200:
        data = response.content
    else:
        raise Exception("Failed to get url: {}".format(response.status_code))

    data = data.decode("utf-8")

    return data


def _getCssStyles(cssData):

    # Google docs used the following class for lists $c1
    cSectionRegexPattern = "\.c\d{1,2}\{[^\}]+}"
    cssSections = re.findall(cSectionRegexPattern, cssData.text)

    cssStyles = {}
    # for each c section extract critical data
    regexValuePattern = ":[^;^}\s]+[;}]"
    startSectionRegex = "[;{]"
    for section in cssSections:
        name = re.findall("c[\d]+", section)[0]
        color = re.findall("{}{}{}".format(startSectionRegex, "color", regexValuePattern), section)
        fontStyle = re.findall("{}{}{}".format(startSectionRegex, "font-style", regexValuePattern), section)
        fontWeight = re.findall("{}{}{}".format(startSectionRegex, "font-weight", regexValuePattern), section)
        textDecoration = re.findall("{}{}{}".format(startSectionRegex, "text-decoration", regexValuePattern), section)
        verticalAlign = re.findall("{}{}{}".format(startSectionRegex, "vertical-align", regexValuePattern), section)

        # Ignore default values
        if (len(color) >0 and "color:#000000" in color[0]):
            color = []
        if (len(fontWeight) >0 and "font-weight:400" in fontWeight[0]):
            fontWeight = []
        if (len(fontStyle) >0 and "font-style:normal" in fontStyle[0]):
            fontStyle = []
        if (len(textDecoration) >0 and "text-decoration:none" in textDecoration[0]):
            textDecoration = []
        if (len(verticalAlign) >0 and "vertical-align:baseline" in verticalAlign[0]):
            verticalAlign = []

        d = [color, fontStyle, fontWeight, textDecoration, verticalAlign]

        styleValues = []
        for i in d:
            if len(i) > 0:
                cleanedStyle = i[0][1:-1]
                styleValues.append(cleanedStyle)
        cssStyles[name] = styleValues

    return cssStyles
def _startOfMultiLineComment(item):

    # Get span text
    if item.name == "p":
        line = ""
        sections = item.find_all("span")
        for span in sections:
            line += span.text
        if ("#multilinecommentstart" == line.replace(" ", "").lower()):
            return True
    return False

def _endOfMultiLineComment(item):

    # Get span text
    if item.name == "p":
        line = ""
        sections = item.find_all("span")
        for span in sections:
            line += span.text
        if ("#multilinecommentend" == line.replace(" ", "").lower()):
            return True
    return False

def _extractSpanWithStyles(soupSpan, cssStyles):

    text = soupSpan.text
    classes = soupSpan.attrs.get("class")

    if classes == None:
        return text

    relevantStyles = []
    for clazz in classes:
        if cssStyles.get(clazz) != None:
            for style in cssStyles.get(clazz):
                relevantStyles.append(style)


    if len(relevantStyles) > 0:
        styleAttributes = ""
        for i in relevantStyles:
            styleAttributes += i + ";"
        # Added whitespace around the text. The whitespace is getting stripped somewhere
        text = text.strip()
        styledText = '<span style="{}"> {} </span>'.format(styleAttributes, text)
        return styledText
    else:
        return text
def _generateOrgListFromHtmlPage(data):
    orgStar = "*"
    soup = BeautifulSoup(data, 'html.parser')
    title = soup.find("div", {"id": "title"})
    deckName = title.text
    contents = soup.find_all(["ul", "p"])

    ## Try and get CSS

    cssData = soup.find_all("style")
    cssStyles = {}
    for css in cssData:
        cssData = soup.find_all("style")[1]
        styleSection = _getCssStyles(cssData)
        cssStyles.update(styleSection)

    multiCommentSection = False
    orgFormattedFile = []
    for item in contents:
        # Handle multiLine comment section
        if _startOfMultiLineComment(item):
            multiCommentSection = True
            continue
        elif multiCommentSection and _endOfMultiLineComment(item):
            multiCommentSection = False
            continue
        elif multiCommentSection:
            continue

        # Handle normal line
        if item.name == "p":
            # Get span text
            line = ""
            textSpans = item.find_all("span")
            # print(textSpans)
            for span in textSpans:
                line += span.text

            # Get link text
            linkText = ""
            allLinks = item.find_all("a")
            for link in allLinks:
                text = link.contents
                for t in text:
                    linkText += t

            # Ignore line if span and link text are the same
            if len(line) > 0 and linkText != line:
                orgFormattedFile.append(line)

        # Hanlde list line
        elif item.name == "ul":
            # print("ul")
            listItems = item.find_all("li")

            # Item class is in the format of "lst-kix_f64mhuyvzb86-1" with last numbers as the level
            classes = item["class"]  # .split("-")[-1])
            regexSearch = "^[\w]{3}-[\w]{3,}-[\d]{1,}"
            indentation = -1
            for i in classes:
                if re.match(regexSearch, i) != None:
                    indentation = int(i.split("-")[-1])

            if (indentation == -1):
                raise Exception("Could not find the correct indentation")

            itemText = []
            imageConfig = ""
            for i in listItems:
                # Get all spans
                textSpans = i.find_all("span")
                lineOfText = ""
                for span in textSpans:
                    lineOfText += _extractSpanWithStyles(span, cssStyles)

                    # Check for images and take first
                    images = span.find_all("img")
                    if len(images) >= 1:
                        imageTemplate = " [image={}]"  # height={}, width={}
                        # Get image styles
                        styles = images[0]["style"]
                        searchRegex = "{}:\s[^;]*;"
                        height = re.findall(searchRegex.format("height"), styles)[0].split(":")[1].replace(";",
                                                                                                           "").strip()
                        width = re.findall(searchRegex.format("width"), styles)[0].split(":")[1].replace(";",
                                                                                                         "").strip()
                        imageConfig = " # height={}, width={}".format(height, width)

                        # Build image line
                        imageText = imageTemplate.format(images[0]["src"])
                        lineOfText += imageText

                # Add image metadata at end of line once
                if len(imageConfig) > 0:
                    lineOfText += imageConfig
                    imageConfig = ""

                itemText.append(lineOfText)

            indentation += 1
            orgStars = (orgStar * indentation)
            for line in itemText:
                if (_closeLineBreak(line)):
                    orgFormattedFile.append(line)
                else:
                    formattedListItem = "{} {}".format(orgStars, line)
                    orgFormattedFile.append(formattedListItem)



        else:
            pass
            # print("Unknown line type: {}".format(item.name))

    return {"deckName": deckName, "data": orgFormattedFile}

class ImportSettingsDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self, mw)
        self.form = dialog.Ui_Form()
        self.form.setupUi(self)
        self.form.buttonBox.accepted.connect(self.accept)
        self.form.buttonBox.rejected.connect(self.reject)
        # self.form.browse.clicked.connect(self.onBrowse)
        # The path to the media directory chosen by user
        self.sheetsurl= None
        # The number of fields in the note type we are using
        self.fieldCount = 0
        self.populateModelList()
        self.exec_()

    def populateModelList(self):
        """Fill in the list of available note types to select from."""
        models = mw.col.models.all()
        for m in models:
            item = QListWidgetItem(m['name'])
            # Put the model in the widget to conveniently fetch later
            item.model = m
            self.form.modelList.addItem(item)
        self.form.modelList.sortItems()
        # self.form.modelList.currentRowChanged.connect(self.populateFieldGrid)
        # Triggers a selection so the fields will be populated
        self.form.modelList.setCurrentRow(0)

    def populateFieldGrid(self):
        """Fill in the fieldMapGrid QGridLayout.
        Each row in the grid contains two columns:
        Column 0 = QLabel with name of field
        Column 1 = QComboBox with selection of mappings ("actions")
        The first two fields will default to Media and File Name, so we have
        special cases for rows 0 and 1. The final row is a spacer."""

        self.clearLayout(self.form.fieldMapGrid)
        # Add note fields to grid
        row = 0
        for field in self.form.modelList.currentItem().model['flds']:
            self.createRow(field['name'], row)
            row += 1
        # # Add special fields to grid
        # for name in SPECIAL_FIELDS:
        #     self.createRow(name, row, special=True)
        #     row += 1
        self.fieldCount = row
        self.form.fieldMapGrid.addItem(
            QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding), row, 0)

    # def createRow(self, name, idx, special=False):
    #     lbl = QLabel(name)
    #     cmb = QComboBox()
    #     cmb.addItems(ACTIONS)
    #     # piggy-back the special flag on QLabel
    #     lbl.special = special
    #     self.form.fieldMapGrid.addWidget(lbl, idx, 0)
    #     self.form.fieldMapGrid.addWidget(cmb, idx, 1)
    #     if idx == 0: cmb.setCurrentIndex(1)
    #     if idx == 1: cmb.setCurrentIndex(2)

    def getDialogResult(self):
        """Return a tuple containing the user-defined settings to follow
        for an import. The tuple contains four items (in order):
         - Path to chosen media directory
         - The model (note type) to use for new notes
         - A dictionary that maps each of the fields in the model to an
           integer index from the ACTIONS list
         - True/False indicating whether the user clicked OK/Cancel"""

        if self.result() == QDialog.Rejected:
            return None, None, False

        model = self.form.modelList.currentItem().model
        # Iterate the grid rows to populate the field map
        # fieldList = []
        # grid = self.form.fieldMapGrid
        # for row in range(self.fieldCount):
        #     # QLabel with field name
        #     field = grid.itemAtPosition(row, 0).widget().text()
        #     # Piggy-backed special flag
        #     special = grid.itemAtPosition(row, 0).widget().special
        #     # QComboBox with index from the action list
        #     actionIdx = grid.itemAtPosition(row, 1).widget().currentIndex()
        #     fieldList.append((field, actionIdx, special))
        return self.form.sheetsurl.text(), model , True

    def accept(self):
        # Show a red warning box if the user tries to import without selecting
        # a directory.
        # if not self.sheetsurl:
        #     self.form.sheetsurl.setStyleSheet("border: 1px solid red")
        #     return
        QDialog.accept(self)

    def clearLayout(self, layout):
        """Convenience method to remove child widgets from a layout."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget() is not None:
                child.widget().deleteLater()
            elif child.layout() is not None:
                self.clearLayout(child.layout())

def compareWords(a,b):
	length=min(len(a),len(b))
	count = 0
	for i in range(length):
		if a[i] == b[i]:
			count+=1

	return count

def createCard(dict,rootdir,word_sv, word_en):

    tree = ET.parse(dict)

    root = tree.getroot()
    words = root.findall("word[@value='" + word_sv + "']")
    from_lang = "sv"

    if len(words) == 0:
        # print('nope')
        words = root.findall("word/translation[@value='" + word_en + "']...")
        from_lang = "en"
        # print(words)
        if len(words) == 0:
            return None;

    j = 0
    target = 0

    overlap = len(words) * [0]

    for word in words:
        # print("word "+str(j))
        card = {}

        card['translationdata'] = word.find('translation')
        # print(card['translationdata'])
        if card['translationdata'] is not None:
            card['translation'] = card['translationdata'].get('value')
            if from_lang == "se":
                overlap[j] = compareWords(card['translation'], word_en)
            # print(card['translation']+" vs "+word_en)
            else:
                # print("v "+word.get('value'))
                # print(word_sv)
                overlap[j] = compareWords(word.get('value'), word_sv)
            # print(word.get('value')+" vs "+word_sv)
        j += 1

    target = overlap.index(max(overlap))
    # print("target "+str(target))
    # print(overlap)

    word = words[target]
    card = {}
    card['value'] = word.get('value')
    card['value']
    card['wordclass'] = word.get('class')

    card['comment'] = word.get('comment')
    card['translationdata'] = word.find('translation')

    if card['translationdata'] is None:
        return None;
    card['translation'] = card['translationdata'].get('value')
    card['translation']
    card['example'] = word.find('example')
    if card['example'] is not None:
        card['examplesv'] = card['example'].get('value')
        card['exampleen'] = ""
        trans = card['example'].find('translation')
        if trans is not None:
            card['exampleen'] = trans.get('value')
    else:
        card['examplesv'] = None
        card['exampleen'] = None

    card['phonetic'] = word.find('phonetic')
    card['soundpath'] = None
    
    if card['phonetic'] is not None:
        card['ipa'] = card['phonetic'].find('value')
        card['soundfile'] = card['phonetic'].find('soundFile')
        if card['soundfile'] is not None:
            card['soundfile'] = card['soundfile'].replace("å", "0345").replace("ö", "0366").replace("ä","0344").replace(" ", "%20").replace("swf", "mp3")
            soundpath = os.path.join(rootdir, card['soundfile'])
            card['soundpath'] = soundpath
        if card['soundfile'] is not None:
            if not os.path.exists(soundpath):
                urllib.request.urlretrieve("http://lexin.nada.kth.se/sound/"+card['soundfile'], soundpath)
                # fname = mw.col.media.addFile(path)
        else:
            card['soundfile'] = None
    else:
        card['ipa'] = None
        card['soundfile'] = None
        card['soundpath'] = None

    # print("value: ",card['value'])
    # print("comment: ",card['comment'])
    # print("translation: ",card['translation'])
    # print("wordclass: ",card['wordclass'])
    # print("soundfile: ",card['soundfile'])

    card['wordclassh'] = ""

    if card['wordclass'] is not None:
        if card['wordclass'] == 'pp':
            card['wordclassh'] = "<br>[preposition] "
        if card['wordclass'] == 'pp':
            card['wordclassh'] = "<br>[preposition] "

    card["front"] = ""
    card["back"] = ""

    card['front'] += card['translation'] + "<br><br>"

    card['back'] += card['value'] + "<br><br>"

    if card['wordclass'] is not None:
        if card['wordclass'] == 'pp':
            card['front'] += "[preposition]<br><br>"
        if card['wordclass'] == 'nn':
            card['front'] += "[noun]<br><br>"
        if card['wordclass'] == 'ab':
            card['front'] += "[adverb]<br><br>"
        if card['wordclass'] == 'jj':
            card['front'] += "[adjective]<br><br>"
        if card['wordclass'] == 'abbrev':
            card['front'] += "[abbreviation]<br><br>"
        if card['wordclass'] == 'pn':
            card['front'] += "[pronoun]<br><br>"
        if card['wordclass'] == 'vb':
            card['front'] += "[verb]<br><br>"
        if card['wordclass'] == 'in':
            card['front'] += "[interjection]<br><br>"
        if card['wordclass'] == 'rg':
            card['front'] += "[number]<br><br>"
        if card['wordclass'] == 'kn':
            card['front'] += "[conjunction]<br><br>"
        if card['wordclass'] == 'pm':
            card['front'] += "[egennamn]<br><br>"
        if card['wordclass'] == 'sn':
            card['front'] += "[subjunction]<br><br>"

    if card['example'] is not None:
        card['front'] += "e.g. " + card['exampleen'] + "<br><br>"
        card['back'] += "e.g. " + card['examplesv'] + "<br><br>"

    if card['ipa'] is not None:
        card['back'] += "[" + card['ipa'] + "]"

    # if card['soundfile'] is not None:
    #     card['back'] += "[sound:" + card['soundfile'] + "]"

    card['csvline'] = card['front'] + "\t" + card['back'] + "\tautoimport"
    return card
# create a new menu item, "test"
action = QAction("Import from Google", mw)
# set it to call testFunction when it's clicked
qconnect(action.triggered, testFunction)
# and add it to the tools menu
mw.form.menuTools.addAction(action)