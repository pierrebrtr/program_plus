from fastapi import FastAPI
from bs4 import BeautifulSoup
import urllib.request
import dateparser
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

elligibleDiffusorTop14Dict = {
    "https://www.lnr.fr/sites/default/files/styles/mini_diffuseur/public/Log-CANALnoir.png?itok=z4ObIabh": "Canal+",
    "https://www.lnr.fr/sites/default/files/styles/mini_diffuseur/public/canaldec3_0.jpg?itok=tsh16SpK": "Canal+ Décalé / Rugby+",
    "https://www.lnr.fr/sites/default/files/styles/mini_diffuseur/public/canalplus_rugbyplus2.jpg?itok=ObeaPhg8": "Canal+ / Rugby+",
    "https://www.lnr.fr/sites/default/files/styles/mini_diffuseur/public/C%2B-Sport-noir_1.png?itok=SqsEWk_P": "Canal+ Sport",
    "https://www.lnr.fr/sites/default/files/styles/mini_diffuseur/public/Rugby%2B-noir.png?itok=b_IN-g76": "Rugby+",
    "https://www.lnr.fr/sites/default/files/styles/mini_diffuseur/public/canal-decale_0.png?itok=7-Nckj3r": "Canal+ Décalé",
}

actualDiffusorName = {
    "Programme TV canal+sport": "Canal+ Sport",
    "Programme TV canal+": "Canal+",
    "Programme TV canal+decale": "Canal+ Décalé",
    "Canal+ Sport": "Canal+ Sport",
    "Canal+ Décalé" : "Canal+ Décalé",
    "Canal+": "Canal+",
    "Canal+sport": "Canal+ Sport",
    "Canal+decale": "Canal+ Décalé"
}

def getDate(tr):
    texts = tr.find("span", {"class": "format-full"}).text.strip()
    return dateparser.parse(texts)


def getHour(tr):
    texts = tr.find("td", {"class": "cell-score"}).text.strip()
    return dateparser.parse(texts)


def getTeams(tr):
    textTeamA = (
        tr.find("td", {"class": "cell-team-a"})
        .find("span", {"class": "format-full"})
        .text.strip()
    )
    textTeamB = (
        tr.find("td", {"class": "cell-team-b"})
        .find("span", {"class": "format-full"})
        .text.strip()
    )
    return textTeamA + " - " + textTeamB

def getDiffusor(tr):
    nextTr = tr.find_next_sibling("tr")
    try:
        img = nextTr.find("ul", {"class": "logo-chanels"}).find("img")
        return img["src"]
    except Exception:
        return ""
    
def getRugbyCompetition(urlPage):

    page = urllib.request.urlopen(urlPage)

    soup = BeautifulSoup(page, "html.parser")

    activeFilterDiv = soup.find_all("a", {"class": ["filter active"]})

    twoNextDays = []

    twoNextDays.append(activeFilterDiv[1].findNext("a"))
    twoNextDays.append(twoNextDays[0].findNext("a"))

    seasonUrl = "https://www.lnr.fr/" + str(activeFilterDiv[0]["href"]).replace(
        "&day=all", ""
    )

    daysUrl = []

    daysNumbers = []

    for filter in twoNextDays:
        if "&day=all" not in filter["href"]:
            daysNumbers.append(int(filter["href"][-5:]))

    for dayNb in daysNumbers:
        daysUrl.append(seasonUrl + "&day=" + str(dayNb))

    listMatch = []

    for day in daysUrl[:2]:
        page = urllib.request.urlopen(day)
        
        soup = BeautifulSoup(page, "html.parser")

        matchDay = soup.find_all("a", {"class": ["filter active"]})
        matchDay = matchDay[1].getText().strip()

        trs = soup.find_all("tr", {"class": ["info-line before", "table-hr"]})

        for tr in trs:
            date = getDate(tr)
            hour = getHour(tr)
            teams = getTeams(tr)
            diffusor = getDiffusor(tr)

            diffusorName = (
                elligibleDiffusorTop14Dict[diffusor]
                if diffusor in elligibleDiffusorTop14Dict
                else ""
            )
            
            match = {
                "date": date.strftime("%d/%m/%Y"),
                "hour": hour.strftime("%H:%M"),
                "teams": teams,
                "diffusor": diffusor,
                "diffusorName": diffusorName,
                "urlPage": urlPage,
                "journee": matchDay,
            }
            listMatch.append(match)
    return listMatch

def getAgendaTvDate(match):
    isDateFound = False
    previousDiv = match.find_previous_sibling("div")
    while isDateFound is not True:
        if previousDiv.find("div", {"class": "matchsDate"}):
            isDateFound = True
            foundDate = previousDiv.find("div", {"class": "matchsDate"}).text.strip()
            return dateparser.parse(foundDate).strftime("%d/%m/%Y")
        else:
            previousDiv = previousDiv.find_previous_sibling("div")


