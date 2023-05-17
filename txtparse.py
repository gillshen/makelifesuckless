import dataclasses
import datetime
import re
import json


class ParsingError(ValueError):
    pass


class DateError(ParsingError):
    pass


def _compile(keyword):
    return re.compile(rf"^\s*{keyword}\s*[:：](.*)$", flags=re.IGNORECASE)


NAME = _compile("name")
EMAIL = _compile("email")
PHONE = _compile("phone")
ADDRESS = _compile("address")
WEBSITE = _compile("website")

SECTION = re.compile(r"^\s*#\s*(.+)$")
LOC = _compile("loc")
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
DESCRIPTION = re.compile(r"^\s*[-•]\s*(.+)$")

AWARD = _compile("award")

TEST = _compile("test")
SCORE = _compile("score")

X_DATE = _compile(r"(?:award|test)\s+date")

SKILLSET_NAME = _compile(r"skillset\s+name")
SKILLS = _compile("skills")


# Model files
MODEL_EDUCATION = """
School: 
Loc: 
Start Date: yyyy-mm
End Date: yyyy-mm
Degree: 
Major: 
Minor: 
GPA: 
Courses: 
"""

MODEL_ACTIVITY = """
Role: 
Org: 
Loc: 
Start Date: yyyy-mm
End Date: yyyy-mm
Hours per Week: 
Weeks per Year: 
- [description]
- [description]
"""

MODEL_TEST = """
Test: 
Score: 
Test Date: 
"""

MODEL_AWARD = """
Award: 
Award Date: yyyy-mm
"""

MODEL_SKILLSET = """
Skillset Name: 
Skills: 
"""

MODEL_CV = re.sub(
    "\n{3,}",
    "\n\n",
    f"""\
Name: 
Email: 
Phone: 
Address: 
Website: 

{MODEL_EDUCATION}

{MODEL_TEST}

{MODEL_AWARD}

{MODEL_SKILLSET}

# Research Experience [change as appropriate]

{MODEL_ACTIVITY}

# Work Experience [change as appropriate]

{MODEL_ACTIVITY}
""",
)


@dataclasses.dataclass
class SmartDate:
    year: int = None
    month: int = None
    day: int = None
    fallback: str = ""

    def __bool__(self):
        return bool(
            self.year is not None
            or self.month is not None
            or self.day is not None
            or self.fallback
        )

    @classmethod
    def from_str(cls, s: str):
        mo = re.match(r"^(\d{4})(?:([-./])([01]?[0-9]))?(?:\2([0-3]?[0-9]))?$", s)
        if mo is None:
            return cls(fallback=s)

        year, _, month, day = mo.groups()
        year = int(year)
        if month is None:
            return cls(year=year)

        month = int(month)
        if month not in set(range(1, 13)):
            raise DateError("month out of range")
        if day is None:
            return cls(year=year, month=month)

        day = int(day)
        try:
            datetime.date(year=year, month=month, day=day)
        except ValueError:
            raise DateError("day out of range")
        else:
            return cls(year=year, month=month, day=day)

    def to_str(self, *, style: str = "american", mask: "SmartDate" = None):
        mask_date = mask or SmartDate()

        if self.year is None and self.fallback != mask_date.fallback:
            return self.fallback
        elif self.year is None:
            return ""

        if self.month is None and self.year != mask_date.year:
            return str(self.year)
        elif self.month is None:
            return ""

        # NOTE: the hash sign, as in '%#d', is windows specific;
        # on Mac/Linux would need to use '-' instead (thus '%-d')
        if style == "american":
            if self.year != mask_date.year:
                format_str = "%b %#d, %Y" if self.day else "%b %Y"
            elif self.month != mask_date.month:
                format_str = "%b %#d" if self.day else "%b"
            else:
                format_str = "%#d" if self.day and self.day != mask_date.day else ""

        elif style == "american long":
            if self.year != mask_date.year:
                format_str = "%B %#d, %Y" if self.day else "%B %Y"
            elif self.month != mask_date.month:
                format_str = "%B %#d" if self.day else "%B"
            else:
                format_str = "%#d" if self.day and self.day != mask_date.day else ""

        elif style == "american slash":
            format_str = "%m/%d/%Y" if self.day else "%m/%Y"

        elif style == "british":
            if self.year != mask_date.year:
                format_str = "%#d %b %Y" if self.day else "%b %Y"
            elif self.month != mask_date.month:
                format_str = "%#d %b" if self.day else "%b"
            else:
                format_str = "%#d" if self.day and self.day != mask_date.day else ""

        elif style == "british long":
            if self.year != mask_date.year:
                format_str = "%#d %B %Y" if self.day else "%B %Y"
            elif self.month != mask_date.month:
                format_str = "%#d %B" if self.day else "%B"
            else:
                format_str = "%#d" if self.day and self.day != mask_date.day else ""

        elif style == "british slash":
            format_str = "%d/%m/%Y" if self.day else "%m/%Y"

        elif style == "iso":
            format_str = "%Y-%m-%d" if self.day else "%Y-%m"
        elif style == "yyyy/mm/dd":
            format_str = "%Y/%m/%d" if self.day else "%Y/%m"
        else:
            raise ValueError(f"unrecognized style: {style}")

        d = datetime.date(year=self.year, month=self.month, day=self.day or 1)
        return d.strftime(format_str)


@dataclasses.dataclass
class Education:
    school: str
    loc: str = ""
    start_date: SmartDate = SmartDate()
    end_date: SmartDate = SmartDate()
    degree: str = ""
    major: str = ""
    minor: str = ""
    gpa: str = ""
    courses: str = ""


