from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os
import json
from datetime import datetime
import re
from bs4 import BeautifulSoup
import time

GUARCAL = "online"
DADDY= "top"

def html_to_json(html):
    soup = BeautifulSoup(html, "html.parser")
    result = {}

    day_blocks = soup.find_all("div", class_="schedule__day")

    for day_block in day_blocks:
        day_title_el = day_block.find("div", class_="schedule__dayTitle")
        day_title = day_title_el.get_text(strip=True) if day_title_el else "Unknown date"

        if " - Schedule Time" in day_title:
            day_title = day_title.split(" - Schedule Time")[0].strip()

        if day_title not in result:
            result[day_title] = {}

        categories = day_block.find_all("div", class_="schedule__category")

        for category in categories:
            category_name_el = category.find("div", class_="card__meta")
            category_name = category_name_el.get_text(strip=True) if category_name_el else "Unknown category"

            if category_name not in result[day_title]:
                result[day_title][category_name] = []

            events = category.find_all("div", class_="schedule__event")

            for event in events:
                header = event.find("div", class_="schedule__eventHeader")
                if not header:
                    continue

                time_el = header.find("span", class_="schedule__time")
                title_el = header.find("span", class_="schedule__eventTitle")
                channels_box = event.find("div", class_="schedule__channels")

                channels = []
                if channels_box:
                    for a in channels_box.find_all("a"):
                        href = a.get("href", "")
                        match = re.search(r"id=(\d+)", href)

                        channels.append({
                            "channel_name": a.get_text(strip=True),
                            "channel_id": match.group(1) if match else "",
                            "channel_href": href,
                            "channel_title": a.get("title", ""),
                            "data_ch": a.get("data-ch", "")
                        })

                result[day_title][category_name].append({
                    "event": title_el.get_text(strip=True) if title_el else "",
                    "time": time_el.get("data-time", "") if time_el else "",
                    "time_visible": time_el.get_text(strip=True) if time_el else "",
                    "channels": channels
                })

    return result

def modify_json_file(json_file_path):
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    current_month = datetime.now().strftime("%B")

    for date in list(data.keys()):
        match = re.match(r"(\w+\s\d+)(st|nd|rd|th)\s(\d{4})", date)
        if match:
            day_part = match.group(1)
            suffix = match.group(2)
            year_part = match.group(3)
            new_date = f"{day_part}{suffix} {current_month} {year_part}"
            data[new_date] = data.pop(date)

    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    
    print(f"File JSON modificato e salvato in {json_file_path}")

