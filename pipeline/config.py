"""Shared paths and constants for the ICBC vehicle-population pipeline."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
HYPER_DIR = os.path.join(DATA, "hyper")
BUILD_DIR = os.path.join(DATA, "build")          # intermediate parquet/csv
OUTPUT_DIR = os.path.join(ROOT, "output")         # final Excel workbook

MASTER_PARQUET = os.path.join(BUILD_DIR, "master_inventory.parquet")
CLASSIFIER_CSV = os.path.join(BUILD_DIR, "vehicle_class_map.csv")

# Views feeding the Excel workbook
VIEW_BY_MODELYEAR = os.path.join(BUILD_DIR, "view_by_model_year.parquet")
VIEW_BY_MODEL = os.path.join(BUILD_DIR, "view_by_model.parquet")
VIEW_BY_MODEL_TOP = os.path.join(BUILD_DIR, "view_by_model_top.parquet")
VIEW_BY_MAKE = os.path.join(BUILD_DIR, "view_by_make.parquet")
VIEW_BY_SEGMENT = os.path.join(BUILD_DIR, "view_by_segment.parquet")
VIEW_COMMUNITY_SUMMARY = os.path.join(BUILD_DIR, "view_community_summary.parquet")

YEARS = [2021, 2022, 2023, 2024, 2025]

for _d in (DATA, HYPER_DIR, BUILD_DIR, OUTPUT_DIR):
    os.makedirs(_d, exist_ok=True)
