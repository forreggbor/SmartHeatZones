# 🔥 SmartHeatZones – Többzónás intelligens fűtésvezérlés

**Fejlesztői koncepció és tervezési dokumentáció (bővített verzió)**  
© 2025 – forreggbor

---

## 🎯 **Projekt célja**

A **SmartHeatZones** célja, hogy egy **rugalmas, többzónás, energiahatékony és adaptív fűtésvezérlő integrációt** biztosítson Home Assistant környezetben,  
amely teljes mértékben **GUI-ból konfigurálható**, és képes **különböző energiaforrásokat és szenzorokat** egy logikai rendszerbe kapcsolni.

Fő fókusz:

- több zóna, több relé támogatás,

- adaptív és prediktív fűtéslogika,

- napelemes + klímás hibrid működés,

- automatikus szezonfelismerés,

- felhasználóbarát kezelőfelület (Mushroom UI + konfigurációs GUI).

---

## ⚙️ **Zónakezelés – új, kiterjesztett logika**

Minden zóna önálló egységként kezelhető, de akár több eszköz is tartozhat hozzá.

### Zónánként beállítható elemek:

| Elem típusa                   | Leírás                                                                          |
| ----------------------------- | ------------------------------------------------------------------------------- |
| **Hőmérő szenzor**            | Kötelező. Akár több is megadható, átlagértéket használ.                         |
| **Relék**                     | 1–3 db relé rendelhető egy zónához (pl. kazán + szelep + keringetőszivattyú).   |
| **Ablak-/ajtóérzékelők**      | Opcionális. Több is rendelhető egy zónához. Ha bármelyik nyitva → fűtés tiltva. |
| **Célhőmérséklet**            | GUI-ból állítható slider vagy preset gombok segítségével.                       |
| **Automata üzem paraméterei** | Időintervallum + hőmérséklet értékek GUI-ból konfigurálhatók.                   |

---

## 🌡️ **Fűtési módok és GUI-funkciók**

### Preset módok:

| Mód                      | Hőmérséklet | Ikon | Szín       |
| ------------------------ | ----------- | ---- | ---------- |
| **Komfort**              | 22 °C       | 🏠   | 🔵 Kék     |
| **Eco**                  | 17 °C       | 🌿   | 🟢 Zöld    |
| **Távol (Házon kívül)**  | 19 °C       | 🚶   | ⚪ Szürke   |
| **Automata (időzített)** | Dinamikus   | ⏰    | 🟠 Narancs |

A beállítások **zónánként eltérhetnek**.  
Minden érték és mód a GUI-ból változtatható (nem YAML-ból).

---

## 🕓 **Automata mód – GUI-ból programozható**

Alapértelmezett értékek (további módosíthatók GUI-n keresztül):

| Időszak         | Alapértelmezett hőmérséklet | GUI mező                         |
| --------------- | --------------------------- | -------------------------------- |
| Éjszaka (22–06) | 20°C                        | `input_number.auto_night_temp`   |
| Reggel (06–07)  | 21.5°C                      | `input_number.auto_morning_temp` |
| Nappal (07–16)  | 19°C                        | `input_number.auto_day_temp`     |
| Este (16–22)    | 22°C                        | `input_number.auto_evening_temp` |

Az automata mód GUI panelen:

- időpontok csúszkával állíthatók,

- hőmérséklet minden intervallumhoz beállítható,

- „Alapértelmezések visszaállítása” gomb.

---

## 🔒 **Biztonsági és adaptív logika (frissített)**

A SmartHeatZones képes felismerni rendellenes hőmérséklet-változásokat és reagálni rá.

### Feltételek:

- **Túlmelegedés elleni védelem:** 26°C felett automatikus lekapcsolás.

- **Tartósan változatlan hőmérséklet:** ha 30 perc alatt ±0.3°C alatt marad → relé automatikus kikapcsolás (hibás szenzor vagy üres zóna esetén).

- **Gyors hőmérséklet-esés:** ha 5 perc alatt több mint 2°C esés történik → fűtés azonnali leállítása (pl. ablaknyitás).

- **Nyitásérzékelő alapú tiltás:** ha bármely érzékelő „open” → az adott zóna reléi *nem kapcsolhatók be*.

Ezek az opciók GUI-ból engedélyezhetők / letilthatók zónánként.

---

## 🧠 **Adaptív és tanuló algoritmus**

- Felfűtési sebesség mérése és a relé működési ciklus optimalizálása.

