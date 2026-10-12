import os, re, json, sys
import requests
from bs4 import BeautifulSoup

BASE = "https://lms.kluniversity.in"
COURSE_ID = os.environ.get("COURSE_ID", "14533")
USER, PWD = os.environ["LMS_USER"], os.environ["LMS_PASS"]
TG_TOKEN, TG_CHAT = os.environ["TG_TOKEN"], os.environ["TG_CHAT"]
STATE = "state.json"
OPEN_WORDS = re.compile(r"(attempt quiz|re-attempt quiz|continue your attempt)", re.I)

def tg(msg):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                  data={"chat_id": TG_CHAT, "text": msg}, timeout=20)

def login():
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (quiz-watch personal script)"
    r = s.get(f"{BASE}/login/index.php", timeout=30)
    form = BeautifulSoup(r.text, "html.parser")
    tok = form.find("input", {"name": "logintoken"})
    data = {"username": USER, "password": PWD}
    if tok: data["logintoken"] = tok["value"]
    r = s.post(f"{BASE}/login/index.php", data=data, timeout=30)
    if "login/index.php" in r.url or "loginerrormessage" in r.text:
        tg("KLU quiz-watch: LOGIN FAILED. Check username/password secrets.")
        sys.exit(1)
    return s

def quiz_status(s, url):
    soup = BeautifulSoup(s.get(url, timeout=30).text, "html.parser")
    title = (soup.find("h1") or soup.find("title")).get_text(" ", strip=True)
    buttons = " ".join(b.get_text(" ", strip=True) for b in soup.select("button, input[type=submit], a.btn"))
    is_open = bool(OPEN_WORDS.search(buttons))
    return title, is_open

def main():
    s = login()
    course = BeautifulSoup(s.get(f"{BASE}/course/view.php?id={COURSE_ID}", timeout=30).text, "html.parser")
    quizzes = {}
    for a in course.select('a[href*="/mod/quiz/view.php"]'):
        quizzes[a["href"].split("&")[0]] = a.get_text(" ", strip=True)
    old = json.load(open(STATE)) if os.path.exists(STATE) else None
    new = {}
    for url in quizzes:
        title, is_open = quiz_status(s, url)
        new[url] = is_open
        was_open = (old or {}).get(url, False)
        if old is not None and is_open and not was_open:
            tg(f"QUIZ OPEN: {title}\n{url}")
        print(title, "OPEN" if is_open else "closed")
    json.dump(new, open(STATE, "w"), indent=1)

main()
