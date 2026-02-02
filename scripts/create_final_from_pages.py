#!/usr/bin/env python3
"""Create final.json from final_pages-yt.json."""

import json
from pathlib import Path

# Load final_pages-yt.json which has the corrected text and page info
input_path = Path(
    "/Users/sheikki/Documents/src/yamlgraph/outputs/ocr_cleanup/Yhdeksän_miehen_saappaat_Pentti_Haanpää_01_01_1945/final_pages-yt.json"
)
with open(input_path) as f:
    data = json.load(f)

# Build final.json structure from final_pages-yt.json
final = {
    "paragraphs": [],
    "corrections": data.get("corrections", []),
    "chapters": data.get("chapters", []),
    "stats": {
        "total_paragraphs": len(data["paragraphs"]),
        "total_corrections": len(data.get("corrections", [])),
        "total_chapters": len(data.get("chapters", [])),
    },
}

# Extract paragraphs with page info
for p in data["paragraphs"]:
    final["paragraphs"].append(
        {
            "text": p.get("text", ""),
            "start_page": p.get("start_page"),
            "end_page": p.get("end_page"),
        }
    )

# Save final.json
output_path = input_path.parent / "final.json"
output_path.write_text(json.dumps(final, ensure_ascii=False, indent=2))

print(f"Created final.json with {len(final['paragraphs'])} paragraphs")
print(f"Saved to: {output_path}")
