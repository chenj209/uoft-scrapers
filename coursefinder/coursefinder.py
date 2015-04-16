import requests, http.cookiejar
from bs4 import BeautifulSoup
from collections import OrderedDict
import time
import re
import json
import os

class Coursefinder:
    """A wrapper for utilizing UofT's Course Finder web service.

    Course Finder is located at http://coursefinder.utoronto.ca/.
    """

    def __init__(self):
        self.host = 'http://coursefinder.utoronto.ca/course-search/search'
        self.urls = None
        self.cookies = http.cookiejar.CookieJar()
        self.s = requests.Session()

    def update_files(self):
        """Update the local JSON files for this scraper."""

        urls = self.search()
        for x in urls:
            course_id = re.search('offImg(.*)', x[0]).group(1)[:14]
            course_code = course_id[:8]
            print('Current Course: %s' % course_id)
            url = '%s/courseSearch/coursedetails/%s' % (self.host, course_id)
            html = self.get_course_html(url)
            with open('html/%s.html' % course_id, 'w+') as outfile:
                outfile.write(html.decode('utf-8'))
            data = self.parse_course_html(course_id, html)
            if data:
                with open('json/%s.json' % course_id, 'w+') as outfile:
                    json.dump(data[0], outfile)
                with open('../calendar/json/%s.json' % course_code, 'w+') as outfile:
                    json.dump(data[1], outfile)

    '''
    def mongo(self):
        for root, dirs, filenames in os.walk('./json'):
            for f in filenames[1:]:
                with open('./json/' + f) as fi:
                    doc = json.loads(fi.read(), object_pairs_hook=OrderedDict)
                    self.push_to_mongo(doc)
                    print(doc['code'])
    '''

    '''
    def run_update(self):
        """Does everything."""

        urls = self.search()
        for x in urls:
            course_id = re.search('offImg(.*)', x[0]).group(1)[:14]
            exists = self.courses.find_one({"course_id": course_id})
            if exists is not None:
                self.count += 1
                percent = str(round((self.count / self.total) * 100, 2))
                print('Skipping Course: %s \t Progress: %s%s' % (course_id, percent, "%"))
                continue
            url = '%s/courseSearch/coursedetails/%s' % (self.host, course_id)
            html = self.get_course_html(url)
            data = self.parse_course_html(course_id, html)
            with open('json/%s.json' % course_id, 'w+') as outfile:
                json.dump(data, outfile)
            self.push_to_mongo(data)

            self.count += 1
            percent = str(round((self.count / self.total) * 100, 2))
            print('Current Course: %s \t Progress: %s%s' % (course_id, percent, "%"))
    '''

    def search(self, query='', requirements=''):
        """Perform a search and return the data as a dict."""

        url = '%s/courseSearch/course/search' % self.host

        data = {
            'queryText': query,
            'requirements': requirements,
            'campusParam': 'St. George,Scarborough,Mississauga'
        }

        # Keep trying to get data until a proper response is given
        json = None
        while json is None:
            try:
                r = self.s.get(url, params=data, cookies=self.cookies)
                if r.status_code == 200:
                    json = r.json()
                else:
                    time.sleep(0.5)
            except requests.exceptions.Timeout:
                continue

        self.total = len(json['aaData'])

        return json['aaData']

    def get_course_html(self, url):
        """Update the locally stored course pages."""

        html = None
        while html is None:
            try:
                r = self.s.get(url, cookies=self.cookies)
                if r.status_code == 200:
                    html = r.text
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                continue

        return html.encode('utf-8')

    def parse_course_html(self, course_id, html):
        """Create JSON files from the HTML pages downloaded."""

        if "The course you are trying to access does not exist" in html.decode('utf-8'):
            return False

        soup = BeautifulSoup(html)

        # Things that appear on all courses

        title = soup.find(id = "u19")
        title_name = title.find_all("span", class_="uif-headerText-span")[0].get_text()

        course_code = course_id[:-5]

        course_name = title_name[10:]

        division = soup.find(id = "u23").find_all("span", id="u23")[0].get_text().strip()

        description = soup.find(id = "u32").find_all("span", id="u32")[0].get_text().strip()

        department = soup.find(id = "u41").find_all("span", id="u41")[0].get_text().strip()

        course_level = soup.find(id = "u86").find_all("span", id="u86")[0].get_text().strip()
        course_level = course_level[:3]
        course_level = int(course_level)

        campus = soup.find(id = "u149").find_all("span", id="u149")[0].get_text().strip()

        if campus == "St. George":
            campus = "UTSG"
        elif campus == "Mississauga":
            campus = "UTM"
        elif campus == "Scarborough":
            campus = "UTSC"

        term = soup.find(id = "u158").find_all("span", id="u158")[0].get_text().strip()

        # Things that don't appear on all courses

        as_breadth = soup.find(id= "u122")
        breadths = []
        if not as_breadth is None:
            as_breadth = as_breadth.find_all("span", id="u122")[0].get_text().strip()
            for ch in as_breadth:
                if ch in "12345":
                    breadths.append(int(ch))

        breadths = sorted(breadths)

        exclusions = soup.find(id= "u68")
        if not exclusions is None:
            exclusions = exclusions.find_all("span", id="u68")[0].get_text().strip()
        else:
            exclusions = ""

        prereq = soup.find(id= "u50")
        if not prereq is None:
            prereq = prereq.find_all("span", id="u50")[0].get_text().strip()
        else:
            prereq = ""

        #Meeting Sections

        meeting_table = soup.find(id = "u172")

        trs = []
        if not meeting_table is None:
            trs = meeting_table.find_all("tr")

        sections = []

        for tr in trs:
            tds = tr.find_all("td")
            if len(tds) > 0:
                code = tds[0].get_text().strip()

                raw_times = tds[1].get_text().replace(
                    'Alternate week', '').strip().split(" ")
                times = []
                for i in range(0, len(raw_times) - 1, 2):
                    times.append(raw_times[i] + " " + raw_times[i + 1])

                instructors = BeautifulSoup(str(tds[2]).replace("<br>", "\n"))
                instructors = instructors.get_text().split("\n")
                instructors = list(filter(None, [x.strip() for x in instructors]))

                raw_locations = tds[3].get_text().strip().split(" ")
                locations = []
                for i in range(0, len(raw_locations) - 1, 2):
                    locations.append(
                        raw_locations[i] + " " + raw_locations[i + 1])

                class_size = tds[4].get_text().strip()

                time_data = []
                for i in range(len(times)):
                    info = times[i].split(" ")
                    day = info[0]
                    hours = info[1].split("-")

                    location = ""
                    try:
                        location = locations[i]
                    except IndexError:
                        location = ""


                    for i in range(len(hours)):
                        x = hours[i].split(':')
                        hours[i] = int(x[0]) + (int(x[1])/60)

                    time_data.append(OrderedDict([
                        ("day", day),
                        ("start", hours[0]),
                        ("end", hours[1]),
                        ("duration", hours[1] - hours[0]),
                        ("location", location)
                    ]))

                code = code.split(" ")
                code = code[0][0] + code[1]

                data = OrderedDict([
                    ("code", code),
                    ("instructors", instructors),
                    ("times", time_data),
                    ("size", int(class_size)),
                    ("enrolment", 0)
                ])

                sections.append(data)

        # Dictionary creation
        course = OrderedDict([
            ("id", course_id),
            ("code", course_code),
            ("name", course_name),
            ("description", description),
            ("division", division),
            ("department", department),
            ("prerequisites", prereq),
            ("exclusions", exclusions),
            ("level", course_level),
            ("campus", campus),
            ("term", term),
            ("breadths", breadths),
            ("meeting_sections", sections)
        ])

        basic_course = OrderedDict([
            ("code", course_code),
            ("name", course_name),
            ("description", description),
            ("division", division),
            ("department", department),
            ("prerequisites", prereq),
            ("exclusions", exclusions),
            ("level", course_level),
            ("campus", campus),
            ("breadths", breadths)
        ])

        return [course, basic_course]

    def push_to_mongo(self, doc):
        """Push all the data to the MongoDB server."""
        self.courses['2014'].insert(doc)
