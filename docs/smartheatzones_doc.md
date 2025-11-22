# SmartHeatZones – Többzónás intelligens fűtésvezérlés

*Fejlesztői koncepció és tervezési dokumentáció*  
© 2025 – forreggbor

---

## 1️⃣ Projekt célja
A SmartHeatZones integráció több fűtési zónát kezel, mindegyikhez külön hőmérőt, relét és célhőmérsékletet rendel.  
Támogatja az automatikus és manuális fűtésmódokat, valamint a napelemes és klímás hibrid működést.

---

## 2️⃣ Alapfunkciók
- Zónánként külön hőmérő és relé  
- Preset módok: Komfort (22°C), Eco (17°C), Távol (19°C), Automata (időzített)  
- Lovelace felület, slideres hőmérséklet-beállítással  
- Aktív mód színes kiemeléssel  

---

## 3️⃣ Automata mód (időalapú működés)
| Időszak | Hőmérséklet |
|----------|--------------|
| Éjszaka (22–06) | 20°C |
| Reggel (06–07) | 21.5°C |
| Nappal (07–16) | 19°C |
| Este (16–22) | 22°C |

---

## 4️⃣ Biztonsági funkciók
- Túlmelegedés elleni védelem (26°C)  
- 30 perces relé időlimit  
- Kandallós zónában adaptív leállítás gyors hőemelkedés esetén  

---

## 5️⃣ Hybrid Energy Mode
A rendszer napelemes és hálózati adatok alapján képes automatikusan váltani a **klíma** és a **kazán** között.  
Ha nincs elég napelemes termelés, a rendszer visszavált a kazánra.  
Kényszerített mód is választható.

---

## 6️⃣ Fejlesztés alatt álló funkciók
- Külső hőmérséklet alapú szezonfelismerés  
- Többnyelvű megjelenítés  
- Statisztikák és előfűtés időjárás alapján  

---

## 7️⃣ GUI (Lovelace)
- Egységes kártyamagasság (170 px)  
- Kék háttér → fűtés kikapcsolva, narancs → aktív  
- Színes preset gombok  

---

## 8️⃣ Architektúra
```
custom_components/smartheatzones/
├── __init__.py
├── config_flow.py
├── zone_controller.py
├── energy_controller.py
├── safety_module.py
└── translations/
```

---

## 9️⃣ Fejlesztési környezet
- IDE: JetBrains PyCharm / PHPStorm  
- Git: Gitea (privát) → GitHub (publikus)  
- License: MIT  
- .gitignore: Python template  

---

## 🔚 Összefoglalás
A SmartHeatZones célja egy adaptív, energiahatékony, többzónás fűtésrendszer létrehozása,  
amely külső energiaforrásokat és hőmérsékleti trendeket is figyelembe vevő vezérléssel.

---

**SmartHeatZones © 2025 – forreggbor**

