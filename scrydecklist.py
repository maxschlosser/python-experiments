import re
import requests
import json
import time
import os
import shutil
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet

os.makedirs("img", exist_ok=True)
os.makedirs("pdf", exist_ok=True)
api_url = "https://api.scryfall.com/cards"

with(open('decklist.mtgo', 'r')) as decklist:
    card_names = decklist.readlines()
    card_names = filter(lambda x: x != "", card_names)
    card_names = [re.sub('[1-9]+ ', '',  card.strip().replace("/", " ")) for card in card_names]
    print(card_names)

def get_card_info(cardjs):
    layout = cardjs['layout']
    oracle = []
    crop = ""
    if layout == 'split'  or layout == "flip":
        for face in cardjs["card_faces"]:
            oracle.append(face['oracle_text'])
        crop = cardjs["image_uris"]["border_crop"]
    elif layout == 'transform' or layout == 'modal_dfc':
        for face in cardjs["card_faces"]:
            oracle.append(face['oracle_text'])
        crop = cardjs["card_faces"][0]["image_uris"]["border_crop"]
    else:
        try:
            oracle.append(cardjs['oracle_text'])
            crop = cardjs["image_uris"]["border_crop"]
        except:
            print(cardjs['name'])
            exit
    name = re.sub("[^a-z1-9-]*", "", cardjs['name'].lower().replace(" ", "-")).replace("--","-")
    if crop == "":
        print(json.dumps(cardjs,indent=4))
        exit
    return([name, crop, oracle])

cards = []
for card in card_names:
    card_resp = requests.get(f"{api_url}/named?exact={card}")
    if card_resp.status_code == 200:
        cardjs = json.loads(card_resp.text)
        cards.append(get_card_info(cardjs))
    elif card_resp.status_code == 429:
        print(f"Got 429, backing off.")
        exit
    else:
        print(f"Error getting {card}.")
        print(card_resp)
    time.sleep(0.05)

for card in cards:
    filename = f"img/{card[0]}.jpg"
    try:
        with(open(filename, "xb")) as imagefile:
            img_resp = requests.get(card[1], stream=True)
            if(img_resp.status_code == 429):
                print("Got 429, backing off")
                exit
            elif(img_resp.status_code == 200):
                shutil.copyfileobj(img_resp.raw, imagefile)
            else:
                print(f"Error downloading image for {card[0]}.")
            time.sleep(0.05)
        del imagefile
    except FileExistsError:
        print(f"{filename} already exists.")

ss = getSampleStyleSheet()['BodyText']
ss.fontSize = 10
x_offset = 5
y_offset = 5
x_count = 2
y_count = 5
width, height = A4
cellwidth = (width-2*x_offset) / x_count
cellheight = (height-2*y_offset) / y_count
cells = [(cellwidth*j+x_offset, cellheight*i+y_offset)  for i in range(0,y_count+1) for j in range(0,x_count+1)]


pdf = canvas.Canvas("pdf/cards.pdf", pagesize=A4)


def refresh_cells():
    pdf.grid([cell[0] for cell in cells], [cell[1] for cell in cells])
    draw_cells = filter(lambda cell: cell[0]<(width-x_offset) and cell[1]<(height-y_offset), sorted(cells))
    return draw_cells

i = 0
draw_cells = refresh_cells()
for card in cards:
    text = " // <br/>".join(card[2])
    i = i+1 
    cell = next(draw_cells)
    imgw, imgh = pdf.drawImage(f"img/{card[0]}.jpg", cell[0]+x_offset, cell[1]+y_offset, height=cellheight-10, anchor='w',preserveAspectRatio=True)
    width_offset = (imgw*((cellheight-10)/imgh)+2*x_offset)
    p = Paragraph(text, ss)
    w, h = p.wrapOn(pdf, cellwidth-width_offset-5, cellheight-y_offset)
    while(h>cellheight-2*y_offset):
        ss.fontSize = ss.fontSize - 1
        p = Paragraph(p.getPlainText(), ss)
        _, h = p.wrapOn(pdf, cellwidth-width_offset-5, cellheight-y_offset)
    p.drawOn(pdf, cell[0]+width_offset, cell[1]+(cellheight-h)-y_offset)
    ss.fontSize = 10
    if i == x_count*y_count:
        pdf.showPage()
        draw_cells = refresh_cells()
        i = 0
pdf.save()