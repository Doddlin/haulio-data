#!/usr/bin/env python3
"""
extract_underpasses.py

Extraherar underfarter och tunnlar utan registrerad fri höjd från
Trafikverkets SverigepaketTP.gpkg och exporterar till GeoJSON (WGS84).

Dessa segment är potentiella varningspunkter för fordon högre än 4.50m
(svensk standardhöjd för broar).

Användning:
    pip install geopandas pyproj
    python extract_underpasses.py --input SverigepaketTP.gpkg --output underpasses.geojson

Krav:
    pip install geopandas pyproj
"""

import argparse
import geopandas as gpd
from shapely.geometry import mapping
import json
import sys

KONSTRUKTION_FILTER = {"underfart", "tunnel", "överfart och underfart"}

KEEP_COLUMNS = [
    "Bro_och_tunnel_Konstruktion",
    "Bro_och_tunnel_Namn",
    "Vagkategori_kategori",
    "Vagnummer_Huvudnummer_Vard",
    "Vagnummer_Europavag",
    "Hastighetsgrans_HogstaTillatnaHastighet_F",
    "ROUTE_ID",
    "_length",
]

def extract(input_path: str, output_path: str):
    print(f"Läser {input_path} ...")
    print("(Detta kan ta en stund för en 2GB+ fil)\n")

    gdf = gpd.read_file(input_path, layer="SverigepaketTP")

    print(f"Totalt antal segment: {len(gdf):,}")

    # Filtrera: underfart/tunnel OCH inget höjdhindervärde
    mask = (
        gdf["Bro_och_tunnel_Konstruktion"].isin(KONSTRUKTION_FILTER) &
        gdf["Hojdhinder45dm_Fri_hojd"].isna()
    )
    filtered = gdf[mask].copy()
    print(f"Underfarter/tunnlar utan höjdvärde: {len(filtered):,}")

    # Behåll bara relevanta kolumner + geometri
    cols_available = [c for c in KEEP_COLUMNS if c in filtered.columns]
    filtered = filtered[cols_available + ["geometry"]]

    # Beräkna mittpunkt i SWEREF99 TM (projected CRS) → korrekt centroid
    centroids = filtered.geometry.centroid
    centroids_wgs84 = gpd.GeoSeries(centroids, crs="EPSG:3006").to_crs(epsg=4326)
    filtered["lat"] = centroids_wgs84.y
    filtered["lon"] = centroids_wgs84.x

    # Konvertera geometrin från SWEREF99 TM (EPSG:3006) → WGS84 (EPSG:4326)
    print("Konverterar koordinater SWEREF99 TM → WGS84 ...")
    filtered = filtered.to_crs(epsg=4326)

    # Byt namn på kolumner till något Flutter-vänligt
    filtered = filtered.rename(columns={
        "Bro_och_tunnel_Konstruktion": "type",
        "Bro_och_tunnel_Namn": "name",
        "Vagkategori_kategori": "road_category",
        "Vagnummer_Huvudnummer_Vard": "road_number",
        "Vagnummer_Europavag": "euro_road",
        "Hastighetsgrans_HogstaTillatnaHastighet_F": "speed_limit",
        "ROUTE_ID": "route_id",
        "_length": "length_m",
    })

    # Exportera som GeoJSON
    print(f"Exporterar till {output_path} ...")
    filtered.to_file(output_path, driver="GeoJSON")

    # Skriv ut filstorlek
    import os
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\n✅ Klar!")
    print(f"   Antal objekt: {len(filtered):,}")
    print(f"   Filstorlek:   {size_mb:.1f} MB")
    print(f"   Sparad till:  {output_path}")
    print(f"\nTips: Om filen är stor, kör:")
    print(f"   gzip -k {output_path}")
    print(f"för att få en .gz-version som Flutter kan ladda komprimerad (~70% mindre).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrahera okända underfarter från NVDB GPKG")
    parser.add_argument("--input", required=True, help="Sökväg till SverigepaketTP.gpkg")
    parser.add_argument("--output", default="underpasses.geojson", help="Utdatafil (default: underpasses.geojson)")
    args = parser.parse_args()

    extract(args.input, args.output)