def extract_schedule_container(max_retries=3, retry_delay=5):
    url = f"https://dlstreams.{DADDY}/"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_output = os.path.join(script_dir, "daddyliveSchedule.json")

    print(f"Accesso alla pagina {url} per estrarre il main-schedule-container...")

    for attempt in range(1, max_retries + 1):
        print(f"Tentativo {attempt} di {max_retries}...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                print("Navigazione alla pagina...")
                page.goto(url, timeout=60000)  # Aumentato a 60 secondi
                print("Attesa per il caricamento completo...")
                page.wait_for_timeout(10000)  # 10 secondi

                schedule_content = page.evaluate("""() => {
                    const container = document.querySelector("div.schedule__day");
                    return container ? container.outerHTML : '';
                }""")

                if not schedule_content:
                    print("AVVISO: main-schedule-container non trovato o vuoto!")
                    if attempt < max_retries:
                        print(f"Attesa di {retry_delay} secondi prima del prossimo tentativo...")
                        browser.close()
                        time.sleep(retry_delay)
                        # Incrementa il ritardo per il prossimo tentativo (backoff esponenziale)
                        retry_delay *= 2
                        continue
                    return False

                print("Conversione HTML in formato JSON...")
                json_data = html_to_json(schedule_content)

                with open(json_output, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, indent=4)

                print(f"Dati JSON salvati in {json_output}")

                modify_json_file(json_output)
                browser.close()
                return True

            except PlaywrightTimeoutError as e:
                print(f"ERRORE DI TIMEOUT: {str(e)}")
                # Cattura uno screenshot in caso di errore per debug
                try:
                    page.screenshot(path=f"error_screenshot_attempt_{attempt}.png")
                    print(f"Screenshot dell'errore salvato in error_screenshot_attempt_{attempt}.png")
                except:
                    pass
                
                browser.close()
                
                if attempt < max_retries:
                    print(f"Attesa di {retry_delay} secondi prima del prossimo tentativo...")
                    time.sleep(retry_delay)
                    # Incrementa il ritardo per il prossimo tentativo (backoff esponenziale)
                    retry_delay *= 2
                else:
                    print(f"Tutti i {max_retries} tentativi falliti.")
                    return False
                    
            except Exception as e:
                print(f"ERRORE: {str(e)}")
                # Cattura uno screenshot in caso di errore per debug
                try:
                    page.screenshot(path=f"error_screenshot_attempt_{attempt}.png")
                    print(f"Screenshot dell'errore salvato in error_screenshot_attempt_{attempt}.png")
                except:
                    pass
                
                browser.close()
                
                if attempt < max_retries:
                    print(f"Attesa di {retry_delay} secondi prima del prossimo tentativo...")
                    time.sleep(retry_delay)
                    # Incrementa il ritardo per il prossimo tentativo (backoff esponenziale)
                    retry_delay *= 2
                else:
                    print(f"Tutti i {max_retries} tentativi falliti.")
                    return False

    return False

def extract_guardacalcio_image_links(max_retries=3, retry_delay=5):
    """
    Utilizza Playwright per scaricare i link delle immagini dalla pagina di guardacalcio
    e li salva in un file.
    """
    url = f"https://vod.direttecommunity.{GUARCAL}/partite-streaming.html"
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # File di output per i link delle immagini
    image_links_output = os.path.join(script_dir, "guardacalcio_image_links.txt") 

    print(f"Accesso alla pagina {url} per estrarre i link delle immagini...")

    extracted_links = []

    for attempt in range(1, max_retries + 1):
        print(f"Tentativo {attempt} di {max_retries}...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True) 
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                print("Navigazione alla pagina...")
                page.goto(url, timeout=90000) # Aumentato a 90 secondi
                
                print("Attesa per il caricamento completo e superamento verifiche...")
                # Attendi che l'elemento principale della pagina sia visibile
                try:
                    page.wait_for_selector('div#home', timeout=30000) # Attendi fino a 30 secondi
                    print("Elemento #home trovato, pagina caricata.")
                except PlaywrightTimeoutError:
                    print("AVVISO: Timeout in attesa dell'elemento #home. La pagina potrebbe non essere completamente caricata o bloccata.")
                    # Continua comunque, potresti aver ricevuto l'HTML parziale

                # Estrai l'HTML del body per analizzarlo con BeautifulSoup
                html_content = page.evaluate("""() => {
                    const body = document.querySelector('body');
                    return body ? body.outerHTML : '';
                }""")

                if not html_content:
                    print("AVVISO: Contenuto HTML del body non trovato o vuoto!")
                    if attempt < max_retries:
                        print(f"Attesa di {retry_delay} secondi prima del prossimo tentativo...")
                        browser.close()
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    return False

                print("Analisi HTML con BeautifulSoup e estrazione link immagini...")
                soup = BeautifulSoup(html_content, 'html.parser')

                # Cerca tutti i tag <img>
                img_tags = soup.find_all('img')
                print(f"Trovate {len(img_tags)} immagini nella pagina.")

                # Estrai i link src
                for img in img_tags:
                    if img.has_attr('src'):
                        src = img['src']
                        # Assicurati che l'URL sia assoluto
                        if src.startswith('http'):
                            extracted_links.append(src)
                        else:
                            # Costruisci URL assoluto
                            base_url = f"https://guardacalcio.{GUARCAL}"
                            if src.startswith('/'):
                                extracted_links.append(base_url + src)
                            else:
                                extracted_links.append(base_url + '/' + src)

                if extracted_links:
                    print(f"Trovati {len(extracted_links)} link di immagini. Salvataggio in {image_links_output}...")
                    with open(image_links_output, "w", encoding="utf-8") as f:
                        for link in extracted_links:
                            f.write(link + "\n")

                    print(f"Link immagini salvati in {image_links_output}")
                    browser.close()
                    return True # Successo

                else:
                    print("Nessun link immagine trovato nella pagina.")
                    browser.close()
                    if attempt < max_retries:
                        print(f"Attesa di {retry_delay} secondi prima del prossimo tentativo...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    return False # Fallimento dopo i tentativi

            except PlaywrightTimeoutError as e:
                print(f"ERRORE DI TIMEOUT DURANTE LA NAVIGAZIONE O L'ATTESA: {str(e)}")
                try:
                    page.screenshot(path=f"error_screenshot_guardacalcio_attempt_{attempt}.png")
                    print(f"Screenshot dell'errore salvato in error_screenshot_guardacalcio_attempt_{attempt}.png")
                except:
                    pass
                browser.close()
                if attempt < max_retries:
                    print(f"Attesa di {retry_delay} secondi prima del prossimo tentativo...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"Tutti i {max_retries} tentativi falliti per {url}.")
                    return False
                    
            except Exception as e:
                print(f"ERRORE GENERALE: {str(e)}")
                try:
                    page.screenshot(path=f"error_screenshot_guardacalcio_attempt_{attempt}.png")
                    print(f"Screenshot dell'errore salvato in error_screenshot_guardacalcio_attempt_{attempt}.png")
                except:
                    pass
                browser.close()
                if attempt < max_retries:
                    print(f"Attesa di {retry_delay} secondi prima del prossimo tentativo...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"Tutti i {max_retries} tentativi falliti per {url}.")
                    return False

    return False # Fallimento dopo i tentativi

if __name__ == "__main__":
    # Puoi scegliere quale funzione eseguire qui.
    # Per scaricare i link delle immagini da guardacalcio:
    success = extract_guardacalcio_image_links()
    if not success:
        print("Errore durante l'estrazione dei link delle immagini da guardacalcio.")
        #exit(1)

    # Se vuoi ancora estrarre lo schedule da daddylive, puoi chiamare anche questa:
    success = extract_schedule_container() # Decommentato
    if not success:
        print("Errore durante l'estrazione dello schedule da daddylive.")
        exit(1) # Usciamo se l'estrazione dello schedule fallisce, poiché itaevents.py ne ha bisogno
