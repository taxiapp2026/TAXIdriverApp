/** Map OSM tags onto Taxi and Fly feature kinds — our schema, OSM as source. */

export const ATTICA_BBOX = {
  west: 22.89,
  south: 37.49,
  east: 24.1,
  north: 38.34,
};

const ROAD_CLASS = new Set([
  "motorway",
  "motorway_link",
  "trunk",
  "trunk_link",
  "primary",
  "primary_link",
  "secondary",
  "secondary_link",
  "tertiary",
  "tertiary_link",
  "residential",
  "living_street",
  "unclassified",
  "service",
  "pedestrian",
  "footway",
  "path",
  "steps",
  "track",
  "cycleway",
  "construction",
]);

export function classifyTags(tags = {}) {
  if (tags.highway && ROAD_CLASS.has(tags.highway)) {
    return { kind: "road", class: tags.highway };
  }
  if (tags.aeroway === "aerodrome" || tags.aeroway === "terminal") {
    return { kind: "poi", class: "airport" };
  }
  if (tags.amenity === "taxi") return { kind: "poi", class: "taxi" };
  if (tags.amenity === "fuel" || tags.amenity === "charging_station") {
    return { kind: "poi", class: "fuel" };
  }
  if (tags.tourism === "hotel" || tags.tourism === "guest_house" || tags.tourism === "hostel" || tags.tourism === "motel") {
    return { kind: "poi", class: "hotel" };
  }
  if (tags.shop) return { kind: "poi", class: "shop" };
  if (tags.amenity === "restaurant" || tags.amenity === "cafe" || tags.amenity === "fast_food" || tags.amenity === "bar") {
    return { kind: "poi", class: "food" };
  }
  if (tags.amenity === "hospital" || tags.amenity === "clinic" || tags.amenity === "doctors") {
    return { kind: "poi", class: "health" };
  }
  if (tags.amenity === "pharmacy") return { kind: "poi", class: "pharmacy" };
  if (tags.amenity === "police" || tags.amenity === "fire_station") {
    return { kind: "poi", class: "emergency" };
  }
  if (tags.railway === "station" || tags.station === "subway" || tags.public_transport === "station") {
    return { kind: "poi", class: "transit" };
  }
  if (tags.highway === "bus_stop") return { kind: "poi", class: "transit" };
  if (tags.amenity === "bank" || tags.amenity === "atm") return { kind: "poi", class: "bank" };
  if (tags.tourism === "attraction" || tags.tourism === "museum" || tags.historic) {
    return { kind: "poi", class: "attraction" };
  }
  if (tags.amenity === "place_of_worship") return { kind: "poi", class: "worship" };
  if (tags.office) return { kind: "poi", class: "office" };
  if (tags.amenity) return { kind: "poi", class: tags.amenity };
  if (tags.natural === "water" || tags.waterway === "riverbank" || tags.landuse === "reservoir") {
    return { kind: "water", class: tags.water || "water" };
  }
  if (tags.waterway) return { kind: "water", class: tags.waterway };
  if (
    tags.leisure === "park" ||
    tags.leisure === "garden" ||
    tags.leisure === "playground" ||
    tags.landuse === "forest" ||
    tags.landuse === "grass" ||
    tags.landuse === "meadow" ||
    tags.landuse === "recreation_ground" ||
    tags.landuse === "cemetery" ||
    tags.natural === "wood"
  ) {
    return { kind: "park", class: tags.leisure || tags.landuse || tags.natural };
  }
  if (tags.building && tags["addr:housenumber"]) {
    return { kind: "address", class: "building" };
  }
  if (tags["addr:housenumber"]) return { kind: "address", class: "address" };
  if (tags.building) return { kind: "building", class: tags.building === "yes" ? "building" : tags.building };
  if (tags.railway) return { kind: "rail", class: tags.railway };
  if (tags.boundary === "administrative") return { kind: "boundary", class: tags.admin_level || "admin" };
  if (tags.place) return { kind: "place", class: tags.place };
  return null;
}

export function displayName(tags = {}) {
  const street = tags["addr:street"];
  const num = tags["addr:housenumber"];
  if (street && num) return `${street} ${num}`;
  return tags.name || tags["name:el"] || tags["name:en"] || tags.ref || tags.shop || tags.amenity || "";
}

export function minZoomFor(kind, cls) {
  if (kind === "water") return 8;
  if (kind === "park") {
    if (cls === "grass" || cls === "garden" || cls === "playground" || cls === "meadow") return 14;
    return 10;
  }
  if (kind === "boundary") return 8;
  if (kind === "place" && (cls === "city" || cls === "town")) return 8;
  if (kind === "road") {
    if (cls.startsWith("motorway") || cls.startsWith("trunk")) return 8;
    if (cls.startsWith("primary")) return 10;
    if (cls.startsWith("secondary")) return 11;
    if (cls.startsWith("tertiary")) return 12;
    if (cls === "residential" || cls === "unclassified" || cls === "living_street") return 13;
    if (cls === "service") return 15;
    return 15;
  }
  if (kind === "rail") return 11;
  if (kind === "poi") {
    if (cls === "airport") return 8;
    if (cls === "hotel" || cls === "fuel" || cls === "transit" || cls === "hospital" || cls === "health" || cls === "taxi") return 12;
    if (["bench", "waste_basket", "waste_disposal", "recycling", "parking", "fountain", "waste_basket"].includes(cls)) return 17;
    return 14;
  }
  if (kind === "address") return 17;
  if (kind === "building") return 16;
  return 12;
}
