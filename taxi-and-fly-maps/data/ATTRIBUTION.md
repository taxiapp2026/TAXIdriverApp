# Πηγές χαρτογραφικών δεδομένων

Ο κώδικας του Taxi and Fly Maps είναι δικός μας. Τα γεωγραφικά δεδομένα **δεν** προέρχονται από Google Maps.

## Επιτρεπόμενες πηγές (δωρεάν, με δικαίωμα επαναχρησιμοποίησης)

| Πηγή | Άδεια | Τι δίνει | Σημείωση |
| --- | --- | --- | --- |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/) | Δρόμοι, στενά, POI, διευθύνσεις, κτίρια | Υποχρεωτική αναφορά: © OpenStreetMap contributors. Share-alike στο παράγωγο dataset. |
| [Geofabrik](https://download.geofabrik.de/europe/greece.html) | ODbL (ίδια OSM δεδομένα) | `greece-latest.osm.pbf` (~325 MB, ημερήσια) | Δωρεάν λήψη. Δεν υπάρχει έτοιμο απόκομμα «Αττική»· γίνεται `osmium extract` στο bbox. |
| Δημόσιο Overpass API | ODbL | Θεματικά ερωτήματα | Δωρεάν, με όρια χρήσης. Όχι για ολόκληρη την Αττική σε ένα query. |
| [data.gov.gr](https://www.data.gov.gr/) | Άδειες ανοικτών δεδομένων δημοσίου | Διοικητικά όρια, στατιστικά | Ελέγχετε την άδεια κάθε dataset χωριστά. |
| [ELSTAT / geodata.gov.gr](https://geodata.gov.gr/) | Συνήθως ανοικτά δεδομένα | Καλλικρατικοί δήμοι, καλύψεις | Χρήσιμο για όρια Αττικής, όχι για κάθε κατάστημα. |
| Δικά μας πεδία / επεξεργαστής | Δικά μας | Διορθώσεις, πιάτσες, σημεία οδηγών | Αποθηκεύονται ως `source=local-edit`. |

## Πηγές που **δεν** χρησιμοποιούμε

- Google Maps, Google tiles, Google Places, Google Geocoding ή οποιοδήποτε Google Maps API
- Οπτική αντιγραφή (screen scraping) του χάρτη της Google
- Πληρωμένα APIs (Mapbox, Here, Google, Geofabrik Overpass επί πληρωμή) χωρίς έγκριση

Η οπτική ανάλυση οθόνης (Screen-to-Code) στο `/vision.html` είναι εργαστήριο για **σκίτσα, δημόσιου τομέα εικόνες, ή στιγμιότυπα του δικού μας χάρτη**. Δεν είναι μέθοδος αναπαραγωγής της βάσης της Google.
