#!/usr/bin/env python3
"""
Add missing 'cma' section to all non-English locale files.
Uses English text as placeholder to fix MISSING_MESSAGE errors.
"""

import json

# The complete 'cma' section from en.json (English text as placeholder)
CMA_SECTION = {
    "steps": {
        "subject": {
            "title": "Subject Property",
            "description": "Select the property to evaluate",
        },
        "comparables": {
            "title": "Comparables",
            "description": "Choose similar properties",
        },
        "adjustments": {
            "title": "Adjustments",
            "description": "Review value adjustments",
        },
        "preview": {"title": "Preview", "description": "Review the report"},
        "export": {"title": "Export", "description": "Download or share"},
    },
    "subject": {
        "searchPlaceholder": "Search by address, city, or property ID...",
        "searchAriaLabel": "Search properties",
        "searchButton": "Search",
        "searching": "Searching...",
        "selectedSubject": "Selected Subject Property",
        "selected": "Selected",
        "price": "Price:",
        "area": "Area:",
        "rooms": "Rooms:",
        "type": "Type:",
        "searchResults": "Search Results ({count})",
        "property": "Property",
        "roomsCount": "{count} rooms",
        "nextComparables": "Next: Select Comparables",
    },
    "comparables": {
        "selectRange": "Select {min}-{max} comparable properties. Drag to reorder by relevance.",
        "refresh": "Refresh",
        "finding": "Finding similar properties...",
        "selected": "Selected:",
        "selectMore": "Select at least {count} more",
        "similarity": "Similarity",
        "noComparables": "No comparable properties found. Try adjusting your search criteria.",
        "selectedComparables": "Selected Comparables",
        "roomsCount": "{count} rooms",
        "property": "Property {id}",
        "back": "Back",
        "nextAdjustments": "Next: Review Adjustments",
    },
    "adjustments": {
        "description": "Review and adjust the valuation factors for each comparable property. Positive adjustments increase the comparable's value; negative adjustments decrease it.",
        "comparable": "Comparable {index}",
        "similarity": "Similarity:",
        "factor": "Factor",
        "subject": "Subject",
        "comparableLabel": "Comparable",
        "adjPercent": "Adj. %",
        "amount": "Amount",
        "totalAdjustments": "Total Adjustments",
        "adjustedPrice": "Adjusted Price:",
        "adjustmentSummary": "Adjustment Summary",
        "avgAdjustment": "Avg Adjustment",
        "priceRange": "Price Range",
        "medianPrice": "Median Price",
        "back": "Back",
        "nextPreview": "Next: Preview Report",
    },
    "preview": {
        "noSubject": "No subject property selected",
        "generating": "Generating CMA report...",
        "generateReport": "Generate Report",
        "noReport": "No report generated yet. Click Generate to create the CMA report.",
        "tryAgain": "Try Again",
        "back": "Back",
        "nextExport": "Next: Export Options",
        "executiveSummary": "Executive Summary",
        "estimatedValue": "Estimated Market Value",
        "range": "Range:",
        "confidenceScore": "Confidence Score",
        "confidenceHigh": "High",
        "confidenceMedium": "Medium",
        "confidenceLow": "Low",
        "pricePerSqm": "Price per m²",
        "subjectProperty": "Subject Property",
        "location": "Location",
        "area": "Area",
        "rooms": "Rooms",
        "type": "Type",
        "comparables": "Comparables ({count})",
        "property": "Property",
        "score": "Score:",
        "marketContext": "Market Context",
        "avgPricePerSqm": "Avg Price/m²",
        "medianPrice": "Median Price",
        "trend": "Trend",
        "inventory": "Inventory",
        "listings": "{count} listings",
        "failedGenerate": "Failed to generate report",
    },
    "export": {
        "noReport": "No report available. Please go back and generate a report first.",
        "back": "Back",
        "reportGenerated": "Report Generated Successfully",
        "reportReady": "Your Comparative Market Analysis report is ready for export.",
        "pdfReport": "PDF Report",
        "professionalFormat": "Professional format",
        "downloading": "Downloading...",
        "downloadPdf": "Download PDF",
        "jsonData": "JSON Data",
        "rawDataExport": "Raw data export",
        "downloadJson": "Download JSON",
        "shareLink": "Share Link",
        "copyShareableUrl": "Copy shareable URL",
        "copied": "Copied!",
        "copyLink": "Copy Link",
        "reportId": "Report ID:",
        "created": "Created:",
        "expires": "Expires:",
        "createNew": "Create New Report",
        "failedDownload": "Failed to download PDF",
    },
}


def add_cma_section(file_path: str, lang_code: str) -> bool:
    """Add 'cma' section to locale file if missing."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Skip if 'cma' already exists
        if "cma" in data:
            print(f"[OK] {lang_code}: 'cma' section already exists")
            return False

        # Insert 'cma' section in alphabetical order (before 'chat')
        # Create new ordered dict with 'cma' inserted
        new_data = {}
        inserted = False

        for key in sorted(data.keys()):
            if key == "chat" and not inserted:
                new_data["cma"] = CMA_SECTION
                inserted = True
            new_data[key] = data[key]

        # If 'chat' doesn't exist, append at end
        if not inserted:
            new_data["cma"] = CMA_SECTION

        # Write back with proper formatting
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
            f.write("\n")  # Add trailing newline

        print(f"[OK] {lang_code}: Added 'cma' section")
        return True

    except Exception as e:
        print(f"[ERROR] {lang_code}: {e}")
        return False


def main():
    """Add 'cma' section to all non-English locale files."""
    locale_files = {
        "de": "de.json",
        "es": "es.json",
        "it": "it.json",
        "pl": "pl.json",
        "pt": "pt.json",
        "ru": "ru.json",
        "tr": "tr.json",
        "uk": "uk.json",
    }

    print("Adding 'cma' section to locale files...\n")

    updated = 0
    for lang_code, filename in locale_files.items():
        if add_cma_section(filename, lang_code):
            updated += 1

    print(f"\n[OK] Updated {updated} locale files")
    print("\nNote: Using English text as placeholder.")
    print("Proper translations should be added for production use.")


if __name__ == "__main__":
    main()
