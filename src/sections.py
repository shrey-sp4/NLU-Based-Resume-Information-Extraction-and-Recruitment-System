import re


HEADERS={

"education":[
"education",
"academic",
"qualification",
"degree"
],

"experience":[
"experience",
"employment",
"research experience",
"work"
],

"skills":[
"skills",
"technical skills"
],

"publications":[
"publication",
"research paper",
"journal",
"conference"
],

"achievements":[
"award",
"achievement",
"honor"
]

}


def detect_sections(text):

    sections={}

    current="other"

    sections[current]=[]

    lines=text.split("\n")

    for line in lines:

        s=line.strip()

        if not s:

            continue

        low=s.lower()

        matched=False

        for sec,vals in HEADERS.items():

            if any(
                w in low
                for w in vals
            ):

                current=sec

                sections.setdefault(
                    current,
                    []
                )

                matched=True

                break

        if not matched:

            sections[current].append(
                s
            )

    return {

        k:"\n".join(v)

        for k,v in sections.items()
    }