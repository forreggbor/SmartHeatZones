# SmartHeatZones v1.4.4 - GYORS REFERENCIA KÁRTYA

## 🔧 GYORS HIBAKERESÉSI PARANCSOK

### SSH Parancsok (HA Szerver)

```bash
# Csatlakozás
ssh root@<ha_ip>

# Fájlok helye
cd /config/custom_components/smartheatzones/

# Fájl tartalom gyors ellenőrzés
head -n 5 climate.py
# Kimenet: Version: 1.4.4

# Log nézés valós időben
tail -f /config/home-assistant.log | grep SmartHeatZones

# HA újraindítás
ha core restart

# HA verzió
ha core info
```

### PyCharm SFTP (Helyi Gép)

```
Tools → Deployment → Browse Remote Host
Navigálj: /config/custom_components/smartheatzones/

Feltöltés:
Right-click fájlon → Upload to <server>

Letöltés:
Right-click mappán → Download from <server>
```

---

## 🐛 GYORS DIAGNÓZIS DÖNTÉSI FA

```
Relék NEM kapcsolnak?
│
├─> Van "Target temperature set" a logban?
│   ├─> NINCS: Böngésző cache → CTRL+SHIFT+DEL
│   └─> VAN: Tovább ↓
│
├─> Van "Auto-switched to HEAT" a logban?
│   ├─> NINCS: Rossz fájl verzió
│   │   └─> Ellenőrizd: head -n 5 climate.py
│   │       Kell: "Version: 1.4.4"
│   └─> VAN: Tovább ↓
│
├─> Van "switch.turn_on" a logban?
│   ├─> NINCS: Options üres
│   │   └─> Nyisd meg: Fogaskerék → Töltsd ki → Mentés
│   └─> VAN: Tovább ↓
│
└─> Van "Failed to control relay" ERROR?
    ├─> VAN: Rossz entity_id
    │   └─> Fejlesztői eszközök → Állapotok
    │       Ellenőrizd: switch.zona_rele_1 létezik?
    └─> NINCS: Relay HW probléma
        └─> Tesztelés kézzel: Fejlesztői eszközök → Szolgáltatások
            switch.turn_on → entity: switch.zona_rele_1
```

---

## 📊 LOGBAN KERESENDŐ KULCSSZAVAK

### ✅ SIKERES MŰKÖDÉS:

```bash
# Indulás
"[SmartHeatZones] Creating climate entity: Földszint"
"[SmartHeatZones] [Földszint] Initialized | Initial HVAC=heat"
"[SmartHeatZones] [Földszint] Initial temperature: 19.5°C"

# Target állítás
"[SmartHeatZones] [Földszint] Target temperature: 21.0 → 23.0°C"
"[SmartHeatZones] [Földszint] Auto-switched to HEAT"

# Kapcsolás
"[SmartHeatZones] [Földszint] Evaluate: current=19.5 target=23.0"
"[SmartHeatZones] [Földszint] Heating ON (Needs heat ...)"
"[SmartHeatZones] [Földszint] switch.turn_on → switch.zona_rele_1"

# Kazán
"[SmartHeatZones] Zone 'Földszint' requested boiler ON (active_zones=1)"
"[SmartHeatZones] Boiler relay switch.kazan_fo → TURN_ON"
```

### ❌ HIBÁK:

```bash
# Kritikus
"ERROR" → Súlyos hiba, azonnali javítás szükséges
"Failed to control relay" → Rossz entity_id vagy HW probléma

# Figyelmeztetés
"WARNING: Sensor unavailable" → Szenzor kiesés, átmeneti
"WARNING: Failed to control relay" → Relay probléma, de folytatódik

# Info (nem hiba)
"Door/window open" → Normál működés
"Heating OFF" → Normál lekapcsolás
```

---

## 🎯 LEGGYAKORIBB PROBLÉMÁK 1-PERC FIX

### 1. ÜRES OPTIONS (80% esély)

**Tünet:** Semmi nem történik, entity létrejön de szürke.

**1-perc fix:**
```
1. Beállítások → Eszközök és szolgáltatások
2. SmartHeatZones → Zóna → Fogaskerék
3. Tölts ki MINDEN mezőt:
   - Hőmérő szenzor: sensor.temp_foldszint
   - Relék: [switch.zona_rele_1]
   - Kazán: switch.kazan_fo
   - Hiszterézis: 0.3
4. MENTÉS
5. Teszteld: Állítsd a target-et
```

### 2. CACHE PROBLÉMA (15% esély)

**Tünet:** Fordítások nem magyarok, kártya nem reagál.

**1-perc fix:**
```
1. CTRL+SHIFT+DEL
2. Cached images and files → Clear
3. CTRL+F5 (hard refresh)
4. Ha továbbra sem működik:
   ssh root@<ha_ip>
   cd /config && rm -rf .cache/
   ha core restart
```

### 3. ROSSZ VERZIÓ (3% esély)

**Tünet:** Auto-switch nem működik.

**1-perc fix:**
```bash
ssh root@<ha_ip>
head -n 5 /config/custom_components/smartheatzones/climate.py

# Ha nem "Version: 1.4.4":
# → Töltsd fel újra a javított fájlt
# → ha core restart
```

### 4. ENTITY_ID ELÍRÁS (2% esély)

**Tünet:** "Failed to control relay"

