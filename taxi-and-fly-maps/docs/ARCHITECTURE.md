# Αρχιτεκτονική Taxi and Fly Maps

Ξεχωριστό σύστημα από την υπάρχουσα εφαρμογή Taxi and Fly. Δεν τροποποιεί Android/client apps.

```
Browser (δικός μας Canvas renderer)
    ↓  /api/features  /api/search  /api/route  CRUD
Node (Express)
    ↓
SQLite + R-Tree + FTS5
    ↑
import-osm.js  ←  Geofabrik PBF / Overpass  (ODbL)
vision.js      ←  εικόνα → διανύσματα (εργαστήριο)
```

## Renderer

Web Mercator, Canvas 2D, χωρίς Mapbox/Google/MapLibre SDK. Επίπεδα: νερό, πάρκα, ράγες, δρόμοι ανά κλάση, POI, ετικέτες. Pan/zoom, επιλογή, σχεδίαση.

## Βάση

Πίνακας `features` με γεωμετρία GeoJSON, χωρικό ευρετήριο R-Tree, αναζήτηση FTS5 (ελληνικά via unicode61). Οι τοπικές διορθώσεις γράφονται με `source=local-edit`.

## Κάλυψη Αττικής

- `npm run import:seed` — κέντρο Αθήνας, Πειραιάς, αεροδρόμιο (Overpass).
- `npm run import:attica` — λήψη `greece-latest.osm.pbf`, αποκοπή bbox Αττικής, φίλτρο δρόμων/POI/διευθύνσεων.

Πλήρης «κάθε στενό / κάθε κατάστημα» εξαρτάται από την πληρότητα του OSM συν τις δικές μας επεξεργασίες — όχι από screen scraping.
