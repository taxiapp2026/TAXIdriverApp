# Taxi and Fly Maps

Δικό μας σύστημα χαρτών για Αθήνα και Αττική: renderer, βάση, αναζήτηση, επεξεργασία και εργαστήριο Screen-to-Code.

**Δεν** χρησιμοποιεί Google Maps API. **Δεν** κατεβάζει κώδικα της Google. **Δεν** πειράζει την υπάρχουσα εφαρμογή Taxi and Fly. **Καμία** πληρωμένη υπηρεσία.

## Γρήγορη εκκίνηση

```bash
cd taxi-and-fly-maps
npm install
npm test
npm start
```

Άνοιγμα: http://127.0.0.1:3477

Η πρώτη εκκίνηση φέρνει δωρεάν απόκομμα OpenStreetMap (κέντρο Αθήνας, Πειραιάς, αεροδρόμιο) μέσω Overpass.

Ολόκληρη η Αττική από Geofabrik (δωρεάν, ODbL, ~325 MB Ελλάδα):

```bash
npm run import:attica
npm start
```

## Τι είναι δικό μας και τι όχι

| Κομμάτι | Προέλευση |
| --- | --- |
| Προβολή χάρτη, στυλ, παν/ζουμ, ετικέτες | Δικός μας Canvas |
| SQLite, χωρικά queries, FTS αναζήτηση | Δικός μας κώδικας |
| Επεξεργαστής POI/δρόμων | Δικός μας |
| Διαδρομή A* πάνω στο οδικό γράφο | Δικός μας |
| Screen-to-Code (εικόνα → διανύσματα) | Δικός μας |
| Γεωμετρίες δρόμων / POI / διευθύνσεις | OpenStreetMap, άδεια ODbL |

Λεπτομέρειες: [data/ATTRIBUTION.md](data/ATTRIBUTION.md), [docs/SCREEN-CAPABILITIES.md](docs/SCREEN-CAPABILITIES.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