**1-perc fix:**
```
1. Fejlesztői eszközök → Állapotok
2. Keresd: "switch.zona"
3. Másold ki a PONTOS nevet (case-sensitive!)
4. Options → Illeszd be pontosan
5. Mentés
```

---

## 📋 ELLENŐRZŐ LISTA (5 PERC)

Minden telepítés vagy frissítés után végezd el:

```
□ SSH: head -n 5 climate.py → "Version: 1.4.4"
□ SSH: ls translations/hu.json → létezik
□ HA: Újraindítás megtörtént (teljes restart)
□ Browser: Cache törölve (CTRL+SHIFT+DEL)
□ UI: Zóna látható (Beállítások → Eszközök)
□ UI: Climate entitás látható (Áttekintés)
□ UI: Aktuális hőmérséklet megjelenik
□ Options: Minden mező kitöltve (fogaskerék)
□ Options: Fordítások MAGYARUL (nem "label_1")
□ Log: Nincs ERROR sor
□ Teszt: Target állítás → Relék kapcsolnak (< 3 sec)
□ Teszt: HEAT/OFF váltás → működik
```

**Ha mind zöld:** ✅ Működik!  
**Ha valamelyik piros:** ↑ Nézd meg a Döntési Fát

---

## 🔥 PANIC MODE - TELJES RESET

Ha minden más failel, végső megoldás (10 perc):

```bash
# 1. Biztonsági mentés
ssh root@<ha_ip>
cd /config/custom_components
tar -czf smartheatzones_backup_$(date +%Y%m%d_%H%M%S).tar.gz smartheatzones/

# 2. Teljes törlés
rm -rf smartheatzones/

# 3. Újratelepítés (PyCharm SFTP)
# Töltsd fel az ÖSSZES fájlt újra a GitHub-ról

# 4. Cache tisztítás
cd /config
rm -rf .cache/
rm -rf .storage/*climate*

# 5. HA restart
ha core restart

# 6. Böngésző
# CTRL+SHIFT+DEL → Clear everything

# 7. Integráció újra hozzáadás
# Beállítások → Integráció hozzáadása → SmartHeatZones
# Hozz létre 1 teszt zónát
# Fogaskerék → Töltsd ki az Options-t
# MENTÉS

# 8. Teszt
# Állíts a target-en → Relék kapcsolnak?
```

**Ha ezután sem működik:** → GitHub Issue (log + screenshot)

---

## 💾 GYORS BACKUP SCRIPT

Mentsd el: `/config/scripts/backup_smartheat.sh`

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/config/backups"
SOURCE="/config/custom_components/smartheatzones"

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/smartheatzones_$DATE.tar.gz $SOURCE
echo "Backup created: smartheatzones_$DATE.tar.gz"

# Csak az utolsó 5 backup megtartása
cd $BACKUP_DIR
ls -t smartheatzones_*.tar.gz | tail -n +6 | xargs rm -f
```

Használat:
```bash
chmod +x /config/scripts/backup_smartheat.sh
/config/scripts/backup_smartheat.sh
```

---

## 📞 SUPPORT CHECKLIST (GitHub Issue Készítés)

Ha GitHub Issue-t nyitsz, csatold:

```
1. HA Verzió:
   Beállítások → Rendszer → Általános
   Core: 2025.10.4

2. Integráció Verzió:
   ssh root@<ha_ip>
   head -n 5 /config/custom_components/smartheatzones/climate.py
   
3. Teljes Log (utolsó 100 sor):
   tail -n 100 /config/home-assistant.log > ~/smartheat_log.txt
   
4. Options Screenshot:
   Fogaskerék → Teljes képernyő → Screenshot

5. Entity State:
   Fejlesztői eszközök → Állapotok → climate.foldszint
   Screenshot

6. Pontos leírás:
   - Mit csináltál?
   - Mi volt a várt eredmény?
   - Mi történt helyette?
   - Mikor kezdődött a probléma?
```

---

## 🎓 TANULÁSI FORRÁSOK

### Home Assistant Fejlesztés:
- https://developers.home-assistant.io/
- https://developers.home-assistant.io/docs/creating_integration_manifest/

### Climate Platform Specifikus:
- https://developers.home-assistant.io/docs/core/entity/climate/

### Python Best Practices:
- https://peps.python.org/pep-0008/ (PEP8)
- https://mypy.readthedocs.io/ (Type Hints)

---

## 📱 MOBIL TESZT (Opcionális)

Home Assistant Companion App-ban:

```
1. Nyisd meg a zóna termosztátját
2. Próbáld állítani a target-et
3. Váltsd OFF/HEAT között
4. Ellenőrizd: azonnal reagál?

Ha NEM → Cache probléma:
- App beállítások → Clear cache
- App újraindítás
- Újra belépés
```

---

**Verzió:** Quick Reference v1.0  
**Dátum:** 2025-10-26  
**Nyomtasd ki és tartsd kéznél!** 🖨️

---

## 📌 BÖNGÉSZŐ KÖNYVJELZŐK (Gyors Hozzáférés)

Mentsd el ezeket:

```
HA Szolgáltatások: http://<ha_ip>:8123/developer-tools/service
HA Állapotok: http://<ha_ip>:8123/developer-tools/state
HA Naplók: http://<ha_ip>:8123/config/logs
HA Eszközök: http://<ha_ip>:8123/config/integrations
GitHub Issues: https://github.com/forreggbor/SmartHeatZones/issues
HA Docs: https://developers.home-assistant.io/docs/creating_integration_manifest
```

