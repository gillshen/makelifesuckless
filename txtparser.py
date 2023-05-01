import dataclasses
# import datetime
import re


def _compile(keyword):
    return re.compile(rf'^\s*{keyword}\s*:(.*)$', flags=re.IGNORECASE)


NAME = _compile('name')
EMAIL = _compile('email')
ADDRESS = _compile('address')
PHONE = _compile('phone')

START_DATE = _compile(r'start\s+date')
END_DATE = _compile(r'end\s+date')

SCHOOL = _compile('school')
DEGREE = _compile('degree')
GPA = _compile('gpa')
COURSES = _compile('courses')

ROLE = _compile('role')
ORG = _compile('org')
HOURS = _compile(r'hours\s+per\s+week')
WEEKS = _compile(r'weeks\s+per\s+year')

DESCRIPTION = re.compile(r'^\s*-\s*(.+)$')
SECTION = re.compile(r'^\s*#\s*(.+)$')


@dataclasses.dataclass
class Education:
    school: str
    start_date: str = ''
    end_date: str = ''
    degree: str = ''
    gpa: str = ''
    courses: str = ''


@dataclasses.dataclass
class Activity:
    role: str
    org: str = ''
    start_date: str = ''
    end_date: str = ''
    hours_per_week: str = ''
    weeks_per_year: str = ''
    descriptions: list[str] = dataclasses.field(default_factory=list)
    section: str = ''


@dataclasses.dataclass
class CV:
    name: str = ''
    email: str = ''
    address: str = ''
    phone: str = ''
    education: list[Education] = dataclasses.field(default_factory=list)
    activities: list[Activity] = dataclasses.field(default_factory=list)


def parse(src: str) -> CV:
    cv = CV()
    section = ''
    curren_data_object = None

    for line in src.splitlines():
        if not line.strip():
            continue

        if name := _match(NAME, line):
            cv.name = name
        elif email := _match(EMAIL, line):
            cv.email = email
        elif address := _match(ADDRESS, line):
            cv.address = address
        elif phone := _match(PHONE, line):
            cv.phone = phone

        elif new_section := _match(SECTION, line):
            section = new_section
        elif school := _match(SCHOOL, line):
            curren_data_object = Education(school=school)
            cv.education.append(curren_data_object)
        elif role := _match(ROLE, line):
            curren_data_object = Activity(role=role, section=section)
            cv.activities.append(curren_data_object)

        elif start_date := _match(START_DATE, line):
            curren_data_object.start_date = start_date
        elif end_date := _match(END_DATE, line):
            curren_data_object.end_date = end_date

        elif degree := _match(DEGREE, line):
            curren_data_object.degree = degree
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

        else:
            print(f'unparseable line: {line!r}')

    return cv


def _match(compiled_pattern: re.Pattern, text: str):
    if mo := compiled_pattern.match(text):
        return mo.group(1).strip()


def _test():
    with open('test.txt', encoding='utf-8') as f:
        cv = parse(f.read())

    print(f'{cv.name=}')
    print(f'{cv.email=}')
    print(f'{cv.address=}')
    print(f'{cv.phone=}')

    for education in cv.education:
        print(education)
    for activity in cv.activities:
        print(activity)


if __name__ == '__main__':
    _test()
