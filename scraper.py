import requests
import random
from bs4 import BeautifulSoup

# ── Real browser User-Agent lar ──────────────────────────────────
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

def _get_headers() -> dict:
    return {
        "User-Agent":                random.choice(_USER_AGENTS),
        "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language":           "en-US,en;q=0.9",
        "Accept-Encoding":           "gzip, deflate, br",
        "Connection":                "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control":             "max-age=0",
        "Referer":                   "https://www.google.com/",
    }

def translate_to_uz(text):
    if not text: return ""
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=uz&dt=t&q={text}"
        res = requests.get(url, timeout=5).json()
        return res[0][0][0]
    except: return "⚠️ Tarjima xatoligi."

def clean_text(element):
    if not element: return ""
    return " ".join(element.get_text(separator=" ", strip=True).split())

def scrape_longman_ultimate(word):
    try:
        url = f"https://www.ldoceonline.com/dictionary/{word.lower().strip().replace(' ', '-')}"
        res = requests.get(url, headers=_get_headers(), timeout=15)
        if res.status_code != 200: return None

        soup = BeautifulSoup(res.text, 'lxml')
        entries = soup.find_all('span', class_='dictentry')
        if not entries: return None

        merged = {}
        global_pron = ""

        for entry in entries:
            pron_tag = entry.find('span', class_='PRON')
            if pron_tag: global_pron = clean_text(pron_tag)

            pos_tag = entry.find('span', class_='POS')
            pos = clean_text(pos_tag).upper() if pos_tag else "WORD"
            
            is_phrvb = "PhrVbEntry" in entry.get('class', []) or entry.find('span', class_='PHRVB')
            if is_phrvb: pos = "PHRASAL VERB"
            
            hwd = clean_text(entry.find('span', class_='HWD')) or word

            if pos not in merged:
                merged[pos] = {"word": hwd, "pron": global_pron, "data": []}
            elif not merged[pos]["pron"] and global_pron:
                merged[pos]["pron"] = global_pron

            blocks = entry.find_all(['span'], class_=['Sense', 'PhrVbEntry'])
            for b in blocks:
                head_pv = b.find(['span'], class_=['Head', 'PHRVB', 'LEXUNIT'])
                pv_name = clean_text(head_pv)
                
                defs = b.find_all('span', class_='DEF')
                if not defs and not pv_name: continue

                sub_list = []
                subs = b.find_all('span', class_='Subsense')
                if subs:
                    for idx, sub in enumerate(subs):
                        d_text = sub.find('span', class_='DEF')
                        if not d_text: continue
                        sub_list.append({
                            "letter": chr(97 + idx),
                            "gram": clean_text(sub.find('span', class_='GRAM')),
                            "def": clean_text(d_text),
                            "exs": [clean_text(ex) for ex in sub.find_all('span', class_='EXAMPLE')]
                        })
                else:
                    for d in defs:
                        sub_list.append({
                            "letter": "",
                            "gram": clean_text(b.find('span', class_='GRAM')),
                            "def": clean_text(d),
                            "exs": [clean_text(ex) for ex in b.find_all('span', class_='EXAMPLE')]
                        })

                if sub_list or pv_name:
                    merged[pos]["data"].append({
                        "sign": clean_text(b.find('span', class_='SIGNPOST')).upper(),
                        "lex": pv_name, "subs": sub_list
                    })
        return merged
    except: return None

def format_output(pos, content, show_examples, show_translation):
    res = f"📕 <b>{content['word'].upper()}</b> [{pos}]\n"
    if content['pron']: res += f"🗣 /{content['pron']}/\n"
    res += "━━━━━━━━━━━━━━━\n\n"
    
    cnt = 1
    for s in content['data']:
        line_head = f"<b>{cnt}.</b> "
        sign = f"<u>{s['sign']}</u> " if s['sign'] else ""
        lex = f"<b>{s['lex']}</b> " if s['lex'] else ""
        
        for i, sub in enumerate(s['subs']):
            gram = f"<code>[{sub['gram'].strip('[]')}]</code> " if sub['gram'] else ""
            letter = f"<b>{sub['letter']})</b> " if sub['letter'] else ""
            copy_def = f"<b><code>{sub['def']}</code></b>"
            
            if i == 0: res += f"{line_head}{sign}{lex}{letter}{gram}{copy_def}\n"
            else: res += f"  {letter}{gram}{copy_def}\n"
            
            if show_translation:
                res += f"🇺🇿 <i>{translate_to_uz(sub['def'])}</i>\n"
            
            if show_examples:
                for ex in sub['exs']: res += f"    • <i>{ex}</i>\n"
        if not s['subs'] and lex: res += f"{line_head}{sign}{lex}\n"
        res += "\n"
        cnt += 1
    return res
