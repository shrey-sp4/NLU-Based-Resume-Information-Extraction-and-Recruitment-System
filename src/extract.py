import os
import fitz
import pdfplumber
import pytesseract
import cv2
import numpy as np

from PIL import Image


MIN_TEXT = 500


def extract_pymupdf(pdf):

    pages=[]

    try:

        doc=fitz.open(pdf)

        for page in doc:

            blocks=page.get_text("blocks")

            blocks=sorted(
                blocks,
                key=lambda x:(x[1],x[0])
            )

            txt=[]

            for b in blocks:

                if len(b)>=5:

                    t=b[4].strip()

                    if t:

                        txt.append(t)

            pages.append(
                "\n".join(txt)
            )

        doc.close()

    except Exception:
        pass

    return "\n\n".join(pages)


def extract_pdfplumber(pdf):

    pages=[]

    try:

        with pdfplumber.open(pdf) as p:

            for page in p.pages:

                txt=page.extract_text()

                if txt:

                    pages.append(txt)

    except:
        pass

    return "\n\n".join(pages)


def ocr_pdf(pdf):

    pages=[]

    try:

        doc=fitz.open(pdf)

        for page in doc:

            pix=page.get_pixmap(
                dpi=300
            )

            img=Image.frombytes(
                "RGB",
                [pix.width,pix.height],
                pix.samples
            )

            img=np.array(img)

            gray=cv2.cvtColor(
                img,
                cv2.COLOR_RGB2GRAY
            )

            gray=cv2.threshold(
                gray,
                0,
                255,
                cv2.THRESH_BINARY+
                cv2.THRESH_OTSU
            )[1]

            txt=pytesseract.image_to_string(
                gray,
                config="--oem 3 --psm 4"
            )

            pages.append(txt)

    except:
        pass

    return "\n\n".join(pages)


def save_text(path,text):

    os.makedirs(
        "output/text",
        exist_ok=True
    )

    out=os.path.join(
        "output/text",
        os.path.basename(
            path
        ).replace(
            ".pdf",
            ".txt"
        )
    )

    with open(
        out,
        "w",
        encoding="utf8"
    ) as f:

        f.write(text)


def extract_text(pdf):

    txt=extract_pymupdf(pdf)

    if len(txt)<MIN_TEXT:

        txt=extract_pdfplumber(pdf)

    if len(txt)<MIN_TEXT:

        txt=ocr_pdf(pdf)

    save_text(
        pdf,
        txt
    )

    return txt