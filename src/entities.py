import re
import spacy
import phonenumbers


nlp=spacy.load(
    "en_core_web_lg"
)


SKILLS=[

"python",
"java",
"machine learning",
"deep learning",
"nlp",
"tensorflow",
"pytorch",
"sql",
"postgresql",
"docker",
"aws",
"opencv",
"react"

]


def get_name(text):

    lines=[

        l.strip()

        for l in text.split("\n")

        if l.strip()

    ]

    ignore=[

        "curriculum vitae",
        "resume",
        "email",
        "phone",
        "research scholar"

    ]

    top="\n".join(
        lines[:12]
    )

    doc=nlp(top)

    for ent in doc.ents:

        if ent.label_=="PERSON":

            if len(
                ent.text.split()
            )<=4:

                return ent.text

    for l in lines[:10]:

        low=l.lower()

        if any(
            x in low
            for x in ignore
        ):
            continue

        if 2<=len(
            l.split()
        )<=5:

            return l

    return ""


def get_email(text):

    m=re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    return m.group() if m else ""


def get_phone(text):

    try:

        nums=[]

        for n in phonenumbers.PhoneNumberMatcher(
            text,
            "IN"
        ):

            nums.append(
                n.raw_string
            )

        return nums[0]

    except:

        return ""


def education(text):

    pattern=r"(Ph\.?D.*|M\.?Tech.*|M\.?Sc.*|MBA.*|B\.?Tech.*|B\.?Sc.*|Bachelor.*|Master.*)"

    return list(

        set(

            re.findall(
                pattern,
                text,
                re.I
            )

        )

    )


def publications(text):

    pubs=[]

    lines=text.split("\n")

    for l in lines:

        if (

            len(l)>20

            and

            (
                re.search(
                    r"\d{4}",
                    l
                )

                or

                "doi" in l.lower()

            )

        ):

            pubs.append(
                l.strip()
            )

    return pubs[:20]


def skills(text):

    low=text.lower()

    return [

        s

        for s in SKILLS

        if s in low

    ]