@dataclasses.dataclass
class Activity:
    role: str
    org: str = ""
    loc: str = ""
    start_date: SmartDate = SmartDate()
    end_date: SmartDate = SmartDate()
    hours_per_week: str = ""
    weeks_per_year: str = ""
    descriptions: list[str] = dataclasses.field(default_factory=list)
    section: str = ""


@dataclasses.dataclass
class Award:
    name: str
    date: SmartDate = SmartDate()


@dataclasses.dataclass
class Test:
    name: str
    score: str = ""
    date: SmartDate = SmartDate()


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
    tests: list[Test] = dataclasses.field(default_factory=list)
    skillsets: list[SkillSet] = dataclasses.field(default_factory=list)

    def activities_of_section(self, section: str = ""):
        return [a for a in self.activities if a.section == section]

    def to_json(self, indent=4):
        return json.dumps(dataclasses.asdict(self), indent=indent)


def parse(src: str) -> tuple[CV, list[str]]:
    cv = CV()
    unparsed = []
    curren_data_object = None
    current_section = ""

    for line in map(_preprocess, src.splitlines()):
        if not line:
            continue

        try:
            if (name := _match(NAME, line)) is not None:
                cv.name = name
            elif (email := _match(EMAIL, line)) is not None:
                cv.email = email
            elif (phone := _match(PHONE, line)) is not None:
                cv.phone = phone
            elif (address := _match(ADDRESS, line)) is not None:
                cv.address = address
            elif (website := _match(WEBSITE, line)) is not None:
                cv.website = website

            elif (new_section := _match(SECTION, line)) is not None:
                current_section = new_section
                cv.activity_sections.append(current_section)
            elif (school := _match(SCHOOL, line)) is not None:
                curren_data_object = Education(school=school)
                cv.education.append(curren_data_object)
            elif (role := _match(ROLE, line)) is not None:
                curren_data_object = Activity(role=role, section=current_section)
                cv.activities.append(curren_data_object)
            elif (skillset_name := _match(SKILLSET_NAME, line)) is not None:
                curren_data_object = SkillSet(name=skillset_name)
                cv.skillsets.append(curren_data_object)
            elif (award_name := _match(AWARD, line)) is not None:
                curren_data_object = Award(name=award_name)
                cv.awards.append(curren_data_object)
            elif (test_name := _match(TEST, line)) is not None:
                curren_data_object = Test(name=test_name)
                cv.tests.append(curren_data_object)

            elif (loc := _match(LOC, line)) is not None:
                curren_data_object.loc = loc
            elif (start_date := _match(START_DATE, line)) is not None:
                curren_data_object.start_date = SmartDate.from_str(start_date)
            elif (end_date := _match(END_DATE, line)) is not None:
                curren_data_object.end_date = SmartDate.from_str(end_date)
            elif (x_date := _match(X_DATE, line)) is not None:
                curren_data_object.date = SmartDate.from_str(x_date)

            elif (degree := _match(DEGREE, line)) is not None:
                curren_data_object.degree = degree
            elif (major := _match(MAJOR, line)) is not None:
                curren_data_object.major = major
            elif (minor := _match(MINOR, line)) is not None:
                curren_data_object.minor = minor
            elif (gpa := _match(GPA, line)) is not None:
                curren_data_object.gpa = gpa
            elif (courses := _match(COURSES, line)) is not None:
                curren_data_object.courses = courses

            elif (org := _match(ORG, line)) is not None:
                curren_data_object.org = org
            elif (hours := _match(HOURS, line)) is not None:
                curren_data_object.hours_per_week = hours
            elif (weeks := _match(WEEKS, line)) is not None:
                curren_data_object.weeks_per_year = weeks
            elif (description := _match(DESCRIPTION, line)) is not None:
                curren_data_object.descriptions.append(description)

            elif (score := _match(SCORE, line)) is not None:
                curren_data_object.score = score
            elif (skills := _match(SKILLS, line)) is not None:
                curren_data_object.skills = skills

            else:
                unparsed.append(line)

        except DateError:
            raise DateError(f"Wrong date in line: {line!r}")
        except Exception as e:
            raise ParsingError(f"Unparsable line: {line!r}\n{e}")

    return cv, unparsed


def _preprocess(line: str):
    # preserve the leading `#` if any and escape other `#`s
    line = re.sub(r"^\s*#", "\uffff", line)
    line = line.replace("#", "\\#").replace("\uffff", "#")

    # protect % sign (latex comments not allowed as a result)
    # escape special characters `_`, `$`, and `&`
    line = re.sub("([_$%&])", r"\\\1", line)

    # preserve `^` and escaped `*`
    line = line.replace("^", "\\^{}")
    line = line.replace("\\*", '{\\char"002A}')

    # remove excessive whitespace
    line = re.sub(r"\s+", " ", line).strip()

    # correct quotes
    line = re.sub(r'(^|\s)"', r"\1``", line)
    line = re.sub(r"(^|\s)'", r"\1`", line)

    # bold and italic
    while line.count("*") > 1:
        line = re.sub(r"\*\*((?:[^*]|\*[^*])*?)\*\*", r"\\textbf{\1}", line)
        line = re.sub(r"\*([^*]*?)\*", r"\\emph{\1}", line)

    # url
    line = re.sub(r"\[(.+?)\]\((.+?)\)", r"\\href{\2}{\1}", line)

    return line


def _match(compiled_pattern: re.Pattern, text: str):
    if mo := compiled_pattern.match(text):
        return mo.group(1).strip()
