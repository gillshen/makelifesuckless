import dataclasses
import re


def _compile(keyword):
    return re.compile(rf"^\s*{keyword}\s*:(.*)$", flags=re.IGNORECASE)


NAME = _compile("name")
EMAIL = _compile("email")
PHONE = _compile("phone")
ADDRESS = _compile("address")
WEBSITE = _compile("website")

START_DATE = _compile(r"start\s+date")
END_DATE = _compile(r"end\s+date")

SCHOOL = _compile("school")
DEGREE = _compile("degree")
MAJOR = _compile("major")
MINOR = _compile("minor")
GPA = _compile("gpa")
COURSES = _compile("courses")

ROLE = _compile("role")
ORG = _compile("org")
HOURS = _compile(r"hours\s+per\s+week")
WEEKS = _compile(r"weeks\s+per\s+year")
DESCRIPTION = re.compile(r"^\s*-\s*(.+)$")
SECTION = re.compile(r"^\s*#\s*(.+)$")

AWARD = _compile("award")
AWARD_DATE = _compile(r"award\s+date")

SKILLSET_NAME = _compile(r"skillset\s+name")
SKILLS = _compile("skills")


@dataclasses.dataclass
class Education:
    school: str
    start_date: str = ""
    end_date: str = ""
    degree: str = ""
    major: str = ""
    minor: str = ""
    gpa: str = ""
    courses: str = ""


@dataclasses.dataclass
class Activity:
    role: str
    org: str = ""
    start_date: str = ""
    end_date: str = ""
    hours_per_week: str = ""
    weeks_per_year: str = ""
    descriptions: list[str] = dataclasses.field(default_factory=list)
    section: str = ""


@dataclasses.dataclass
class Award:
    name: str
    date: str = ""


@dataclasses.dataclass
class SkillSet:
    name: str
    skills: str = ""


@dataclasses.dataclass
class CV:
    name: str = ""
    email: str = ""
    address: str = ""
    phone: str = ""
    website: str = ""
    education: list[Education] = dataclasses.field(default_factory=list)
    activity_sections: list[str] = dataclasses.field(default_factory=list)
    activities: list[Activity] = dataclasses.field(default_factory=list)
    awards: list[Award] = dataclasses.field(default_factory=list)
    skillsets: list[SkillSet] = dataclasses.field(default_factory=list)

    def activities_of_section(self, section: str = ""):
        return [a for a in self.activities if a.section == section]


def parse(src: str) -> CV:
    cv = CV()
    curren_data_object = None
    current_section = ""

    for line in src.splitlines():
        if not line.strip():
            continue

        if name := _match(NAME, line):
            cv.name = name
        elif email := _match(EMAIL, line):
            cv.email = email
        elif phone := _match(PHONE, line):
            cv.phone = phone
        elif address := _match(ADDRESS, line):
            cv.address = address
        elif website := _match(WEBSITE, line):
            cv.website = website

        elif new_section := _match(SECTION, line):
            current_section = new_section
            cv.activity_sections.append(current_section)
        elif school := _match(SCHOOL, line):
            curren_data_object = Education(school=school)
            cv.education.append(curren_data_object)
        elif role := _match(ROLE, line):
            curren_data_object = Activity(role=role, section=current_section)
            cv.activities.append(curren_data_object)
        elif skillset_name := _match(SKILLSET_NAME, line):
            curren_data_object = SkillSet(name=skillset_name)
            cv.skillsets.append(curren_data_object)
        elif award_name := _match(AWARD, line):
            curren_data_object = Award(name=award_name)
            cv.awards.append(curren_data_object)

        elif start_date := _match(START_DATE, line):
            curren_data_object.start_date = start_date
        elif end_date := _match(END_DATE, line):
            curren_data_object.end_date = end_date

        elif degree := _match(DEGREE, line):
            curren_data_object.degree = degree
        elif major := _match(MAJOR, line):
            curren_data_object.major = major
        elif minor := _match(MINOR, line):
            curren_data_object.minor = minor
        elif gpa := _match(GPA, line):
            curren_data_object.gpa = gpa
        elif courses := _match(COURSES, line):
            curren_data_object.courses = courses

        elif org := _match(ORG, line):
            curren_data_object.org = org
        elif hours := _match(HOURS, line):
            curren_data_object.hours_per_week = hours
        elif weeks := _match(WEEKS, line):
            curren_data_object.weeks_per_year = weeks
        elif description := _match(DESCRIPTION, line):
            curren_data_object.descriptions.append(description)

        elif award_date := _match(AWARD_DATE, line):
            curren_data_object.date = award_date
        elif skills := _match(SKILLS, line):
            curren_data_object.skills = skills

        else:
            print(f"unparseable line: {line!r}")

    return cv


def _match(compiled_pattern: re.Pattern, text: str):
    if mo := compiled_pattern.match(text):
        return mo.group(1).strip()