- A hőmérséklet stabilizálásához az algoritmus képes előrelátóan kapcsolni (pl. túlmelegedés elkerülésére).

- Ha a fűtés „nem reagál” (pl. kazánhiba), automatikus értesítés (HA notification vagy Telegram).

---

## ⚡ **Hybrid Energy Mode**

- Figyeli a napelemes termelést és a ház aktuális energiafogyasztását.

- Ha elegendő termelés van → vált **klímás fűtésre**.

- Ha nincs → **visszakapcsol kazánra**.

- Manuálisan is kényszeríthető üzemmódok:
  
  - 🔆 *PV prioritás* (amíg van napelem-termelés, addig fűtsön klímával),
  
  - 🔥 *Kazán mód* (klasszikus vezérlés),
  
  - ♻️ *Auto* (a rendszer dönt a két mód között).

Hiszterézis és időzített átváltás védi a klímát a gyakori kapcsolásoktól.

---

## 🎨 **Felhasználói felület (Lovelace & Config GUI)**

- **Integráció menüben** beállítható zónák, szenzorok, és időzítések.

- **Mushroom UI** vezérlők minden zónához.

- Színkódolás:
  
  - 🔵 Kék → Fűtés kikapcsolva
  
  - 🟠 Narancs → Fűtés aktív
  
  - 🟢 Zöld → Célhőmérséklet elérve
  
  - 🔴 Piros → Hiba (érzékelő vagy reléprobléma)

- Állapotkártya:
  
  - Aktuális hőmérséklet
  
  - Beállított hőmérséklet
  
  - Relé állapot(ok)
  
  - Utolsó frissítés ideje
  
  - Átlagos zónatermelés (klíma + kazán energia)

---

## 🧩 **Architektúra (frissített)**

```
custom_components/smartheatzones/ 
├── __init__.py 
├── manifest.json 
├── config_flow.py 
├── const.py 
├── zone_manager.py 
├── relay_controller.py 
├── safety_engine.py 
├── climate_bridge.py 
├── translations/ 
    ├── hu.json 
    └── en.json 

```

---

## 🧰 **Fejlesztési környezet**

- **IDE:** JetBrains PyCharm / PHPStorm

- **Version Control:**
  
  - Privát fejlesztés: *Gitea – gabor*
  
  - Publikus verzió: *GitHub – forreggbor/SmartHeatZones*

- **License:** MIT

- **.gitignore:** Python + HA sablon

- **Dokumentáció:** Markdown (JetBrains + Git kompatibilis)

---

## 🚀 **Fejlesztési roadmap**

| Fázis | Leírás                               | Státusz          |
| ----- | ------------------------------------ |------------------|
| 1.    | Funkcionális és UI tervezés          | ✅ Kész           |
| 2.    | Alap integrációs modul               | ✅ Kész           |
| 3.    | Többrelés zónakezelés és érzékelők   | ✅ Kész           |
| 4.    | Biztonsági és adaptív logika         | ✅ Kész           |
| 5.    | GUI konfigurátor (Integrations menü) | ✅ Kész           |
| 6.    | Hybrid Energy Mode                   | ⚠️ Még nincs     |
| 7.    | Többnyelvű felület és dokumentáció   | ✅ Kész           |
| 8.    | Publikus HACS megjelenés             | 🚧 Előkészítve   |

---

## 💡 **További fejlesztési javaslatok**

1. **Prediktív fűtés** – külső hőmérsékleti trendek és múltbeli adatok alapján előre felfűtés.

2. **Energiafogyasztás loggolás** – minden reléhez kWh statisztika (Shelly API integrációval).

3. **Távolléti mód automatizálás** – HA „person” státusz alapján (ha senki nincs otthon).

4. **Időjárás-API integráció** – pl. OpenWeatherMap alapján szezonfelismerés.

5. **Voice Control kompatibilitás** – Google Home / Alexa eszközökkel.

6. **Rendszer státuszkártya** – összesített energiahatékonyság, napi statisztika, átlagfűtési idő.

7. **AI alapú hőkomfort-optimalizálás** – hosszú távon: gépi tanulás a felhasználói szokásokból.

---

📄 **Fejlesztés tulajdonosa:** *forreggbor*  
📂 **Privát fejlesztői repository:** *gabor @ Gitea*  
🌐 **Publikus GitHub repo:** *forreggbor/SmartHeatZones*  
📘 **Dokumentáció formátum:** Markdown + PDF export