def getLigue1Date(match):
    previousDiv = match.find_parent("li")

    matchDay = previousDiv.find_all("span")

    foundDate = matchDay[0].text.strip().replace("Aujourd'hui - ", "")
    return dateparser.parse(foundDate).strftime("%d/%m/%Y")


def formatDiffusorName(tempDiffusorName):
    try :
        return actualDiffusorName[tempDiffusorName]
    except KeyError:
        if "Canal" in tempDiffusorName:
            return "Canal But UNK"
        else : 
            return "Except"

def getFootballCompetition(urlpage):

    page = urllib.request.urlopen(urlpage)

    soup = BeautifulSoup(page, "html.parser")

    divs = soup.find_all("div", {"class": "ListingMatchs_Match"})

    listMatch = []

    for div in divs:
        texts = div.find_all("div", {"class": "ListingMatchs_Equipe"})
        infosMatch = div.find_all("div", {"class": "ListingMatchs_InfosMatch"})
        horaire = infosMatch[0].find_all("div", {"class": "mb-1"})
        imgList = []
        for img in div.find_all("img", alt=True):

            if "icones_tv" in img["src"]:
                imgList.append(img)

        dateMatch = getAgendaTvDate(div)

        match = {
            "date": dateMatch,
            "hour": horaire[0].text.strip(),
            "teams": texts[0].text.strip() + " - " + texts[1].text.strip(),
            "diffusor": imgList[-1]["src"],
            "diffusorName": formatDiffusorName(imgList[-1]["alt"]),
            "urlPage": "https://www.agendatv-foot.com"
            + infosMatch[0].find_all("a", href=True)[0]["href"],
            "journee": "",
        }
        if match["diffusorName"] != "Except":
            listMatch.append(match)

    return listMatch

def getAutoMoto():

    urlpage = "https://www.agendatv-auto-moto.com/"

    page = urllib.request.urlopen(urlpage)

    soup = BeautifulSoup(page, "html.parser")

    divs = soup.find_all("div", {"class": "ListingMatchs_Match"})

    listMatch = []
    
    for div in divs:
        texts = div.find_all("div", {"class": "ListingMatchs_Equipe"})
        infosMatch = div.find_all("div", {"class": "ListingMatchs_InfosMatch"})
        texts = infosMatch[0].find_all("div")
        isRace = False
        for textDivs in texts:
            if "Course" in textDivs.text.strip():
                isRace = True
            
        if isRace:
            horaire = infosMatch[0].find_all("div", {"class": "mb-1"})
            dateMatch = getAgendaTvDate(div)
            imgListProg = []
            imgsDiv = div.find_all("div", {"class": "col-3 col-lg-2"})
            for imgDiv in imgsDiv:
                for img in imgDiv.find_all("img", alt=True):
                    imgListProg.append(img["src"])

            imgCompetition = imgListProg[0]
            sportType = ""
            if "competition_moto_gp_11112020171919.png" in imgCompetition:
                sportType = "Moto GP"
            elif "competitions_formule_1_06112020150905.jpg" in imgCompetition:
                sportType = "Formule 1"

            imgList = []
            for img in div.find_all("img", alt=True):
                if "icones_tv" in img["src"]:
                    imgList.append(img)
            if len(imgList) > 0 and sportType != "":
                match = {
                    "date": dateMatch,
                    "hour": horaire[0].text.strip().replace("\t", "").replace("(Direct)", "").replace("\n", ""),
                    "teams": "A COMPLETER",
                    "diffusor": imgList[-1]["src"],
                    "diffusorName": formatDiffusorName(imgList[-1]["alt"]) ,
                    "urlPage": "https://www.agendatv-auto-moto.com"
                    + infosMatch[0].find_all("a", href=True)[0]["href"],
                    "journee": texts[1].text.strip(),
                    "type": sportType
                }
                listMatch.append(match)

    return listMatch

@app.get("/")
async def root():
    return "Hello world"

@app.get("/automoto")
async def root():
    automoto = getAutoMoto()
    return {"AutoMoto": automoto}

@app.get("/rugby")
async def root():
    top14 = getRugbyCompetition("https://www.lnr.fr/rugby-top-14/calendrier-resultats-rugby-top-14")
    prod2 = getRugbyCompetition("https://www.lnr.fr/rugby-pro-d2/calendrier-resultats-rugby-pro-d2")
    return {"Top14": top14, "ProD2": prod2}


@app.get("/football")
async def root():
    ligue1 = getFootballCompetition("https://www.agendatv-foot.com/match-programme-tv-ligue+1")
    premiereLeague = getFootballCompetition("https://www.agendatv-foot.com/match-programme-tv-english+premier+league")
    europaLeague = getFootballCompetition("https://www.agendatv-foot.com/match-programme-tv-europa+league")
    championsLeague = getFootballCompetition("https://www.agendatv-foot.com/match-programme-tv-champions+league")
    return {"Ligue 1": ligue1, "EPL": premiereLeague, "EuropaLeague": europaLeague, "ChampionsLeague": championsLeague}
