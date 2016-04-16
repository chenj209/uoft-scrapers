import logging
import os
import sys

from .scrapers.buildings import Buildings
from .scrapers.calendar.utsg import UTSGCalendar
from .scrapers.coursefinder import CourseFinder
from .scrapers.exams.utm import UTMExams
from .scrapers.exams.utsc import UTSCExams
from .scrapers.exams.utsg import UTSGExams
from .scrapers.food import Food
from .scrapers.textbooks import Textbooks
from .scrapers.timetable.utm import UTMTimetable
from .scrapers.timetable.utsc import UTSCTimetable
from .scrapers.timetable.utsg import UTSGTimetable
from .scrapers.utmshuttle import UTMShuttle
from .scrapers.parking import Parking


class NullHandler(logging.Handler):
    def emit(self, record):
        pass

logging.getLogger("uoftscrapers").addHandler(NullHandler())
