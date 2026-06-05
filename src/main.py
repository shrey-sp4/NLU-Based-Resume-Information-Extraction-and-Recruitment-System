import os
import json

from extract import *
from clean import *
from sections import *
from entities import *


INPUT="data/resumes"

os.makedirs(
    "output",
    exist_ok=True
)

results=[]


for f in os.listdir(INPUT):

    if not f.endswith(".pdf"):

        continue

    path=os.path.join(
        INPUT,
        f
    )

    print(
        "processing",
        f
    )

    raw=extract_text(path)

    text=clean_text(raw)

    sec=detect_sections(text)

    record={

        "file":f,

        "name":
        get_name(text),

        "email":
        get_email(text),

        "phone":
        get_phone(text),

        "education":
        education(
            sec.get(
                "education",
                text
            )
        ),

        "experience":
        sec.get(
            "experience",
            ""
        ),

        "research_publications":
        publications(
            sec.get(
                "publications",
                text
            )
        ),

        "skills":
        skills(text),

        "achievements":
        sec.get(
            "achievements",
            ""
        )

    }

    results.append(
        record
    )


with open(

    "output/resumes.json",

    "w",

    encoding="utf8"

) as f:

    json.dump(
        results,
        f,
        indent=2,
        ensure_ascii=False
    )

print("done")