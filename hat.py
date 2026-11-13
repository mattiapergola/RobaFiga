import re
import os
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 15

def clean_href(href):
    if not href:
        return href
    # rimuove TUTTI i backslash, poi spazi
    return href.replace("\\", "").strip()


def extract_channel_links(main_url):
    response = requests.get(main_url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    anchors = soup.select(
        "body > main > div.match-card.is-live > div.btn-group > a"
    )

    links = []
    for a in anchors:
        href = clean_href(a.get("href", ""))
        if not href:
            continue

        full = urljoin(main_url, href)

        if full not in links:
            links.append(full)

    return links


def extract_embed_url(channel_url):
    response = requests.get(channel_url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    iframe = soup.find("iframe", src=True)
    if not iframe:
        return None

    src = clean_href(iframe["src"])
    return urljoin(channel_url, src)


def add_channels_to_m3u(channels, m3u_file):
    # scrive da zero, così non restano vecchie voci malformed
    with open(m3u_file, "a", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("\n# Canali aggiunti da Hattrick\n")
        for name, url in channels.items():
            f.write(create_m3u_entry(name, url))

def get_channel_name(channel_url):
    return channel_url.rstrip("/").split("/")[-1].replace(".htm", "")
channel_associations = {
    "euro1": "EuroSport 1",
    "skyuno": "Sky UNO",
    "skyunohd": "Sky UNO",
    "tennis": "Sky Sport Tennis",
    "tennishd": "Sky Sport Tennis",
    "dazn1hd": "DAZN 1",
    "motogp": "Sky Sport MotoGP",
    "motogphd": "Sky Sport MotoGP",
    "f1": "Sky Sport F1",
    "f1hd": "Sky Sport F1",
    "max": "Sky Sport Football",
    "maxhd": "Sky Sport Football",
    "arena": "Sky Sport Arena",
    "arenahd": "Sky Sport Arena",
    "calcio": "Sky Sport Calcio",
    "calciohd": "Sky Sport Calcio",
    "uno": "Sky Sport UNO",
    "unohd": "Sky Sport UNO",
    "sport24hd": "Sky Sport 24"
}

tvg_id_associations = {
    "EuroSport 1": "eurosport1.it",
    "Sky UNO": "skyuno.it",
    "Sky Sport Tennis": "skysporttennis.it",
    "DAZN 1": "dazn1.it",
    "Sky Sport MotoGP": "skysportmotogp.it",
    "Sky Sport F1": "skysportf1.it",
    "Sky Sport Football": "skysportmax.it",
    "Sky Sport Arena": "skysportarena.it",
    "Sky Sport Calcio": "skysportcalcio.it",
    "Sky Sport UNO": "skysportuno.it",
    "Sky Sport 24": "skysport24.it"
}

group_title_associations = {
    "EuroSport 1": "Sport",
    "Sky UNO": "Sky",
    "Sky Sport Tennis": "Sport",
    "DAZN 1": "Sport",
    "Sky Sport MotoGP": "Sport",
    "Sky Sport F1": "Sport",
    "Sky Sport Football": "Sport",
    "Sky Sport Arena": "Sport",
    "Sky Sport Calcio": "Sport",
    "Sky Sport UNO": "Sport",
    "Sky Sport 24": "Sport"
}

logo_associations = {
    "EuroSport 1": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/spain/eurosport-1-es.png",
    "Sky UNO": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-uno-it.png",
    "Sky Sport Tennis": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-tennis-it.png",
    "DAZN 1": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/DAZN_1_Logo.svg/774px-DAZN_1_Logo.svg.png",
    "Sky Sport MotoGP": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-motogp-it.png",
    "Sky Sport F1": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-f1-it.png",
    "Sky Sport Football": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-football-it.png",
    "Sky Sport Arena": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-arena-it.png",
    "Sky Sport Calcio": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-calcio-it.png",
    "Sky Sport UNO": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-uno-it.png",
    "Sky Sport 24": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-24-it.png"
}

def get_channel_info(channel_name):
    tvg_name = channel_associations.get(channel_name, channel_name)
    tvg_id = tvg_id_associations.get(tvg_name, "")
    group_title = group_title_associations.get(tvg_name, "Altro")
    logo = logo_associations.get(tvg_name, "")
    suffix = "(Hd)" if "hd" in channel_name.lower() else "(H)"

    return {
        "tvg_id": tvg_id,
        "tvg_name": tvg_name,
        "tvg_logo": logo,
        "group_title": group_title,
        "suffix": suffix
    }
    
def create_m3u_entry(channel_name, embed_url):
    info = get_channel_info(channel_name)
    extinf = (
        f'#EXTINF:-1 tvg-id="{info["tvg_id"]}" '
        f'tvg-name="{info["tvg_name"]}" '
        f'tvg-logo="{info["tvg_logo"]}" '
        f'group-title="{info["group_title"]}", '
        f'{info["tvg_name"]} {info["suffix"]}'
    )
    return f"{extinf}\n{embed_url}\n"


def main():
    main_url = "https://htsport.info/"
    links = extract_channel_links(main_url)

    results = {}
    for i, url in enumerate(links, 1):
        name = get_channel_name(url)
        print(f"[{i}/{len(links)}] {name}")

        embed = extract_embed_url(url)
        if embed:
            results[name] = embed
        else:
            print(f"Nessun embed trovato per {name}")

        time.sleep(1)

    with open("hattrick_channels.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    add_channels_to_m3u(results, "247ita.m3u8")

if __name__ == "__main__":
    main()
